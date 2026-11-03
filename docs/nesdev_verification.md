# NESdev "RAMBO-1" page: verification against the jig

**DRAFT 0.2, 2026-10-31** A line-by-line check of every assertion on <https://www.nesdev.org/wiki/RAMBO-1> against
what was measured on the RAMBO jig (`docs/findings.md`, F-001 to F-054, plus the replay in section 4). This is separate
from `docs/functional_description.md`: that document describes the chip; this document tests another source's claims.

**Page snapshot:** raw wikitext fetched 2026-10-31 from `https://www.nesdev.org/w/index.php?title=RAMBO-1&action=raw`,
9970 bytes, 205 lines, SHA-256 `1721290b8c6d797331ae0f10c9efb57cca18a304e2da2e88f0bb31ab2cba439b`. If the wiki has
changed, re-run the check against the new text.

**Verdicts**

| Verdict | Meaning |
|---|---|
| VERIFIED | Measured; the claim holds (a qualification may be stated) |
| CONTRADICTED | Measured; the claim is wrong or off by a stated amount |
| PARTLY | Some parts verified, others not (stated) |
| CONSISTENT | Nothing found against it, but not a direct test |
| ANSWERED | The page says "unknown" or is silent, and the jig gives an answer |
| PENDING (exp N) | A test is designed but not yet run (none left in this version) |
| NOT TESTABLE | Not a chip-level fact (database, game, emulator, board wiring), or beyond what the jig can reach |

**Limits that apply to every row.** One chip. Steady-state and about 2-3 us timing resolution (the Mega's shortest bus
step is 1.9 us; a real M2 half-cycle is about 280 ns). Only CPU A0, A13 and A14 reach the chip, so register aliasing over
A1-A12 cannot be tested. The IRQ rows rest on a simulator replay (section 4) as well as on the direct measurements.

## 1. Summary

Of the 68 assertions on the page: **42 VERIFIED** (a few with a stated qualification), **6 CONTRADICTED**, 4 PARTLY,
3 CONSISTENT, 3 ANSWERED (the page was silent or said "unknown"), and 10 NOT TESTABLE (metadata, games, emulators, board
wiring). No row is left pending. The register map, banking, mirroring, register semantics, the A12 filter's shape and the
interrupt latency hold. The corrections are concentrated in the IRQ description, plus one about the PRG bank data and one
about the power-on state:

| # | The page says | Measured |
|---|---|---|
| 1 | The first reload after $C001 is "ORed with 1" | **No.** L = 2, 4, 8 behave as L, not L+1 (282 replay mismatches if applied) |
| 2 | $C001 "reloads the counter with the value in $C000" (refined rules) | **No.** The latch value present at the first real clock is used, not the value at the $C001 write (run 33: 20 mismatches) |
| 3 | After $C001 "the next clock will occur 4 cycles later" | **5 M2 falls**, not 4, in CPU mode (111 replay mismatches with 4) |
| 4 | "Trigger IRQ after 4 CPU cycles" | **1 M2 cycle** after the clock that brings the counter to zero in CPU mode (22 mismatches with 4) |
| 5 | Bank data: "all eight bits are used" | True for CHR registers; **PRG registers R6, R7, RF use only 5 bits** (F-010). Rated PARTLY |
| 6 | R6, R7, RF and $8000 are "unspecified at power on" | **Deterministic on this chip**: PRG banks read $1F at every window; CHR behaves as 1 KB mode with zero banks (7 cold starts) |
| 7 | $C001 "sets the 4-bit counter to 17" | **Only if the counter is already full (16)**; otherwise it is left alone and the first A12 pulse counts (F-052). The L+2 interval holds only in that case |

What the page gets right that matters: the 4-bit "A12 filter" model (falling-edge sampling, the 16 threshold, one clock per pulse, the second-fall interrupt), the
one-extra-edge first interval in the usual case, and the shape of the counter algorithm. With corrections 1-4 and 7 applied to the page's rules, the resulting model (section 4)
reproduces every recorded IRQ sample: 0 mismatches in 3393. Its CPU-mode part has two fitted numbers.

