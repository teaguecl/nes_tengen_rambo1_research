#!/usr/bin/env python3
"""Experiment E2a (docs/rp2350_adapter_plan.md): how long after /ROMSEL falls does a $E000 write release /IRQ, and does it depend on when the data byte arrives?
Each trial: $C001 (CPU mode), $E001, six idle cycles (the CPU-mode expiry at cycle 6 asserts /IRQ with latch 0), then a $E000 write whose data byte arrives
t_data ns after /ROMSEL falls (negative = before the window opens); the stale byte before it is `stale`. /IRQ release is measured against the /ROMSEL fall at 6.67 ns.
Console value to compare: 130 ns (F-067, data arrives about 100 ns into the window, stale byte $E0).
Usage: python3 -I firmware/rp2350_jig/tools/e2_release.py [--stale E0] [--values -200,-100,0,50,100,200,300]"""
import argparse, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H

def trial_block(w, t, t_data, stale):
    t = H.write_cycle(w, t, 0xC001, 0x01, stale=0xE0, t_data=100.0, tail=False)       # C001: CPU mode (data bit 0 = 1); the next store follows at once
    t = H.write_cycle(w, t, 0xE001, 0x00, stale=0xE0, t_data=100.0)       # E001: enable
    t = H.idle_cycles(w, t, 6)                                              # expiry at cycle 6 after the C001: /IRQ asserts
    t_e000 = t
    t = H.write_cycle(w, t, 0xE000, 0x00, stale=stale, t_data=t_data)     # the test write
    t = H.idle_cycles(w, t, 2)
    return t, t_e000

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--stale', default='E0'); ap.add_argument('--values', default='-200,-100,0,50,100,150,200,300')
    ap.add_argument('--repeat', type=int, default=3); a = ap.parse_args()
    values = [float(v) for v in a.values.split(',')]; stale = int(a.stale, 16)
    j = H.Jig()
    print(j.cmd("cold 500", 1, 6.0)[0]); j.cmd("oe on")
    j.cmd("wr c000 00")                                                    # latch 0
    j.cmd("idle")
    order = []
    for r in range(a.repeat): order += values
    w = H.Wave(); t = 300.0; marks = []
    for tv in order:
        t, te = trial_block(w, t, tv, stale); marks.append((tv, te))
    words = w.render(t + 200)
    print("%d trials, %d words" % (len(order), len(words)))
    if len(words) > 48 * 1024: sys.exit("too many words")
    j.load(words); res = j.run(len(words) + 200, 1.0); print(res)
    cap = j.dump()
    irq = H.bits(cap, H.OUT_BIT["IRQ"]); rom = H.bits(cap, H.STIM_CAPBIT["ROMSEL"]); rw = H.bits(cap, H.STIM_CAPBIT["RW"]); m2 = H.bits(cap, H.STIM_CAPBIT["M2"])
    irq_rise = [i for i in H.edges(irq) if irq[i]]
    write_falls = [i for i in H.edges(rom) if not rom[i] and not rw[i]]          # /ROMSEL falls in write cycles (R/W low)
    # the E000 test write is the 3rd write of each trial block: C001, E001, E000
    tests = write_falls[2::3]
    out = {}
    for k, (tv, _) in enumerate(marks):
        if k >= len(tests): break
        rf = tests[k]; rr = [i for i in irq_rise if rf <= i < rf + 200]
        out.setdefault(tv, []).append(round((rr[0] - rf) * H.PIO_NS, 1) if rr else None)
    print("data arrives t_data ns after /ROMSEL falls (stale byte $%02X): /IRQ release delay after the /ROMSEL fall, ns (adapter buffers included, about 16 ns):" % stale)
    for tv in values:
        v = out.get(tv, [])
        good = [x for x in v if x is not None]
        print("  t_data %6.0f ns : %s   mean %s" % (tv, v, ("%.1f" % statistics.mean(good)) if good else "no release"))
    j.cmd("idle")
if __name__ == '__main__': main()
