#!/usr/bin/env python3
"""Experiment E6: do CPU READS of the register addresses ($8000..$E001, R/W high, M2 high, /ROMSEL low) change anything?
For each of the 8 addresses X the same run is made with the read cycles and without them (baseline); the results must be identical.
  A (state)    : registers set to distinct values; 6 read cycles of X; then a write of $5C to $8001; snapshots of the PRG (4 CPU A13/A14 combinations) and
                 CHR/CIRAM/IRQ outputs (8 PPU A10-A12 combinations) before the reads and after the write: any difference from the baseline run is a side effect.
  B (CPU mode) : latch 10, CPU mode, /IRQ expected 46 cycles after $C001; every cycle from 1 to 70 is a read of X; compares the assertion cycle and the /IRQ level.
  C (A12 mode) : latch 3, A12 mode, 6 pulses with 17 low cycles between, the low cycles are reads of X; compares the pulse that asserts /IRQ and its cycle.
Usage: python3 -I e6_reads.py [A|B|C|all] """
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H
ADDR = [0x8000, 0x8001, 0xA000, 0xA001, 0xC000, 0xC001, 0xE000, 0xE001]
P = 559.0
OUTMASK = sum(1 << b for b in H.OUT_BIT.values())

def read_cycle(w, t0, addr):
    a = {"A0": addr & 1, "A13": (addr >> 13) & 1, "A14": (addr >> 14) & 1}
    w.at(t0 - 125, RW=1, M2=0, ROMSEL=1, **a, **H.data_bits(0xFF))
    w.at(t0, M2=1); w.at(t0 + 28, ROMSEL=0); w.at(t0 + 363, M2=0); w.at(t0 + 376, ROMSEL=1)
    return t0 + P

def cycle(w, t, addr):
    return read_cycle(w, t, addr) if addr is not None else H.idle_cycles(w, t, 1)

def pulse(w, t0):
    w.at(t0 + 363 - 120, PPUA12=1); w.at(t0 + 363 + 100, PPUA12=0)

def setup(j):
    for idx, val in [(6, 0x15), (7, 0x0A), (0, 0xA1), (1, 0x42), (2, 0x84), (3, 0x18), (4, 0x24), (5, 0x48), (8, 0x11), (9, 0x22)]:
        j.cmd("wr 8000 %02x" % (0x20 | idx)); j.cmd("wr 8001 %02x" % val)
    j.cmd("wr a000 01"); j.cmd("wr e000 00"); j.cmd("idle")

def snapshots(w, t, marks):
    for a13, a14 in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        w.at(t, M2=0, RW=1, ROMSEL=1, A13=a13, A14=a14, PPUA10=0, PPUA11=0, PPUA12=0); marks.append(t + 250); t += 300
    for g in range(8):
        w.at(t, M2=0, RW=1, ROMSEL=1, A13=1, A14=1, PPUA10=g & 1, PPUA11=(g >> 1) & 1, PPUA12=(g >> 2) & 1); marks.append(t + 250); t += 300
    w.at(t, PPUA10=0, PPUA11=0, PPUA12=0)
    return t + 100

def sample(cap, t): return cap[24 + int(round(t / H.PIO_NS)) + 2] & OUTMASK

def run_wave(j, w, t): 
    words = w.render(t + 300); assert len(words) < 48 * 1024
    j.load(words); j.run(len(words) + 200, 1.0); cap = j.dump(); j.cmd("idle"); return cap

def exp_A(j, X):
    setup(j); w = H.Wave(); marks = []; t = 300.0
    w.at(100.0, PPUA12=0)
    t = snapshots(w, t, marks)
    for k in range(6): t = cycle(w, t, X)
    t = H.write_cycle(w, t, 0x8001, 0x5C, tail=False)
    t = snapshots(w, t, marks)
    cap = run_wave(j, w, t)
    return [sample(cap, m) for m in marks]

def irq_series(cap): return H.bits(cap, H.OUT_BIT["IRQ"])

def exp_B(j, X):
    setup(j); w = H.Wave(); t = 300.0
    t = H.write_cycle(w, t, 0xE000, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC000, 0x0A, tail=False)
    t = H.write_cycle(w, t, 0xE001, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC001, 0x01)
    t0 = t
    for k in range(70): t = cycle(w, t, X)
    cap = run_wave(j, w, t); irq = irq_series(cap)
    fall = [i for i in H.edges(irq) if not irq[i]]
    return [round(((i - 24 - 2) * H.PIO_NS - t0) / P, 2) for i in fall if (i - 26) * H.PIO_NS > t0 - 100], irq[-60]

def exp_C(j, X):
    setup(j); w = H.Wave(); t = 300.0
    w.at(100.0, PPUA12=0)
    t = H.write_cycle(w, t, 0xE000, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC000, 0x03, tail=False)
    t = H.write_cycle(w, t, 0xE001, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC001, 0x00)
    t0 = t; pulses = []
    pulse(w, t); t = H.idle_cycles(w, t, 1)               # swallowed
    for p in range(6):
        for k in range(17): t = cycle(w, t, X)
        pulse(w, t); pulses.append(t); t = H.idle_cycles(w, t, 1)
    for k in range(5): t = cycle(w, t, X)
    cap = run_wave(j, w, t); irq = irq_series(cap)
    fall = [i for i in H.edges(irq) if not irq[i]]
    out = []
    for i in fall:
        tt = (i - 26) * H.PIO_NS
        if tt > t0: out.append("%.2f cycles after the pulse #%d" % ((tt - max(p for p in pulses if p <= tt)) / P, 1 + max(k for k, p in enumerate(pulses) if p <= tt)))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('which', nargs='?', default='all'); a = ap.parse_args()
    j = H.Jig(); print(j.cmd("cold 500", 1, 6.0)[0]); j.cmd("oe on"); j.cmd("idle")
    for name, fn in (("A", exp_A), ("B", exp_B), ("C", exp_C)):
        if a.which not in (name, 'all'): continue
        base = fn(j, None); print("part %s baseline: %s" % (name, base if name != 'A' else "%d samples" % len(base)))
        for X in ADDR:
            r = fn(j, X)
            if name == 'A': d = [i for i, (x, y) in enumerate(zip(r, base)) if x != y]; print("  read $%04X : %s" % (X, "identical to the baseline" if not d else "DIFFERS at snapshots %s" % d))
            else: print("  read $%04X : %s" % (X, "identical to the baseline" if r == base else "DIFFERS: %s" % (r,)))
    j.cmd("oe off"); j.cmd("power off")
if __name__ == '__main__': main()
