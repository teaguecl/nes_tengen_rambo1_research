#!/usr/bin/env python3
"""Report for experiments 22-25. Tracks M2 cycles (t) and A12 pulses (p) since the last $C001 write and
lists every point where IRQ_N goes low. Usage: tools/irq_reload_report.py results/NN_*.csv"""
import csv, re, sys
rows = [r for r in csv.reader(l for l in open(sys.argv[1]) if not l.startswith("#"))]
hdr = rows[0]; irq = hdr.index("IRQ_N")
seg = None
def flush():
    if seg: print(f"{seg[0]:36} " + ("; ".join(seg[1]) if seg[1] else "IRQ never went low") + f"   [IRQ after $C001 write: {seg[2]}]")
t = p = 0; a12 = 0; prev = None; first_after_c001 = None
for r in rows[1:]:
    cmd = r[2]
    if r[4] == "mark":
        flush(); seg = [r[2][5:], [], "?"]; t = p = 0; a12 = 0; prev = None; continue
    if seg is None: continue
    m = re.match(r"w (\w+) (\w+)", cmd)
    if m:
        if m.group(1) == "C001":
            t = p = 0; first_after_c001 = True
        else: t += 1
    elif cmd.startswith("m "): t += int(cmd.split()[1])
    elif cmd == "a12 1":
        if a12 == 0: p += 1
        a12 = 1
    elif cmd == "a12 0": a12 = 0
    elif cmd == "r" and r[irq] != "":
        v = r[irq]
        if first_after_c001:
            seg[2] = v; first_after_c001 = False
        if prev == "1" and v == "0": seg[1].append(f"low at t={t} p={p}")
        if prev == "0" and v == "1": seg[1].append(f"high at t={t} p={p}")
        prev = v
flush()
