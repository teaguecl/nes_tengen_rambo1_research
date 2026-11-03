#!/usr/bin/env python3
"""Report for experiment 28: IRQ_N after each step of the cold counter test.
Usage: tools/cold_counter_report.py results/28_*.csv"""
import csv, sys
rows = [r for r in csv.reader(l for l in open(sys.argv[1]) if not l.startswith("#"))]
hdr = rows[0]; irq = hdr.index("IRQ_N")
t = p = 0; a12 = 0; stage = "stage 1 (asserted at power-on)"; last = None
log = []
for r in rows[1:]:
    c = r[2]
    if c.startswith("w E000"): stage = "after E000"
    if c.startswith("w E001"): stage = "after E001"
    if c.startswith("m 64") and stage == "after E001": stage = "A12 pulses after E001"
    if c.startswith("m "): t += int(c.split()[1])
    elif c.startswith("w "): t += 1
    elif c == "a12 1":
        if a12 == 0: p += 1
        a12 = 1
    elif c == "a12 0": a12 = 0
    if c == "r" or c.startswith("w E00"):
        v = r[irq]
        if v != "": log.append((stage, t, p, v))
for st in dict.fromkeys(x[0] for x in log):
    vals = [x for x in log if x[0] == st]
    print(f"{st:34} IRQ_N seq: {''.join(x[3] for x in vals)}   (t={vals[0][1]}..{vals[-1][1]}, pulses={vals[0][2]}..{vals[-1][2]})")
