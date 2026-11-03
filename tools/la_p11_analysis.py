#!/usr/bin/env python3
"""Analyse a timing-probe phase 11 or 12 capture (docs/logic_analyzer_guide.md section 10): A12 mode with no PPU activity, blocks of $E000, $C001, $E001, $E000 (acknowledge) with the
gaps g1 (E000 to C001) and g2 (C001 to E001) from a grid. Channels: CH1 M2, CH2 R/W, CH3 /ROMSEL, CH4 A0, CH5 A13, CH6 /IRQ. The reference model predicts that /IRQ stays high in every block
(no A12 pulse, so no clock); a low /IRQ is a difference (finding F-073). Prints, for each (g1, g2) and each alignment of the $E001 write cycle to a 4-cycle count (cycle index mod 4, counted from the first M2 rise of the capture, so only comparable within one capture), how many blocks had /IRQ low and when it went low relative to the $E001 and $C001 write cycles.
Usage: python3 -I tools/la_p11_analysis.py RATE_HZ FILE.sr [FILE.sr ...]"""
import sys, zipfile, collections, bisect

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def edges(sig, rising=None):
    return [k for k in range(1, len(sig)) if sig[k] != sig[k-1] and (rising is None or bool(sig[k]) == rising)]

def main():
    rate = float(sys.argv[1]); T = 1e9 / rate
    table = collections.defaultdict(collections.Counter); nblocks = 0
    for f in sys.argv[2:]:
        d = load(f)
        m2 = [b & 1 for b in d]; rw = [b >> 1 & 1 for b in d]; ro = [b >> 2 & 1 for b in d]; a0 = [b >> 3 & 1 for b in d]; a13 = [b >> 4 & 1 for b in d]; irq = [b >> 5 & 1 for b in d]
        r, fl = edges(m2, True), edges(m2, False)
        per = [r[i+1] - r[i] for i in range(len(r) - 1)]
        if not per or abs(sum(per) / len(per) * T - 558.9) > 15 or max(per) > 1.3 * sum(per) / len(per): continue
        n = len(r) - 1
        fall = []
        for k in range(n):
            j = bisect.bisect_right(fl, r[k]); fall.append(fl[j] if j < len(fl) and fl[j] < r[k+1] else None)
        wr = []
        for k in edges(ro, False):
            if not rw[k] and k + 2 < len(d):
                c = bisect.bisect_right(r, k) - 1
                if 0 <= c < n: wr.append((c, (a0[k+2], a13[k+2])))
        KIND = {(0, 1): 'E000', (1, 0): 'C001', (1, 1): 'E001', (0, 0): 'C000'}
        wr = [(c, KIND.get(t, '?')) for c, t in wr]
        low = [None if fall[c] is None else 1 - irq[min(fall[c] + 2, len(d) - 1)] for c in range(n)]
        for i in range(len(wr) - 3):
            if [w[1] for w in wr[i:i+4]] != ['E000', 'C001', 'E001', 'E000']: continue
            c0, c1, c2, c3 = [w[0] for w in wr[i:i+4]]
            if c3 + 2 >= n or c0 < 1: continue
            nblocks += 1
            lows = [c for c in range(c0, c3 + 1) if low[c]]
            if lows:
                first = lows[0]
                key = "low, first at E001%+d / C001%+d, last low cycle E001%+d" % (first - c2, first - c1, lows[-1] - c2)
            else: key = "high throughout"
            table[(c1 - c0, c2 - c1, c2 % 4)][key] += 1
    print("blocks analysed: %d" % nblocks)
    for g in sorted(table):
        for k, c in sorted(table[g].items(), key=lambda x: -x[1]):
            print("g1=%3d g2=%3d  E001 cycle mod 4 = %d  %4d x  %s" % (g[0], g[1], g[2], c, k))
main()
