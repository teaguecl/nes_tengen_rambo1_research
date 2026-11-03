#!/usr/bin/env python3
"""Analyse a timing-probe phase 4 capture (docs/logic_analyzer_guide.md section 10): the loop reads $8000, $A000 and $C000 with R6 = $00, R7 = $15, RF = $0A, between code fetches from the fixed bank ($E000-$FFFF).
Channels: CH1 M2, CH2 CPU A14, CH3 PRG A13, CH4 PRG A14, CH5 CPU A13, CH6 PRG A15, CH7 PRG A16, CH8 PRG A17. The PRG outputs follow CPU A13/A14 through the PRG registers (F-011):
$8000 window (A14 A13 = 00): 0; $A000 (01): $15; $C000 (10): $0A; $E000 (11): $1F. Reports the output pattern seen for each CPU window (a check of the wiring), and for each change of CPU A13/A14
(lines grouped within 4 samples) the delay from the first and from the last CPU line edge to each output edge, with statistical sub-sample estimates. Usage: python3 -I tools/la_p4_analysis.py RATE_HZ FILE.sr [FILE.sr ...]"""
import sys, zipfile, collections

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def est(c, T):
    if not c: return float('nan')
    best = max(c, key=lambda k: c[k] + c.get(k + 1, 0)); n = c[best] + c.get(best + 1, 0)
    return (best + c.get(best + 1, 0) / n) * T

OUT = {2: "PRG A13", 3: "PRG A14", 5: "PRG A15", 6: "PRG A16", 7: "PRG A17"}
EXPECT = {0: 0x00, 1: 0x15, 2: 0x0A, 3: 0x1F}
def main():
    rate = float(sys.argv[1]); T = 1e9 / rate; W = int(300 / T)          # look only up to 300 ns (about half a cycle) after a CPU address change
    res = collections.defaultdict(collections.Counter); res2 = collections.defaultdict(collections.Counter); pattern = collections.Counter(); nev = 0
    for f in sys.argv[2:]:
        d = load(f)
        win = [((b >> 1 & 1) << 1) | (b >> 4 & 1) for b in d]                       # CPU A14, A13
        val = [sum(((b >> ch) & 1) << i for i, ch in enumerate((2, 3, 5, 6, 7))) for b in d]   # PRG A13..A17
        for k in range(12, len(d) - 12):
            if win[k-5] == win[k-4] == win[k-3] and win[k+3] == win[k+4] == win[k+5]:     # stable before and after: sample the pattern
                pass
        k = 1
        while k < len(d) - W:
            if win[k] != win[k-1]:
                first = k; last = k
                for j in range(k + 1, k + 5):
                    if win[j] != win[j-1]: last = j
                before, after = win[first - 1], win[last]
                nev += 1
                if all(win[j] == after for j in range(last + 1, last + 6)): pattern[(after, val[min(last + 8, len(d) - 1)])] += 1
                for ch in OUT:
                    for j in range(first, first + W):
                        if ((d[j] >> ch) & 1) != ((d[j-1] >> ch) & 1):
                            key = (before, after, ch, (d[j] >> ch) & 1)
                            res[key][j - first] += 1; res2[key][j - last] += 1
                            break
                k = last + 5
            else: k += 1
    print("CPU A13/A14 changes: %d" % nev)
    for w in sorted(set(a for a, v in pattern)):
        vals = {v: c for (a, v), c in pattern.items() if a == w}
        print("CPU window A14A13=%d%d: PRG A13-A17 as a number (expected %02X): %s" % (w >> 1, w & 1, EXPECT[w], {"%02X" % v: c for v, c in sorted(vals.items(), key=lambda x: -x[1])[:3]}))
    print("delay = output edge minus the FIRST CPU line edge (upper bound) / minus the LAST one (lower bound; negative = the output moved first)")
    for key in sorted(res):
        b, a, ch, lvl = key
        print("%d%d -> %d%d  %-8s %-4s  from first %6.1f ns | from last %6.1f ns   (%d events)" % (b >> 1, b & 1, a >> 1, a & 1, OUT[ch], "rise" if lvl else "fall", est(res[key], T), est(res2[key], T), sum(res[key].values())))
    print("(sample period %.1f ns; estimates +-5 ns, include the 220 ohm + input delay, about 2-3 ns; the PRG outputs come straight from the chip)" % T)
main()
