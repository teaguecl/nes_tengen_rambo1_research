# Tengen RAMBO-1 (337006): functional description

**DRAFT 0.5, 2026-11-02.** This document explains how the chip works as a system. It is derived from
`docs/findings.md` (F-001 to F-090), which is the reference for exact values
and evidence; this document is the narrative: what blocks the chip contains, what each one does, and how a program sees them. Evidence markers are defined at the top of `docs/findings.md`: **[V]** verified on the jig, **[I]** inferred,
**[U]** unknown, **[C]** confirmed by a test ROM on a real NES (v0.2). All statements come from one chip, measured on the jig
at whole-M2-cycle resolution (about 2 us per bus step, not the 280 ns half-cycle of a real NES) and then confirmed in a real
console with six test ROMs (`rom/README.txt`); the CPU-cycle interrupt was measured there to 1-cycle resolution. Propagation delays in the console were then measured with a logic analyser to +-5 ns (`docs/timing_measurements.md`, F-064 to F-076). Setup and hold, the write window, output delays, the filter threshold and the power-on state were finally measured with an RP2350 adapter that places bus edges to 6.7 ns (F-078 to F-090).

## 1. What the chip is

The RAMBO-1 is a cartridge mapper. It sits between the NES CPU and PPU buses and the cartridge's PRG and CHR memories.
It does five jobs:

1. It turns CPU writes to $8000-$FFFF into bank numbers, and drives the upper address lines of the PRG ROM (A13-A17)
   and the CHR ROM (A10-A17).
2. It enables the PRG ROM only during CPU reads of $8000-$FFFF (the /CE output).
3. It controls nametable mirroring through one output (CIRAM A10).
4. It counts either PPU scanlines (through PPU A12) or CPU cycles, and raises an interrupt (/IRQ) when a programmed count
   expires.
5. It contains the cartridge's lockout (CIC) function on pins 15-18 **[I]**. This was not exercised; nothing in
   this document describes it.

Its register scheme is the MMC3's with extensions (this document's structure follows the measured behaviour, not
the NESdev text). The IRQ timing differs from an MMC3's; see section 6.

## 2. Block diagram (functional)

```
 CPU side                                   PPU side
 M2, R/W, /ROMSEL, A0, A13, A14, D0-D7      PPU A10, A11, A12
        |                                          |
   +----+--------------+                 +---------+----------+
   | write-window logic |                 |  A12 edge filter   |
   | (M2 & !R/W & !ROMSEL)                +---------+----------+
   +----+---------+-----+                           |
        |         |                                 v
        |   register file  <------ pin 19 -----> IRQ counter + latch  ---> /IRQ
        |   (bank select, R0-R9, RF,              (A12 or CPU-cycle clock)
        |    mirroring, IRQ regs)
        |         |
        +--> PRG bank mux ---> PRG A13-A17       CHR bank mux ---> CHR A10-A17
        +--> /CE decode  ---> PRG /CE            mirroring mux --> CIRAM A10
```

The register file is written only by the CPU. The CHR mux, PRG mux and mirroring mux are purely combinational reads of
it plus the incoming address lines **[I]** (from F-006 to F-011, F-041): no clocked output stage was
observed, and changing PPU A10-A12 or CPU A13/A14 changes the outputs immediately at the resolution tested.

## 3. The bus interface

### 3.1 Register writes

The chip has no address latch or clock of its own for writes. A write is enabled by a level condition:

> **M2 high, R/W low, /ROMSEL low** (any order) **[V]** (F-013)

While this condition holds, the CHR bank registers (R0-R5, R8, R9) and the mirroring register (`$A000`) are transparent: their outputs follow the data bus **[V][C]** (F-014, F-066, F-070, F-089). The PRG bank registers (R6, R7, RF) are not: they change when the window closes **[V]** (F-089). The control register (`$8000`) also takes effect only at the end of the cycle, 15 ns after M2 falls **[C]** (F-069). The window closes at the first of the M2 fall, the /ROMSEL rise and the R/W rise, and the register keeps the data that was present at that
instant (setup and hold each under 10 ns; a 7 ns window is enough) **[V]** (F-082), and ignores everything after. Address bits A0, A13 and A14 are taken as they are during the window **[V]**
(F-016). On a real NES the CPU holds data stable around the closing edge, so this behaves like an ordinary write.

