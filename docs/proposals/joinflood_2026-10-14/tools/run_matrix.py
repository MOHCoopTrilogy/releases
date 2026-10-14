"""run_matrix.py - the any-settings proof (joinflood stage 2): a pairwise-covering matrix of client frame/network
settings on the user's own config, two clients per run, lobby -> ready -> briefing -> m1l1. Every pair of values of
(com_maxfps 60/125/200/333, cl_maxpackets 30/60/100/125, cl_packetdup 0/1/2, rate 25000/90000, snaps 20/40) occurs in
at least one client; the last client is the user's real combination.

    python -I run_matrix.py <prefix> [--srv fix|rel] [--cl fix|rel] [--only N]
Writes <prefix>_matrix.tsv next to the runs in H:\\hzm_archive\\joinflood.
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
A = r"H:\hzm_archive\joinflood"
ROWS = """60,30,0,25000,20
60,60,1,90000,40
125,100,2,25000,40
200,125,2,90000,20
333,30,0,90000,40
333,60,1,25000,20
125,100,0,90000,20
200,125,0,25000,40
125,30,1,25000,20
200,100,1,25000,20
60,30,2,25000,20
60,125,1,25000,20
125,60,0,25000,20
200,60,2,25000,20
333,100,2,25000,20
60,100,0,25000,20
125,125,0,25000,20
200,30,0,25000,20
333,125,0,25000,20
200,100,1,90000,40""".split("\n")
SV = re.compile(r"\^~\^~\^ SVNET cl=(\d+) st=(\d+) .*? in=(\d+) infrag=(\d+) lastin=(-?\d+) ping=(-?\d+)")


def read(p):
    try:
        return open(p, "rb").read().decode("latin-1")
    except OSError:
        return ""


def judge(run, n, mx):
    srv = read(os.path.join(A, run, "srv", "maintt", "qconsole.log")) or read(os.path.join(A, run, "pc1", "maintt", "qconsole.log"))
    pc = read(os.path.join(A, run, "pc%d" % n, "maintt", "qconsole.log"))
    name = "JFTester%d" % n
    cl = n - 1
    entered = len(re.findall(r"%s has entered the battle" % name, srv))
    merged = len(re.findall(r"COOPSYNC merged cl=%d " % cl, srv)) > 0 and "upload timed out" not in srv
    m1l1 = "Server: m1l1" in pc
    active = silent = p100 = pmax = 0
    for m in SV.finditer(srv):
        if int(m.group(1)) != cl or int(m.group(2)) != 4:
            continue
        active += 1
        silent += int(m.group(5)) > 1000
        p = int(m.group(6))
        p100 += p > 100
        pmax = max(pmax, p)
    pk0 = len(re.findall(r"CLNET2 pk=0 ", pc))
    timeouts = len(re.findall(r"%s timed out" % name, srv))
    m1l1 = entered >= 3   # lobby, briefing, m1l1 (only the rcon-issuing client sees "Server: m1l1" in its own log)
    ok = entered >= 3 and merged and silent == 0 and timeouts == 0 and p100 <= 2
    return [run, str(n)] + mx + [str(entered), str(int(merged)), str(int(m1l1)), str(active), str(silent), str(p100),
                                  str(pmax), str(pk0), str(timeouts), "OK" if ok else "FAIL"]


def main():
    prefix = sys.argv[1]
    a = sys.argv[2:]
    srv = a[a.index("--srv") + 1] if "--srv" in a else "fix"
    cli = a[a.index("--cl") + 1] if "--cl" in a else "fix"
    only = int(a[a.index("--only") + 1]) if "--only" in a else None
    out = os.path.join(A, prefix + "_matrix.tsv")
    hdr = ["run", "client", "fps", "maxpackets", "packetdup", "rate", "snaps", "entered", "merged", "m1l1", "active_s",
           "silent_s", "ping>100_s", "ping_max", "client_pk0_s", "timeouts", "verdict"]
    if not os.path.isfile(out):
        open(out, "w").write("\t".join(hdr) + "\n")
    for k in range(0, len(ROWS), 2):
        if only is not None and k // 2 != only:
            continue
        run = "%s_m%02d" % (prefix, k // 2)
        grp = ";".join(ROWS[k:k + 2])
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "run_joinflood.py"), "run", run, "--srv", srv, "--cl", cli,
                        "--lobby", "stock", "--clients", "2", "--lobbysec", "100", "--missionsec", "100", "--usercfg",
                        "--clprobe2", "--mx", grp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(out, "a") as f:
            for n in (1, 2):
                row = judge(run, n, ROWS[k + n - 1].split(","))
                f.write("\t".join(row) + "\n")
                print("\t".join(row), flush=True)


if __name__ == "__main__":
    main()
