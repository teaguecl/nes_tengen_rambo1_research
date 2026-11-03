# RAMBO-1 notes for FPGA implementers

**DRAFT 0.3, 2026-11-02.** For engineers building a hardware replacement for the Tengen 337006 (iNES mapper 64) that must work in a real NES or Famicom. Read
`docs/functional_description.md` for the behaviour and `reference/rambo1.py` for the state machine; this document adds what an HDL design needs: which parts are clocked, which are
combinational, and every nanosecond figure we have. Source of each number: the finding ID in brackets (`docs/findings.md`, F-001 to F-090).

**How far to trust this.** One chip, one console (NTSC), one temperature, a 24 MHz / 48 MHz USB logic analyser (+-5 ns, `docs/timing_measurements.md` section 1), an Arduino
jig with microsecond resolution, and an RP2350 adapter that places bus edges to 6.7 ns (its buffers add about 15 ns to every output). No manufacturer data, no scope, no voltage or edge-rate measurements. Confidence tags: **[C]** confirmed in a console, **[V]** verified on the jig only,
**[I]** inferred, **[U]** unknown.

## 1. What the chip is, for an HDL

- **There is no clock input other than M2.** Everything happens on levels of M2, R/W and /ROMSEL, and on **M2 falling edges** (the only clocked events found).
- **Three kinds of logic:**
  1. *Write path:* level-enabled latches for the registers (section 3).
  2. *Combinational outputs:* PRG A13-A17, CHR A10-A17, CIRAM A10, PRG /CE (section 4).
  3. *Counter and /IRQ:* advances on M2 falling edges (section 5).
- State that survives: the registers, the IRQ latch, the counter, the A12 filter (0..17), mode and enable flags, the /IRQ flip-flop. Nothing is reset by the console's reset button [C] (F-061).

## 2. Pins and how each is used

| Pin(s) | Signal | Dir | Used for | Class |
|---|---|---|---|---|
| 1 | M2 | in | write enable level, counter and filter clock (falling edge), /CE gate | clock |
| 7, 38, 36 | CPU A0, A13, A14 | in | register select (A1-A12 are not decoded [C], F-063); PRG window select | write path, comb. |
| 10 | CPU R/W | in | write enable; /CE gate | level |
| 11 | /ROMSEL | in | write enable; /CE gate | level |
| 33, 32, 9, 31, 8, 34, 6, 35 | CPU D0-D7 | in | register data | write path |
| 13, 27, 14 | PPU A10, A11, A12 | in | CHR/CIRAM select; A12 drives the scanline counter | comb. + clocked |
| 4, 37, 3, 2, 39 | PRG A13-A17 | out | bank number for the 8 KB window selected by CPU A13/A14 | comb. |
| 5 | PRG /CE | out | low only for M2 = 1, R/W = 1, /ROMSEL = 0 | comb. |
| 12, 28, 25, 26, 24, 23, 21, 22 | CHR A10-A17 | out | bank number for the 1 KB window selected by PPU A10-A12 | comb. |
| 29 | CIRAM A10 | out | PPU A10 (vertical) or PPU A11 (horizontal) | comb. |
| 30 | /IRQ | out | low = asserted; the cart has a 10 k pull-up, so open-drain is likely **[U]** | clocked |
| 19 | (pin 19) | in | tied to GND on the original board; when high every register write stores `$0B` [V] (F-046). Tie low. | |
| 15-18 | CIC | | not characterised | |

## 3. The write path

**Enable:** `write_en = M2 & ~R/W & ~/ROMSEL` is a level, not an edge, in any order [V] (F-013). The register is chosen by A0, A13, A14 as they are during the window [V] (F-016). The address decode
(`$8000/1`, `$A000/1`, `$C000/1`, `$E000/1`; A0 = 0 or 1) is in `reference/rambo1.py`, method `write`.

