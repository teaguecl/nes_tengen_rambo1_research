#!/usr/bin/env python3
"""Reference model of the Tengen RAMBO-1 (337006, iNES mapper 64), reverse engineered from one chip.

Every rule below comes from docs/findings.md (finding IDs in the comments) and is described in docs/functional_description.md and
docs/functional_description.md. Nothing here is from a manufacturer. The model has no I/O: it is the chip's behaviour as a
state machine, meant to be read, ported to an emulator or an HDL, and used as a test oracle.

TIME. The model counts M2 cycles (CPU cycles). In every M2 cycle the caller does, in this order:
    1. any CPU writes that happen in this cycle          write(addr, value)
    2. the end of the cycle (the M2 falling edge)         cycle(a12)
where `a12` is the level of PPU A12 at that M2 falling edge. Reads need no call except the combinational outputs.
An emulator that models the PPU in dots should sample A12 at the middle of each CPU cycle, which is the M2 fall.
(Sub-cycle timing is not characterised: see docs/functional_description.md section 9 and F-081 to F-090.)

OUTPUTS. prg_bank(), chr_bank(), ciram_a10() and prg_ce() are combinational functions of the registers and the address
lines. `irq` is the state of /IRQ (True = asserted, pin low).
"""


class Rambo1:
    CHR_REGS = (0, 1, 2, 3, 4, 5, 8, 9)       # 8-bit registers
    PRG_REGS = (6, 7, 15)                      # 5-bit registers

    def __init__(self):
        self.power_on()

    # ------------------------------------------------------------------ power-on (F-001 to F-004, F-034 to F-036)
    def power_on(self):
        self.ctrl = 0x20                       # $8000 value seen by the outputs: K = 1 (1 KB CHR layout), P = 0, C = 0, index 0
        self.reg = {i: 0 for i in self.CHR_REGS}            # all CHR outputs bank 0
        self.reg.update({6: 0x1F, 7: 0x1F, 15: 0x1F})        # PRG windows all bank $1F
        self.mirror = 0                        # vertical
        self.latch = 0xFF                      # shared by both modes
        self.enabled = False
        self.irq = True                        # /IRQ asserted until the first $E000 (origin unknown, F-034)
        self.pin19 = 0                         # pin 19: when 1, every register write stores $0B (F-046)
        # IRQ counter
        self.cpu_mode = True                   # F-088: the chip powers up in CPU-cycle mode, latch FF, counter already running
        self.filt = 16                         # A12 filter. Real chip: NOT full at power-on, about 8 after a short power cycle, 2 to 5 after seconds (F-085); 16 here keeps the tests; matters only for the first 8 falls
        self.reload = True                     # next counted A12 clock reloads the counter
        self.counter = 0
        self._assert_in = 0                    # A12 mode: /IRQ asserts when this reaches 0 (one M2 fall after the clock, F-050)
        self._t = 8                            # CPU mode: cycles since the $C001 write cycle (None = timer off); at power-on the first expiry is at M2 fall 1018 (F-088)
        self._lat_c = 0xFF                     # latch value captured 5 cycles after $C001 (F-028)
        self._next = 4 * (0xFF + 1) + 2        # CPU mode: t of the next expiry

    # ------------------------------------------------------------------ CPU writes
    def write(self, addr, value):
        """A CPU write cycle at addr ($8000-$FFFF; /ROMSEL low). Decode uses A0, A13, A14 only (F-063: A1-A12 ignored)."""
        if self.pin19:
            value = 0x0B                       # F-046
        sel, odd = (addr >> 13) & 3, addr & 1
        if sel == 0:
            if not odd:
                self.ctrl = value              # K, P, C and the index take effect at once (F-040, run 35); bit 4 does nothing
            else:
                i = self.ctrl & 15
                if i in self.CHR_REGS:         # R0-R5, R8, R9: 8 bits; R8, R9 accept writes even when K = 0 (F-049)
                    self.reg[i] = value
                elif i in self.PRG_REGS:       # R6, R7, RF: low 5 bits (F-010)
                    self.reg[i] = value & 0x1F
                # indices 10-14 store nothing visible (F-039)
        elif sel == 1:
            if not odd:
                self.mirror = value & 1        # only bit 0 (F-041); $A001 does nothing visible (F-042, F-053)
        elif sel == 2:
            if not odd:
                self.latch = value
            else:
                self._write_c001(value)
        else:
            if not odd:                        # $E000: release /IRQ and disable; the counter is not disturbed (F-029)
                self.enabled = False
                self.irq = False
            else:                              # $E001: enable only; does not release /IRQ (F-030)
                self.enabled = True

    def _write_c001(self, value):
        """Bit 0 selects the clock (1 = CPU cycles, 0 = A12). Every write restarts the counter in the mode it selects and
        carries nothing over from the other mode (F-024, F-026, F-057). It never releases /IRQ (F-025)."""
        early = bool(value & 1) and not self.cpu_mode and self.filt < 16     # F-087: A12 mode -> CPU mode with the A12 filter not full
        self.cpu_mode = bool(value & 1)
        self._assert_in = 0
        if self.cpu_mode:
            self._early = early                # the first CPU-mode expiry then comes 4 cycles early
            self._t = -1                       # the cycle() that ends this write cycle makes t = 0
            self._lat_c = None
            self._next = None
        else:
            self._t = None                     # a pending CPU-mode expiry is cancelled (F-057)
            self.reload = True
            if self.filt == 16:
                self.filt = 17                 # F-052: only if the filter is full; the next rising edge then does not clock

    # ------------------------------------------------------------------ the M2 falling edge
    def cycle(self, a12):
        """End of one M2 cycle. a12 = PPU A12 at the M2 falling edge of this cycle."""
        # A12 filter (F-022, F-051): counts M2 falls with A12 low; a fall with A12 high clocks the counter if the filter
        # is exactly full (16) and always resets it. 17 (set by $C001) is "above full": the next high fall does not clock.
        if a12:
            if self.filt == 16 and not self.cpu_mode:
                self._a12_clock()
            self.filt = 0
        elif self.filt < 16:
            self.filt += 1
        # /IRQ asserts one M2 fall after the clocking fall (F-050), and only if the interrupt is enabled at that fall: an $E001 written in the cycle
        # of the assertion is in time and an $E000 written in it prevents the assertion (F-074; the CPU-mode expiry tests the flag at its own fall, F-071/F-072)
        if self._assert_in:
            self._assert_in -= 1
            if self._assert_in == 0 and self.enabled:
                self.irq = True
        # CPU-cycle mode (F-018, F-019, F-028, F-031)
        if self._t is not None:
            self._t += 1
            early = getattr(self, '_early', False)
            if self._t == (1 if early else 5):
                self._lat_c = self.latch       # the first interval takes the latch as it is 5 cycles after the write (F-087: 1 cycle after it, and 4 cycles shorter)
                self._next = 4 * (self._lat_c + 1) + 2 - (4 if early else 0)
            if self._next is not None and self._t == self._next:
                if self.enabled:
                    self.irq = True            # an expiry while disabled is lost (F-031)
                self._next = self._t + 4 * (self.latch + 1)    # repeat period 4(L+1) with the latch at the expiry [I]

    def _a12_clock(self):
        """One counted A12 pulse (MMC3-style counter). The latch is used at the reload, so the first counted pulse after $C001
        takes it (F-038); the counter expires on the clock that brings it to 0 (pulse L+2 after $C001 with a full filter,
        L+1 otherwise; then every L+1 pulses) (F-021, F-037, F-052, F-055, F-056)."""
        if self.reload:
            self.counter = self.latch               # the reload that follows $C001: expires if the latch is 0 (F-055)
            self.reload = False
            expire = self.counter == 0
        elif self.counter == 0:
            self.counter = self.latch               # the automatic reload at zero never expires; this matters only for latch 0 (F-075)
            expire = False
        else:
            self.counter -= 1
            expire = self.counter == 0
        if expire:
            self._assert_in = 2

    def run(self, n, a12):
        """n M2 cycles with A12 constant; same as n calls of cycle(a12), with shortcuts for idle spans."""
        while n > 0:
            if self._t is None and not self._assert_in:
                if not a12 and self.filt >= 16:
                    return                     # nothing can change
                if not a12:
                    k = min(n, 16 - self.filt)
                    self.filt += k
                    n -= k
                    continue
                if self.filt == 0:
                    n = 0                      # A12 high and already reset: only the first high fall does anything
                    return
            self.cycle(a12)
            n -= 1

    # ------------------------------------------------------------------ combinational outputs
    def prg_ce(self, m2, rw, romsel):
        """PRG /CE asserted (low) only for M2 = 1, R/W = 1 (read), /ROMSEL = 0 (F-012)."""
        return bool(m2 and rw and not romsel)

    def prg_bank(self, cpu_addr):
        """5-bit bank for a CPU read at $8000-$FFFF (PRG A17-A13). The address lines follow CPU A13/A14 even when /ROMSEL is
        high (F-011); /CE does the gating."""
        w = (cpu_addr >> 13) & 3
        p = (self.ctrl >> 6) & 1
        banks = ((self.reg[6], self.reg[7], self.reg[15], 0x1F), (self.reg[15], self.reg[7], self.reg[6], 0x1F))[p]
        return banks[w]

    def chr_bank(self, ppu_addr):
        """8-bit value on CHR A17-A10 for a PPU address 0-$1FFF (F-006, F-007)."""
        w = (ppu_addr >> 10) & 7
        if self.ctrl & 0x80:
            w ^= 4                             # C: swap the two 4 KB halves
        k = (self.ctrl >> 5) & 1
        if w < 4:
            if k:
                return self.reg[(0, 8, 1, 9)[w]]
            r = self.reg[0] if w < 2 else self.reg[1]
            return (r & 0xFE) | ((ppu_addr >> 10) & 1)    # 2 KB window: register bit 0 replaced by PPU A10
        return self.reg[w - 2]                 # R2-R5: bit 0 goes straight to CHR A10

    def ciram_a10(self, ppu_addr):
        """CIRAM A10: PPU A10 (vertical) or PPU A11 (horizontal) (F-041)."""
        return (ppu_addr >> 10) & 1 if self.mirror == 0 else (ppu_addr >> 11) & 1
