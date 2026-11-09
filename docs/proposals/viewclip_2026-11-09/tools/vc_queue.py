"""viewclip jobs through the shared display queue (H:\\hzm_work\\DISPLAY_QUEUE.md): ONE run per turn, then yield.
For each job: append "viewclip HH:MM waiting" to display_queue.txt, wait until no openmohaa.exe runs AND our line is the
oldest waiting line (full-width = solo: no other client may run), remove our line, run the job (vc_go's run: one client), then go to the back of the queue again.
    python vc_queue.py <job> [<job> ...]        (jobs as vc_go.py; VC_SIDES / VC_MOVES / WV_RES pass through)
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
Q = os.path.join("H:" + os.sep, "hzm_work", "display_queue.txt")
ME = "viewclip"


def lines():
    try:
        return [l.rstrip("\n") for l in open(Q, encoding="utf-8") if l.strip()]
    except FileNotFoundError:
        return []


def write(ls):
    for _ in range(20):
        try:
            with open(Q, "w", encoding="utf-8", newline="\n") as f:
                f.write("".join(l + "\n" for l in ls))
            return
        except OSError:
            time.sleep(0.5)


def busy():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq openmohaa.exe"], capture_output=True, text=True).stdout
    return "openmohaa.exe" in out.lower()


def take_turn():
    if not any(l.startswith(ME + " ") for l in lines()):
        write(lines() + ["%s %s waiting solo (full-width 3440)" % (ME, time.strftime("%H:%M"))])
    while True:
        if not any(l.startswith(ME + " ") for l in lines()):     # another agent rewrote the file without our line: re-queue
            write(lines() + ["%s %s waiting solo (full-width 3440)" % (ME, time.strftime("%H:%M"))])
        ls = [l for l in lines() if " waiting" in l]           # incl. "waiting solo (...)" / "waiting (blocked ...)" lines
        if not busy() and ls and ls[0].startswith(ME + " "):
            write([l for l in lines() if not l.startswith(ME + " ")])
            return
        time.sleep(15)


def main(jobs):
    for j in jobs:
        take_turn()
        kind, rest = j.split(":", 1)
        if kind == "fs":                          # finishes2 in-game look test (fs2_ingame.py run <finish>)
            args = [os.path.join(HERE, "..", "..", "finishes2_2026-11-09", "tools", "fs2_ingame.py"), "run", rest]   # rest = <finish>[@<gun>]
        else:
            args = [os.path.join(HERE, "run_ab.py")] + rest.split(":")
        p = subprocess.run([sys.executable] + args, env=dict(os.environ, WV_DISPLAY_RES="3440x1440"), capture_output=True, text=True)
        for l in (p.stdout + p.stderr).splitlines():
            if "launched" in l or "VIOLATION" in l or " run " in l or "Error" in l or "Traceback" in l:
                print(l[:170], flush=True)
    print("vc_queue done", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "--jobs":          # one job per line (names with spaces)
        a = [l.strip() for l in open(a[1], encoding="utf-8") if l.strip()]
    main(a)
