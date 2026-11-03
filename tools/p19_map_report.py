#!/usr/bin/env python3
"""Reports for experiments 46-49. Usage: tools/p19_map_report.py results/NN_*.csv"""
import csv, re, sys
rows = [r for r in csv.reader(l for l in open(sys.argv[1]) if not l.startswith("#"))]
hdr = rows[0]; ix = {n: hdr.index(n) for n in hdr[5:]}
CHR = [f"CHR_A{n}" for n in range(10, 18)]; PRG = [f"PRG_A{n}" for n in range(13, 18)]
chrv = lambda r: sum(int(r[ix[n]]) << i for i, n in enumerate(CHR))
prgv = lambda r: sum(int(r[ix[n]]) << i for i, n in enumerate(PRG))
segs = []
for r in rows[1:]:
    if r[4] == "mark": segs.append((r[2][5:], [])); continue
    if segs and r[ix["IRQ_N"]] != "": segs[-1][1].append(r)
name = sys.argv[1].split("/")[-1]
if name.startswith("46"):
    res = {}
    for lab, rs in segs:
        S, T = [int(x, 16) for x in re.findall(r"=(\w+)", lab)]
        rr = [r for r in rs if r[2] == "r"]; rd = [r for r in rs if r[2].startswith("rd")]
        x, z, y = chrv(rr[0]), chrv(rr[1]), chrv(rr[2]); p = prgv(rd[0])
        inv = z == 0x50
        k = (x == 0xD0) if not inv else (y == 0xD0)
        res[(S, T)] = (int(inv) << 2 | (1 if p == 0x14 else 0) << 1 | int(k))
    print("rows: written-before S (bits 7,6,5), columns: T written with pin 19 high; cell = resulting bits 7,6,5")
    print("S\\T  " + "  ".join(f"{(((t>>2)&1)<<2|((t>>1)&1)<<1|(t&1)):03b}" for t in range(8)))
    for s in range(8):
        cells = []
        for t in range(8):
            sk, tk = (s & 7), (t & 7)
            r_ = res[(((s >> 2) & 1) << 7 | ((s >> 1) & 1) << 6 | (s & 1) << 5, ((t >> 2) & 1) << 7 | ((t >> 1) & 1) << 6 | (t & 1) << 5)]
            tag = "=T" if r_ == t else ("=S" if r_ == s else "??")
            cells.append(f"{r_:03b}{tag}")
        print(f"{s:03b}  " + " ".join(cells))
elif name.startswith("47"):
    tab = {}
    for lab, rs in segs:
        reg, V, W = re.match(r"reg=(\w+) V=(\w+) W=(\w+)", lab).groups()
        r = rs[-1]
        val = prgv(r) if reg == "R6" else (chrv(r) if reg != "A000" else int(r[ix["CIRAM_A10"]]))
        tab.setdefault(reg, {})[(V, W)] = val
    for reg, t in tab.items():
        Vs = sorted({v for v, _ in t}); Ws = sorted({w for _, w in t})
        print(f"{reg}: rows = start V, cols = written W, cell = result")
        print("  V\\W  " + "  ".join(Ws))
        for v in Vs: print(f"  {v}   " + "  ".join(f"{t[(v, w)]:02X}" for w in Ws))
elif name.startswith("48"):
    base_chr = [0x10, 0xD0, 0x30, 0xF0, 0x50, 0x70, 0x90, 0xB0]; base_prg = [0x05, 0x0A, 0x14, 0x1F]
    for lab, rs in segs:
        rr = [chrv(r) for r in rs if r[2] == "r"][-8:]; rd = [prgv(r) for r in rs if r[2].startswith("rd")][-4:]
        diff = [f"CHR[{i}]:{base_chr[i]:02X}->{rr[i]:02X}" for i in range(8) if rr[i] != base_chr[i]] + \
               [f"PRG[{i}]:{base_prg[i]:02X}->{rd[i]:02X}" for i in range(4) if rd[i] != base_prg[i]]
        print(f"{lab:16} " + ("; ".join(diff) if diff else "no change"))
elif name.startswith("49"):
    for lab, rs in segs:
        print(f"{lab}\n   IRQ_N: " + "".join(r[ix["IRQ_N"]] for r in rs if r[2] in ("r",)))
