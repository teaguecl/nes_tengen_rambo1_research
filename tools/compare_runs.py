#!/usr/bin/env python3
"""Compare two experiment logs row by row: same command sequence, differing output signals.
Usage: tools/compare_runs.py A.csv B.csv [--ignore IRQ_N,...]
Prints the number of rows compared, rows with differing signals (with the signals), and any command mismatch.
"""
import csv, sys

def load(p):
    rows = [r for r in csv.reader(l for l in open(p) if not l.startswith("#"))]
    return rows[0], rows[1:]

ignore = set()
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if "--ignore" in sys.argv:
    ignore = set(sys.argv[sys.argv.index("--ignore") + 1].split(","))
    args = [a for a in args if a != sys.argv[sys.argv.index("--ignore") + 1]]
ha, ra = load(args[0]); hb, rb = load(args[1])
sig = [i for i, n in enumerate(ha) if i >= 5 and n not in ignore]
n = min(len(ra), len(rb))
cmd_bad = diff = 0
for i in range(n):
    if ra[i][2] != rb[i][2]:
        cmd_bad += 1
        if cmd_bad <= 3: print(f"row {i}: command mismatch {ra[i][2]!r} vs {rb[i][2]!r}")
        continue
    d = [f"{ha[j]}:{ra[i][j]}->{rb[i][j]}" for j in sig if ra[i][j] != rb[i][j]]
    if d:
        diff += 1
        if diff <= 15: print(f"row {i} {ra[i][2]!r}: " + " ".join(d))
print(f"compared {n} rows ({len(ra)} vs {len(rb)}); rows with signal differences: {diff}; command mismatches: {cmd_bad}")
