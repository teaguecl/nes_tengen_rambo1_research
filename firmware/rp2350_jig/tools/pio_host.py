#!/usr/bin/env python3
"""Host side of the RAMBO-1 RP2350 PIO engine (docs/rp2350_adapter_plan.md). Binary-safe serial, stimulus upload, run, capture download, decoding.
A stimulus word has bit 0 = D0 ... bit 7 = D7, 8 = M2, 9 = R/W, 10 = /ROMSEL, 11 = A0, 12 = A13, 13 = A14, 14 = PPU A10, 15 = PPU A11, 16 = PPU A12.
A capture word has bit k = GPIO 16 + k (the stimulus pins read back are bits 10 to 26)."""
import glob, os, select, struct, sys, termios, time

STIM_NAMES = ["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "M2", "RW", "ROMSEL", "A0", "A13", "A14", "PPUA10", "PPUA11", "PPUA12"]
S = {n: i for i, n in enumerate(STIM_NAMES)}
IDLE = 0x1FFFF
# the chip's outputs: name -> GPIO
OUT_GPIO = {"PRGA13": 18, "PRGA14": 17, "PRGA15": 16, "PRGA16": 47, "PRGA17": 46, "CE": 45, "CHRA10": 44, "CHRA11": 43, "CHRA12": 14, "CHRA13": 13,
            "CHRA14": 12, "CHRA15": 23, "CHRA16": 22, "CHRA17": 21, "CIRAM": 20, "IRQ": 19}
def cap_bit(gpio): return gpio - 16          # None for GPIO below 16 (CHR A12-A14 are outside this capture window)
OUT_BIT = {n: g - 16 for n, g in OUT_GPIO.items() if g >= 16}
STIM_CAPBIT = {n: 10 + i for i, n in enumerate(STIM_NAMES)}     # GPIO 26 + i -> capture bit 10 + i

class Jig:
    def __init__(self, port=None):
        port = port or (sorted(glob.glob('/dev/ttyACM*')) or [None])[-1]
        if not port: raise SystemExit("no /dev/ttyACM* port")
        self.fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        a = termios.tcgetattr(self.fd)
        a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
        a[4] = a[5] = termios.B115200; a[6][termios.VMIN] = 0; a[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSANOW, a)
        self.drain()

    def drain(self, t=0.3):
        end = time.time() + t
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if r: os.read(self.fd, 65536); end = time.time() + t

    def read_line(self, timeout=5.0):
        buf = b''; end = time.time() + timeout
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if r:
                c = os.read(self.fd, 1)
                if c == b'\n': return buf.decode(errors='replace').strip('\r\n> ')
                buf += c
        raise TimeoutError("no line: got %r" % buf)

    def read_exact(self, n, timeout=20.0):
        buf = bytearray(); end = time.time() + timeout
        while len(buf) < n and time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if r: buf += os.read(self.fd, min(65536, n - len(buf)))
        if len(buf) < n: raise TimeoutError("short read %d of %d" % (len(buf), n))
        return bytes(buf)

    def cmd(self, c, lines=1, timeout=5.0):
        """Send a text command; return its reply lines (the first echoed line is skipped)."""
        os.write(self.fd, (c + '\n').encode())
        out = []
        for _ in range(lines + 1):
            out.append(self.read_line(timeout))
        return out[1:]

    def write_all(self, data):
        mv = memoryview(data); off = 0
        while off < len(mv):
            r, w, _ = select.select([], [self.fd], [], 1.0)
            if w:
                try: off += os.write(self.fd, mv[off:off + 4096])
                except BlockingIOError: pass

    def load(self, words):
        self.drain(0.15)
        os.write(self.fd, ("load %d\n" % len(words)).encode())
        self.read_line(); self.read_line()                       # echo, "ready n"
        self.write_all(struct.pack('<%dI' % len(words), *words))
        return self.read_line(10.0)

    def run(self, ncap, div=1.0):
        self.drain(0.1)
        os.write(self.fd, ("run %d %g\n" % (ncap, div)).encode())
        self.read_line()
        lines = [self.read_line(10.0)]
        return lines[0]

    def dump(self, n=None):
        self.drain(0.1)
        os.write(self.fd, ("dump%s\n" % ("" if n is None else " %d" % n)).encode())
        self.read_line()
        hdr = self.read_line(10.0)
        nbytes = int(hdr.split()[1])
        raw = self.read_exact(nbytes, 30.0)
        self.read_line(); self.read_line() if False else None
        self.drain(0.2)
        return list(struct.unpack('<%dI' % (nbytes // 4), raw))

# ---------- helpers for building and reading waveforms
def word(**kw):
    """A stimulus word from the idle pattern with the named lines changed, e.g. word(M2=0, RW=0)."""
    w = IDLE
    for k, v in kw.items():
        w = (w | (1 << S[k])) if v else (w & ~(1 << S[k]))
    return w

def bits(cap, bit): return [(c >> bit) & 1 for c in cap]
def stim_from_cap(cap): return [(c >> 10) & 0x1FFFF for c in cap]
def edges(series):
    return [i for i in range(1, len(series)) if series[i] != series[i - 1]]

# ---------- waveform builder: events at times in ns, rendered on the 6.667 ns PIO grid
PIO_NS = 1e9 / 150e6

class Wave:
    """Build a stimulus as a list of (time_ns, {line: level}) events on a timeline, then render to words (one per PIO cycle, 6.667 ns).
    The state before the first event is idle (all lines high)."""
    def __init__(self): self.events = []
    def at(self, t_ns, **lines):
        self.events.append((t_ns, lines)); return self
    def render(self, t_end_ns, lead_idle=24, trail_idle=24):
        evs = sorted(self.events, key=lambda e: e[0])
        words = [IDLE] * lead_idle
        w = IDLE; i = 0; n = int(round(t_end_ns / PIO_NS))
        for c in range(n):
            t = c * PIO_NS
            while i < len(evs) and evs[i][0] <= t + 1e-9:
                for k, v in evs[i][1].items():
                    w = (w | (1 << S[k])) if v else (w & ~(1 << S[k]))
                i += 1
            words.append(w)
        words.append(IDLE); words += [IDLE] * trail_idle
        return words

def data_bits(v, prefix="D"):
    return {prefix + str(i): (v >> i) & 1 for i in range(8)}

# The console's shape of a CPU cycle (F-064, F-066), relative to the M2 rise at t0 (ns): R/W and the address lines are set about 125 ns before M2 rises,
# /ROMSEL falls 28 ns after M2 rises and rises 13 ns after it falls (M2 high for 363 ns of the 559 ns cycle), R/W returns about 83 ns after M2 falls, the data
# bus holds the stale value (the previous bus byte) until the CPU's byte arrives about 100 ns into the window.
CYCLE_NS = 559.0
def write_cycle(w, t0, addr, data, stale=0xE0, t_data=100.0, t_rw_fall=-125.0, t_rom_fall=28.0, t_m2_high=363.0, t_rom_rise_after_m2f=13.0, t_rw_rise_after_m2f=83.0,
                t_data_hold_after_m2f=170.0, next_data=0xFF, tail=True):
    """One CPU write cycle at address `addr` ($8000 and up) with the byte `data`. Times are relative to the M2 rise t0; every one is a parameter.
    t_data = when the CPU's byte replaces the stale one, relative to the /ROMSEL fall. tail=False leaves R/W, the address and the data as they are after the
    cycle (for a write cycle that follows immediately: consecutive stores keep R/W low)."""
    a = {"A0": addr & 1, "A13": (addr >> 13) & 1, "A14": (addr >> 14) & 1}
    w.at(t0 + t_rw_fall, RW=0, M2=0, ROMSEL=1, **a, **data_bits(stale))
    w.at(t0, M2=1)
    w.at(t0 + t_rom_fall, ROMSEL=0)
    w.at(t0 + t_rom_fall + t_data, **data_bits(data))
    w.at(t0 + t_m2_high, M2=0)
    w.at(t0 + t_m2_high + t_rom_rise_after_m2f, ROMSEL=1)
    if tail:
        w.at(t0 + t_m2_high + t_rw_rise_after_m2f, RW=1)
        w.at(t0 + t_m2_high + t_data_hold_after_m2f, A0=1, A13=1, A14=1, **data_bits(next_data))
    return t0 + CYCLE_NS

def idle_cycles(w, t0, n):
    for k in range(n):
        w.at(t0 + k * CYCLE_NS, M2=1); w.at(t0 + k * CYCLE_NS + 363.0, M2=0)
    return t0 + n * CYCLE_NS
