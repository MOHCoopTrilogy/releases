#!/usr/bin/env python3
r"""Headless boot of a converted EA map on the PRIVATE G:\mohaa-ea dedicated server (no window, own home,
basepath = GOG read-only, port 12395). Reports load, Script Errors and navmesh lines. Stops only its own PID.
usage: ea_dedboot.py <map> [seconds] [k=v extra +set pairs ...] [--exec cfgname]"""
import collections, os, re, subprocess, sys, time

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-ea"
HOME = os.path.join(CLIENT, "dedhome")      # its own home: never the test client's (a held qconsole.log broke a queued run)
LOG = os.path.join(HOME, "maintt", "qconsole.log")

PATTERNS = ["Script Error", "ERROR", "Spawning Entities Done", "nav(mesh|igation)", "recast",
            r"\^~\^~\^", "couldn't", "WARNING"]


def boot(mapname, secs=90, extra=(), execs=()):
    if os.path.exists(LOG):
        os.remove(LOG)
    args = [os.path.join(CLIENT, "omohaaded.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "dedicated", "1", "+set", "fs_homepath", HOME, "+set", "net_port", "12395",
            "+set", "sv_maxclients", "4", "+set", "g_gametype", "2", "+set", "logfile", "2",
            "+set", "developer", "1", "+set", "com_abnormalExit", "0", "+set", "s_volume", "0"]
    for k, v in extra:
        args += ["+set", k, v]
    for e in execs:
        args += ["+exec", e]
    args += ["+set", "ui_dmmap", mapname, "+map", mapname]
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
    print("ded pid", p.pid, flush=True)
    t0 = time.time()
    try:
        while time.time() - t0 < secs and p.poll() is None:
            time.sleep(2)
    finally:
        if p.poll() is None:
            p.kill()          # our own PID only
    return p.poll(), (open(LOG, "rb").read().decode("latin-1") if os.path.exists(LOG) else "")


def report(txt):
    for pat in PATTERNS:
        hits = [ln for ln in txt.splitlines() if re.search(pat, ln, re.I)]
        print(f"--- {pat}: {len(hits)}")
        c = collections.Counter(re.sub(r"^\[[^\]]*\] ", "", h).strip()[:170] for h in hits)
        for h, n in c.most_common(8):
            print("   ", n, "x", h)


def main(argv):
    mapname = argv[1]
    secs = int(argv[2]) if len(argv) > 2 and argv[2].isdigit() else 90
    rest = argv[3:] if len(argv) > 2 and argv[2].isdigit() else argv[2:]
    execs = [rest[i + 1] for i, a in enumerate(rest) if a == "--exec"]
    extra = [a.split("=", 1) for a in rest if "=" in a]
    code, txt = boot(mapname, secs, extra, execs)
    print("exit", code, "log bytes", len(txt))
    report(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
