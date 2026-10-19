#!/usr/bin/env python3
"""build_keep.py - build ONLY the gl2 renderer of the isolated keep tree and install it into the keep private client.

Never touches openmohaa-hzm, its .cmake, build.ps1, publish_release.ps1 or any fixed-name DLL (verified by hash).
  python build_keep.py <suffix> [--no-install] [--reglob] [--tree keep|live]
      builds openmohaa-hzm-keep (.cmake-keep) and installs G:\\mohaa-keeptest\\renderer_opengl2keep<suffix>.dll (+pdb)
      --tree live: the worktree openmohaa-hzm-live (.cmake-live): branch keep-v1103 = keep merged onto the v1.10.3
      candidate source; branch live = the live-graphics-settings work on top of it
Steps (renderer_reinit vet H16): regenerate+check the generated headers, stamp the commit, build the one target, fail
on errors and on C4013/C4047 outside the allow-list (bug-3036/3021: an implicit declaration truncates pointers on
x64), grep one literal per new source file out of the DLL (a new .c file needs a CMake re-glob, TRAPS T14e), record
SHA-256s in builds.json, verify the fixed-name DLLs did not change.
"""
import hashlib, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
TREES = {"keep": (r"C:\mohaa-coop-dev\openmohaa-hzm-keep", ".cmake-keep"),
         "live": (r"C:\mohaa-coop-dev\openmohaa-hzm-live", ".cmake-live")}
_tree = sys.argv[sys.argv.index("--tree") + 1] if "--tree" in sys.argv else "keep"
SRC = TREES[_tree][0]
BLD = os.path.join(SRC, TREES[_tree][1])
STAMP = os.path.join(SRC, r"code\renderergl2\tr_hzm_keepbuild.h")
PRIV = r"G:\mohaa-keeptest"
FIXED = [r"G:\mohaa-gl2\renderer_opengl2.dll", r"G:\mohaa-gl2\renderer_opengl2flip.dll",
         r"G:\GOG\Medal of Honor - Allied Assault War Chest\renderer_opengl2.dll",
         r"G:\mohaa-gfxtest\renderer_opengl2.dll", r"G:\mohaa-gfxtest\renderer_opengl2flip.dll"]
C4013_ALLOW = ("'R_VisDebugLoad'", "'TIKI_Reset_Caches'",
               # pre-existing in main (not keep code): tr_bsp.c firstmarksurface = marksurfaces + index,
               # tr_sprite.c model = tr.models - both in the main snapshot unchanged, statement-level, no truncation
               "tr_bsp.c(", "tr_sprite.c(")
# one literal that only exists if the file was compiled in (new files need the CMake re-glob)
MUST_CONTAIN = {"tr_hzm_keepprobe.c": b"RKEEPBUILD", "tr_hzm_keep.c": b"RKEEPASSERT",
                # included by tr_hzm_keep.c only when HZM_KEEP_FASTPATH is 1 (P2+): proves the fast path is built in
                "tr_hzm_keep_fast.h": b"RKEEPFAST",
                # live-graphics-settings work (branch live of openmohaa-hzm-live)
                "tr_hzm_live.c": b"LIVEAPPLY cvar="}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git(*a):
    return subprocess.run(["git", "-C", SRC] + list(a), capture_output=True, text=True).stdout.strip()


