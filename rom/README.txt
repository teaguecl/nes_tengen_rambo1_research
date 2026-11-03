Tengen RAMBO-1 (mapper 64) Test ROMs
------------------------------------
These ROMs test the behavior of the Tengen RAMBO-1 mapper chip (337006,
iNES mapper 64) on a real NES, and in emulators. They were written from
measurements of a real chip and every test passes on real hardware (NTSC
console, chip on a flash development cart).  There are six groups of tests,
one group for each ROM.

The tests start with basic functionality and build up: a later test in a ROM
is skipped when a test it depends on has failed, so the first failure points
at the cause.


Contents
--------
  Running the tests
  Output of the tests
  Failure codes and INFO lines
  Test ROMs
    g1_power_on   power-on state                 (5 tests)
    g2_banking    banking and register decode    (14 tests)
    g3_bus        bus behavior                   (7 tests)
    g4_cpu_irq    CPU-cycle IRQ                  (13 tests)
    g5_a12_irq    A12-mode (scanline) IRQ        (12 tests)
    g6_raster     rendering and raster splits    (11 tests)
  Emulator notes
  Building the ROMs
  Files and further reading


Running the tests
-----------------
Run a ROM on a console or in an emulator, wait for the result screen, and
read it. Nothing needs to be pressed. Each ROM finishes in well under a
second of emulated time, except g6_raster, which first shows a four-second
raster demo and finishes after about six seconds.
My emulator is the only one I'm aware of that passes all six tests as of
November 2026 (https://github.com/teaguecl/ONE).

Hardware: each ROM is an iNES 2.0 file for mapper 64 with 256 KB of PRG and
256 KB of CHR ROM. It runs on a cartridge that carries a RAMBO-1 and has the
PRG ROM output enable driven by the RAMBO's PRG /CE output (the original
Tengen boards do this). The ROMs use no PRG RAM, no battery, and no feature
of any particular cartridge.

g1_power_on checks the chip's power-on state, so it must be run after
POWERING THE CONSOLE ON. The reset button does not reset this mapper: after a
reset, g1_power_on gives false failures (its first test, normally, because
the previous run disabled the interrupt). The other ROMs can be started
either way.

The header says horizontal mirroring on purpose. The chip powers on with
vertical mirroring, and g1_power_on checks that it is not the header that
decides.


Output of the tests
-------------------
Every ROM shows its report on the screen and leaves the same result in RAM.

Screen. The background is GREEN when all tests passed and RED when any
failed. The first lines give the ROM name and a note, then one line per test:

   RAMBO-1 G5: A12-MODE IRQ
   POWER-ON OR RESET. ANY START.

   01 FIRST EXPIRY AT L+2      PASS
   02 FIRST EXPIRY L=0, L=1    PASS
   03 REPEAT PERIOD L+1        PASS
   ...
   0A CPU TO A12 MODE          PASS

   ALL TESTS PASSED

A failing test shows its detail on the next line, and the bottom line gives
the number of failed tests:

   03 REPEAT PERIOD L+1        FAIL
     CODE 02 GOT 02 EXP 03 AT 01
   ...
   TESTS FAILED: 01

A test that was not run because a test it depends on failed shows SKIP.
A test that only reports a value shows PASS and an INFO line (see below).
All numbers on the screen are hexadecimal.

RAM. For automation:

   $0300       status: $80 while running, $00 if all tests passed, otherwise
               the failure code of the first failing test
   $0301-$0303 signature $DE $B0 $61 (valid once the ROM has started)
   $0304...    the report text, ASCII, zero-terminated (the same lines as the
               screen; line feed = $0A)

Read the status after the report is complete (status no longer $80).

Sound. A series of beeps repeats: ONE beep means all tests passed, N beeps
means the first failing test had failure code N.


Failure codes and INFO lines
----------------------------
The failure code is the second number on the detail line ("CODE 02"). Code 2
is the usual "the result was wrong" and codes above 2 name a more specific
case; they are given with each test below. "GOT", "EXP" and "AT" are
one-byte values whose meaning also depends on the test:

   GOT  what the ROM read or measured
   EXP  what the chip should have given
   AT   where: a window, register, latch value or step number

