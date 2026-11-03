# Tengen RAMBO-1 (mapper 64): guide for emulator authors

**DRAFT 0.5, 2026-11-02.** For people writing or fixing a NES emulator's mapper 64. Everything here was measured on one RAMBO-1
chip (337006) on a jig, with a logic analyser in one NTSC console, and on a 150 MHz RP2350 adapter; the evidence is in `docs/findings.md` (F-001 to F-090), the full description in
`docs/functional_description.md` and `docs/fpga_notes.md`. The NESdev wiki page for mapper 64 was used as a hypothesis and
re-measured, not copied. Evidence markers: **[C]** confirmed by a test ROM on real hardware, **[V]** verified on the jig,
**[I]** inferred, **[U]** unknown.

You get these:

1. The rules, short enough to implement from (sections 1 to 3), and a reference implementation, `reference/rambo1.py`
   (about 200 lines of Python, with comments naming the finding behind every rule).
2. A section for people who already have an MMC3 implementation (section 4A).
3. Six test ROMs (`rom/`) that run on the chip and print pass or fail, so you can check your implementation without
   hardware (section 5).

## 1. What a mapper 64 emulation has to get right

Most games only need the banking. The interrupt counter is where emulators differ from the chip, and a few of the
differences change which scanline a game's split lands on.

### 1.1 Registers

Decode on CPU A0, A13, A14 only, with /ROMSEL low (address $8000 or above). A1-A12 take no part: each 8 KB block has one even
and one odd register repeated through it **[C]** (F-063). Writes take the data on the bus, with no bus conflict with the ROM byte
**[C]**; read-modify-write instructions end with the final value **[C]**.

| Address | Register |
|---|---|
| $8000 | bank select: bits 3-0 index, bit 5 K (1 KB CHR mode), bit 6 P (PRG mode), bit 7 C (CHR inversion); bit 4 does nothing |
| $8001 | data for the selected index |
| $A000 | bit 0: 0 = vertical, 1 = horizontal; bits 1-7 ignored |
| $A001 | nothing visible |
| $C000 | IRQ latch |
| $C001 | bit 0: 0 = A12 mode, 1 = CPU-cycle mode; **every write restarts the counter**; bits 1-7 ignored |
| $E000 | release /IRQ and disable |
| $E001 | enable |

Index 0-5: CHR R0-R5 (8 bits). 6, 7 and 15 ($F): PRG R6, R7, RF (low 5 bits only). 8, 9: CHR R8, R9 (8 bits; they accept
writes at any time and keep the value, but only act when K = 1). Indices 10-14 store nothing visible **[C]** (F-039, F-049, F-062).
**A write to $8000 alone changes K, P and C at once**; the mapping does not wait for $8001 **[C]** (F-040): an emulator that only
rebuilds its banks on $8001 is wrong.

### 1.2 Outputs

CHR (PPU address A0-$1FFF, 1 KB windows; C inverts by XORing the window number with 4 [C] F-006):

| K | $0000 | $0400 | $0800 | $0C00 | $1000 | $1400 | $1800 | $1C00 |
|---|---|---|---|---|---|---|---|---|
| 0 | R0 | R0 | R1 | R1 | R2 | R3 | R4 | R5 |
| 1 | R0 | R8 | R1 | R9 | R2 | R3 | R4 | R5 |

In the 2 KB windows (K = 0, R0 and R1) the register's **bit 0 is replaced by PPU A10**: the bank is (R & $FE) | A10, so an odd
R0 value maps the same pair as the even value below it **[C]** (F-007). In every other window the register's bit 0 goes to CHR A10
as it is.

PRG ($8000-$FFFF, 8 KB windows): P = 0: R6, R7, RF, fixed $1F; P = 1: RF, R7, R6, fixed $1F **[C]**. Only the low 5 bits reach the
ROM (256 KB maximum).

Mirroring: CIRAM A10 = PPU A10 (vertical) or PPU A11 (horizontal) by $A000 bit 0 **[C]**.

### 1.3 Power-on and reset

After a **power cycle** **[C]** (F-001 to F-004, F-035, F-061): /IRQ is asserted (an interrupt is taken at once if I is clear, until the
program writes $E000); all three switchable PRG windows are bank $1F; every CHR window is bank 0 in the 1 KB layout (K = 1);
mirroring is vertical, whatever the iNES header says; the IRQ latch is $FF (a counter started without writing $C000 expires
after about 1026 cycles).

