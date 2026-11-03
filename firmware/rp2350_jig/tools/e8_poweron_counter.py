#!/usr/bin/env python3
"""Experiment E8: the IRQ counter right after a real cold start, with NO $C000 / $C001 write (latch and mode as the chip powers up; F-001, F-035: latch FF).
After the cold start only $E000 (releases the power-on /IRQ) and $E001 (enables) are written. Then, in chunks that keep the chip state between runs (the bus idles):
  --mode idle  : M2 cycles only, A12 low, up to --cycles (a CPU-cycle counter running from power-on would expire every 4 x 256 = 1024 cycles)
  --mode pulse : A12 pulses (17 low cycles between), up to --pulses; reports the number of the pulse after which /IRQ falls
Usage: python3 -I e8_poweron_counter.py --mode idle|pulse [--off 500] [--repeat 1] [--cycles 4000] [--pulses 300]"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H
from e4_filter import cyc, pulse

P = 559.0
def chunk_idle(first, ncyc):
    w = H.Wave(); t = 300.0; w.at(100.0, PPUA12=1 if A12HIGH else 0)
    if first:
        t = H.write_cycle(w, t, 0xE000, 0x00, tail=False)
        t = H.write_cycle(w, t, 0xE001, 0x00)
    t, _ = cyc(w, t, ncyc, P)
    return w, t, None

GAP = 17
A12HIGH = False
def chunk_pulse(first, npulse, lead=20):
    w = H.Wave(); t = 300.0; w.at(100.0, PPUA12=0); ps = []
    if first:
        t = H.write_cycle(w, t, 0xE000, 0x00, tail=False)
        t = H.write_cycle(w, t, 0xE001, 0x00)
    t, _ = cyc(w, t, lead, P)
    for k in range(npulse):
        t, f = cyc(w, t, 1, P); pulse(w, f[0]); ps.append(f[0])
        t, _ = cyc(w, t, GAP, P)
    return w, t, ps

def one_start(j, a):
    j.cmd("oe off"); j.cmd("cold %d" % a.off, 1, 20.0 + a.off / 1000.0); j.cmd("oe on"); j.cmd("idle")
    done = 0; first = True; result = None; falls = 0
    while result is None and done < (a.cycles if a.mode == 'idle' else a.pulses):
        if a.mode == 'idle': n = min(560, a.cycles - done); w, t, ps = chunk_idle(first, n)
        else: n = min(max(1, 540 // (GAP + 1)), a.pulses - done); w, t, ps = chunk_pulse(first, n)
        words = w.render(t + 200); assert len(words) < 48 * 1024
        j.load(words); j.run(len(words) + 200, 1.0); cap = j.dump(); j.cmd("idle")
        irq = H.bits(cap, H.OUT_BIT["IRQ"])
        start_low = irq[30] == 0
        fall = [i for i in H.edges(irq) if not irq[i]]
        if not first and start_low: result = ("low at the start of the chunk", done)
        elif fall:
            tt = (fall[0] - 26) * H.PIO_NS
            if a.mode == 'idle': result = ("/IRQ fell at M2 fall number %d since the first M2 fall (the $E000 write cycle is number 1)" % (falls + int((tt - 300.0) / P) + 1), done)
            else:
                k = max(i for i, p in enumerate(ps) if p <= tt + 1) if any(p <= tt + 1 for p in ps) else -1
                result = ("pulse %d of this chunk, %.2f cycles after it" % (k + 1, (tt - ps[k]) / P) if k >= 0 else "before the first pulse", done)
        falls += n + (2 if first else 0); done += n; first = False
    return result, done

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--mode', required=True, choices=['idle', 'pulse']); ap.add_argument('--off', type=int, default=500)
    ap.add_argument('--repeat', type=int, default=1); ap.add_argument('--cycles', type=int, default=4000); ap.add_argument('--pulses', type=int, default=300); ap.add_argument('--gap', type=int, default=17); ap.add_argument('--a12high', action='store_true'); a = ap.parse_args()
    global GAP, A12HIGH; GAP = a.gap; A12HIGH = a.a12high
    j = H.Jig()
    for r in range(a.repeat):
        res, done = one_start(j, a)
        print("start %d (off %d ms): %s " % (r + 1, a.off, res if res else "no /IRQ in %d %s" % (done, 'cycles' if a.mode == 'idle' else 'pulses')))
    j.cmd("idle"); j.cmd("oe off"); j.cmd("power off")
if __name__ == '__main__': main()