Practical consequences for a program:

- No write is possible with M2 low, with R/W high or with /ROMSEL high, so the chip cannot be disturbed by PRG ROM
  reads or by other bus traffic **[V]**.
- Read-modify-write instructions leave the final value in the register: of the two back-to-back writes the second wins
  **[C]** (F-063).
- The chip has no A1-A12 pins, so those address bits take no part in the decode: each 8 KB block ($8000, $A000, $C000, $E000)
  holds its even/odd register pair repeated throughout **[C]** (F-063). A program may use any address in the block.
- Reads of the eight register addresses change nothing: no register, output, counter or /IRQ is affected **[V]** (F-086).

### 3.2 PRG /CE

PRG /CE goes low only when **M2 = 1, R/W = 1, /ROMSEL = 0**; the other seven combinations give high **[V]** (F-012).
The ROM is therefore enabled only during CPU reads of $8000-$FFFF, never during writes. This explains why register
writes to ROM space cause no bus conflict **[I]**; a real console confirms it: a write stores the data written, not the data ANDed with
the ROM byte **[C]** (F-063).

## 4. Banking

### 4.1 Registers

Eight register addresses are decoded from CPU A14, A13 and A0 (even/odd pairs at $8000, $A000, $C000, $E000):

| Address | Function |
|---|---|
| $8000 | Bank select: register index (bits 0-3), K (bit 5), P (bit 6), C (bit 7) |
| $8001 | Bank data for the selected index |
| $A000 | Mirroring (bit 0) |
| $A001 | No visible function |
| $C000 | IRQ latch |
| $C001 | IRQ mode and counter restart |
| $E000 | IRQ acknowledge and disable |
| $E001 | IRQ enable |

The two-step $8000/$8001 scheme is the MMC3's: write the index, then the data. Index values:

- 0-5: CHR banks R0-R5, 8 bits wide.
- 6, 7: PRG banks R6, R7, 5 bits wide.
- 8, 9: extra CHR banks R8, R9, 8 bits wide, used only when K = 1.
- F: PRG bank RF, 5 bits wide.
- A-E: accept no visible data; bit 4 of $8000 has no visible effect **[V]** (F-039, F-040).

### 4.2 CHR

Eight 1 KB windows from $0000 to $1FFF are mapped to registers as follows. K selects between 2 KB banks (R0, R1) and
1 KB banks (R0/R8, R1/R9). C swaps the two 4 KB halves **[V]** (F-006).

| K / C | $0000 | $0400 | $0800 | $0C00 | $1000 | $1400 | $1800 | $1C00 |
|---|---|---|---|---|---|---|---|---|
| 0 / 0 | R0 | R0 | R1 | R1 | R2 | R3 | R4 | R5 |
| 1 / 0 | R0 | R8 | R1 | R9 | R2 | R3 | R4 | R5 |
| 0 / 1 | R2 | R3 | R4 | R5 | R0 | R0 | R1 | R1 |
| 1 / 1 | R2 | R3 | R4 | R5 | R0 | R8 | R1 | R9 |

In a 2 KB window, the register's bit 0 is replaced by PPU A10, so the pair of 1 KB halves is consecutive. In every other
window register bit 0 goes straight to CHR A10 **[V]** (F-007). R8 and R9 can be written at any time and keep their
value; they take effect when K becomes 1 **[V]** (F-049).

### 4.3 PRG

Three switchable 8 KB windows and one fixed window. P swaps which register serves $8000 and $C000 **[V]** (F-009):

| Window | P = 0 | P = 1 |
|---|---|---|
| $8000-$9FFF | R6 | RF |
| $A000-$BFFF | R7 | R7 |
| $C000-$DFFF | RF | R6 |
| $E000-$FFFF | bank $1F | bank $1F |