Unknowns on the page that the jig answers: the "extra kick" (section 3, U-2), $A001's PRG-RAM question (U-1), the
power-on values (U-5), the instruction to "refine and merge" the two descriptions (U-4). The experiments that closed the
remaining rows are in section 5.

## 2. Assertion by assertion

IDs are in page order. "F-xxx" refers to `docs/findings.md`.

### 2.1 Introduction and infobox

| ID | Assertion | Verdict | Evidence |
|---|---|---|---|
| W-01 | RAMBO-1 is "canonically designated as mapper 64" | NOT TESTABLE | iNES numbering |
| W-02 | "Basically Tengen's version of the MMC3, but with some extra features" | CONSISTENT | Same four register pairs and bank/mirror/IRQ roles; extras confirmed: R8, R9, K bit, CPU-cycle IRQ, RF. No MMC3 on the jig to compare |
| W-03 | "Came as a 40-pin PDIP" | VERIFIED | The chip is a 40-pin DIP (`docs/hardware.md` pinout) |
| W-04 | A variant with different mirroring control is mapper 158 | NOT TESTABLE | Board wiring. CONSISTENT with CHR A17 carrying bit 7 of the bank (F-007) |
| W-05 | Example games (Klax, Skull and Crossbones, Shinobi, Rolling Thunder, Hard Drivin' proto) | NOT TESTABLE | Game list |
| W-06 | Company Tengen; board 800032 | VERIFIED | Chip marking 337006; the jig board is an 800032 Rev A |
| W-07 | PRG max 256K | VERIFIED | Five PRG address outputs, A13-A17 (F-010) |
| W-08 | PRG page: 3 x 8K + 8K fixed | VERIFIED | F-009 |
| W-09 | CHR max 256K | VERIFIED | Eight CHR bank bits on A10-A17 (F-007) |
| W-10 | CHR page: 1K x 8, or 2K x 2 + 1K x 4 | VERIFIED | F-006 |
| W-11 | Mirroring H or V, switchable | VERIFIED | F-041 (one CIRAM A10 output) |
| W-12 | Bus conflicts: No | VERIFIED (qualified) | PRG /CE is active only on reads (F-012). Holds for boards that use /CE for the ROM, as the 800032 does |
| W-13 | IRQ: yes | VERIFIED | F-018 to F-038 |
| W-14 | iNES 064, UNIF TENGEN-800032, NES cart DB count | NOT TESTABLE | Database metadata |

### 2.2 Banks and bank select

| ID | Assertion | Verdict | Evidence |
|---|---|---|---|
| W-15 | $8000-$9FFF, $A000-$BFFF, $C000-$DFFF switchable 8 KiB PRG; $E000-$FFFF fixed to the last bank | VERIFIED | F-009; fixed window reads bank $1F, the last of 256K |
| W-16 | Three selectable CHR configurations (eight 1K; 2K at $0000/$0800 + four 1K at $1000+; the inverse) | VERIFIED | F-006. The four (K, C) combinations give these three size layouts, two of them with eight 1K banks |
| W-17 | Four register pairs at $8000/$A000/$C000/$E000; even address selects the low register, odd the high | PARTLY | A0, A13, A14 verified (F-011-F-016, F-029). Aliasing over A1-A12 not testable here |
| W-18 | Bank select layout `CPKx RRRR` (bit 7 C, bit 6 P, bit 5 K, bit 4 unused) | VERIFIED | F-006, F-009, F-040. Bit 4 has no visible effect |
| W-19 | R0-R5 select the CHR banks at the listed windows (2 KiB if K=0, 1 KiB if K=1; R0/R1 swap with R2-R5 under inversion) | VERIFIED | F-006, F-039 |
| W-20 | R6 at $8000 (or $C000), R7 at $A000, RF at $C000 (or $8000) | VERIFIED | F-009 |
| W-21 | R8, R9: "If K=1" select the 1 KiB banks at $0400/$0C00 (or $1400/$1C00) | VERIFIED | Windows: F-006. R8/R9 accept writes and keep their values while K=0 (written under K=0, visible after switching to K=1; kept across K=0 and back). "If K=1" is about when they have an effect, not when they can be written (F-049) |
| W-22 | Indices 10-14 are not listed | ANSWERED | No visible effect (F-039) |
| W-23 | Index "specifies which bank register to update on next write to Bank Data" | VERIFIED | F-039 |
| W-24 | K=0: two 2K banks; K=1: four 1K banks at the low half (or high half under inversion) | VERIFIED | F-006 |
| W-25 | P=0: $8000=R6, $C000=RF; P=1: $8000=RF, $C000=R6; $A000=R7 either way | VERIFIED | F-009 |
| W-26 | C inverts: low half becomes the four 1K banks, high half the 2K banks | VERIFIED | F-006 |
| W-27 | CHR table (all 16 cells) | VERIFIED | F-006, run 05 |
| W-28 | "With 2KiB banks only even-numbered banks selectable; the lowest bit is ignored and passes PPU A10 to CHR A10" | VERIFIED | F-007 |

### 2.3 PRG banks, bank data, mirroring, $A001

| ID | Assertion | Verdict | Evidence |
|---|---|---|---|
| W-29 | R6, R7, RF, $8000 are "unspecified at power on", so the reset vector must be in $E000-$FFFF | CONTRADICTED (qualified) | Deterministic over 7 cold starts: all PRG windows read bank $1F; CHR behaves as 1 KB mode with banks 0 (F-002, F-003, F-045). The advice stays prudent for other chips |
| W-30 | PRG table, and "(-1) is the last bank" | VERIFIED | F-009 |
| W-31 | Bank data: "all eight bits are used for a new value for the bank" | PARTLY (CONTRADICTED for PRG) | CHR registers use all eight (F-007). R6, R7, RF: only the low five bits reach the chip's outputs (F-010) |
| W-32 | Mirroring bit M: 0 vertical, 1 horizontal; other bits unused | VERIFIED | F-041 |
| W-33 | "This applies to mapper 64 only" | NOT TESTABLE | Board variant |
| W-34 | $A001 "either not implemented or has undiscovered functionality" | CONSISTENT | No effect on any CHR, PRG or CIRAM output for six values (F-042), and none on IRQ timing, release or assertion (F-053). No function found |
| W-35 | "There is not presently any reason to believe that RAMBO-1 has any support for PRG-RAM" | VERIFIED | The 40 pins contain no RAM chip-enable, write-enable or output-enable. The only chip select is PRG /CE (F-012). The chip cannot switch external PRG RAM |

### 2.4 IRQ registers

| ID | Assertion | Verdict | Evidence |
|---|---|---|---|
| W-36 | IRQ latch: all eight bits form the reload value | VERIFIED | First expiry at 4(L+1)+2 for L = 0-5, 8, 11, 10, 20, 40, 55, 80, AA, FF: every bit exercised (F-054, F-035) |
| W-37 | When the counter is zero, or a reload is requested through $C001, the latch is copied into the counter "at the end of the current scanline" | PARTLY | The copy happens at the next counting clock using the latch value present then (A12: second counted edge, F-038; CPU: first clock, F-028). "End of the scanline" is not a chip-visible event |
| W-38 | $C001 bit 0: 0 = scanline mode, 1 = CPU cycle mode; other bits unused | VERIFIED | F-027 |
| W-39 | Writing $C001 clears the counter so it is reloaded at the next clock | VERIFIED | F-024, F-038 |
| W-40 | ...and resets the prescaler in cycle mode | VERIFIED | The first expiry is the same however the prescaler stood before the write (F-024) |
| W-41 | ...so the next clock occurs 4 cycles later | CONTRADICTED (by one cycle) | The first clock is 5 M2 falls after the $C001 write cycle (F-028). Replay with 4: 111 mismatches. May reflect internal write synchronisation |
| W-42 | $E000: any value disables counter interrupts AND acknowledges pending ones | VERIFIED | F-029, F-032 |
| W-43 | $E001: any value enables; writing it does not acknowledge a set IRQ | VERIFIED | F-030, F-032 |

### 2.5 IRQ counter operation

| ID | Assertion | Verdict | Evidence |
|---|---|---|---|
| W-44 | Two modes: PPU A12 ("scanline") and CPU cycle | VERIFIED | F-018, F-021 |
| W-45 | Scanline mode is clocked "very similar to the MMC3 and follows the same restrictions" | PARTLY | The restrictions seen on A12 (low-time filter, F-022; sampling in step with M2, F-023) are MMC3-like. No MMC3 on the jig |
| W-46 | The interrupt triggers later than MMC3's, "delayed until M2 falls twice after the PPU A12 rise" | VERIFIED | /IRQ stays high through the first M2 fall after the clocking A12 rise and goes low after the second, whether A12 rose while M2 was low or high (F-050) |
| W-47 | CPU cycle mode: counter clocked every 4 CPU cycles | VERIFIED | F-018 |
| W-48 | CPU mode IRQ triggers "one M2 cycle later than one would naively expect" | CONSISTENT | Best fit: /IRQ asserts 1 M2 cycle after the clock that brings the counter to zero (replay 0 mismatches; "naive" is not defined by the page) |
| W-49 | IF $C001 was written since the previous clock: reload the counter with the reload value | VERIFIED | F-024, F-038 |
| W-50 | ...and if non-zero, the value is "ORed with 1" | CONTRADICTED | First expiry is L+2 edges (A12) or 4(L+1)+2 cycles (CPU) for L = 2, 4, 8; a forced OR 1 gives 282 mismatches (runs 16, 20-27, 32, 33) |
| W-51 | ELSE IF the counter is 0: reload with the reload value | VERIFIED | Repeat interval L+1 edges (A12, F-037) and 4(L+1) cycles (CPU, F-019) |
| W-52 | ELSE decrement by 1 | VERIFIED | F-018, F-037 |
| W-53 | If the counter is now 0 AND IRQs are enabled: trigger | VERIFIED | Expiries while disabled are lost (F-031) |
| W-54 | ...the trigger comes "after 4 CPU cycles" | CONTRADICTED | CPU mode: 1 M2 cycle after the zero clock (0 mismatches; 4 cycles gives 22 in run 16 alone). A12 mode: one further M2 fall after the clocking fall (F-050). Neither is 4 cycles. The page's "M2 falls twice" (W-46) is the right one for A12 mode |
| W-55 | "It's still unknown how the extra kick works. Klax still requires +1" | ANSWERED | See U-2 |
| W-56 | Most emulators run Skull and Crossbones with a glitched scanline | NOT TESTABLE | Emulator and game behaviour. Measured parameters in section 4 may help emulator authors |

### 2.6 The refined scanline rules

| ID | Assertion | Verdict | Evidence |
|---|---|---|---|
| W-57 | M2 falling edge, PA12 = 0: if the 4-bit counter < 16, increment it | VERIFIED | 16 low M2 falls count and 15 do not, whether A12 dropped while M2 was low or high; the falling edge is what is counted, not the rising edge (F-022, F-051) |
| W-58 | M2 falling edge, PA12 = 1: if the 4-bit counter = 16, clock the 8-bit counter | VERIFIED | Clocks only after >= 16 low falls; needs the M2 fall while A12 is high (A12 high across only a rise never counts, across only a fall does); one clock per pulse however long A12 stays high (6 cycles tried) (F-023, F-051) |
| W-59 | ...and always reset the 4-bit counter to 0 | VERIFIED | A pulse closer than 16 falls to the previous never counts; a `$C001` write with A12 already high leaves the filter reset, so pulse 1 counts (F-051, F-052) |
| W-60 | On an 8-bit clock with value 0: trigger IRQ if enabled, reload from $C000; else decrement | VERIFIED | Interval structure confirmed (F-021, F-037). Both this and the main-text ordering reproduce the A12 data |
| W-61 | ...the trigger waits one more cycle "regardless of PA12 next cycle" | VERIFIED | /IRQ still goes low after the second fall when A12 drops again after the first fall, including during M2 high (F-050, variants C and D) |
| W-62 | On a write to $C001: reload the 8-bit counter with the value in $C000 | CONTRADICTED | The latch present at the first real clock is used, not the one at the write (F-038, run 33). Forcing reload at the write: 340 replay mismatches; the page's refined variant: 20 in run 33 and 74 in run 23 |
| W-63 | ...and set the 4-bit counter to 17 | CONTRADICTED (as unconditional) | The filter is forced to 17 only if it is already full (16) at the `$C001` write; otherwise it is left alone and pulse 1 counts. With filter always 17: 17 of 28 samples in run 56 mismatch (F-052) |
| W-64 | "Following these rules has demonstrated accurate behavior, but this needs to be refined and merged" | ANSWERED | See U-4. With W-50, W-54 and W-62 corrected, the merged rules reproduce 3365 recorded samples |

### 2.7 Variants and notes

| ID | Assertion | Verdict | Evidence |
|---|---|---|---|
| W-65 | Mapper 158 wires CIRAM A10 to CHR A17, bit 7 of each CHR bank controls the nametable page | NOT TESTABLE (board wiring) | CONSISTENT: CHR A17 carries bit 7 of the CHR bank (F-007) |
| W-66 | Games not using extended features are "mostly compatible with a standard MMC3" with minor IRQ timing differences | NOT TESTABLE | Needs an MMC3 and games. CONSISTENT with the A12 interrupt being one counted edge later than a plain reload-on-first-edge model (F-021) |
| W-67 | See also: mapper 176; Disch's list | NOT TESTABLE | References |
| W-68 | The \Firebug\ mapper document's initial state "is inaccurate" | NOT TESTABLE as stated | The document was not compared. The measured initial state is in the functional description, section 5, for anyone who wants to |

## 3. Things the page marks unknown, and the answers

| ID | Unknown | Answer from the jig |
|---|---|---|
| U-1 | What $A001 does; whether it is PRG-RAM related (W-34, W-35) | No effect on CHR, PRG, mirroring for `00, 01, 40, 80, C0, FF` (F-042). The chip has no pin that could carry a RAM enable (W-35). No effect on IRQ timing or release either (F-053) |
| U-2 | "How the extra kick works" (W-55) | There is no OR-with-1 (W-50). The extra step is that **the first A12 edge after $C001 is not counted, when the A12 filter is full at the write** (A12 low for 16 or more M2 falls, the normal case). $C001 forces a full filter to 17, which is not 16, so the first rising edge does not clock; the second edge loads the latch and L more edges bring the counter to zero: /IRQ on edge L+2 instead of L+1. When the filter is not full at the write, the first edge counts and /IRQ comes on edge L+1 (F-052). This is the "+1" that Klax needs |
| U-3 | Why emulators glitch Skull and Crossbones (W-56) | Not determinable without the game. If an emulator reproduces the first-edge swallow, the first-interval latch timing (second edge) and the 16-cycle filter, it follows the measured chip |
| U-4 | "Refine and merge" the two IRQ descriptions (W-64) | Merged model in section 4: single algorithm, no OR 1, filter set to 17 by $C001, latch taken at the first real clock, CPU first clock at 5 cycles, 1-cycle assert delay. 0 mismatches over 3365 samples |
| U-5 | Power-on values of R6, R7, RF and $8000 (W-29) | R6, R7, RF read as bank $1F; $8000 behaves as K=1 with banks 0 (CHR), P and C not separable; /IRQ asserted; mirroring vertical; IRQ latch $FF (F-001 to F-004, F-034-F-036, F-045) |
| U-6 | The meaning of $8000 bit 4 ("x") | None visible (F-040) |
| U-7 | Indices 10-14 | None visible (F-039) |
| U-8 | The A12 mode delay ("M2 falls twice", "after 4 cycles", "1 more cycle": three descriptions on the page) | CPU mode: 1 M2 cycle after the zero clock. A12 mode: /IRQ goes low after the second M2 fall following the clocking rise, i.e. 1 M2 fall after the clocking fall (F-050). "M2 falls twice" and "wait 1 more cycle" are right; "4 CPU cycles" is not |

## 4. Replay of the IRQ models against the recorded logs

`tools/irq_model_check.py` replays the command stream of each recorded IRQ run (14 experiments, 3393 samples of /IRQ) through
candidate counter models and counts samples where the model disagrees with the chip. Two simulator bugs (a delay
counted down in the fall that set it; a wrong initial filter value) were found and fixed while building it; both were
bugs in the simulator, not chip behaviours. Events are M2 falling edges; A12 is
sampled on them, as in the page's refined description.

| Experiment | ours (merged) | OR 1 added | filter always 17 | filter = 0 | counter loaded at $C001 write | clock at 4 cycles | page: main text | page: refined |
|---|---|---|---|---|---|---|---|---|
| 16 CPU, L=1,2,3,4,8 | 0/258 | 12 | 0 | 0 | 20 | 5 | 22 | 5 |
| 19 A12 threshold | 0/72 | 0 | 0 | 1 | 49 | 0 | 0 | 0 |
| 20 A12 count vs latch | 0/98 | 3 | 0 | 7 | 6 | 0 | 3 | 0 |
| 21 CPU prescaler phase | 0/341 | 48 | 0 | 0 | 48 | 21 | 66 | 21 |
| 22 $C001 rewrite | 0/383 | 51 | 0 | 0 | 43 | 27 | 67 | 27 |
| 23 latch change | 0/623 | 40 | 0 | 0 | 72 | 32 | 86 | 74 |
| 24 mode switch | 0/254 | 20 | 0 | 1 | 20 | 3 | 26 | 3 |
| 25 $C001 data bits | 0/209 | 26 | 0 | 6 | 26 | 5 | 36 | 5 |
| 26 $E000/$E001 (CPU) | 0/840 | 72 | 0 | 0 | 72 | 18 | 102 | 18 |
| 27 $E000/$E001 (A12) | 0/86 | 0 | 0 | 8 | 8 | 0 | 0 | 0 |
| 31 A12, power-on latch | 0/16 | 0 | 0 | 1 | 1 | 0 | 0 | 0 |
| 32 A12 period | 0/60 | 6 | 0 | 9 | 9 | 0 | 6 | 0 |
| 33 A12 latch load | 0/125 | 4 | 0 | 14 | 14 | 0 | 4 | 20 |
| 56 $C001 vs filter state | 0/28 | 0 | 17 | 7 | 0 | 0 | 17 | 17 |
| **Total** | **0/3393** | 282 | 17 | 54 | 388 | 111 | 435 | 190 |

Column key: "ours" is the merged model below; the next five are single changes to it (OR 1 on the first reload; the filter
always forced to 17 by $C001; the filter set to 0 by $C001; the counter loaded from the latch at the $C001 write; the first CPU
clock 4 cycles instead of 5 after $C001). The last two are the page's own algorithms: the main text (OR 1, first clock
at 4 cycles, trigger after 4 cycles) and the refined pseudo-code (reload at the $C001 write, trigger when the value is
zero at the clock).

