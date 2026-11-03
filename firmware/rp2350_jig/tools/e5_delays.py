#!/usr/bin/env python3
"""Experiment E5 (docs/rp2350_adapter_plan.md): output delays of the combinational outputs, measured as the time from a stimulus edge (read back at the RP2350 pin, i.e. before
the 74HCT541) to the output edge (read at the RP2350 pin, i.e. after the 74LVC541A). The adapter's two buffers are therefore included (about 16 ns, F-080); resolution 6.67 ns.
  prg : CPU A13/A14 through a Gray code (00,01,11,10) with R6 = 15, R7 = 0A (window outputs 15, 0A, 1E, 1F) -> PRG A13..A17
  chr : PPU A12/A11/A10 through a Gray code, 1 KB banks alternating 00 / FF in every window -> CHR A10, A11, A15, A16, A17 and CIRAM A10 (CHR A12..A14 are outside the capture window)
  ce  : /CE against /ROMSEL, M2 and R/W (one line toggled at a time, the others at the stated level)
Usage: python3 -I e5_delays.py [prg|chr|ce|all] [--m2 0|1]"""
import argparse, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H

HOLD = 60      # words per state (400 ns)
def run_states(j, states, loops):
    words = [H.IDLE] * 40
    for _ in range(loops):
        for s in states: words += [s] * HOLD
    words += [H.IDLE] * 40
    j.load(words); j.run(len(words) + 100, 1.0); return j.dump()

def analyse(cap, line, outs, win=150.0):
    st = H.bits(cap, H.STIM_CAPBIT[line]); res = {}
    n = int(win / H.PIO_NS)
    for e in H.edges(st):
        di = 'rise' if st[e] else 'fall'
        for o in outs:
            ob = H.bits(cap, H.OUT_BIT[o])
            for k in range(e - 2, e + n):
                if k > 0 and ob[k] != ob[k - 1] and k >= e - 2:
                    res.setdefault((di, o, 'rise' if ob[k] else 'fall'), []).append((k - e) * H.PIO_NS); break
    return res

def show(title, line, res):
    print("%s: %s edge -> output edge, delay ns (min / mean / max, n)" % (title, line))
    for (di, o, do), v in sorted(res.items()):
        print("   %-4s -> %-7s %-4s : %5.1f / %5.1f / %5.1f  (n=%d)" % (di, o, do, min(v), statistics.mean(v), max(v), len(v)))

def setup(j):
    for idx, val in [(6, 0x15), (7, 0x0A), (0, 0x00), (8, 0xFF), (1, 0xFF), (9, 0x00), (2, 0xFF), (3, 0x00), (4, 0x00), (5, 0xFF)]:
        j.cmd("wr 8000 %02x" % (0x20 | idx)); j.cmd("wr 8001 %02x" % val)
    j.cmd("idle")

def gray(nbits, names, base):
    out = []; prev = None
    for g in [0, 1, 3, 2, 6, 7, 5, 4][:2 ** nbits]:
        kw = {nm: (g >> i) & 1 for i, nm in enumerate(names)}; out.append(H.word(**{**base, **kw}))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('which', nargs='?', default='all'); ap.add_argument('--m2', type=int, default=0); a = ap.parse_args()
    j = H.Jig(); print(j.cmd("cold 500", 1, 6.0)[0]); j.cmd("oe on"); j.cmd("idle"); setup(j)
    base = dict(M2=a.m2, RW=1, ROMSEL=1)
    if a.which in ('prg', 'all'):
        cap = run_states(j, gray(2, ["A13", "A14"], base), 6); outs = ["PRGA13", "PRGA14", "PRGA15", "PRGA16", "PRGA17"]
        for ln in ("A13", "A14"): show("PRG (M2=%d)" % a.m2, "CPU " + ln, analyse(cap, ln, outs))
    if a.which in ('chr', 'all'):
        cap = run_states(j, gray(3, ["PPUA10", "PPUA11", "PPUA12"], dict(M2=1, RW=1, ROMSEL=1)), 6); outs = ["CHRA10", "CHRA11", "CHRA15", "CHRA16", "CHRA17", "CIRAM"]
        for ln in ("PPUA10", "PPUA11", "PPUA12"): show("CHR/CIRAM", ln, analyse(cap, ln, outs))
    if a.which in ('ce', 'all'):
        for lv, tog in [(dict(M2=1, RW=1), "ROMSEL"), (dict(ROMSEL=0, RW=1), "M2"), (dict(M2=1, ROMSEL=0), "RW"), (dict(M2=0, RW=1), "ROMSEL"), (dict(M2=1, RW=0), "ROMSEL")]:
            states = [H.word(**{**lv, tog: 1}), H.word(**{**lv, tog: 0})]
            cap = run_states(j, states, 8); res = analyse(cap, tog, ["CE"])
            show("/CE with %s fixed" % lv, tog, res) if res else print("/CE with %s fixed: no /CE change when %s toggles" % (lv, tog))
    j.cmd("idle"); j.cmd("oe off"); j.cmd("power off")
if __name__ == '__main__': main()
