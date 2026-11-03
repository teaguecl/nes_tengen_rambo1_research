#!/usr/bin/env python3
"""Report for experiments 16/17: events after enabling until IRQ_N first goes low, per latch value.
Usage: tools/irq_basic_report.py results/16_*.csv"""
import csv, re, sys
rows = [r for r in csv.reader(l for l in open(sys.argv[1]) if not l.startswith("#"))]
hdr = rows[0]; irq = hdr.index("IRQ_N")
segs = []
for r in rows[1:]:
    if r[4] == "mark":
        segs.append([r[2], []])
    elif segs:
        segs[-1][1].append(r)
for label, rs in segs:
    irq_after = {}          # IRQ_N right after each setup write
    events = []
    for r in rs:
        if r[irq] == "":
            continue
        if r[2].startswith("w "):
            irq_after[r[2]] = r[irq]
        elif r[2] == "r" or r[2].startswith(("m 1", "a 1")):
            events.append(r[irq])
    first = events.index("0") + 1 if "0" in events else None
    seq = "".join(events)
    print(f"{label:22} setup IRQ_N: " + " ".join(f"{k.split()[1]}={v}" for k, v in irq_after.items())
          + f" | first low after {first} event(s)" if first else
          f"{label:22} setup IRQ_N: " + " ".join(f"{k.split()[1]}={v}" for k, v in irq_after.items()) + " | never asserted")
    print("   IRQ_N per event: " + seq)
