#!/usr/bin/env python3
"""Analyse a timing-probe phase 1 capture (docs/logic_analyzer_guide.md section 10): D0 = CH2, M2 = CH1, /CE = CH3, CIRAM A10 = CH6, R/W = CH7,
/ROMSEL = CH8, with $A000 written $00/$01 alternately and PPU address $2400. Reports /CE during writes, the CIRAM A10 output change against
/ROMSEL falling and M2 rising (sub-sample delay estimated statistically), and whether the output ever changes outside the write window.
Usage: python3 -I tools/la_p1_analysis.py RATE_HZ FILE.sr [FILE.sr ...]"""
import sys, zipfile, collections, bisect

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def edges(sig, rising):
    return [k for k in range(1, len(sig)) if sig[k] != sig[k-1] and bool(sig[k]) == rising]

def last_before(lst, k):
    i = bisect.bisect_right(lst, k) - 1
    return lst[i] if i >= 0 else None

def main():
    rate = float(sys.argv[1]); T = 1e9 / rate
    ce_in_write = collections.Counter(); ce_other = collections.Counter()
    d_rsf = {0: collections.Counter(), 1: collections.Counter()}; d_m2r = {0: collections.Counter(), 1: collections.Counter()}; d_m2f = collections.Counter()
    rs_m2 = collections.Counter()
    ci_in = ci_out = 0; wr = 0
    for f in sys.argv[2:]:
        d = load(f)
        m2 = [b & 1 for b in d]; dd = [b >> 1 & 1 for b in d]; ce = [b >> 2 & 1 for b in d]
        ci = [b >> 5 & 1 for b in d]; rw = [b >> 6 & 1 for b in d]; rs = [b >> 7 & 1 for b in d]
        m2r, m2f, rsf, rsr = edges(m2, True), edges(m2, False), edges(rs, False), edges(rs, True)
        for k in rsf:
            m = last_before(m2r, k)
            if m is not None: rs_m2[k - m] += 1
        wr += sum(1 for k in range(1, len(d)) if rw[k-1] and not rw[k])
        for k in range(2, len(d) - 2):
            if m2[k] and not rs[k] and not rw[k] and len({m2[k-1], m2[k+1]}) == 1:
                (ce_in_write if True else ce_other)[ce[k]] += 1
            elif m2[k] and not rs[k] and rw[k]: ce_other[ce[k]] += 1
        for k in range(1, len(d)):
            if ci[k] == ci[k-1]: continue
            r = last_before(rsf, k); m = last_before(m2r, k); mf = last_before(m2f, k)
            if r is None or m is None or mf is None: continue
            if m2[k] and not rs[k] and not rw[k] and (k - r) * T <= 250:
                ci_in += 1; d_rsf[ci[k]][k - r] += 1; d_m2r[ci[k]][k - m] += 1
            else:
                ci_out += 1; d_m2f[k - mf] += 1
    print("writes seen: %d" % wr)
    print("/CE during a write (M2 high, /ROMSEL low, R/W low): high %d, low %d" % (ce_in_write[1], ce_in_write[0]))
    print("/CE during a read of $8000+ (M2 high, /ROMSEL low, R/W high): high %d, low %d" % (ce_other[1], ce_other[0]))
    print("CIRAM A10 changes inside the write window: %d; outside it: %d (samples after last M2 fall: %s)" % (ci_in, ci_out, dict(d_m2f)))
    def est(c):
        if not c: return None
        ks = sorted(c); best = max(ks, key=lambda k: c[k] + c.get(k + 1, 0)); n = c[best] + c.get(best + 1, 0)
        return (best + c.get(best + 1, 0) / n) * T if n else None
    print("/ROMSEL falls after M2 rises: samples %s -> about %.1f ns" % (dict(sorted(rs_m2.items())), est(rs_m2)))
    for lvl, nm in ((1, "rises (vertical, A10 = 1)"), (0, "falls (horizontal, A11 = 0)")):
        for tag, c in (("M2 rising", d_m2r[lvl]), ("/ROMSEL falling", d_rsf[lvl])):
            e = est(c)
            print("CIRAM A10 %s, after %s: samples %s -> about %.1f ns" % (nm, tag, dict(sorted(c.items())), e if e is not None else float('nan')))
    print("(sample period %.1f ns; estimates are +-5 ns and include the 220 ohm + input delay, about 2-3 ns)" % T)
main()
