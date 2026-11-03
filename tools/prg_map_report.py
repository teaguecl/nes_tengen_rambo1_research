#!/usr/bin/env python3
"""Summarise a 07_prg_map log: PRG bank number (A17..A13) and /CE per read address, plus which
register value it matches (low 5 bits), or 'fixed' for the all-ones last bank.
Usage: tools/prg_map_report.py results/07_prg_map_*.csv
"""
import csv, re, sys

VALS = {"lo": {"R6": 0x05, "R7": 0x0A, "RF": 0x14}, "hi": {"R6": 0x25, "R7": 0x4A, "RF": 0x94}}
PRG = [f"PRG_A{n}" for n in range(13, 18)]

rows = [r for r in csv.reader(l for l in open(sys.argv[1]) if not l.startswith("#"))]
hdr = rows[0]
col = {n: hdr.index(n) for n in PRG + ["PRG_CE_N"]}
vs = None
for r in rows[1:]:
    cmd = r[2]
    if r[4] == "mark":
        m = re.match(r"mark ctrl=(\w+) vals=(\w+)", cmd)
        ctrl, vs = m.group(1), m.group(2)
        print(f"\n== ctrl=${ctrl} (PRG mode bit 6 = {int(ctrl,16)>>6&1}) vals={vs}  "
              + " ".join(f"{k}={v:02X}" for k, v in VALS[vs].items()))
        print("read  | bank A17..A13 | /CE | matches")
    elif vs and cmd.startswith("rd ") and r[col["PRG_A13"]] != "":
        bank = sum(int(r[col[n]]) << i for i, n in enumerate(PRG))
        hit = [k for k, v in VALS[vs].items() if v & 0x1F == bank]
        if bank == 0x1F and not hit:
            hit = ["fixed(last)"]
        print(f"{cmd[3:]:5} |      {bank:02X}       |  {r[col['PRG_CE_N']]}  | {','.join(hit) or '?'}")
