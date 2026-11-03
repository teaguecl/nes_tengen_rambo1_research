#!/usr/bin/env python3
"""Experiment E7: a $C001 write between the clocking fall of an A12 pulse and the /IRQ assertion that follows it (F-050, F-074). A12 mode, latch 0, enabled; the
clocking pulse falls in cycle K (A12 high at that M2 fall; latch 0 so the reload after $C001 expires: /IRQ asserts at the M2 fall of cycle K+1 or K+2, F-050);
$C001 is written in cycle K+j (j = -1..4; j = 0 is the clocking cycle itself). Data 00 (A12 mode again: reload) or 01 (CPU mode). Does /IRQ still assert,
and in which cycle? Usage: python3 -I e7_modeswitch.py [--repeat 3]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H
from e4_filter import pulse

P = 559.0
LATCH = 0
NOPULSE = False
INITCPU = False
LOWS = 17
def trial(w, t, j, data, marks):
    w.at(t - 200, PPUA12=0)                                  # A12 low at every M2 fall of the setup writes (the filter must fill)
    t = H.write_cycle(w, t, 0xE000, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC000, LATCH, tail=False)
    t = H.write_cycle(w, t, 0xE001, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC001, 0x01 if INITCPU else 0x00)
    w.at(t, PPUA12=0)
    pulse(w, t + 363.0); t = H.idle_cycles(w, t, 1)             # swallowed
    t = H.idle_cycles(w, t, LOWS)
    K = t                                                    # start of cycle K
    for m in range(0, 50):                   # cycles K .. K+7
        if j is not None and m == j: t = H.write_cycle(w, t, 0xC001, data)
        else: t = H.idle_cycles(w, t, 1)
        if m == 0 and not NOPULSE: pulse(w, K + 363.0)
    marks.append(K)
    return H.idle_cycles(w, t, 4)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--repeat', type=int, default=3); ap.add_argument('--latch', type=int, default=0); ap.add_argument('--js', default='None,0,1,2,3,4'); ap.add_argument('--nopulse', action='store_true'); ap.add_argument('--initcpu', action='store_true'); ap.add_argument('--lows', type=int, default=17); a = ap.parse_args()
    global LATCH, NOPULSE, INITCPU, LOWS; LOWS = a.lows; LATCH = a.latch; NOPULSE = a.nopulse; INITCPU = a.initcpu
    js = [None if v == 'None' else int(v) for v in a.js.split(',')]; res = {}
    jg = H.Jig(); print(jg.cmd("cold 500", 1, 6.0)[0]); jg.cmd("oe on"); jg.cmd("wr c000 %02x" % a.latch); jg.cmd("idle")
    cases = [(j, d) for j in js for d in ((0x00, 0x01) if j is not None else (0x00,))]
    order = [c for r in range(a.repeat) for c in cases]
    k = 0
    while k < len(order):
        w = H.Wave(); t = 300.0; marks = []; chunk = []
        while k < len(order) and len(chunk) < 3:
            t = trial(w, t, order[k][0], order[k][1], marks); chunk.append(order[k]); k += 1
        words = w.render(t + 200); jg.load(words); jg.run(len(words) + 200, 1.0); cap = jg.dump(); jg.cmd("idle")
        irq = H.bits(cap, H.OUT_BIT["IRQ"])
        for c, K in zip(chunk, marks):
            i0 = 24 + int(round(K / H.PIO_NS)) + 2
            fall = [i for i in range(i0 - 5, i0 + int(48 * P / H.PIO_NS)) if not irq[i] and irq[i - 1]]
            res.setdefault(c, []).append(round(((fall[0] - i0) * H.PIO_NS - 363.0) / P, 2) if fall else None)
    print("cycle of the /IRQ fall relative to the clocking cycle K (K+1 means the M2 fall of the cycle after K); '-' = no /IRQ within 8 cycles")
    for j in js:
        for d in ((0x00, 0x01) if j is not None else (0x00,)):
            print("  $C001 in cycle K+%s data %02X : %s" % (j if j is not None else "-(none)", d, "  ".join(str(x) if x is not None else "-" for x in res[(j, d)])))
    jg.cmd("oe off"); jg.cmd("power off")
if __name__ == '__main__': main()
