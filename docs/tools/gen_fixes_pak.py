"""gen_fixes_pak.py - small OVERRIDES pak for asset-bucket files changed after a release (v1.10.4, bug-3251).

    python docs/tools/gen_fixes_pak.py build     # write hzm-mohaa-coop-mod/zzzzzzzzzz_coop_fixes.pk3
    python docs/tools/gen_fixes_pak.py check     # exit 1 on any drift (pak, pinned bases, sources)
    python docs/tools/gen_fixes_pak.py restore   # put every pinned base back in the mod tree (bytes AND mtime)

WHY. build.ps1 packs every file under models/ textures/ gfx/ env/ into zzzzzz_co-op_hzm_mod_assets_tex.pk3 (~1.3 GB),
keyed by an input digest of relpath|size|mtime-ticks, and the auto-updater reuses paks by sha256. ONE changed .tik
there (models/human/new_generic_human.tik, bug-3196) re-hashed the whole pak = a 1.3 GB re-download for every player.
So the mod tree keeps the RELEASED copy of such a file (same bytes, same mtime ticks -> the tex bucket stays a cache
hit), and the fixed copy ships here, from docs/tools/assets/fixes/<same relpath>.

LOAD ORDER (qcommon/files.cpp FS_AddGameDirectory2): paks in a dir are sorted by FS_PathCmp (case-insensitive byte
order) and each is PREPENDED to the search path, so the last-sorted pak wins; `zzzzzzzzzz_coop_fixes` (ten z) sorts
after `zzzzzz_co-op_hzm_mod_*` (six z), so its copy overrides the assets_tex copy. `original_paks_priority` is never
true (FS_AddGameDirectory passes false). A LOOSE file in maintt/ would still beat it (loose dir added after its paks).

⚠ TRAP THIS CREATES: the mod tree's copy of an overridden file is NOT what the game loads. Edit the copy under
docs/tools/assets/fixes/, never the mod tree - `check` fails if a pinned base changed (bytes or mtime), so an edit in
the wrong place cannot ship silently. Tools that read the mod tree (check_anim_rootless, audits) see the base copy.
When a release ships a NEW assets_tex pak anyway, fold the fixes back into the mod tree and empty this pak.

Pins: docs/tools/assets/fixes/fixes_manifest.json = {relpath: {"base_md5", "base_ticks", "base_from"}}.
Deterministic: members sorted, ZIP_STORED, fixed timestamp.
"""
import hashlib, io, json, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "docs", "tools", "assets", "fixes")
MANIFEST = os.path.join(SRC, "fixes_manifest.json")
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
PAKNAME = "zzzzzzzzzz_coop_fixes.pk3"
PAK = os.path.join(MOD, PAKNAME)
STAMP = (2026, 9, 28, 0, 0, 0)
GOG_MAINTT = r"G:/GOG/Medal of Honor - Allied Assault War Chest/maintt"
EPOCH_TICKS = 621355968000000000   # .NET ticks at 1970-01-01T00:00:00Z


def pathcmp_key(s):
    return [ord("/") if c in "\\:" else ord(c.lower()) for c in s]


