#!/usr/bin/env python3
"""Analyse a timing-probe phase 2 capture (docs/logic_analyzer_guide.md section 10): $8000 written $80 / $00 alternately (the C bit), R0 = $FE, R2 = 0,
PPU address 0. Channels: CH1 M2, CH2 R/W, CH3 /ROMSEL, CH4 D7, CH7 CHR A11, CH8 CHR A17. A write of $00 (C = 0) selects R0 (outputs high), $80 selects R2 (low).
Finding: the outputs change at the END of the write cycle (M2 falling, /ROMSEL rising), not at the start. Reports whether every output change lies just after an
M2 fall that ends a write cycle (R/W low, /ROMSEL low just before), the delay after M2 falling and after /ROMSEL rising for each direction and output,
the skew between CHR A11 and A17, and when D7 becomes valid. Usage: python3 -I tools/la_p2_analysis.py RATE_HZ FILE.sr [FILE.sr ...]"""
import sys, zipfile, collections, bisect

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def edges(sig, rising):
    return [k for k in range(1, len(sig)) if sig[k] != sig[k-1] and bool(sig[k]) == rising]

def last_before(lst, k):
    i = bisect.bisect_right(lst, k) - 1
    return lst[i] if i >= 0 else None

def est(c, T):
    if not c: return float('nan')
    best = max(c, key=lambda k: c[k] + c.get(k + 1, 0)); n = c[best] + c.get(best + 1, 0)
    return (best + c.get(best + 1, 0) / n) * T

def main():
    rate = float(sys.argv[1]); T = 1e9 / rate
    rs_m2 = collections.Counter(); dsetup = collections.Counter(); inside = outside = 0; skew = collections.Counter()
    r = {(ch, lvl): collections.Counter() for ch in (6, 7) for lvl in (0, 1)}; m = {k: collections.Counter() for k in r}
    for f in sys.argv[2:]:
        d = load(f)
        d7 = [b >> 3 & 1 for b in d]; m2 = [b & 1 for b in d]; rw = [b >> 1 & 1 for b in d]; rs = [b >> 2 & 1 for b in d]
        m2r, m2f = edges(m2, True), edges(m2, False)
        rsf = edges(rs, False)
        per = [m2r[i+1] - m2r[i] for i in range(len(m2r) - 1)]
        if not per or abs(sum(per) / len(per) * T - 558.9) > 15 or max(per) > 1.3 * sum(per) / len(per): continue
        for k in rsf:
            a = last_before(m2r, k)
            if a is not None: rs_m2[k - a] += 1
        rsr = edges(rs, True)
        for ch in (6, 7):
            sig = [b >> ch & 1 for b in d]
            for k in range(1, len(d)):
                if sig[k] == sig[k-1]: continue
                f = last_before(m2f, k); q = last_before(rsr, k)
                if f is None or q is None: continue
                if (k - f) * T <= 400 and not rw[f - 1] and not rs[f - 1]:
                    inside += 1; r[(ch, sig[k])][k - q] += 1; m[(ch, sig[k])][k - f] += 1
                else: outside += 1
        for k in range(2, len(d)):                     # data setup: last D7 edge before the M2 fall of a write cycle
            if m2[k-1] and not m2[k] and not rw[k-1] and not rs[k-1]:
                j = k - 1
                while j > 0 and d7[j] == d7[j-1] and k - j < 40: j -= 1
                dsetup[(k - j) * T // 10 * 10] += 1
        a11 = edges([b >> 6 & 1 for b in d], True) + edges([b >> 6 & 1 for b in d], False)
        a17 = sorted(edges([b >> 7 & 1 for b in d], True) + edges([b >> 7 & 1 for b in d], False))
        for k in a11:
            j = bisect.bisect_left(a17, k - 3)
            if j < len(a17) and abs(a17[j] - k) <= 3: skew[a17[j] - k] += 1
    print("output changes within 400 ns after the M2 fall that ends a write cycle: %d; elsewhere: %d" % (inside, outside))
    print("/ROMSEL falls after M2 rises: %s -> about %.1f ns" % (dict(sorted(rs_m2.items())), est(rs_m2, T)))
    for ch, nm in ((6, "CHR A11"), (7, "CHR A17")):
        for lvl, dn in ((1, "rises (write $00, R0 selected)"), (0, "falls (write $80, R2 selected)")):
            print("%s %s: after /ROMSEL rising %s -> about %.1f ns; after M2 falling %s -> about %.1f ns" %
                  (nm, dn, dict(sorted(r[(ch, lvl)].items())), est(r[(ch, lvl)], T), dict(sorted(m[(ch, lvl)].items())), est(m[(ch, lvl)], T)))
    print("CHR A17 edge minus CHR A11 edge (samples): %s" % dict(sorted(skew.items())))
    print("D7 stable for (ns, binned) before the M2 fall that ends a write cycle: %s" % dict(sorted(dsetup.items())))
    print("(sample period %.1f ns; +-5 ns)" % T)
main()
