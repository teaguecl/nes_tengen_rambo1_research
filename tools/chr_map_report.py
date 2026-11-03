#!/usr/bin/env python3
"""Summarise a 05_chr_map log: for each pass, the CHR byte (A17..A10) per PPU A10-A12 combination
and which register value it matches (top 7 bits, so bit 0 differences still match).
Usage: tools/chr_map_report.py results/05_chr_map_*.csv
"""
import csv, re, sys

EVEN = {0: 0x10, 1: 0x30, 2: 0x50, 3: 0x70, 4: 0x90, 5: 0xB0, 8: 0xD0, 9: 0xF0}
CHR = [f"CHR_A{n}" for n in range(10, 18)]

rows = [r for r in csv.reader(l for l in open(sys.argv[1]) if not l.startswith("#"))]
hdr = rows[0]
col = {n: hdr.index(n) for n in CHR}
a12 = 0
vs = None
for r in rows[1:]:
    cmd = r[2]
    if r[4] == "mark":
        m = re.match(r"mark ctrl=(\w+) vals=(\w+)", cmd)
        ctrl, vs = m.group(1), m.group(2)
        print(f"\n== ctrl=${ctrl} (1KB mode={int(ctrl,16)>>5&1}, inversion={int(ctrl,16)>>7}) vals={vs}")
        print("A12 A11 A10 | CHR A17..A10 | matches")
        continue
    if cmd.startswith("a12 "):
        a12 = int(cmd.split()[1])
    elif vs and cmd.startswith("ppu ") and r[col["CHR_A10"]] != "":
        _, a10, a11 = cmd.split()
        byte = sum(int(r[col[n]]) << i for i, n in enumerate(CHR))
        want = {k: v | (1 if vs == "odd" else 0) for k, v in EVEN.items()}
        hit = [f"R{k}" for k, v in want.items() if byte >> 1 == v >> 1]
        extra = ""
        if hit and (byte & 1) != (want[int(hit[0][1:])] & 1):
            extra = f" (A10={byte & 1}, reg bit0={want[int(hit[0][1:])] & 1})"
        print(f" {a12}   {a11}   {a10}  |      {byte:02X}      | {','.join(hit) or '?'}{extra}")
