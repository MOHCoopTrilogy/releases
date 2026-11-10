#!/usr/bin/env python3
"""Display-queue waiter (H:\\hzm_work\\DISPLAY_QUEUE.md): appends our line, waits until it is the OLDEST waiting
line and enough client slots are free, marks it running, runs the given command, then removes the line.
Gives up (and removes the line) after --timeout minutes, so a dead waiter never blocks the queue.
usage: ea_queue_run.py --clients N --label TEXT [--solo] [--timeout MIN] -- <command ...>"""
import os
import subprocess
import sys
import time

Q = r"H:\hzm_work\display_queue.txt"


def running_clients():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq openmohaa.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return sum(1 for ln in out.splitlines() if "openmohaa" in ln.lower())


def lines():
    try:
        return [l.rstrip("\n") for l in open(Q, encoding="latin-1") if l.strip()]
    except OSError:
        return []


def write(ls):
    with open(Q, "w", encoding="latin-1", newline="\n") as f:
        f.write("".join(l + "\n" for l in ls))


def main(argv):
    i = argv.index("--")
    opts, cmd = argv[:i], argv[i + 1:]
    n = int(opts[opts.index("--clients") + 1])
    label = opts[opts.index("--label") + 1]
    solo = "--solo" in opts
    second = "--second" in opts      # the 1920x1080 second screen: its own single slot
    timeout = float(opts[opts.index("--timeout") + 1]) if "--timeout" in opts else 60
    me = "ea %s waiting%s (%s)" % (time.strftime("%H:%M"), " solo" if solo else (" second" if second else ""), label)
    write(lines() + [me])
    t0 = time.time()
    try:
        while True:
            ls = lines()
            if me not in ls:
                write(ls + [me])          # someone removed it while we were alive: re-add at the end
                ls = lines()
            waiting = [l for l in ls if " waiting" in l and ((" second" in l) == second)]
            up = running_clients()
            first = waiting and waiting[0] == me
            if second:
                free = not any(" running second" in l for l in ls if l != me) and up < 4
            else:
                free = (up == 0) if solo else (up + n <= 3)
            if any(" running solo" in l for l in ls if l != me):     # a solo run owns every screen (fps/timing)
                free = False
            if first and free:
                break
            if time.time() - t0 > timeout * 60:
                print("queue timeout", flush=True)
                return 3
            time.sleep(10)
        run = me.replace(" waiting", " running")
        write([run if l == me else l for l in lines()])
        me = run
        print("launching:", " ".join(cmd), flush=True)
        return subprocess.call(cmd)
    finally:
        write([l for l in lines() if l != me])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
