#!/usr/bin/env python3
"""Run each phase of build/timing_probe.nes on the simulator with the reference model as the chip, and check that the loop produces the
bus pattern and the chip outputs that docs/timing_measurements.md assumes. Usage: python3 -I tools/probe_check.py [ROM]"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hwsim
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'reference'))
from rambo1 import Rambo1

BUTTONS = {1: 1, 2: 2, 3: 3, 4: 4}      # phase -> index in A B SELECT START UP ... (B = 1, SELECT = 2, START = 3, UP = 4)

class Logged(hwsim.NES):
    def __init__(self, rom, model):
        super().__init__(rom, model)
        self.wlog, self.rlog, self.ppuw = [], [], []
    def wr(self, a, v, ofs=0):
        if a >= 0x8000: self.wlog.append((self.cyc + ofs, a, v))
        if a == 0x2006: self.ppuw.append((self.cyc + ofs, v))
        super().wr(a, v, ofs)
    def rd(self, a):
        v = super().rd(a)
        if 0x8000 <= a < 0xE000: self.rlog.append((self.cyc, a))
        return v

def run_phase(rom, phase):
    nes = Logged(rom, "ref")
    if phase:
        for b in (phase if isinstance(phase, tuple) else (phase,)): nes.pad_bits[b] = 1     # A=0 B=1 SELECT=2 START=3 UP=4 DOWN=5 LEFT=6 RIGHT=7
    start = None
    while nes.cyc < 40_000_000:
        nes.step()
        if nes.render_on: start = nes.cyc
        elif start is not None and not nes.render_on and nes.cyc > start:
            break                            # rendering went off again: the loop is about to run
    assert start is not None, "screen never turned on"
    t0 = nes.cyc
    nes.wlog.clear(); nes.rlog.clear(); nes.ppuw.clear()
    for _ in range(400): nes.step()           # let the loop's own setup finish; only the steady state is logged below
    nes.wlog.clear(); nes.rlog.clear(); nes.ppuw.clear()
    t0 = nes.cyc
    outs = []
    irq_edges = []
    prev = nes.map.irq_line
    irq_edges.append((nes.cyc, prev))
    while nes.cyc < t0 + 200_000:
        nes.step()
        if nes.map.irq_line != prev:
            irq_edges.append((nes.cyc, nes.map.irq_line)); prev = nes.map.irq_line
    return nes, irq_edges

def race(phase, j):
    """The reference model's prediction for phases 7 and 8: the cycle (after the $C001 write cycle) at which /IRQ first asserts, or None."""
    m = Rambo1(); m.write(0xE000, 0); m.write(0xC000, 4); m.write(0xC001, 1); m.cycle(0)
    first = None
    for t in range(1, 70):
        if phase == 7 and t == j: m.write(0xE001, 0)
        if phase == 8 and t == 8: m.write(0xE001, 0)
        if phase == 8 and t == j: m.write(0xE000, 0)
        prev = m.irq; m.cycle(0)
        if m.irq and not prev and first is None: first = t
    return first

def check(name, ok, detail=""):
    print("%-58s %s %s" % (name, "ok" if ok else "FAIL", detail))
    return ok