**What the console does to the data.** The CPU puts the byte on the bus late: in the traces the bus still holds the previous byte (the instruction's address high byte) when the window opens and the new byte arrives
about 100 ns after /ROMSEL falls [C] (F-066, F-070), and it is stable for at least 200 ns before M2 falls [C] (F-069). A design that follows the data line, or one that latches at the end of the cycle, both work with this.
The chip needs no hold after the closing edge: the adapter found hold under 10 ns (F-082), although a console's bus does stay valid a little after M2 falls.

| Register | Behaviour | Delay | Source |
|---|---|---|---|
| `$A000` mirroring | **transparent**: the output follows D0 while the window is open | 13 ns after /ROMSEL falls if the bus byte is already right; about 3 ns behind D0 | [C] F-066 |
| `$8001` bank data | **transparent for the CHR registers (R0-R5, R8, R9); R6, R7, RF are not (F-089)** | 20 ns after /ROMSEL falls if the bus byte is already right; 10 ns behind the data line | [C] F-070 |
| `$8000` control (K, P, C, index) | **takes effect only at the end of the cycle**, not transparent | 14.7 to 15.1 ns after M2 falls (0 to 1 ns after /ROMSEL rises) | [C] F-069 |
| `$E000` acknowledge | /IRQ released inside the window | 130 ns after /ROMSEL falls, about 200 ns before M2 falls (455 of 455) | [C] F-067 |
| `$E001` enable, `$E000` disable (for the expiry decision) | CPU mode: in effect for the expiry decided at the M2 fall of the **same** cycle; a write one cycle later is too late (5,638 blocks, no exceptions). **A12 mode: tested at the fall one after the clocking fall**, so a write in the clocking cycle or the next cycle counts | the flag changes at least 200 ns before that M2 fall | [C] F-071, F-072, F-074 |
| `$C000`, `$C001`, `$A001` | internal; effects are seen only through the counter | not measured on a console | [U] |

What the figures say for a design: the control register must not be transparent (a data glitch in the window would glitch the CHR outputs in a console where the byte arrives late), and the data registers may be either: the CHR registers and `$A000` are transparent on the chip, R6, R7 and RF are latched at the close (F-089), and a console only ever shows a stable byte at the end of the cycle. **Which edge closes the window is now measured (F-082, adapter):** the first of the M2 fall, the /ROMSEL rise and the R/W rise, and the data present at that instant is stored (setup and hold each under 10 ns; a 7 ns window is enough). See "Adapter measurements" below.

**Console timing around the write** (M2 period 558.9 ns, high phase about 363 ns) [C] (F-064): /ROMSEL falls 28.2 ns after M2 rises and rises 13.2 ns after M2 falls. The write window is therefore about 350 ns long.
**PRG /CE stays high in every write cycle** (66,750 samples, none low) [C] (F-066).

**Register contents.** Power-on state (all [V] jig, F-001 to F-004; [C] on a console for /IRQ and the PRG bank at boot, G1): PRG windows all bank `$1F`; CHR registers 0 with the 1 KB layout (K = 1); vertical mirroring; latch `$FF`; /IRQ asserted;
IRQ disabled; the counter is already running in CPU-cycle mode (section 5, F-088). R6, R7, RF keep 5 bits; R8, R9 accept writes even when K = 0; indices 10-14 store nothing visible; `$8000` bit 4 does nothing; `$A000` keeps bit 0 only; `$A001` has no visible effect. See the model.

### Adapter measurements (RP2350 adapter, 150 MHz PIO, 6.7 ns steps; F-081 to F-090)

The adapter replays bus cycles with timing set to a few ns. Its input buffers add about 15 ns to every output, so output delays are upper bounds.

| Topic | Result | Source |
|---|---|---|
| Window close | The window is the AND of M2 high, R/W low and /ROMSEL low. It closes at the first of M2 fall, /ROMSEL rise, R/W rise; the data at that instant is stored. Setup and hold under 10 ns; a 7 ns window is enough | F-082 |
| Which registers are transparent | Transparent while the window is open: R0-R5, R8, R9 (CHR) and `$A000`. Not transparent (updated at the close): R6, R7, RF. `$8000` takes effect at the end of the cycle (F-069) | F-089, F-066, F-070 |
| A12 sampling | In A12 mode A12 is sampled at the M2 fall. A pulse counts if and only if A12 is high at the fall (setup and hold under 10 ns). The 41 to 83 ns console figure was an analyser artefact | F-081 |
| A12 filter | Counts M2 falls only. Exactly 16 low falls are needed, for M2 periods of 300 to 1500 ns; no time-based fill; an A12 glitch between falls is ignored | F-084 |
| Combinational outputs | PRG A13-A17, CHR A10/A11/A15-A17, CIRAM and /CE respond in 13.3 to 20 ns through the adapter (rising 13.3, falling up to 20). The chip's own share is a few ns, unresolved | F-083 |
| Reads of the register addresses | No effect at all (registers, outputs, counters, /IRQ) | F-086 |
| Power-on filter | The A12 filter is not full at power-on: about 8 falls after 0.2 to 1 s off, 5 after 2 s, 4 after 5 s, 3 after 10 s, 2 after 30 s | F-085 |
| Power-on counter | The chip powers up in CPU-cycle mode with latch `$FF` and the counter running: with only `$E000` and `$E001` written the first /IRQ falls at M2 fall 1018 (500 ms off) or 1019 (5 or 30 s off). A12 pulses before the first `$C001` do nothing | F-088 |
| A12 to CPU switch | If the A12 filter is below 16 at the `$C001` write, the first CPU-mode expiry comes 4(L+1)-2 cycles after the write, not 4(L+1)+2 | F-087 |
| Enable-flag instant | The flag is a level set as soon as the write acts and is tested at the M2 fall to within about 7 ns; a window closing up to 150 ns before the fall still counts, one opening 5 ns or more after it does not | F-090 |

## 4. The combinational outputs

All of these depend only on registers and input address lines, with no clock.

- **PRG A13-A17** follow CPU A13/A14 through the three PRG registers and the P bit, **even when /ROMSEL is high** [V] (F-011); only /CE gates the ROM. **Combinational within about 8 ns of the CPU address [C] (F-076)**: rising outputs 0 to 2 ns, falling 6 to 8.5 ns, the five outputs equal within about 2 ns.
- **CHR A10-A17 and CIRAM A10 follow PPU A10-A12 within about 10 ns** [C] (F-068): PPU A10 rising to CHR A10 rising 4 to 5 ns, to CIRAM A10 1 ns; PPU A12 falling to CHR A10/A11/A17 6 to 7 ns, equal within 1 ns.
  When several PPU lines change together the output follows the first line that moves (the intermediate address selects a different window). An FPGA must not add a registered stage here.
- **PRG /CE** `= M2 & R/W & ~/ROMSEL` (active low) [C] (F-064): falls 3.9 ns after the later of M2 rising and /ROMSEL falling, rises 7.1 ns after M2 falls, about 6 ns before /ROMSEL rises. /CE is low for about 340 ns of the
  559 ns cycle, which is the ROM access time an FPGA design must deliver bank outputs within.

## 5. The IRQ counter and /IRQ

The counter has two modes, switched by `$C001` bit 0. Both advance **on the M2 falling edge**, and `reference/rambo1.py` method `cycle()` is the executable specification. In summary:

- **A12 filter [C] (F-022, F-051, F-065):** at each M2 fall, if A12 is low the filter counts up to 16; if A12 is high, the counter is clocked when the filter is exactly 16 (not in CPU mode), and the filter resets to 0. A `$C001` write
  sets the filter 16 to 17 (so the first rise is swallowed). The real PPU produces two kinds of A12 rise: sprite-fetch toggles preceded by 1 or 2 low M2 falls (never counted) and one rise per line preceded by 93 or 94 low
  M2 falls. Any threshold from 3 to 92 would behave the same in a console; 16 was measured on the jig and confirmed by the adapter, which also showed that it counts M2 falls (not time: the same 16 for M2 periods of 300 to 1500 ns) and ignores A12 glitches between falls (F-084). A12 high pulse width in a sprite fetch is about 750 ns [C].
- **A12 counter:** reload from the latch on the first clock after `$C001` or at 0, else decrement; expiry on the clock that brings it to 0 (pulse L+2 after `$C001` with a full filter, L+1 otherwise, period L+1).
  The latch is read at the reload [V] (F-037, F-038, F-055, F-056).
- **CPU-cycle counter [C] (F-018, F-019, F-028, F-058, F-067):** after `$C001` with bit 0 set, the first expiry is `4(L+1)+2` M2 cycles later, with the latch captured 5 cycles after the write; then every `4(L+1)` using the latch at
  that time. In a console with latch 40 the period was 164.0 cycles exactly (455 interrupts, spread under 0.1 cycle). **One exception [V] (F-087):** an A12 to CPU switch with the A12 filter below 16 at the `$C001` write makes the first expiry come 4(L+1)-2 cycles after the write (4 cycles early); a CPU to CPU rewrite is not early.
- **Enable flag in A12 mode [C] (F-074):** tested at the fall at which /IRQ falls (one M2 fall after the clocking fall), not at the clocking fall: an `$E001` written in either of those two cycles enables it in time, an `$E000` written in either prevents it. Latch 0: only the reload after `$C001` expires, not the automatic reload at zero (F-075).
- **A12 sampling [C] (F-074):** an A12 rise less than 41 ns before the M2 fall still counted at that fall; the A12 level from 0 to 83 ns after the fall gave the same result as at the fall (one alignment only). **Superseded by the adapter (F-081):** the chip samples A12 at the M2 fall only, with setup and hold under 10 ns; the 41 to 83 ns console figure was an analyser artefact.
- **/IRQ output:** asserts (falls) **one M2 fall after the clocking or expiry fall** in A12 mode (F-050) and **10 ns after an M2 fall** in CPU mode [C] (F-067) and about 8 ns in A12 mode [C] (F-065). It is only asserted if
  the counter is enabled when it expires; an expiry while disabled is lost [V] (F-031). `$E000` releases /IRQ and disables, leaving the counter alone (F-029); `$E001` enables only (F-030); `$C001` never releases /IRQ (F-025).
  A CPU to A12 mode switch cancels a pending expiry (F-057).
- **/IRQ at power-on [C] (F-079):** the asserted state appears only after the supply has been off for a long time (about 6 s after a short soak, more than 10 s after a long one: it is a slowly decaying stored state, not a reset); an FPGA design starts with /IRQ asserted at configuration.
- **Power-on reset [C] (F-078):** the original chip has no reset that clears its registers while VCC is still around 1 V: its state survived a minute with the rail at about 1 V and was cleared only when the rail was discharged (200 ms off was enough). An FPGA design should reset on configuration and need not model the retention.
- **Reads [V] (F-086):** reads of the eight register addresses change nothing (registers, outputs, counters, /IRQ); an FPGA needs no read side effects.
- **Power-on state of the counter [V] (F-085, F-088):** the chip powers up in CPU-cycle mode with latch `$FF` and the counter already running; with only `$E000` and `$E001` written the first /IRQ falls at M2 fall 1018 or 1019. The A12 filter is not full at power-on (about 8 falls after a short power cycle, 2 to 5 after seconds off), so the first A12 pulses can count early.
- **Power-on:** /IRQ is already low in the first sample the analyser sees, 21 ms before M2 starts [C] (F-065), so the asserted state is set without M2 (a power-on reset of that flip-flop, or an analog start-up condition). Reset an FPGA
  /IRQ flip-flop to asserted at configuration, and do not use the console reset button for anything.

## 6. A starting structure for the HDL

1. Do not put input synchronisers or registers on the combinational paths (section 4): they add delay. Synchronise only on the counter side.
2. Counter side: run from M2 falling edge directly or from a fast clock with an edge detector. Sample PPU A12 as it is just before M2 falls (the model's `a12` argument is the level at the M2 fall).
3. Write side: latches enabled by `write_en`; every register stores the data present at the first closing edge (M2 fall, /ROMSEL rise or R/W rise, F-082). The CHR data registers and `$A000` are also transparent while the window is open; R6, R7, RF and `$8000` are not (F-089, F-069).
4. /IRQ: a flip-flop set on the clock of an M2 fall, one fall later in A12 mode, cleared by `$E000` while the window is open. Observed ordering: asserted 10 ns after an M2 fall, released 130 ns after /ROMSEL falls in the console (80 ns on the adapter, F-080).
5. Reset: configuration-time values from section 3, plus CPU-cycle mode with latch `$FF` and the counter running (F-088), and a partly filled A12 filter if you want to match a freshly powered chip (F-085); no input resets anything else.

## 7. How to check an FPGA against the chip

- **Behaviour:** the six test ROMs (`rom/`, `rom/README.txt`) run in a console and give a pass/fail screen; the same ROMs pass on the real chip (G1 to G6, 62 tests). Run them in a power cycle for G1.
- **Adapter-level timing:** the RP2350 adapter tools in `firmware/rp2350_jig/tools/` (E2 to E10) place bus edges to 6.7 ns and read the outputs; they apply to the original chip and to a replacement alike, and were used for the figures marked F-081 to F-090. Run them with the cart out of the console and the safety rules in `hardware/README.md`.
- **Timing:** the timing probe (`rom/timing_probe.s`, `docs/logic_analyzer_guide.md` section 10) repeats the write, IRQ and CHR patterns. Capture an FPGA cart with the same leads and run
  `tools/la_p1_analysis.py` (mirroring writes), `la_p2_analysis.py` (control writes), `la_p3_analysis.py` (IRQ), `la_p5_analysis.py` (CHR/CIRAM), `la_p6_analysis.py` (bank data) and compare with the table in section 8.

## 8. All the figures in one table

| Quantity | Value | Source |
|---|---|---|
| M2 period / high phase (NTSC) | 558.9 ns / about 363 ns | F-064 |
| /ROMSEL falls after M2 rises / rises after M2 falls | 28.2 ns / 13.2 ns (console decode) | F-064 |
| PRG /CE falls after later of M2 rise, /ROMSEL fall / rises after M2 falls | 3.9 ns / 7.1 ns | F-064 |
| CPU data byte valid after /ROMSEL falls / stable before M2 falls | about 100 ns / at least 200 ns | F-066, F-069 |
| CIRAM A10 behind a `$A000` write / behind D0 | 13 ns after /ROMSEL falls if already right / about 3 ns | F-066 |
| CHR A11, A17 behind a `$8001` write | 20 ns after /ROMSEL falls if already right / 10 ns behind the data line | F-070 |
| CHR A11, A17 after a `$8000` write | 14.7 to 15.1 ns after M2 falls, not transparent | F-069 |
| CHR/CIRAM behind PPU A10-A12 | about 1 to 12 ns, single-line changes 1 to 7 ns | F-068 |
| PRG A13-A17 behind CPU A13/A14 | rising 0 to 2 ns, falling 6 to 8.5 ns | F-076 |
| /IRQ asserts after an M2 fall (CPU mode / A12 mode) | 10 ns / 8 ns | F-067, F-065 |
| /IRQ released by `$E000` | 130 ns after /ROMSEL falls in the console, 80 ns when driven by the adapter (both inside the window; includes the rise of an open-drain output through its 10 k pull-up, load dependent); independent of the data timing | F-067, F-080 |
| CPU-mode period / first expiry | 4(L+1) M2 cycles (164.0 for L = 40) / 4(L+1)+2 | F-058, F-067 |
| A12 filter | 16 M2 falls (jig and adapter); a console cannot separate 3 to 92 | F-051, F-065, F-084 |
| A12 pulse width in a sprite fetch / counted pulses per frame | 750 ns / 241 | F-065 |
| Write window: closing edge / setup, hold / shortest window | first of M2 fall, /ROMSEL rise, R/W rise / each under 10 ns / 7 ns | F-082 |
| Combinational output delays through the adapter | 13.3 ns rising, up to 20 ns falling (buffers add about 15 ns) | F-083 |
| A12 filter threshold / dependence on M2 period | 16 falls / none (300 to 1500 ns) | F-084 |
| A12 filter at power-on | about 8 falls after 0.2 to 1 s off, 2 after 30 s | F-085 |
| Power-on IRQ counter | CPU mode, latch `$FF`, running: first /IRQ at M2 fall 1018 or 1019 | F-088 |
| Early CPU expiry after an A12 to CPU switch with the filter below 16 | 4 cycles early | F-087 |
| Instant at which the IRQ enable flag is tested | the M2 fall, within about 7 ns; a write closing up to 150 ns before it counts | F-090 |

## 9. Not known (and why it matters)

The items below need a scope, a supply sweep or other hardware I don't have.

1. **Absolute chip delays.** Setup and hold (under 10 ns) and the shortest write window (7 ns) are measured (F-081, F-082), but the adapter's buffers add about 15 ns to every output, so the chip's own output delays and margins below a few ns are unresolved (F-083). In a console the byte is stable for at least 200 ns before the M2 fall, so latching at the first closing edge is safe.
2. **/CE against a write whose data is late** (the PRG output delay is measured: F-076).
3. **`$C000` and `$C001` timing inside a cycle** (not measured; cycle-level behaviour is known). `$E000` and `$E001` are settled, including the instant at which the enable flag is tested (F-090): see the tables in section 3.
4. **Voltage levels, output drive, edge rates, power-supply sensitivity**, and the output type of /IRQ.
5. **PAL console timing** and Famicom differences (M2 is the same signal, but the PPU waveform is different).
6. **The CIC** and pins 15 to 18.
7. One chip: unit-to-unit and temperature variation are unknown.

## 10. Revision history

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-11-01 | First version: structure, write path, outputs, counter, figures from F-064 to F-072 |
| 0.2 | 2026-11-01 | A12-mode enable flag tested at the assertion fall (F-074), latch 0 rule (F-075), PRG output delay (F-076), A12 sampling window |
| 0.3 | 2026-11-02 | Adapter measurements F-081 to F-090 (window close, transparency per register, A12 sampling, filter threshold, power-on state); absorbed the unique parts of the retired datasheet; whole-file stale-line pass (see the notes in sections 3, 5, 6, 8 and 9) |