**What the replay can and cannot say.** Two numbers in the CPU-mode part of the merged model were fitted to the CPU logs:
the first clock at 5 cycles and the 1-cycle assert delay. The A12-mode part has no fitted parameter (the assert delay
there was measured directly in exp 52). Replay assumptions: the filter starts full, and it tracks A12 in both modes (not
observable in CPU mode). Zero mismatches shows the model is consistent
with everything recorded; the ablations show which pieces are needed.

**Merged model**

```
state:   latch (8 bits, power-on $FF), cnt, reload_pending, enabled, /IRQ line, filt (0..17), prescaler, mode
$C000 w: latch = data
$C001 w: mode = data bit 0;  reload_pending = 1;  if filt = 16: filt = 17;  prescaler restarts (first CPU clock 5 M2 falls later)
$E000 w: enabled = 0;  /IRQ released
$E001 w: enabled = 1                                   (counter and /IRQ unaffected)
every M2 falling edge:
   CPU mode:  advance prescaler; every 4th step: CLOCK
   A12 mode:  if A12 = 0:  if filt < 16: filt++
              else:        if filt = 16: CLOCK;   filt = 0
CLOCK:     if reload_pending:   cnt = latch;  reload_pending = 0        (no OR 1)
           elif cnt = 0:        cnt = latch
           else:                cnt--
           if cnt = 0 and enabled:  assert /IRQ one M2 fall after the clocking fall (both modes)
```

