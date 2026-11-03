#!/bin/sh
# Build the ROMs, run each on the hardware-model harness (must pass) and on MesenCE headless (report only).
# Usage: tools/run_checks.sh [path-to-MesenCE-binary]   (default ~/Downloads/Mesen, a MesenCE build)
cd "$(dirname "$0")/.." || exit 1
MESEN=${1:-$HOME/Downloads/Mesen}
make -s || exit 1
echo "== reference model unit checks"
python3 -I ../reference/test_rambo1.py || exit 1
rc=0
for r in g1_power_on g2_banking g3_bus g4_cpu_irq g5_a12_irq g6_raster; do
    echo "== $r: hardware model (all tests must pass)"
    python3 -I tools/hwsim.py build/$r.nes --quiet || rc=1
    echo "== $r: reference model (reference/rambo1.py; all tests must pass)"
    python3 -I tools/hwsim.py build/$r.nes --model ref --quiet || rc=1
    if [ -x "$MESEN" ]; then
        echo "== $r: MesenCE (failures here are expected where the emulator differs from the chip)"
        timeout 90 "$MESEN" --testRunner tools/mesen_dump.lua build/$r.nes 2>&1 | grep -E "FAIL|CODE|status|FAILED|PASSED"
    fi
done
echo "== timing probe: bus pattern and chip outputs of all the phases"
python3 -I tools/probe_check.py || rc=1
[ -x "$MESEN" ] && sh tools/delay_check.sh "$MESEN"
exit $rc
