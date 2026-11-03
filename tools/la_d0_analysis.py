#!/usr/bin/env python3
"""Look at the data bus around the writes of a timing-probe phase 10/13/14/15/16/17 loop (finding F-073). Channels: CH1 M2, CH2 R/W, CH3 /ROMSEL, CH4 A0, CH5 A13, CH6 /IRQ, CH7 D0 (J2 pin 3).
For each block of $E000, $C001, $E001, $E000 it records, for each write cycle, D0 at the start of the window (the samples just after /ROMSEL falls), at the end (just before /ROMSEL rises), its
changes inside the window (time after /ROMSEL falls), and whether /IRQ was low during the block. Prints a summary by write kind and /IRQ outcome, and one example window trace per kind.
Usage: python3 -I tools/la_d0_analysis.py RATE_HZ FILE.sr [FILE.sr ...]"""
import sys, zipfile, collections, bisect

def load(f):
    z = zipfile.ZipFile(f)
    return b''.join(z.read(n) for n in sorted(z.namelist()) if n.startswith('logic'))

def edges(sig, rising=None):
    return [k for k in range(1, len(sig)) if sig[k] != sig[k-1] and (rising is None or bool(sig[k]) == rising)]

def main():
    rate = float(sys.argv[1]); T = 1e9 / rate
    summ = collections.defaultdict(collections.Counter); example = {}
    for f in sys.argv[2:]:
        d = load(f)
        m2 = [b & 1 for b in d]; rw = [b >> 1 & 1 for b in d]; ro = [b >> 2 & 1 for b in d]; a0 = [b >> 3 & 1 for b in d]; a13 = [b >> 4 & 1 for b in d]; irq = [b >> 5 & 1 for b in d]; d0 = [b >> 6 & 1 for b in d]
        r, fl = edges(m2, True), edges(m2, False)
        per = [r[i+1] - r[i] for i in range(len(r) - 1)]
        if not per or abs(sum(per) / len(per) * T - 558.9) > 15 or max(per) > 1.3 * sum(per) / len(per): continue
        rsf, rsr = edges(ro, False), edges(ro, True)
        KIND = {(0, 1): 'E000', (1, 0): 'C001', (1, 1): 'E001', (0, 0): 'C000'}
        wr = []
        for k in rsf:
            if rw[k] == 0 and k + 3 < len(d):
                j = bisect.bisect_right(rsr, k)
                if j < len(rsr): wr.append((k, rsr[j], KIND.get((a0[k+3], a13[k+3]), '?')))
        for i in range(len(wr) - 3):
            if [w[2] for w in wr[i:i+4]] != ['E000', 'C001', 'E001', 'E000']: continue
            lowirq = any(irq[k] == 0 for k in range(wr[i+1][0], wr[i+3][0]))
            out = 'IRQ low' if lowirq else 'IRQ high'
            for (s, e, kind) in wr[i:i+3]:
                start = d0[min(s + 1, len(d) - 1)]; end = d0[max(e - 1, 0)]
                ch = [round((k - s) * T) for k in range(s + 1, e) if d0[k] != d0[k-1]]
                summ[(kind, out)][("D0 start %d, end %d, changes at %s ns" % (start, end, ch))] += 1
                if (kind, out) not in example:
                    example[(kind, out)] = "".join(str(d0[k]) for k in range(s - 4, e + 6)) + "   (D0 per sample from 4 before /ROMSEL falls; ROMSEL low for %d samples)" % (e - s)
    for key in sorted(summ):
        print("%s write, %s:" % key)
        for k, c in summ[key].most_common(6): print("   %5d x  %s" % (c, k))
        print("   example D0:", example[key])
main()
