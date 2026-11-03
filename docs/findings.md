# RAMBO-1 findings log

Verified behaviour of the Tengen RAMBO-1 (337006), measured on the jig. This is the evidence base for the
functional description, the emulator guide, the FPGA notes and the test ROMs. NESdev claims stay hypotheses (`nesdev_verification.md`) until they appear here.

**Evidence markers** (used in every document of this project)

| Marker | Meaning |
|---|---|
| **[V]** | Verified on the jig; the finding IDs are given |
| **[C]** | Confirmed by a test ROM on a real NES (cycle-exact CPU, real PPU); the test group is given |
| **[I]** | Inferred from [V] observations; the inference is stated |
| **[U]** | Unknown or not tested |

**Scope and measurement conditions**
- **Device:** Tengen RAMBO-1, marking 337006 (the Tengen mapper commonly listed as iNES mapper 64 with extensions), 40-pin DIP taken from "Rolling Thunder". One chip examined, seated in a socket on the jig board (cart board 800032 Rev A) with its flash chips removed. No manufacturer datasheet exists; every statement was measured.
- **Mega jig (F-001 to F-063):** the Mega 2560 drives every RAMBO input and reads every output through 220 ohm series resistors. The shortest bus step is about 1.9 us, against a real NTSC M2 half-cycle of about 280 ns, so jig timing statements are steady-state or at 2 to 3 us resolution. Only CPU A0, A13 and A14 are wired on the jig; aliasing over A1 to A12 was settled in a real console (F-063). Outputs are read as digital levels; analogue levels and thresholds were not measured.
- **Real console (F-055 onward):** the same chip on the development cart (board 800032 Rev A with two SST39SF040 flash chips holding the test ROM) in an NTSC front-loader NES, running the six test ROMs (62 tests, all pass). CPU-cycle measurements have 1-cycle resolution. Logic-analyser timing (24/48 MHz, +-5 ns) is in `timing_measurements.md` (F-064 to F-076).
- **RP2350 adapter (F-078 to F-090):** a PIO engine at 150 MHz replays bus cycles with 6.7 ns steps; setup, hold, window width and output delays were measured with it. Its input buffers add about 15 ns to every output.
- **Not measured:** supply voltage and temperature (USB power only, pin 19 grounded unless stated, cold starts after 15 s unpowered), DC parameters, edge rates, PAL consoles, other chips or consoles (the console's CPU/PPU alignment changes at each power-up). The CIC and pin 19 were not exercised from a console.

**Evidence index** (topic to findings)

| Topic | Findings |
|---|---|
| Pins and electrical | F-001, F-043 |
| Registers | F-006 to F-010, F-024 to F-027, F-032, F-039 to F-042, F-049, F-062, F-063 |
| Write and read cycles | F-011 to F-017, F-063, F-064, F-066, F-069, F-070, F-081 to F-083, F-086, F-089 |
| CHR banking | F-006, F-007, F-041, F-068 |
| PRG banking | F-009 to F-011, F-076 |
| Power-on | F-001 to F-004, F-034 to F-036, F-045, F-061, F-078, F-079, F-085, F-088 |
| IRQ counter | F-018 to F-038, F-048 to F-060, F-065, F-067, F-071, F-072, F-074, F-075, F-084, F-087, F-090 |
| Pin 19 | F-043 to F-047 |
| Emulator differences | F-058, F-059, F-060 and the test ROM results |

**Conventions**
- *Confidence:* **High** = reproduced across independent runs or states; **Medium** = one run, clear result;
  **Low** = single observation or partly inferred.
- *Observable from a NES:* whether a test ROM running on a console could check it (CPU read/write, PPU reads,
  CPU IRQ). "No" means it is a pin-level fact only the jig can see.
- Logs are in `results/`; scripts in `experiments/`. Outputs are read through the Mega at roughly 100 ms after
  each step, so every finding here is **steady-state** (no edge timing or propagation delay).
- All runs: chip seated in the socket, flash chips removed. SW1C was ON except runs 39 to 50 (SW1C off, pin 19 wired
  to Mega D2 for 40 to 50). Cold starts (USB only, 15 s unpowered): runs 01, 04, 06, 08, 28, 29, 39; the rest were warm.

## Experiment index

| ID | Script | Log | Kind |
|---|---|---|---|
| 01 | `01_cold_idle.txt` | `01_cold_idle_20261030_221009.csv` | cold |
| 02 | `02_chr_r0.txt` | `02_chr_r0_20261030_220600.csv` | warm |
| 03 | `03_ciram_mirroring.txt` | `03_ciram_mirroring_20261030_220609.csv` | warm |
| 04 | `04_cold_probe.txt` | `04_cold_probe_20261030_221804.csv` | cold |
| 05 | `05_chr_map.txt` (generated) | `05_chr_map_20261030_221941.csv` | warm |
| 06 | `06_cold_1kb_mode.txt` | `06_cold_1kb_mode_20261030_222309.csv` | cold |
| 07 | `07_prg_map.txt` (generated) | `07_prg_map_20261030_222542.csv` | warm |
| 08 | `08_cold_prg.txt` | `08_cold_prg_20261030_222822.csv` | cold |
| 09 | `09_ce_timing.txt` (generated) | `09_ce_timing_20261030_223029.csv` | warm |
| 10 | `10_wseq_selftest.txt` | `10_wseq_selftest_20261030_223947.csv` | warm (tool check, not a chip finding) |
| 11 | `11_write_a0_phase.txt` (generated) | `11_write_a0_phase_20261030_224249.csv` | warm |
| 12 | `12_write_a13_phase.txt` (generated) | `12_write_a13_phase_20261030_224338.csv` | warm |
| 13 | `13_write_data_phase.txt` (generated) | `13_write_data_phase_20261030_224603.csv` (the earlier `..._224426.csv` is INVALID: it read R1, not R0) | warm |
| 14 | `14_write_shapes.txt` (generated) | `14_write_shapes_20261030_224520.csv` | warm |
| 15 | `15_write_transparent.txt` | `15_write_transparent_20261030_224730.csv` | warm |
| 16 | `16_irq_cpu_cycle.txt` (generated) | `16_irq_cpu_cycle_20261030_224925.csv` | warm |
| 17 | `17_irq_a12.txt` (generated) | `17_irq_a12_20261030_225108.csv` (A12 high ~125 ns, never counted) and `..._225156.csv` (A12 high 4 M2 cycles, low 8: never counted) | warm |
| 18 | `18_a12_sweep.txt` | `18_a12_sweep_20261030_225321.csv` | warm |
| 19 | `19_a12_threshold.txt` | `19_a12_threshold_20261030_225505.csv` | warm |
| 20 | `20_a12_count_vs_latch.txt` | `20_a12_count_vs_latch_20261030_225626.csv` | warm |
| 21 | `21_cpu_prescaler_phase.txt` | `21_cpu_prescaler_phase_20261030_225751.csv` | warm |
| 22 | `22_c001_rewrite_cpu.txt` (generated) | `22_c001_rewrite_cpu_20261030_230719.csv` (the earlier `..._230224.csv` is SUPERSEDED: it enabled IRQ before `$C001`, so a leftover counter could assert /IRQ first) | warm |
| 23 | `23_latch_change_cpu.txt` (generated) | `23_latch_change_cpu_20261030_230929.csv` (earlier `..._230435.csv` superseded, same setup flaw) | warm |
| 24 | `24_irq_mode_switch.txt` (generated) | `24_irq_mode_switch_20261030_231314.csv` | warm |
| 25 | `25_c001_data_bits.txt` (generated) | `25_c001_data_bits_20261030_231530.csv` | warm |
| 26 | `26_irq_ack_cpu.txt` (generated) | `26_irq_ack_cpu_20261030_232637.csv` | warm |
| 27 | `27_irq_ack_a12.txt` (generated) | `27_irq_ack_a12_20261030_233118.csv` | warm |
| 28 | `28_cold_counter.txt` | `28_cold_counter_20261030_234443.csv` | cold |
| 29 | `29_cold_latch.txt` | `29_cold_latch_20261030_234948.csv` | cold |
| 30 | `30_latch_refine.txt` | `30_latch_refine_20261030_235101.csv` (run on the same powered-up chip, no `$C000` written in between) | warm, follows 29 |
| 31 | `31_a12_poweron_latch.txt` (generated) | `31_a12_poweron_latch_20261030_235304.csv` (same chip, still no `$C000` since power-up) | warm, follows 30 |
| 32 | `32_a12_period.txt` (generated) | `32_a12_period_20261030_235558.csv` | warm |
| 33 | `33_a12_latch_load.txt` (generated) | `33_a12_latch_load_20261030_235643.csv` | warm |
| 34 | `34_decode_index.txt` (generated) | `34_decode_index_20261031_000123.csv` | warm |
| 35 | `35_decode_ctrl_bits.txt` (generated) | `35_decode_ctrl_bits_20261031_000341.csv` | warm |
| 36 | `36_decode_a000_data.txt` (generated) | `36_decode_a000_data_20261031_000607.csv` | warm |
| 37 | `37_decode_a001_data.txt` (generated) | `37_decode_a001_data_20261031_000744.csv` | warm |
| 40 | `40_regression_p19_{0,1,z}.txt` (38 with a pin 19 command first) | `40_regression_p19_0_20261031_011803.csv`, `..._1_20261031_011902.csv`, `..._z_20261031_012001.csv` | warm; first runs with the pin 19 flying lead |
| 41, 42 | `41_p19high_index.txt`, `42_p19high_ctrl_bits.txt` (34, 35 with pin 19 high) | `41_p19high_index_20261031_012149.csv`, `42_p19high_ctrl_bits_20261031_012407.csv` | warm, pin 19 HIGH throughout (the final `p19 z` left it high, F-047). Baselines in these logs are leftover register state, see F-046 |
| 46 | `46_p19_ctrl_matrix.txt` (generated by `tools/gen_p19_map.py`) | `46_p19_ctrl_matrix_20261031_013411.csv` | warm; pin 19 low-driven for loads |
| 47 | `47_p19_value_function.txt` (generated) | `47_p19_value_function_20261031_013719.csv` | warm |
| 48 | `48_p19_register_accept.txt` (generated) | `48_p19_register_accept_20261031_014104.csv` | warm |
| 49 | `49_p19_irq_registers.txt` (generated) | `49_p19_irq_registers_20261031_014414.csv` | warm |
| 50 | `50_p19_constant_checks.txt` | `50_p19_constant_checks_20261031_014557.csv` | warm |
| 43 | `43_p19_write_protect.txt` | `43_p19_write_protect_20261031_012706.csv` | warm, INVALID as a low/high comparison: its "released" steps were still high (F-047). Superseded by 44 |
| 44 | `44_p19_write_protect_lowdrive.txt` | `44_p19_write_protect_lowdrive_20261031_012838.csv` | warm, low driven with `p19 0` |
| 45 | `45_p19high_single_writes.txt` | `45_p19high_single_writes_20261031_012949.csv` | warm |
| 39 | `39_cold_poweron_sw1c_off.txt` | `39_cold_poweron_sw1c_off_20261031_005010.csv`; latch refinement on the same chip `30_latch_refine_20261031_005121.csv` | cold, SW1C OFF |
| 51 | `51_k_gates_r8_r9.txt` (generated by `tools/gen_nesdev_checks.py`) | `51_k_gates_r8_r9_20261031_020921.csv` | warm; chip cold-started, SW1C ON, flying wire off |
| 52 | `52_a12_latency.txt` (generated) | `52_a12_latency_20261031_022138.csv` (the earlier `..._021006.csv` and `..._021229.csv` are SUPERSEDED: their setups did not fill the A12 filter before `$C001`, so variants B-D started with /IRQ already asserted, see F-052) | warm |
| 53 | `53_a12_filter_shape.txt` (generated) | `53_a12_filter_shape_20261031_022723.csv` | warm |
| 54 | `54_a001_irq.txt` (generated) | `54_a001_irq_20261031_022156.csv` (first run, one unexplained outlier, see F-053), reruns `..._022501.csv`, `..._022608.csv` | warm |
| 55 | `55_latch_bits.txt` (generated) | `55_latch_bits_20261031_022303.csv` | warm |
| 56 | `56_c001_filter_state.txt` (generated) | `56_c001_filter_state_20261031_021943.csv` | warm |
| 57 | `57_a12_nonfull_low_latch.txt` (generated by `tools/gen_j_experiments.py`) | `57_a12_nonfull_low_latch_20261101_001854.csv` | warm |
| 58 | `58_a12_period_l5_16.txt` (generated) | `58_a12_period_l5_16_20261101_002023.csv` | warm |
| 59 | `59_cpu_to_a12_switch.txt` (generated) | `59_cpu_to_a12_switch_20261101_002655.csv`; summary with `tools/j4_report.py` | warm |
| 38 | `38_regression.txt` (generated by `tools/gen_regression.py`) | warm controls `38_regression_20261031_001358.csv` and `..._001457.csv`; cold control, SW1C ON `38_regression_20261031_003916.csv`; cold test, SW1C OFF `38_regression_20261031_004356.csv`. Compare with `tools/compare_runs.py` | warm and cold |

Reports: `tools/chr_map_report.py` (05), `tools/prg_map_report.py` (07), `tools/ce_timing_report.py` (09),
`tools/write_order_report.py` (11-14), `tools/irq_basic_report.py` (16, 17), `tools/irq_reload_report.py` (22-27), `tools/cold_counter_report.py` (28); 31-33 use `tools/irq_reload_report.py`; 34-37 use `tools/decode_report.py` (generator `tools/gen_decode_sweep.py`); 46-49 use `tools/p19_map_report.py`. Experiments 11-15 use `wseq` (steps are ~1.9 us + 4 cycles per tick).

**RP2350 adapter experiments (F-078 to F-090).** Scripts in `firmware/rp2350_jig/tools/`; each run prints its table and nothing else is stored, so a result is reproduced by running the script on a cart in jig mode.

| Experiment | Script | Finding |
|---|---|---|
| E2a, `$E000` release delay; replay of console captures | `e2_release.py`, `replay.py` | F-080 |
| E3, A12 setup and hold against the M2 fall | `e3_a12.py` | F-081 |
| E2, write window: closing edge, setup, hold, width | `e2_window.py` | F-082 |
| E5, output delays | `e5_delays.py` | F-083 |
| E4, A12 filter threshold, period independence, glitches | `e4_filter.py` | F-084 |
| E4b, A12 filter after a cold start | `e4b_poweron.py` | F-085 |
| E6, read side effects | `e6_reads.py` | F-086 |
| E7, A12 to CPU mode switch | `e7_modeswitch.py` | F-087 |
| E8, power-on counter | `e8_poweron_counter.py` | F-088 |
| E9, register transparency map | `e9_transparency.py` | F-089 |
| E10, enable-flag instant | `e10_enable_instant.py` | F-090 |
| Cold starts and supply retention (first runs) | `jig.py` (`cold`, `discharge`) | F-078, F-079 |

## Power-on state

**F-001: /IRQ is asserted (low) from a cold start.** `IRQ_N` reads 0 before any write. A write to `$E000` releases
it. PPU A12 activity before the write (a rising edge) does not change it.
- Evidence: runs 01, 04, 06, 08, 28 (five independent cold starts); meter on RAMBO pin 30 read 0.023 V with no
  serial port open.
- Confidence: High. Not explained: which internal state asserts it.
- Observable from a NES: Probably, as an IRQ pending once the CPU I flag is cleared; not tested.

**F-002: PRG banks power up at the last bank.** Reads at `$8000`, `$A000`, `$C000` and `$E000` all show
PRG A17..A13 = `1F`.
- Evidence: run 08 (one cold start; the all-ones PRG pattern also appeared in the idle reads of 01, 04, 06).
- Confidence: Medium. Cannot tell "R6/R7/RF hold 1F (or FF)" from "outputs forced high until the first write".
- Observable from a NES: Yes (read the ROM at `$8000-$DFFF` at start-up).

**F-003: CHR powers up behaving as 1 KB CHR mode with every bank 0.** CHR A10..A17 stay 0 for all PPU
A10/A11/A12 values. After `w 8000 00` (2 KB mode) CHR A10 follows PPU A10; after `w 8000 20` (1 KB mode) it stops
following again.
- Evidence: runs 04 (PPU A10-A12 sweep) and 06 (mode comparison), both cold.
- Confidence: Medium-High. The stored mode bit cannot be read back; this is the behaviour of the outputs.
- Observable from a NES: Yes (read pattern tiles with no CHR setup).

**F-004: Mirroring powers up vertical.** `CIRAM_A10` follows PPU A10 before any `$A000` write.
- Evidence: runs 04, 06 (cold); also 03.
- Confidence: High.
- Observable from a NES: Yes (nametable write/read aliasing).

## IRQ

**F-005: `$E000` (even) write releases /IRQ.** Verified from the power-on asserted state only.
- Evidence: runs 01, 04, 06, 08. Superseded and extended by F-029 to F-032 (`$E001` enable, `$C001` does not release).

## CHR banking

**F-006: CHR bank registers map to PPU windows as in MMC3, with extra 1 KB registers R8 and R9.**

| `$8000` bit 5 / bit 7 | $0000 | $0400 | $0800 | $0C00 | $1000 | $1400 | $1800 | $1C00 |
|---|---|---|---|---|---|---|---|---|
| 0 / 0 (2 KB) | R0 | R0 | R1 | R1 | R2 | R3 | R4 | R5 |
| 1 / 0 (1 KB) | R0 | R8 | R1 | R9 | R2 | R3 | R4 | R5 |
| 0 / 1 (2 KB, inverted) | R2 | R3 | R4 | R5 | R0 | R0 | R1 | R1 |
| 1 / 1 (1 KB, inverted) | R2 | R3 | R4 | R5 | R0 | R8 | R1 | R9 |

- Evidence: run 05 (every combination, both value sets), with run 02 as a first check.
- Confidence: High for the table. Bits 4 and 6 of `$8000` were not varied here (bit 6 is covered by F-009).
- Observable from a NES: Yes.

**F-007: CHR bank value is eight bits wide; bit 0 is ignored on R0/R1 in 2 KB mode.** The register byte appears
directly on CHR A17..A10. In 2 KB mode R0/R1 bit 0 is ignored and CHR A10 follows PPU A10; in 1 KB mode, and for
R2-R5, bit 0 drives CHR A10.
- Evidence: run 05 ("even" and "odd" value sets).
- Confidence: High.
- Observable from a NES: Yes.

**F-008: `$A000` bit 0 selects mirroring.** 0 = `CIRAM_A10` follows PPU A10, 1 = follows PPU A11. Only the values
`00` and `01` were written.
- Evidence: run 03 (warm).
- Confidence: Medium. Other bits of `$A000` are covered in F-041; four-screen cannot be seen (one CIRAM A10 output).
- Observable from a NES: Yes.

## PRG banking

**F-009: PRG registers map as in the NESdev description, with the mode in `$8000` bit 6.**

| Window | bit 6 = 0 | bit 6 = 1 |
|---|---|---|
| $8000 | R6 | RF |
| $A000 | R7 | R7 |
| $C000 | RF | R6 |
| $E000 | fixed (bank 1F) | fixed (bank 1F) |

- Evidence: run 07. Confidence: High. Observable from a NES: Yes.

**F-010: Only the low five bits of PRG bank values reach the address pins.** Setting bits 5, 6 and 7 of R6/R7/RF
changed nothing on PRG A17..A13. The CHR mode bits (`$8000` bits 5 and 7) have no effect on PRG banking.
- Evidence: run 07 ("hi" and "lo" passes, four `$8000` mode values).
- Confidence: High. Whether the extra bits matter for anything else is not known.

**F-011: PRG A13..A17 follow CPU A13/A14 even when /ROMSEL is high.** A read cycle at `$0000` (A13=A14=0) shows
the `$8000`-window bank; at `$6000` it shows the fixed bank. Only /CE is gated.
- Evidence: runs 07, 08 (reads below `$8000`). Confidence: High.
- Observable from a NES: No (the ROM is not selected outside `$8000-$FFFF`).

**F-012: PRG /CE is active (low) only when M2 = 1, R/W = 1 and /ROMSEL = 0.** All seven other combinations leave it
high, including the write combination. Not path-dependent: same result from every predecessor state.
- Evidence: run 09 (8 targets x 8 predecessors, at `$E000`); reads at all four windows in 07, 08.
- Confidence: High for static levels. Not tested: propagation delay, glitches, behaviour at other addresses with
  write combinations (the firmware only allows that combination at `$E000`).
- Observable from a NES: Indirectly (no bus conflicts on writes to ROM space).

## Register decode

Experiments 34-37 load a known value into every visible register, make one change, and compare a fingerprint of
the whole mapping (CHR byte for eight PPU A10/A11/A12 combinations, PRG bank at four windows, `CIRAM_A10` for the
four PPU A10/A11 combinations) with the unchanged baseline. Only changes that reach an output pin are visible.

**F-039: Bank-select index 0 to 9 and 15 (F) select R0 to R9 and RF, and indices 10 to 14 (A to E) have no
visible effect.** After `$8000 = idx` and `$8001 = 66`: idx 0, 1, 2, 3, 4, 5 changed the CHR windows $0000, $0800,
$1000, $1400, $1800, $1C00 (1 KB mode); 8 and 9 changed $0400 and $0C00; 6 and 7 changed PRG $8000 and $A000;
F changed PRG $C000. Indices A to E changed nothing. PRG values showed only the low five bits (`06`).
- Evidence: run 34. Confidence: High for visibility; hidden state behind A-E cannot be excluded.
- Observable from a NES: Yes (writing an index that does nothing).

**F-040: `$8000` bit 4 has no visible effect.** All 16 high-nibble values with index 0 and no data write: each
value with bit 4 set gave exactly the same fingerprint as the same value with bit 4 clear (`00/10`, `20/30`,
`40/50`, ..., `E0/F0`). Bits 5, 6, 7 behave as in F-006 and F-009.
- Evidence: run 35. Confidence: High for the mapping outputs.

**F-041: Only bit 0 of `$A000` is visible: 0 = `CIRAM_A10` follows PPU A10 (vertical), 1 = follows PPU A11
(horizontal).** Data `00, 02, 04, 08, 10, 20, 40, 80, FE` all gave vertical; `01, FF` gave horizontal.
- Evidence: run 36. Confidence: High. The RAMBO has one `CIRAM_A10` output, so a four-screen mode cannot be
  distinguished from the others here.

**F-042: `$A001` has no visible effect on any output for `00, 01, 40, 80, C0, FF`.** No change in CHR, PRG or
mirroring (and the sweep did not look at /IRQ).
- Evidence: run 37. Confidence: Medium. It may control something not visible from the pins (the NESdev text calls
  it a PRG-RAM register on MMC3; the RAMBO has no RAM pins).

## IRQ counter

Setup used in every run: `$E000` (acknowledge/disable), `$C000` = L (latch), `$C001` = mode (bit 0: 0 = A12, 1 = CPU
cycles), `$E001` (enable). Each `w` is itself one M2 cycle on the bus. "Events" are counted from after the
`$E001` write, with `/IRQ` read after each. All runs are warm.

**F-018: In CPU-cycle mode the counter advances once per four M2 cycles, and /IRQ asserts 4 x (L + 1) + 2 M2
cycles after the `$C001` write cycle.** Counting the `$E001` write cycle and the idle cycles after it, /IRQ first
went low after 9, 13, 17, 21 and 37 events for L = 1, 2, 3, 4 and 8, which is 4L + 5 events after `$E001`.
- Evidence: run 16; run 21 (see F-019). Confidence: High for the formula at these values.
- Observable from a NES: Yes (IRQ timing against a cycle count).

**F-019: The counter runs and reloads whether or not IRQ is enabled; a disabled interrupt is not remembered.**
With L = 2 and k idle cycles inserted between `$C001` and `$E001`, /IRQ always asserted 14 M2 cycles after the
`$C001` write when enabled before then (k = 0 to 12). With k = 16 the count had passed zero while disabled:
/IRQ stayed high at enable, and went low 12 cycles (= 4 x (L + 1)) after the first would-be assertion. So the
counter reloads and repeats with period 4 x (L + 1), and `$C001` evidently restarts its phase (the offset of 2 was
the same in every run).
- Evidence: run 21. Confidence: High. Not tested: `$C001` written while counting; the prescaler phase has not been
  separated from the counter reload.
- Observable from a NES: Yes.

**F-020: Once asserted, /IRQ stays low until `$E000`.** It remained low for at least 40 further M2 cycles, through
at least one reload period.
- Evidence: runs 16, 21. Confidence: Medium (no other release method tried).

**F-021: In A12 mode /IRQ asserts on counted rising edge number L + 2.** With A12 low 20 M2 cycles between
pulses, /IRQ first went low at pulse 2, 3, 4, 5, 6, 7 and 10 for L = 0, 1, 2, 3, 4, 5 and 8. The run started with
A12 low for 64 M2 cycles after `$E001`, and the first pulse already counted.
- Evidence: run 20. Confidence: High for L = 0 to 5 and 8.
- QUALIFICATION (F-052): the L + 2 holds when the A12 filter was already full (A12 low for 16 or more M2 cycles) at the
  `$C001` write, which was true in every run from 16 to 33. If the filter was not full, the first pulse counts and /IRQ comes
  at pulse L + 1.
- Note: this is one pulse later than the simplest MMC3 model (reload on the first edge, then L decrements)
  would predict, which would give L + 1. This agrees with the "late IRQ" mentioned on the NESdev page, but the
  NESdev claim itself is still unverified.
- Observable from a NES: Yes.

**F-022: A12 pulses count only if A12 was low for 16 or more M2 cycles before the rising edge.** With A12 high for
2 M2 cycles and low for G M2 cycles between pulses, /IRQ asserted for G = 16 (at pulse 3 with L = 1) and never for
G = 8 to 15 in 8 pulses. A coarse sweep (run 18) agrees: G = 1 and 4 never, 16 and 64 yes.
- Evidence: runs 17 (G = 8), 18, 19. Confidence: Medium. The threshold is exact only for this protocol. A12 rose
  with M2 low, the `m` command ends each low period with M2 low, and G counts complete M2 cycles. The true rule may
  be a count of M2 edges of one polarity, or have a phase dependence of one cycle.
- UPDATE (F-051): the filter counts M2 falling edges with A12 low. 16 falls count, 15 do not, whether A12 dropped while
  M2 was low or while it was high.
- Observable from a NES: Partly (the PPU's A12 behaviour around sprite fetches).

**F-023: A short A12 pulse that does not span an M2 edge is not counted.** A12 high for ~125 ns with no M2 clock
never counted (run 17, first log), and in run 18 H = 0 (no M2 cycle while A12 is high) never counted at any G,
whereas H = 1 or more counted at G = 16 and 64. So the A12 input is sampled in step with M2, not asynchronously.
- UPDATE (F-051): the sampling edge is the M2 falling edge while A12 is high; A12 high across only the M2 rising edge never counts.
- Evidence: runs 17, 18. Confidence: Medium. Whether it needs a full M2 cycle or one particular edge was not
  separated (H = 1 was the smallest tried that included an M2 edge).

**F-024: A `$C001` write restarts the counter in the mode it selects.** Rewriting `$C001` after j = 0 to 19 cycles
(CPU mode, L = 4) always gave /IRQ 22 cycles after the rewrite, wherever the first count had reached. In A12
mode, rewriting `$C001` after 1 to 4 counted pulses gave /IRQ at pulse L + 2 = 6 counted from the rewrite.
- Evidence: runs 22, 24. Confidence: High.
- Observable from a NES: Yes.

**F-025: A `$C001` write does not release an already asserted /IRQ.** With the first expiry already past
(j = 21 and 25), /IRQ stayed low through the rewrite. Only `$E000` releases it (F-020).
- Evidence: run 22. Confidence: Medium-High.

**F-026: Switching mode at `$C001` carries nothing over.** CPU to A12 (after 0, 8 or 15 cycles): /IRQ came at A12
pulse 6, and the cycle counting did not continue (each pulse carried 22 M2 cycles, so a surviving cycle count
would have fired at pulse 1). A12 to CPU (after 0, 2 or 4 pulses): /IRQ 22 cycles after the write, as for a fresh
start.
- Evidence: run 24. Confidence: High at these values.

**F-027: Only bit 0 of the `$C001` data selects the mode.** Data `00, 02, 04, 10, 80, FE` all gave A12 mode (/IRQ at
pulse L + 2 = 4 for L = 2); `01, 03, 05, 81, FF` all gave CPU mode (14 cycles = 4 x (2 + 1) + 2). Bits 1 to 7 had
no visible effect on either result.
- Evidence: run 25. Confidence: High for the values tried; effects on anything other than the first expiry were
  not looked for.

**F-028: The counter takes the latch value about 5 M2 cycles after the `$C001` write, and later latch changes
apply at the next reload.** In CPU mode, writing `$C000` (4 to 1) up to 5 cycles after `$C001` made the first
expiry come at t = 10 = 4 x (1 + 1) + 2 (the new latch was used for the first load); writing it from cycle 6 on
left the first expiry at t = 22 (old latch) and changed the *second* expiry to 8 cycles after the first (t = 30),
not 20 (t = 42, the control with no change). The first-expiry formula is therefore consistent with a load at about
cycle 5 followed by 4L + 1 cycles.
- Evidence: run 23 (`$C000` written at t = 2 to 17). Confidence: Medium. Cycle resolution; measured in CPU mode
  only; whether the A12-mode counter loads at the first counted edge, so that a latch change before that edge
  counts, was not tested.
- Observable from a NES: Yes.

**F-029: `$E000` releases /IRQ and disables it, and does not disturb the counter.** Writing `$E000` after /IRQ
asserted took /IRQ high at once; writing it mid-count and re-enabling before the expiry left that expiry where it
was (CPU mode, L = 4, `$E000` at cycle 10 and `$E001` at 11: /IRQ at t = 22). The counter phase and period are
unaffected by `$E000`/`$E001`.
- Evidence: runs 26, 27. Confidence: High.

**F-030: `$E001` only enables; it neither restarts the counter nor releases an asserted /IRQ.** Repeating `$E001`
while enabled (at cycles 5, 10, 15) left the expiry at t = 22. `$E001` written while /IRQ was low (no `$E000`)
left /IRQ low.
- Evidence: run 26 (and run 27, `$E001` again after pulse 1). Confidence: High.

**F-031: An expiry that happens while disabled is lost, in both modes.** CPU mode: disabled from cycle 10 to
cycle 30, no /IRQ at 22 and none at enable; /IRQ came at t = 42 (22 + 20, the next period). With `$E000` and no
re-enable, /IRQ never asserted through t = 60. A12 mode (L = 1, expiries at pulses 3, 5, 7): disabled until after
pulse 6, then enabled: no /IRQ at the enable, and /IRQ at pulse 7.
- Evidence: runs 26, 27. Confidence: High. (Earlier evidence in F-019.)

**F-032: The data byte of `$E000` and `$E001` is ignored.** Data `00, 01, 80, FF` all acknowledged on `$E000` and
enabled on `$E001`, with /IRQ high after the ack and the next expiry unchanged (t = 42).
- Evidence: run 26. Confidence: High for the values tried. The address bits other than A0, A13 and A14 are not
  wired to the RAMBO on the jig, so register aliasing over A1-A12 cannot be tested here.

**F-033: In A12 mode the counter keeps counting after an expiry, with a period one counted pulse shorter than
the first interval.** L = 1: expiries at pulses 3, 5, 7. So the first interval after `$C001` is L + 2 pulses (F-021)
and later intervals are L + 1. This matches CPU mode, where the first interval (4 x (L + 1) + 2 cycles) is the
period (4 x (L + 1)) plus 2 cycles of start-up. After an ack with immediate re-enable, /IRQ came back two pulses
later (pulse 5) without restarting the counter.
- Evidence: run 27 (control, ack-plus-enable, disable-across-expiry). Confidence: Medium-High for L = 1; L = 2, 3
  and 4 are confirmed in F-037.
- Observable from a NES: Yes.

**F-034: The power-on /IRQ assertion is not a re-triggering counter at small latch values.** After a cold start,
/IRQ stayed low through 8 idle M2 cycles and 3 A12 pulses. `$E000` released it. Then `$E001` was written with no
`$C000` or `$C001` ever written, and /IRQ stayed high through 40 further M2 cycles and 12 A12 pulses (about 475 M2
cycles in all after the ack).
- Evidence: run 28. Confidence: Medium. One cold start. This rules out a power-on state of "enabled, counting
  M2 cycles or A12 edges with latch 0 to about 10". It does not rule out a long period (a latch of `FF` would
  need ~1024 cycles in CPU mode), or a counter that does not run until the first `$C001`.
- The power-on latch is `FF` (F-035), which explains why no counter expiry appeared in 475 cycles.

**F-035: The latch powers up at `FF`.** After a cold start, with `$E000`, then `$C001 = 01` and `$E001` and no
`$C000` ever written, /IRQ first went low at t = 1026 M2 cycles after the `$C001` write (run 30, one-cycle
resolution). That is 4 x (255 + 1) + 2, the CPU-mode formula of F-018 with L = 255. The coarse cold run (run 29)
saw it between 1025 and 1032 before the refinement.
- Evidence: runs 29 (cold) and 30 (same chip, still no `$C000` write). Confidence: Medium-High. One cold start.
  The latch is assumed to be one register shared by both modes: the A12-mode count from the power-on latch
  (255 + 2 = 257 counted pulses) was not tested.
- Consequence: the power-on /IRQ low (F-001) is not the counter expiring; it is a separate stored state that
  `$E000` clears (F-034). The first `$C001` after power-up without `$C000` gives a ~1 ms interrupt delay in CPU
  mode (1026 cycles at the NES clock of 1.79 MHz is about 573 us).
- Observable from a NES: Yes (start the counter without writing the latch and time the interrupt).

**F-036: The power-on latch is `FF` in A12 mode too.** With no `$C000` written since the cold start, `$E000`,
`$C001 = 00` and `$E001`, /IRQ first went low at A12 pulse 257 (= 255 + 2), after 250 unread pulses and then a read
after every pulse.
- Evidence: run 31 (same chip as run 30, never power-cycled in between). Confidence: Medium-High. One cold
  start; so the latch is one register shared by both modes.

**F-037: In A12 mode, expiries repeat every L + 1 counted pulses, after a first expiry at pulse L + 2.** L = 2:
pulses 4, 7, 10. L = 3: 5, 9, 13. L = 4: 6, 11, 16. (Acknowledge and re-enable one pulse after each.)
- Evidence: run 32. Confidence: High.

**F-038: The A12-mode counter takes the latch at the second counted edge.** With the latch at 4 and then written
as 1 (a) 2, 7, 8 or 25 cycles after `$C001`, before pulse 1, or (b) after pulse 1, the first expiry came at pulse 3,
so the new latch was used. Written (c) after pulse 2 or 4, the first expiry stayed at pulse 6 (old latch), and
expiries after that used the new latch (/IRQ at pulses 10 after an ack at 9, matching a period of 2).
- QUALIFICATION (F-052): the first counted edge is skipped only if the filter was full at the `$C001` write.
- This is different from CPU mode, where the latch is taken about 5 M2 cycles after `$C001` (F-028).
- It also fits the first interval of L + 2: the first counted edge starts the counter, the second loads the
  latch, and L more edges bring it to zero.
- Evidence: run 33 (seven write times). Confidence: Medium-High. Edge counted by the chip is the filtered A12
  rising edge; the edge/phase relative to M2 is untested.
- Observable from a NES: Yes (a game writing `$C000` between the first and second scanline of a frame).

**F-048: A simulator replay of 14 recorded IRQ runs (3393 /IRQ samples) is reproduced exactly by one counter model.**
`tools/irq_model_check.py` replays each run's command stream (M2 falling edges, A12 sampled on them). The merged model
(the A12 filter forced to 17 by `$C001` only when it is full, F-052; the counter loaded from the latch at the first real
clock after `$C001`; no OR 1; CPU mode first clock 5 M2 falls after the `$C001` write, /IRQ 1 M2 cycle after the zero
clock) gives 0 mismatches. Single changes break it: OR 1 on the first reload, 282; the filter forced to 17 on every
`$C001`, 17; filter set to 0, 54; counter loaded at the `$C001` write, 388; first CPU clock at 4 cycles,
111. The NESdev page's main-text and refined algorithms give 435 and 190.
- Evidence: runs 16 to 27, 31 to 33 and 56, replayed on 2026-10-31. Confidence: High that the model is consistent with
  the recordings; Medium for the CPU-mode constants, which were fitted (first clock at 5, delay 1). The A12-mode part has
  no fitted number.
- Replay assumptions: the filter starts full (the chip sat idle with A12 low before every run) and tracks A12 in both modes
  (not observable in CPU mode). Two simulator bugs found and fixed while building it (a pending delay counted down in the
  same fall that set it; the initial filter value), neither a chip behaviour.
- See `docs/nesdev_verification.md` for the assertion-by-assertion comparison.

**F-049: R8 and R9 accept writes, and keep their values, while K = 0.** R8 := 44 and R9 := 46 written with K = 0
did not show (as expected); after switching to K = 1 without rewriting them the windows showed 44 and 46. Values
written with K = 1 survived K = 0 and back to K = 1. "If K=1" on the NESdev page describes when the registers have an
effect, not when they can be written.
- Evidence: run 51. Confidence: High.

**F-050: In A12 mode /IRQ goes low after the second M2 fall following the A12 rise that clocks the counter.** L = 0, the
second counted pulse stepped by M2 edge, sampled after every step: /IRQ stayed high through the first M2 fall after the
rise and went low after the second fall, in four phase variants (A12 rising while M2 low or high). It still asserted
when A12 dropped again before the second fall, including when it dropped during M2 high. So the delay is one further
M2 fall after the clocking fall, independent of A12 afterwards.
- Evidence: run 52 (valid log `..._022138.csv`). Confidence: High at M2-edge resolution (about 2.4 us per step).
- The CPU-mode delay is also one M2 cycle after the zero clock (F-048).

**F-051: The A12 filter counts M2 falling edges, and the counter is clocked by the M2 fall at which A12 is high.** With
L = 1 and every pulse counting the interrupt comes at pulse 3. Results: 16 M2 falls with A12 low count and 15 do not,
both when A12 dropped while M2 was low (16 rises) and while M2 was high (15 rises with 16 falls: still counted); A12 high
across an M2 rise only (low at the fall) never counted; A12 high across a fall only counted; A12 high for 6 M2 cycles
counted once per pulse.
- Evidence: run 53 variants v1 to v7. Confidence: High at this resolution.

**F-052: A write to `$C001` forces the A12 filter to 17 only if the filter is already full (16); otherwise the filter is
left alone.** The first A12 pulse after `$C001` is swallowed when 16 or more M2 falls with A12 low have occurred before the
`$C001` write (the register-write cycles count as falls); it is counted otherwise, and /IRQ then comes at pulse L + 1.
Scan: with n low falls before `$C001`, pulse 1 counted for 0 to 14 falls and was swallowed for 15 or more, whether the
falls were idle cycles or register writes (the same total of 16 in each split). With the pulse right after the `$E001`
write, pulse 1 counted only when the filter was 14 or 15 at the write (it reached 16 by the pulse) and not when it was
at most 13 or at least 16. A write with A12 already high (so an A12-high fall resets the filter first) leaves pulse 1
counted (run 53 v8a, v8b: /IRQ at pulse 2 for L = 1).
- Evidence: run 56 (28 trials), run 53 v8a to v8c, manual probes. The unconditional "set to 17" gives 17 mismatches in
  run 56's 28 samples; the conditional rule gives 0 across all 3393 recorded IRQ samples (F-048).
- Why earlier runs missed it: in runs 16 to 33 A12 had been low for far longer than 16 cycles before every `$C001`,
  so the filter was always full. Experiments 52 and 53 first failed for this reason: their setups did not wait, so
  the swallow depended on what had run before.
- Confidence: High for the boundary and the full-filter condition. The exact internal form (set to 17, increment past 16,
  or a separate flag) cannot be separated at the pins.

**F-053: Writing `$A001` does not change the IRQ counter or /IRQ.** CPU mode, L = 2: with `$A001` = `FF`, `80`, `01`
written at t = 3, /IRQ first went low at t = 14 as without a write; `$A001` = `FF` written while /IRQ was low left it low.
A12 mode, L = 2: `$A001` = `00` or `FF` after pulse 1 left /IRQ at pulse 4. In the first run `$A001` = `00` at t = 3 gave
t = 10; this did not reproduce in six manual repeats (also right after A12-mode activity) or in two full reruns (all 14),
and is recorded as an unexplained one-off.
- Evidence: run 54 and its two reruns. Confidence: Medium-High.

**F-054: All eight IRQ latch bits work.** CPU mode first expiry at 4 x (L + 1) + 2 for L = `10`, `20`, `40`, `55`, `80`, `AA`
(t = 70, 134, 262, 346, 518, 686), all as predicted. With the earlier values (0 to 5, 8, 11, 255) every bit has been
exercised.
- Evidence: run 55. Confidence: High.

**F-055: In A12 mode with the filter not full at `$C001`, /IRQ asserts at counted pulse L + 1 for L = 0, 1, 2; with the filter full it asserts at L + 2.** With 0, 6 or 12 low falls before `$C001` (writes counted): L = 0 at pulse 1, L = 1 at pulse 2, L = 2 at pulse 3. With 20 low falls: pulses 2, 3, 4.
- Evidence: run 57 (12 trials, one per (L, n)). Confidence: High. Extends F-052 to L = 0 and 1 (earlier only L = 1 at one filter value was seen).
- Observable from a NES: Yes, but only after unusual A12 activity just before `$C001`.

**F-056: In A12 mode the repeat period is L + 1 pulses for every latch from 5 to 16.** First expiry at pulse L + 2, then L + 1 and 2L + 2 pulses later (ack and enable one pulse after each expiry): L = 5: 7, 13, 19; L = 8: 10, 19, 28; L = 12: 14, 27, 40; L = 16: 18, 35, 52. All twelve latches match.
- Evidence: run 58. Confidence: High. Joins F-037 (L = 2 to 4), so the rule is confirmed for L = 2 to 16.
- Observable from a NES: Yes.

**F-057: Writing `$C001` with bit 0 = 0 (switch from CPU mode to A12 mode) cancels a pending CPU-mode expiry and starts the A12 counter cleanly.** CPU mode, L = 4, enabled; first expiry at 22 M2 cycles after the CPU-mode `$C001` (/IRQ read low at 22 and later, high at 21 and earlier). `$C001` := 0 written at 11 to 21 cycles after the CPU-mode `$C001` (the last at the cycle before the expiry): /IRQ never asserted in the 50 cycles after the switch, so neither the pending expiry nor the repeat 20 cycles later fired. Switch at 22 to 29 (expiry already happened): /IRQ stays low until `$E000`. In all 19 trials, after `$E000` and `$E001` the A12 counter (full filter) expired at pulse 6 = L + 2 and not before, whether or not the CPU-mode counter had expired first.
- Evidence: run 59 (19 switch times, 11 to 29 cycles, L = 4). Confidence: High for the outcome. Resolution: one M2 cycle; the `w` that carries the switch is itself one cycle, so the boundary between "cancelled" (21) and "already fired" (22) is exact only to about one cycle.
- Observable from a NES: Yes, but only a game that switches modes around an expiry would see it.


## Register write timing

Experiments 11-15 vary the order and phase of the write signals with `wseq`. Resolution is one step (about
3 us at T=4, 1.9 us at T=0); nothing finer than that can be said. Phases: P0 M2 low, /ROMSEL high; P1 M2 high;
P2 M2 high and /ROMSEL low (window); P3 /ROMSEL high, M2 high; P4 M2 low.

**F-013: A register write is enabled by the level combination M2 = 1, R/W = 0, /ROMSEL = 0.** The order in which
the three conditions are met does not matter: /ROMSEL low first and then M2 rising, M2 first, ROMSEL low with R/W
falling inside the window, and /ROMSEL held low throughout all produce a write as soon as the third condition
holds. /ROMSEL low with M2 low never writes; M2 high and /ROMSEL low with R/W high (a read) never writes.
- Evidence: run 14 (nine window shapes, sampled after every step). Confidence: High at ~3 us resolution.
- Observable from a NES: No (only the normal shape occurs on a console).

**F-014: The register is transparent while the window is open and holds its value when the window closes.**
Data changed 10 -> 20 -> 30 inside an open window; the CHR output followed each change. After /ROMSEL rose, a
further change to 50 had no effect. A write whose data changes late in the window therefore keeps the *last*
value before the window closes.
- Evidence: run 15 (sampled after every step); run 13 shows the same from the other side (below).
- Confidence: High. Closing is tied to /ROMSEL rising in these runs; closing by M2 falling or R/W rising was not
  separated.
- Observable from a NES: Indirectly (on a real console the data bus is stable through the window).

**F-015: The data byte that counts is the one present when the window closes.** With one of two data values
placed in each of the five phases (32 patterns), the result followed only the value in P3, which is applied
about 125 ns (2 CPU cycles of the Mega) before /ROMSEL rises. Values in P0, P1 and P2 (earlier) and P4 (later)
were ignored.
- Evidence: run 13 (the corrected rerun). Confidence: High for ordering; the setup time is only bounded: data
  that arrives ~125 ns before /ROMSEL rises is captured (RP2350 item 2).

**F-016: The register address (A0, A13) counts as it is during the window, not as it is at the closing edge.**
Over 32 patterns for A0 (run 11) and A13 (run 12), the result followed only the P2 value. A change to A0 or A13
made at the same instant /ROMSEL rises (P3) was ignored.
- Confidence: Medium. A mid-window address change was not tested, so whether the decode is also transparent, or
  latched when the window opens, is not known.
- Observable from a NES: No.

**F-017: A window of about 2 us is long enough for a write.** The shortest window we can produce (one step at
T=0, ~1.9 us per phase) still wrote the register. The true minimum is unknown (RP2350 item 2).

## Pin 19

**F-043: RAMBO pin 19 has the same protection-diode signature as an input pin, not a ground pad.** Chip removed,
unpowered, diode mode on a meter (lead polarity not recorded; the same convention was used for each pair):

| Pair | Reading 1 | Reading 2 |
|---|---|---|
| pin 19 - pin 20 (GND) | OL | 0.557 V (resistance 2.78 MOhm) |
| pin 14 (PPU A12, input) - pin 20 | OL | 0.555 V |
| pin 19 - pin 40 (VCC) | 0.647 V | OL |
| pin 14 - pin 40 | 0.645 V | OL |
| pin 20 - pin 40 | 0.478 V | OL |

Pin 19 reads within 2 mV of pin 14 against both rails. A second ground pad bonded to pin 20 would read near 0 ohm
against it in both directions; it does not.
- Evidence: bench measurement 2026-10-31 (no experiment script). Confidence: High that pin 19 has input-style
  clamps to both rails; whether it is a mode/test input or something else is unknown.
- The cart netlist has pin 19 on its own net (`RAMBO_P19`) with SW1 contact 3A and no pull-up or pull-down, so with
  SW1C off the pin floats.

**F-044: With SW1C off (pin 19 floating) the pin sits at about 0 V and behaviour is unchanged.** A meter on pin 19
read 0.059 V at power-up and 0.059 V five seconds later, with nothing else connected to the net. The regression
(CHR and PRG mapping in six `$8000` modes, CPU-mode IRQ with L = 1 and 4, A12 filter at G = 16 and 15, PRG /CE
truth table: 357 steps) gave 0 signal differences between the cold start with SW1C on and the cold start with
SW1C off. Two warm controls with SW1C on were also identical to each other and to the cold control.
- Evidence: runs 38 (four logs, see index) and the bench reading. Confidence: High for the regression result;
  Medium for the cause.
- CORRECTION (see F-047): the reading was of a fresh, never-driven pin, which had simply not been charged. A
  floating pin 19 is not held low by anything; it keeps whatever level it last had. So F-044 and F-045 show only
  that a pin 19 at 0 V (floating or grounded) gives the same results as grounded. They say nothing about a
  floating pin in general.
- The regression cannot distinguish "pin 19 low" from "pin 19 does not matter", because pin 19 was low in both
  configurations.
- The power-on state with SW1C off was read separately: see F-045.
- Not tested: pin 19 driven high, or toggled while running. That is the test that can show whether pin 19 is a
  mode or test input.

**F-045: The cold power-on state is the same with pin 19 floating (SW1C off) as with it grounded.** First command
after power-up was a plain `r`: PRG A13-A17 all high, /CE high, CHR A10-A17 all low, `CIRAM_A10` low, /IRQ low.
With no register writes: CHR stayed 00 for all eight PPU A10/A11/A12 combinations and `CIRAM_A10` followed PPU A10;
PRG reads at `$8000`, `$A000`, `$C000`, `$E000` all gave bank `1F` with /CE low, and at `$6000` /CE high. After
`$E000` (/IRQ released), `$C001 = 01` and `$E001` with no `$C000`, /IRQ first went low at the coarse read at
t = 1032 (as in run 29), and at exactly t = 1026 in the one-cycle refinement on the same chip (run 30 repeat),
so the power-on latch is `FF` again.
- Evidence: run 39 and the repeat of run 30, both with SW1C OFF. Confidence: High that pin 19 floating-low gives
  no difference; one cold start in this configuration.
- Scope: pin 19 was at 0.059 V (a fresh, never-driven pin, F-044/F-047), so this shows that 0 V and grounded are
  equivalent. It does not show that pin 19 high has no effect: it has (F-046).

**F-046: With pin 19 held high, every register write stores the constant `0B` (binary 00001011), whatever data is on the bus.**
Pin 19 was driven from Mega D2 through 1 kohm, SW1C off. Raising or lowering the pin changes nothing by itself; only
writes are affected. Registers written with pin 19 high, after the value was set with the pin driven low:

| Register written (pin high) | Result |
|---|---|
| R0, R1, R2, R3, R4, R5, R8, R9 (`$8001`, index selected while low) | the register reads `0B` (R0 in 2 KB mode shows `0A` at a10 = 0, since bit 0 is the PPU A10 pass-through) |
| R6, R7, RF | PRG bank `0B` |
| `$8000` (bank select) | mode bits 5, 6, 7 cleared; the index becomes one with no visible register (consistent with index `0B`, an unused one), so later `$8001` writes have no visible effect |
| `$A000` | horizontal mirroring (bit 0 = 1, as in `0B`) |
| `$C000` | latch = 11 (`0B`): first CPU-mode expiry at t = 50 = 4 x (11 + 1) + 2 |
| `$C001` | counter restarts, mode = CPU (bit 0 = 1, as in `0B`) |
| `$E000`, `$E001` | work normally (acknowledge, enable); the data byte is ignored anyway (F-032) |

- Data independence: R0 was written with `00, 54, AA, FE, FF, 15, 30` from start values `00, 54, AA, FE`; R2 and R6 with
  four values each; `$C000` with `01, FF, 04`; `$A000` with `00, 01, 02, 03, FE, FF`. The result was the same constant
  every time. The stored value did not depend on the PPU A10/A11/A12 lines during the write (all eight combinations).
- The constant holds when the pin returns low: the changes persist.
- Reading the earlier results again: the "ignored" `$8001` writes and the "clear-only"/"set-only" appearance of
  `$8000` and `$A000` (runs 40, 41, 42, 44, 45) were this rule seen through the index becoming `0B` and the mode bits
  and mirroring bit already matching `0B`. The `$8000` matrix (run 46) shows bits 5-7 end at 0 for every S and T.
- Evidence: runs 40 (p19 = 1), 44, 45, 46, 47, 48, 49, 50. Confidence: High for `$8001` registers, `$C000`, and
  `$8000` bits 5-7; Medium for the index becoming `0B` (inferred); `$A001` and the unused indices cannot be seen.
- What it looks like: a test or initialisation input that makes the register-write data path take a fixed value.
  The original board ties it to ground, so it is never seen on a console.
- Not tested: the power-on state with pin 19 held high from before power-up (the Mega only drives it after boot);
  whether the constant depends on the write address in a way not covered (all tested addresses gave `0B`); whether the
  A12-mode counter is affected differently from the CPU-mode counter (only `$C000`/`$C001` writes were tested).
- Observable from a NES: No (pin 19 is grounded on a cartridge).

**F-047: A released pin 19 keeps its last level; only a driven low is reliably low.** After the pin had been driven
high, `p19 z` (released, high impedance) read back `net=1`, and the chip stayed in the pin-high behaviour for
several minutes. The earlier 0.059 V reading (F-044) was a fresh, never-driven pin.
- Evidence: run 43 (invalid as a comparison, but it showed this), the `p19` readback after it. Confidence: High.
- Consequence: use `p19 0`, not `p19 z`, as the low state. Runs 41 to 43 were pin-high throughout.
- Not known: how long the retained level lasts, or what the leakage path is.

## Operational notes (jig)

- **`wseq` timing (measured, run 10).** A step lasts about 30 cycles of overhead plus 4 cycles per tick
  (T=0 gives ~30 cycles = 1.9 us per step; 40 steps at T=10 added 1520 cycles, 3.8 cycles per tick). The first
  version took 59 cycles of overhead and 6 cycles per tick; the player was rewritten to precompute port values.
  These are cycle counts from Timer1, not scope measurements. A real NTSC M2 half-cycle is ~280 ns, so the Mega
  is about 7x too slow to reproduce real bus timing (see RP2350 items below).

- Pin 30 /IRQ goes direct to J2-40 (no series resistor); the 10k pull-up is R3.
- An unseated chip produced misleading results (CHR outputs not following inputs, /IRQ low). Reseating fixed it.
  Re-check seating before trusting any "dead" behaviour.
- With the barrel jack powered before the USB cable, the Mega's USB chip enumerated as the Atmel DFU device
  (`03eb:2fef`) three times. USB-only power has enumerated normally every time. Use USB only, and for a cold start
  unplug everything for 15 s before replugging USB.

## Open questions and status

(Status column as of the Mega jig, 2026-10-31. **Update 2026-11-02:** questions 1 to 6 are answered further by F-055 to F-090; what is still open is in `functional_description.md` section 9: the origin of the power-on /IRQ (F-034), the chip's own output delays below the adapter's buffer delay, voltage levels and edge rates, the CIC (question 7), pin 19's purpose and power-up behaviour, and other chips, consoles and PAL.)

| # | Question (from the first `hardware.md`) | Status |
|---|---|---|
| 1 | Register map and bank output mapping | CHR (F-006/007), PRG (F-009/010), decode (F-039 to F-042) done. Hidden state behind unused indices and `$A001` cannot be seen from the pins; `$8000`/`$8001` address aliasing over A1-A12 cannot be tested on the jig |
| 2 | PRG /CE behaviour | Answered statically (F-012); timing untested |
| 3 | IRQ counts, reload, late IRQ, mode switching | F-018 to F-021 (counts), F-024 to F-028 (reload, mode switch). F-029 to F-033 (ack, enable, repeat edges). F-036 to F-038 (A12-mode latch and period). Untested: A12 filter during the first edges after a reload, the origin of the power-on /IRQ state |
| 4 | A12 filter threshold | F-022/F-023: needs 16 M2 cycles low and A12 high across an M2 edge (steady-state, whole M2 cycles). Exact edge rules and absolute times need the RP2350 |
| 5 | Power-on register state | F-001 to F-004, F-034, F-035 (latch `FF`). Untested: power-on counter phase, the stored /IRQ state's origin, $A000/$8000 bit-level contents beyond what the outputs show |
| 6 | Pin 19 | F-043: has input-style clamp diodes to both rails, so it is an input tied low on the original board. Pin 19 high makes every register write store the constant `0B` regardless of data (F-046); it is an input that the original board grounds. Released does not mean low (F-047). Open: power-on state with the pin held high from before power-up, A12-mode counter behaviour with the pin high |
| 7 | CIC | Not tested |

## Open items for the RP2350 adapter (not possible or not meaningful on the Mega)

(2026-11-02: the plan for building and using the adapter is `docs/rp2350_adapter_plan.md`. **Status after the adapter work:** item 2 (write window) is answered by F-082 and F-089; item 3 (delays) by F-083 and the console captures (F-064 to F-076), except the chip's own few-ns share; item 4 (A12 filter in absolute time) by F-084 and F-081; item 5 (IRQ latency) by F-065, F-067 and F-090; item 7 (cold starts) by F-078, F-079, F-085 and F-088. Not done: item 1 at real speed was covered by replays (F-080), item 6 (frame-rate A12 patterns on the adapter), item 8 (high-impedance bus) and item 9 (soak).)

The RP2350 setup (`j2_rp2350_pinmap.csv`) adds software power switching (GPIO4 `PWR_EN`), tri-statable drivers
(GPIO15 `OE_EN`), a 150 MHz clock with PIO state machines, and buffered outputs. Items that need it:

1. **Real-speed bus timing.** The Mega cannot step faster than ~1.9 us, against a ~280 ns M2 half-cycle on a real
   NES. Needed: exact NTSC (and PAL) M2/ROMSEL/R/W/address phasing, run continuously, to check that findings from
   slow stepping hold at real speed.
2. **Write window setup/hold in nanoseconds.** F-013 to F-017 show the write is level-sensitive and closes with the
   window, but only to ~2 us resolution. Needed: setup/hold of D0-D7, A0, A13, A14 against the closing edge, which
   signal (M2, /ROMSEL, R/W) is the one that closes it when they fall at different times, the minimum window width,
   and whether the address decode is transparent or latched at window open.
3. **Propagation delays and glitches.** /CE versus M2 and /ROMSEL edges, CHR and PRG address response to bank
   register writes and to PPU A10-A12 changes, `CIRAM_A10` response. Needs timestamped capture of every output
   transition (PIO sampling to DMA); the Mega polls outputs no faster than ~2 us. The level-shifter delay of the
   74HCT541 / 74LVC541A path must be calibrated out.
4. **A12 filter in absolute time.** The filter threshold is probably a count of M2 cycles low (open question 4),
   but pulse widths below ~2 us (short A12 highs and lows, glitch rejection) cannot be generated on the Mega.
5. **IRQ latency.** Delay from the counting edge to /IRQ asserting, in M2 cycles and ns, including the reported
   late IRQ. On the Mega this is limited to whole-cycle steps and ~2 us sampling.
6. **Frame-rate IRQ emulation.** Real PPU A12 patterns (eight rising edges per scanline, correct M2 relationship)
   at full rate over whole frames (~29780 CPU cycles), and long CPU-cycle-mode counts, run unattended. The Mega can
   do functional counts at slow speed, not frame-rate patterns.
7. **Repeatable cold starts.** Power-cycling in software (`PWR_EN`) allows hundreds of cold starts for power-on
   state variation (F-001 to F-004 are from four starts) and sweeps of power-supply ramp rate and brownout
   behaviour, with no unplugging. Also removes the barrel-jack/DFU problem from the cold-start procedure.
8. **High-impedance data bus.** `OE_EN` tri-states the drivers, so floating inputs and bus-hold behaviour on D0-D7
   and the control lines can be tested. The Mega always drives them.
9. **Soak and statistics.** Long unattended runs repeating a sequence thousands of times to find rare
   mis-latches or races.

Things the Mega can still do (no timing dependence): IRQ functional behaviour (reload value, enable, acknowledge,
mode switch at M2-cycle granularity), A12 filter in whole M2 cycles, remaining register decode (`$8000` bit 4,
unused indices, `$A001`, other `$A000` bits), pin 19 behaviour, and write-order experiments with `wseq`.

## F-058 (G4 on real hardware, 2026-11-01)
ROM g4_cpu_irq passes 10/10 on the real cart (PXL_20261101_173407801.jpg). Interrupt-PC-capture measurements
give tau(L) = 4L + 7 (INFO line 07 17 03: tau(0)=7, tau(4)=0x17, tau(255) low byte 03), i.e. slope exactly 4 cycles per L
including L 0->1 (MesenCE fails that step: tau(0)=tau(1)). Repeat period 4(L+1), expiry-while-disabled lost,
$E000/$E001 leave the counter alone, $C001 restarts the counter and keeps /IRQ, latch taken by cycle 5,
$C001 bit0=0 cancels a pending expiry: all confirmed from the CPU side. The sim's absolute offset is 3 cycles lower (tau(0)=4).

## F-059 (G5 on real hardware, 2026-11-01)
ROM g5_a12_irq passes 10/10 on the real cart (PXL_20261101_180621473.jpg), power-up start. Confirmed from the CPU side with PPUADDR-driven A12:
first expiry at pulse L+2 for L = 0..8 and 16 (so no L <= 1 special case on the chip); repeat period L+1 for L = 1..8 and 16;
`$C000` written before the first counted pulse is used and one written after it is not; filter not full at `$C001` gives L+1;
`$E001` does not release /IRQ, `$E000` does, an expiry while disabled is lost; A12 to CPU and CPU to A12 mode switches carry nothing over (pulse 6).
Filter sweep (INFO `10 FC 07`): gaps of 13 and 15 cycles from fall to next rise do not count; 16, 17, ... 24 all count, so the smallest counted gap is 16
cycles on this CPU/PPU alignment (same as F-022/F-051: 16 M2 falls). The ROM does not assert 16 and 17 because the alignment may move the threshold by one.

## F-060 (G6 on real hardware, 2026-11-01)
ROM g6_raster, first build, on the real cart (PXL_20261101_182726997.jpg): 10 of 11 tests passed.
- With the sprites at $1000 and the background at $0000 (also 8x16 sprites, and with the CHR inversion bit set) the A12 counter
  puts the interrupt on the scanline the latch names: the smallest latch whose interrupt sees a sprite-0 hit on line H0 is H0 (offset 0)
  for H0 = 40, 96 and 152. The 241 counted pulses per frame give exactly 120, 240 and 15 interrupts in 8 frames for L = 15, 7, 127,
  and CPU-cycle mode with L = 255 gives 232. With both tables at $0000 no interrupt comes.
- With the background at $1000 and the sprites at $0000 the smallest latch was 97 for H0 = 96: the interrupt comes one line earlier (L-1).
  MesenCE gives the same. Explanation (consistent with F-052, not isolated by a separate experiment): the PPU address bus keeps A12 high
  after the last background fetch of the frame, so A12 is already high when `$C001` is written in vblank, the first pulse is not
  swallowed and the interrupt comes at pulse L+1. My first model assumed A12 low in vblank and was wrong for this configuration.
- Both tables at $1000, L = 0, 8 frames: 1 interrupt (INFO). MesenCE counts 8; the model 7 (not corrected, informational). **Later explained by F-075**: with latch 0 only the reload after `$C001` expires, so any waveform with at least one counted pulse gives one interrupt; MesenCE and the old model expire on every reload to 0.
- Confirmation (2026-11-01, PXL_20261101_184033171.jpg, PXL_20261101_183955076.mp4): the corrected G6 passes 11 of 11 on the real cart, test 5 included (smallest latch 97 for H0 = 96 with the background at $1000). The demo shows the colour bands with horizontal, straight edges, stable from frame to frame.

## Findings from the test ROMs on a real console (2026-11-01)

The jig findings above were measured at about 2 us per bus step. The test ROMs (`rom/`, groups G1 to G6) run on a real NES
(front loader, NTSC) with the chip on the development flash cart, so they exercise real-speed bus cycles, the real CPU's
instruction sequences and the real PPU. Results are pass/fail against the chip model (`reference/rambo1.py`), so a pass confirms
the model at real speed; the failures that matter are in `docs/test_rom_design.md`.

**F-061: Power-on state seen from a real CPU (G1, 5 of 5 after a cold start).** With the APU frame IRQ inhibited and I clear, an interrupt
is taken at once (/IRQ asserted) and a write to `$E000` releases it; all three switchable PRG windows read bank `$1F`; every CHR window
reads bank 0 in the 1 KB layout; mirroring is vertical although the iNES header says horizontal; with `$C001` = 1 and no `$C000` write the
first interrupt comes 1026 cycles (+-8) later (latch `$FF`).
- Evidence: G1, PXL_20261101_060446215.jpg. Confidence: High. Agrees with F-001 to F-004, F-034, F-035 (jig).
- **The console reset button does not reset the mapper.** After a reset, G1 fails only test 1 (`/IRQ` not asserted), because the first run's `$E000`
  had disabled the interrupt and the chip kept that state; the banks and mirroring were unchanged. (PXL_20261101_060411948.jpg.) G1 never
  changes banks, so this shows only the interrupt state persisting; the chip evidently has no reset input.

**F-062: Banking and register decode at real speed (G2, 14 of 14).** PRG R6, R7, RF with several banks and the P bit; PRG bank width is 5 bits
(`$20+n`, `$40+n`, `$80+n` read bank n); CHR R0 to R5 in both layouts, the C inversion and every window; odd R0/R1 values in 2 KB mode map the
pair (R and `$FE`, R or 1); R8 and R9 act only when K = 1 and keep a value written while K = 0; index A-E and `$8000` bit 4 change nothing;
changing only K, P or C with an `$8000` write (no `$8001`) changes the mapping at once; `$A000` bit 0 only; `$A001` writes change no bank, mirroring
or interrupt state.
- Evidence: G2, PXL_20261101_065506451.jpg and five cold starts plus resets, all green. Confidence: High. Agrees with F-006 to F-011, F-039 to F-042, F-049, F-053.
  (An earlier screen corruption during G2 bring-up was a dirty connector, per the user, and cleaned; it was not a chip effect.)

**F-063: Bus behaviour at real speed (G3, 7 of 7, flash `/OE` wired to the RAMBO PRG `/CE` output).**
- No bus conflict: writes to ROM addresses whose ROM byte differs from the data store the data written, not an AND or OR with the ROM byte.
- Read-modify-write instructions leave the final value: `INC`, `DEC`, `ASL`, `LSR` on `$8001` (read, write old, write new) and `INC` on `$8000` and `$A000`.
  The second of two back-to-back writes wins, so back-to-back windows work at real speed.
- **Aliasing: A1-A12 take no part in register decode.** A write to `$8000 | (1 << k)` or `$A000 | (1 << k)` for each k = 1 to 12 behaves as the register at the same
  A0/A13/A14. (Resolves the open item; the jig did not wire A1-A12.)
- Writes without /ROMSEL (addresses `$4020`-`$7FFF`, seen through the IRQ registers, whose A14 = 1 addresses sit there) do nothing; reads of any register address, including `$E000`
  and `$E001`, change nothing and do not touch the interrupt.
- Open-bus reads at `$4020`, `$5000`, `$6000` return `$FF` on this cart; that comes from the cart's 1 kohm data pull-ups, not from the chip.
- Evidence: G3, PXL_20261101_071233730.jpg. Confidence: High for the points above; the open-bus value is a property of the cart.

## Logic analyser measurements in a running console (2026-11-01)

First captures of the chip in the console with a 24 MHz / 48 MHz USB logic analyser on the J2 header (`docs/logic_analyzer_guide.md`, capture set B:
M2, R/W, /ROMSEL, PRG /CE). The test ROM was G6 on its result screen, whose idle loop reads the ROM at $E000 and up. Timing figures are statistical
(see `docs/timing_measurements.md`), valid to a few nanoseconds, and relative: M2, R/W and /ROMSEL are seen through the cart's 220 ohm series resistors and the
analyser's input capacitance (an extra delay of the order of 2 to 3 ns, not measured), while PRG /CE comes straight from the chip.

**F-064: PRG /CE follows the truth table of F-012 in a real console, and its edges are within 8 ns of the controlling inputs.**
- 1,000,000 samples at 24 MHz and 24 bursts of 6000 samples at 48 MHz: with M2 = 1, R/W = 1 and /ROMSEL = 0 the output /CE is low in every stable sample
  (260,160 and 55,816); with M2 = 0 or /ROMSEL = 1 it is high in every stable sample. R/W = 0 (writes) was seen only to the APU, so /CE during a mapper write was not captured here.
  The only samples that disagree are one-sample edge lags (1.15% of the enabled samples at both rates: the one sample after the enabling edge).
- Timing relative to M2 (mean over 63,900 edges at 24 MHz and 4,600 at 48 MHz, which agree to 0.1 ns): /ROMSEL falls **28.2 ns** after M2 rises and rises **13.2 ns** after M2
  falls (the console's decode, not the chip). **/CE falls 3.9 ns after /ROMSEL falls** (/ROMSEL being the later input) and **rises 7.1 ns after M2 falls**, about 6 ns **before**
  /ROMSEL rises. So on the trailing edge /CE is controlled by M2, not by /ROMSEL: the chip gates /CE with M2, as the jig result F-012 required.
- Evidence: `captures/setB_24m_g6result.sr`, `captures/b48/burst_*.sr`, script `tools/la_setb_analysis.py`. Confidence: High for the truth table and ordering; Medium
  for the nanosecond figures (statistical, one console, the input-side RC delay not removed).
- Observable from a NES: not by software; the data are for emulator timing and FPGA implementers.

**F-065: The A12 counter against the real PPU waveform and /IRQ in a console (capture set A, G6 raster demo, 24 MHz, 41.7 ms = 2.5 frames).**
- The PPU's A12 has two kinds of rise per line. Rises preceded by A12 low for only **1 or 2 M2 falls** (4,263 of them: the toggles inside the sprite fetches, high pulses
  of about 750 ns) and rises preceded by **93 or 94 M2 falls** of low (609 of them, spaced 63.6 us = one line): the second kind is the one the chip counts. Nothing lies between 2 and 93, so the
  real waveform does not distinguish any filter threshold from 3 to 92 falls (F-022, F-051 measured 16 on the jig).
- 241 counted rises per frame: 609 counted rises in 2.5 frames, spaced one line (63.6 us), with a gap of 22 lines (1.398 ms) between the last visible line and the pre-render line. The demo configuration
  (sprites $1000, background $0000) holds A12 **low through the whole vertical blank** (1.386 ms stretches), consistent with the explanation of F-060.
- /IRQ falls once per demo interrupt, 3.81 ms apart (60 lines), exactly 60 counted rises apart inside a frame and **61 across the frame boundary** (the re-armed counter's swallowed pre-render pulse plus
  lines 0 to 59): the interrupt is on line L = 59 (F-021, F-060).
- **Timing of /IRQ.** The clocking rise of A12 is followed by the first M2 fall with A12 high (250 to 458 ns later), and **/IRQ falls at the next M2 fall, 8 ns later on average** (0 or 1 sample of 41.7 ns, mean 0.20):
  one M2 cycle after the clocking fall, as F-050 found on the jig. /IRQ was low 28 us per interrupt (the demo handler's acknowledge).
- Power-on capture (first 42 ms after the supply, trigger on the first A12 edge, `captures/setA_poweron_boot.sr`): /IRQ is low **from the first sample**, before M2 has started; M2 begins about 21 ms later.
- Evidence: `captures/setA_g6_demo.sr`, `captures/setA_poweron_boot.sr`, script `tools/la_seta_analysis.py`. Confidence: High for the structure, counts and the /IRQ ordering; the 8 ns
  figure is statistical (one capture, 10 interrupts), +-5 ns and not corrected for the analyser input.

**F-066: A register write in a running console: /CE stays high, the output follows the data inside the write window (timing probe phase 1, `captures/p1_data_24m.sr`, `captures/p1_data_48m/`).**
- ROM: `$A000` written `$00` and `$01` alternately every 6 and 9 CPU cycles, PPU address `$2400` (A10 = 1, A11 = 0), so CIRAM A10 = 1 for vertical and 0 for horizontal.
- **/CE is high during every write cycle**: 66,750 samples with M2 high, /ROMSEL low and R/W low, none with /CE low (F-012 on a real console). During reads of `$8000+` it is low in 98.8 % of samples (the rest are edge samples).
- **All 9,940 CIRAM A10 changes (24 MHz) lie inside the write window** (M2 high, /ROMSEL low, R/W low); none outside. The data was stable before M2 rose, so the output is transparent: it follows D0 as soon as the window opens (level-sensitive, consistent with the jig result).
- Delays, statistical sub-sample estimates, 24 MHz and 48 MHz agree to 1.3 ns: /ROMSEL falls 26.5 ns after M2 rises (F-064: 28.2 ns, consistent). CIRAM A10 **rising** (horizontal to vertical) is 13 ns after /ROMSEL falls (40 ns after M2 rises); CIRAM A10 **falling** (vertical to horizontal) is 101 ns after /ROMSEL falls (128 ns after M2 rises): this is when the CPU's data arrives (below). The write window is about 350 ns long, so both are inside it.
- **The rising/falling asymmetry is the CPU's data timing, not a chip delay.** Before the CPU drives the byte, D0 still holds the previous bus value (the high byte of the address in the instruction, `$A0`, so D0 = 0). For a write of `$00` the data was already right and CIRAM A10 rose 13 ns after /ROMSEL fell; for `$01`, D0 only rose about 100 ns into the window, and CIRAM A10 fell **0 to 3 ns after D0 rose** (D0 edge and CIRAM edge in the same sample in 4,625 of 4,970 cases, one sample later in 345: about 3 ns). So the mirroring output follows D0 transparently, with a delay of a few ns, and the data on a console becomes valid about 100 ns into the window (see F-069).
- Which edge closes the window is not shown by this ROM: the CPU holds the data stable past the end of the cycle. See F-069 for the control register.
- Caveat: +-5 ns, includes the 220 ohm series resistor and analyser input (about 2-3 ns). One chip, one console.
- Evidence: script `tools/la_p1_analysis.py`. Confidence: High.

**F-067: /IRQ assertion and release timing in CPU-cycle mode in a console (timing probe phase 3, `captures/p3_irq_24m.sr`, `captures/p3_irq_48m/`).**
- ROM: latch 40, CPU mode; the handler writes `$E000` then `$E001` and returns. /IRQ falls every **164.0 M2 cycles** (455 events at 24 MHz, 48 at 48 MHz; min and max within 0.1 cycle), as F-058 predicts (4 x 41).
- **/IRQ falls 10 ns after an M2 fall** (10.3 ns at 24 MHz, 10.9 ns at 48 MHz): the output changes on the M2 falling edge in CPU mode too, as F-050 found for A12 mode (8 ns).
- **/IRQ rises during the first write, the `$E000` cycle, in 455 of 455 cases** (48 of 48), not in the `$E001` write. It rises **130 ns after /ROMSEL falls** (130.8 ns at 24 MHz, 129.3 ns at 48 MHz), 157 ns after M2 rises, and about 200 ns before M2 falls. So the release happens inside the write window, not at its end: the transparent, level-sensitive window of F-066 applies to the acknowledge too.
- /IRQ low time in this loop is 12.6 to 14.7 M2 cycles (CPU latency, not a chip property).
- Compare F-066: CIRAM A10 follows a mirroring write after 13 ns (rise) or 101 ns (fall); the acknowledge takes 130 ns, so the register-write response is 13 to 130 ns depending on the output.
- Caveats: +-5 ns; /ROMSEL is seen through its 220 ohm resistor, /IRQ is direct from the chip. One chip.
- Evidence: script `tools/la_p3_analysis.py`. Confidence: High.

**F-068: The CHR and CIRAM outputs follow PPU A10-A12 combinationally, within about 10 ns (timing probe phase 5, `captures/p5_chr_24m.sr`, `captures/p5_chr_48m/`).**
- ROM: 1 KB CHR windows R0..R3 = 0, 1, 2, $FF; PPU address cycled `$0000`, `$0400`, `$0800`, `$1000` (rendering off). 6,086 address changes at 24 MHz, 427 at 48 MHz. Outputs were `00 01 02 FF` in every window, as F-005..F-010 say.
- Single-line changes give clean delays from the PPU edge to the output edge: A10 rising to CHR A10 rising **4 to 5 ns**; A10 rising to CIRAM A10 rising **1 ns**; A12 falling to CHR A10, A11 and A17 falling **6 to 7 ns**, all three equal within 1 ns. A10 falling to CIRAM A10 falling is **5 to 12 ns** (the PPU lines A10 and A11 change together within one sample, so this is bracketed, not exact).
- On changes of several PPU lines (001 to 010, 010 to 100) the outputs follow the first line that moves: the CHR bank number depends on the window the intermediate address selects, so an output can move up to one sample before the last PPU line settles.
- All outputs change within **about 10 ns** of the PPU address, below what this analyser resolves (+-5 ns, sample period 41.7 ns at 24 MHz). The PPU lines are seen on the J2 side of the 220 ohm resistors, so the true delay from the chip's own pin is a few ns shorter. The paths are combinational (no M2 or clock involved): an FPGA model can treat the CHR and CIRAM outputs as a function of the registers and PPU A10-A12 with no registered delay.
- Contrast F-066: CIRAM A10 follows a mirroring write 13 ns after /ROMSEL falls or about 3 ns after the data line rises (the 101 ns there is when the CPU's byte arrives), and follows **PPU A10** in 1 to 12 ns.
- Evidence: script `tools/la_p5_analysis.py`. Confidence: High that the delay is under 10 ns; the exact figure is not resolved.

**F-069: A control-register write ($8000) takes effect at the END of the write cycle, 15 ns after the M2 fall (timing probe phase 2, `captures/p2_ctrl_24m.sr`, `captures/p2_ctrl_48m/`).**
- ROM: `$8000` written `$80` and `$00` alternately (the C bit), R0 = `$FE`, R2 = `$00`, PPU address 0, so CHR A11 to A17 switch between 1 (R0) and 0 (R2). 9,941 writes at 24 MHz, 719 at 48 MHz.
- **All 19,882 output changes (CHR A11 and A17, 24 MHz) occur within one sample of the M2 fall that ends a write cycle; none at any other time**, including write cycles where D7 had been stable since before the window opened. So this register is **not transparent**: the change is made when the cycle ends, not while the window is open. (Compare `$A000`, F-066, which follows the data line during the window.)
- **CHR A11 and A17 change 14.7 to 15.1 ns after M2 falls**, 0 to 1 ns after /ROMSEL rises (/ROMSEL rises 13.2 ns after M2 falls, F-064); rising and falling edges are equal within 0.4 ns, and CHR A11 and A17 change in the same sample in 99.3 % of cases (+-1 sample otherwise). Whether the chip acts on the M2 fall (internal delay about 15 ns) or on /ROMSEL rising (about 1 ns) cannot be separated: the two edges are 13 ns apart and the resolution is +-5 ns.
- Data setup: D7 was stable for at least 200 ns before the M2 fall in every write (the CPU's byte arrives about 100 ns into the window, F-066); the hold time after the M2 fall was not measured here.
- **This contradicts a general reading of F-014** ("every register is transparent while the window is open"): that was found on the jig at about 3 us resolution, probably on the bank data register. The control register behaves as latched at the end of the cycle. *Update:* the data register `$8001` was measured on a console in F-070 (transparent for the CHR registers), and F-089 (adapter) then showed that R6, R7 and RF are not transparent.
- Evidence: script `tools/la_p2_analysis.py`. Confidence: High for the timing and for non-transparency of `$8000`; Medium for what it means for other registers.

**F-070: The bank data register ($8001) is transparent on a console; the control register ($8000) is not (timing probe phase 6, `captures/p6_bank_24m.sr`, `captures/p6_bank_48m/`).**
- ROM: `$8001` written `$FE` and `$00` alternately, R0 selected, PPU address 0, so CHR A17 follows D7 (R0 bit 7) and CHR A11 follows D1 (bit 1). 9,940 writes at 24 MHz, 717 at 48 MHz.
- **All CHR A11 and A17 changes (9,940 of 9,940, and 717 of 717) occur inside the write window**, none at the M2 fall. Compare `$8000` (F-069): every change at the end of the cycle. The two registers behave differently.
- The output follows the data line as it arrives: with the stale bus value already correct, CHR A17 rises **20 ns after /ROMSEL falls**; when D7 arrives about 100 ns into the window (the CPU's byte, F-066), CHR A17 follows **10.0 ns after the D7 edge** (24 and 48 MHz agree). CHR A11 follows D1 the same way: 21 ns after /ROMSEL falls when D1 was already right, 101 ns when it arrives later. 24 and 48 MHz agree to 1.3 ns.
- So the transparent data path costs about 10 ns (data in to bank out) and the window opens about 20 ns after /ROMSEL falls ($A000: 13 ns, 3 ns from D0; the difference is within the 5 ns resolution plus the different output).
- **Summary of what a console shows:** `$8001` (bank data) and `$A000` (mirroring) are transparent while the window is open (F-066, F-070); `$8000` (control) takes effect at the end of the cycle (F-069), 15 ns after M2 falls. F-014's blanket statement holds for the data registers on the jig and now on a console; the control register is the exception. Other registers (`$C000`, `$C001` and RAMBO-only ones) are not measured on a console.
- *Update (F-089):* this holds for the CHR data registers R0 to R5, R8, R9 only; R6, R7 and RF (PRG) are not transparent. Which registers are transparent, and the exact closing edge, are in F-082 and F-089.
- Evidence: script `tools/la_p6_analysis.py`. Confidence: High.

**F-071: An `$E001` write in the same M2 cycle as a CPU-mode expiry enables it in time; one cycle later is too late (timing probe phase 7, `captures/p7_race_24m_1..3.sr`).**
- ROM: CPU-cycle mode, latch 4, interrupts masked. Disabled before `$C001`; `$E001` written so that its write cycle is j cycles after the `$C001` write cycle, j = 18 to 26. The first expiry is 22 cycles after `$C001` (F-058: 4 x 5 + 2), the next 42.
- **For j = 18 to 22, /IRQ asserted at cycle 22 in every block; for j = 23 to 26, the cycle-22 expiry was lost and /IRQ asserted at cycle 42 in every block.** 2,819 blocks over three 24 MHz captures, about 312 per j: 2,817 matched this exactly (the other two are one `-` each, a missing release at the end of a capture). No intermediate result, no j with a mixed outcome. This is exactly the reference model's prediction.
- So a write cycle that is the expiry's own cycle (j = 22) already counts: the enable flag is effective by the M2 fall that ends the cycle, consistent with the `$E001` register being set during the write window (about 200 ns before M2 falls), as for the other transparent registers (F-066, F-070). The expiry is a decision at the M2 fall; the flag must be in place before it.
- Caveat: this shows the order at cycle resolution. Because j = 22 and j = 23 are the only cycles that straddle the boundary and the outcome flips cleanly between them, nothing finer is needed to implement it: write effects are visible to the M2 fall of the same cycle.
- Evidence: script `tools/la_p7_analysis.py 7`. Confidence: High.

**F-072: An `$E000` write in the same M2 cycle as a CPU-mode expiry prevents it; one cycle later is too late, and the interrupt is released in the following cycle (timing probe phase 8, `captures/p8_race_24m_1..3.sr`).**
- ROM: CPU-cycle mode, latch 4, `$E001` written early (cycle 8), `$E000` written so that its write cycle is j cycles after the `$C001` write cycle, j = 18 to 26 (expiry at cycle 22).
- **For j = 18 to 22 (including the expiry's own cycle), /IRQ never asserted. For j = 23 to 26, /IRQ asserted at cycle 22 and was released at cycle j** (the cycle of the `$E000` write). 2,819 blocks, 312 to 314 per j, **no exceptions**. This is exactly the reference model's prediction.
- With F-071: **a write to `$E000` or `$E001` is in effect for the expiry decision made at the M2 fall that ends the same cycle** (the model order: writes of a cycle, then the M2 fall). An enable in the expiry cycle counts (F-071), a disable in the expiry cycle stops it (here), and one cycle later is too late for both. That matches the transparent window of F-066/F-070 and the 130 ns /IRQ release inside the window (F-067): the flag changes about 200 ns before the M2 fall that makes the decision.
- Evidence: script `tools/la_p7_analysis.py 8`. Confidence: High.

**F-073 (WITHDRAWN: a bug in the timing probe ROM, not a chip behaviour).** The early /IRQ seen in probe phases 10, 13, 14 and 17, and the silence of phase 9, came from the data written to `$C001`, which was not the 0 that the ROM was meant to write. The probe's cycle-padding macros (`PAD`, `PADG`) burned cycles with `lda $00`, which loads A from zero-page `$00` (`ptr`, the low byte of the last string pointer printed to the screen). After the first iteration of every loop, `sta MAP_IRQMODE` therefore wrote that stray byte, whose bit 0 depended on where the assembler had put the strings: odd in some builds (CPU-cycle mode, latch 0: first expiry 4(0+1)+2 = 6 cycles after `$C001`, so /IRQ falls at `$C001` + 6 when the `$E001` four cycles after `$C001` has enabled it), even in others (A12 mode, nothing to clock). Evidence: the D0 capture of phase 17 (`captures/invalid_f073/pwr/p17_cold_1.sr`, `tools/la_d0_analysis.py`): in all 653 blocks D0 was 1 at the end of the `$C001` write window; the reference model with `$C001` data 1 asserts at exactly cycle 6, as measured. **The reference model was right; the chip is not anomalous.** The padding now uses `bit $00` (A untouched) and `rom/tools/probe_check.py` checks that every `$C001` write in the A12-mode phases has bit 0 = 0. The original notes follow, kept as the record of how the bug was found.

**F-073 (open, [C] observation): In a loop of `$E000`, `$C001` (A12 mode, latch 0), `$E001` at +4 cycles, /IRQ goes low 3 cycles after the `$E001` with no A12 pulse; with `$E001` 170 cycles after `$C001` it never goes low. The reference model predicts neither (timing probe phases 9 and 10, `captures/invalid_f073/`).**
- ROM: rendering on (sprites `$1000`), latch 0, a 228-cycle loop. Phase 9: `$E000` at cycle 3, `$C001` (data 0) at 7, `$E001` at 177. Phase 10: `$E000` at 3, `$C001` at 7, `$E001` at 11, `$E000` at 177. The counted A12 pulses (filter rule) are one per line, 113 to 114 cycles apart, as expected (614 in 2.5 frames).
- **Phase 9:** /IRQ never went low in 2,396 iterations over eight captures, including about half of them in which the model has the `$E001` in place before the expiring pulse (model: /IRQ one cycle after the clocking fall).
- **Phase 10:** /IRQ went low **at cycle 7 after the `$C001` write (3 cycles after the `$E001`)** in every one of 951 iterations, whatever the A12 pulses did: first pulse early or late in the iteration, and the 78 iterations in vblank with no pulses at all, and was released by the `$E000` at cycle 177 (1 cycle later). The model predicts /IRQ only at the clocking fall of the second counted pulse.
- The model is right about the sequences in G5 and G6 (all pass on the chip), which use the same register order but start the sequence with `$E000` about 40 cycles before `$C001` and with A12 pulses from `$2006`. Candidates: (1) the `$E000` 4 cycles before `$C001` matters (a short gap, or `$E000` while /IRQ is low); (2) latch 0 behaves differently when the counter has expired before `$C001`, with an expiry flag that `$E000` clears from the pin but not from the counter and that `$E001` exposes again; (3) a one-shot internal event shortly after `$C001` (like the 5-cycle latch capture in CPU mode, F-028) that asserts if enabled in time (phase 10) and is lost if enabled late (phase 9). Not settled.
- **Phase 11 (gap sweep, rendering off, no A12 pulses, latch 0; `captures/p11_sweep_l0_24m_*.sr`, `tools/la_p11_analysis.py`):** `$E000`, `$C001`, `$E001` with every combination of g1 = 4, 8, 16, 24, 44 and g2 = 4, 6, 9, 14, 24, 44, 100 cycles (938 blocks, 26 to 27 per combination): **/IRQ stayed high in every block**, including g1 = 4, g2 = 4, the same spacing as phase 10. So the early /IRQ of phase 10 is not a function of the register sequence alone: it needs something from the PPU's activity (rendering on, or the A12 pulses and the counter state they leave behind). Phases 13 and 14 (the phase 10 loop with rendering on and no pulses, and with rendering off) are built to separate these.
- **Phases 13 and 14** (the phase 10 loop with rendering on and both tables at `$0000`, so A12 stays low; and with rendering off; `captures/invalid_f073/p13_*`, `captures/invalid_f073/p14_*`): **/IRQ went low 3 cycles after the `$E001` in every block** (653 and 652 blocks) and stayed low until the `$E000` 166 cycles later. So neither the A12 pulses nor rendering matter: the loop itself does it. The bus pattern in the last 14 cycles before the `$E001` is the same as in phase 11's g1 = 4, g2 = 4 block, where /IRQ stayed high. What differs: (a) the loop is exactly 228 cycles, a multiple of 4, so every `$E001` sits at the same alignment to any free-running 4-cycle count, while the phase 11 blocks have variable lengths and each capture there shows one alignment for a given block (13 or 14 blocks, one alignment per capture, different between captures); (b) in phases 10, 13 and 14 the `$E000` that opens an iteration is preceded by a `$E000` that released an asserted /IRQ.  Phase 15 (231-cycle loop, alignment steps by 3 per iteration) tests (a).
- **Observation (clue, not an explanation):** in phases 10, 13 and 14 /IRQ went low exactly **6 cycles after the `$C001` write** (and 2 after the `$E001`). 6 is the first-expiry time of the CPU-cycle counter with latch 0 (4(L+1)+2, F-058). That fits the chip being in CPU-cycle mode in those loops (so the `$C001` data of 0 did not select A12 mode, or the mode did not change) with `$E001` landing before the expiry. It does not explain why the same loop, rebuilt with straight-line padding in place of `dex`/`bne` delay loops (phase 16, all periods 224 to 236 including 228, cold start, 3 captures, 1,055 iterations), is silent.
- **Not yet an emulator rule.** The reference model and the emulator guide are unchanged; the caveat is recorded in `docs/emulator_guide.md` section 6. The sequence `$E000`, `$C001`, `$E001` is how most MMC3-style code initialises the counter, so this matters. The next probe sweeps the gaps with no PPU activity (phases 11 and 12).
- Evidence: scripts `tools/la_p9_analysis.py 9` and `10` (they show the mismatches), plus the per-iteration timeline in this entry. Confidence: High that the chip differs from the model in this loop; the cause is open.
- **Power cycles (phase 14 again, `captures/pwr/`):** three more cold starts (15 s off, power on with START + DOWN), no reprogramming: /IRQ went low 3 cycles after the `$E001` in 326 of 326 blocks each time. So the early /IRQ is **not** a random power-up state: it follows the loop (228 cycles, asserts) and not the 231-cycle loop of phase 15, which was silent at all four alignments to a 4-cycle count (644 blocks, `captures/invalid_f073/p15_*`), and not the phase 11 sweep. Neither code address parity (phases 13 and 14 have opposite parity and both assert, phase 15 has the parity of phase 13 and is silent) nor rendering nor A12 pulses decides it. Next: a scan of the loop period (phase 16).

**F-074: In A12 mode the enable flag is tested at the fall at which /IRQ falls (one fall after the clocking fall): an `$E001` written in that cycle is still in time, an `$E000` written in it prevents the assertion (timing probe phases 9 and 10, fixed image, `captures/p9c_*`, `captures/p10c_*`).**
- ROM: rendering on (sprites `$1000`), latch 0, a 228-cycle loop: `$E000` (cycle 3), `$C001` with data 0 (cycle 7), `$E001` 170 cycles after `$C001`. The loop drifts 2/3 cycle per iteration against the PPU's line pairs, so the `$E001` write sweeps across the counter's clocking fall (about 1,460 iterations in five captures). (The earlier phase 9 and 10 runs were invalid: F-073, a ROM bug.)
- In every iteration in which the chip asserted /IRQ, the `$E001` write cycle was at or before the assertion cycle, never after: write cycle minus assertion cycle = -23 to **0** (14 iterations at 0), no value above 0. The model (reference/rambo1.py as of F-072) requires the `$E001` by the *clocking* cycle, one cycle earlier; it tests the enable flag at the clocking fall and schedules the assertion for the next fall. The chip tests it at the assertion fall.
- **Phase 10 (the `$E000` side):** with the `$E000` in the assertion cycle the chip did not assert in 11 of 14 iterations (the model of F-072 asserts and stays low); with the `$E000` one cycle later the chip asserts and releases exactly as modelled.
- **Check by replay:** the reference model, changed so that the enable flag is tested at the assertion fall (and F-075), was replayed over the captured bus (writes, A12 at each M2 fall): **0 mismatches in /IRQ over 371,265 cycles in phase 9 and 371,264 cycles in phase 10** (1,471 and 1,482 iterations, five captures each). The unchanged model gave 7,474 and 1,232 mismatched cycles.
- **A12 sampling point.** The replay matches with the A12 level taken from 0 to 2 samples (0 to 83 ns) after the M2 fall (as seen at J2, before the 220 ohm resistor); one sample before the fall (41 ns), and three samples after (125 ns), it does not. So in this console an A12 rise that arrives up to 41 ns before the M2 fall still counts at that fall (the setup time is below 41 ns), and the A12 level at 83 ns after the fall is what the chip used. One PPU/CPU alignment only; the A12 edge sits at a fixed phase against M2 within a run.
- The A12 level at the M2 fall is ambiguous in these captures (A12 rises within one sample of the M2 fall: about 4 % of cycles, the same in every capture), so the offset d to the clocking cycle is uncertain by one cycle; the result above uses the chip's own assertion cycle and is not affected. Evidence: `tools/la_p9_analysis.py 9`. Confidence: High that the latest `$E001` that counts is in the assertion cycle. The `$E000` side is to be taken from phase 10.

**F-075: With latch 0 in A12 mode, the counter expires on the reload that follows `$C001` and not on the automatic reload at zero (same captures).**
- When the filter was full at `$C001` (the first counted pulse swallowed, the second reloading the counter) and the `$E001` came before the second pulse, the chip asserted /IRQ in 181 of 184 iterations at that second pulse, as the model says.
- When the filter was **not** full at `$C001` (9 to 11 low falls: the first counted pulse reloads the counter with 0) and the `$E001` fell between the first and second counted pulses, the model says the second pulse reloads again (counter 0 again) and expires, because it expires on every reload to 0 when L = 0 (period L + 1 = 1 pulse). **The chip did not assert in 216 of 217 iterations.** So after the first expiry with L = 0, the next pulse does not expire.
- This is consistent with the chip expiring on a decrement to zero and on the reload that follows `$C001`, but not on the reload at zero. For L >= 1 the two rules give the same result (period L + 1), which is why every earlier test agreed (F-037, F-056, F-059); only L = 0 shows it. The pulses after that never expire either (probe phase 18 below).
- **Free-running counter (probe phase 18, `captures/p18_*`, `tools/la_p18_analysis.py`):** `$C001` written once at start-up, latch 0, then only `$E000`/`$E001` every 114 cycles with rendering on: **2,435 counted pulses in four captures, and /IRQ never fell** (the expiry after `$C001` happened long before the captures). The model before F-075 would have asserted after every pulse. The updated model replayed over the captured bus: 0 mismatches in 296,607 cycles. So with latch 0 the chip does not expire again at any later pulse, not just the next one.
- **Control (probe phase 19, latch 1, same loop, `captures/p19_*`):** 2,435 counted pulses, **1,168 /IRQ falls, each right after a counted pulse, spaced 2 pulses apart in 1,156 cases** (period L + 1 = 2, F-059; the 8 other gaps are longer, with an expiry that fell in the short disabled window between the loop's `$E000` and `$E001` lost). The model replayed over the captured bus: 0 mismatches in 296,607 cycles. The test therefore sees what it should see for latch 1, and the silence for latch 0 is real.
- Evidence: the same captures, per-iteration timeline in the log of this session (filter at `$C001`, counted pulses, `$E001` cycle, chip assertion cycle). Confidence: High for "no expiry at the pulse after a reload to 0 with L = 0".

**F-076: The PRG outputs follow CPU A13/A14 combinationally within about 8 ns (timing probe phase 4, `captures/p4_prg_24m_*.sr`, `captures/p4_prg_48m/`).**
- ROM: R6 = `$00`, R7 = `$15`, RF = `$0A`; a loop reads `$8000`, `$A000` and `$C000` between code fetches from the fixed bank (`$E000-$FFFF`). 59,643 changes of CPU A13/A14 at 24 MHz (2,147 at 48 MHz).
- **Pattern:** PRG A17-A13 read `00`, `15`, `0A` and `1F` for the windows `$8000`, `$A000`, `$C000` and `$E000` in every case (9,940 or more per window at 24 MHz): F-009 to F-011 on a console, with the PRG address lines following CPU A13/A14 as they are on the jig even outside register writes.
- **Delay from the CPU address change to the PRG outputs** (24 and 48 MHz agree to about 1 ns): **rising outputs 0 to 2 ns, falling outputs 6 to 8.5 ns**, the five outputs equal within about 2 ns (PRG A14 is the slowest, about 1.5 ns behind the others). The asymmetry is the same as on the CHR outputs (F-068: rises 1 to 5 ns, falls 6 to 7 ns) and is probably the input threshold of the chip against the analyser's: the true propagation delay is a few ns, below what this analyser resolves. The CPU lines are seen on the J2 side of the 220 ohm resistors.
- For an FPGA: the PRG bank outputs are a combinational function of CPU A13/A14 and the registers, valid within about 10 ns of the address (the ROM needs the address stable before /CE falls, about 340 ns later: F-064). No register on that path.
- Evidence: script `tools/la_p4_analysis.py`. Confidence: High that the delay is under 10 ns; the exact figure is not resolved.

**F-077: The four tests added after the first hardware runs pass on the real chip (G4 tests 11 and 12, G5 tests 11 and 12; PXL_20261102_030502170.jpg, PXL_20261102_030742823.jpg, 2026-11-01).**
- `g4_cpu_irq` (image md5 `960ad4be...`, reset vector `$F469`): 12 of 12 pass, "ALL TESTS PASSED" on the green screen; the first-expiry INFO line is unchanged (`07 17 03`). Test 11 (`$E001` in the expiry's own cycle, L = 4): interrupt at once; in the next cycle the expiry is lost and the next one comes 20 cycles later (F-071). Test 12: an `$E000` in the expiry cycle gives no interrupt (F-072).
- `g5_a12_irq` (md5 `28d38be0...`, reset vector `$E622`): 12 of 12 pass; the filter-threshold INFO line is unchanged (`10 FC 07`). Test 11: latch 0, twelve pulses, exactly one interrupt; test 12 (control): latch 1, five interrupts (F-075, F-059).
- This closes the loop between the logic-analyser findings and the pass/fail ROMs: the rules found with a probe and a replay are now checked from the CPU side on a console, so any emulator author can run them. 61 tests across G1 to G6, all confirmed on one chip and one console. The A12-mode enable-flag rule (F-074) still has no test ROM.

**F-078: The chip keeps its register contents while its supply is switched off but not discharged; a real power-on state needs the supply to collapse (RP2350 adapter, first runs, 2026-11-02).**
- Setup: the adapter's cart-power switch (Q1) turns the cart's 5 V off, but the rail (C6, 10 uF, and the cart's own capacitance) has no discharge path: a meter on J2 pin 1 still read **1.2 V** well after switch-off.
- Observation 1: the first `power on` of the cart after bring-up showed a **non-zero CHR state**: CHR A17..A10 per PPU window `00 02 00 00 00 3F 11 FF`, not the all-zero state of F-003 (seven cold starts on the Mega jig) and of G1 test 3. It was the same at five "cold starts" of 2 s, 2 s, 15 s, 15 s and 40 s off.
- Observation 2: after writing R0 to R5, R8 and R9 with one distinct data bit each (`01 02 04 08 10 20 40 80`; this also exercised D0 to D7, all PPU windows and all eight CHR outputs), a power-off of 3 seconds, and of about a minute, **left those values intact**.
- Observation 3: with the supply **discharged** (all stimulus lines driven low with the drivers on while the power is off, so the cart's own pull-ups drain the rail through them in about a millisecond), a power-off of **200 ms or 1 s** gives the documented power-on state every time (3 of 3): CHR 0 in all windows, PRG `1F`, /CE high, CIRAM following PPU A10 (vertical), /IRQ asserted (F-001 to F-004), **with the supply rising in microseconds** (the Q1 switch), far faster than the console or the Mega's USB. So the power-on state does not depend on the ramp rate, at least not within this range.
- Conclusion: the registers are not reset by anything except the supply collapsing; there is no brown-out detection that clears them at 1 V or so. The earlier documented cold starts (15 s unplugged on the Mega jig, the console after being off) were real power-offs; a **quick power cycle of a console may leave the mapper's registers as they were** (not tested in a console). The retention threshold (the voltage or time below which the state is lost) is not measured.
- Consequence for the adapter: a cold start must discharge the rail (firmware `cold`, `discharge`); `power off` alone is not a cold start.
- Evidence: the adapter session of 2026-11-02 (firmware 0.3, `firmware/rp2350_jig/`); not yet logged to a capture file. Confidence: High for the retention and the discharge fix; the cause (the chip's internal storage retaining state down to about 1 V) is inferred.

**F-079: The chip's /IRQ state survives a power-off of up to about 5 seconds, much longer than its registers; the asserted power-on /IRQ comes back only after about 5 to 6 s off (RP2350 adapter, 2026-11-02).**
- Method: release /IRQ with a `$E000` write, switch the cart power off with the rail discharged (F-078: all stimulus lines low, drivers on, 300 ms), stay off for T, power on, read /IRQ before any write.
- Results (/IRQ after power-on; 0 = asserted, 1 = still released): T = 0.8 s, 2.5 s, 4.0 s (twice): **1, 1, 1, 1**; T = 5.0 s: **1 and 0** (mixed); T = 6, 7 s (twice each), 8, 11, 14, 17 s (twice each) and 20 s: **0 every time** (14 of 14).
- The CHR registers, in contrast, were back to 0 after a power-off of 200 ms with the rail discharged (F-078). So /IRQ is not reset like the registers: its state decays on its own, in about 5 s, to the asserted state. A cold start to see the documented power-on state therefore needs about **10 s off** (F-001's procedure, 15 s unplugged, was fine; a power-off of a second or two, as in a quick console power cycle, may leave /IRQ released).
- This does not say why the decayed state is "asserted" (F-034 stays open) but it shows that the asserted /IRQ is a stored state that takes seconds to appear, not a reset state. A power-on test such as G1 test 1 must be preceded by a power-off of at least about 10 s; G1 already says "power cycle required".
- Not tested: whether the other registers behave the same when the discharge is shorter or longer, the temperature dependence, and a console (the cart in a console with its own supply behaviour).
- Evidence: adapter session 2026-11-02 (firmware 0.4, `power`/`discharge` commands); not yet logged to a capture file. Confidence: High for the 5 to 6 s boundary within +-1 s at room temperature, one chip.
- **Update, same day: the retention is not a fixed 5 s; it depends on how long the chip held the released state.** A second series powered the chip for P seconds with /IRQ released, switched it off (rail discharged) for 10 s and read /IRQ; each trial began with a 10 s power-off as well. P = 0.5 s: asserted; P = 5 s: asserted; **P = 30 s: still released; P = 120 s (twice): still released; P = 30 s: still released; P = 5 s: still released (this one contaminated by the previous trials);** P = 0.5 s: asserted. So after a short soak a 10 s power-off re-asserts /IRQ, after 30 s or more powered it does not, and the state then needs more than 10 s off (20 s did work once, after a long soak, in the first series). The 5 to 6 s boundary above holds only for a short soak (and the 20 s off of the first series for a long one).
- Consequence: a reliable power-on /IRQ test needs a long off time (20 s or more, and the cart not left powered for long with /IRQ released); the adapter's replays do not depend on it, because the CPU-mode expiry trick (C001, E001, six cycles) asserts /IRQ whenever it is wanted. The cause (a slowly charging and discharging node) is a guess, and F-034, the origin of the power-on /IRQ, stays open.


**F-080: The `$E000` /IRQ release takes 80 ns from /ROMSEL falling when the adapter drives the chip, whatever the data timing; the adapter replays the console's bus and gets the same /IRQ edges (RP2350 adapter, PIO engine, 2026-11-02).**
- The PIO engine (firmware 0.4) drives all 17 chip inputs from a DMA-fed buffer at the full 150 MHz clock (one new state per 6.67 ns, no dropped or repeated word in 19,968 of 19,968 cycles of a pseudo-random pattern) and captures the stimulus read-back and the chip's outputs from the same cycle (the read-back lags the commanded word by exactly 2 cycles, 13.3 ns).
- **Replay of the console's bus (the plan's acceptance test):** the bus of the A12-race loops (`captures/p10c_*`, `captures/p9c_*`: M2, R/W, /ROMSEL, A0, A13, PPU A12 at 24 MHz; data lines D0 to D7 driven 0, A14 high) was driven into the chip. **/IRQ edges, directions and order match the console's in 4 of 4 replays** (one with five edges: assertion times within 27 ns of the console's, two release times 87 and 90 ns earlier; three captures in which /IRQ stays silent, and the chip stays silent too).
- **Release delay against the data timing (experiment E2a, `firmware/rp2350_jig/tools/e2_release.py`):** a `$E000` write with the data byte arriving from 200 ns before the window opens to 300 ns after it (stale byte `$E0`), CPU-mode expiry asserting /IRQ beforehand: **/IRQ rose 80.0 ns after /ROMSEL fell in all 24 trials** (8 data times, 3 each), with the adapter's buffers (about 16 ns) included. The data timing has no effect.
- The console's figure (F-067) is 130 ns. The difference of about 50 ns is not the data bus or the edge placement. A plausible cause is the **analog rise of an open-drain /IRQ**: the line rises through the cart's 10 k pull-up (R3) after the chip lets go, and a threshold crossing (1.4 to 1.65 V) takes about 0.4 R C, which depends on the load (the analyser lead and the adapter's ribbon and buffer differ). The assertion edge (a pull-down) is fast and agrees (20 ns here against 8 to 10 ns in the console, plus the buffers). Not proven: needs a scope or a change of the load.
- Consequence for the figures: the 130 ns of F-067 and the 13 ns / 101 ns type measurements of open-drain outputs include the pull-up RC and should be read as "threshold crossing at the pin with this load", not as the chip's logic delay (which is shorter). The CHR and PRG outputs are push-pull and are not affected.
- Evidence: adapter session 2026-11-02; scripts `firmware/rp2350_jig/tools/replay.py`, `e2_release.py`, `selftest_pio.py`. Confidence: High for the 80 ns and the independence of the data timing; Medium for the replay (data lines unknown in the captures); the RC explanation is a hypothesis.

**F-081: In A12 mode the chip samples PPU A12 at the M2 falling edge with no measurable setup or hold time: a pulse is counted if and only if A12 is high at the fall (RP2350 adapter, experiment E3, 2026-11-02).**
- Method (`firmware/rp2350_jig/tools/e3_a12.py`): A12 mode, latch 0, interrupt enabled; per trial `$E000`, `$C001` (data 0), `$E001`, one swallowed pulse (after `$C001` the next pulse does not clock, F-052), 18 idle cycles with A12 low (filter full), then a test pulse with A12 high from `rise` to `fall` (ns, relative to the M2 fall of one idle cycle, at the adapter's GPIO side; the 74HCT541 delay of about 8 ns is in both lines, the skew between U3 and U4 is not calibrated). A counted pulse reloads the counter from latch 0 and /IRQ asserts within three cycles. Three repeats per point, 6.67 ns grid.
- **Setup scan** (fall fixed at +150 ns, rise from -200 to +60 ns, 10 ns steps): counted at every rise up to 0 ns (3 of 3 each), **not counted from +10 ns on (0 of 3 each)**.
- **Hold scan** (rise fixed at -250 ns, fall from -120 to +100 ns): **not counted up to and including 0 ns, counted from +10 ns on** (3 of 3 each).
- So the pulse is counted exactly when A12 is high at the M2 fall, to within the 10 ns step and the uncalibrated buffer skew (a few ns): the sampling instant lies between 0 and +10 ns after the fall at the GPIO side, setup and hold are each below about 10 ns. A pulse that ends before the fall or begins after it is not counted, however close; a pulse that is high only between two M2 falls leaves no trace (the filter and counter are not touched by it).
- This sharpens F-074. The console captures gave "a rise up to 41 ns before the fall counts" and a replay best fit with the A12 level taken 0 to 83 ns after the fall; those figures are bounded by the analyser's 41.7 ns sample grid and the probe and resistor delays, not by the chip: the chip's own window is a few ns around the fall. For an emulator: take A12 at the M2 fall, nothing more. For an FPGA: sample A12 on the M2 falling edge in the M2 domain, with the usual synchroniser concerns for the real asynchronous A12.
- Not measured: the dependence on the A12 slew (the adapter's edges are about 5 ns; the console's PPU edges are slower, through the 220 ohm resistor), on the supply voltage, and on temperature; a finer scan than the 6.67 ns PIO step (needs the loopback calibration, M3).
- Operational note: two USB host-controller crashes on the PC during long adapter runs (xhci_hcd HC died); after moving the adapter to a powered USB hub the E3 hold scan, including a cold start, ran without a drop.
- Confidence: High for the symmetry and the ±10 ns bound; the exact instant is not resolved below 10 ns.

**F-082: The register write window closes at the first of the M2 fall, the /ROMSEL rise and the R/W rise, and the data is latched at that instant; a window as short as 7 ns is enough; R6 (PRG) is not transparent (RP2350 adapter, experiment E2, 2026-11-02).**
- Method (`firmware/rp2350_jig/tools/e2_window.py`): R6 selected with `$8000`=06 and cleared with `$8001`=00; then a test write to `$8001` with data X = `0A` that changes to Y = `15` at a chosen time; the stored value is read back on PRG A13..A17 with CPU A13 = A14 = 0. Stored X, Y or the old 00 shows what was latched. Console-shaped edges (M2 high 363 ns, /ROMSEL rises 13 ns and R/W 83 ns after the M2 fall). Times at the adapter's GPIO side, 6.67 ns grid, 3 repeats per point; all results identical in the three repeats unless noted.
- **Which edge closes the window:** with one of the three lines ending 100 ns before the other two and the data changing 50 ns after it, the stored value is X (the old data) for M2 early, /ROMSEL early and R/W early (2 of 2 each), and Y when all three stay until after the change. So the window is the AND of M2 high, R/W low and /ROMSEL low, and it closes at the first of the three to end.
- **Data timing against the M2 fall** (/ROMSEL and R/W ending 13 and 83 ns later): data changed up to 0 ns after the M2 fall: Y stored (27 of 27); changed 10 ns or more after it: X stored (18 of 18). So the data is latched at the M2 fall, setup and hold each under 10 ns (the same instant as the A12 sampling, F-081). With the console's edge order the M2 fall is the closing edge.
- **Minimum window** (data valid throughout): the M2-fall-limited window (/ROMSEL low beforehand) and the /ROMSEL-limited window (M2 high beforehand) both latch the data from 7 ns up (3 of 3 at 7, 10, 13 ns and every longer width); at 3 ns the result was 1 of 3 and 2 of 3 (one PIO cycle is 6.67 ns, so a 3 ns request is a 0 or 1 cycle pulse on the grid). The real minimum is below 7 ns, within the resolution; the chip needs no wide window.
- **R6 is not transparent:** during the open window (sampled 250 ns after the M2 rise, data X on the bus, CPU A13 = A14 = 0) the PRG outputs still show the old value 00 and change only after the window closes. F-066/F-070 found the CHR bank data (R0) and `$A000` transparent. So the transparency is not a property of `$8001` as a whole: **a PRG bank register (R6) updates at the end of the write, a CHR bank register (R0) follows the data inside it.** **Control with the same harness and CHR R0** (`e2_window.py --reg chr`, `$8000`=20, X = `A1`, Y = `42`, PPU A10-A12 low, read on CHR A10, A11, A15-A17): the outputs show X (`A1`) while the window is open, i.e. R0 *is* transparent here, as F-070 found on the console, and the closing rule and the latch instant are the same as for R6 (stored X for each of the three early edges, Y when none; data changing up to 0 ns after the M2 fall gives Y, 10 ns or more gives X; 2 of 2 and 2 of 2 repeats). So the method sees transparency where it exists and R6 differs from R0 on this chip. R7 and the other registers are untested.
- Evidence: adapter session 2026-11-02. Confidence: High for the closing rule, the latch instant (to 10 ns) and the minimum window (under 7 ns); High for R6 not being transparent in this setup, to be confirmed on the console with a PRG-reading probe.

**F-083: Every combinational output (PRG A13-A17, CHR A10, A11, A15-A17, CIRAM A10, PRG /CE) follows its inputs within 13.3 to 20 ns through the adapter, i.e. within a few ns inside the chip; falling outputs are about one PIO cycle slower than rising ones (RP2350 adapter, experiment E5, 2026-11-02).**
- Method (`firmware/rp2350_jig/tools/e5_delays.py`): a Gray code over the input lines (one line changes per step, 400 ns per state, 6 loops), banks chosen so that every step flips every visible output (R6 = 15, R7 = 0A, fixed 1E/1F; CHR 1 KB banks 00/FF alternating in every window). Delay = output edge minus the stimulus edge as read back at the RP2350 pins, so it includes the 74HCT541 (stimulus) and 74LVC541A (output) buffers, about 15 ns together (F-080), at 6.67 ns resolution. CHR A12 to A14 are outside the capture window.
- **PRG outputs vs CPU A13/A14** (M2 low, R/W and /ROMSEL high): rising outputs 13.3 ns (all 6 of 6), falling outputs 13.3 to 20.0 ns (mean 17.8). **CHR outputs vs PPU A10/A11/A12 and CIRAM A10 vs PPU A10/A11:** the same, 13.3 ns rising, 13.3 to 20.0 ns falling (mean about 17.8), every output and every input line alike. No output is slower than 20 ns.
- The chip's own share is what is left after the buffers: not more than about 5 ns, and not resolved by the 6.67 ns grid (needs the loopback calibration, M3). This agrees with the console figures of F-076 (rising 0 to 2 ns, falling 6 to 8.5 ns behind the input): the extra delay of the falling edge shows here as the rise at 13.3 and the fall at 13.3 or 20.0.
- **/CE** (reads of the pin): /CE falls 13.3 to 20 ns after /ROMSEL falls (M2 high, R/W high) and rises 13.3 ns after it rises; with /ROMSEL low and R/W high /CE falls 13.3 to 20 ns after the M2 rise and rises 13.3 to 20 ns after the M2 fall; with M2 high and /ROMSEL low /CE falls 13.3 ns after the R/W rise and rises 13.3 to 20 ns after the R/W fall. **With M2 low, or with R/W low, /ROMSEL has no effect on /CE** (no change in 8 of 8 toggles each). So /CE = low exactly when M2 is high, /ROMSEL is low and R/W is high (a read of $8000 to $FFFF), as in the truth table of F-012 and the console edges of F-064, now with all three inputs combinational at the same speed as the bank outputs. /CE has no stretch or latch: it ends 13 to 20 ns after M2 falls, i.e. within a few ns of the chip.
- For an emulator: the outputs are combinational, no delay worth modelling; for an FPGA: the bus can be treated as a combinational path with a tco of a few ns to the outputs (the ROM's own access time then dominates).
- Evidence: adapter session 2026-11-02. Confidence: High that all outputs respond within 20 ns total; the split into buffers and chip is estimated, not measured.

**F-084: The A12 filter counts M2 falling edges only: exactly 16 falls with A12 low are needed, for M2 periods from 300 to 1500 ns, with no dependence on elapsed time and no reaction to an A12 glitch between falls (RP2350 adapter, experiment E4, 2026-11-02).**
- Method (`firmware/rp2350_jig/tools/e4_filter.py`): A12 mode, latch 0, interrupt enabled; per trial `$E000`, `$C001` (data 0), `$E001`, one swallowed pulse (F-052), the low period under test, then a test pulse (A12 high across one M2 fall). Counted = the counter reloaded from latch 0 and /IRQ asserted. 3 of 3 repeats agree in every row.
- **Threshold** (n idle M2 cycles with A12 low between the swallowed pulse and the test pulse, M2 period 559 ns): n = 10 to 15: not counted (0 of 3 each); **n = 16 to 20: counted (3 of 3 each)**. Same result at M2 periods of **300 ns** (n = 13 to 18) and **1500 ns** (n = 13 to 18): the threshold is 16 M2 cycles whatever their length, from 3.3 MHz down to 0.67 MHz.
- **No time component:** 6 cycles, then M2 held low for 0, 1, 5, 20 or 50 microseconds with A12 low, then 6 more cycles (12 in all): never counted (0 of 3 each, 15 of 15). The filter does not fill with time; it needs M2 falls.
- **An A12 glitch between falls is ignored:** 10 cycles, a 100 ns A12 high pulse inside the M2-low phase (not covering a fall), then m more cycles: counted for m = 6 to 9 (10 + m = 16 or more), not counted for m = 4 and 5. The glitch neither resets the filter nor adds to it, which agrees with F-081 (A12 is only looked at on the M2 fall).
- For an emulator: the model `filt` counter in the reference (F-022, F-051) is right as it stands; count M2 falls (CPU cycles), ignore A12 between them. For an FPGA: a 5-bit counter in the M2 domain, reset by A12 high sampled at the M2 fall, nothing asynchronous.
- Not tested: the filter's first value after power-on (the model assumes full; untested since a cold start needs the power cycle plus a probe), and what a very short M2 high time does to the count.
- Evidence: adapter session 2026-11-02. Confidence: High.

**F-085: After power-on the A12 filter is NOT full: it starts at about 8 M2 falls after a short power cycle and at lower values after a longer one (2 to 5 after 2 to 30 s off), so the first A12 pulses after power-on can count earlier than 16 falls (RP2350 adapter, experiment E4b, 2026-11-02).**
- Method (`firmware/rp2350_jig/tools/e4b_poweron.py`): one real cold start per point (supply discharged, `cold`, F-078), then at once `$E000`, `$C000`=00, `$E001`, `$C001` (data 0), n idle cycles, a test pulse; A12 held low from before the first M2 fall; L idle cycles before the first write. Counted = /IRQ asserts. A filter that powers up full (16) is made 17 by `$C001` and swallows the pulse for every n.
- **Not full:** the pulse counts at small n (n = 3 for L = 0 and L = 1, 3 of 3 repeats at each n), so the filter is below 16 at `$C001`. It becomes full during the run: with L = 5 or 6 (falls before `$C001` = 8 or 9) the pulse is swallowed for every n up to 6 (the filter is full at `$C001`), with L = 4 it counts even at n = 0 (the filter reaches 16 exactly with the `$C001` cycle). From L = 1 to 4 the threshold n* falls by one per lead cycle (3, 2, 1, 0), as a counter that counts every low fall must.
- **Starting count** f0 (the filter's value before the first M2 fall, from n* = 16 - f0 - L - 4 at L = 1): **8 after 0.2, 0.5 and 1 s off** (2 of 2 repeats at each; 3 of 3 at L = 0), **5 after 2 s** (n* = 6, 2 of 2), **4 after 5 s** (n* = 7, 2 of 2), **3 after 10 s** (n* = 8), **2 after 30 s** (n* = 9); after 60 s the pulse counted already at n = 8 (f0 of 3 or more; 1 run). So the start value is not fixed: it falls with the time the supply was off, in the same way as the stored /IRQ state decays (F-079), and is not the reset value of a logic counter. Single runs at 10, 30 and 60 s.
- At L = 0 (the first M2 fall is the `$E000` write) the threshold is n* = 3, the same as at L = 1, one count more than the counter model gives (4); unexplained, possibly the first fall after power-on counts twice, or counts differently for a write cycle. A reproducible effect (3 of 3), size one fall.
- **For an emulator:** the power-on value of the filter hardly matters: it affects only the first A12 pulses in the first dozens of M2 cycles after power-on, and programs write `$C001` after hundreds of cycles. If a model needs a value, use the quick-restart value 8 (not 16, not 0) and let it count up. The reference model keeps 16 (full) as its default; the difference shows only in the first 8 falls after power-on. The old open question in `docs/emulator_guide.md` section "unknown" is answered: not full.
- **For an FPGA:** the filter counter has no defined reset value; a design that resets it to 0 (or any value) differs from the chip only in those first falls.
- Not tested: the power-on value for an off time of several minutes, other chips, the 1 s to 2 s transition (8 to 5).
- Confidence: High that the filter is not full at power-on and that the start value depends on the off time; Medium for the individual values (single runs in the 10 to 60 s rows).

**F-086: CPU reads of the eight register addresses ($8000 to $E001) have no effect on the chip (RP2350 adapter, experiment E6, 2026-11-02).**
- Method (`firmware/rp2350_jig/tools/e6_reads.py`): a read cycle is R/W high, M2 high 363 ns, /ROMSEL low from 28 ns after the M2 rise to 13 ns after the M2 fall, CPU A0/A13/A14 set to the register address, the data bus released (high). For each of the eight addresses the same run was made with and without the reads, and the outputs compared sample by sample.
- **Part A, registers and outputs:** R6, R7, R0 to R5, R8, R9 and mirroring set to distinct values; 6 read cycles of X; then a write of `5C` to `$8001`; 24 snapshots (4 PRG windows, 8 PPU A10-A12 combinations, before the reads and after the write; PRG, CHR A10/A11/A15-A17, CIRAM and /IRQ outputs). **Identical to the run without reads for all eight addresses.** The snapshots are sensitive: they show 10 distinct values and the `5C` write changes one of them, so a changed register, mirroring bit or index would show.
- **Part B, CPU-cycle counter:** latch 10, CPU mode, every one of 70 cycles after `$C001` a read of X: /IRQ asserts 45.7 cycles after the `$C001` write (as without reads) and stays low at the end, for all eight addresses. So no read acknowledges the interrupt (including `$E000`), restarts or stalls the counter, or changes the enable.
- **Part C, A12 counter:** latch 3, A12 mode, a swallowed pulse and six pulses with 17 read cycles between them: /IRQ asserts 1.69 cycles after pulse 4 (as without reads) for all eight addresses. So reads do not touch the A12 filter, the counter or the reload flag either.
- Conclusion: **the chip ignores reads of its register addresses entirely**; the registers are written only when R/W is low (F-066, F-082). An emulator may treat a read of $8000-$FFFF as a plain ROM read; an FPGA needs no read path.
- Not tested: reads of the unused addresses (all eight combinations of A0/A13/A14 are the registers, so there are none), reads with M2 low (no window), and a read during the CPU's own write window (impossible on a real bus).
- Evidence: adapter session 2026-11-02. Confidence: High. (A first version of part C asserted nothing because the pulse cycles had no M2 edges; found by the baseline showing no /IRQ at all and fixed before the result was used.)

**F-087: Switching from A12 mode to CPU mode with `$C001` while the A12 filter is not full makes the first CPU-mode expiry come 4 cycles early: 4(L+1)-2 after the write instead of 4(L+1)+2 (RP2350 adapter, experiment E7, 2026-11-02).**
- Method (`firmware/rp2350_jig/tools/e7_modeswitch.py`): A12 mode, latch L, enabled; `$C001` (data 00), a swallowed pulse, a number of idle cycles with A12 low, then (optionally) a counted A12 pulse whose M2 fall is cycle K; a `$C001` with data 01 (CPU mode) is written in cycle K+j; the first /IRQ fall is measured in cycles from K. 2 to 4 repeats per point, all identical to the cycle.
- **Normal timing** (F-058, F-026): the first expiry is 4(L+1)+2 cycles after the write: `$C001` in the clocking cycle itself (j = 0): K+6, K+14 for L = 0, 2; and for j >= 17: j+14 (K+31, K+34, K+38 for j = 17, 20, 24 at L = 2). Same with no counted pulse at all and the filter full.
- **Early timing:** for j = 1 to 16 (L = 2) the first expiry is at **j + 10** = 4(L+1)-2 after the write: K+11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 24, 25 and 26 for j = 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15 and 16. For L = 0: K+3 (j = 1), L = 5: K+23 (j = 1); in all cases 4(L+1)-2 after the write.
- **The condition is the A12 filter, not the pulse:** after a counted pulse at K the filter is 0 at K and has `j-1` low falls at the write in cycle K+j; j = 16 (filter 15) is early and j = 17 (filter 16, full) is normal. The same early result with **no counted pulse at all** when the filter is simply not yet full (5 low cycles after the swallowed pulse, `$C001` in K+1 and K+3: j+10, 3 of 3 each). A write in the clocking cycle (filter still full at the write) is normal.
- **It needs a switch from A12 mode:** a CPU-mode `$C001` rewrite while already in CPU mode is not early, also with the filter at 4 (latch 5, `$C001` in K+5: expiry 26 after the write as usual, 3 of 3).
- **The other half:** a `$C001` with data 00 (A12 mode again) in the cycle of the assertion (K+1) prevents the pending /IRQ (8 of 8; the model already does this); in K+2 and later the assertion has happened and stays. For latch 0, a CPU-mode write in K+1 gives /IRQ at K+3 and not at the A12 assertion cycle K+1 (the pending assertion is cancelled, 4 of 4).
- **Not tested:** the effect of the filter at the write when the mode before was never written (power-on), and for CPU to A12 (F-057: cancels cleanly).
- **For an emulator:** at a `$C001` write with bit 0 set while in A12 mode, if the A12 filter is below 16 (A12 was high at an M2 fall within the last 16 cycles), start the CPU-mode counter 4 cycles ahead: the first expiry 4(L+1)-2 cycles after the write. A game that switches to CPU mode in the middle of a frame with rendering on (A12 busy) sees this; with rendering off or A12 steadily low (the test ROMs) the filter is full and the old rule holds. The reference model (`reference/rambo1.py`) now has it (36 checks).
- **For an FPGA:** the CPU-mode prescaler is not reset by the write when the A12 filter is running; it shares a state with the A12 filter or counter; the rule above is the observed behaviour.
- **Test ROM:** `rom/g4_cpu_irq.s` test 13 (`A12 TO CPU, FILTER LOW`) checks the rule from the CPU side: two arms, A12 lowered 4 or 48 cycles before the `$C001`, the interrupts must be 2 NOPs apart. Hardware and reference models pass; MesenCE fails (GOT 0). Flash image `rom/build/g4_cpu_irq_prg.bin` (reset vector `$F624`, md5 `840cd507...`). **Console run (PXL_20261102_063722124.jpg, 2026-11-02): 13 of 13 pass, test 13 included; the INFO line is unchanged (`07 17 03`).** So the rule is confirmed on the console from the CPU side, not only with the adapter.
- Evidence: adapter session 2026-11-02. Confidence: High for the rule within the tested cells (about 20 cells, all repeats identical); the latch is read one cycle after the write in the early case (L = 0 expiry at write+2 is earlier than the usual 5-cycle latch capture); a latch change within 1 to 5 cycles of the write is untested.

**F-088: After power-on the IRQ counter is already running in CPU-cycle mode with latch FF: with no `$C000` or `$C001` write the first interrupt comes at M2 fall number 1018 to 1019 (RP2350 adapter, experiment E8, 2026-11-02).**
- Method (`firmware/rp2350_jig/tools/e8_poweron_counter.py`): one real cold start (supply discharged, `cold`, F-078), then only `$E000` (releases the power-on /IRQ) and `$E001` (enables); no `$C000` and no `$C001`. Then M2 cycles in chunks of 560 cycles with the chip's state kept between runs (bus idle). Fall numbers count M2 falls from the first M2 fall, which is the `$E000` write cycle (number 1). Three variants: A12 held low (idle), A12 held high, and A12 pulses (17 or 40 low cycles between them, to 120 pulses).
- **Result:** /IRQ falls at **M2 fall number 1018** (3 of 3 cold starts with 500 ms off, A12 low) or **1019** (2 of 2 with 5 s off, 2 of 2 with 30 s off, 1 start with A12 held high, 1 start with A12 pulses every 18 cycles: 1019; 1 start with pulses every 41 cycles: 1018). In every start the interrupt came; none earlier, none absent within 3,600 cycles.
- **What this means:** the chip powers up in **CPU-cycle mode** with the latch at FF and the counter running from the first M2 cycle: 4(255+1) = 1024 counts. A `$C001` CPU-mode write expires 4(L+1)+2 = 1026 falls after the write (F-058); the power-on counter expires at 1018 to 1019, as if it had been started about 7 to 8 falls before the first M2 fall. **A12 pulses before the first `$C001` do nothing:** with up to 85 pulses applied the interrupt arrived at the same cycle as with none (so the counter is not clocked by A12 in the power-on mode, and the A12 mode needs a `$C001` with bit 0 = 0).
- The off time (0.5 s to 30 s) moves the figure by at most one cycle, unlike the filter (F-085) and the /IRQ (F-079). The one-cycle difference follows the off time or the A12 level; the data cannot separate them.
- **For an emulator:** after a power cycle (not after a reset, which keeps the registers), set CPU mode with latch FF and start the CPU counter so that the first expiry comes at M2 cycle 1018 after the first cycle; an enabled interrupt (`$E001`) then fires about 1,018 cycles after power-on if the game has not written `$C001` by then. Games write `$C000`/`$C001` and `$E000` early, so this matters mostly for test ROMs and for a game that enables the interrupt first and sets the mode late.
- **Not measured:** the period after the first expiry (4 x 256 = 1024 assumed), the A12-mode counter's power-on value (not reachable without a `$C001`), the first-expiry figure with the filter at its power-on state (F-085) vs full (the F-087 early rule would give 1022 from a full-filter start; the observed 1018 to 1019 is earlier still), and whether a `$C000` before `$C001` changes it.
- Evidence: adapter session 2026-11-02. Confidence: High for the CPU-mode power-on state and the 1018 to 1019 figure (8 of 8 starts); the equivalent start offset is a fit.

## F-089: write-window transparency of every bank register and $A000 (E9, adapter, 2026-11-02)
Tool: firmware/rp2350_jig/tools/e9_transparency.py, 3 repeats, all 36 results per column identical. Per register: data X->Y 150 ns after the /ROMSEL fall (T), 10 ns before the M2 fall (E), 10 ns after it (L).
- **Transparent (output follows the data bus while the window is open):** R0, R1, R2, R3, R4, R5, R8, R9 (all CHR) and $A000 (mirroring/CIRAM A10). Test T read Y live, before the M2 fall.
- **Not transparent:** R6 and RF. The output kept the old value (00) for the whole window and changed only at the close. R7 cannot be watched live (the write address selects PRG window 0, which is R6/RF); its stored value behaves like R6.
- **Latch instant, all twelve:** the data present at the M2 fall is stored (E stores Y, L stores X; setup and hold each under 10 ns), as in F-082 for R6 and R0.
- So the split is CHR bank registers and $A000 transparent, PRG bank registers (R6, R7, RF) latched at the window close. Emulators need none of this (a write is atomic at CPU level); it matters to FPGA/cartridge designs and to anything that glitches the data bus mid-write.

## F-090: the IRQ enable flag is tested at the M2 fall itself, to within about 7 ns (E10, adapter, 2026-11-02)
Tool: firmware/rp2350_jig/tools/e10_enable_instant.py. CPU mode, latch 2, first expiry in cycle K = 14. 8 repeats for the last table, 2-3 for the rest; every column was constant except the 6.7 ns quantisation of the /IRQ edge (20-26 ns after the M2 fall, buffers included).
- **Early side:** an `$E001` whose window ends 0 to 150 ns before the M2 fall of the expiry cycle (window 20 ns wide, /ROMSEL rise as the closing edge) still enables the expiry: /IRQ falls at the usual instant. An `$E000` with the same timing prevents it every time. So the flag is a stored level that is set as soon as the window acts (consistent with F-066/F-070 transparency), not something sampled from the bus at the fall.
- **Late side:** a write whose M2 rise comes g ns after the expiry fall (M2 low shortened to g, /ROMSEL low 3 ns later, window to the next fall):
  - g of 5 ns or more (and 25 to 196 ns): `$E001` gives no /IRQ, `$E000` does not stop it. Too late, as in F-071/F-072.
  - g = 3 ns: same, too late.
  - **g = 4 ns (one PIO step, about 7 ns after the fall): `$E000` prevented the /IRQ in 8 of 8 runs, and `$E001` produced an /IRQ one cycle late (at the next M2 fall, +580 ns) in 8 of 8 runs.** Both are deterministic. That is the boundary: the decision is made at the M2 fall plus a few ns, and a write landing right at that edge disables in time while an enable in the same sliver is seen only by the following cycle's decision. Since g = 3 and g = 5 ns behave as "too late", the 4 ns point is a runt-edge corner (M2 and /ROMSEL change inside one 6.7 ns step); treat it as the resolution limit of this adapter, not as a usable chip behaviour.
- **Emulator consequence:** none. The F-071/F-072/F-074 cycle rule (a write in the expiry cycle is in time, one cycle later is not) is exactly right; there is no sub-cycle region that matters on a real NES, where writes finish at the M2 fall.
- Open: whether the late-enable /IRQ at +580 ns is a real second decision or a runt artefact. It would need a faster stimulus than 150 MHz PIO to resolve.
