#!/usr/bin/env python3
"""Analyse a timing-probe phase 6 capture (docs/logic_analyzer_guide.md section 10): $8001 written $FE / $00 alternately (R0), PPU address 0.
Channels: CH1 M2, CH2 R/W, CH3 /ROMSEL, CH4 D7, CH7 CHR A11 (R0 bit 1, D1), CH8 CHR A17 (R0 bit 7, D7). Reports whether the CHR outputs change inside the
write window (transparent) or at its end, and for CHR A17 the delay after the D7 edge and after /ROMSEL falling. Compare phase 2 (F-069, $8000).
Usage: python3 -I tools/la_p6_analysis.py RATE_HZ FILE.sr [FILE.sr ...]"""
import sys, zipfile, collections, bisect

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def edges(sig, rising=None):
    return [k for k in range(1, len(sig)) if sig[k] != sig[k-1] and (rising is None or bool(sig[k]) == rising)]

def last_before(lst, k):
    i = bisect.bisect_right(lst, k) - 1
    return lst[i] if i >= 0 else None

def est(c, T):
    if not c: return float('nan')
    best = max(c, key=lambda k: c[k] + c.get(k + 1, 0)); n = c[best] + c.get(best + 1, 0)
    return (best + c.get(best + 1, 0) / n) * T

def main():
    rate = float(sys.argv[1]); T = 1e9 / rate
    where = collections.Counter(); rs = {(ch, l): collections.Counter() for ch in (6, 7) for l in (0, 1)}; dd = {l: collections.Counter() for l in (0, 1)}
    d7_in = collections.Counter(); d7_after = collections.Counter()
    for f in sys.argv[2:]:
        d = load(f)
        m2 = [b & 1 for b in d]; rw = [b >> 1 & 1 for b in d]; ro = [b >> 2 & 1 for b in d]; d7 = [b >> 3 & 1 for b in d]
        m2r, m2f, rsf = edges(m2, True), edges(m2, False), edges(ro, False)
        per = [m2r[i+1] - m2r[i] for i in range(len(m2r) - 1)]
        if not per or abs(sum(per) / len(per) * T - 558.9) > 15 or max(per) > 1.3 * sum(per) / len(per): continue
        d7e = edges(d7)
        for ch in (6, 7):
            sig = [b >> ch & 1 for b in d]
            for k in edges(sig):
                w = last_before(rsf, k)
                if w is None: continue
                if m2[k] and not ro[k] and not rw[k] and (k - w) * T <= 400: where[(ch, 'inside the window')] += 1
                elif (k - (last_before(m2f, k) or -999)) * T <= 100: where[(ch, 'at the M2 fall')] += 1
                else: where[(ch, 'elsewhere')] += 1
                if m2[k] and not ro[k] and not rw[k] and (k - w) * T <= 400:
                    rs[(ch, sig[k])][k - w] += 1
                    if ch == 7:
                        e = last_before(d7e, k)
                        if e is not None and k - e <= 6 and e > w - 1: dd[sig[k]][k - e] += 1
    for (ch, w), n in sorted(where.items()): print("%s edges %s: %d" % ("CHR A11" if ch == 6 else "CHR A17", w, n))
    for ch, nm in ((7, "CHR A17"), (6, "CHR A11")):
        for l, dn in ((1, "rises (write $FE)"), (0, "falls (write $00)")):
            print("%s %s: after /ROMSEL falling %s -> about %.1f ns" % (nm, dn, dict(sorted(rs[(ch, l)].items())), est(rs[(ch, l)], T)))
    for l, dn in ((1, "rises"), (0, "falls")):
        print("CHR A17 %s after the D7 edge that precedes it (inside the window): %s -> about %.1f ns" % (dn, dict(sorted(dd[l].items())), est(dd[l], T)))
    print("(sample period %.1f ns; +-5 ns, includes the 220 ohm + input delay on D7 and /ROMSEL, about 2-3 ns)" % T)
main()