**The counter is already running at power-on [C] (F-088):** the chip powers up in CPU-cycle mode with latch $FF and counts M2 cycles from the first one, without any `$C001` write. Once /IRQ is enabled (`$E001`) the first expiry is at M2 cycle 1018 (1019 in some starts), counting the first cycle as 1, not 1026 as after a `$C001`. A12 pulses before the first `$C001` are ignored. The A12 filter is not full at power-on either (about 8 M2 falls after a short power cycle, fewer after seconds off, F-085), which matters only for the first pulses. A game or test ROM that enables the interrupt and does not write `$C001` within about a thousand cycles of power-on gets an interrupt there. After a reset (not a power cycle) the registers, including this counter's state, are not cleared.

**The power-on /IRQ takes seconds to appear [C] (F-079):** a released /IRQ stays released through a power-off of up to about 5 s (longer if the cart had been powered for 30 s or more), so a short power cycle may not give the asserted /IRQ; the registers clear much faster. **The supply must really collapse for the power-on state [C] (F-078):** with the cart's supply left at about 1 V (switched off but not discharged) the chip kept its registers for a minute or more; a real console that is switched off and on quickly may do the same. For an emulator this only matters if you model very short power cycles; a cold start with the supply down for a moment gives the state below.

**The console's reset button does not reset the mapper** **[C]** (F-061): registers, banks and the interrupt state stay as they were. Emulators
that reinitialise the mapper on reset are wrong for this chip.

## 2. The interrupt counter

### 2.1 CPU-cycle mode ($C001 bit 0 = 1)

With t counting M2 cycles after the cycle that wrote $C001 **[V]** (F-018 to F-019, F-028, F-031, F-054) and **[C]** (F-058):

- The first expiry is at **t = 4(L+1) + 2**, exactly linear in L for L = 0 to 255 (**no special case for L = 0 or 1**). L is the latch as it is
  5 cycles after $C001: a $C000 write up to 5 cycles after the $C001 write sets the first interval.
- Then every **4(L+1)** cycles, with the latch as it is at each expiry.
- /IRQ asserts at an expiry only if enabled; **an expiry while disabled is lost** (nothing is remembered). **A `$E000` or `$E001` write in the same CPU cycle as the expiry counts [C] (F-071, F-072):** apply the cycle's writes before the expiry check of that cycle, as `reference/rambo1.py` does.
- $E000 and $E001 do not disturb the counter. $C001 restarts it and does not release an asserted /IRQ.
- **Early first expiry [V] (F-087, G4 test 13 on the console):** if the mode is switched from A12 to CPU while the A12 filter is below 16 (A12 high or toggling in the last 16 M2 cycles), the first expiry is at t = 4(L+1) - 2, four cycles earlier. A CPU to CPU rewrite is not early, and neither is a switch with the filter full. The reference model does this.

### 2.2 A12 mode ($C001 bit 0 = 0)

The chip counts **M2 falling edges** and looks at PPU A12 at each (F-022, F-023, F-050 to F-052 [V]; [C] F-059):

```
filter: at every M2 fall
    if A12 is low:  if filter < 16, filter += 1            (a value of 17 stays 17 while A12 is low)
    if A12 is high: if filter == 16 then clock the counter; filter = 0
$C001 write (either mode): if filter == 16 then filter = 17    ("filter full": the next rise does not clock)
clock:  if reload_flag:     counter = latch, reload_flag = 0, expire = (counter == 0)   (the latch is read here, F-038)
        elif counter == 0:  counter = latch, expire = 0   (the automatic reload at zero never expires: matters only for L = 0, F-075)
        else:               counter -= 1, expire = (counter == 0)
        if expire: /IRQ is to assert at the next M2 fall (one fall after the clocking fall, F-050)
at that next M2 fall: /IRQ goes low only if the interrupt is enabled NOW, after the writes of that cycle (F-074)
$C001 write (A12 mode): reload_flag = 1
```

Consequences you can check against the tests:

- With a full filter at $C001 the **first** A12 pulse after the write is swallowed, so the first interrupt comes on **pulse L+2**,
  then every L+1 pulses. The first expiry at L+2 holds for L = 0 and 1 too, and the period L+1 for L >= 1 **[C]** (F-021, F-055, F-056, F-059); **with L = 0 there is only the one expiry per `$C001`** (F-075, below).
