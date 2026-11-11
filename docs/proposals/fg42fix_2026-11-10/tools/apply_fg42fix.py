"""apply_fg42fix.py - bug-10899 hotfix, the pak half (the mod half is the fg42fix mod branch: anims_shared.txt merged).

The three out-of-band paks that sort after the mod's own pak lose their copy of models/player/base/anims_shared.txt, so
the mod tree's copy (repacked into zzzzzz_co-op_hzm_mod_assets_tey / code by build.ps1) is the one that loads. Every
other entry is copied byte-for-byte (strip_pak_entry.py). The paks are build inputs in the mod root (untracked, *.pk3
is gitignored), so this script is the record of the change.

    python apply_fg42fix.py                    dry run: what would change, the gate verdict with the staged paks
    python apply_fg42fix.py --apply [--base DIR]   back up to H:/hzm_work/fg42fix/bak, then replace the paks in DIR
                                                (default C:/mohaa-coop-dev/hzm-mohaa-coop-mod)
"""
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = r"H:\hzm_work\fg42fix\paks"
BAK = r"H:\hzm_work\fg42fix\bak"
PAKS = ["zzzzzzzzzz_coop_fixes.pk3", "zzzzzzzzzzzz_coop_fixes2.pk3", "zzzzzzzzzzzzz_coop_stress.pk3"]
ENTRY = "models/player/base/anims_shared.txt"


def arg(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


BASE = arg("--base", r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod")
TREE = arg("--tree", BASE)     # the mod tree whose anims_shared.txt the gate checks (the fg42fix worktree before merge)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def main():
    plan = []
    for p in PAKS:
        live, staged = os.path.join(BASE, p), os.path.join(STAGE, p)
        has = ENTRY in [n.lower() for n in zipfile.ZipFile(live).namelist()]
        if not has:
            print("%s: already without %s" % (p, ENTRY))
            continue
        # the staged pak must be the live one minus exactly that entry (the live pak may have moved on since staging)
        a = {i.filename: i.CRC for i in zipfile.ZipFile(live).infolist() if i.filename.lower() != ENTRY}
        b = {i.filename: i.CRC for i in zipfile.ZipFile(staged).infolist()}
        if a != b:
            print("%s: the live pak changed since staging - restage: strip_pak_entry.py %s %s" % (p, live, staged))
            return 1
        plan.append((live, staged))
        print("%s: drop %s (%s -> %s)" % (p, ENTRY, sha(live), sha(staged)))
    gate = [sys.executable, os.path.join(HERE, "..", "..", "..", "tools", "check_anim_aliases.py"), "--mod", TREE,
            "--pakdir", STAGE]
    r = subprocess.run(gate, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        print("gate fails with the staged paks - not applying (is the merged anims_shared.txt in %s?)" % BASE)
        return 1
    if "--apply" not in sys.argv:
        print("dry run - pass --apply")
        return 0
    os.makedirs(BAK, exist_ok=True)
    for live, staged in plan:
        shutil.copy2(live, os.path.join(BAK, os.path.basename(live)))
    for live, staged in plan:
        shutil.copy2(staged, live + ".new")
        os.replace(live + ".new", live)
        print("applied", live)
    return 0


if __name__ == "__main__":
    sys.exit(main())