An INFO line follows a test that records a discovery value. It is not a
failure and has no expected value that must match, but the values seen on
real hardware are given below, and a different value from an emulator is a
sign worth a look.


Test ROMs
---------

g1_power_on: power-on state
...........................
Valid only after powering the console on. Nothing in this ROM writes a
mapper register until the checks are done. The ROM disables the APU frame
interrupt first, so that only the mapper can pull /IRQ.

 1 IRQ ASSERTED AT POWER-ON   With interrupts enabled, an interrupt must
   arrive at once: the chip holds /IRQ low from power-on until $E000 is
   written. Then a write to $E000 must release it.
   Code 2: no interrupt arrived. Code 3: still interrupting after $E000.
 2 PRG BANK 1F AT POWER-ON    The windows at $8000, $A000, $C000 and $E000
   all show PRG bank $1F, read back through the bank's identity block.
   Code 2: wrong bank (AT = window high byte).
 3 CHR BANK 0 AT POWER-ON     All eight 1 KB CHR windows show bank 0, read
   through PPU address $2007. Code 2: the bank number is wrong. Code 3: the
   check byte is wrong. (AT = window)
 4 MIRRORING VERTICAL         Writes to nametables $2000, $2400, $2800 and
   $2C00 must alias as vertical mirroring, even though the header says
   horizontal. Code 2: not vertical.
 5 IRQ LATCH FF (CPU MODE)    With CPU-cycle mode started by $C001 = 1 and no
   write to $C000, the first interrupt must arrive after about 1026 cycles
   (latch $FF); the ROM times it with a 13-cycle loop and accepts 936 to 1118
   cycles. Code 2: GOT = loop passes counted (0 = no interrupt), EXP = 79.

Real hardware, after power-up: 5 of 5 pass. After a reset, test 1 fails
(CODE 02 GOT 00 EXP 01), which is the expected consequence of the reset button
not resetting the chip, not a fault.


g2_banking: banking and register decode
.......................................
Banks are identified by reading back the identity block at the start of each
8 KB PRG bank and 1 KB CHR bank, never by looking at the picture. PRG is read
through the CPU, CHR through $2007. The ROM uses all 32 PRG banks and 256 CHR
banks.

  1 PRG R6 R7 RF BANKS      P=0: R6 at $8000, R7 at $A000, RF at $C000, bank
                            $1F fixed at $E000.
  2 PRG MODE BIT SWAPS      P=1 swaps the $8000 and $C000 windows (R6 <-> RF).
                            Code 3: swapping back by an $8000 write failed.
  3 PRG 5-BIT BANK WIDTH    Only the low 5 bits of R6, R7 and RF reach the
                            ROM: values $20+n, $40+n, $80+n read bank n.
  4 PRG ALL 32 BANKS        R6 = 0..31 each show their own bank.
  5 CHR 1K MODE R0-R5 R8 R9 K=1: windows R0 R8 R1 R9 R2 R3 R4 R5.
  6 CHR 2K MODE PAIRS       K=0: R0 and R1 each cover a pair of 1 KB halves.
  7 CHR INVERSION BIT       C=1 swaps the two 4 KB halves of CHR space.
                            Code 2: with K=1. Code 3: with K=0.
  8 CHR 8-BIT BANK WIDTH    All 8 bits of the CHR registers reach the ROM.
  9 CHR 2K ODD R0 R1 (A10)  In 2 KB mode bit 0 of R0 and R1 is replaced by
                            PPU A10, so an odd value maps the same pair as
                            the even value below it.
 10 R8 R9 ONLY WITH K=1     R8 and R9 accept writes while K=0, keep their
                            values, and only act when K=1.
                            Codes: 2 K=1 does not show R8/R9, 3 new R8 not
                            used, 4 K=0 does not ignore R8, 5 R8 lost when K
                            went 0 -> 1.
 11 MODE BITS BY $8000 ALONE Changing K, P or C by writing $8000 only (no
                            $8001 afterwards) changes the mapping at once.
                            The code is the step number that failed.
 12 INDEX A-E, BIT 4 IGNORED Register indices $A-$E select nothing, and bit 4
                            of $8000 changes nothing.
 13 MIRRORING $A000 BIT 0   Only bit 0 of $A000 matters: 0 vertical, 1
                            horizontal (AT = value written).
 14 $A001 NO VISIBLE EFFECT Writes to $A001 change no bank and no mirroring.
                            Code 3: mirroring changed.