- With the filter not full (fewer than 15 M2 falls with A12 low before the write) the first pulse counts: **pulse L+1** **[V]** (F-052, F-055).
- 16 M2 falls with A12 low are needed before a rise; 15 are not enough. On the test console a gap of 13 or 15 cycles never counted and 16 to
  24 always counted. The adapter confirmed exactly 16 for M2 periods of 300 to 1500 ns; the filter counts M2 falls, not time, and an A12 glitch between falls does not count (F-084, F-081).
- A $C000 written before the first counted pulse sets the first interval; written later it is used from the next reload **[C]** (F-038).
- **The enable flag is tested one fall after the clocking fall [C] (F-074):** an `$E001` written in the clocking cycle or in the next cycle enables the interrupt in time; an `$E000`
  written in either cycle prevents it (the chip does not remember an expiry that happened while disabled). A write one cycle later is too late. In CPU mode the flag is tested at the expiry fall itself (F-071).
- **Latch 0 is special [C] (F-075):** only the reload that follows `$C001` expires. After that, with L = 0, the pulses do not expire again until the next `$C001` (the automatic reload at zero does not expire).
  Latches 1 and above are unaffected (period L + 1). An emulator that expires on every reload to 0 gives an interrupt on every line for L = 0; the chip gives one.
- A12 mode ignores A12 edges while CPU mode is selected, and a mode switch carries nothing over: a pending CPU-mode expiry is
  cancelled by a $C001 write of 0 up to 21 cycles after the CPU-mode write (**[V]** F-057), and A12 then expires at pulse L+2 (**[C]**).

### 2.3 The /IRQ line

/IRQ is sticky: once low it stays low until a write to $E000 (which also disables). $E001 only enables and does not release it. $C001 never
releases it **[C]** (F-020, F-025, F-029, F-030, F-063).

## 3. Wiring it to an emulated PPU

The A12 counter sees whatever the PPU does on its address bus, so the mapper is only as right as your PPU's A12 behaviour. What the chip
needs from the PPU:

1. **Sample A12 at the middle of each CPU cycle** (the M2 fall) and call the filter once per CPU cycle. A cheaper scheme is fine if it gives
   the same pulse sequence.
2. **One counted pulse per line:** with sprites at $1000 and background at $0000 the rise is at dot 260 of each line; the shorter A12 toggles
   inside a sprite fetch are removed by the 16-fall filter. Rendering lines are 0-239 **and the pre-render line (261)**, so a frame has
   **241 counted pulses** **[C]** (F-060). With latch L, 8 frames give floor((8 x 241 - (L+2)) / (L+1)) + 1 interrupts (120 for L = 15,
   240 for L = 7, 15 for L = 127); CPU mode with L = 255 gives 232 interrupts in 8 frames.
3. **The idle PPU bus keeps A12 where the last fetch left it.** With sprites at $1000 the last fetch of a frame is a background
   prefetch at $0000, so A12 is low through vblank and a $C001 written there swallows the pre-render pulse: the interrupt is on line
   L. With **background at $1000 and sprites at $0000** the last fetch is at $1xxx, A12 stays high through vblank, the filter is
   not full, the first pulse counts, and the interrupt arrives **one line earlier** (line L-1) **[C]** (F-060). An emulator that
   forces A12 low outside rendering gets this wrong by one line.
4. In that second configuration the rise is at about dot 324 (the prefetch for the next line), not 260.
5. Both tables at $0000: no A12 rise, no interrupt. Both at $1000: A12 is almost always high; one interrupt in eight frames was seen
   with L = 0. That is the latch 0 rule of section 2.2 **[I]** (F-075): the counter expires only on the reload after `$C001`, so one counted pulse gives the one interrupt (MesenCE counts 8).