Run it: `python3 -I tools/irq_model_check.py` (variants are defined at the top of the file).

## 5. Experiments run for this review

Generated by `tools/gen_nesdev_checks.py`; run 2026-10-31 on the chip after a cold start, SW1C ON, flying wire off.

| Exp | Script | Result | Rows decided |
|---|---|---|---|
| 51 | `51_k_gates_r8_r9.txt` | R8/R9 accept writes and keep values while K=0 (F-049) | W-21 |
| 52 | `52_a12_latency.txt` | /IRQ low after the second M2 fall following the clocking rise, independent of A12 afterwards (F-050) | W-46, W-54, W-61, U-8 |
| 53 | `53_a12_filter_shape.txt` | the filter counts M2 falling edges; clocks at the fall with A12 high; once per pulse; `$C001` with A12 high does not swallow (F-051, F-052) | W-57, W-58, W-59, W-63 |
| 54 | `54_a001_irq.txt` | `$A001` has no effect on the IRQ (F-053); one unreproduced outlier in the first run | W-34, U-1 |
| 55 | `55_latch_bits.txt` | all eight latch bits work (F-054) | W-36 |
| 56 | `56_c001_filter_state.txt` | `$C001` forces the filter to 17 only if full (F-052) | W-63, U-2 |

**Lesson from this round.** Experiments 52 and 53 first gave wrong answers because their setup did not make the A12 filter
full before `$C001`, so the result depended on what ran before. That led to experiment 56 and the finding that the "set to
17" is conditional. All earlier IRQ runs (16-33) happened to have the filter full, which is why the replay matched them. Logs
from the first, flawed versions are marked superseded in `docs/findings.md`.

