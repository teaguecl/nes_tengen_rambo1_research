#!/usr/bin/env python3
"""Analyse a timing-probe phase 18 or 19 capture (docs/logic_analyzer_guide.md section 10): A12 mode, latch 0 (phase 18) or 1 (phase 19), $C001 written once at start-up, then $E000 and $E001 every 114 cycles
with rendering on, so the counter runs free over hundreds of counted pulses. Channels: CH1 M2, CH2 R/W, CH3 /ROMSEL, CH4 A0, CH5 A13, CH6 /IRQ, CH7 PPU A12.
Reports the counted pulses (filter rule, A12 taken 1 sample after each M2 fall), how many of them were followed by a falling /IRQ, the gaps between those expiries in counted pulses, and a replay
of the captured bus through reference/rambo1.py (the model: latch 0 one expiry only; latch 1 every second pulse), counting /IRQ mismatches.
Usage: python3 -I tools/la_p18_analysis.py LATCH RATE_HZ FILE.sr [FILE.sr ...]"""
import sys, os, zipfile, collections, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reference'))
from rambo1 import Rambo1

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def edges(sig, rising=None):
    return [k for k in range(1, len(sig)) if sig[k] != sig[k-1] and (rising is None or bool(sig[k]) == rising)]

def main():
    latch = int(sys.argv[1]); rate = float(sys.argv[2]); T = 1e9 / rate
    tot_pulses = tot_exp = mism = ncyc = 0; gaps = collections.Counter(); per_capture = []
    for f in sys.argv[3:]:
        d = load(f)
        m2 = [b & 1 for b in d]; rw = [b >> 1 & 1 for b in d]; ro = [b >> 2 & 1 for b in d]; a0 = [b >> 3 & 1 for b in d]; a13 = [b >> 4 & 1 for b in d]; irq = [b >> 5 & 1 for b in d]; a12 = [b >> 6 & 1 for b in d]
        r, fl = edges(m2, True), edges(m2, False)
        per = [r[i+1] - r[i] for i in range(len(r) - 1)]
        if not per or abs(sum(per) / len(per) * T - 558.9) > 15 or max(per) > 1.3 * sum(per) / len(per): continue
        n = len(r) - 1
        fall = []
        for k in range(n):
            j = bisect.bisect_right(fl, r[k]); fall.append(fl[j] if j < len(fl) and fl[j] < r[k+1] else None)
        wr = {}
        for k in edges(ro, False):
            if not rw[k] and k + 2 < len(d):
                c = bisect.bisect_right(r, k) - 1
                if 0 <= c < n: wr.setdefault(c, []).append((a0[k+2], a13[k+2]))
        # the counter has been running free since start-up: replay from every possible starting state (counter value, reload flag) and keep the best
        filt = 16; counted = []; asserts = []; prev_low = None
        lows = {}
        for k in range(n):
            if fall[k] is None: continue
            lvl = a12[min(fall[k] + 1, len(d) - 1)]
            if lvl:
                if filt == 16: counted.append(k)
                filt = 0
            elif filt < 16: filt += 1
            low = 1 - irq[min(fall[k] + 2, len(d) - 1)]
            lows[k] = (lvl, low)
            if prev_low == 0 and low == 1: asserts.append(k)
            prev_low = low
        best = None
        for start in [(c, False) for c in range(latch + 1)] + [(0, True)]:
            m = Rambo1(); m.latch = latch; m.cpu_mode = False; m.enabled = True; m.reload = start[1]; m.counter = start[0]; m.filt = 16
            bad = cnt = 0
            for k in range(n):
                if k not in lows: continue
                for a0v, a13v in wr.get(k, []):
                    m.write((0xE000 if a13v else 0xC000) | a0v, 0)
                m.cycle(lows[k][0])
                if k > 400:
                    cnt += 1
                    if (1 if m.irq else 0) != lows[k][1]: bad += 1
            if best is None or bad < best[0]: best = (bad, cnt, start)
        cap_mism, cnt_c, _start = best
        ncyc += cnt_c
        mism += cap_mism
        idx = {c: i for i, c in enumerate(counted)}
        # expiry events: assertion cycle a follows the clocking fall at a-1 (A12 mode, F-050)
        exp_pulses = [idx[a - 1] for a in asserts if (a - 1) in idx]
        tot_pulses += len(counted); tot_exp += len(exp_pulses)
        for x, y in zip(exp_pulses, exp_pulses[1:]): gaps[y - x] += 1
        per_capture.append((len(counted), len(asserts), len(exp_pulses)))
    print("latch %d: counted pulses %d, /IRQ falling edges %d (each right after a counted pulse: %d)" % (latch, tot_pulses, sum(p[1] for p in per_capture), tot_exp))
    print("gaps between expiries in counted pulses: %s" % dict(sorted(gaps.items())))
    print("per capture (pulses, /IRQ falls, falls after a pulse): %s" % per_capture)
    print("model replay: /IRQ mismatches %d in %d cycles" % (mism, ncyc))
main()