Failure details: GOT and EXP are the identity bytes of the bank seen and the
bank expected; AT is the window (CHR: 0..7 for $0000..$1C00, PRG: the window
high byte).

Real hardware: 14 of 14 pass.


g3_bus: bus behavior
....................
The tests write to the chip's registers in ways a real CPU does, and check
that nothing else changes. The chip must have the PRG ROM output enable
connected to its /CE output; on an emulator this is always true.

 1 NO BUS CONFLICT          Writes a register while the ROM byte at that
   address differs from the data (pairs chosen so that an AND or OR with the
   ROM byte would change the value). The register must take the data written.
   Code 2: R6 data wrong. Code 3: the index write lost its value (ROM byte 0,
   AND). Code 4: the same with ROM byte $1F (OR).
 2 READ-MODIFY-WRITE FINAL  INC, DEC, ASL and LSR on $8001, INC on $8000 and
   INC on $A000 read the register's address, write the old value back, then
   write the changed value. The register must end with the changed value.
   Codes 2-5: INC, DEC, ASL, LSR on $8001. Code 6: INC $8000. Code 7: INC
   $A000.
 3 ALIASES A1-A12 DECODE    A write to $8000 or $A000 with any one of address
   bits A1-A12 set (for each of the 12 bits) must act as the register at
   the address without that bit: the chip has no A1-A12 pins.
   Code 2: a bank register alias failed (AT = bit number). Code 3: a
   mirroring alias failed.
 4 NO ROMSEL, NO REGISTER   Writes to $4020-$7FFF, where /ROMSEL is high,
   must do nothing. They are checked through the IRQ registers, whose
   addresses with A14 = 1 sit there. Code 2: a write like $E000 released or
   disabled the interrupt. Code 3: a write like $E001 enabled it. Code 4:
   setup failure (no interrupt after the real $E001).
 5 READS DO NOT WRITE       Reads of the register addresses ($8000, $8001,
   $A000, $A001, $C000, $C001, $E000, $E001, $9FFE, $9FFF), with the ROM data
   on the bus, must not change the index or any bank. Code 2: a read acted
   as a write.
 6 READS LEAVE IRQ ALONE    Reads of $E000 and $E001 must not release or
   enable the interrupt. Code 2: a read of $E001 enabled it. Code 3: setup
   failure. Code 4: a read of $E000 released /IRQ.
 7 OPEN BUS $4020/5000/6000 Discovery. Reads three addresses that nobody
   drives and prints the values.
   INFO values: depends on the cartridge, not on the chip. On the
   development cart, which has 1 kohm pull-ups on the data lines, the line
   reads "INFO FF FF FF". A cartridge without pull-ups would give the high
   byte of the address (classic open bus). This is never a failure.

Real hardware: 7 of 7 pass.


g4_cpu_irq: CPU-cycle IRQ
.........................
CPU-cycle mode ($C001 bit 0 = 1) counts M2 cycles. These tests measure the
time of the interrupt to one CPU cycle, so the console or emulator must run
the CPU and the interrupt exactly: an emulator that checks /IRQ at the wrong
point in an instruction can fail here for reasons outside the mapper.