## 6. Measured behaviour the page does not mention

The extracted text of the page does not mention the integrated CIC (lockout) function on pins 15-18. Its linked
pinout page was not read for this review, so whether that page covers it is unchecked. The jig has not measured the CIC
(functional description section 9), so there is no verdict to give; it is listed here only as something the main page is silent on.

Candidates for adding to the wiki, each with its finding: power-on state (F-001-F-004, F-034, F-035); the 16-M2-cycle
A12 low requirement and the need for an M2 edge while A12 is high (F-022, F-023); the latch taken at the second counted edge
in scanline mode and about 5 cycles after $C001 in cycle mode (F-028, F-038); expiries while disabled are lost (F-031);
the counter runs while disabled (F-019); /IRQ stays low until $E000 (F-020); only five PRG bank bits (F-010); $8000 bit 4,
indices 10-14, $A000 bits 1-7 and $A001 do nothing visible (F-039-F-042); the /CE truth table (F-012); the register-write
window (F-013-F-017); pin 19 as a test input (F-043-F-047).

## 7. Suggested corrections to the wiki text

1. Remove "ORed with 1". Replace "(see notes)" with: the first real clock after $C001 loads the latch unchanged.
2. Scanline mode: if A12 has been low for 16 or more M2 cycles when $C001 is written (the usual case), the first rising edge of
   A12 afterwards does not clock the counter, so the interrupt occurs on counted edge L+2 (instead of L+1).
   Otherwise the first edge counts and the interrupt occurs on edge L+1.
