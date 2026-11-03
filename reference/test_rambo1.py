#!/usr/bin/env python3
"""Checks of reference/rambo1.py against the measured behaviour (finding IDs in each test). Run: python3 -I test_rambo1.py"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rambo1 import Rambo1


class Bus:
    """Drives the model one M2 cycle at a time. A12 is held at self.a12 for every cycle()."""
    def __init__(self):
        self.m = Rambo1()
        self.a12 = 0

    def idle(self, n=1):
        for _ in range(n):
            self.m.cycle(self.a12)

    def wr(self, addr, val):
        self.m.write(addr, val)
        self.m.cycle(self.a12)              # the write cycle ends

    def reg(self, index, val):
        self.wr(0x8000, index)
        self.wr(0x8001, val)

    def pulse(self, high=2, low=20):
        """One A12 pulse followed by `low` cycles with A12 low; returns /IRQ after the pulse (high phase)."""
        self.a12 = 1
        self.idle(high)
        irq = self.m.irq
        self.a12 = 0
        self.idle(low)
        return irq

    def start(self, latch, mode, low=20):
        self.wr(0xE000, 0)
        self.wr(0xC000, latch)
        self.idle(low)
        self.wr(0xC001, mode)
        self.wr(0xE001, 0)


class PowerOn(unittest.TestCase):
    def test_state(self):                   # F-001 to F-004, F-034, F-035
        m = Rambo1()
        self.assertTrue(m.irq)
        self.assertEqual([m.prg_bank(a) for a in (0x8000, 0xA000, 0xC000, 0xE000)], [0x1F] * 4)
        self.assertEqual({m.chr_bank(a) for a in range(0, 0x2000, 0x400)}, {0})
        self.assertEqual(m.ciram_a10(0x0400), 1)             # vertical: follows PPU A10
        self.assertEqual(m.ciram_a10(0x0800), 0)
        self.assertEqual(m.latch, 0xFF)

    def test_e000_releases(self):           # F-020
        b = Bus(); b.wr(0xE000, 0)
        self.assertFalse(b.m.irq)


class Banking(unittest.TestCase):
    def test_chr_k0(self):                  # F-006, F-007: 2 KB layout, register bit 0 replaced by PPU A10
        b = Bus()
        for i, v in enumerate((0x11, 0x23, 0x30, 0x41, 0x52, 0x63)):
            b.wr(0x8000, i); b.wr(0x8001, v)
        b.wr(0x8000, 0x00)                                   # K = 0
        m = b.m
        self.assertEqual([m.chr_bank(a) for a in range(0, 0x1000, 0x400)], [0x10, 0x11, 0x22, 0x23])
        self.assertEqual([m.chr_bank(a) for a in range(0x1000, 0x2000, 0x400)], [0x30, 0x41, 0x52, 0x63])

    def test_chr_k1_and_inversion(self):    # F-006, F-049
        b = Bus()
        for i, v in zip((0, 1, 2, 3, 4, 5, 8, 9), (10, 11, 12, 13, 14, 15, 16, 17)):
            b.reg(i, v)
        b.wr(0x8000, 0x20)
        m = b.m
        self.assertEqual([m.chr_bank(a) for a in range(0, 0x2000, 0x400)], [10, 16, 11, 17, 12, 13, 14, 15])
        b.wr(0x8000, 0xA0)                                   # C
        self.assertEqual([m.chr_bank(a) for a in range(0, 0x2000, 0x400)], [12, 13, 14, 15, 10, 16, 11, 17])

    def test_r8_r9_keep_value(self):        # F-049
        b = Bus(); b.reg(8, 0x55); b.wr(0x8000, 0x20)
        self.assertEqual(b.m.chr_bank(0x0400), 0x55)

    def test_prg(self):                     # F-009, F-010
        b = Bus()
        b.reg(6, 0x23); b.reg(7, 0x45); b.reg(15, 0x07)
        m = b.m
        self.assertEqual([m.prg_bank(a) for a in (0x8000, 0xA000, 0xC000, 0xE000)], [3, 5, 7, 0x1F])
        b.wr(0x8000, 0x40 | 15)                              # P
        self.assertEqual([m.prg_bank(a) for a in (0x8000, 0xA000, 0xC000, 0xE000)], [7, 5, 3, 0x1F])

    def test_mode_by_8000_alone(self):      # F-040 (run 35): no $8001 needed
        b = Bus(); b.reg(2, 0x77); b.wr(0x8000, 0x00)
        self.assertEqual(b.m.chr_bank(0x1000), 0x77)
        b.wr(0x8000, 0x80)
        self.assertEqual(b.m.chr_bank(0x0000), 0x77)

    def test_unused(self):                  # F-039, F-040, F-041, F-042
        b = Bus(); b.reg(0, 0x30); b.reg(6, 5)
        snap = (dict(b.m.reg), b.m.mirror)
        for idx in (10, 11, 12, 13, 14):
            b.reg(idx, 0xFF)
        b.wr(0xA001, 0xFF)
        self.assertEqual((dict(b.m.reg), b.m.mirror), snap)
        b.wr(0xA000, 0xFE)
        self.assertEqual(b.m.mirror, 0)
        b.wr(0xA000, 0x03)
        self.assertEqual(b.m.mirror, 1)
        self.assertEqual(b.m.ciram_a10(0x0800), 1)           # horizontal: follows PPU A11

    def test_aliases(self):                 # F-063
        for k in range(1, 13):
            b = Bus()
            b.wr(0x8000 | (1 << k), 6); b.wr(0x8001 | (1 << k), 9)
            self.assertEqual(b.m.reg[6], 9, k)

    def test_pin19(self):                   # F-046
        b = Bus(); b.wr(0x8000, 6); b.m.pin19 = 1; b.wr(0x8001, 0x15)
        self.assertEqual(b.m.reg[6], 0x0B)


class CpuMode(unittest.TestCase):
    def first_expiry(self, latch):
        b = Bus()
        b.start(latch, 1, low=0)             # $C001 is written inside start(); recompute precisely below
        return b

    def t_to_irq(self, latch, setup_after=0):
        b = Bus()
        b.wr(0xE000, 0); b.wr(0xC000, latch); b.wr(0xE001, 0)
        b.m.write(0xC001, 1); b.m.cycle(0)                   # t = 0: end of the $C001 write cycle
        t = 0
        while not b.m.irq and t < 5000:
            b.idle(); t += 1
        return t

    def test_first_expiry(self):            # F-018, F-054: t = 4(L+1)+2
        for L in (0, 1, 2, 3, 4, 8, 16, 32, 64, 85, 128, 170, 255):
            self.assertEqual(self.t_to_irq(L), 4 * (L + 1) + 2, L)

    def test_period_and_ack(self):          # F-019, F-029
        b = Bus(); L = 4
        b.wr(0xE000, 0); b.wr(0xC000, L); b.wr(0xE001, 0)
        b.m.write(0xC001, 1); b.m.cycle(0)
        times = []
        t = 0
        while len(times) < 3:
            b.idle(); t += 1
            if b.m.irq:
                times.append(t)
                b.m.write(0xE000, 0); b.m.cycle(0); t += 1
                b.m.write(0xE001, 0); b.m.cycle(0); t += 1
        self.assertEqual(times[0], 22)
        self.assertEqual(times[1] - times[0] - 2 + 2, 20 + 0)   # ack and enable cost two cycles but the period is 20 cycles
        self.assertEqual(times[2] - times[1], 20)

    def test_expiry_while_disabled_is_lost(self):   # F-031
        b = Bus(); L = 4
        b.wr(0xE000, 0); b.wr(0xC000, L)
        b.m.write(0xC001, 1); b.m.cycle(0)                   # disabled
        b.idle(30)
        self.assertFalse(b.m.irq)
        b.wr(0xE001, 0)
        self.assertFalse(b.m.irq)
        t = 0
        while not b.m.irq:
            b.idle(); t += 1
        self.assertEqual(t + 31, 42)                      # next expiry at 22 + 20 after $C001

    def test_latch_window(self):            # F-028: $C000 up to 5 cycles after $C001 sets the first interval
        for k, first in ((1, 6), (5, 6), (6, 22)):
            b = Bus()
            b.wr(0xE000, 0); b.wr(0xC000, 4); b.wr(0xE001, 0)
            b.m.write(0xC001, 1); b.m.cycle(0)               # t = 0
            for _ in range(k - 1):
                b.idle()
            b.wr(0xC000, 0)                                   # k cycles after the $C001 write cycle
            t = k
            while not b.m.irq:
                b.idle(); t += 1
            self.assertEqual(t, first, k)

    def test_c001_restart_keeps_irq(self):  # F-024, F-025
        b = Bus(); L = 4
        b.wr(0xE000, 0); b.wr(0xC000, L); b.wr(0xE001, 0)
        b.m.write(0xC001, 1); b.m.cycle(0)
        b.idle(10)
        b.m.write(0xC001, 1); b.m.cycle(0)                   # restart
        t = 0
        while not b.m.irq:
            b.idle(); t += 1
        self.assertEqual(t, 22)
        b.m.write(0xC001, 1); b.m.cycle(0)
        self.assertTrue(b.m.irq)                              # not released

    def test_switch_to_a12_cancels(self):   # F-057
        for k in (11, 15, 21):
            b = Bus()
            b.wr(0xE000, 0); b.wr(0xC000, 4); b.wr(0xE001, 0)
            b.m.write(0xC001, 1); b.m.cycle(0)
            b.idle(k - 1)
            b.m.write(0xC001, 0); b.m.cycle(0)
            b.idle(50)
            self.assertFalse(b.m.irq, k)
        b = Bus()
        b.wr(0xE000, 0); b.wr(0xC000, 4); b.wr(0xE001, 0)
        b.m.write(0xC001, 1); b.m.cycle(0)
        b.idle(24)
        self.assertTrue(b.m.irq)
        b.m.write(0xC001, 0); b.m.cycle(0)
        self.assertTrue(b.m.irq)                              # stays low until $E000


class A12Mode(unittest.TestCase):
    def test_first_expiry_full_filter(self):    # F-021: pulse L+2
        for L in (0, 1, 2, 3, 4, 5, 8, 16):
            b = Bus(); b.start(L, 0)
            n = 0
            while True:
                n += 1
                if b.pulse() or n > 50:
                    break
            self.assertEqual(n, L + 2, L)

    def test_not_full_filter(self):         # F-052, F-055: pulse L+1 when fewer than 15 low falls precede $C001
        for L in (0, 1, 2):
            for low in (0, 6, 12):
                b = Bus()
                b.wr(0xE000, 0); b.wr(0xC000, L)
                b.a12 = 1; b.idle(2); b.a12 = 0; b.idle(low)
                b.m.write(0xC001, 0); b.m.cycle(0)
                b.wr(0xE001, 0)
                b.idle(30)
                n = 0
                while True:
                    n += 1
                    if b.pulse() or n > 50:
                        break
                self.assertEqual(n, L + 1, (L, low))

    def test_period(self):                  # F-037, F-056: L+1
        for L in (1, 2, 3, 4, 5, 8, 12, 16):
            b = Bus(); b.start(L, 0)
            hits = []
            n = 0
            while len(hits) < 3 and n < 200:
                n += 1
                if b.pulse():
                    hits.append(n)
                    b.wr(0xE000, 0); b.wr(0xE001, 0)
            self.assertEqual(hits, [L + 2, 2 * L + 3, 3 * L + 4], L)

    def test_filter_threshold(self):        # F-022, F-051: 16 M2 falls with A12 low count, 15 do not
        for low, counts in ((8, False), (14, False), (15, False), (16, True), (17, True), (40, True)):
            b = Bus(); b.start(1, 0)                          # L = 1: expiry on the second counted pulse
            b.pulse(low=20)                                   # pulse 1: swallowed ($C001 with a full filter)
            self.assertFalse(b.pulse(low=low))                # pulse 2: counted (first counted pulse)
            self.assertEqual(b.pulse(), counts, low)          # pulse 3 counts only if the gap before it was long enough

    def test_short_high_never_counts(self): # F-023: A12 high across no M2 fall
        b = Bus(); b.start(0, 0)
        b.pulse(); b.pulse()
        # a rise and fall between two M2 falls is not visible to cycle(): nothing to model; the filter keeps counting low
        b.idle(20)
        self.assertEqual(b.m.filt, 16)

    def test_latch_at_first_counted_pulse(self):    # F-038
        for after, expect in ((0, 3), (1, 3), (2, 6), (4, 6)):
            b = Bus(); b.start(4, 0)
            n = 0
            if after == 0:
                b.wr(0xC000, 1)
            while True:
                n += 1
                if b.pulse() or n > 50:
                    break
                if n == after:
                    b.wr(0xC000, 1)
            self.assertEqual(n, expect, after)

    def test_e000_e001_in_a12_mode(self):   # F-029 to F-031
        b = Bus(); b.start(1, 0)                              # expiries at pulses 3, 5, 7
        self.assertFalse(b.pulse()); self.assertFalse(b.pulse())
        b.wr(0xE000, 0)
        for _ in range(4):                                    # pulses 3 to 6: expiries at 3 and 5 are lost
            self.assertFalse(b.pulse())
        b.wr(0xE001, 0)
        self.assertFalse(b.m.irq)
        self.assertTrue(b.pulse())                            # pulse 7
        b.wr(0xE001, 0)
        self.assertTrue(b.m.irq)                              # $E001 does not release
        b.wr(0xE000, 0)
        self.assertFalse(b.m.irq)

    def test_a12_to_cpu_restarts(self):     # F-026
        b = Bus(); b.start(4, 0)
        b.pulse(); b.pulse()
        b.m.write(0xC001, 1); b.m.cycle(0)
        t = 0
        while not b.m.irq:
            b.idle(); t += 1
        self.assertEqual(t, 22)

    def test_frame_pulses(self):            # functional description 6.4: 241 counted pulses per frame
        L = 15
        b = Bus(); b.start(L, 0)
        count = 0
        for _ in range(8 * 241):
            if b.pulse(low=40):
                count += 1
                b.wr(0xE000, 0); b.wr(0xE001, 0)
        self.assertEqual(count, 120)


class A12EnableTiming(unittest.TestCase):
    """F-074 and F-075: the A12-mode enable flag is tested at the fall at which /IRQ falls (one fall after the clocking fall); latch 0 expires only on the reload after $C001."""

    def clock(self, enable_at=None, disable_at=None):
        """Latch 0, A12 mode, filter full, interrupt disabled; the first counted pulse is swallowed, the clocking fall of the second is cycle 0.
        $E001 is written in cycle `enable_at` and $E000 in cycle `disable_at` (relative to the clocking cycle). Returns the cycle at which /IRQ first fell, or None."""
        m = Rambo1(); m.latch = 0
        m.write(0xE000, 0); m.write(0xC001, 0)
        m.cycle(0)
        for _ in range(20): m.cycle(0)
        m.cycle(1)                          # the first counted pulse: swallowed
        for _ in range(20): m.cycle(0)
        first = None
        for c in range(0, 6):
            if c == enable_at: m.write(0xE001, 0)
            if c == disable_at: m.write(0xE000, 0)
            if c == 0: m.cycle(1)           # the clocking fall of the second counted pulse
            else: m.cycle(0)
            if m.irq and first is None: first = c
        return first

    def test_enable_before_and_in_the_clocking_cycle(self):
        self.assertEqual(self.clock(enable_at=0), 1)

    def test_enable_in_the_assertion_cycle_is_in_time(self):         # F-074
        self.assertEqual(self.clock(enable_at=1), 1)

    def test_enable_one_cycle_later_is_too_late(self):
        self.assertIsNone(self.clock(enable_at=2))

    def test_disable_in_the_assertion_cycle_prevents_it(self):       # F-074 (phase 10)
        self.assertIsNone(self.clock(enable_at=0, disable_at=1))

    def test_disable_after_the_assertion_releases_it(self):
        m = Rambo1(); m.latch = 0
        m.write(0xE000, 0); m.write(0xC001, 0); m.write(0xE001, 0)
        m.cycle(0)
        for _ in range(20): m.cycle(0)
        m.cycle(1)
        for _ in range(20): m.cycle(0)
        m.cycle(1); m.cycle(0)
        self.assertTrue(m.irq)
        m.write(0xE000, 0); m.cycle(0)
        self.assertFalse(m.irq)

    def test_latch_zero_does_not_expire_again(self):                 # F-075
        m = Rambo1(); m.latch = 0
        m.write(0xE000, 0); m.write(0xC001, 0); m.write(0xE001, 0)
        for _ in range(20): m.cycle(0)
        expiries = 0
        for p in range(6):                      # the pulses after $C001: swallowed, expires, then no more
            m.cycle(1); m.cycle(0)
            if m.irq: expiries += 1; m.write(0xE000, 0); m.cycle(0); m.write(0xE001, 0)
            for _ in range(20): m.cycle(0)
        self.assertEqual(expiries, 1)

    def test_latch_one_still_has_period_two(self):                   # F-059
        m = Rambo1(); m.latch = 1
        m.write(0xE000, 0); m.write(0xC001, 0); m.write(0xE001, 0)
        for _ in range(20): m.cycle(0)
        seen = []
        for p in range(1, 9):
            m.cycle(1); m.cycle(0)
            if m.irq:
                seen.append(p); m.write(0xE000, 0); m.cycle(0); m.write(0xE001, 0)
            for _ in range(20): m.cycle(0)
        self.assertEqual(seen, [3, 5, 7])


class C001FilterNotFull(unittest.TestCase):
    """F-087: a $C001 write switching from A12 mode to CPU mode while the A12 filter is not full."""

    def run_case(self, latch, j, data, n=40):
        """Latch `latch`, A12 mode, enabled, filter full; first counted pulse swallowed; the clocking fall is cycle 0; $C001 := data in cycle j. First /IRQ fall cycle or None."""
        m = Rambo1(); m.latch = latch
        m.write(0xE000, 0); m.write(0xE001, 0); m.write(0xC001, 0)
        m.cycle(0)
        for _ in range(20): m.cycle(0)
        m.cycle(1)                          # swallowed
        for _ in range(20): m.cycle(0)
        for c in range(n):
            if c == j: m.write(0xC001, data)
            m.cycle(1 if c == 0 else 0)
            if m.irq: return c
        return None

    def test_a12_mode_again_cancels_the_assertion(self):
        self.assertIsNone(self.run_case(0, 1, 0))

    def test_cpu_mode_with_a_full_filter_is_normal(self):             # F-087: the clocking cycle itself (filter full at the write) and 17 or more cycles later
        self.assertEqual(self.run_case(0, 0, 1), 6)
        self.assertEqual(self.run_case(2, 0, 1), 14)
        self.assertEqual(self.run_case(2, 17, 1), 31)
        self.assertEqual(self.run_case(2, 24, 1), 38)

    def test_cpu_mode_with_a_filter_not_full_expires_four_cycles_early(self):    # F-087: 4(L+1)-2 after the write, for j = 1..16
        self.assertEqual(self.run_case(0, 1, 1), 3)
        self.assertEqual(self.run_case(2, 1, 1), 11)
        self.assertEqual(self.run_case(5, 1, 1), 23)
        for j in (2, 5, 12, 16): self.assertEqual(self.run_case(2, j, 1), j + 10)

    def test_cpu_to_cpu_rewrite_is_not_early(self):                  # F-087: the early expiry needs a switch from A12 mode
        m = Rambo1(); m.latch = 2
        m.write(0xE000, 0); m.write(0xE001, 0); m.write(0xC001, 1)
        for _ in range(3): m.cycle(1)
        m.write(0xC001, 1)
        n = 0
        while not m.irq and n < 40: m.cycle(0); n += 1
        self.assertEqual(n, 15)                      # the write cycle's own fall is the first of 15 = 4(L+1)+2+1 counted here


class PowerOnCounter(unittest.TestCase):
    """F-088: the counter runs in CPU mode from power-on, latch FF, first expiry at M2 fall 1018 (the $E000 write cycle is fall 1)."""

    def test_first_expiry_without_c001(self):
        m = Rambo1()
        m.write(0xE000, 0); m.cycle(0)
        m.write(0xE001, 0); m.cycle(0)
        n = 2
        while not m.irq and n < 3000: m.cycle(0); n += 1
        self.assertEqual(n, 1018)

    def test_a12_pulses_do_nothing_before_c001(self):
        m = Rambo1(); m.write(0xE000, 0); m.write(0xE001, 0)
        for k in range(100):
            for _ in range(17): m.cycle(0)
            m.cycle(1)
            self.assertFalse(m.irq and k < 50)


if __name__ == "__main__":
    unittest.main(verbosity=1)
