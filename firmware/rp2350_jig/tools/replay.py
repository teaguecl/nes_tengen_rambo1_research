#!/usr/bin/env python3
"""Replay a logic-analyser capture of the console's bus into the chip on the RP2350 adapter and compare the chip's /IRQ with the capture's /IRQ
(the plan's acceptance test, docs/rp2350_adapter_plan.md section 7). For the A12-mode captures of the timing probe (phases 9/10, 18/19):
channels CH1 M2, CH2 R/W, CH3 /ROMSEL, CH4 A0, CH5 A13, CH6 /IRQ, CH7 PPU A12 (24 MHz, 41.67 ns per sample). Data lines are not in the capture:
D0..D7 are driven 0 (a $C001 with data 0 selects A12 mode; the data of $E000/$E001 is ignored); A14 is held high (all accesses are to $E000 and above);
PPU A10 and A11 stay high.
Usage: python3 -I firmware/rp2350_jig/tools/replay.py CAPTURE.sr [--cycles N] [--start-after K] [--cold]"""
import argparse, os, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H

PIO_PER_SAMPLE = 150e6 / 24e6          # 6.25 PIO cycles per 24 MHz sample

def load_sr(path):
    z = zipfile.ZipFile(path)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def sample_word(b):
    """The stimulus word for one capture sample (channel bits: 0 M2, 1 R/W, 2 /ROMSEL, 3 A0, 4 A13, 5 /IRQ, 6 PPU A12)."""
    w = H.IDLE & ~0xFF                                # D0..D7 = 0
    for ch, name in ((0, "M2"), (1, "RW"), (2, "ROMSEL"), (3, "A0"), (4, "A13"), (6, "PPUA12")):
        if not (b >> ch) & 1: w &= ~(1 << H.S[name])
    return w

def find_start(d, after):
    """The first E000 write cycle ($E000: A0 = 0, A13 = 1, R/W low with /ROMSEL low) after sample `after`; the segment starts 8 M2 cycles earlier."""
    for k in range(max(after, 200), len(d) - 1):
        b, pb = d[k], d[k - 1]
        if ((pb >> 2) & 1) and not ((b >> 2) & 1) and not ((b >> 1) & 1) and not ((b >> 3) & 1) and ((b >> 4) & 1):
            return max(0, k - int(8 * 13.4))
    raise SystemExit("no $E000 write found")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('capture'); ap.add_argument('--cycles', type=int, default=500); ap.add_argument('--start-after', type=int, default=1000)
    ap.add_argument('--cold', action='store_true', help="cold start the cart first (power off with discharge, 10 s off) and set latch 0"); a = ap.parse_args()
    d = load_sr(a.capture)
    k0 = find_start(d, a.start_after); nsamp = int(a.cycles * 13.4)
    seg = d[k0:k0 + nsamp]
    ncyc = int(len(seg) * PIO_PER_SAMPLE)
    words = [H.IDLE] * 24
    for c in range(ncyc): words.append(sample_word(seg[min(int(c / PIO_PER_SAMPLE), len(seg) - 1)]))
    words += [H.IDLE] * 24
    if len(words) > 48 * 1024: sys.exit("segment too long: %d words (max 49152)" % len(words))
    orig_irq = [(b >> 5) & 1 for b in seg]; orig_m2 = [b & 1 for b in seg]
    j = H.Jig()
    if a.cold:
        print(j.cmd("cold 10000", 1, 20.0)[0]); j.cmd("oe on")           # 10 s off: /IRQ is asserted again only after about 6 s (F-079)
        print(j.cmd("wr c000 00")[0])                       # latch 0 (as the probe set it before its loop)
        j.cmd("idle")
    # make sure /IRQ is asserted at the start, as it was in the console at this point of the loop, whatever the power-on retention (F-079) did:
    # a CPU-mode expiry (latch 0, $C001 := 1, $E001, then idle write cycles) asserts it
    if a.cold:
        if orig_irq[0] == 0:                       # the capture starts with /IRQ asserted: assert it with a CPU-mode expiry
            j.cmd("wr c001 01"); j.cmd("wr e001 00")
            for _ in range(8): j.cmd("wr 8000 00")
        else:                                       # the capture starts with /IRQ released
            j.cmd("wr e000 00")
        j.cmd("idle"); print("/IRQ at the start of the capture: %d; before the replay: %s (0 = asserted)" % (orig_irq[0], j.cmd("out")[0].split("IRQ")[-1].strip()))
    print("replaying %d samples (%d M2 cycles) = %d PIO cycles" % (len(seg), a.cycles, ncyc))
    j.load(words)
    res = j.run(len(words) + 200, 1.0); print(res)
    cap = j.dump()
    irq = H.bits(cap, H.OUT_BIT["IRQ"]); m2 = H.bits(cap, H.STIM_CAPBIT["M2"])
    def first_m2_rise(series):
        for i in range(1, len(series)):
            if series[i] and not series[i - 1]: return i
    o0, r0 = first_m2_rise(orig_m2), first_m2_rise(m2[24 + 2:])
    r0 = (r0 or 0) + 24 + 2
    def ev(series, t0, unit_ns):
        return [(round((i - t0) * unit_ns, 1), series[i]) for i in H.edges(series)]
    e_orig = ev(orig_irq, o0, 1e9 / 24e6); e_rep = ev(irq, r0, 1e9 / 150e6)
    print("original /IRQ edges (ns after the first M2 rise): ", e_orig)
    print("replayed /IRQ edges (ns after the first M2 rise): ", e_rep)
    # delays at the adapter's resolution (6.67 ns per cycle): the /IRQ release against the /ROMSEL fall of the $E000 write, the assertion against the M2 fall
    romsel = H.bits(cap, H.STIM_CAPBIT["ROMSEL"]); rw = H.bits(cap, H.STIM_CAPBIT["RW"])
    m2f = [i for i in H.edges(m2) if not m2[i]]; rsf = [i for i in H.edges(romsel) if not romsel[i] and not rw[i]]
    rel = [(i, [x for x in rsf if x < i][-1:]) for i in H.edges(irq) if irq[i]]
    asr = [(i, [x for x in m2f if x <= i][-1:]) for i in H.edges(irq) if not irq[i]]
    print("replay /IRQ release minus the preceding write-cycle /ROMSEL fall (ns): ", [round((i - r[0]) * 6.667, 1) for i, r in rel if r])
    print("replay /IRQ assertion minus the preceding M2 fall (ns):                ", [round((i - r[0]) * 6.667, 1) for i, r in asr if r])
    # assertion (falling) edges: logic, compared within about one 24 MHz sample plus the buffers; release (rising) edges include the RC rise of the open-drain /IRQ
    # through its pull-up, which depends on the load (the analyser lead against the adapter): compared within 120 ns only
    ok = len(e_orig) == len(e_rep) and all(a_[1] == b_[1] and abs(a_[0] - b_[0]) <= (45 if a_[1] == 0 else 120) for a_, b_ in zip(e_orig, e_rep))
    print("RESULT:", "MATCH (same edges and directions; assertions within 45 ns, releases within 120 ns)" if ok else "DIFFERENT")
    j.cmd("idle")

if __name__ == '__main__': main()
