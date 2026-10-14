"""analyze_run.py - the numbers of one archived joinflood run (H:\\hzm_archive\\joinflood\\<run>), per map.

    python -I analyze_run.py <run> [<run to compare the client's challenge/Armory UI cvars with>]

Per server map segment and client: seconds active, max reliable commands in flight, max parked, max waiting
(in flight + parked), largest snapshot, seconds in which a client packet arrived only as a fragment (the client
exe stall), seconds with no client packet for > 1 s while active (what the player sees as the connection icon),
timeouts, progression merge lines. With a second run: the client's archived challenge / Armory UI cvars
(coop_ui*, coop_loLk*, coop_loCmt*, coop_pin*) compared value by value.
"""
import os, re, sys

A = r"H:\hzm_archive\joinflood"
SV = re.compile(r"\[2026-\d\d-\d\d ([\d:]+)[^\]]*\] \^~\^~\^ SVNET cl=(\d+) st=(\d+) inflight=(\d+) max=(\d+) parked=(\d+) "
                r"max=(\d+) snaps=(\d+) avg=(\d+) max=(\d+) over1300=(\d+) skipfrag=(\d+) skiprate=(\d+) in=(\d+) "
                r"infrag=(\d+) lastin=(-?\d+) ping=(-?\d+)")


def read(p):
    try:
        return open(p, "rb").read().decode("latin-1")
    except OSError:
        return ""


def ui_cvars(run, pc="pc1"):
    cfg = read(os.path.join(A, run, pc, "maintt", "configs", "omconfig.cfg"))
    return dict(re.findall(r'(?m)^seta (coop_ui[A-Z]\d+|coop_loLk[A-Za-z]*\d+|coop_loCmt\d+|coop_loFcmtA\d+|coop_pinCount) "([^"]*)"', cfg))


def main():
    run = sys.argv[1]
    log = read(os.path.join(A, run, "srv", "maintt", "qconsole.log"))
    if not log:  # listen host: the host's own log
        log = read(os.path.join(A, run, "pc1", "maintt", "qconsole.log"))
    segs = re.split(r"(?=\[[^\]]*\] (?:Server: |Rcon from ))", log)  # an rcon map prints no Server: line
    for seg in segs:
        m = re.match(r"\[[^\]]*\] (?:Server: (\S+)|Rcon from (\S+))", seg)
        name = (m.group(1) or "(rcon map from %s)" % m.group(2)) if m else "(start)"
        per = {}
        for r in SV.finditer(seg):
            cl, st = int(r.group(2)), int(r.group(3))
            d = per.setdefault(cl, dict(active=0, inflight=0, parked=0, waiting=0, snap=0, fragsecs=0, silent=0, pingmax=0, ping100=0))
            if st != 4:
                continue
            d["active"] += 1
            d["inflight"] = max(d["inflight"], int(r.group(5)))
            d["parked"] = max(d["parked"], int(r.group(7)))
            d["waiting"] = max(d["waiting"], int(r.group(4)) + int(r.group(6)))
            d["snap"] = max(d["snap"], int(r.group(10)))
            d["fragsecs"] += int(r.group(15)) > 0 and int(r.group(14)) < 10
            d["silent"] += int(r.group(16)) > 1000
            d["pingmax"] = max(d["pingmax"], int(r.group(17)))
            d["ping100"] += int(r.group(17)) > 100
        if not per and not m:
            continue
        print("== %s" % name)
        for cl, d in sorted(per.items()):
            print("   cl=%d active %ds | in flight max %d | parked max %d | snapshot max %d B | client-fragment-only s %d"
                  " | no client packet >1 s: %d s | ping max %d ms, %d s over 100 ms" % (cl, d["active"], d["inflight"], d["parked"],
                  d["snap"], d["fragsecs"], d["silent"], d["pingmax"], d["ping100"]))
        for ev in re.findall(r"[^\r\n]*(?:COOPSYNC (?:merged|upload timed out|want)|timed out|Server command overflow|"
                             r"Script Error|has entered the battle)[^\r\n]*", seg)[:12]:
            print("   ", re.sub(r"^\[\d{4}-\d\d-\d\d ([\d:]+)[^\]]*\]", r"\1", ev.strip())[:180])
    if len(sys.argv) > 2:
        a, b = ui_cvars(run), ui_cvars(sys.argv[2])
        keys = sorted(set(a) | set(b))
        diff = [k for k in keys if a.get(k) != b.get(k)]
        print("UI cvars: %s has %d, %s has %d, differing %d %s" % (run, len(a), sys.argv[2], len(b), len(diff), diff[:10]))


if __name__ == "__main__":
    main()
