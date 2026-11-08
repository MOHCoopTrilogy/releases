#!/usr/bin/env python3
"""gen_wpnfix_pak.py - zzzzzzzzzzzzzzzz_coop_wpnfix.pk3: weapon-file overrides that must out-sort EVERY other coop pak.

    python docs/tools/gen_wpnfix_pak.py build           # docs/tools/assets/wpnfix/** -> <mod>/zzzzzzzzzzzzzzzz_coop_wpnfix.pk3
    python docs/tools/gen_wpnfix_pak.py check           # exit 1: pak stale, or a pinned base (the copy we override) changed
    python docs/tools/gen_wpnfix_pak.py winner <rel>..  # every pak / tree that carries <rel>, in load order; the last one loads
    python docs/tools/gen_wpnfix_pak.py adopt <rel>..   # copy the CURRENT winning copy into the sources + pin it (then edit)

WHY (v1.10.64, wpnfix). A weapon .tik ships in up to six places - the mod tree (assets pak), the fixes pak (10 z), fixes2
(12 z), stress (13 z), late (14 z), scopeglass (15 z) - and the LAST-sorting one is what the game loads. The out-of-band
paks were assembled by hand in test copies and have no sources, so a fix made in the mod tree or the fixes pak can be
silently shadowed: bug-10526 (two invisible WW1 variants) was fixed in the mod tree on 2026-11-04 and v1.10.63 still
loaded the broken copies from scopeglass; bug-10532 (TT-33 SILENCED finishes) was fixed in the fixes pak under a stress
copy. This pak sorts after all of them (16 z), carries only the files changed here, and pins the md5 of the copy it
replaced, so `check` fails when someone changes that base (re-derive the override from the new base with `adopt`).

Load order rule (qcommon/files.cpp, see gen_fixes_pak.py): paks sorted by FS_PathCmp, the last-sorting pak wins; a
LOOSE file in maintt/ still beats every pak. Deterministic build: members in path order, ZIP_STORED, fixed timestamp.
"""
import hashlib
import io
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")                    # where the shipped out-of-band paks live
MOD = os.environ.get("HZM_MOD") or BASE_MOD                             # where build writes the pak
SRC = os.path.join(ROOT, "docs", "tools", "assets", "wpnfix")
MANIFEST = os.path.join(SRC, "wpnfix_manifest.json")
PAKNAME = "zzzzzzzzzzzzzzzz_coop_wpnfix.pk3"
STAMP = (2026, 11, 8, 0, 0, 0)


def pathcmp_key(s):
    return [ord("/") if c in "\\:" else ord(c.lower()) for c in s]


def carriers(rel, exclude_self=True):
    """[(where, bytes)] in load order: the loose mod tree (packed into zzzzzz_co-op_hzm_mod_*), then every later pak"""
    out = []
    p = os.path.join(BASE_MOD, *rel.split("/"))
    if os.path.isfile(p):
        out.append(("mod tree", open(p, "rb").read()))
    paks = sorted((f for f in os.listdir(BASE_MOD) if f.lower().endswith(".pk3")), key=pathcmp_key)
    for f in paks:
        if pathcmp_key(f) <= pathcmp_key("zzzzzz_co-op_hzm_mod_code.pk3") or (exclude_self and f == PAKNAME):
            continue
        try:
            with zipfile.ZipFile(os.path.join(BASE_MOD, f)) as z:
                for n in z.namelist():
                    if n.lower() == rel.lower():
                        out.append((f, z.read(n)))
        except zipfile.BadZipFile:
            pass
    return out


def load_manifest():
    return json.load(open(MANIFEST, encoding="utf-8")) if os.path.exists(MANIFEST) else {}


def members():
    out = []
    for dp, _dn, fn in os.walk(SRC):
        for f in fn:
            if f == "wpnfix_manifest.json":
                continue
            rel = os.path.relpath(os.path.join(dp, f), SRC).replace(os.sep, "/")
            out.append((rel, open(os.path.join(dp, f), "rb").read()))
    return sorted(out, key=lambda m: pathcmp_key(m[0]))


def render(mem):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for name, data in mem:
            zi = zipfile.ZipInfo(name, STAMP)
            zi.compress_type = zipfile.ZIP_STORED
            zi.external_attr = 0o644 << 16
            zi.create_system = 0
            z.writestr(zi, data)
    return buf.getvalue()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    man = load_manifest()
    if mode == "winner":
        for rel in sys.argv[2:]:
            c = carriers(rel, exclude_self=False)
            print("%-48s %s" % (rel, " < ".join(w for w, _ in c) + "   => " + c[-1][0] if c else "NOT SHIPPED"))
        return 0
    if mode == "adopt":
        for rel in sys.argv[2:]:
            c = carriers(rel)
            dst = os.path.join(SRC, *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if c:
                open(dst, "wb").write(c[-1][1])
                man[rel] = {"base": c[-1][0], "base_md5": hashlib.md5(c[-1][1]).hexdigest()}
            else:
                man[rel] = {"new": True}
            print("adopted", rel, man[rel])
        open(MANIFEST, "w", encoding="utf-8", newline="\n").write(json.dumps(man, indent=2, sort_keys=True) + "\n")
        return 0
    mem = members()
    fails = []
    if sorted(r for r, _ in mem) != sorted(man):
        fails.append("sources != manifest: %s" % sorted(set(r for r, _ in mem) ^ set(man)))
    for rel, data in mem:
        pin = man.get(rel, {})
        c = carriers(rel)
        if pin.get("new"):
            if c:
                fails.append("%s: pinned NEW but %s now carries it" % (rel, c[-1][0]))
        elif pin:
            if not c:
                fails.append("%s: its base %s is gone" % (rel, pin["base"]))
            elif hashlib.md5(c[-1][1]).hexdigest() != pin["base_md5"] or c[-1][0] != pin["base"]:
                fails.append("%s: the copy we override changed (%s) - re-derive with `adopt` and re-apply the fix" % (rel, c[-1][0]))
            elif c[-1][1] == data:
                fails.append("%s: override identical to its base - drop it" % rel)
    data = render(mem)
    pak = os.path.join(MOD, PAKNAME)
    if mode == "build":
        open(pak, "wb").write(data)
        print("wpnfix pak: %d members, sha256 %s" % (len(mem), hashlib.sha256(data).hexdigest()))
    else:
        if not os.path.exists(pak) or open(pak, "rb").read() != data:
            fails.append("%s is stale - run build" % PAKNAME)
    for f in fails:
        print("FAIL", f)
    if mode == "check":
        print("wpnfix pak: %d members, %s" % (len(mem), "OK" if not fails else "%d problem(s)" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
