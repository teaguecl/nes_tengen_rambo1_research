#!/usr/bin/env python3
"""Analyse a timing-probe phase 3 capture (docs/logic_analyzer_guide.md section 10): CPU-cycle IRQ every 164 cycles, handler writes $E000
then $E001. Channels: CH1 M2 (D0), CH3 /IRQ (D2), CH7 R/W (D6), CH8 /ROMSEL (D7). Reports the /IRQ period, /IRQ falling against the M2 fall,
/IRQ rising against the $E000 write cycle (/ROMSEL falling, M2 rising, M2 falling) with statistical sub-sample delays, which write cycle releases it,
and how long /IRQ stays low. Usage: python3 -I tools/la_p3_analysis.py RATE_HZ FILE.sr [FILE.sr ...]"""
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
    per = []; fall_m2f = collections.Counter(); low = []
    rise_rsf = collections.Counter(); rise_m2r = collections.Counter(); rise_m2f = collections.Counter()
    which = collections.Counter(); ce = collections.Counter(); n_irq = 0
    for f in sys.argv[2:]:
        d = load(f)
        m2 = [b & 1 for b in d]; irq = [b >> 2 & 1 for b in d]; rw = [b >> 6 & 1 for b in d]; rs = [b >> 7 & 1 for b in d]
        m2r, m2f = edges(m2, True), edges(m2, False)
        ifl, irs = edges(irq, False), edges(irq, True)
        rsf = [k for k in edges(rs, False) if not rw[k]]            # write cycles
        rsr = edges(rs, True)
        mper = [m2r[i+1] - m2r[i] for i in range(len(m2r) - 1)]
        if not mper or abs(sum(mper) / len(mper) * T - 558.9) > 15 or max(mper) > 1.3 * sum(mper) / len(mper): continue
        for a, b in zip(ifl, ifl[1:]): per.append((b - a) * T / 558.9)
        for k in ifl:
            m = last_before(m2f, k)
            if m is not None: fall_m2f[k - m] += 1
            n_irq += 1
            r = next((x for x in irs if x > k), None)
            if r is None: continue
            low.append((r - k) * T / 558.9)
            w = [x for x in rsf if x > k][:2]
            if not w: continue
            w0 = w[0]
            wend = next((x for x in rsr if x > w0), None)
            if wend is None: continue
            which['released during 1st write ($E000)' if w0 - 2 <= r <= wend + 2 else 'other'] += 1
            if w0 - 2 <= r <= wend + 2:
                rise_rsf[r - w0] += 1
                m = last_before(m2r, w0); mf = next((x for x in m2f if x > w0), None)
                if m is not None: rise_m2r[r - m] += 1
                if mf is not None: rise_m2f[r - mf] += 1
            for x in [x for x in rsf if x > k][:1]:
                ce_k = [(b >> 3) & 1 for b in d[x: x + 4]]
        print("")
    print("/IRQ falling edges used: %d" % n_irq)
    if per: print("period between /IRQ falls: mean %.2f M2 cycles (expected 164), min %.1f max %.1f" % (sum(per) / len(per), min(per), max(per)))
    print("/IRQ low time: mean %.1f M2 cycles, min %.1f, max %.1f" % (sum(low) / len(low), min(low), max(low)))
    print("which write releases /IRQ:", dict(which))
    print("/IRQ falls after the previous M2 fall: samples %s -> about %.1f ns" % (dict(sorted(fall_m2f.items())), est(fall_m2f, T)))
    print("/IRQ rises after /ROMSEL falls in the $E000 write: samples %s -> about %.1f ns" % (dict(sorted(rise_rsf.items())), est(rise_rsf, T)))
    print("/IRQ rises after M2 rises: samples %s -> about %.1f ns" % (dict(sorted(rise_m2r.items())), est(rise_m2r, T)))
    print("/IRQ rises relative to the end-of-cycle M2 fall (negative = before): samples %s" % dict(sorted(rise_m2f.items())))
    print("(sample period %.1f ns; +-5 ns)" % T)
main()