Method: after the $C001 write a run of NOPs executes with interrupts enabled.
The interrupt handler reads the address that was interrupted from the stack,
which gives the expiry time in units of one NOP. The same trial is run again
with the $E001 store made one cycle longer, which gives the cycle. Only
differences between times are checked, so the fixed delay between the chip's
/IRQ and the CPU's poll cancels. Latch values up to 255 are reached with a
delay routine that takes exactly 32q+11 cycles.

 1 IRQ RELEASE AND DISABLE  $E000 releases and disables, $E001 enables.
   Code 2: interrupt while disabled. Code 3: none after $E001. Code 4: still
   interrupting after $E000.
 2 FIRST EXPIRY SLOPE 4/L   The time of the first interrupt for the latch
   values L = 0 1 2 3 4 8 16 40 255 must grow by exactly 4 cycles per step
   of L (L=0 and L=1 included: no special case). Code 2: wrong slope (GOT
   and EXP are the low bytes of the measured and expected difference, AT
   the index of the first L). Code 3: a measurement failed.
 3 THRESHOLD REPEATABLE     L = 4 three more times and L = 255 twice must
   give exactly the first result.
 4 REPEAT PERIOD 4(L+1)     The second interrupt comes 4(L+1) cycles after
   the first (L = 8, 16, 24). Code 2/3: the difference between two latch
   values is wrong. Code 4: no second interrupt.
 5 EXPIRY WHILE DISABLED    With L = 4, $E001 written after the first expiry
   (cycle 26): that expiry is lost, and the interrupt comes at the next one,
   20 cycles later, not at once. Code 2: the time is wrong. Code 3: a
   measurement failed.
 6 E000+E001 KEEP COUNT     $E000 followed by $E001 before the expiry must
   not move it. Code 2: the control run differs (harness problem). Code 3:
   $E000/$E001 moved the expiry.
 7 C001 RESTARTS, KEEPS IRQ A second $C001 written 14 cycles after the first
   moves the expiry later by exactly 14 (code 2). After an interrupt, $C001
   must leave /IRQ low: the interrupt is taken again at once (code 3: it
   was released).
 8 LATCH TAKEN BY CYCLE 5   A $C000 write up to 5 cycles after $C001 sets the
   first interval; later does not. Tested with a write 4 cycles after
   (must be used) and 6 cycles after (must not). Code 2: the write after 4
   cycles was missed. Code 3: the write after 6 cycles was used. Code 4: a
   measurement failed.
 9 C001 MODE SWITCH CANCELS A $C001 write with bit 0 = 0 (A12 mode) 14 or 18
   cycles after the CPU-mode $C001, before the first expiry at 22, cancels
   the expiry: no interrupt in the next 200 cycles. A switch at 26 cycles,
   after the expiry, leaves exactly one interrupt. Codes 2 and 3: an
   interrupt although the switch came first. Code 4: the interrupt at 22 was
   lost.
10 FIRST EXPIRY ABSOLUTE    Discovery. Prints the low bytes of the measured
   time for L = 0, 4 and 255 (the chip's expiry is 6, 22 and 1026 cycles
   after the write; the ROM adds a fixed offset for the CPU's interrupt
   latency and the way the handler reads the PC).
   INFO values on the test console: "INFO 07 17 03". The differences are the
   point: the second is the first plus 16 (4 cycles x 4) and the third ends
   in 03 (4 x 255 + 7 = $403). The absolute offset may differ on another
   console or emulator by a small constant.

11 E001 IN EXPIRY CYCLE     CPU mode, L = 4: the first expiry is 22 cycles
   after the $C001 write cycle. An $E001 written in cycle 22 itself enables
   the interrupt in time: it is taken at once. An $E001 written in cycle 23
   is too late: that expiry is lost (an expiry while disabled is never
   remembered) and the next one, 20 cycles later, is the first interrupt.
   Code 2: GOT = sled position of the first interrupt after the cycle-22
   write (expected below 4). Code 3: no interrupt at all in that trial. Code
   4: GOT = position after the cycle-23 write (expected 7 to 13; FF = none).
12 E000 IN EXPIRY CYCLE     CPU mode, L = 4, interrupt enabled early: an
   $E000 written in cycle 22, the expiry's own cycle, prevents it, and no
   interrupt comes in the next 200 cycles. A control with a store to RAM in
   the same cycle gives the interrupt at once. Code 2: GOT = interrupts taken
   (expected 0). Code 3: the control gave no interrupt (a problem with the
   test, not the chip). This test cannot tell "prevented" from "released
   within the same cycle"; the CPU cannot see the difference either.