def find_out():
    for root, _, files in os.walk(BLD):
        if "renderer_opengl2.dll" in files and root.endswith("Release"):
            return os.path.join(root, "renderer_opengl2.dll")
    return None


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        raise SystemExit(__doc__)
    suffix = sys.argv[1]
    fixed_before = {p: sha(p) for p in FIXED if os.path.exists(p)}
    for gen in ("gen_rkeep_lists.py", "gen_tr_offsets.py"):
        r = subprocess.run([sys.executable, os.path.join(HERE, gen), "--engine", os.path.join(SRC, "code")],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("%s failed:\n%s%s" % (gen, r.stdout, r.stderr))
        print(r.stdout.strip().splitlines()[0])
    head = git("rev-parse", "--short", "HEAD")
    dirty = [l for l in git("status", "--porcelain", "--", "code").splitlines()
             if "tr_hzm_keepbuild.h" not in l]
    commit = head + ("-dirty" if dirty else "")
    date = time.strftime("%Y-%m-%dT%H:%M")
    orig = open(STAMP, "rb").read()
    stamped = orig.replace(b'#define HZM_KEEP_COMMIT "src"', ('#define HZM_KEEP_COMMIT "%s"' % commit).encode()) \
                  .replace(b'#define HZM_KEEP_DATE "unstamped"', ('#define HZM_KEEP_DATE "%s"' % date).encode())
    if stamped == orig:
        raise SystemExit("stamp placeholder not found in %s" % STAMP)
    open(STAMP, "wb").write(stamped)
    log = os.path.join(HERE, "builds", "build_%s_%s.log" % (suffix, time.strftime("%Y%m%d_%H%M%S")))
    os.makedirs(os.path.dirname(log), exist_ok=True)
    try:
        if "--reglob" in sys.argv:
            r = subprocess.run(["cmake", "."], cwd=BLD, capture_output=True, text=True)
            if r.returncode:
                raise SystemExit("cmake re-glob failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])
        # test DLLs carry the fault switches (r_hzmKeepFault); the source default is 0 so a ship build never does.
        # cl.exe honours the CL environment variable; every keep build sets it, so incremental builds stay consistent
        env = dict(os.environ)
        env["CL"] = (env.get("CL", "") + " /DHZM_KEEP_TESTHOOKS=1").strip()
        with open(log, "w") as lf:
            r = subprocess.run(["cmake", "--build", ".", "--config", "Release", "--target", "omohrenderergl2", "--",
                                "/m", "/v:minimal"], cwd=BLD, stdout=lf, stderr=subprocess.STDOUT, env=env)
    finally:
        open(STAMP, "wb").write(orig)
    txt = open(log, encoding="utf-8", errors="replace").read()
    errs = [l for l in txt.splitlines() if ": error" in l or "fatal error" in l or " error MSB" in l]
    warn = [l for l in txt.splitlines() if ("C4013" in l or "C4047" in l)
            and not any(a in l for a in C4013_ALLOW[:2])
            and not ("C4047" in l and any(a in l for a in C4013_ALLOW[2:]))]
    print("cmake exit", r.returncode, "| errors", len(errs), "| new C4013/C4047", len(warn), "| log", log)
    for l in (errs + warn)[:25]:
        print("  ", l.strip())
    if r.returncode or errs or warn:
        raise SystemExit("BUILD FAILED")
    out = find_out()
    data = open(out, "rb").read()
    missing = [f for f, lit in MUST_CONTAIN.items()
               if os.path.exists(os.path.join(SRC, "code", "renderergl2", f)) and lit not in data]
    if missing:
        raise SystemExit("literal from %s missing in the DLL - re-run with --reglob" % missing)
    if os.path.exists(os.path.join(SRC, "code", "renderergl2", "tr_hzm_keep.c")) and b"RKEEPFAULT bit=" not in data:
        raise SystemExit("the test hooks are not compiled in (HZM_KEEP_TESTHOOKS) - touch tr_hzm_keep.c and rebuild")
    if commit.encode() not in data:
        raise SystemExit("build stamp %s missing in the DLL" % commit)
    rec = {"suffix": suffix, "tree": _tree, "commit": commit, "date": date, "dll": out, "sha256": sha(out), "size": len(data)}
    if "--no-install" not in sys.argv:
        if not os.path.isdir(PRIV):
            raise SystemExit("%s missing - run rkeep_client.py setup first" % PRIV)
        dst = os.path.join(PRIV, "renderer_opengl2keep%s.dll" % suffix)
        shutil.copyfile(out, dst)
        pdb = out[:-4] + ".pdb"
        if os.path.exists(pdb):
            shutil.copyfile(pdb, dst[:-4] + ".pdb")
        rec["installed"] = dst
        rec["installed_sha256"] = sha(dst)
    fixed_after = {p: sha(p) for p in FIXED if os.path.exists(p)}
    rec["fixed_unchanged"] = fixed_before == fixed_after
    db = os.path.join(HERE, "builds", "builds.json")
    allrec = json.load(open(db)) if os.path.exists(db) else []
    allrec.append(rec)
    json.dump(allrec, open(db, "w"), indent=1)
    print(json.dumps(rec, indent=1))
    if not rec["fixed_unchanged"]:
        raise SystemExit("A FIXED-NAME DLL CHANGED DURING THE BUILD - investigate before anything else")


if __name__ == "__main__":
    main()
