#!/usr/bin/env python3
"""Report for experiments 34-37: fingerprint differences against segment 'none'.
Usage: tools/decode_report.py results/NN_*.csv"""
import csv, sys
rows = [r for r in csv.reader(l for l in open(sys.argv[1]) if not l.startswith("#"))]
hdr = rows[0]
CHR = [hdr.index(f"CHR_A{n}") for n in range(10, 18)]
PRG = [hdr.index(f"PRG_A{n}") for n in range(13, 18)]
CIR = hdr.index("CIRAM_A10")
names_chr = [f"CHR[a12={a12} a11={a11} a10={a10}]" for a12 in (0, 1) for a11 in (0, 1) for a10 in (0, 1)]
names_prg = [f"PRG[{w}]" for w in ("8000", "A000", "C000", "E000")]
names_cir = [f"CIRAM[a11={a11} a10={a10}]" for a11 in (0, 1) for a10 in (0, 1)]
segs = []
for r in rows[1:]:
    if r[4] == "mark":
        segs.append([r[2][5:], [], [], []]); continue
    if not segs or r[CIR] == "":
        continue
    sg = segs[-1]
    c = r[2]
    if c == "r":
        sg[1].append(sum(int(r[x]) << i for i, x in enumerate(CHR)))
        sg[3].append(int(r[CIR]))
    elif c.startswith("rd "):
        sg[2].append(sum(int(r[x]) << i for i, x in enumerate(PRG)))
def vec(sg):
    chrv, prgv, cirv = sg[1][-8:], sg[2][-4:], sg[3][-8:]
    cir = [cirv[0], cirv[1], cirv[2], cirv[3]]                       # a12=0 combos: a11,a10
    return dict(zip(names_chr, chrv)) | dict(zip(names_prg, prgv)) | dict(zip(names_cir, cir))
base = vec(segs[0])
print("baseline:", " ".join(f"{k.split('[')[1][:-1]}={v:02X}" for k, v in base.items() if k.startswith("CHR")),
      "|", " ".join(f"{k}={v:02X}" for k, v in base.items() if k.startswith("PRG")))
for sg in segs[1:]:
    v = vec(sg)
    diff = [f"{k}: {base[k]:02X}->{v[k]:02X}" for k in v if v[k] != base[k]]
    print(f"{sg[0]:20} " + ("; ".join(diff) if diff else "no change from baseline"))
