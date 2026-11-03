#!/usr/bin/env python3
"""Minimal NES harness that models the RAMBO-1 *as measured on the jig* (docs/findings.md) and runs a test ROM on it.
It checks the ROM logic: a ROM that fails here is wrong or mis-specified. It is not an emulator: no rendering, a
synthetic vblank flag, instruction-level interrupt polling, CPU-mode IRQ timing from F-018 only, no A12 counter.
Usage: hwsim.py ROM.nes [--model hw] [--max-cycles N]
Prints the report text, the status byte and the beep count; exit status 0 when the ROM reports all passed."""
import sys, os, argparse

class Mapper:
    """Chip as measured. Only behaviour needed by groups 1 and 2 is modelled."""
    def __init__(self, prg, chr_, model="hw"):
        self.prg, self.chr, self.model = prg, chr_, model
        self.flags = set(model.split(",")) - {"hw"}      # fault injection: emulator-style deviations from the chip
        self.ctrl = 0x20                       # F-003: behaves as 1 KB layout with zero banks
        self.reg = {i: 0 for i in (0, 1, 2, 3, 4, 5, 8, 9)}
        self.reg.update({6: 0x1F, 7: 0x1F, 15: 0x1F})   # F-002
        self.mirror = 0                        # F-004 vertical
        self.latch = 0xFF                      # F-035
        self.enabled = False
        self.cpu_mode = False
        self.irq_line = True                   # F-001 asserted at power-on, released by $E000
        self.next_exp = None
        self.period = 0
        self.pending_ctrl = None
        self.c001_cyc, self.first_pending = None, False
        self.held = False
        self.a12, self.a12_since = 0, -10**6   # A12 level and the cycle it last fell (filter = cycles low)
        self.counter, self.reload, self.swallow, self.latch_c = 0, True, False, 0xFF
        if "noirq" in self.flags: self.irq_line = False      # D4: /IRQ not asserted at power-on
        if "zeroprg" in self.flags:                          # D1, D2, D5: emulator-style power-on registers
            self.reg.update({6: 0, 7: 1, 15: 2, 0: 0, 1: 2, 2: 4, 3: 5, 4: 6, 5: 7, 8: 8, 9: 9}); self.ctrl = 0; self.latch = 0
        if "hdrmirror" in self.flags: self.mirror = 1        # D3: mirroring taken from the (horizontal) header

    def tick(self, cyc):
        while self.cpu_mode and self.next_exp is not None and self.next_exp <= cyc:
            if self.enabled:
                self.irq_line = True
            elif "lost" in self.flags: self.held = True              # fault: an expiry while disabled is kept
            self.first_pending = False
            self.next_exp += self.period

    def a12_set(self, lvl, cyc):
        """PPU A12 changes. A rise counts if A12 was low for >= 16 cycles (F-022, F-051); see edge()."""
        self.tick(cyc)
        if lvl == self.a12: return
        self.a12 = lvl
        if not lvl:
            self.a12_since = cyc; return
        if self.cpu_mode: return
        if cyc - self.a12_since >= (10 if "fastfilter" in self.flags else 16): self.edge()

    def edge(self):
        if self.swallow:                       # F-052: the first pulse after a $C001 with a full filter is swallowed
            self.swallow = False; return
        lat = self.latch_c if "latchearly" in self.flags else self.latch
        if "oddlatch" in self.flags: lat |= 1  # D9: Nestopia-style latch | 1
        if self.reload:
            self.counter, self.reload = lat, False
            expire = self.counter == 0                       # the reload after $C001 expires for latch 0
        elif self.counter == 0:
            self.counter = lat
            expire = "l0repeat" in self.flags and lat == 0   # F-075: the automatic reload at zero does not (fault l0repeat: it does)
        else:
            self.counter -= 1
            expire = self.counter == 0
        if expire:
            if self.enabled: self.irq_line = True
            elif "lost" in self.flags: self.held = True

    def prg_read(self, a):
        w = (a - 0x8000) >> 13
        p = (self.ctrl >> 6) & 1
        bank = [(self.reg[6], self.reg[7], self.reg[15], 0x1F), (self.reg[15], self.reg[7], self.reg[6], 0x1F)][p][w]
        return self.prg[(bank & 0x1F) * 0x2000 + (a & 0x1FFF)]

    def chr_read(self, a):
        a &= 0x1FFF
        s = (a >> 10) ^ (4 if self.ctrl & 0x80 and "noinv" not in self.flags else 0)
        k = (self.ctrl >> 5) & 1
        if s < 4:
            r0, r1 = (self.reg[0], self.reg[1])
            if k:
                v = [self.reg[0], self.reg[8], self.reg[1], self.reg[9]][s]
            else:
                base = r0 if s < 2 else r1
                v = (base & ~1) | ((a >> 10) & 1)          # bit 0 replaced by PPU A10 (F-007)
                if "r0raw" in self.flags:                  # D6 (MesenCE): first half uses the raw register, second half R | 1
                    v = base if (a >> 10) & 1 == 0 else base | 1
        else:
            v = self.reg[s - 2]
        return self.chr[((v & 0xFF) * 1024 + (a & 0x3FF)) % len(self.chr)]

    def nt_page(self, a):
        return ((a >> 10) & 1) if self.mirror == 0 else ((a >> 11) & 1)

    def write(self, a, v, cyc):
        self.tick(cyc if "e1late" in self.flags else cyc - 1)   # F-071/F-072: a write in the expiry's own cycle precedes the expiry (fault e1late: it follows)
        sel, odd = (a >> 13) & 3, a & 1
        if sel == 0:
            if not odd:
                if "defer" in self.flags: self.pending_ctrl = v      # D7 (Mesen2): mapping refreshed only at $8001
                else: self.ctrl = v
            else:
                if self.pending_ctrl is not None: self.ctrl, self.pending_ctrl = self.pending_ctrl, None
                i = self.ctrl & 15
                if i in (0, 1, 2, 3, 4, 5, 8, 9):
                    self.reg[i] = v
                elif i in (6, 7, 15):
                    self.reg[i] = v & 0x1F                 # F-010
        elif sel == 1:
            if not odd:
                self.mirror = v & 1                        # F-041
        elif sel == 2:
            if not odd:
                self.latch = v
                if self.cpu_mode and self.c001_cyc is not None and cyc - self.c001_cyc <= (8 if "latch8" in self.flags else 5) and self.first_pending:
                    self.period = 4 * (v + 1)                      # F-028: still within the load window
                    self.next_exp = self.c001_cyc + self.period + 2
            else:
                if "noswitch" in self.flags and self.cpu_mode: v |= 1        # fault: bit 0 = 0 does not leave CPU mode
                prev_cpu = self.cpu_mode
                self.cpu_mode = bool(v & 1)
                early = self.cpu_mode and not prev_cpu and not (self.a12 == 0 and cyc - self.a12_since >= 15) and "noearly" not in self.flags   # F-087: A12 to CPU with the filter not full: 4 cycles early
                lat = 0 if ("l1" in self.flags and self.latch == 1) else self.latch   # fault: Mesen2-style L = 1 special case
                self.period = (3 if "period3" in self.flags else 4) * (lat + 1)
                if "c001rel" in self.flags: self.irq_line = False                    # fault: $C001 releases /IRQ
                if not ("c001keep" in self.flags and self.next_exp is not None):     # fault: $C001 does not restart the counter
                    self.next_exp = cyc + self.period + 2 - (4 if early else 0) if self.cpu_mode else None   # F-018, F-087
                self.c001_cyc, self.first_pending = cyc, True
                if not self.cpu_mode:
                    self.reload, self.counter, self.latch_c = True, 0, self.latch
                    full = self.a12 == 0 and cyc - self.a12_since >= 15
                    self.swallow = full or "alwaysswallow" in self.flags
                    if "noswallow" in self.flags: self.swallow = False
                    if "a12l1" in self.flags and self.latch <= 1: self.swallow = False   # D8: L <= 1 special case
                    if "swextra" in self.flags and prev_cpu:                              # D14: extra clock on a CPU to A12 switch
                        self.swallow = False; self.edge(); self.swallow = full
        else:
            if not odd:
                self.enabled = False
                self.irq_line = False
                self.held = False
                if "ackrestart" in self.flags and self.cpu_mode: self.next_exp = cyc + self.period + 2   # fault: $E000 restarts the counter
            else:
                self.enabled = True
                if "e1rel" in self.flags: self.irq_line = False
                if self.held: self.irq_line = True; self.held = False


