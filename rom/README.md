# RAMBO-1 test ROMs

Six ROMs (G1 to G6, 62 tests) for a real NES, in ca65 assembly. **Full description of every test, the result screen, the RAM block and the audio codes: [`README.txt`](README.txt).** Design: [`../docs/test_rom_design.md`](../docs/test_rom_design.md).

- **Build:** from the repo root, `./drun.sh "cd rom && make"` (or `make` here with cc65 and Python 3). Expected MD5 sums are in the [top-level README](../README.md#building-and-running).
- **Check without hardware:** `./drun.sh rom/tools/run_checks.sh` builds the ROMs and runs them on the software models of the chip (`tools/hwsim.py`, `--model hw` or `ref`, with fault flags that mimic emulator deviations). It checks the ROMs' logic, not the chip.
- **Cart:** mapper 64, 256 KiB PRG and 256 KiB CHR (iNES 2.0). Header mirroring is horizontal on purpose (the chip powers on vertical).
- **G1 only after a power cycle:** a reset keeps the mapper state. The other ROMs start from any state.
- **Development flash cart:** the ROMs run unchanged on any cart with a RAMBO-1. On the author's flash cart, switch SW2 must be on "RAMBO*" (PRG chip /OE from the RAMBO /CE output, as on an original board) for G3. Cart-specific results are in `../docs/test_rom_design.md`, section 11.
