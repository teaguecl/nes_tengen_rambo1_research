#!/usr/bin/env python3
"""Analyse a timing-probe phase 16 capture (docs/logic_analyzer_guide.md section 10): the phase 10 loop ($E000 at 3, $C001 at 7, $E001 at 11, $E000 at 177 of each iteration, rendering
off) run for 40 iterations at each period 224, 225, ... 236 M2 cycles, then round again. Channels: CH1 M2, CH2 R/W, CH3 /ROMSEL, CH4 A0, CH5 A13, CH6 /IRQ. For each period (the number
of M2 cycles from one $C001 write to the next) reports how many iterations had /IRQ low during the iteration and when it went low relative to the $E001 write (the model predicts never).
Usage: python3 -I tools/la_p16_analysis.py RATE_HZ FILE.sr [FILE.sr ...]"""
import sys, zipfile, collections, bisect

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def edges(sig, rising=None):
    return [k for k in range(1, len(sig)) if sig[k] != sig[k-1] and (rising is None or bool(sig[k]) == rising)]

def main():
    rate = float(sys.argv[1]); T = 1e9 / rate
    table = collections.defaultdict(collections.Counter)
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
        KIND = {(0, 1): 'E000', (1, 0): 'C001', (1, 1): 'E001', (0, 0): 'C000'}
        wr = []
        for k in edges(ro, False):
            if not rw[k] and k + 2 < len(d):
                c = bisect.bisect_right(r, k) - 1
                if 0 <= c < n: wr.append((c, KIND.get((a0[k+2], a13[k+2]), '?')))
        low = [None if fall[c] is None else 1 - irq[min(fall[c] + 2, len(d) - 1)] for c in range(n)]
        for i in range(len(wr) - 4):
            if [w[1] for w in wr[i:i+4]] != ['E000', 'C001', 'E001', 'E000'] or wr[i+4][1] != 'E000': continue
            c1, c2, c3, c0n = wr[i+1][0], wr[i+2][0], wr[i+3][0], wr[i+4][0]
            if c2 - c1 != 4 or c0n + 2 >= n: continue
            period = c0n - wr[i][0]
            lows = [c for c in range(c1, c0n) if low[c]]
            table[period]["low at E001%+d" % (lows[0] - c2) if lows else "high"] += 1
    for p in sorted(table):
        print("period %3d  %s" % (p, dict(table[p])))
main()