Only five bits of the register reach PRG A13-A17, so the PRG ROM is at most 256 KB **[V]** (F-010). The PRG address
lines track CPU A13/A14 continuously, even when /ROMSEL is high; only /CE is gated **[V]** (F-011).

### 4.4 Mirroring

CIRAM A10 is driven by PPU A10 when $A000 bit 0 = 0 (vertical) and by PPU A11 when bit 0 = 1 (horizontal). Only bit 0
matters **[V]** (F-041). There is only one mirroring output, so one-screen and four-screen layouts are **[U]**.

## 5. Power-on behaviour

Without any program running, the chip comes up in a defined state **[V]** (F-001 to F-004, F-034, F-035):

- PRG: all switchable windows show bank $1F, the same as the fixed window. A program therefore finds its reset vector
  and initialisation code at the top of the ROM regardless of which window it executes in. The NESdev statement that
  the banks are unspecified at power-on does not hold for this chip: they measured $1F on every cold start.
- CHR: every output is 0, in the 1 KB layout (CHR A10 does not follow PPU A10 until K is cleared).
- Mirroring: vertical, even if the iNES header says horizontal.
- IRQ latch: $FF, and the counter is already running in CPU-cycle mode, so a program that enables /IRQ (`$E001`) without ever writing `$C001` gets a first interrupt about 1018 M2 cycles after power-on **[V]** (F-088). A12 pulses before the first `$C001` do nothing. The A12 filter is not full at power-on (about 8 M2 falls after a short power cycle, 2 to 5 after seconds off), so the first pulses can count early (F-085).
- **/IRQ is asserted** until the program writes $E000. It is not the counter expiring. Whether this is a stored flag or
  a property of the enable logic is **[U]** (F-034). A program should therefore write $E000 early, as the MMC3
  convention already requires.
- The console's reset button does **not** reset the chip: banks, mirroring and the interrupt state stay as they were
  **[C]** (F-061). This state applies only after a power cycle, and a program started by reset must not assume it. The supply must really collapse for the power-on state: with the rail left at about 1 V the chip kept its registers for a minute (F-078), and /IRQ stays released through a power-off of up to about 5 s (F-079).

## 6. The interrupt counter

### 6.1 Structure

The IRQ section is an 8-bit down counter with an 8-bit reload latch ($C000), a clock source chosen by $C001 bit 0,
an enable flag ($E000/$E001) and a sticky interrupt output. The counter and the interrupt are separate: the counter
runs and reloads whether or not interrupts are enabled **[V]** (F-019, F-031).

Writing $C001 restarts the counter in the selected mode and starts a fresh interval. It does not release an
asserted /IRQ **[V]** (F-024, F-025, F-026).

### 6.2 CPU-cycle mode

A divide-by-4 prescaler counts M2 cycles. Every fourth M2 cycle clocks the counter. After a $C001 write, the first
clock arrives about 5 M2 cycles later, when the counter takes the latch; the interrupt first asserts at
**4(L+1)+2 cycles** after the write, then every **4(L+1)** cycles **[V]** (F-018, F-019, F-028, F-054). Measured with a real
CPU at 1-cycle resolution **[C]** (F-058): the first-expiry time is exactly linear in L, 4 cycles per step, from L = 0 up to 255,
with no special case at L = 0 or 1. **Exception [V] (F-087):** if the mode is switched from A12 to CPU with the A12 filter below 16 at the `$C001` write, the first expiry comes 4 cycles early, 4(L+1)-2 after the write; a CPU to CPU rewrite is not early. The counter
takes the latch value as it stands when it loads: a $C000 write up to 5 cycles after $C001 sets the first interval; a
later write only changes later intervals.

### 6.3 A12 (scanline) mode

The PPU's A12 line, rising once per scanline when BG and sprites use different pattern tables, clocks the counter,
after a filter that rejects the rapid A12 toggling during sprite fetches:

