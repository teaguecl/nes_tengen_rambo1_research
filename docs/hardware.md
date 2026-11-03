# Hardware reference

Pin numbers for the NES edge connector follow NESdev numbering. (The Tengen silkscreen runs the other way.) Behaviour is in
`functional_description.md` and `findings.md`; this file holds the pinout, what was learned from the original board, and the jig wiring.

## RAMBO-1 (Tengen 337006-001) pinout, verified by continuity on an 800032 Rev A board

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | M2 (in) | 21 | CHR A16 (out) |
| 2 | PRG A16 (out) | 22 | CHR A17 (out) |
| 3 | PRG A15 (out) | 23 | CHR A15 (out) |
| 4 | PRG A13 (out) | 24 | CHR A14 (out) |
| 5 | PRG /CE (out) | 25 | CHR A12 (out) |
| 6 | CPU D6 (in) | 26 | CHR A13 (out) |
| 7 | CPU A0 (in) | 27 | PPU A11 (in) |
| 8 | CPU D4 (in) | 28 | CHR A11 (out) |
| 9 | CPU D2 (in) | 29 | CIRAM A10 (out) |
| 10 | CPU R/W (in) | 30 | /IRQ (out) |
| 11 | /ROMSEL (in) | 31 | CPU D3 (in) |
| 12 | CHR A10 (out) | 32 | CPU D1 (in) |
| 13 | PPU A10 (in) | 33 | CPU D0 (in) |
| 14 | PPU A12 (in) | 34 | CPU D5 (in) |
| 15 | CIC toPak | 35 | CPU D7 (in) |
| 16 | CIC toMB | 36 | CPU A14 (in) |
| 17 | CIC +RST | 37 | PRG A14 (out) |
| 18 | CIC CLK | 38 | CPU A13 (in) |
| 19 | Pin 19 (input; tied to GND on the board) | 39 | PRG A17 (out) |
| 20 | GND | 40 | +5 V |

Pin 19 is an input that is tied to GND on the original board; when it is high every register write stores `$0B` (F-046, F-047, `functional_description.md` section 7).
Pins 15-18 are the integrated CIC (lockout); nothing about them has been measured.

## Observations from the original board

- The 28-pin PRG mask ROM has a single enable (pin 20) driven only by RAMBO pin 5; /ROMSEL does not reach the ROM. Pin 5 is low only for M2 = 1, R/W = 1,
  /ROMSEL = 0, i.e. reads of $8000-$FFFF, which is why there are no bus conflicts (F-012).
- CHR ROM enable = PPU /RD OR PPU A13 (74LS32).
- The RAMBO's own CIC handles lockout (the R6/R7 grounding pads for an external lockout are unpopulated).

## J2 maps

J2 is the 40-pin header on the cart/jig board. Machine-readable maps: `j2_mega_pinmap.csv` (Mega adapter) and `j2_rp2350_pinmap.csv`
(RP2350 adapter); the cart netlist is `cart_netlist.csv`. The Mega map:

| J2 | Signal | Dir | Mega pin | Port bit |
|---|---|---|---|---|
| 1 | +5V | power | 5V |  |
| 3 | D0 | mega_to_rambo | D22 | PA0 |
| 4 | D1 | mega_to_rambo | D23 | PA1 |
| 5 | D2 | mega_to_rambo | D24 | PA2 |
| 6 | D3 | mega_to_rambo | D25 | PA3 |
| 7 | D4 | mega_to_rambo | D26 | PA4 |
| 8 | D5 | mega_to_rambo | D27 | PA5 |
| 9 | D6 | mega_to_rambo | D28 | PA6 |
| 10 | D7 | mega_to_rambo | D29 | PA7 |
| 12 | M2 | mega_to_rambo | D30 | PC7 |
| 13 | RW | mega_to_rambo | D31 | PC6 |
| 14 | ROMSEL_N | mega_to_rambo | D32 | PC5 |
| 15 | A0 | mega_to_rambo | D33 | PC4 |
| 16 | A13 | mega_to_rambo | D34 | PC3 |
| 17 | A14 | mega_to_rambo | D35 | PC2 |
| 19 | PPU_A10 | mega_to_rambo | D36 | PC1 |
| 20 | PPU_A11 | mega_to_rambo | D37 | PC0 |
| 21 | PPU_A12 | mega_to_rambo | D38 | PD7 |
| 23 | PRG_A13 | rambo_to_mega | D39 | PG2 |
| 24 | PRG_A14 | rambo_to_mega | D40 | PG1 |
| 25 | PRG_A15 | rambo_to_mega | D41 | PG0 |
| 26 | PRG_A16 | rambo_to_mega | D42 | PL7 |
| 27 | PRG_A17 | rambo_to_mega | D43 | PL6 |
| 28 | PRG_CE_N | rambo_to_mega | D44 | PL5 |
| 30 | CHR_A10 | rambo_to_mega | D45 | PL4 |
| 31 | CHR_A11 | rambo_to_mega | D46 | PL3 |
| 32 | CHR_A12 | rambo_to_mega | D47 | PL2 |
| 33 | CHR_A13 | rambo_to_mega | D48 | PL1 |
| 34 | CHR_A14 | rambo_to_mega | D49 | PL0 |
| 35 | CHR_A15 | rambo_to_mega | D50 | PB3 |
| 36 | CHR_A16 | rambo_to_mega | D51 | PB2 |
| 37 | CHR_A17 | rambo_to_mega | D52 | PB1 |
| 39 | CIRAM_A10 | rambo_to_mega | D53 | PB0 |
| 40 | IRQ_N | rambo_to_mega | D21 | PD0 (INT0) |

J2 grounds: pins 2, 11, 18, 22, 29, 38.

## Emulating a CPU write on the jig

The real NES drives /ROMSEL low only while M2 is high, for addresses $8000-$FFFF.
1. R/W low; set A0/A13/A14 for the target register; M2 low, /ROMSEL high.
2. Drive D0-D7 (PORTA on the Mega).
3. M2 high, then /ROMSEL low.
4. /ROMSEL high, then M2 low. The chip stores the data present at the first of the M2 fall, the /ROMSEL rise and the R/W rise (F-082).
5. Return R/W high. Data lines may stay driven: with the flash removed nothing else drives the bus.

A CPU read cycle is the same with R/W high and no data driven; use it to observe PRG /CE (pin 5).

## Counting inputs for IRQs

- CPU-cycle mode counts M2 cycles; toggle M2 with /ROMSEL high and R/W high (idle bus cycles).
- A12 mode needs PPU A12 high at an M2 fall after A12 was low for 16 M2 falls (F-084); see `emulator_guide.md` section 2.2.
