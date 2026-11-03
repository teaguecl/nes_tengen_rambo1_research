#!/bin/sh
# Make the 512 KiB flash image for U2 from build/<name>.nes (PRG only, no iNES header, upper half $FF) and verify it.
# Usage: tools/mkimage.sh g5_a12_irq     -> build/g5_a12_irq_prg.bin
cd "$(dirname "$0")/.." || exit 1
n=$1; [ -f build/$n.nes ] || { echo "no build/$n.nes"; exit 1; }
python3 -I - "$n" <<'PY' || exit 1
import sys
n = sys.argv[1]
rom = open("build/%s.nes" % n, "rb").read()
prg_len = rom[4] * 16384
prg = rom[16:16 + prg_len]
img = prg + b"\xff" * (512 * 1024 - len(prg))
open("build/%s_prg.bin" % n, "wb").write(img)
chk = open("build/%s_prg.bin" % n, "rb").read()
assert len(chk) == 512 * 1024 and chk[:prg_len] == prg
assert chk[:2] == b"\x00\xff", "bank 0 identity block missing (header included?)"
v = chk[prg_len - 6:prg_len]
reset = v[2] | v[3] << 8
assert 0xE000 <= reset <= 0xFFF9, "reset vector %04X outside the fixed bank" % reset
print("build/%s_prg.bin OK: %d bytes, reset vector $%04X" % (n, len(chk), reset))
PY
