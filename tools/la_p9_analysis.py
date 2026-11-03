#!/usr/bin/env python3
"""Analyse a timing-probe phase 9 or 10 capture (docs/logic_analyzer_guide.md section 10): A12-mode race. Channels: CH1 M2, CH2 R/W, CH3 /ROMSEL, CH4 A0, CH5 A13,
CH6 /IRQ, CH7 PPU A12. The ROM loops every 228 cycles: $E000, $C001 (A12 mode, latch 0), then (phase 9) $E001 or (phase 10, after an early $E001) $E000 written 170 cycles after
$C001; the loop drifts 2/3 cycle per iteration against the PPU's line pairs, so the swept write crosses the M2 fall that clocks the counter.
The capture is replayed through reference/rambo1.py: every M2 cycle gets the captured writes and the captured A12 level at the M2 fall, and the model's /IRQ is compared with the
measured /IRQ just after the fall. A second model with the enable flag forced on finds the clocking cycle c of the expiring pulse. Results are grouped by d = (swept write cycle) - c.
Usage: [A12_LAG=n] python3 -I tools/la_p9_analysis.py PHASE RATE_HZ FILE.sr [FILE.sr ...]   (A12_LAG: the A12 sample is taken n samples after the M2 fall, default 1)"""
import sys, os, zipfile, collections, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reference'))
from rambo1 import Rambo1

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def edges(sig, rising=None):
    return [k for k in range(1, len(sig)) if sig[k] != sig[k-1] and (rising is None or bool(sig[k]) == rising)]

def main():
    phase = int(sys.argv[1]); rate = float(sys.argv[2]); T = 1e9 / rate
    lag = int(os.environ.get('A12_LAG', '1'))          # A12 is taken at (M2 fall sample + lag); the chip's own sampling point is estimated by trying several
    sweep_a0 = 1 if phase == 9 else 0
    table = collections.defaultdict(collections.Counter); mism_cycles = ncyc = amb = iters = 0; a12_skew = collections.Counter()
    for f in sys.argv[3:]:
        d = load(f)
        m2 = [b & 1 for b in d]; rw = [b >> 1 & 1 for b in d]; ro = [b >> 2 & 1 for b in d]; a0 = [b >> 3 & 1 for b in d]
        a13 = [b >> 4 & 1 for b in d]; irq = [b >> 5 & 1 for b in d]; a12 = [b >> 6 & 1 for b in d]
        r, fl = edges(m2, True), edges(m2, False)
        per = [r[i+1] - r[i] for i in range(len(r) - 1)]
        if not per or abs(sum(per) / len(per) * T - 558.9) > 15 or max(per) > 1.3 * sum(per) / len(per): continue
        n = len(r) - 1
        fall = []
        for k in range(n):
            j = bisect.bisect_right(fl, r[k]); fall.append(fl[j] if j < len(fl) and fl[j] < r[k+1] else None)
        wr = {}                                             # cycle -> list of (A0, A13) of write cycles
        for k in edges(ro, False):
            if not rw[k] and k + 2 < len(d):
                c = bisect.bisect_right(r, k) - 1
                if 0 <= c < n: wr.setdefault(c, []).append((a0[k+2], a13[k+2]))
        m, sh = Rambo1(), Rambo1(); m.latch = sh.latch = 0
        pred, shadow_clock = [], []
        a12lv, meas = [], []
        for k in range(n):
            fk = fall[k]
            if fk is None: a12lv.append(None); meas.append(None); continue
            if any(a12[j] != a12[j-1] for j in range(fk - 1, fk + 2)): amb += 1
            a12lv.append(a12[min(fk + lag, len(d) - 1)]); meas.append(1 - irq[min(fk + 2, len(d) - 1)])   # 1 = /IRQ low (asserted)
        for k in range(n):
            if a12lv[k] is None: pred.append(None); shadow_clock.append(False); continue
            for a0v, a13v in wr.get(k, []):
                addr = (0xE000 if a13v else 0xC000) | a0v
                m.write(addr, 0); sh.write(addr, 0); sh.enabled = True
            m.cycle(a12lv[k]); sh.cycle(a12lv[k]); sh.enabled = True
            pred.append(1 if m.irq else 0); shadow_clock.append(sh._assert_in == 1)
        for k in range(300, n):
            if pred[k] is None or meas[k] is None: continue
            ncyc += 1
            if pred[k] != meas[k]: mism_cycles += 1
        # per iteration
        c001 = [k for k in sorted(wr) if (1, 0) in wr[k]]
        for w in c001:
            if w < 300 or w + 230 >= n: continue
            cs = [k for k in range(w, w + 200) if shadow_clock[k]]
            e = [k for k in range(w + 100, w + 200) if (sweep_a0, 1) in wr.get(k, [])]
            if not cs or not e: continue
            iters += 1
            dd = e[-1] - cs[0]
            def outcome(series):
                lows = [k for k in range(cs[0] - 1, w + 200) if series[k] == 1]
                if not lows: return "no assert"
                o = lows[0] - cs[0]
                rel = next((k for k in range(lows[0], w + 200) if series[k] == 0), None)
                return "assert c%+d" % o + (", released c%+d" % (rel - cs[0]) if rel is not None else "")
            table[dd][(outcome(pred), outcome(meas))] += 1
    print("cycles compared: %d, /IRQ mismatches (model vs chip): %d; A12 within 1 sample of an M2 fall (ambiguous level): %d; iterations analysed: %d" % (ncyc, mism_cycles, amb, iters))
    print("d = swept write cycle minus the clocking cycle c (0 = the write is in the same cycle as the clocking fall)")
    for dd in sorted(table):
        for (p, m_), c in sorted(table[dd].items(), key=lambda x: -x[1]):
            print("d=%+4d  %5d x  model: %-28s chip: %-28s %s" % (dd, c, p, m_, "" if p == m_ else "<-- DIFFERENT"))
main()
