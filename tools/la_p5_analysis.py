#!/usr/bin/env python3
"""Analyse a timing-probe phase 5 capture (docs/logic_analyzer_guide.md section 10): PPU address cycling $0000, $0400, $0800, $1000 with the
1 KB CHR windows R0..R3 = 0, 1, 2, $FF. Channels: CH1 M2, CH2 PPU A12, CH3 CHR A10, CH4 PPU A10, CH5 PPU A11, CH6 CIRAM A10, CH7 CHR A11, CH8 CHR A17.
For each PPU address change (PPU lines grouped within 4 samples) reports the delay from the LAST PPU line edge to each output edge, with statistical
sub-sample estimates, and the skew between the PPU lines themselves. Usage: python3 -I tools/la_p5_analysis.py RATE_HZ FILE.sr [FILE.sr ...]"""
import sys, zipfile, collections

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def est(c, T):
    if not c: return float('nan')
    best = max(c, key=lambda k: c[k] + c.get(k + 1, 0)); n = c[best] + c.get(best + 1, 0)
    return (best + c.get(best + 1, 0) / n) * T

NAMES = {2: "CHR A10", 6: "CHR A11", 7: "CHR A17", 5: "CIRAM A10"}
def main():
    rate = float(sys.argv[1]); T = 1e9 / rate; W = int(4000 / T)          # look up to 4 us after a PPU change
    res = collections.defaultdict(collections.Counter); res2 = collections.defaultdict(collections.Counter); skew = collections.Counter(); nev = 0; unexpected = 0
    for f in sys.argv[2:]:
        d = load(f)
        ppu = [((b >> 1 & 1) << 2) | ((b >> 4 & 1) << 1) | (b >> 3 & 1) for b in d]     # A12 A11 A10
        k = 1
        while k < len(d) - W:
            if ppu[k] != ppu[k-1]:
                first = k; last = k; j = k + 1
                while j < k + 5:
                    if ppu[j] != ppu[j-1]: last = j
                    j += 1
                before, after = ppu[first - 1], ppu[last]
                bits = lambda b, s: [(b >> s) & 1 for s in (0,)]
                nev += 1
                # skew: edges of the individual PPU lines inside the group
                lines = [i for i in (2, 4, 3) if ((d[first-1] >> i) & 1) != ((d[last+1] >> i) & 1)]
                if len(lines) > 1:
                    t = [next(j for j in range(first, first + 6) if ((d[j] >> i) & 1) != ((d[first-1] >> i) & 1)) for i in lines]
                    skew[max(t) - min(t)] += 1
                for ch in (2, 5, 6, 7):
                    for j in range(first, first + W):
                        if ((d[j] >> ch) & 1) != ((d[j-1] >> ch) & 1):
                            res[(before, after, ch, (d[j] >> ch) & 1)][j - first] += 1
                            res2[(before, after, ch, (d[j] >> ch) & 1)][j - last] += 1
                            break
                k = last + 5
            else:
                k += 1
    print("PPU address changes: %d; spread between PPU lines changing together: %s samples" % (nev, dict(sorted(skew.items()))))
    print("delay = output edge minus the FIRST PPU line edge of the change (upper bound) and minus the LAST one (lower bound; negative = the output moved first)")
    for key in sorted(res):
        b, a, ch, lvl = key; c = res[key]
        c2 = res2[key]
        print("%03d -> %03d  %-9s %-4s  from first: %-18s %6.1f ns | from last: %-22s %6.1f ns" % (int(bin(b)[2:]), int(bin(a)[2:]), NAMES[ch], "rise" if lvl else "fall", dict(sorted(c.items())), est(c, T), dict(sorted(c2.items())), est(c2, T)))
    print("(sample period %.1f ns; estimates +-5 ns, include the 220 ohm + input delay, about 2-3 ns; CHR outputs come straight from the chip)" % T)
main()
