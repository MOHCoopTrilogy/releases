"""hudops.py - anchored edits for the HUD declutter build (docs/proposals/hud_declutter_2026-10-05).

    python hudops.py check            # every op matches exactly the expected number of times (working tree)
    python hudops.py apply            # apply to the working tree (skips ops already applied)
    python hudops.py stage            # stage ONLY these hunks: HEAD blob + ops -> index (other agents' edits stay unstaged)
    python hudops.py stage --dry      # show what would be staged

Ops live in ops_*.py as OPS = [(repo, relpath, old, new, count), ...]. `old` is literal text in which any run of
spaces/tabs matches [ \t]+ and every newline matches \r?\n, so CRLF/LF and indentation drift do not break it.
`new` is literal; its "\n" become the file's own line ending. An op whose `new` is already present (and `old` is
not) counts as applied. New files: (repo, relpath, None, <source path>, 0) copies the file.
"""
import os, re, sys, subprocess, glob, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
REPOS = {"mod": r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod", "eng": r"C:\mohaa-coop-dev\openmohaa-hzm"}


def load_ops():
    ops = []
    for f in sorted(glob.glob(os.path.join(HERE, "ops_*.py"))):
        spec = importlib.util.spec_from_file_location(os.path.basename(f)[:-3], f)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        ops += m.OPS
    return ops


def pat(old):
    out = []
    i = 0
    while i < len(old):
        ch = old[i]
        if ch == "\n":
            out.append(r"\r?\n")
        elif ch in " \t":
            j = i
            while j < len(old) and old[j] in " \t":
                j += 1
            out.append(r"[ \t]+")
            i = j
            continue
        else:
            out.append(re.escape(ch))
        i += 1
    return re.compile("".join(out))


def eol_of(txt):
    return "\r\n" if txt.count("\r\n") * 2 > txt.count("\n") else "\n"


def apply_text(txt, ops_for_file, path, strict=True):
    eol = eol_of(txt)
    msgs = []
    for (repo, rel, old, new, count) in ops_for_file:
        if old is None:
            continue
        p = pat(old)
        hits = p.findall(txt)
        newe = new.replace("\n", eol)
        insertion = bool(p.search(newe))   # new keeps old inside it: test "applied" first
        if insertion and pat(new).search(txt):
            msgs.append("already  %s: %s" % (rel, old.strip()[:60]))
        elif len(hits) == count:
            txt = p.sub(lambda m: newe, txt)
        elif not insertion and len(hits) == 0 and pat(new).search(txt):
            msgs.append("already  %s: %s" % (rel, old.strip()[:60]))
        else:
            msgs.append("MISMATCH %s: expected %d got %d: %s" % (rel, count, len(hits), old.strip()[:80]))
    return txt, msgs


def group(ops):
    g = {}
    for op in ops:
        g.setdefault((op[0], op[1]), []).append(op)
    return g


def read(path):
    with open(path, "rb") as f:
        return f.read().decode("latin-1")


def write(path, txt):
    with open(path, "wb") as f:
        f.write(txt.encode("latin-1"))


def cmd_check_apply(do_write):
    bad = 0
    for (repo, rel), lst in group(load_ops()).items():
        path = os.path.join(REPOS[repo], rel)
        if lst[0][2] is None:
            src = lst[0][3]
            if do_write and (not os.path.exists(path) or read(path) != read(src)):
                write(path, read(src))
                print("copied   %s" % rel)
            continue
        txt = read(path)
        new, msgs = apply_text(txt, lst, path)
        for m in msgs:
            print(m)
            bad += m.startswith("MISMATCH")
        if do_write and new != txt:
            write(path, new)
            print("wrote    %s (%d ops)" % (rel, len(lst)))
    print("mismatches:", bad)
    return bad


def git(repo, *a, inp=None):
    r = subprocess.run(["git", "-C", REPOS[repo]] + list(a), input=inp, capture_output=True)
    if r.returncode:
        raise RuntimeError("git %s: %s" % (a, r.stderr.decode("latin-1")))
    return r.stdout


def cmd_stage(dry):
    bad = 0
    for (repo, rel), lst in group(load_ops()).items():
        relg = rel.replace("\\", "/")
        if lst[0][2] is None:
            txt = read(lst[0][3])
        else:
            try:
                head = git(repo, "show", "HEAD:" + relg).decode("latin-1")
            except RuntimeError:
                print("NOT IN HEAD", rel)
                bad += 1
                continue
            txt, msgs = apply_text(head, lst, rel)
            for m in msgs:
                print("[HEAD] " + m)
                bad += 1
        if dry:
            print("would stage %s:%s" % (repo, rel))
            continue
        blob = git(repo, "hash-object", "-w", "--stdin", "--path", relg, inp=txt.encode("latin-1")).decode().strip()
        mode = "100644"
        try:
            ls = git(repo, "ls-files", "-s", "--", relg).decode().split()
            if ls:
                mode = ls[0]
        except RuntimeError:
            pass
        git(repo, "update-index", "--add", "--cacheinfo", "%s,%s,%s" % (mode, blob, relg))
        print("staged %s:%s" % (repo, rel))
    print("problems:", bad)
    return bad


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "check":
        sys.exit(1 if cmd_check_apply(False) else 0)
    if c == "apply":
        sys.exit(1 if cmd_check_apply(True) else 0)
    if c == "stage":
        sys.exit(1 if cmd_stage("--dry" in sys.argv) else 0)