13 A12 TO CPU, FILTER LOW   Latch 2, A12 mode, interrupt disabled. A12 is raised and lowered
   with PPUADDR; then $C001 := 1 (CPU mode) and $E001, and a sled of NOPs
   shows when the first expiry comes. Arm A: the $C001 store follows the A12
   fall by about 4 cycles (the A12 filter is not full): the expiry is
   4(L+1)-2 = 10 cycles after the write. Arm B: 44 cycles of NOPs in
   between (the filter is full): 4(L+1)+2 = 14 cycles. Pass when B is taken
   exactly 2 NOPs after A (finding F-087). Code 2: GOT = NOPs(B) - NOPs(A),
   expected 2; AT = NOPs(A). Code 3: no usable interrupt in arm A (det1 = 1)
   or B (2). An emulator that restarts the CPU counter the same way whatever
   the A12 filter holds fails with GOT = 0.

Real hardware: 13 of 13 pass (tests 11 and 12 were added later, findings
F-071 and F-072, and passed on the console on 2026-11-01). Test 13 (F-087)
passes on the hardware model and the reference model and on the console
(13 of 13, 2026-11-02).


g5_a12_irq: A12-mode (scanline) IRQ
...................................
A12-mode counts rising edges of PPU A12 that follow at least 16 M2 falling
edges with A12 low. The ROM makes the A12 pulses itself, with rendering
off, by writing PPU address pairs to $2006 ($10,$00 puts A12 high, $00,$00
low). After every pulse it opens an interrupt window (CLI, NOP, NOP, SEI) and
looks at the interrupt count, so the unit of every result is one pulse. L is
the latch value.

 1 FIRST EXPIRY AT L+2      With the filter full when $C001 is written (A12
   low for a long time), the first interrupt comes at pulse L+2 (the first
   pulse after $C001 is swallowed), for L = 2 3 4 5 6 7 8 16.
   Code 2: GOT = the pulse number of the first interrupt (0 = none), EXP =
   L+2, AT = L.
 2 FIRST EXPIRY L=0, L=1    The same rule for L = 0 and L = 1. A separate test
   because several emulators have a special case here, and the rest of the
   ROM should still run when it fails. Same code and values as test 1.
 3 REPEAT PERIOD L+1        After the first interrupt (acknowledged and
   re-enabled), the next two come L+1 pulses apart, for L = 1..8 and 16.
   Code 2: the first interrupt is wrong. Code 3: the second or third (GOT =
   the pulse seen, EXP = the pulse expected, AT = L).
 4 FILTER NEEDS 16 FALLS    With L=1 and the pulses spaced by a chosen number
   of cycles from fall to the next rise, gaps of 13 and 15 cycles must not
   count, and gaps of 18 to 24 must. Gaps of 16 and 17 are not asserted
   because the threshold can move by one cycle with the CPU/PPU alignment.
   Code 2: a short gap counted (AT = the gap). Code 3: a long gap did not
   count.
 5 FILTER THRESHOLD         Discovery. INFO gives the smallest gap that
   counted, then the result bits of the sweep (gaps 13 15 16 17 18 19 20 21,
   then 22 23 24; bit 0 first, 1 = counted).
   INFO value on the test console: "INFO 10 FC 07": the smallest counted gap
   is 16 cycles, 13 and 15 do not count, 16 to 24 all do.
 6 C000 AT FIRST COUNT      With L = 4 and a new latch of 1 written after 0,
   1, 2 or 4 pulses: written before the first counted pulse (after 0 or 1
   pulses) the interrupt is at pulse 3, written after it (2 or 4 pulses) at
   pulse 6. Code 2: GOT = pulse seen, EXP = expected, AT = number of
   pulses before the write.
 7 FILTER NOT FULL AT C001  If A12 fell only about 12 cycles before the
   $C001 write (the filter is not full), the first pulse counts and the
   interrupt is at pulse L+1, for L = 0, 1, 2. Code 2: GOT = pulse seen,
   EXP = L+1.
 8 E000/E001 IN A12 MODE    $E001 alone does not release /IRQ; $E000 does;
   expiries while disabled are lost and not kept. Codes: 2 first interrupt not
   at pulse 3; 3 $E001 released /IRQ; 4 $E000 did not release it; 5 an
   interrupt where none is due (before the first expiry, or while
   disabled); 6 an expiry that happened while disabled was delivered at the
   enable; 7 no interrupt at pulse 7.
 9 A12 TO CPU MODE          Switching from A12 to CPU mode with $C001 = 1
   restarts the CPU counter: the interrupt is 22 cycles later (L = 4), not
   earlier. Code 2: an interrupt during the pulses. Code 3: an interrupt
   within 10 cycles of the switch. Code 4: none after 50 cycles.
