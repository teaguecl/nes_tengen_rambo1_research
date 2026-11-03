#!/usr/bin/env python3
"""Experiment E3 (docs/rp2350_adapter_plan.md): the A12 setup and hold against the M2 fall (F-074's open point: the console gave only "a rise up to 41 ns before the fall counts").
Each trial, A12 mode, latch 0, enabled: $E000, $C001 (data 0, reload), $E001, one swallowed pulse, 18 idle cycles with A12 low (filter full), then the TEST PULSE with
A12 high from `rise` to `fall` (ns relative to the M2 fall of one idle cycle), then idle cycles. If the pulse is counted the counter reloads from latch 0 and
expires: /IRQ asserts within 3 cycles. Result per trial: counted (1) or not (0).
  --scan setup : fall = +150 ns fixed, rise swept        --scan hold : rise = -250 ns fixed, fall swept
Times are at the adapter's GPIO side: the 74HCT541 delay (about 8 ns, U3 for M2 and U4 for A12) is in both lines and mostly cancels; skew of a few ns is not calibrated.
Usage: python3 -I e3_a12.py --scan setup|hold [--values a,b,c] [--repeat 2]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H

def trial(w, t, rise, fall, marks):
    t = H.write_cycle(w, t, 0xE000, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC001, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xE001, 0x00)
    w.at(t, PPUA12=0)
    fs = t + 363.0                                           # swallowed pulse (the filter is 17 after $C001)
    w.at(fs - 200, PPUA12=1); w.at(fs + 100, PPUA12=0)
    t = H.idle_cycles(w, t, 1 + 18)
    ft = t + 363.0
    w.at(ft + rise, PPUA12=1); w.at(ft + fall, PPUA12=0)
    marks.append(ft)
    t = H.idle_cycles(w, t, 6)
    return t

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--scan', required=True, choices=['setup', 'hold']); ap.add_argument('--values')
    ap.add_argument('--repeat', type=int, default=2); ap.add_argument('--fixed', type=float); a = ap.parse_args()
    if a.values: values = [float(v) for v in a.values.split(',')]
    elif a.scan == 'setup': values = list(range(-200, 61, 10))
    else: values = list(range(-120, 101, 10))
    j = H.Jig()
    print(j.cmd("cold 500", 1, 6.0)[0]); j.cmd("oe on")
    j.cmd("wr c000 00"); j.cmd("idle")
    order = [v for r in range(a.repeat) for v in values]
    per_run = 18; res = {}
    for k in range(0, len(order), per_run):
        chunk = order[k:k + per_run]; w = H.Wave(); t = 300.0; marks = []
        for v in chunk:
            rise, fall = (v, a.fixed if a.fixed is not None else 150.0) if a.scan == 'setup' else (a.fixed if a.fixed is not None else -250.0, v)
            t = trial(w, t, rise, fall, marks)
        words = w.render(t + 200)
        if len(words) > 48 * 1024: sys.exit("too many words")
        j.load(words); j.run(len(words) + 200, 1.0); cap = j.dump()
        irq = H.bits(cap, H.OUT_BIT["IRQ"])
        for v, ft in zip(chunk, marks):
            i0 = 24 + int(round(ft / H.PIO_NS)) + 2
            before = irq[i0 - 15]; after = [irq[i] for i in range(i0, i0 + int(4 * 559 / H.PIO_NS))]
            res.setdefault(v, []).append((before, 0 if all(after) else 1))
        j.cmd("idle")
    print("scan %s: A12 pulse %s; counted = /IRQ asserted within 4 cycles" % (a.scan, "rise swept (fall %+.0f)" % (a.fixed if a.fixed is not None else 150) if a.scan == 'setup' else "fall swept (rise %+.0f)" % (a.fixed if a.fixed is not None else -250)))
    bad = 0
    for v in values:
        r = res.get(v, []); bad += sum(1 for b, c in r if b == 0)
        print("  %+6.0f ns : %s   (%d of %d counted)" % (v, " ".join(str(c) for b, c in r), sum(c for b, c in r), len(r)))
    if bad: print("WARNING: /IRQ was not released before %d test pulses" % bad)
    j.cmd("oe off"); j.cmd("power off")
if __name__ == '__main__': main()
