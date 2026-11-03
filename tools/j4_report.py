#!/usr/bin/env python3
"""Report for experiment 59 (J4). Per switch time: IRQ_N samples as a string (0 = asserted).
Sample order: [pre-switch] [after switch] [+2] [+10] [+30] [+50] | after $E000 | after $E001 | pulses 1..8.
Usage: tools/j4_report.py results/59_*.csv"""
import csv, re, sys
rows = [r for r in csv.reader(l for l in open(sys.argv[1]) if not l.startswith("#"))]
hdr = rows[0]; irq = hdr.index("IRQ_N")
seg = None
print("switch-t  pre sw +2 +10 +30 +50 | ack enb | pulses 1-8")
def flush():
    if not seg: return
    s = seg[1]
    g = lambda a, b: "".join(s[a:b])
    print(f"{seg[0]:>8}  {g(0,1)}   {g(1,2)}  {g(2,3)}  {g(3,4)}   {g(4,5)}   {g(5,6)}  |  {g(6,7)}   {g(7,8)}  | {g(8,16)}" + ("" if len(s) >= 16 else "   (incomplete)"))
for r in rows[1:]:
    if r[4] == "mark":
        flush(); m = re.search(r"at t=(\d+)", r[2]); seg = [m.group(1), []]; continue
    if seg is not None and r[2] == "r" and r[irq] != "": seg[1].append(r[irq])
flush()
