#!/usr/bin/env python3
"""Analyse a logic-analyser capture of capture set B (docs/logic_analyzer_guide.md): D0 = M2, D1 = R/W, D2 = /ROMSEL, D3 = PRG /CE.
Prints the /CE truth table on stable samples, how many samples fall outside it, and the edge-to-edge delays, estimated statistically
from the fraction of cases where an edge lands one sample later (valid when the delay is under one sample and the analyser clock is
unrelated to the console's). Usage: python3 -I tools/la_setb_analysis.py RATE_HZ FILE.sr [FILE.sr ...]
Bursts with dropped samples are rejected by their M2 period."""
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
    rate = float(sys.argv[1]); files = sys.argv[2:]
    T = 1e9 / rate
    table = collections.defaultdict(collections.Counter)
    out_low = enab = enab_low = 0
    cnt = {k: collections.Counter() for k in ('rsf-m2r', 'rsr-m2f', 'cef-rsf', 'cef-m2r', 'cer-m2f', 'cer-rsr')}
    used = rejected = 0
    for f in files:
        d = load(f)
        m2 = [b & 1 for b in d]; rw = [b >> 1 & 1 for b in d]; rs = [b >> 2 & 1 for b in d]; ce = [b >> 3 & 1 for b in d]
        m2r, m2f = edges(m2, True), edges(m2, False)
        per = [m2r[i+1] - m2r[i] for i in range(len(m2r) - 1)]
        mean = sum(per) / len(per) if per else 0
        if not per or abs(mean * T - 558.7) > 15 or max(per) > mean * 1.3 or min(per) < mean * 0.7:
            rejected += 1; continue
        used += 1
        n = len(d)
        for k in range(2, n - 2):
            if any((d[j] ^ d[k]) & 7 for j in (k-2, k-1, k+1, k+2)): continue
            table[(m2[k], rw[k], rs[k])][ce[k]] += 1
        for k in range(n):
            e = m2[k] and rw[k] and not rs[k]
            enab += bool(e); enab_low += bool(e and not ce[k]); out_low += bool(not ce[k] and not e)
        rsf, rsr = edges(rs, False), edges(rs, True); cef, cer = edges(ce, False), edges(ce, True)
        for k in rsf:
            a = last_before(m2r, k)
            if a is not None and k - a < mean: cnt['rsf-m2r'][k - a] += 1
        for k in rsr:
            a = last_before(m2f, k)
            if a is not None and k - a < mean: cnt['rsr-m2f'][k - a] += 1
        for k in cef:
            a = last_before(rsf, k); b = last_before(m2r, k)
            if a is not None and k - a < mean: cnt['cef-rsf'][k - a] += 1
            if b is not None and k - b < mean: cnt['cef-m2r'][k - b] += 1
        for k in cer:
            a = last_before(rsr, k); b = last_before(m2f, k)
            if a is not None and k - a < mean: cnt['cer-rsr'][k - a] += 1
            if b is not None and k - b < mean: cnt['cer-m2f'][k - b] += 1
    print('captures used %d, rejected %d, sample period %.1f ns' % (used, rejected, T))
    print('/CE on stable samples, (M2, R/W, /ROMSEL) -> counts of /CE level (0 = asserted):')
    for key in sorted(table): print('  ', key, dict(table[key]))
    print('samples with M2=1, R/W=1, /ROMSEL=0: %d, of which /CE low: %d (%.2f%%)' % (enab, enab_low, 100.0 * enab_low / max(1, enab)))
    print('samples with /CE low outside that condition (one-sample edge lag): %d' % out_low)
    names = {'rsf-m2r': '/ROMSEL fall after M2 rise', 'rsr-m2f': '/ROMSEL rise after M2 fall', 'cef-rsf': '/CE fall after /ROMSEL fall',
             'cef-m2r': '/CE fall after M2 rise', 'cer-m2f': '/CE rise after M2 fall', 'cer-rsr': '/CE rise after /ROMSEL rise'}
    for k, c in cnt.items():
        tot = sum(c.values())
        if not tot: continue
        near = {a: b for a, b in c.items() if a < 6}
        m = sum(a * b for a, b in near.items()) / sum(near.values())
        print('%-30s n=%5d  samples %s  mean %.2f samples = %.1f ns' % (names[k], tot, sorted(near.items()), m, m * T))

main()
