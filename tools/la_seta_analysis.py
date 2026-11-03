#!/usr/bin/env python3
"""Analyse a capture of set A (docs/logic_analyzer_guide.md): D0 = M2, D1 = PPU A12, D2 = /IRQ (D3 = PPU A10, D4 = PPU A11, D5 = CIRAM A10,
D6 = R/W, D7 = /ROMSEL). Applies the chip's A12 filter rule (16 M2 falls with A12 low before a rise) to find the counted pulses and relates them
to the falls of /IRQ. Usage: python3 -I tools/la_seta_analysis.py RATE_HZ FILE.sr"""
import sys, zipfile, collections, bisect

def main():
    rate = float(sys.argv[1]); T = 1e9 / rate
    z = zipfile.ZipFile(sys.argv[2])
    d = b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))
    n = len(d)
    bit = lambda i: [(b >> i) & 1 for b in d]
    m2, a12, irq = bit(0), bit(1), bit(2)
    def edges(s, rising): return [k for k in range(1, n) if s[k] != s[k-1] and bool(s[k]) == rising]
    m2f = edges(m2, False); a12r = edges(a12, True); a12f = edges(a12, False); irqf = edges(irq, False); irqr = edges(irq, True)
    print('%d samples, %.2f ms; M2 falls %d, A12 rises %d, A12 falls %d, /IRQ falls %d' % (n, n * T / 1e6, len(m2f), len(a12r), len(a12f), len(irqf)))
    # chip filter: M2 falls with A12 low since the last A12 high (a fall with A12 high resets); a rise counts if >= 16 such falls precede it
    lowfalls = {}
    cnt = 0; ri = 0; counted = []
    last_high_idx = None
    # walk M2 falls in order, with the A12 level at each fall
    events = sorted([(k, 'f') for k in m2f] + [(k, 'r') for k in a12r])
    for k, kind in events:
        if kind == 'f':
            if a12[k]: cnt = 0
            else: cnt += 1
        else:
            lowfalls[k] = cnt
            if cnt >= 16: counted.append(k)
    print('A12 rises with >= 16 M2 falls of low before them (counted pulses): %d' % len(counted))
    if len(counted) > 3:
        sp = [counted[i+1] - counted[i] for i in range(len(counted) - 1)]
        c = collections.Counter(round(s * T / 1000) for s in sp)
        print('spacing of counted pulses (us): %s' % c.most_common(4))
        print('  mean spacing in the picture lines: %.3f us' % (sum(s for s in sp if 1400 < s * T / 1000 * rate / 1e6 * 1e3 < 1e9) / 1) if False else '')
    hist = collections.Counter(min(v, 40) for v in lowfalls.values())
    print('histogram of low M2 falls before each A12 rise: %s' % sorted(hist.items()))
    # for each /IRQ fall: the clocking pulse = last counted rise before it
    print('\n/IRQ falls: counted pulses since the previous /IRQ fall, delay from the clocking rise')
    prev = None; res = []
    for k in irqf:
        i = bisect.bisect_right(counted, k) - 1
        if i < 0: continue
        r = counted[i]
        clk = next((x for x in m2f if x > r and a12[x]), None)   # first M2 fall with A12 high after the rise
        row = (k, r, clk)
        npulses = None if prev is None else sum(1 for c in counted if prev < c <= r)
        res.append((k, r, clk, npulses))
        prev = r
    dly = collections.Counter(); phase = collections.Counter()
    for k, r, clk, npl in res:
        s = '  /IRQ fall %.3f ms: clocking rise %.3f ms (%.0f ns before), pulses since previous /IRQ: %s' % (k * T / 1e6, r * T / 1e6, (k - r) * T, npl)
        if clk is not None:
            s += ', first M2 fall with A12 high %.0f ns after the rise, /IRQ falls %.0f ns after that fall' % ((clk - r) * T, (k - clk) * T)
            dly[k - clk] += 1; phase[clk - r] += 1
        print(s)
    if dly:
        print('\n/IRQ fall minus the clocking M2 fall (samples): %s   (one M2 period = %.1f samples)' % (sorted(dly.items()), 1e9 / 1789773 / T))
    # A12 level during the vertical blank: the longest stretch with A12 low and its position
    lows = [(a12f[i], next((x for x in a12r if x > a12f[i]), None)) for i in range(len(a12f))]
    lows = [(a, b, b - a) for a, b in lows if b is not None]
    longest = sorted(lows, key=lambda t: -t[2])[:4]
    print('\nlongest A12-low stretches: %s' % ['%.3f ms starting at %.3f ms' % (l * T / 1e6, a * T / 1e6) for a, b, l in longest])
    hl = sorted(((a12r[i], next((x for x in a12f if x > a12r[i]), None)) for i in range(len(a12r))), key=lambda t: 0)
    hi = [(b - a) for a, b in hl if b is not None]
    print('A12 high pulse width: min %.0f ns, median %.0f ns, max %.0f ns' % (min(hi) * T, sorted(hi)[len(hi)//2] * T, max(hi) * T))

main()
