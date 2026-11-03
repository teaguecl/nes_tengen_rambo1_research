#!/usr/bin/env python3
"""Experiment E2 (docs/rp2350_adapter_plan.md): the register write window. Register under test: R6 through $8001 (R6 is read back combinationally on PRG A13..A17
with CPU A13 = A14 = 0). Each trial: $8000 <- 06, $8001 <- 00, then the TEST WRITE to $8001, then a read of PRG A13..A17. Stored value: 00 = the write was not
latched at all, X = 0A, Y = 15 (alternate bits, so a partly latched byte shows).
  --scan data      : data goes X -> Y at t ns relative to the M2 fall (console edges: M2 falls at 363, /ROMSEL rises at +13, R/W at +83)
  --scan close     : which edge closes the window: one of M2 / ROMSEL / R/W moves 100 ns early, the other two stay late, data X -> Y 50 ns after the early edge
                     (values: M2, ROMSEL, RW, none); stored X = the early edge closed the window, Y = it did not
  --scan width_m2  : /ROMSEL low from before; the window is cut by the M2 fall w ns after the M2 rise (data Y valid throughout)
  --scan width_rom : M2 high; /ROMSEL low for w ns, M2 falls late
Times are at the adapter's GPIO side (74HCT541 skew of a few ns between the lines is not calibrated). Usage: python3 -I e2_window.py --scan ... [--values a,b] [--repeat n]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H
X, Y = 0x0A, 0x15
REG = 'prg'     # --reg chr: the register under test is R0 read on CHR A10/A11/A15-A17 (PPU A10-A12 low); X = A1, Y = 42
IDX = 0x06

def test_write(w, t0, m2_fall=363.0, rom_fall=28.0, rom_rise=376.0, rw_rise=446.0, m2_rise=0.0, d0=None, d1=None, t_chg=None):
    d0 = X if d0 is None else d0
    w.at(t0 - 125, RW=0, M2=0, ROMSEL=1, A0=1, A13=0, A14=0, **H.data_bits(d0))
    w.at(t0 + m2_rise, M2=1); w.at(t0 + rom_fall, ROMSEL=0)
    if t_chg is not None: w.at(t0 + t_chg, **H.data_bits(d1))
    w.at(t0 + m2_fall, M2=0); w.at(t0 + rom_rise, ROMSEL=1); w.at(t0 + rw_rise, RW=1)
    return t0 + 559.0

def trial(w, t, scan, v, marks):
    t = H.write_cycle(w, t, 0x8000, IDX, tail=False)
    t = H.write_cycle(w, t, 0x8001, 0x00, tail=False)
    t0 = t
    if scan == 'data': t = test_write(w, t, d1=Y, t_chg=363.0 + v)
    elif scan == 'close':
        e = {'M2': dict(m2_fall=363.0, rom_rise=463.0, rw_rise=463.0), 'ROMSEL': dict(m2_fall=463.0, rom_rise=363.0, rw_rise=463.0),
             'RW': dict(m2_fall=463.0, rom_rise=463.0, rw_rise=363.0), 'none': dict(m2_fall=463.0, rom_rise=463.0, rw_rise=463.0)}[v]
        t = test_write(w, t, d1=Y, t_chg=413.0, **e)
    elif scan == 'width_m2': t = test_write(w, t, d0=Y, rom_fall=-50.0, m2_fall=v, rom_rise=v + 13.0, rw_rise=v + 83.0)
    elif scan == 'width_rom': t = test_write(w, t, d0=Y, rom_fall=28.0, rom_rise=28.0 + v, m2_fall=363.0, rw_rise=446.0)
    if REG == 'prg': w.at(t + 20, A13=0, A14=0)                 # read R6 on PRG A13..A17
    marks.append((t0, t + 300.0))
    if REG == 'prg': w.at(t + 400, A13=1, A14=1)
    return t + 559.0

def prg(cap, i):
    b = lambda n: (cap[i] >> H.OUT_BIT[n]) & 1
    if REG == 'chr': return b("CHRA10") | b("CHRA11") << 1 | b("CHRA15") << 5 | b("CHRA16") << 6 | b("CHRA17") << 7
    return b("PRGA13") | b("PRGA14") << 1 | b("PRGA15") << 2 | b("PRGA16") << 3 | b("PRGA17") << 4

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--scan', required=True, choices=['data', 'close', 'width_m2', 'width_rom'])
    ap.add_argument('--reg', default='prg', choices=['prg', 'chr']); ap.add_argument('--values'); ap.add_argument('--repeat', type=int, default=2); a = ap.parse_args()
    if a.values: values = a.values.split(',')
    elif a.scan == 'data': values = [str(v) for v in range(-80, 61, 10)]
    elif a.scan == 'close': values = ['M2', 'ROMSEL', 'RW', 'none']
    else: values = [str(v) for v in (3, 7, 10, 13, 17, 20, 27, 33, 40, 53, 67, 100)]
    global X, Y, REG, IDX
    REG = a.reg
    if REG == 'chr': X, Y, IDX = 0xA1, 0x42, 0x20
    conv = (lambda s: s) if a.scan == 'close' else float
    j = H.Jig()
    print(j.cmd("cold 500", 1, 6.0)[0]); j.cmd("oe on"); j.cmd("idle")
    order = [v for r in range(a.repeat) for v in values]; per_run = 40; res = {}
    for k in range(0, len(order), per_run):
        chunk = order[k:k + per_run]; w = H.Wave(); t = 300.0; marks = []
        if REG == 'chr': w.at(100.0, PPUA10=0, PPUA11=0, PPUA12=0)
        for v in chunk: t = trial(w, t, a.scan, conv(v), marks)
        words = w.render(t + 200)
        if len(words) > 48 * 1024: sys.exit("too many words")
        j.load(words); j.run(len(words) + 200, 1.0); cap = j.dump()
        for v, (t0, ts) in zip(chunk, marks):
            idx = lambda tt: 24 + int(round(tt / H.PIO_NS)) + 2
            res.setdefault(v, []).append((prg(cap, idx(t0 + 250)), prg(cap, idx(ts))))
        j.cmd("idle")
    print("scan %s: stored value after the write (live value late in the window in brackets); X=0A Y=15 old=00" % a.scan)
    name = {0: 'old', X: 'X', Y: 'Y'}
    for v in values:
        r = res[v]; print("  %6s : %s" % (v, "  ".join("%s[%02X]" % (name.get(s, '%02X' % s), l) for l, s in r)))
    j.cmd("oe off"); j.cmd("power off")
if __name__ == '__main__': main()
