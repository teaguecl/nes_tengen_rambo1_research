# RAMBO-1 reference model

`rambo1.py` is the Tengen RAMBO-1 (337006, mapper 64) as a state machine, written from `docs/findings.md`; every rule carries the finding that
supports it. It has no dependencies and no I/O. Use it to read the rules, to port to an emulator or an HDL, or as a test oracle.

```python
from rambo1 import Rambo1
m = Rambo1()                      # power-on state
m.write(0x8000, 6); m.write(0x8001, 5)    # CPU write cycle (address >= $8000)
m.cycle(a12)                      # end of every M2 cycle: a12 = PPU A12 at the M2 fall
m.prg_bank(0x8000), m.chr_bank(0x0400), m.ciram_a10(0x2400), m.irq
```

Order inside one CPU cycle: writes, then `cycle(a12)`. See the module docstring and `docs/emulator_guide.md` section 4.

- `test_rambo1.py`: 38 checks of the model against the measured behaviour (`./drun.sh python3 -I reference/test_rambo1.py` from the repo root).

Changes after the first version: the A12-mode enable flag is tested one M2 fall after the clocking fall (F-074), and with latch 0 only the reload after `$C001` expires (F-075). The model has been replayed over about 1.5 million captured console cycles
(`rom/tools/la_p9_analysis.py`, `la_p18_analysis.py`) with no /IRQ mismatch, and it passes all six test ROMs.
- `../rom/tools/hwsim.py ROM --model ref`: runs a test ROM with this model as the chip; all six ROMs pass.
- `../rom/tools/run_checks.sh`: builds the ROMs and runs everything (unit checks, simulator with both chip models, MesenCE if present).

Not modelled (not characterised): sub-cycle timing, the A12 filter's start-up value (assumed full), pin 19 beyond the stored-value rule.