3. Refined rules, $C001: "If the 4-bit counter is 16, set it to 17. Mark the 8-bit counter to be loaded from $C000 at the next
   real clock" (not "reload ... with the value in $C000" at the write, and not an unconditional 17).
4. Cycle mode: the first clock is 5 M2 cycles after the $C001 write (not 4); /IRQ asserts 1 M2 cycle after the zero clock.
5. Bank data: R6, R7, RF use bits 0-4 only. R8 and R9 can be written with K=0 and keep their values.
6. Power-on: the PRG banks read $1F, mirroring is vertical, the latch is $FF, /IRQ is asserted until $E000.


## 8. Reproducing

- Page text: `curl -sS "https://www.nesdev.org/w/index.php?title=RAMBO-1&action=raw"`; compare the SHA-256 above.
- IRQ replay: `python3 -I tools/irq_model_check.py` (needs `results/*.csv` from runs 16-33 and 56).
- Experiments: `python3 -I tools/gen_nesdev_checks.py`, then
  `tools/rambo_run.py experiments/5N_*.txt --power warm --no-trace` (a cold start first, SW1C ON).

## 9. Revision history

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-10-31 | First pass; 68 assertions; replay of 13 IRQ experiments; experiments 51-55 generated but not run |
| 0.2 | 2026-10-31 | Experiments 51-56 run; pending rows decided; W-63 changed (the 17 is conditional); replay now 14 experiments, 3393 samples |
