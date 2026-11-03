#!/usr/bin/env python3
"""Experiment E4 (docs/rp2350_adapter_plan.md): the A12 filter threshold at exact timing (F-022, F-051: 16 M2 falls with A12 low, then a high fall clocks).
Each trial, A12 mode, latch 0, enabled: $E000, $C001 (data 0), $E001, one swallowed pulse (A12 high across an M2 fall; $C001 makes the next high fall not clock), the
LOW PERIOD under test (A12 low at every M2 fall), then a test pulse (A12 high across an M2 fall). Counted = the counter reloaded from latch 0 and expired: /IRQ asserts.
  --mode scan   : n idle cycles with A12 low (n swept), M2 period --period ns (default 559 = 1.79 MHz)
  --mode gap    : 6 cycles, then M2 held low for G ns (A12 low, no M2 edges), then 6 cycles (total 12 < 16); counted would mean the filter also runs on time
  --mode glitch : 10 cycles, a 100 ns A12 high pulse that does not cover an M2 fall, then m more cycles (m swept; 10 + m >= 16 counts if the glitch is ignored)
Usage: python3 -I e4_filter.py --mode scan|gap|glitch [--values a,b,c] [--period 559] [--repeat 2]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H

def cyc(w, t, n, P):
    """n idle M2 cycles of period P (M2 high 65 %). Returns (end, [fall times])."""
    f = []
    for k in range(n):
        w.at(t + k * P, M2=1); w.at(t + k * P + 0.65 * P, M2=0); f.append(t + k * P + 0.65 * P)
    return t + n * P, f

def pulse(w, fall):
    w.at(fall - 120, PPUA12=1); w.at(fall + 100, PPUA12=0)

def trial(w, t, mode, v, P, marks):
    t = H.write_cycle(w, t, 0xE000, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC001, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xE001, 0x00)
    w.at(t, PPUA12=0)
    t, f = cyc(w, t, 1, P); pulse(w, f[0])                       # swallowed
    if mode == 'scan': t, _ = cyc(w, t, int(v), P)
    elif mode == 'gap':
        t, _ = cyc(w, t, 6, P); t += v; t, _ = cyc(w, t, 6, P)
    else:
        t, _ = cyc(w, t, 10, P); w.at(t - 0.35 * P + 20, PPUA12=1); w.at(t - 0.35 * P + 120, PPUA12=0)   # inside the M2-low phase after the 10th fall
        t, _ = cyc(w, t, int(v), P)
    t, f = cyc(w, t, 1, P); pulse(w, f[0]); marks.append(f[0])
    t, _ = cyc(w, t, 5, P)
    return t

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--mode', required=True, choices=['scan', 'gap', 'glitch']); ap.add_argument('--values')
    ap.add_argument('--period', type=float, default=559.0); ap.add_argument('--repeat', type=int, default=2); a = ap.parse_args()
    if a.values: values = [float(v) for v in a.values.split(',')]
    elif a.mode == 'scan': values = list(range(10, 21))
    elif a.mode == 'gap': values = [0, 1000, 5000, 20000, 50000]
    else: values = list(range(4, 10))
    j = H.Jig(); print(j.cmd("cold 500", 1, 6.0)[0]); j.cmd("oe on"); j.cmd("wr c000 00"); j.cmd("idle")
    order = [v for r in range(a.repeat) for v in values]; res = {}; k = 0
    while k < len(order):
        w = H.Wave(); t = 300.0; marks = []; chunk = []
        while k < len(order):
            tt = trial(H.Wave(), 0.0, a.mode, order[k], a.period, [])      # dry run for the length
            if t + tt > 300000.0 and chunk: break
            t = trial(w, t, a.mode, order[k], a.period, marks); chunk.append(order[k]); k += 1
        words = w.render(t + 200)
        if len(words) > 48 * 1024: sys.exit("too many words")
        j.load(words); j.run(len(words) + 200, 1.0); cap = j.dump()
        irq = H.bits(cap, H.OUT_BIT["IRQ"])
        for v, ft in zip(chunk, marks):
            i0 = 24 + int(round(ft / H.PIO_NS)) + 2
            before = irq[i0 - 15]; after = irq[i0:i0 + int(4 * a.period / H.PIO_NS)]
            res.setdefault(v, []).append(0 if all(after) else 1 if before else -1)
        j.cmd("idle")
    print("mode %s, M2 period %.0f ns: counted (1) / not (0) / -1 = /IRQ already low before the test pulse" % (a.mode, a.period))
    for v in values: r = res[v]; print("  %8.0f : %s   (%d of %d)" % (v, " ".join(str(c) for c in r), sum(1 for c in r if c == 1), len(r)))
    j.cmd("oe off"); j.cmd("power off")
if __name__ == '__main__': main()