- The filter counts M2 falling edges while A12 is low, up to 16 **[V]** (F-022, F-051); the threshold does not depend on the M2 period (300 to 1500 ns), nothing is counted by time, and an A12 glitch between falls is ignored **[V]** (F-084). A12 is sampled at the M2 fall only, with setup and hold under 10 ns (F-081).
- A12 rising only counts as a clock if the filter has reached 16. The counter is clocked at the M2 falling edge where A12
  is high, once per pulse. Every M2 fall with A12 high resets the filter **[V]** (F-023, F-051).
- A write to $C001 sets the filter to 17 if it was full, so the first edge after the write is skipped; if it was not
  full, the first edge counts **[V]** (F-052).
- In the normal (full-filter) case, the second edge loads the latch and the interrupt asserts on counted edge **L+2**,
  then every **L+1** edges. This is one edge later than an MMC3 and matches the reported "late IRQ" **[V]**
  (F-021, F-037, F-038, F-052).
- /IRQ falls one M2 falling edge after the clocking edge **[V]** (F-050).
- The first-expiry rule has no special case for L = 0 or 1 (it is pulse L+2 for a full filter and L+1 for one that is not)
  **[V]** (F-055); the repeat period is L+1 for every latch **[V]** (F-056); all of this holds with the pulses made by the
  console's own PPU address register **[C]** (F-059).
- A $C000 write before the first counted pulse sets the first interval; a later one is used from the next reload **[C]**
  (F-038, F-059).

### 6.4 A12 mode in a running picture

With rendering on, the PPU gives the filter one counted pulse per line, so a frame has 241 counted pulses (240 lines plus
the pre-render line) **[C]** (F-060). Which line the interrupt falls on depends on where A12 rises:

