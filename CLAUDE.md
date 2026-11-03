# RAMBO-1 reverse-engineering jig: Arduino Mega firmware

## Goal
Characterize the Tengen RAMBO-1 mapper chip (Tengen 337006, iNES mapper 64) by driving its inputs
and reading its outputs from an Arduino Mega 2560. Confirm the NESdev documentation first, then
probe edge cases (IRQ timing, A12 filtering, power-on state, pin 19, PRG /CE behaviour).

## Hardware chain
Mega 2560 -> Mega adapter board -> 40-wire ribbon -> J2 on the cart/jig board -> RAMBO-1 (U1).
- The Mega powers the cart through J2 pin 1 (+5 V). There is no software power switch on the Mega
  adapter, so power-on experiments need a manual unplug or the later RP2350 adapter.
- All 17 RAMBO inputs pass through 220 ohm series resistors on the cart. 9 control/PPU inputs have
  10k pull-ups; CPU D0-D7 have 1k pull-ups (R8, copied from the original Tengen board).
  Driving a data line low sinks about 5 mA: fine for the Mega, but V_OL reads slightly above 0 V.
- RAMBO /IRQ has a 10k pull-up on the cart (likely open-drain output).
- Full pin map, RAMBO pinout and bus-cycle details: @docs/hardware.md
- Machine-readable maps: docs/j2_mega_pinmap.csv, docs/j2_rp2350_pinmap.csv, docs/cart_netlist.csv

## Jig-mode rules (never break these)
- Never connect the jig while the cart is in a console.
- Flash chips U2/U3 are removed in jig mode, so nothing else drives CPU D0-D7.
- SW1C (RAMBO pin 19 to GND) normally ON. SW1A/SW1B (flash write enable) OFF.
- Optional RAMBO pin 19 control: flying lead from Mega D2 (PE4) through 1 kohm to the pin 19 net (SW1 contact 3A),
  SW1C OFF while it is fitted. Firmware command `p19 0|1|z`; defined in pins.h. Pin 19 is an input; when high every
  register write stores the constant 0B regardless of data (docs/findings.md F-046). A released pin (`z`) keeps its last level
  (F-047), so use `p19 0` for the low state. Leave it driven low (`p19 0`) when not experimenting with it.
- Configure every Mega pin to a defined state at the very start of setup(); the cart pull-ups hold
  the RAMBO inputs idle (M2, R/W, /ROMSEL high) until then.

## Port usage (direct port I/O, not digitalWrite, for speed and atomicity)
- PORTA (D22-D29): CPU D0-D7, output.
- PORTC (D30-D37): M2=PC7, R/W=PC6, /ROMSEL=PC5, A0=PC4, A13=PC3, A14=PC2, PPU A10=PC1, PPU A11=PC0. Output.
- PD7 (D38): PPU A12, output (drives the scanline IRQ counter).
- RAMBO outputs are inputs on the Mega, spread over PG2-PG0, PL7-PL0, PB3-PB0 in physical order
  (see docs/hardware.md). Read all three ports and reassemble.
- /IRQ: D21 = PD0 = INT0, so it can use an external interrupt.
- Mapping was chosen for crossing-free PCB routing, so bit order inside ports is not signal order.
  Keep all bit mapping in one header (e.g. pins.h) and never hard-code it elsewhere.

## Firmware conventions
- Arduino Mega 2560 (ATmega2560, 16 MHz). Arduino IDE / arduino-cli or PlatformIO.
- Serial console at 115200 baud for commands and results.
- Keep a small command interpreter: write register, read outputs, clock M2 N times, pulse A12 N times,
  dump state. Experiments should be scripts of these commands, with results logged as text/CSV.
- Treat NESdev mapper 64 docs as hypotheses to verify, not facts.

## Later: RP2350 adapter
Plan: docs/rp2350_adapter_plan.md (not built yet).
Same J2 pinout via level shifters, Olimex RP2350-PICO2-BB48 (still being sourced).
Firmware rule there: enable cart power (GPIO4) before enabling drivers (GPIO15), disable drivers first.