10 CPU TO A12 MODE          CPU mode L = 4 started, switched to A12 mode 14
   cycles later: the pending expiry is cancelled, the A12 counter starts
   clean, and the interrupt comes at pulse 6 (L+2). Code 2: GOT = pulse seen
   (0 = none), EXP = 6.

11 LATCH 0: ONE EXPIRY      Latch 0, twelve pulses, the interrupt acknowledged
   and re-enabled after each one that is taken. The reload after $C001
   (pulse 2) expires and the automatic reload at zero does not: exactly one
   interrupt. (An emulator that expires on every reload to 0 gives 11.)
   Code 2: GOT = interrupts counted, EXP = 1.
12 LATCH 1: EVERY 2ND PULSE The same with latch 1, the control: expiries at
   pulses 3, 5, 7, 9 and 11, so 5 interrupts. Code 2: GOT = interrupts
   counted, EXP = 5.

Real hardware: 12 of 12 pass (tests 11 and 12 were added later, finding
F-075, and passed on the console on 2026-11-01).


g6_raster: rendering and raster splits
......................................
These tests run with the PPU rendering. The scanline of an interrupt is
measured without counting cycles: sprite 0 is placed so that its hit lands on
a known line H0, late on the line (x = 200). The handler reads $2002 at once;
the sprite-0 hit flag is set only if the interrupt came on a line at or
after H0. So the smallest latch value L whose interrupt sees the flag is the
one whose interrupt falls on line H0. The ROM sweeps L over H0-3..H0+3.
The background is a column of "L" tiles, which is what you see on screen
during the tests.

 1 RASTER SPLIT DEMO        Visual. For four seconds the screen is cut into
   four horizontal bands (lines 0-59, 60-119, 120-179 and 180-239) by an
   interrupt every 60 lines that changes the PPU colour emphasis bits (the
   green background changes shade: normal, red, green, blue emphasis), with
   the text "RAMBO-1 RASTER SPLITS" and "BANDS MUST BE STRAIGHT" at the top.
   WHAT TO SEE: the band edges must be straight horizontal lines, in the same
   place every frame, with no flicker or jitter. Ragged or moving edges mean
   the interrupt is late or irregular. This test always passes; it exists
   for the eye.
 2 SPRITE 0 HIT REFERENCE   Without any mapper interrupt, the hit flag must
   be set at the start of vblank. Code 2: no hit (the picture is not set up,
   so the tests below are not valid).
 3 IRQ LINE FOLLOWS LATCH   The offset (smallest latch seeing the hit, minus
   H0) must be the same for H0 = 40, 96 and 152: one line per latch step.
   Code 2: no latch in the window saw the flag (AT = H0). Code 3: the offset
   differs (GOT = offset, EXP = the first offset, AT = index of the H0).
 4 IRQ LINE OFFSET          Discovery. INFO: the offset, the smallest latch
   for H0 = 40 and for H0 = 152.
   INFO value on the test console: "INFO 00 28 98": offset 0 (the interrupt
   is on the line the latch names), 40 and 152 as hex.
 5 BG $1000: LINE L-1       Background at $1000 and sprites at $0000: the
   A12 pulse is at dot 324 and A12 stays high through vblank, so the first
   pulse after $C001 is not swallowed and the interrupt comes one line
   earlier: the smallest latch is H0+1. Code 2: GOT = smallest latch, EXP =
   the expected one, AT = H0.
 6 8X16 SPRITES             8x16 sprites with the tile's bit 0 selecting
   $1000 give the same offset as test 3. Code 2: as test 5.
 7 CHR INVERSION BIT        With the C bit set in $8000 the offset is the same
   (the PPU's A12 is not affected by the mapper's CHR inversion).
 8 NO A12 EDGE: NO IRQ      Both pattern tables at $0000: A12 never rises and
   no interrupt comes in eight frames. Code 2: GOT = interrupts counted.
 9 REPEATED SPLITS          With L = 15, 7 and 127 and the interrupt
   acknowledged each time, eight frames give exactly 120, 240 and 15
   interrupts: a frame has 241 counted A12 pulses (240 lines plus the
   pre-render line). Code 2: GOT = count, EXP = expected, AT = L.