class RefMapper:
    """Adapter: runs the clean reference model (reference/rambo1.py) as the chip, so the test ROMs can be checked against it.
    Model name "ref". A12 levels take effect from the cycle after the change (the sample is at the M2 fall)."""
    def __init__(self, prg, chr_, model="ref"):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reference"))
        from rambo1 import Rambo1
        self.m = Rambo1()
        self.prg, self.chr = prg, chr_
        self.flags = set()
        self.level, self.done = 0, 0

    def advance(self, to):
        if to > self.done:
            self.m.run(to - self.done, self.level)
            self.done = to

    @property
    def irq_line(self): return self.m.irq

    def tick(self, cyc): self.advance(cyc)

    def write(self, a, v, cyc):
        self.advance(cyc)
        self.m.write(a, v)

    def a12_set(self, lvl, cyc):
        self.advance(cyc + 1)
        self.level = lvl

    def prg_read(self, a):
        return self.prg[(self.m.prg_bank(a) & 0x1F) * 0x2000 + (a & 0x1FFF)]

    def chr_read(self, a):
        return self.chr[((self.m.chr_bank(a & 0x1FFF) & 0xFF) * 1024 + (a & 0x3FF)) % len(self.chr)]

    def nt_page(self, a): return self.m.ciram_a10(a)

