#!/usr/bin/env python3
"""Experiment E4b: the A12 filter's value right after power-on. One real cold start per point (supply discharged, `cold 500`), then at once:
$E000 (releases the power-on /IRQ), $C000=00, $E001, $C001 (data 0: A12 mode, reload), n idle cycles with A12 low from the first cycle on, then a test pulse
(A12 high across an M2 fall). Counted = /IRQ asserts. If the filter starts at f0 (< 13) the pulse counts for n >= 12 - f0 (four write cycles are four low falls);
a filter that starts full (16) is made 17 by $C001 and swallows the pulse for every n. Usage: python3 -I e4b_poweron.py [--values 0,4,8,...] [--repeat 2] [--off 500]"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H
from e4_filter import cyc, pulse

def build(n, P=559.0, k=0):
    w = H.Wave(); t = 300.0
    w.at(100.0, PPUA12=0)
    if k: t, _ = cyc(w, t, k, P)                               # k idle cycles with A12 low before the first write
    t = H.write_cycle(w, t, 0xE000, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC000, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xE001, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC001, 0x00)
    t, _ = cyc(w, t, int(n), P)
    t, f = cyc(w, t, 1, P); pulse(w, f[0])
    ft = f[0]
    t, _ = cyc(w, t, 6, P)
    return w.render(t + 200), ft

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--values'); ap.add_argument('--repeat', type=int, default=2); ap.add_argument('--off', type=int, default=500); ap.add_argument('--lead', type=int, default=0); ap.add_argument('--wait', type=float, default=0.0); a = ap.parse_args()
    values = [int(v) for v in a.values.split(',')] if a.values else list(range(0, 17))
    j = H.Jig(); res = {}
    for r in range(a.repeat):
        for n in values:
            j.cmd("oe off"); print(j.cmd("cold %d" % a.off, 1, 20.0 + a.off / 1000.0)[0][:5], end=" ", flush=True)
            j.cmd("oe on"); j.cmd("idle"); time.sleep(a.wait)
            words, ft = build(n, k=a.lead)
            j.load(words); j.run(len(words) + 200, 1.0); cap = j.dump(); j.cmd("idle")
            irq = H.bits(cap, H.OUT_BIT["IRQ"]); i0 = 24 + int(round(ft / H.PIO_NS)) + 2
            before = irq[i0 - 15]; after = irq[i0:i0 + int(4 * 559 / H.PIO_NS)]
            res.setdefault(n, []).append(0 if all(after) else 1 if before else -1)
    print("\n[%d idle cycles before the first write] A12 filter after a cold start (off %d ms): n low cycles after $C001, then the pulse: counted 1 / not 0 / -1 = /IRQ not released before the pulse" % (a.lead, a.off))
    for n in values: r = res[n]; print("  n=%2d : %s" % (n, " ".join(str(c) for c in r)))
    j.cmd("oe off"); j.cmd("power off")
if __name__ == '__main__': main()