10 CPU-CYCLE SPLITS         CPU-cycle mode, L = 255: 232 interrupts in eight
   frames (first at 1026 cycles, then every 1024). Code 2: GOT = count.
11 BOTH TABLES AT $1000     Discovery: both pattern tables at $1000, L = 0,
   eight frames. INFO shows the number of interrupts.
   INFO value on the test console: "INFO 01 00 00" (one interrupt). This is a
   measured observation only. It is explained by the latch 0 rule: the
   counter expires only on the reload after $C001, so one counted pulse gives
   one interrupt (docs/findings.md F-075).

While the tests after the demo run, the screen shows a column of "L" tiles;
that is the reference for the sprite-0 hit and is normal.

Real hardware: 11 of 11 pass.


Emulator notes
--------------
The tests were chosen to fail in emulators that follow the NESdev
description of mapper 64 instead of the chip. If a test fails in an
emulator, check docs/emulator_guide.md (sections 1 to 3 and 4A), which give
the chip's behavior. In short, the chip:

  * powers on with /IRQ asserted, PRG banks $1F, CHR bank 0 in 1 KB layout,
    vertical mirroring and latch $FF, and is not reset by the reset button;
  * changes K, P and C as soon as $8000 is written;
  * has no special case for latch values 0 and 1, in either IRQ mode;
  * swallows the first A12 pulse after a $C001 write when the A12 filter is
    full, so the first scanline interrupt comes at pulse L+2 (L+1 when the
    filter was not full), and every L+1 pulses after that, except that with
    latch 0 there is only the one interrupt per $C001 (G5 test 11);
  * in CPU-cycle mode takes an $E001 or $E000 written in the expiry's own
    cycle into account, and one a cycle later too late (G4 tests 11, 12);
  * needs 16 M2 falls with A12 low before an A12 rise counts;
  * keeps A12 as the PPU left it between lines and through vblank.

An emulator that passes all six ROMs is not proven identical to the chip
(the rule that, in A12 mode, the enable flag is tested one M2 fall after the
clocking fall, finding F-074, cannot be tested from the CPU side: see
docs/test_rom_design.md, section 17)
(nothing below one CPU cycle was tested), but one that fails any of them
differs from it.


Building the ROMs
-----------------
Ready-made .nes files are in build/. To rebuild, install cc65 2.19 (ca65 and
ld65) and Python 3, then run "make" in this directory. "tools/run_checks.sh"
builds everything and runs the ROMs on the built-in simulator with two chip
models. The MD5 sums in the top-level README were made with the Ubuntu 24.04
package cc65 2.19-1 (ca65 reports itself as "V2.18 - Ubuntu 2.19-1"); another
version may produce different bytes.

To burn a flash chip for a development cart, "tools/mkimage.sh NAME" makes
the 512 KiB image for the PRG chip from build/NAME.nes and verifies it. The
CHR image is the same for every ROM.


Files and further reading
-------------------------
  g1_power_on.s .. g6_raster.s   the test ROM sources (one per group)
  timing_probe.s                 not a test: repeats one bus pattern for a
                                 logic analyser (phases 1-19, chosen by the
                                 controller button held at reset); see
                                 ../docs/logic_analyzer_guide.md section 10
  common/                        shared code: result screen, banking checks,
                                 the exact-cycle delay routine
  tools/                         simulator, scripts, build helpers
  ../docs/functional_description.md   how the chip works as a system
  ../docs/emulator_guide.md      the rules and emulator differences
  ../docs/test_rom_design.md     why each test exists and how it was built
  ../docs/findings.md            every measurement, F-001 to F-090
  ../reference/rambo1.py         the chip as a small Python model


Revision
--------
2026-11-01  First release: six ROMs, all passing on a real RAMBO-1.
