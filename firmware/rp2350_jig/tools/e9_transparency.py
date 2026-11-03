#!/usr/bin/env python3
"""Experiment E9: write-window transparency and latch instant of every bank register and $A000 (extends E2 / F-082).
Per register, three trials (old value is 00; X, Y alternate bits; mirror: old = X = 1, Y = 0):
  T : data X -> Y 150 ns after the /ROMSEL fall, long before the M2 fall; the output is sampled 250 ns after the M2 rise (still inside the window), then after the cycle.
      live = Y means the register is transparent (the output follows the data bus while the window is open); live = X means it is not.
  E : data X -> Y 10 ns BEFORE the M2 fall   -> stored Y if the data is latched at the fall (setup < 10 ns).
  L : data X -> Y 10 ns AFTER  the M2 fall   -> stored X if the data is latched at the fall (hold < 10 ns).
Registers: R0-R5, R8, R9 (CHR, read live on CHR A10/A11/A15-A17 through the PPU address, 1 KB mode), R6 and RF (PRG, read live: CPU A13 = A14 = 0 during the
write is window 0 = R6 with P = 0, RF with P = 1), R7 (PRG, stored value only: the write address already selects window 0), $A000 (CIRAM).
Usage: python3 -I e9_transparency.py [--regs R0,R6,...] [--repeat n]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H

# name: (index, ctrl byte, kind, ppu bits (A12, A11, A10) or None)
W = {'R0': 0, 'R8': 1, 'R1': 2, 'R9': 3, 'R2': 4, 'R3': 5, 'R4': 6, 'R5': 7}
REGS = {n: (i, 0x20 | i, 'chr', w) for n, w in W.items() for i in [{'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3, 'R4': 4, 'R5': 5, 'R8': 8, 'R9': 9}[n]]}
REGS['R6'] = (6, 0x06, 'prg', None)
REGS['R7'] = (7, 0x07, 'prgstore', None)
REGS['RF'] = (15, 0x4F, 'prg', None)
REGS['A000'] = (None, None, 'mirror', None)

def vals(kind):
    if kind == 'chr': return 0xA1, 0x42
    if kind == 'mirror': return 1, 0
    return 0x0A, 0x15

def decode(cap, i, kind):
    b = lambda n: (cap[i] >> H.OUT_BIT[n]) & 1
    if kind == 'chr': return b("CHRA10") | b("CHRA11") << 1 | b("CHRA15") << 5 | b("CHRA16") << 6 | b("CHRA17") << 7
    if kind == 'mirror': return b("CIRAM")
    return b("PRGA13") | b("PRGA14") << 1 | b("PRGA15") << 2 | b("PRGA16") << 3 | b("PRGA17") << 4

def trial(w, t, reg, mode, marks):
    idx, ctrl, kind, ppu = REGS[reg]
    X, Y = vals(kind)
    if ppu is not None: w.at(t, PPUA12=(ppu >> 2) & 1, PPUA11=(ppu >> 1) & 1, PPUA10=ppu & 1)
    if kind == 'mirror':
        w.at(t, PPUA12=0, PPUA11=1, PPUA10=0)
        addr, tt = 0xA000, t
        tt = H.write_cycle(w, tt, 0xA000, 1, tail=False)          # old = 1 = X
    else:
        addr = 0x8001
        tt = H.write_cycle(w, t, 0x8000, ctrl, tail=False)
        tt = H.write_cycle(w, tt, 0x8001, 0x00, tail=False)
    t0 = tt
    a = {"A0": addr & 1, "A13": (addr >> 13) & 1, "A14": (addr >> 14) & 1}
    w.at(t0 - 125, RW=0, M2=0, ROMSEL=1, **a, **H.data_bits(X))
    w.at(t0, M2=1); w.at(t0 + 28, ROMSEL=0)
    tchg = {'T': 28 + 150.0, 'E': 363.0 - 10, 'L': 363.0 + 10}[mode]
    w.at(t0 + tchg, **H.data_bits(Y))
    w.at(t0 + 363, M2=0); w.at(t0 + 376, ROMSEL=1); w.at(t0 + 446, RW=1)
    t = t0 + 559.0
    if kind == 'prgstore': w.at(t + 20, A13=1, A14=0)          # window 1 = R7
    elif kind == 'prg': w.at(t + 20, A13=0, A14=0)
    else: w.at(t + 20, A13=0, A14=0)
    marks.append((t0, t))
    w.at(t + 400, A13=1, A14=1)
    return t + 559.0

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--regs'); ap.add_argument('--repeat', type=int, default=3); a = ap.parse_args()
    names = a.regs.split(',') if a.regs else list(REGS)
    j = H.Jig()
    print(j.cmd("cold 500", 1, 6.0)[0]); j.cmd("oe on"); j.cmd("idle")
    order = [(r, m) for rep in range(a.repeat) for r in names for m in 'TEL']
    res = {}; per_run = 40
    for k in range(0, len(order), per_run):
        chunk = order[k:k + per_run]; w = H.Wave(); t = 300.0; marks = []
        for r, m in chunk: t = trial(w, t, r, m, marks)
        words = w.render(t + 200)
        if len(words) > 48 * 1024: sys.exit("too many words")
        j.load(words); j.run(len(words) + 200, 1.0); cap = j.dump()
        for (r, m), (t0, ts) in zip(chunk, marks):
            idx = lambda tt: 24 + int(round(tt / H.PIO_NS)) + 2
            kind = REGS[r][2]
            res.setdefault((r, m), []).append((decode(cap, idx(t0 + 250), kind), decode(cap, idx(ts + 300), kind)))
        j.cmd("idle")
    print("old=00 (mirror: old=1)  X/Y per register; each cell: live[stored]")
    for r in names:
        X, Y = vals(REGS[r][2]); nm = {X: 'X', Y: 'Y'}
        f = lambda s: nm.get(s, '%02X' % s)
        line = []
        for m in 'TEL':
            line.append("%s: %s" % (m, " ".join("%s[%s]" % (f(l), f(s)) for l, s in res[(r, m)])))
        print("  %-5s %s" % (r, "   ".join(line)))
    j.cmd("oe off"); j.cmd("power off")
if __name__ == '__main__': main()
