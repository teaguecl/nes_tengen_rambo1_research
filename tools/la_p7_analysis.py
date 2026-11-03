#!/usr/bin/env python3
"""Analyse a timing-probe phase 7 or 8 capture (docs/logic_analyzer_guide.md section 10): the $E001 (phase 7) or $E000 (phase 8) write is placed in cycle j = 18..26
after the $C001 write cycle (CPU mode, latch 4: first expiry at cycle 22, next at 42). Channels: CH1 M2, CH2 R/W, CH3 /ROMSEL, CH4 A0, CH5 A13, CH6 /IRQ.
Cycles are counted in M2 periods; cycle 0 is the one that contains the $C001 write (ROMSEL falling with R/W low, A13 = 0, A0 = 1). For every j reports when /IRQ
asserted (cycle after $C001) and when it was released. The reference model predicts (rom/tools/probe_check.py): phase 7 expiry at 22 for j <= 22, at 42 for j >= 23;
phase 8 lost for j <= 22, asserted at 22 for j >= 23. Usage: python3 -I tools/la_p7_analysis.py PHASE RATE_HZ FILE.sr [FILE.sr ...]"""
import sys, zipfile, collections, bisect

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def edges(sig, rising=None):
    return [k for k in range(1, len(sig)) if sig[k] != sig[k-1] and (rising is None or bool(sig[k]) == rising)]

def main():
    phase = int(sys.argv[1]); rate = float(sys.argv[2]); T = 1e9 / rate
    tgt_a0 = 1 if phase == 7 else 0                      # $E001 has A0 = 1, $E000 has A0 = 0
    res = collections.defaultdict(collections.Counter); nblk = 0; skipped = 0
    for f in sys.argv[3:]:
        d = load(f)
        m2 = [b & 1 for b in d]; rw = [b >> 1 & 1 for b in d]; ro = [b >> 2 & 1 for b in d]
        a0 = [b >> 3 & 1 for b in d]; a13 = [b >> 4 & 1 for b in d]; irq = [b >> 5 & 1 for b in d]
        m2r = edges(m2, True)
        per = [m2r[i+1] - m2r[i] for i in range(len(m2r) - 1)]
        if not per or abs(sum(per) / len(per) * T - 558.9) > 15 or max(per) > 1.3 * sum(per) / len(per): skipped += 1; continue
        def cyc(k): return bisect.bisect_right(m2r, k) - 1          # index of the M2 cycle containing sample k
        wr = [(cyc(k), a0[k+2], a13[k+2]) for k in edges(ro, False) if not rw[k] and k + 2 < len(d)]   # write cycles: (cycle, A0, A13)
        ifall, irise = edges(irq, False), edges(irq, True)
        c001 = [c for c, a, b in wr if a == 1 and b == 0]
        tgt = [c for c, a, b in wr if a == tgt_a0 and b == 1]
        for c0 in c001:
            nxt = [c for c in tgt if c0 < c < c0 + 40]
            if not nxt: continue
            j = nxt[0] - c0
            last = max(c for c in c001 if c <= c0)
            fl = [cyc(k) - c0 for k in ifall if m2r[0] < k and c0 <= cyc(k) < c0 + 60]
            rs = [cyc(k) - c0 for k in irise if c0 <= cyc(k) < c0 + 70]
            res[j][("assert %d" % fl[0] if fl else "no assert", "released %d" % rs[0] if rs else "-")] += 1; nblk += 1
    print("blocks analysed: %d (bursts rejected: %d); phase %d, j = cycles from the $C001 write cycle to the %s write cycle" % (nblk, skipped, phase, "$E001" if phase == 7 else "$E000"))
    pred = {7: lambda j: "assert 22" if j <= 22 else "assert 42", 8: lambda j: "no assert" if j <= 22 else "assert 22"}[phase]
    for j in sorted(res):
        print("j=%2d  model: %-10s  measured: %s" % (j, pred(j), dict(res[j])))
main()