- **Sprites at $1000, background at $0000** (the usual MMC3 arrangement; 8x16 sprites with odd tiles work the same, and so does
  the CHR inversion bit, which does not touch the PPU's A12): the pulse is at dot 260 of each line. A12 is low in vblank, so
  the first pulse after a $C001 written there is swallowed, and the interrupt arrives **on line L**, in the horizontal blank
  after the visible pixels. A handler that writes PPUMASK first thing changes the picture from the next line **[C]**.
- **Background at $1000, sprites at $0000**: the pulse is at about dot 324 (the prefetch for the next line), and A12 is still
  high in vblank, so the first pulse is not swallowed (the "filter not full" rule of F-052). The interrupt arrives **on line
  L - 1**, one line earlier than in the first case **[C]**.
- Both tables at $0000: A12 never rises, no interrupts. Both at $1000: A12 is almost always high, and only one interrupt was
  seen in eight frames with L = 0 **[C]**. This is not about the waveform: with latch 0 the counter expires only on the reload after `$C001` **[C]** (F-075), so one counted pulse is enough and one interrupt is all there is **[I]**.

Counting interrupts: with latch L, eight frames give floor((8 x 241 - (L + 2)) / (L + 1)) + 1 interrupts (120 for L = 15, 240 for
L = 7, 15 for L = 127), and CPU-cycle mode with L = 255 gives 232 interrupts in eight frames **[C]**.

### 6.5 Acknowledge and enable

/IRQ is sticky. Once low it stays low until $E000, which also disables further interrupts. $E001 only enables. An
expiry that occurs while disabled is lost: nothing is remembered and /IRQ asserts at the next expiry after
enabling **[V]** (F-020, F-029, F-031, F-032). Neither $E000 nor $E001 changes the counter phase. A write to `$E000` or `$E001` in the same CPU cycle as a CPU-mode expiry counts, one cycle later is too late **[C]** (F-071, F-072); in A12 mode the enable flag is tested one M2 fall after the clocking fall, so a write in the clocking cycle or the next one counts **[C]** (F-074). The flag is a stored level, tested at the M2 fall to within about 7 ns (F-090).

### 6.6 What a program should expect

- To use scanline mode like an MMC3: write the latch, write $C001 (bit 0 = 0), then $E001. Allow for L+2 rather than L+1
  edges for the first interrupt, and L+1 afterwards. With the usual pattern-table arrangement and $C001 written in vblank
  the interrupt is on line L; with the background at $1000 it is on line L - 1.
- Writing $C001 while the filter is not full (A12 high or toggling within the preceding 16 M2 cycles) changes the
  first interval by one edge.
- To use cycle mode: set bit 0 in $C001. The interval is fully predictable in CPU cycles; it can be used without the
  PPU.
- At power-on the latch is $FF, /IRQ is asserted and the CPU-cycle counter is already running, so write $E000 first, and write `$C001` before enabling if you want a defined interval.

## 7. Pin 19

Pin 19 is an input (it has clamp diodes like the other inputs) and is tied to ground on the Tengen board **[V]**
(F-043). With it low, or never driven, the chip behaves as described above **[V]** (F-044, F-045). With it high, every
register write stores the constant $0B whatever data is on the bus, so the chip cannot be programmed normally
**[V]** (F-046). Treat this as a test mode. A released pin keeps its last level **[V]** (F-047), so it should be tied
to ground in any design. Its role in manufacturing or in the original design is **[U]**.

## 8. What the chip does not do

Observed to be absent **[V]**:

- No PRG-RAM control: $A001 has no visible effect on any output (F-042, F-053).
- No bus conflicts: /CE is never enabled during a write.
- No dependence of banking on /ROMSEL, apart from /CE (F-011).
- No reset input: the console's reset button does not change any chip state (F-061).
- No address decode on A1-A12 (F-063).
- No read side effects: reading the register addresses changes nothing (F-086).

## 9. Open questions

The following remain open, in rough order of value:

1. Power-on origin of the asserted /IRQ (it is low before M2 starts, F-065, so it does not need M2). The power-on counter state is now known (CPU mode, latch `$FF`, running: F-088).
2. The chip's own output delays and margins below a few ns: the adapter's buffers add about 15 ns (F-083). Voltage levels, edge rates and DC parameters were not measured. (Setup and hold, the closing edge and the shortest window are settled: F-081, F-082; per-register transparency: F-089; back-to-back writes and read-modify-write: **[C]**, F-063.)
3. The integrated CIC (pins 15-18, the lockout function; lines on cart header J3): protocol, timing, region behaviour, whether and how it can be disabled. Nothing about it has been measured.
4. Chip-to-chip and console-to-console variation: one chip and one console were tested; the CPU/PPU alignment changes at each power-up (the G5 gap threshold of 16 cycles was seen on one alignment, so the ROM does not assert 16 and 17).
5. What pin 19 is for, and its power-on behaviour when held high from before power-up. Pin 19 and the CIC were not exercised from a console.
6. Hidden registers or bits that reach no output pin (`$A001` function, indices 10-14, `$8000` bit 4). A program in a console cannot see them either (F-062).
7. PAL consoles and Famicom differences.

Closed since v0.1: address aliasing over A1-A12 (not decoded, F-063); why exactly one interrupt appears in eight frames with both pattern tables at $1000 (latch 0 expires only once per `$C001`, F-075); when the A12-mode enable flag is tested (F-074); the PRG and CHR output delays (F-068, F-076).

## 10. Revision history

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-10-31 | First draft, from datasheet v0.3 and findings F-001 to F-054 |
| 0.2 | 2026-11-01 | Real-console confirmation (marker [C]): no reset input, aliasing and read-modify-write settled, exact linear CPU-mode timing, A12 mode with the console's PPU, interrupt line in a running picture (6.4), open questions revised; from datasheet v0.4 and F-001 to F-063 |
| 0.3 | 2026-11-01 | Logic-analyser timing (F-064 to F-072): register write transparency per register, /IRQ timing, enable/disable in the expiry cycle; from datasheet v0.5 |
| 0.4 | 2026-11-01 | A12-mode enable flag tested at the assertion fall (F-074), latch 0 expires only on the reload after `$C001` (F-075; explains the single interrupt of G6 test 11), PRG output delay (F-076); from datasheet v0.6 |
| 0.5 | 2026-11-02 | The datasheet was retired: its markers, measurement conditions and evidence index moved to `docs/findings.md`; open questions merged into section 9 and updated for F-081 to F-090 |
