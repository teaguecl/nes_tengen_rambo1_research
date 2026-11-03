#!/usr/bin/env python3
"""Report for experiments 11-14. Usage: tools/write_order_report.py results/NN_*.csv"""
import csv, re, sys

rows = [r for r in csv.reader(l for l in open(sys.argv[1]) if not l.startswith("#"))]
hdr = rows[0]
ix = {n: hdr.index(n) for n in hdr[5:]}
CHR = [f"CHR_A{n}" for n in range(10, 18)]
name = sys.argv[1].split("/")[-1]


def segments():
    seg = None
    for r in rows[1:]:
        if r[4] == "mark":
            seg = (r[2].split(" ", 1)[1], [])
            yield_ = seg
            segs.append(seg)
        elif seg is not None:
            seg[1].append(r)

segs = []
segments()
if "write_shapes" in name or "_14_" in name or name.startswith("14"):
    for label, rs in segs:
        samples = [r for r in rs if r[4] in ("ok", "sample") and r[ix["CIRAM_A10"]] != "" and
                   (r[2].startswith("wseq run") or "[sample" in r[2])]
        seq = "".join(r[ix["CIRAM_A10"]] for r in samples)
        flip = seq.find("1")
        print(f"{label:28} CIRAM per step: {seq}  " + (f"(flips at step {flip})" if flip >= 0 else "(never)"))
else:
    use_chr = name.startswith("13")
    print("pattern P0..P4 -> result")
    for label, rs in segs:
        last = [r for r in rs if r[ix["CIRAM_A10"]] != "" and r[2].startswith("wseq run")][-1]
        if use_chr:
            v = sum(int(last[ix[n]]) << i for i, n in enumerate(CHR))
            res = f"CHR byte {v:02X}"
        else:
            res = f"CIRAM_A10={last[ix['CIRAM_A10']]}"
        print(f"  {label[4:]:6} -> {res}")
