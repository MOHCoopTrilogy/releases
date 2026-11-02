"""Gate: every animation a coop player statemap names must exist in the anims_shared.txt that actually LOADS.

bug-10394 (v1.10.58-59): cover v3 added `coop_cover_wall_r` to anims_shared.txt, but three later-sorting paks
(zzzzzzzzzz_coop_fixes, zzzzzzzzzzzz_coop_fixes2, zzzzzzzzzzzzz_coop_stress) carry whole-file copies of
models/player/base/anims_shared.txt and the LAST one wins. The alias never loaded, the cover legs states
ping-ponged ("possible infinite state loop") and the server dropped every player who took cover on the right.

This resolves the winning copy the way the engine does - the mod tree's files go into the code / side paks,
then every *.pk3 in the mod root and the GOG maintt folder is ranked by file name - and checks every
`coop_*` anim on the left of a `:` in the coop statemaps against it.

    python docs/tools/check_anim_aliases.py          # exit 1 = a statemap anim is missing from the winning copy
"""
import glob
import os
import re
import sys
import zipfile

MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt"
ENTRY = "models/player/base/anims_shared.txt"
STATEMAPS = ["coop_mod/player_legs.st"]          # a missing LEGS anim state-loops and drops the player: blocking
WARN_STATEMAPS = ["coop_mod/player_torso.st"]    # torso misses only log "Can't find player animation": reported


def winning_copy():
    cands = {}
    # the mod tree's own file ships inside zzzzzz_co-op_hzm_mod_* paks (code / assets_tey) - rank it under that name
    tree = os.path.join(MOD, *ENTRY.split("/"))
    if os.path.exists(tree):
        cands["zzzzzz_co-op_hzm_mod_assets_tey.pk3"] = ("mod tree", open(tree, "rb").read())
    for d in (GOG, MOD):
        for p in glob.glob(os.path.join(d, "*.pk3")):
            name = os.path.basename(p)
            try:
                z = zipfile.ZipFile(p)
            except Exception:
                continue
            for e in z.namelist():
                if e.lower() == ENTRY:
                    # a pak in the mod root replaces the deployed one of the same name
                    if name not in cands or d == MOD:
                        cands[name] = (p, z.read(e))
    if not cands:
        return None, None
    win = sorted(cands)[-1]
    return win, cands[win][1].decode("latin-1")


def main():
    win, text = winning_copy()
    if text is None:
        print("check_anim_aliases: no anims_shared.txt found")
        return 1
    names = set()
    for sm in STATEMAPS:
        p = os.path.join(MOD, *sm.split("/"))
        if os.path.exists(p):
            names |= set(re.findall(r"^\s*(coop_[A-Za-z0-9_]+)\s*:", open(p, encoding="latin-1").read(), re.M))
    missing = sorted(n for n in names if not re.search(r"^\s*" + re.escape(n) + r"\s", text, re.M))
    warn = set()
    for sm in WARN_STATEMAPS:
        p = os.path.join(MOD, *sm.split("/"))
        if os.path.exists(p):
            warn |= set(re.findall(r"^\s*(coop_[A-Za-z0-9_]+)\s*:", open(p, encoding="latin-1").read(), re.M))
    wmiss = sorted(n for n in warn if not re.search(r"^\s*" + re.escape(n) + r"\s", text, re.M))
    if wmiss:
        print("warning - torso statemap anims missing (log spam, not a crash): " + ", ".join(wmiss))
    print("check_anim_aliases: %d coop statemap anims, winning anims_shared.txt = %s" % (len(names), win))
    if missing:
        print("MISSING from the copy that loads (the game will state-loop and drop the player):")
        for n in missing:
            print("   ", n)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
