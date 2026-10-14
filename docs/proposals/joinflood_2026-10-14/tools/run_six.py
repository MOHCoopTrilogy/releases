"""run_six.py - the stage-2 proof the user asked for (six runs; the extremes stand in for every setting between).
    python -I run_six.py <prefix> [--srv fix] [--cl fix] [--only k]
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_matrix import judge, A  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = [  # name, clients' fps,maxpackets,packetdup,rate,snaps, extra args
    ("1_user200", "200,100,1,90000,40", ["--usercfg"]),
    ("2_worst", "333,125,5,90000,40", ["--usercfg"]),
    ("3_light", "60,30,0,25000,20", ["--usercfg"]),
    ("4_pristine200", "200,100,1,90000,40", []),
    ("5_two200", "200,100,1,90000,40;200,100,1,90000,40", ["--usercfg", "--clients", "2"]),
    ("6_listen200", "200,100,1,90000,40;200,100,1,90000,40", ["--usercfg", "--clients", "2", "--listen"]),
]


def main():
    prefix = sys.argv[1]
    a = sys.argv[2:]
    srv = a[a.index("--srv") + 1] if "--srv" in a else "fix"
    cli = a[a.index("--cl") + 1] if "--cl" in a else "fix"
    only = a[a.index("--only") + 1] if "--only" in a else None
    out = os.path.join(A, prefix + "_six.tsv")
    for name, mx, extra in RUNS:
        if only and not name.startswith(only):
            continue
        run = "%s_%s" % (prefix, name)
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "run_joinflood.py"), "run", run, "--srv", srv, "--cl", cli,
                        "--lobby", "stock", "--lobbysec", "90", "--missionsec", "120", "--clprobe2", "--mx", mx] + extra,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for n in range(1, mx.count(";") + 2):
            row = judge(run, n, mx.split(";")[n - 1].split(","))
            with open(out, "a") as f:
                f.write("\t".join(row) + "\n")
            print("\t".join(row), flush=True)


if __name__ == "__main__":
    main()
