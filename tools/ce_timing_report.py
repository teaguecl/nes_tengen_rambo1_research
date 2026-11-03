#!/usr/bin/env python3
"""Summarise a 09_ce_timing log: /CE per (target, predecessor), flagging path dependence, plus
whether any other output changed with the predecessor.
Usage: tools/ce_timing_report.py results/09_ce_timing_*.csv
"""
import csv, re, sys
rows = [r for r in csv.reader(l for l in open(sys.argv[1]) if not l.startswith("#"))]
hdr = rows[0]
sig = hdr[5:]
ce = hdr.index("PRG_CE_N")
res = {}                      # (pre, tgt) -> (ce, full row of signals)
cur = None
last_bus = None
for r in rows[1:]:
    if r[4] == "mark":
        m = re.match(r"mark pre=(\d+) target=(\d+)", r[2])
        cur = (m.group(1), m.group(2)); n = 0
    elif cur and r[2].startswith("bus "):
        n += 1
        if n == 2:
            res[cur] = (r[ce], tuple(r[5:]))
states = sorted({t for _, t in res})
print("target (M2 RW ROMSEL_N) | /CE by predecessor " + " ".join(states) + " | path-dependent?")
for t in states:
    ces = [res[(p, t)][0] for p in states]
    others = {res[(p, t)][1] for p in states}
    flag = "NO" if len(set(ces)) == 1 else "YES"
    other = "" if len(others) == 1 else "  (other outputs vary too)"
    print(f"        {t}             |  {'   '.join(ces)}  | {flag}{other}")