class NES:
    def __init__(self, rom, model):
        assert rom[:4] == b"NES\x1a"
        prg_len, chr_len = rom[4] * 16384, rom[5] * 8192
        self.map = (RefMapper if model == "ref" else Mapper)(rom[16:16 + prg_len], rom[16 + prg_len:16 + prg_len + chr_len], model)
        self.ram = bytearray(2048)
        self.vram = [bytearray(1024), bytearray(1024)]
        self.pal = bytearray(32)
        self.vaddr = 0; self.toggle = 0; self.buf = 0; self.ppuctrl = 0; self.ppumask = 0
        self.vbl_read_frame = -1
        self.pad_bits = [0] * 8; self.pad_idx = 0                  # controller 1: A B SELECT START UP DOWN LEFT RIGHT
        self.oam = bytearray(256); self.oamaddr = 0; self.nmi_done = -1; self.pt = None
        self.render_on = False
        self.cyc = 0
        self.a = self.x = self.y = 0; self.sp = 0xFD
        self.n = self.v = self.d = self.z = self.c = 0; self.i = 1
        self.pc = self.rd16(0xFFFC)

    # ---- bus
    FR, V0 = 262 * 341, 241 * 341 + 1       # PPU dots per frame; the dot at which the vblank flag is set (line 241, dot 1)

    def vbl(self):
        f, r = divmod(self.cyc * 3 - self.V0, self.FR)
        return r < 20 * 341 and self.vbl_read_frame != f

    def hit(self):
        """Sprite 0 hit flag: set at line OAM[0].Y + 1, dot X + 2, cleared at the pre-render line (the picture is assumed to have opaque pixels there)."""
        if self.ppumask & 0x18 != 0x18: return False
        line = self.oam[0] + 1
        if line > 239: return False
        pos = (self.cyc * 3) % self.FR
        return line * 341 + self.oam[3] + 2 <= pos < 261 * 341 + 1

    def a12_events(self, t0, t1):
        """A12 transitions of the rendering PPU in the dot range (t0, t1], by pattern table configuration."""
        ctrl = self.ppuctrl
        spr = 1 if ctrl & 0x28 else 0                   # 8x16 sprites fetch $1000 too (unused sprites use tile $FF)
        bg = 1 if ctrl & 0x10 else 0
        ev = []
        for fr in range(t0 // self.FR, t1 // self.FR + 1):
            base = fr * self.FR
            for ln in range(max(0, (t0 - base) // 341 - 1), min(261, (t1 - base) // 341 + 1) + 1):
                rend, lb = ln < 240 or ln == 261, base + ln * 341
                if spr and not bg:
                    if rend: ev += [(lb + 260, 1), (lb + 324, 0)]          # sprite fetches at $1000, once per line
                elif bg and not spr:
                    if rend: ev += [(lb + 324, 1)]                         # next line's background prefetch at $1000
                    if ln < 240: ev += [(lb + 257, 0)]                     # sprite fetches at $0000 pull A12 low
                    if ln == 261: ev += [(lb + 1, 0)]                      # idle bus keeps A12 high through vblank (measured)
                elif spr and bg:
                    if ln == 261: ev += [(lb + 260, 1)]                    # high through the whole frame
                    if ln == 241: ev += [(lb, 0)]
        return sorted(e for e in ev if t0 < e[0] <= t1)

    def ppu_sync(self):
        t = self.cyc * 3
        if self.pt is None: self.pt = t; return
        if t <= self.pt: return
        if self.ppumask & 0x18:
            for T, lvl in self.a12_events(self.pt, t): self.map.a12_set(lvl, T // 3)
        self.pt = t

    def ppu_read_vram(self, a):
        a &= 0x3FFF
        if a < 0x2000: return self.map.chr_read(a)
        if a < 0x3F00: return self.vram[self.map.nt_page(a)][a & 0x3FF]
        return self.pal[a & 0x1F]

    def rd(self, a):
        self.ppu_sync()
        self.map.tick(self.cyc)
        if a < 0x2000: return self.ram[a & 0x7FF]
        if 0x2000 <= a < 0x4000:
            r = a & 7
            if r == 2:
                v = (0x80 if self.vbl() else 0) | (0x40 if self.hit() else 0)
                if v & 0x80:
                    self.vbl_read_frame = (self.cyc * 3 - self.V0) // self.FR
                self.toggle = 0
                return v
            if r == 7:
                if (self.vaddr & 0x3FFF) < 0x3F00:
                    v, self.buf = self.buf, self.ppu_read_vram(self.vaddr)
                else:
                    v = self.ppu_read_vram(self.vaddr)
                self.vaddr = (self.vaddr + (32 if self.ppuctrl & 4 else 1)) & 0x7FFF
                return v
            return 0
        if a == 0x4015: return 0
        if a == 0x4016:
            v = self.pad_bits[self.pad_idx] if self.pad_idx < 8 else 1
            self.pad_idx += 1
            return v
        if a >= 0x8000:
            v = self.map.prg_read(a)
            if "rddec" in self.map.flags: self.map.write(a, v, self.cyc)      # fault: reads decoded as writes
            return v
        return 0

    SOFS = {'zp': 2, 'zpx': 3, 'zpy': 3, 'abs': 3, 'absx': 4, 'absy': 4, 'indx': 5, 'indy': 5}   # store: write on the last cycle
    ROFS = {'zp': 4, 'zpx': 5, 'abs': 5, 'absx': 6}                                              # read-modify-write: final write

    def wr(self, a, v, ofs=0):
        self.ppu_sync()
        if a < 0x2000: self.ram[a & 0x7FF] = v; return
        if 0x2000 <= a < 0x4000:
            r = a & 7
            if r == 0: self.ppuctrl = v
            elif r == 1: self.ppumask = v; self.render_on = bool(v & 0x18)
            elif r == 3: self.oamaddr = v
            elif r == 4: self.oam[self.oamaddr] = v; self.oamaddr = (self.oamaddr + 1) & 0xFF
            elif r == 6:
                if not self.toggle: self.vaddr = (v & 0x3F) << 8 | (self.vaddr & 0xFF)
                else:
                    self.vaddr = (self.vaddr & 0x7F00) | v
                    self.map.a12_set((self.vaddr >> 12) & 1, self.cyc + ofs)
                self.toggle ^= 1
            elif r == 7:
                a2 = self.vaddr & 0x3FFF
                if 0x2000 <= a2 < 0x3F00: self.vram[self.map.nt_page(a2)][a2 & 0x3FF] = v
                elif a2 >= 0x3F00: self.pal[a2 & 0x1F] = v
                self.vaddr = (self.vaddr + (32 if self.ppuctrl & 4 else 1)) & 0x7FFF
            return
        if a == 0x4016 and not v & 1: self.pad_idx = 0                       # strobe
        if a >= 0x8000:
            if "conflict" in self.map.flags: v &= self.map.prg_read(a)        # fault: bus conflict, AND with the ROM byte
            self.map.write(a, v, self.cyc + ofs); return
        if a >= 0x4020 and "lowdec" in self.map.flags: self.map.write(a | 0x8000, v, self.cyc + ofs)   # fault: /ROMSEL ignored

    def rd16(self, a): return self.rd(a) | self.rd(a + 1) << 8

    # ---- cpu
    def push(self, v): self.wr(0x100 + self.sp, v); self.sp = (self.sp - 1) & 0xFF
    def pull(self): self.sp = (self.sp + 1) & 0xFF; return self.rd(0x100 + self.sp)
    def getp(self, b=0x20):
        return self.n << 7 | self.v << 6 | 0x20 | b | self.d << 3 | self.i << 2 | self.z << 1 | self.c
    def setp(self, p):
        self.n, self.v, self.d, self.i, self.z, self.c = p >> 7 & 1, p >> 6 & 1, p >> 3 & 1, p >> 2 & 1, p >> 1 & 1, p & 1
    def nz(self, v): self.n = v >> 7 & 1; self.z = int(v == 0); return v

    def addr(self, mode, rw):
        """Return (effective address, extra cycles) for an addressing mode; rw 'r' adds page-cross cycles."""
        pc = self.pc
        if mode == 'imm': self.pc += 1; return pc, 0
        if mode == 'zp': self.pc += 1; return self.rd(pc), 0
        if mode == 'zpx': self.pc += 1; return (self.rd(pc) + self.x) & 0xFF, 0
        if mode == 'zpy': self.pc += 1; return (self.rd(pc) + self.y) & 0xFF, 0
        if mode == 'abs': self.pc += 2; return self.rd16(pc), 0
        if mode in ('absx', 'absy'):
            self.pc += 2; b = self.rd16(pc); i = self.x if mode == 'absx' else self.y; e = (b + i) & 0xFFFF
            return e, (1 if rw == 'r' and (b ^ e) & 0xFF00 else 0)
        if mode == 'indx':
            self.pc += 1; z = (self.rd(pc) + self.x) & 0xFF
            return self.rd(z) | self.rd((z + 1) & 0xFF) << 8, 0
        if mode == 'indy':
            self.pc += 1; z = self.rd(pc); b = self.rd(z) | self.rd((z + 1) & 0xFF) << 8; e = (b + self.y) & 0xFFFF
            return e, (1 if rw == 'r' and (b ^ e) & 0xFF00 else 0)
        raise Exception(mode)

    def branch(self, cond):
        off = self.rd(self.pc); self.pc += 1
        cyc = 2
        if cond:
            if off & 0x80: off -= 256
            t = (self.pc + off) & 0xFFFF
            cyc += 1 + (1 if (t ^ self.pc) & 0xFF00 else 0)
            self.pc = t
        return cyc

    def irq(self):
        self.push(self.pc >> 8); self.push(self.pc & 0xFF); self.push(self.getp(0x20)); self.i = 1
        self.pc = self.rd16(0xFFFE); self.cyc += 7

    def nmi(self):
        self.push(self.pc >> 8); self.push(self.pc & 0xFF); self.push(self.getp(0x20)); self.i = 1
        self.pc = self.rd16(0xFFFA); self.cyc += 7

    def step(self):
        self.ppu_sync()
        if self.ppuctrl & 0x80:
            f, r = divmod(self.cyc * 3 - self.V0, self.FR)
            if r < 20 * 341 and self.nmi_done != f:
                self.nmi_done = f; self.nmi(); return
        self.map.tick(self.cyc)
        if self.map.irq_line and not self.i:
            self.irq(); return
        op = self.rd(self.pc); self.pc += 1
        cyc = self.exec(op)
        self.cyc += cyc

    ALU = {0: 'ora', 1: 'and', 2: 'eor', 3: 'adc', 4: 'sta', 5: 'lda', 6: 'cmp', 7: 'sbc'}
    M01 = ['indx', 'zp', 'imm', 'abs', 'indy', 'zpx', 'absy', 'absx']

    def adc(self, m):
        r = self.a + m + self.c
        self.v = int((~(self.a ^ m) & (self.a ^ r)) & 0x80 != 0); self.c = int(r > 255); self.a = self.nz(r & 0xFF)

    def exec(self, op):
        c, b, a = op & 3, op >> 2 & 7, op >> 5
        impl = {0x08: 'php', 0x28: 'plp', 0x48: 'pha', 0x68: 'pla', 0x88: 'dey', 0xA8: 'tay', 0xC8: 'iny', 0xE8: 'inx',
                0x18: 'clc', 0x38: 'sec', 0x58: 'cli', 0x78: 'sei', 0x98: 'tya', 0xB8: 'clv', 0xD8: 'cld', 0xF8: 'sed',
                0x8A: 'txa', 0x9A: 'txs', 0xAA: 'tax', 0xBA: 'tsx', 0xCA: 'dex', 0xEA: 'nop'}
        if op in impl:
            n = impl[op]
            if n == 'php': self.push(self.getp(0x30)); return 3
            if n == 'plp': self.setp(self.pull()); return 4
            if n == 'pha': self.push(self.a); return 3
            if n == 'pla': self.a = self.nz(self.pull()); return 4
            if n == 'dey': self.y = self.nz((self.y - 1) & 0xFF)
            elif n == 'tay': self.y = self.nz(self.a)
            elif n == 'iny': self.y = self.nz((self.y + 1) & 0xFF)
            elif n == 'inx': self.x = self.nz((self.x + 1) & 0xFF)
            elif n == 'clc': self.c = 0
            elif n == 'sec': self.c = 1
            elif n == 'cli': self.i = 0
            elif n == 'sei': self.i = 1
            elif n == 'tya': self.a = self.nz(self.y)
            elif n == 'clv': self.v = 0
            elif n == 'cld': self.d = 0
            elif n == 'sed': self.d = 1
            elif n == 'txa': self.a = self.nz(self.x)
            elif n == 'txs': self.sp = self.x
            elif n == 'tax': self.x = self.nz(self.a)
            elif n == 'tsx': self.x = self.nz(self.sp)
            elif n == 'dex': self.x = self.nz((self.x - 1) & 0xFF)
            return 2
        if op & 0x1F == 0x10:        # branches
            f = [self.n, self.v, self.c, self.z][a >> 1]
            return self.branch(f == (a & 1))
        if op == 0x20:
            t = self.rd16(self.pc); r = self.pc + 1; self.push(r >> 8); self.push(r & 0xFF); self.pc = t; return 6
        if op == 0x60: self.pc = (self.pull() | self.pull() << 8) + 1; return 6
        if op == 0x40: self.setp(self.pull()); self.pc = self.pull() | self.pull() << 8; return 6
        if op == 0x4C: self.pc = self.rd16(self.pc); return 3
        if op == 0x6C:
            p = self.rd16(self.pc); self.pc = self.rd(p) | self.rd((p & 0xFF00) | ((p + 1) & 0xFF)) << 8; return 5
        if c == 1:
            m = self.M01[b]; name = self.ALU[a]
            e, ex = self.addr(m, 'w' if name == 'sta' else 'r')
            base = {'imm': 2, 'zp': 3, 'zpx': 4, 'abs': 4, 'absx': 4, 'absy': 4, 'indx': 6, 'indy': 5}[m]
            if name == 'sta':
                self.wr(e, self.a, self.SOFS[m]); return base + (1 if m in ('absx', 'absy', 'indy') else 0)
            v = self.rd(e)
            if name == 'lda': self.a = self.nz(v)
            elif name == 'ora': self.a = self.nz(self.a | v)
            elif name == 'and': self.a = self.nz(self.a & v)
            elif name == 'eor': self.a = self.nz(self.a ^ v)
            elif name == 'adc': self.adc(v)
            elif name == 'sbc': self.adc(v ^ 0xFF)
            elif name == 'cmp': r = self.a - v; self.c = int(self.a >= v); self.nz(r & 0xFF)
            return base + ex
        if c == 2:
            if b == 2:               # accumulator shifts
                v = self.a
                self.a = self.shift(a, v); return 2
            if a >= 4 and a <= 5:    # STX / LDX
                m = {0: 'imm', 1: 'zp', 3: 'abs', 5: 'zpy', 7: 'absy'}[b]
                e, ex = self.addr(m, 'r' if a == 5 else 'w')
                if a == 4: self.wr(e, self.x, self.SOFS[m]); return {'zp': 3, 'zpy': 4, 'abs': 4}[m]
                self.x = self.nz(self.rd(e)); return {'imm': 2, 'zp': 3, 'zpy': 4, 'abs': 4, 'absy': 4}[m] + ex
            m = {1: 'zp', 3: 'abs', 5: 'zpx', 7: 'absx'}[b]
            e, ex = self.addr(m, 'w')
            v = self.rd(e)
            self.wr(e, v, self.ROFS[m] - 1)    # NMOS 6502 read-modify-write: old value is written back first
            if a == 6: v = self.nz((v - 1) & 0xFF)
            elif a == 7: v = self.nz((v + 1) & 0xFF)
            else: v = self.shift(a, v)
            if not ('rmwfirst' in self.map.flags and e >= 0x8000): self.wr(e, v, self.ROFS[m])     # fault: only the first (old value) write reaches the chip
            return {'zp': 5, 'zpx': 6, 'abs': 6, 'absx': 7}[m]
        if c == 0:
            m = {0: 'imm', 1: 'zp', 3: 'abs', 5: 'zpx', 7: 'absx'}[b]
            e, ex = self.addr(m, 'r' if a != 4 else 'w')
            base = {'imm': 2, 'zp': 3, 'zpx': 4, 'abs': 4, 'absx': 4}[m]
            if a == 1:               # BIT
                v = self.rd(e); self.z = int(self.a & v == 0); self.n = v >> 7 & 1; self.v = v >> 6 & 1; return base
            if a == 4: self.wr(e, self.y, self.SOFS[m]); return base
            v = self.rd(e)
            if a == 5: self.y = self.nz(v)
            elif a == 6: self.c = int(self.y >= v); self.nz((self.y - v) & 0xFF)
            elif a == 7: self.c = int(self.x >= v); self.nz((self.x - v) & 0xFF)
            else: raise Exception("op %02x" % op)
            return base + ex
        raise Exception("unimplemented opcode %02x at %04x" % (op, self.pc - 1))

    def shift(self, a, v):
        if a == 0: self.c = v >> 7; v = (v << 1) & 0xFF
        elif a == 1: o = self.c; self.c = v >> 7; v = (v << 1 | o) & 0xFF
        elif a == 2: self.c = v & 1; v >>= 1
        elif a == 3: o = self.c; self.c = v & 1; v = v >> 1 | o << 7
        else: raise Exception("shift")
        return self.nz(v)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("rom"); ap.add_argument("--model", default="hw")
    ap.add_argument("--max-cycles", type=int, default=80_000_000); ap.add_argument("--quiet", action="store_true")
    o = ap.parse_args()
    nes = NES(open(o.rom, "rb").read(), o.model)
    while nes.cyc < o.max_cycles and not (nes.ram[0x301:0x304] == b"\xde\xb0\x61" and nes.ram[0x300] != 0x80):
        nes.step()
    status = nes.ram[0x300]
    if nes.ram[0x300] == 0x80:
        print("TIMEOUT: ROM never reached the results screen; status $%02X pc $%04X" % (status, nes.pc)); return 2
    text = bytes(nes.ram[0x304:0x800]).split(b"\0")[0].decode()
    if not o.quiet: print(text)
    sig = bytes(nes.ram[0x301:0x304]).hex()
    print("status $%02X  signature %s  beeps %d  cycles %d" % (status, sig, status if status else 1, nes.cyc))
    return 0 if status == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
