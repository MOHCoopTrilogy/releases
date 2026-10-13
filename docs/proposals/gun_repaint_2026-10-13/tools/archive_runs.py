"""Move finished run folders G:/mohaa-hudfeed3/runs/rp_<prefix>* to H:/hzm_archive/repaint/<run>/ (one folder per
run), with a file-count check. Nothing is deleted: a run whose count does not match after the move is reported.

    python archive_runs.py <prefix>        e.g. rp_sil_
"""
import os, sys, shutil
SRC = "G:/mohaa-hudfeed3/runs"
DST = "H:/hzm_archive/repaint"


def count(d):
    return sum(len(fs) for _, _, fs in os.walk(d))


def main():
    pre = sys.argv[1]
    assert pre.startswith("rp_")
    os.makedirs(DST, exist_ok=True)
    for n in sorted(os.listdir(SRC)):
        s = os.path.join(SRC, n)
        if not (n.startswith(pre) and os.path.isdir(s)):
            continue
        d = os.path.join(DST, n)
        if os.path.exists(d):
            print("SKIP (already in the archive)", n); continue
        c0 = count(s)
        shutil.move(s, d)
        c1 = count(d)
        print("%-40s %3d files -> %s %s" % (n, c0, d, "OK" if c0 == c1 and not os.path.exists(s) else "MISMATCH %d" % c1))


if __name__ == "__main__":
    main()