def load():
    man = json.load(open(MANIFEST, encoding="utf-8"))
    fails, members = [], []
    on_disk = []
    for dp, _dn, fn in os.walk(SRC):
        for f in fn:
            if f == "fixes_manifest.json":
                continue
            on_disk.append(os.path.relpath(os.path.join(dp, f), SRC).replace(os.sep, "/"))
    if sorted(on_disk) != sorted(man):
        fails.append("sources %s != manifest %s" % (sorted(on_disk), sorted(man)))
    for rel in sorted(man):
        data = open(os.path.join(SRC, *rel.split("/")), "rb").read()
        if "base_pak" in man[rel]:
            # [2026-10-06, bug-3453] base is a member of a THIRD-PARTY pak (never edited in place, no mod-tree copy):
            # pin it by md5 against that pak in the GOG maintt when it is there; the override just has to out-sort it.
            bp = os.path.join(GOG_MAINTT, man[rel]["base_pak"])
            if os.path.isfile(bp):
                with zipfile.ZipFile(bp) as z:
                    names = {n.lower(): n for n in z.namelist()}
                    if rel.lower() not in names:
                        fails.append("%s: not in its base pak %s" % (rel, man[rel]["base_pak"]))
                    elif hashlib.md5(z.read(names[rel.lower()])).hexdigest() != man[rel]["base_md5"]:
                        fails.append("%s: base pak member changed (re-derive the override)" % rel)
            if not pathcmp_key(PAKNAME) > pathcmp_key(man[rel]["base_pak"]):
                fails.append("%s does not sort after %s" % (PAKNAME, man[rel]["base_pak"]))
            members.append((rel, data))
            continue
        base = os.path.join(MOD, *rel.split("/"))
        if not os.path.isfile(base):
            fails.append("%s: no base copy in the mod tree" % rel)
        else:
            b = open(base, "rb").read()
            if hashlib.md5(b).hexdigest() != man[rel]["base_md5"]:
                fails.append("%s: the MOD-TREE copy changed (md5 %s, pinned %s) - edit docs/tools/assets/fixes/%s "
                             "instead, then `restore`" % (rel, hashlib.md5(b).hexdigest(), man[rel]["base_md5"], rel))
            ticks = os.stat(base).st_mtime_ns // 100 + EPOCH_TICKS
            if ticks != man[rel]["base_ticks"]:
                fails.append("%s: mod-tree mtime ticks %d != pinned %d - the assets_tex bucket would re-hash; run "
                             "`restore`" % (rel, ticks, man[rel]["base_ticks"]))
        if data == (open(base, "rb").read() if os.path.isfile(base) else None):
            fails.append("%s: override identical to its base - drop it from the pak" % rel)
        if rel.lower().endswith((".tik", ".shader", ".txt", ".scr")):
            crlf, lf = data.count(b"\r\n"), data.count(b"\n")
            if crlf and crlf != lf:
                fails.append("%s: mixed line endings (%d CRLF / %d LF)" % (rel, crlf, lf))
        members.append((rel, data))
    # it must sort after every coop pak it overrides
    for other in ("zzzzzz_co-op_hzm_mod_assets_tex.pk3", "zzzzzz_co-op_hzm_mod_code.pk3", "zzzzzz_co-op_hzm_mod_assets_snd.pk3"):
        if not pathcmp_key(PAKNAME) > pathcmp_key(other):
            fails.append("%s does not sort after %s" % (PAKNAME, other))
    return man, members, fails


def render(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for name, data in members:
            zi = zipfile.ZipInfo(name, STAMP)
            zi.compress_type = zipfile.ZIP_STORED
            zi.external_attr = 0o644 << 16
            zi.create_system = 0
            z.writestr(zi, data)
    return buf.getvalue()


def restore(man):
    for rel, pin in sorted(man.items()):
        if "base_pak" in pin:
            continue                    # third-party base: nothing in the mod tree to restore
        src = os.path.join(ROOT, *pin["base_from"].split("/"))
        data = open(src, "rb").read() if not pin["base_from"].endswith(".pk3") else None
        if data is None:
            with zipfile.ZipFile(src) as z:
                data = z.read(rel)
        assert hashlib.md5(data).hexdigest() == pin["base_md5"], (rel, "base source does not match its pin")
        dst = os.path.join(MOD, *rel.split("/"))
        open(dst, "wb").write(data)
        ns = (pin["base_ticks"] - EPOCH_TICKS) * 100
        os.utime(dst, ns=(ns, ns))
        print("restored", rel, pin["base_md5"], pin["base_ticks"])


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    man, members, fails = load()
    if mode == "restore":
        restore(man)
        return 0
    for f in fails:
        print("FAIL", f)
    if fails:
        return 1
    data = render(members)
    if mode == "build":
        open(PAK, "wb").write(data)
        print("wrote %s: %d members, %d bytes" % (PAK, len(members), len(data)))
        return 0
    if not os.path.exists(PAK) or open(PAK, "rb").read() != data:
        print("FAIL %s missing or differs from a rebuild - run: python docs/tools/gen_fixes_pak.py build" % PAKNAME)
        return 1
    print("OK %s: %d member(s), byte-identical to a rebuild; pinned bases intact" % (PAKNAME, len(members)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
