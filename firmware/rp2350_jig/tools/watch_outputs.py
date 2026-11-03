#!/usr/bin/env python3
"""Watch the chip-output lines and log every change (bring-up step 9: touch J2 pin 1 (5 V) to each output pin in turn).
Usage: python3 -I firmware/rp2350_jig/tools/watch_outputs.py SECONDS [--port /dev/ttyACM0]"""
import os, re, sys, time, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jig

def read_outputs(fd):
    os.write(fd, b'state\n')
    txt = jig.read_until_quiet(fd, 0.15, 2.0)
    out = {}
    for m in re.finditer(r'^\s+(\w+)\s+GPIO(\d+)\s+J2-(\d+)\s+=\s+([01])', txt, re.M):
        out[(m.group(1), int(m.group(3)))] = int(m.group(4))
    return {k: v for k, v in out.items() if k[1] >= 23 and k[0] not in ('D0','D1','D2','D3','D4','D5','D6','D7','M2','RW','ROMSEL','A0','A13','A14','PPUA10','PPUA11','PPUA12')}

def main():
    secs = float(sys.argv[1]); port = (sys.argv[sys.argv.index('--port') + 1] if '--port' in sys.argv else sorted(glob.glob('/dev/ttyACM*'))[-1])
    fd = jig.open_port(port); jig.read_until_quiet(fd, 0.2, 1.0)
    prev = None; seen_high = set(); t0 = time.time(); order = []
    while time.time() - t0 < secs:
        cur = read_outputs(fd)
        if prev is not None and cur != prev:
            for k in sorted(cur, key=lambda k: k[1]):
                if cur[k] != prev.get(k):
                    print("%6.1f s  J2-%-2d %-7s -> %d" % (time.time() - t0, k[1], k[0], cur[k]), flush=True)
                    if cur[k]: seen_high.add(k); order.append(k)
        prev = cur
        time.sleep(0.05)
    allk = sorted(prev, key=lambda k: k[1]) if prev else []
    print("\nseen going high: " + (" ".join("J2-%d(%s)" % (k[1], k[0]) for k in sorted(seen_high, key=lambda k: k[1])) or "none"))
    print("never went high: " + (" ".join("J2-%d(%s)" % (k[1], k[0]) for k in allk if k not in seen_high) or "none"))
if __name__ == '__main__': main()
