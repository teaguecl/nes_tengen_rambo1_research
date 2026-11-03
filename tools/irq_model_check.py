#!/usr/bin/env python3
"""Replay recorded IRQ experiment logs through candidate counter models and count mismatches in /IRQ.

Events come from the 'command' column of results/*.csv: 'm N' (N idle M2 cycles), 'w ADDR DATA' (one M2 cycle
carrying a register write, applied before that cycle's M2 fall), 'a12 V' (A12 level). A12 and the prescaler are
processed on every M2 FALLING edge, as in the NESdev refined description. /IRQ is compared on every row that
carries outputs. Usage: tools/irq_model_check.py [VARIANT ...]   (default: all)
"""
import csv, glob, sys

class Model:
    def __init__(s, v, latch0=None):
        s.v = v; s.latch = 0 if latch0 is None else latch0; s.cnt = 0; s.enabled = False
        s.mode = 1; s.p = 0; s.c4 = 16;   # the chip sat idle with A12 low before every run, so the filter starts full
        s.a12 = 0; s.flag = False; s.irq = False; s.pend = None
    def write(s, addr, data):
        v = s.v
        if addr == 0xC000: s.latch = data
        elif addr == 0xC001:
            s.mode = data & 1; s.flag = True; s.p = v["p0"]
            ci = v["c4_init"]
            if ci == "full17": s.c4 = 17 if s.c4 >= 16 else s.c4      # measured: 17 only if the filter was already full
            else: s.c4 = ci
            if v["reload_at"] == "write": s.cnt = s.latch; s.flag = False   # NESdev refined: loaded NOW, no pending reload
        elif addr == 0xE000: s.enabled = False; s.irq = False; s.pend = None
        elif addr == 0xE001: s.enabled = True
    def clock8(s):
        v = s.v
        if v["rule"] == "now_zero":
            if s.flag:
                s.cnt = s.latch | (1 if (v["or1"] and s.latch) else 0); s.flag = False
            elif s.cnt == 0: s.cnt = s.latch
            else: s.cnt -= 1
            hit = (s.cnt == 0)
        else:   # refined: trigger when value is zero AT the clock, then reload
            if s.cnt == 0: hit = True; s.cnt = s.latch
            else: s.cnt -= 1; hit = False
            s.flag = False
        if hit and s.enabled:
            d = v["delay_cpu"] if s.mode == 1 else v["delay_a12"]
            if d == 0: s.irq = True
            else: s.pend = d
    def fall(s):
        if s.pend is not None:          # a delay scheduled earlier counts down BEFORE this fall's clock
            s.pend -= 1
            if s.pend <= 0: s.irq = True; s.pend = None
        # The A12 filter is assumed to track A12 in both modes (not observable in CPU mode); only A12 mode clocks from it.
        if s.a12 == 0:
            if s.c4 < 16: s.c4 += 1
        else:
            if s.c4 == 16 and s.mode == 0: s.clock8()
            s.c4 = 0
        if s.mode == 1:
            s.p += 1
            if s.p >= 4: s.p = 0; s.clock8()

BASE = dict(p0=0, c4_init="full17", reload_at="clock", rule="now_zero", or1=False, delay_cpu=1, delay_a12=1)
VARIANTS = {
    "ours":              dict(BASE, p0=-2),                       # first clock 5 cycles after $C001, IRQ 1 cycle later
    "ours+OR1":          dict(BASE, p0=-2, or1=True),
    "ours,17 always":    dict(BASE, p0=-2, c4_init=17),            # NESdev: always set to 17
    "ours,c4=0":         dict(BASE, p0=-2, c4_init=0),
    "ours,reload@write": dict(BASE, p0=-2, reload_at="write"),
    "ours,prescale=4":   dict(BASE, p0=-1),                       # NESdev: next clock 4 cycles later
    "wiki main":         dict(BASE, p0=-1, or1=True, delay_cpu=4, c4_init=17),
    "wiki refined":      dict(BASE, p0=-1, reload_at="write", rule="zero_at_clock", delay_cpu=1, c4_init=17),
}

def replay(path, v, latch0):
    rows = [r for r in csv.reader(l for l in open(path) if not l.startswith("#"))]
    h = rows[0]; irq = h.index("IRQ_N"); m = Model(v, latch0)
    n = bad = 0; seen_c001 = False
    for r in rows[1:]:
        c = r[2].split()
        if not c or r[4] == "mark": continue
        if c[0] == "m":
            for _ in range(int(c[1])): m.fall()
        elif c[0] == "w" and len(c) == 3:
            a = int(c[1], 16); m.write(a, int(c[2], 16)); seen_c001 |= (a == 0xC001); m.fall()
        elif c[0] == "a12": m.a12 = int(c[1])
        if r[irq] != "" and seen_c001 and c[0] in ("m", "w", "r", "a12"):
            n += 1; bad += (0 if m.irq else 1) != int(r[irq]) and 1 or 0
            bad -= 0
    return n, bad

def main():
    names = sys.argv[1:] or list(VARIANTS)
    sets = [("16 cpu L", "16"), ("19 a12 thresh", "19"), ("20 a12 count", "20"), ("21 cpu phase", "21"),
            ("22 c001 rewrite", "22"), ("23 latch change", "23"), ("24 mode switch", "24"), ("25 c001 bits", "25"),
            ("26 ack cpu", "26"), ("27 ack a12", "27"), ("31 a12 FF latch", "31"), ("32 a12 period", "32"), ("33 a12 latch load", "33"), ("56 c001 vs filter", "56")]
    logs = {}
    for lab, pre in sets:
        f = sorted(glob.glob(f"results/{pre}_*.csv"))
        # use the latest log for each, except 17/22/23 style superseded pairs (latest is the valid one)
        if f: logs[lab] = f[-1]
    print(f"{'experiment':20}" + "".join(f"{n:>20}" for n in names))
    tot = {n: [0, 0] for n in names}
    for lab, f in logs.items():
        cells = []
        for n in names:
            N, B = replay(f, VARIANTS[n], 255 if lab.startswith("31") else None)
            tot[n][0] += N; tot[n][1] += B; cells.append(f"{B}/{N}")
        print(f"{lab:20}" + "".join(f"{c:>20}" for c in cells))
    print(f"{'TOTAL mismatches':20}" + "".join(f"{t[1]}/{t[0]:>5}".rjust(20) for t in (tot[n] for n in names)))

if __name__ == "__main__":
    main()
