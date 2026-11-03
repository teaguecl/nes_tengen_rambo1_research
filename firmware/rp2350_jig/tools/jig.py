#!/usr/bin/env python3
"""Talk to the RAMBO-1 RP2350 jig over USB serial (no pyserial needed: plain termios, like tools/rambo_run.py).
Usage: python3 -I firmware/rp2350_jig/tools/jig.py [--port /dev/ttyACM0] [--wait S] "state" "power on" ...   (one reply per command)
       python3 -I firmware/rp2350_jig/tools/jig.py --port /dev/ttyACM0            (no commands: an interactive prompt)"""
import argparse, glob, os, select, sys, termios, time

def open_port(path):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
    a[4] = a[5] = termios.B115200
    a[6][termios.VMIN] = 0; a[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, a)
    return fd

def read_until_quiet(fd, quiet=0.25, total=5.0):
    out = b''; t0 = time.time(); last = time.time()
    while time.time() - t0 < total:
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            d = os.read(fd, 4096)
            if d: out += d; last = time.time()
        elif time.time() - last > quiet and out: break
    return out.decode(errors='replace')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--port'); ap.add_argument('--wait', type=float, default=0.25)
    ap.add_argument('cmds', nargs='*'); a = ap.parse_args()
    port = a.port or (sorted(glob.glob('/dev/ttyACM*')) or [None])[-1]
    if not port: sys.exit("no /dev/ttyACM* port: is the jig plugged in and running the firmware (not in BOOTSEL mode)?")
    fd = open_port(port)
    read_until_quiet(fd, 0.2, 1.0)                      # drain the banner
    if a.cmds:
        for c in a.cmds:
            os.write(fd, (c + '\n').encode())
            print(read_until_quiet(fd, a.wait).replace('\r', '').rstrip('> \n'))
    else:
        print("port", port, "- type commands, Ctrl-D to quit")
        for line in sys.stdin:
            os.write(fd, line.encode()); print(read_until_quiet(fd, a.wait).replace('\r', '').rstrip())
if __name__ == '__main__': main()
