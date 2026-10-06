"""Out-of-band weapon HD paks (2026-10, user-approved full scope; docs/proposals/weapon_hd_2026-10-05).

    python docs/tools/weapon_hd/gen_weapon_hd_pak.py build 1low      pack C:/mohaa-weaponhd/build/stage/cls1 -> OUTBOX pak + manifest
    python docs/tools/weapon_hd/gen_weapon_hd_pak.py install 1low    after the class PASSED QA: copy the OUTBOX pak into the mod
                                                                      root (build.ps1 / publish_release.ps1 ship whatever is there)
    python docs/tools/weapon_hd/gen_weapon_hd_pak.py check           every pak present in the mod root matches its manifest
                                                                      (+ the wear pak's TIKs match a fresh regeneration)

PAKS (all in hzm-mohaa-coop-mod/, gitignored; copied by build.ps1, staged by publish_release.ps1):
  zzzzzzzzzz_coop_hd_wpn_1low.pk3   class 1 - sheets whose original art is <= 800 px (the xw imports, retail 512s)
  zzzzzzzzzz_coop_hd_wpn_2hd.pk3    class 2 - sheets with real >= 1024 art (HRRTM etc.) at 4096
  zzzzzzzzzz_coop_hd_wpn_3var.pk3   class 3 - skin-variant sheets (<= 2048)
  zzzzzzzzzz_coop_hd_wpn_4fin.pk3   baked finishes (bloody / camo) re-baked from the HD bases
  zzzzzzzzzz_coop_hd_wpn_5wear.pk3  per-instance wear: 2 extra 4096 rows per main sheet + generated TIK copies
WHY OUT OF BAND: the 1.3 GB assets_tex pak is reused by sha256 by the updater; anything under textures/ or models/
in the mod tree would re-hash it (gen_fixes_pak.py has the story). Each pak stays far below GitHub's 2 GB asset cap.
LOAD ORDER: ten z + `coop_hd_w` sorts after zzzzzzzzzz_coop_hd_m3l1a (the Omaha pak, which owns 14 weapon sheets
globally and is NOT modified), after _hd_a_tilefix / _hd_shadowfix / _hd_skies and after zzzzzzzzzz_coop_fixes, so
these .dds win; every member is a .dds at the stem the engine loads (R_LoadImage probes .dds first) - no shader or
.tik is overridden except the wear pak's generated TIKs.
DETERMINISTIC (the updater compares sha256): members sorted by FS_PathCmp order, fixed timestamp, DEFLATE level 6
(DXT1 of dark gun art deflates to ~0.6). The manifest (committed) pins every member's md5 + size, so `check` fails
on any drift and a rebuilt pak can be proven identical.
"""
import hashlib, json, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = r"C:/mohaa-weaponhd/build/stage"
OUTBOX = r"C:/mohaa-weaponhd/paks"     # built paks wait here until their class passes QA (coordinator rule, 2026-10-05)
PAKS = {"1low": "cls1", "2hd": "cls2", "3var": "cls3", "4fin": "fin", "5wear": "wear"}
STAMP = (2026, 10, 5, 0, 0, 0)


def pakname(k):
    return "zzzzzzzzzz_coop_hd_wpn_%s.pk3" % k


def key(s):
    return [ord("/") if c in "\\:" else ord(c.lower()) for c in s]


def manifest_path(k):
    return os.path.join(HERE, "manifest_%s.json" % k)


def build(k):
    src = os.path.join(BUILD, PAKS[k])
    members = []
    for dp, _d, fn in os.walk(src):
        for f in fn:
            members.append(os.path.relpath(os.path.join(dp, f), src).replace(os.sep, "/"))
    members.sort(key=key)
    assert members, "nothing staged in " + src
    man = {}
    os.makedirs(OUTBOX, exist_ok=True)
    out = os.path.join(OUTBOX, pakname(k))
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w") as z:
        for m in members:
            data = open(os.path.join(src, *m.split("/")), "rb").read()
            assert m.lower().endswith((".dds", ".tik", ".shader")), m
            zi = zipfile.ZipInfo(m, STAMP)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data, compresslevel=6)
            man[m] = {"md5": hashlib.md5(data).hexdigest(), "size": len(data)}
    os.replace(tmp, out)
    size = os.path.getsize(out)
    assert size < 1900 * 1024 * 1024, "pak over the GitHub 2 GB asset cap - split it"
    json.dump({"pak": pakname(k), "members": man, "pak_bytes": size,
               "pak_sha256": hashlib.sha256(open(out, "rb").read()).hexdigest()},
              open(manifest_path(k), "w"), indent=1, sort_keys=True)
    print("%s: %d members, %.1f MB" % (pakname(k), len(man), size / 1e6))


def check():
    bad = []
    for k in PAKS:
        p = os.path.join(MOD, pakname(k))
        mp = manifest_path(k)
        if not os.path.exists(mp):
            if os.path.exists(p):
                bad.append("%s has no manifest" % pakname(k))
            continue
        man = json.load(open(mp))
        if not os.path.exists(p):
            continue                    # built but not installed yet (awaiting QA) - nothing ships, nothing to check
        if hashlib.sha256(open(p, "rb").read()).hexdigest() != man["pak_sha256"]:
            z = zipfile.ZipFile(p)
            names = set(z.namelist())
            if names != set(man["members"]):
                bad.append("%s: members differ from manifest" % pakname(k))
            for m, info in man["members"].items():
                if m in names and hashlib.md5(z.read(m)).hexdigest() != info["md5"]:
                    bad.append("%s: %s md5 drift" % (pakname(k), m))
            bad.append("%s: sha256 differs from manifest" % pakname(k))
    if os.path.exists(manifest_path("5wear")):
        import gen_wear_tiks
        bad += gen_wear_tiks.check()
    for b in bad:
        print("WEAPON HD PAK CHECK:", b)
    print("weapon hd paks: %s" % ("OK" if not bad else "%d problem(s)" % len(bad)))
    return 1 if bad else 0


def install(k):
    import shutil
    src = os.path.join(OUTBOX, pakname(k))
    man = json.load(open(manifest_path(k)))
    assert hashlib.sha256(open(src, "rb").read()).hexdigest() == man["pak_sha256"], "outbox pak != manifest - rebuild"
    shutil.copyfile(src, os.path.join(MOD, pakname(k)))
    print("installed", pakname(k), "->", MOD)


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    if sys.argv[1] == "build":
        build(sys.argv[2])
    elif sys.argv[1] == "install":
        install(sys.argv[2])
    else:
        sys.exit(check())