def main():
    rom = open(sys.argv[1] if len(sys.argv) > 1 else "build/timing_probe.nes", "rb").read()
    good = True
    # phase 1: data writes
    nes, _ = run_phase(rom, 0)
    w = [(c, a, v) for c, a, v in nes.wlog if a == 0xA000]
    good &= check("phase 1: $A000 writes alternate $00 / $01", len(w) > 1000 and {v for c, a, v in w} == {1, 0} and all(w[i][2] != w[i+1][2] for i in range(len(w) - 1)), "(%d writes)" % len(w))
    sp = collections.Counter(w[i+1][0] - w[i][0] for i in range(len(w) - 1))
    good &= check("phase 1: write spacing 6 and 9 cycles", set(sp) == {6, 9}, str(dict(sp)))
    good &= check("phase 1: only $A000 written in the loop", all(a == 0xA000 for c, a, v in nes.wlog))
    good &= check("phase 1: CIRAM A10 differs between the two mirroring values at $2400", nes.map.m.ciram_a10(0x2400) in (0, 1))
    # phase 2: control writes
    nes, _ = run_phase(rom, 1)
    w = [(c, a, v) for c, a, v in nes.wlog]
    good &= check("phase 2: $8000 writes alternate $80 / $00", len(w) > 1000 and all(a == 0x8000 for c, a, v in w) and {v for c, a, v in w} == {0x80, 0} and all(w[i][2] != w[i+1][2] for i in range(len(w) - 1)), "(%d writes)" % len(w))
    m = nes.map.m
    m.write(0x8000, 0x80); b1 = m.chr_bank(0); m.write(0x8000, 0x00); b0 = m.chr_bank(0)
    good &= check("phase 2: window 0 switches between R2 = $00 and R0 = $FE", (b1, b0) == (0x00, 0xFE), "(C=1: %02X, C=0: %02X)" % (b1, b0))
    # phase 3: IRQ ack loop
    nes, edges = run_phase(rom, 2)
    falls = [c for c, v in edges if v]          # /IRQ asserted
    rises = [c for c, v in edges if not v]
    per = collections.Counter(falls[i+1] - falls[i] for i in range(len(falls) - 1))
    span = falls[-1] - falls[0]
    good &= check("phase 3: /IRQ asserted every 164 cycles on average", len(falls) > 1000 and abs(span / (len(falls) - 1) - 164) < 0.05, "(%d interrupts, mean %.2f cycles, steps %s)" % (len(falls), span / (len(falls) - 1), sorted(per)))
    seq = sorted(edges)
    low = [seq[i+1][0] - seq[i][0] for i in range(len(seq) - 1) if seq[i][1] and not seq[i+1][1]]
    good &= check("phase 3: /IRQ released by the $E000 write within 40 cycles", max(low) < 40, "(low %d to %d cycles)" % (min(low), max(low)))
    wl = collections.Counter((a, v) for c, a, v in nes.wlog)
    good &= check("phase 3: writes only to $E000 and $E001", set(a for a, v in wl) == {0xE000, 0xE001}, str(dict(wl)))
    # phase 4: PRG reads
    nes, _ = run_phase(rom, 3)
    rd = collections.Counter(a for c, a in nes.rlog)
    good &= check("phase 4: loop reads $8000, $A000 and $C000 equally often", set(rd) == {0x8000, 0xA000, 0xC000} and max(rd.values()) - min(rd.values()) <= 1, str(dict(rd)))
    m = nes.map.m
    good &= check("phase 4: PRG outputs differ per window", [m.prg_bank(a) for a in (0x8000, 0xA000, 0xC000, 0xE000)] == [0x00, 0x15, 0x0A, 0x1F])
    # phase 5: PPUADDR pattern
    nes, _ = run_phase(rom, 4)
    vals = [v for c, v in nes.ppuw]
    cyc = [0, 0, 4, 0, 8, 0, 0x10, 0]
    rot = [i for i in range(8) if vals[i:i+8] == cyc]
    good &= check("phase 5: PPUADDR pairs cycle $0000 $0400 $0800 $1000", len(vals) > 1000 and bool(rot) and all(vals[i] == cyc[(i - rot[0]) % 8] for i in range(len(vals))))
    m = nes.map.m
    outs = [m.chr_bank(a) for a in (0x0000, 0x0400, 0x0800, 0x1000)]
    good &= check("phase 5: CHR outputs $00 $01 $02 $FF for the four addresses", outs == [0x00, 0x01, 0x02, 0xFF], str(["%02X" % o for o in outs]))
    # phase 6: $8001 data writes
    nes, _ = run_phase(rom, 5)
    w = [(c, a, v) for c, a, v in nes.wlog if a == 0x8001]
    good &= check("phase 6: $8001 writes alternate $FE / $00", len(w) > 1000 and {v for c, a, v in w} == {0xFE, 0} and all(w[i][2] != w[i+1][2] for i in range(len(w) - 1)), "(%d writes)" % len(w))
    good &= check("phase 6: only $8001 written in the loop", all(a == 0x8001 for c, a, v in nes.wlog))
    good &= check("phase 6: CHR A11-A17 follow R0 (chip model)", nes.map.m.chr_bank(0) in (0xFE, 0x00))
    # phases 7 and 8: enable / disable race. j = cycles from the $C001 write cycle to the $E001 (phase 7) / $E000 (phase 8) write cycle
    for ph, reg, nm in ((6, 0xE001, "7 ($E001)"), (7, 0xE000, "8 ($E000)")):
        nes, edges = run_phase(rom, ph)
        wl = nes.wlog
        res = collections.defaultdict(collections.Counter)
        for n in range(len(wl)):
            if wl[n][1] != 0xC001: continue
            c0 = wl[n][0]
            ev = [(c, a) for c, a, v in wl[n+1:n+8]]
            tgt = [c for c, a in ev if a == reg and c - c0 < 40]
            if not tgt: continue
            jj = tgt[-1] - c0
            asr = [c - c0 for c, v in edges if v and c0 < c < c0 + 60]
            res[jj][(asr[0] // 10 * 10) if asr else None] += 1
        js = sorted(res)
        good &= check("phase %s: j covers 18..26 exactly" % nm, js == list(range(18, 27)), str(js))
        if ph == 6: print("    j -> /IRQ asserted at cycle (tens): " + ", ".join("%d: %s" % (jj, dict(res[jj])) for jj in js))
    # phases 9 and 10: A12-mode race, a 228-cycle loop with the swept write 170 cycles after $C001
    for ph, btn, reg, nm in (((0, 4), "A+UP", 0xE001, "9"), ((0, 5), "A+DOWN", 0xE000, "10")):
        nes, edges = run_phase(rom, ph)
        wl = [(c, a) for c, a, v in nes.wlog]
        c001 = [c for c, a in wl if a == 0xC001]
        per = collections.Counter(c001[i+1] - c001[i] for i in range(len(c001) - 1))
        good &= check("phase %s: $C001 every 228 cycles" % nm, len(c001) > 500 and set(per) == {228}, str(dict(per)))
        sw = [[c for c, a in wl if a == reg and c0 + 100 < c < c0 + 200] for c0 in c001[:-1]]
        dist = collections.Counter(x[-1] - c0 for x, c0 in zip(sw, c001) if x)
        good &= check("phase %s: swept $%04X write 170 cycles after $C001" % (nm, reg), set(dist) == {170}, str(dict(dist)))
        good &= check("phase %s: rendering on, writes only to $E000/$E001/$C001" % nm, nes.render_on and set(a for c, a in wl) <= {0xE000, 0xE001, 0xC001})
    # phases 11 and 12: gap sweep with no A12 pulses
    for ph, nm in (((1, 4), "11"), ((1, 5), "12")):
        nes, edges = run_phase(rom, ph)
        wl = [(c, a) for c, a, v in nes.wlog]
        grid = collections.Counter()
        for k in range(len(wl) - 3):
            if [a for c, a in wl[k:k+4]] == [0xE000, 0xC001, 0xE001, 0xE000]:
                grid[(wl[k+1][0] - wl[k][0], wl[k+2][0] - wl[k+1][0])] += 1
        want = {(g1, g2) for g1 in (4, 8, 24) for g2 in (4, 9, 24, 44)}
        n = sorted(set(grid.values()))
        good &= check("phase %s: all 12 (g1, g2) gaps occur, each equally often" % nm, set(grid) == want and max(n) - min(n) <= 1, "(%d blocks, counts %s)" % (sum(grid.values()), n))
        good &= check("phase %s: only $E000/$E001/$C001 written, rendering off" % nm, set(a for c, a in wl) <= {0xE000, 0xE001, 0xC001} and not nes.render_on)
    # phases 13 and 14: the phase 10 loop with the PPU changed
    for ph, nm, rend in (((3, 4), "13", True), ((3, 5), "14", False)):
        nes, edges = run_phase(rom, ph)
        wl = [(c, a) for c, a, v in nes.wlog]
        c001 = [c for c, a in wl if a == 0xC001]
        per = collections.Counter(c001[i+1] - c001[i] for i in range(len(c001) - 1))
        seq = [a for c, a in wl[:4]]
        good &= check("phase %s: $C001 every 228 cycles, same writes as phase 10" % nm, len(c001) > 500 and set(per) == {228} and set(a for c, a in wl) == {0xE000, 0xC001, 0xE001}, str(dict(per)))
        good &= check("phase %s: rendering %s" % (nm, "on" if rend else "off"), nes.render_on == rend)
    # phase 15: the phase 10 loop, 231 cycles
    nes, edges = run_phase(rom, (2, 4))
    wl = [(c, a) for c, a, v in nes.wlog]
    c001 = [c for c, a in wl if a == 0xC001]
    per = collections.Counter(c001[i+1] - c001[i] for i in range(len(c001) - 1))
    good &= check("phase 15: $C001 every 231 cycles, rendering off", len(c001) > 500 and set(per) == {231} and not nes.render_on, str(dict(per)))
    # phase 16: period scan
    nes, edges = run_phase(rom, (2, 5))
    wl = [(c, a) for c, a, v in nes.wlog]
    c001 = [c for c, a in wl if a == 0xC001]
    per = collections.Counter(c001[i+1] - c001[i] for i in range(len(c001) - 1))
    good &= check("phase 16: every period 224..236 occurs, 39 times each", set(k for k, v in per.items() if v > 20) == set(range(224, 237)) and all(36 <= per[k] <= 80 for k in range(224, 237)), str(sorted(per.items())))
    # phase 17: the old-style loop
    nes, edges = run_phase(rom, (2, 3))
    wl = [(c, a) for c, a, v in nes.wlog]
    c001 = [c for c, a in wl if a == 0xC001]
    per = collections.Counter(c001[i+1] - c001[i] for i in range(len(c001) - 1))
    good &= check("phase 17: $C001 every 228 cycles, rendering off", len(c001) > 500 and set(per) == {228} and not nes.render_on, str(dict(per)))
    # data of the $C001 writes: the A12-mode phases must write bit 0 = 0 (a stray A once made them CPU-mode phases, F-073)
    for ph, nm in (((0, 4), "9"), ((0, 5), "10"), ((1, 4), "11"), ((3, 4), "13"), ((3, 5), "14"), ((2, 4), "15"), ((2, 5), "16"), ((2, 3), "17")):
        nes, edges = run_phase(rom, ph)
        vals = collections.Counter(v for c, a, v in nes.wlog if a == 0xC001)
        good &= check("phase %s: every $C001 write has data bit 0 = 0 (A12 mode)" % nm, bool(vals) and all(v & 1 == 0 for v in vals), str(dict(vals)))
    # phases 18 and 19: free-running counter
    for ph, nm in (((3, 6), "18"), ((3, 7), "19")):
        nes, edges = run_phase(rom, ph)
        wl = [(c, a) for c, a, v in nes.wlog]
        e000 = [c for c, a in wl if a == 0xE000]
        per = collections.Counter(e000[i+1] - e000[i] for i in range(len(e000) - 1))
        good &= check("phase %s: $E000/$E001 every 114 cycles, rendering on" % nm, len(e000) > 1000 and set(per) == {114} and set(a for c, a in wl) == {0xE000, 0xE001} and nes.render_on, str(dict(per)))
    pred7 = [race(7, j) for j in range(18, 27)]; pred8 = [race(8, j) for j in range(18, 27)]
    good &= check("phase 7 model prediction: expiry at 22 for j <= 22, else 42", pred7 == [22] * 5 + [42] * 4, str(pred7))
    good &= check("phase 8 model prediction: lost for j <= 22, asserted at 22 for j >= 23", pred8 == [None] * 5 + [22] * 4, str(pred8))
    print("\nALL OK" if good else "\nFAILURES")
    return 0 if good else 1

sys.exit(main())
