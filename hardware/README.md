# Hardware: jig and adapter boards

KiCad projects for the boards used to characterise the RAMBO-1.

| Folder | Board | Used for |
|---|---|---|
| `jig_board/` | Cart / jig board: the RAMBO-1 (U1) with the NES edge connector footprint, flash chips U2/U3, switches SW1A-C, header J2 and the CIC header J3 | The device under test. In the console it is a flash cart. On the bench it is driven through J2 |
| `mega_adapter/` | Arduino Mega 2560 shield with the 40-way ribbon to J2 | The first jig (`../firmware/rambo_jig/` firmware) |
| `rp2350_adapter/` | Olimex RP2350-PICO2-BB48 carrier with three 74HCT541 drivers (5 V stimulus) and two 74LVC541A buffers (outputs) | The PIO-engine adapter (`../firmware/rp2350_jig/` firmware), experiments E2 to E10 |
| `generators/` | `rambo1_cart.py` (SKiDL netlist of the cart from the verified continuity map), `rambo1_cart_sklib.py`, footprint generators, adapter pin maps | Regenerate the netlist and footprints |

Each board folder has the KiCad project (`.kicad_pro`, `.kicad_sch`, `.kicad_pcb`), its symbol library, the `nes_cart.pretty` footprints.

## Status

- The designs were built and used. The RP2350 adapter board was checked against the pin map (all 33 signals match) and is documented in
  [`../docs/rp2350_adapter_plan.md`](../docs/rp2350_adapter_plan.md) and [`../docs/rp2350_bringup.md`](../docs/rp2350_bringup.md).
- Loopback calibration of the adapter's edge timing has not been done (it needs jumper wires). Treat adapter timings of a few ns as uncertain.
- The Olimex module is third-party: https://github.com/OLIMEX/RP2350-PICO2-BB48 (design files and documents).
- Open the projects with KiCad 10. Library tables use `${KIPRJMOD}`, so they should open from any location.

## Safety (read before building the jig)

- Never connect a jig or adapter while the cart is in a console.
- Remove flash chips U2 and U3 in jig mode, so nothing else drives the CPU data bus.
- Fit SW1C (RAMBO pin 19 to GND). Switch SW1A and SW1B off (flash write enable).
- Enable cart power before the drivers, and disable the drivers before cutting power.
- Never connect the Mega jig, the RP2350 adapter and the logic analyser to the cart at the same time. Power the console off before moving analyser leads.
- Use a powered USB hub for long adapter runs. Two unpowered runs crashed the host's USB controller.

The full rules are in [`../CLAUDE.md`](../CLAUDE.md) and [`../docs/hardware.md`](../docs/hardware.md).

Licence: CERN-OHL-P-2.0, see `LICENSE-hardware.md`.
