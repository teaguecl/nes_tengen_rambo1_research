#!/usr/bin/env python3
"""PIO engine self-test (no chip needed; drivers OFF): a pseudo-random stimulus that changes on every cycle is run at several clock dividers and the
captured read-back of the stimulus pins is compared with what was sent. Finds the lag between a word being output and being seen in the capture and
the fastest divider at which DMA keeps the PIO fed (no dropped or repeated words). Usage: python3 -I firmware/rp2350_jig/tools/selftest_pio.py"""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pio_host as H

def main():
    j = H.Jig()
    print(j.cmd("ver")[0])
    j.cmd("oe off")
    random.seed(1)
    n = 20000
    words = [H.IDLE] * 16
    prev = H.IDLE
    for _ in range(n):
        w = random.getrandbits(17)
        while w == prev or w == H.IDLE: w = random.getrandbits(17)
        words.append(w); prev = w
    words += [H.IDLE] * 16
    print("loading %d words ..." % len(words), j.load(words))
    for div in (1.0, 1.25, 1.5, 2.0, 3.0, 4.0):
        res = j.run(len(words) + 64, div)
        cap = j.dump()
        sent = words; got = H.stim_from_cap(cap)
        best = None
        for lag in range(0, 6):
            ok = sum(1 for i in range(32, len(sent) - 32) if got[i + lag] == sent[i])
            if best is None or ok > best[1]: best = (lag, ok)
        tot = len(sent) - 64
        print("div %-5g: %s" % (div, res))
        print("          read-back equals the word sent %d cycles earlier in %d of %d cycles (%.2f %%)" % (best[0], best[1], tot, 100.0 * best[1] / tot))
    j.cmd("idle")
main()
