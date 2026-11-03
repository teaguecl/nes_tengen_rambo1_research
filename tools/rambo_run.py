#!/usr/bin/env python3
"""Run a RAMBO jig experiment script against the Mega and log every step as CSV.

Usage: tools/rambo_run.py experiments/NAME.txt [--port /dev/ttyACM0] [--power cold|warm|unknown]
                          [--note TEXT] [--no-trace] [--out results]

Script lines (blank lines and text after '#' are ignored):
  <firmware command>        sent as-is (w, r, m, a, a12, ppu, d, c)
  expect SIG=V [SIG=V ...]  compare against the most recent output read; logs PASS/FAIL
  sleep MS                  wait on the host
  mark TEXT                 log a labelled row (to segment a long log for analysis)
  requires cold|warm        abort unless --power matches (the runner cannot power-cycle the cart)

After every command that is not a read, the runner issues 'r' (unless --no-trace) so each
row carries the full output word. Opening the serial port may reset the Mega (not always) but never power-cycles the cart,
so --power is a label you assert, not something measured. The firmware banner is best-effort
(it is often missed and logged as '').
Exit status is 1 if any expect failed.
"""
import argparse, csv, datetime, os, select, sys, termios, time

SIGNALS = ["PRG_A13", "PRG_A14", "PRG_A15", "PRG_A16", "PRG_A17", "PRG_CE_N",
           "CHR_A10", "CHR_A11", "CHR_A12", "CHR_A13", "CHR_A14", "CHR_A15",
           "CHR_A16", "CHR_A17", "CIRAM_A10", "IRQ_N"]


def open_port(path):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
    a = termios.tcgetattr(fd)
    a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
    a[4] = a[5] = termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    return fd


def read_quiet(fd, first_timeout, quiet=0.12):
    """Read until the line goes quiet for `quiet` seconds (or first_timeout with no data)."""
    out = b""
    deadline = time.time() + first_timeout
    while time.time() < deadline:
        if select.select([fd], [], [], 0.05)[0]:
            out += os.read(fd, 1024)
            deadline = time.time() + quiet
    return out.decode(errors="replace").strip()


def send(fd, cmd):
    termios.tcflush(fd, termios.TCIFLUSH)
    os.write(fd, (cmd + "\n").encode())
    return read_quiet(fd, 1.0)


def parse_all_outputs(reply):
    """Return a list of {signal: 0/1}, one per 'out,...' line (wseq runs return several)."""
    found = []
    for line in reply.splitlines():
        if line.startswith("out,"):
            f = dict(p.split("=") for p in line.split(",") if "=" in p)
            if all(s in f for s in SIGNALS):
                found.append({s: int(f[s]) for s in SIGNALS})
    return found


def parse_outputs(reply):
    """Return the first {signal: 0/1} from an 'out,...' line, or None."""
    found = parse_all_outputs(reply)
    return found[0] if found else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--power", choices=["cold", "warm", "unknown"], default="unknown")
    ap.add_argument("--note", default="")
    ap.add_argument("--no-trace", action="store_true")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()

    name = os.path.splitext(os.path.basename(args.script))[0]
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{name}_{stamp}.csv")

    fd = open_port(args.port)
    time.sleep(2.5)                       # Mega resets when the port opens
    banner = read_quiet(fd, 0.5)

    fails = 0
    last = None
    t0 = time.time()
    with open(path, "w", newline="") as f:
        for line in (f"# script={args.script}", f"# date={datetime.datetime.now().isoformat()}",
                     f"# power={args.power}", f"# note={args.note}", f"# firmware={banner!r}"):
            f.write(line + "\n")
        w = csv.writer(f)
        w.writerow(["t_s", "step", "command", "reply", "result"] + SIGNALS)

        def log(step, cmd, reply, result="", outs=None):
            row = [f"{time.time() - t0:.3f}", step, cmd, reply.replace("\n", " | "), result]
            row += [outs[s] for s in SIGNALS] if outs else [""] * len(SIGNALS)
            w.writerow(row)

        step = 0
        for raw in open(args.script):
            text = raw.split("#", 1)[0].strip()
            if not text:
                continue
            step += 1
            word, _, rest = text.partition(" ")
            if word == "requires":
                if args.power != rest.strip():
                    sys.exit(f"{args.script}: requires --power {rest.strip()} (got {args.power})")
                log(step, text, "", "ok")
            elif word == "mark":
                log(step, text, rest, "mark")
                print(f"----  {rest}")
            elif word == "sleep":
                time.sleep(int(rest) / 1000.0)
                log(step, text, "", "ok")
            elif word == "expect":
                if last is None:
                    log(step, text, "no output read yet", "FAIL"); fails += 1; continue
                bad = []
                for term in rest.split():
                    s, v = term.split("=")
                    if last.get(s) != int(v):
                        bad.append(f"{s}={last.get(s)}(want {v})")
                result = "FAIL" if bad else "PASS"
                fails += bool(bad)
                log(step, text, " ".join(bad), result, last)
                print(f"{result}  {text}" + (f"   <- {' '.join(bad)}" if bad else ""))
            else:
                reply = send(fd, text)
                all_outs = parse_all_outputs(reply)
                outs = all_outs[0] if all_outs else None
                if outs is None and not args.no_trace and word != "r":
                    outs = parse_outputs(send(fd, "r"))
                if outs:
                    last = all_outs[-1] if all_outs else outs
                result = "err" if reply.startswith("err") or not reply else "ok"
                log(step, text, reply, result, outs)
                for k, extra in enumerate(all_outs[1:], start=2):   # wseq samples 2..n
                    log(step, f"{text} [sample {k}]", "", "sample", extra)
                print(f"{result:4}  {text:20} {reply.splitlines()[0] if reply else ''}")

    os.close(fd)
    print(f"{'FAIL' if fails else 'done'}: {fails} expect failure(s); log -> {path}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