6. **What the real PPU waveform looks like** (logic analyser, F-065): in the usual configuration A12 is high for about 750 ns at each of the eight sprite fetches of a line, with 1 or 2 M2 cycles
   of low between them, then low for about 93 M2 cycles (the background fetches) before the next line's first sprite fetch. Only that last rise is counted; nothing in a real
   frame lies between 2 and 93 low M2 cycles, so any filter threshold in that range gives the right result in normal rendering (the chip's is 16). In vblank A12 stays low. There are 241 counted rises
   per frame, 22 lines apart across vblank.
7. **/IRQ timing:** /IRQ falls at the second M2 fall after the A12 rise (the first M2 fall with A12 high clocks the counter), about 8 ns later (F-065). For a CPU-visible interrupt that is one CPU cycle after the clocking cycle.
8. With rendering off, A12 follows the PPU address (writes to $2006 put bit 12 of the address on the bus), which is how the test ROMs
   make pulses.

The interrupt in the usual configuration arrives in the horizontal blank after the visible pixels of the line: a handler that
writes PPUMASK first thing changes the picture from the next line (the raster demo in G6 does this).

A lazy implementation is possible: for CPU mode keep the cycle number of the next expiry (4(L+1)+2 after $C001, then every 4(L+1)) and
compare it at every CPU cycle; for A12 mode keep the filter as a count of M2 falls since the last fall seen with A12 high.

## 4. Reference model

`reference/rambo1.py` is the whole chip as a state machine: `write(addr, value)` for CPU writes, `cycle(a12)` once per M2 cycle,
and `prg_bank()`, `chr_bank()`, `ciram_a10()`, `prg_ce()`, `irq` as outputs. `reference/test_rambo1.py` checks it against the
findings (38 checks, run `python3 -I reference/test_rambo1.py`). `rom/tools/hwsim.py --model ref` runs the test ROMs on a small 6502
harness with the reference model as the chip: all six pass. Use it as an oracle for differential testing of your own mapper.

Conventions: within a CPU cycle, CPU writes come first, then `cycle(a12)` for the M2 fall. The model's t counts the `cycle()` calls
after the one that ends the write cycle. Within a cycle the order is settled for `$E000`/`$E001` against a CPU-mode expiry **[C]** (F-071, F-072). Propagation delays are in `docs/timing_measurements.md` and `docs/fpga_notes.md`; setup and hold of the A12 sample and of register writes are under 10 ns (F-081, F-082), too short to matter for an emulator.

## 4A. Starting from an MMC3 implementation

The RAMBO-1 is Tengen's answer to the MMC3 and shares its register layout, so an existing MMC3 (mapper 4) implementation is a good base. This section lists what to change. **The RAMBO-1 side is measured (finding numbers given). The MMC3 side is the behaviour as usually documented on the NESdev wiki and implemented in emulators; this project did not measure an MMC3**, and MMC3 revisions differ in the details marked (rev).

### 4A.1 What stays the same

- Register decode on CPU A0, A13, A14 with /ROMSEL low, even/odd pairs at `$8000`, `$A000`, `$C000`, `$E000` (F-063). No bus conflicts.
- `$8000` bit 7 (C) swaps the two 4 KB CHR halves; `$8000` bit 6 (P) selects the PRG layout; `$A000` bit 0: 0 = vertical, 1 = horizontal (bits 1-7 ignored).
- With K = 0 (bit 5 clear) the CHR map is the MMC3's: R0 and R1 are 2 KB windows whose bit 0 is replaced by PPU A10, R2-R5 are 1 KB windows (F-006, F-007).
- `$E000` releases /IRQ and disables; `$E001` enables and does not release it; /IRQ is sticky (F-029, F-030). `$C000` is the reload latch.
- In A12 mode the counter clocks on filtered rising edges of PPU A12, reloads from the latch when it is zero, and expires on the clock that brings it to zero.

### 4A.2 Register differences

| | MMC3 | RAMBO-1 |
|---|---|---|
| `$8000` index | bits 2-0 (R0-R7) | **bits 3-0**: R0-R5, R6, R7, **R8, R9, RF (index 15)**; indices 10-14 store nothing (F-039, F-049) |
| `$8000` bit 5 | unused | **K: 1 KB CHR mode** (see below) |
| `$8000` bit 4 | unused | does nothing (F-040) |
| `$8000` timing | | K, P, C and the index take effect **at the `$8000` write itself**, not at the next `$8001`. Rebuild your banks on `$8000` too |
| R6, R7 | 6 bits | **5 bits** (low 5 only reach the ROM, 256 KB maximum) (F-010) |
| `$A001` | PRG RAM enable / write protect | **nothing visible** (F-042, F-053). Do not map a RAM-protect function |
| `$C001` | reload only; the mode never changes | **bit 0 selects the clock source** (0 = A12, 1 = CPU cycles), and every write restarts the counter in the selected mode. Bits 1-7 ignored (F-024, F-026, F-057) |

**K (1 KB CHR mode)** turns the two 2 KB windows into four 1 KB windows, using the new registers R8 and R9:

| K | $0000 | $0400 | $0800 | $0C00 | $1000-$1FFF |
|---|---|---|---|---|---|
| 0 (MMC3) | R0 | R0 (bit 0 = A10) | R1 | R1 (bit 0 = A10) | R2, R3, R4, R5 |
| 1 | R0 | **R8** | R1 | **R9** | R2, R3, R4, R5 |

In K = 1 the full 8-bit register goes to CHR A17-A10, bit 0 included. R8 and R9 accept writes whatever K is, and keep the value, but only act when K = 1. The C bit XORs the window number with 4 as on the MMC3.

### 4A.3 PRG banking

| P | `$8000` | `$A000` | `$C000` | `$E000` |
|---|---|---|---|---|
| MMC3, P = 0 | R6 | R7 | fixed second-last | fixed last |
| MMC3, P = 1 | fixed second-last | R7 | R6 | fixed last |
| RAMBO-1, P = 0 | R6 | R7 | **RF** | **fixed $1F** |
| RAMBO-1, P = 1 | **RF** | R7 | R6 | **fixed $1F** |

Three differences: the "second-last" window is a third **switchable register (RF)**, not a fixed bank; the last window is the constant `$1F` (the chip has only 5 PRG address lines), so a 128 KB ROM does not see "the last bank" there unless the program arranges it; and the banks are 5 bits. The A13/A14 outputs follow the CPU address even without /ROMSEL (F-011, F-076), which is invisible to software.

### 4A.4 The interrupt counter

Most of the work is here. The A12-mode counter looks like an MMC3's but differs in several measured ways:

| | MMC3 (as commonly emulated) | RAMBO-1 |
|---|---|---|
| A12 filter | rising edge counts if A12 was low for a few M2 cycles (about 3, rev-dependent) | **A12 must be low at 16 consecutive M2 falls**; 15 is not enough. The threshold does not depend on the M2 period (F-022, F-084). The chip samples A12 at the M2 **fall** only; a glitch between falls is ignored (F-081) |
| After `$C001` | counter cleared; the next clock reloads from the latch, so the IRQ is on clock **L+1** | `$C001` also marks the filter "full, next rise does not clock" (**17**): if the filter was full, the **first pulse is swallowed** and the IRQ is on pulse **L+2**; if the filter was not full (fewer than 15 low falls before the write), pulse L+1 (F-052, F-055). Emulate this with a filter counter, not a boolean |
| Latch 0 | (rev) IRQ on every clock | **one expiry per `$C001`** (the reload that follows `$C001`); after that no expiry until the next `$C001` (F-075). Latch 1 and up: period L+1 as on the MMC3 |
| /IRQ timing | at the clock | **one M2 fall after the clocking fall**, and only if the interrupt is enabled at that fall: an `$E001` in the clocking cycle or the next one is in time, an `$E000` in either prevents it (F-050, F-074) |
| Expiry while disabled | lost | lost (F-031) |
| CPU-cycle mode | none | **new**: first expiry 4(L+1)+2 M2 cycles after the `$C001` cycle, then every 4(L+1), latch read at each expiry (F-018, F-019, F-028). Linear for every L, no special case for 0 or 1. `$E000`/`$E001` in the expiry cycle count (F-071, F-072). The one subtle case: an A12 to CPU switch while the A12 filter is below 16 expires 4 cycles early (F-087) |
| Mode switch | not applicable | nothing carries over; a pending CPU-mode expiry is cancelled by an A12-mode `$C001` (F-057) |

Because the filter is counted in M2 falls, an emulator that feeds the mapper only A12 rising edges must also tell it how many M2 cycles A12 had been low. section 3 shows how to wire this from the PPU; `reference/rambo1.py` has `cycle(a12)` (called once per M2 fall with the A12 level) as the model to copy.

### 4A.5 Power-on and reset

MMC3 emulators usually start with arbitrary or zeroed registers. The RAMBO-1 has a measured state (section 1.3): PRG R6, R7, RF all `$1F`, CHR registers 0 with **K = 1**, vertical mirroring, latch `$FF`, **/IRQ asserted**, and the counter already running in CPU-cycle mode (first expiry at M2 cycle about 1018). The reset button changes nothing in the mapper (F-061).

### 4A.6 Porting checklist

1. Widen the `$8000` index to 4 bits; add R8, R9, RF; add K; rebuild banks on every `$8000` write.
2. Change the PRG layout to R6/R7/RF/`$1F` (P = 0) and RF/R7/R6/`$1F` (P = 1); mask banks to 5 bits.
3. Remove PRG RAM protect from `$A001`.
4. Make `$C001` a mode and restart register; add CPU-cycle mode.
5. Replace the A12 edge filter by the 16-fall filter, with the 17 "swallow" state set by `$C001`.
6. Delay the A12-mode /IRQ by one M2 fall, test the enable flag at that fall, and give latch 0 one expiry per `$C001`.
7. Apply the power-on state of section 1.3.
8. Run the test ROMs (section 5): G2 covers the CHR/PRG banking, G4 the CPU mode, G5 and G6 the A12 mode.

## 5. The test ROMs

`rom/build/*.nes` (source and `make` in `rom/`; needs cc65). iNES 2.0, mapper 64, 256 KiB PRG and 256 KiB CHR, header mirroring horizontal on
purpose. Each ROM prints a list on screen and puts its result in RAM so that a headless emulator can read it:

| Address | Meaning |
|---|---|
| $0300 | status: $80 while running, $00 all passed, else the code of the first failing test |
| $0301-$0303 | `DE B0 61` (signature) |
| $0304... | the report text, zero-terminated |

The screen is green when all passed and red otherwise; the beeper gives one beep for a pass or N beeps for failure code N. A test that
depends on another that failed is shown as SKIP. A failing line is followed by `CODE cc GOT gg EXP ee AT aa`.
`INFO` lines are discovery output and never failures. (G1 to G5 take only a few frames of emulated time; G6 needs 380.)

| ROM | Tests | Needs | Frames to finish |
|---|---|---|---|
| `g1_power_on` | power-on state | a power cycle (a reset gives false failures) | a few |
| `g2_banking` | banking, widths, R8/R9, unused indices, mirroring | any start | a few |
| `g3_bus` | no bus conflict, read-modify-write, aliasing, /ROMSEL, reads | PRG ROM output enable = RAMBO /CE (always true in an emulator) | a few |
| `g4_cpu_irq` | CPU-cycle IRQ to one cycle, races in the expiry cycle, early expiry after a mode switch | any start | a few |
| `g5_a12_irq` | A12-mode IRQ, filter, latch timing, mode switches | any start | a few |
| `g6_raster` | rendering: interrupt line, PPU configurations, counts, demo | any start | about 380 (6 s, of which the demo is 4 s) |

To read the result from an emulator, read $0300 after 450 frames (G6) or 60 frames (the others). `rom/tools/run_checks.sh` runs all six on the software models of the chip. Expected result on the chip: every test passes
(G6 includes the A12-line-offset INFO `00 28 98`).

Two things to know when reading failures: the tests were designed to fail in emulators that copy the NESdev description; a failure in
an emulator is expected wherever it follows the NESdev description instead of the rules in sections 1 and 2. G4 and G5 measure by interrupt timing, so an emulator with an approximate
interrupt delivery (for example one that polls /IRQ once per instruction at the wrong cycle) can fail them for reasons outside the mapper.

## 6. Not known

- Anything finer than one M2 cycle other than the delays in `docs/timing_measurements.md` and `docs/fpga_notes.md`. Setup and hold are under 10 ns (F-081, F-082); the chip's own output delays, voltage levels and edge rates are not known.
- **Not covered by the test ROMs:** F-074 (in A12 mode the enable flag is tested one M2 fall after the clocking fall) was found with the timing probe and a logic analyser; no test ROM checks it, and none can from the CPU side (analysis in `docs/test_rom_design.md` section 17); `reference/test_rambo1.py` (`A12EnableTiming`) does.
  F-071, F-072 and F-075 are checked by G4 tests 11 and 12 and G5 tests 11 and 12, which pass on the console (F-077); F-087 by G4 test 13, also confirmed on the console. An emulator can be checked against all of them with `reference/test_rambo1.py`.
- The CIC (pins 15-18) and pin 19 behaviour from a console.
- Chip-to-chip variation (one chip tested), PAL timing (an NTSC console only), and multi-console CPU/PPU alignment effects.

## 7. Revision history

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-11-01 | First draft: rules, PPU interface, reference model, emulator differences, test ROM usage |
| 0.2 | 2026-11-01 | Findings to F-072; the write order within a cycle for `$E000`/`$E001` is confirmed (F-071, F-072); pointers to the timing measurements and FPGA notes |
| 0.3 | 2026-11-01 | A12 mode: the enable flag is tested one fall after the clocking fall (F-074); latch 0 expires only on the reload after `$C001` (F-075); reference model and clock pseudo-code changed |
| 0.4 | 2026-11-02 | New section 4A for MMC3 implementers (differences and a porting checklist); findings to F-090 |
| 0.5 | 2026-11-02 | Section 5 (existing emulators against the chip) removed; later sections renumbered; F-085 and F-087 added to sections 1.3 and 2.1; stale statements about setup and hold, the filter and the check count corrected |
