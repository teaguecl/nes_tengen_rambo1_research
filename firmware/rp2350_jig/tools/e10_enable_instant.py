#!/usr/bin/env python3
"""Experiment E10: the sub-cycle instant at which the IRQ enable flag is tested (F-071, F-072, F-074 at cycle level). CPU-cycle mode, latch LAT; the first expiry
falls in cycle K (the M2 fall that ends cycle K; K = 4(LAT+1)+2 counted from the $C001 write cycle = cycle 0, found by the 'ref' trial).
  ref        : $E001 in cycle 3 (long before): /IRQ falls at the fall of cycle K (reference).
  none       : no $E001: no /IRQ.
  en_end d   : $E001 in cycle K, window closed by a /ROMSEL rise d ns BEFORE the M2 fall (window 20 ns wide: /ROMSEL falls at fall-d-20).
  dis_end d  : $E001 in cycle 3, then $E000 in cycle K, same closing d.
  en_late g  : $E001 in cycle K+1 with the M2 rise only g ns after the fall of K (normal: 196), /ROMSEL falls 15 ns after the rise, window to the fall of K+1.
  dis_late g : same with $E000 (enabled before).
Output: time of the /IRQ fall relative to the M2 fall of cycle K (ns), '-' = none within K-1..K+4.
Usage: python3 -I e10_enable_instant.py [--lat 2] [--repeat 2] [--ends 0,10,..] [--lates 196,150,..]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H
P = 559.0

def trial(w, t, case, d, LAT, K, marks):
    t = H.write_cycle(w, t, 0xE000, 0x00, tail=False)
    t = H.write_cycle(w, t, 0xC000, LAT, tail=False)
    Tc = t
    t = H.write_cycle(w, t, 0xC001, 0x01)          # cycle 0
    pre = case in ('ref', 'dis_end', 'dis_late')
    for k in range(1, K + 5):
        s = Tc + P * k
        if k == 3 and pre: H.write_cycle(w, s, 0xE001, 0x00); continue
        if case == 'en_end' and k == K or case == 'dis_end' and k == K:
            addr = 0xE001 if case == 'en_end' else 0xE000
            f = s + 363.0
            a = {"A0": addr & 1, "A13": (addr >> 13) & 1, "A14": (addr >> 14) & 1}
            w.at(s - 125, RW=0, M2=0, ROMSEL=1, **a, **H.data_bits(0xE0))
            w.at(s, M2=1); w.at(f - d - 20, ROMSEL=0); w.at(f - d, ROMSEL=1)
            w.at(f, M2=0); w.at(f + 83, RW=1); w.at(f + 170, A0=1, A13=1, A14=1, **H.data_bits(0xFF)); continue
        if case in ('en_late', 'dis_late') and k == K + 1:
            addr = 0xE001 if case == 'en_late' else 0xE000
            f0 = Tc + P * K + 363.0; f = f0 + P
            a = {"A0": addr & 1, "A13": (addr >> 13) & 1, "A14": (addr >> 14) & 1}
            w.at(f0 + 5, RW=0, **a, **H.data_bits(0xE0))
            w.at(f0 + d, M2=1); w.at(f0 + d + 3, ROMSEL=0)
            w.at(f, M2=0); w.at(f + 13, ROMSEL=1); w.at(f + 83, RW=1); w.at(f + 170, A0=1, A13=1, A14=1, **H.data_bits(0xFF)); continue
        H.idle_cycles(w, s, 1)
    marks.append(Tc + P * K + 363.0)
    return Tc + P * (K + 5)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--lat', type=int, default=2); ap.add_argument('--repeat', type=int, default=2)
    ap.add_argument('--ends', default='0,5,10,20,40,80,150'); ap.add_argument('--lates', default='196,170,140,110,80,50,25')
    a = ap.parse_args(); K = 4 * (a.lat + 1) + 2
    cases = [('ref', 0), ('none', 0)] + [('en_end', float(v)) for v in a.ends.split(',')] + [('dis_end', float(v)) for v in a.ends.split(',')] \
        + [('en_late', float(v)) for v in a.lates.split(',')] + [('dis_late', float(v)) for v in a.lates.split(',')]
    j = H.Jig(); print(j.cmd("cold 500", 1, 6.0)[0]); j.cmd("oe on"); j.cmd("idle")
    order = [c for r in range(a.repeat) for c in cases]; res = {}; k = 0
    while k < len(order):
        w = H.Wave(); t = 300.0; marks = []; chunk = []
        while k < len(order) and len(chunk) < 8:
            t = trial(w, t, order[k][0], order[k][1], a.lat, K, marks); chunk.append(order[k]); k += 1
        words = w.render(t + 200)
        if len(words) > 48 * 1024: sys.exit("too many words")
        j.load(words); j.run(len(words) + 200, 1.0); cap = j.dump(); j.cmd("idle")
        irq = H.bits(cap, H.OUT_BIT["IRQ"])
        for c, f in zip(chunk, marks):
            lo = 24 + int(round((f - P) / H.PIO_NS)) + 2; hi = 24 + int(round((f + 4 * P) / H.PIO_NS)) + 2
            fl = [i for i in range(lo, hi) if not irq[i] and irq[i - 1]]
            res.setdefault(c, []).append(round((fl[0] - 26) * H.PIO_NS - f) if fl else None)
    print("K = %d; /IRQ fall relative to the M2 fall of cycle K (ns)" % K)
    for c in cases: print("  %-9s %6.0f : %s" % (c[0], c[1], "  ".join(str(x) if x is not None else "-" for x in res[c])))
    j.cmd("oe off"); j.cmd("power off")
if __name__ == '__main__': main()
