"""gen_tileart_pak.py - pack the coop mission-tile art into its own out-of-band pak.

    python docs/tools/gen_tileart_pak.py build    # write hzm-mohaa-coop-mod/zzzzzzzzzz_coop_tileart.pk3
    python docs/tools/gen_tileart_pak.py check    # exit 1 unless the pak on disk is byte-identical to a rebuild

WHY A SEPARATE PAK (the gen_loadart_pak.py recipe, bug-3251): anything under textures/ in the mod tree lands in
zzzzzz_co-op_hzm_mod_assets_tex.pk3 (~1.3 GB) and the auto-updater reuses assets per PAK by sha256, so new art there
would make every player re-download that whole pak. The images live in docs/tools/assets/tileart/ and ship here.
Members are NEW names under textures/mohmenu/hzmtile/ - asked for only by the coop_tileArt<N>_{c,s} cvars the
ui/coop_start/*.cfg files set - so no .dds/.tga of the same name can shadow them (TRAPS T6).

Deterministic: members sorted, ZIP_STORED, fixed timestamp. Gates:
  * every hzmtile image a ui/coop_start/*.cfg names has exactly one source jpg, and every source is named by a cfg;
  * cards 512x512, prints (print_*) 512x384, baseline/progressive JPEG (SOF read, no PIL);
  * lowercase ASCII names;
  * no scripts/*.shader in the mod tree defines a textures/mohmenu/hzmtile/* name (a shader would change sampling).
"""
import glob
import io
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "docs", "tools", "assets", "tileart")
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
PAK = os.path.join(MOD, "zzzzzzzzzz_coop_tileart.pk3")
PREFIX = "textures/mohmenu/hzmtile/"
STAMP = (2026, 9, 29, 0, 0, 0)


def jpeg_size(b):
    assert b[:2] == b"\xff\xd8", "not a JPEG"
    i = 2
    while i < len(b):
        assert b[i] == 0xFF, "bad marker at %d" % i
        m = b[i + 1]
        seg = int.from_bytes(b[i + 2:i + 4], "big")
        if m in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(b[i + 7:i + 9], "big"), int.from_bytes(b[i + 5:i + 7], "big")
        i += 2 + seg
    raise AssertionError("no SOF marker")


def wanted():
    names = set()
    for p in glob.glob(os.path.join(MOD, "ui", "coop_start", "*.cfg")):
        names |= set(re.findall(re.escape(PREFIX) + r"([a-z0-9_]+)", open(p, encoding="latin-1").read()))
    return {n + ".jpg" for n in names}


def sources():
    fails = []
    have = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".jpg")) if os.path.isdir(SRC) else []
    cards = {f for f in have if not f.startswith("print_")}
    want = wanted()
    if cards != want:
        fails.append("cards vs cfg names: missing %s, unused %s" % (sorted(want - cards)[:8], sorted(cards - want)[:8]))
    # war-room prints (print_<card>): not named by a cfg (the menu remaster's board uses them); exactly one per card
    prints = {f for f in have if f.startswith("print_")}
    if prints != {"print_" + c for c in cards}:
        fails.append("prints vs cards: missing %s, orphan %s" % (sorted({"print_" + c for c in cards} - prints)[:8],
                                                                 sorted(prints - {"print_" + c for c in cards})[:8]))
    for sh in glob.glob(os.path.join(MOD, "scripts", "*.shader")):
        if PREFIX.rstrip("/") in open(sh, encoding="latin-1").read():
            fails.append("%s names %s - tile art must stay bare images" % (os.path.basename(sh), PREFIX))
    out = []
    for n in have:
        if not re.fullmatch(r"[a-z0-9_]+\.jpg", n):
            fails.append("bad name " + n)
        b = open(os.path.join(SRC, n), "rb").read()
        want_size = (512, 384) if n.startswith("print_") else (512, 512)
        if jpeg_size(b) != want_size:
            fails.append("%s is %dx%d, want %dx%d" % ((n,) + jpeg_size(b) + want_size))
        out.append((PREFIX + n, b))
    return out, fails


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


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    members, fails = sources()
    for f in fails:
        print("FAIL", f)
    if fails:
        return 1
    data = render(members)
    if mode == "build":
        open(PAK, "wb").write(data)
        print("wrote %s: %d members, %d bytes" % (PAK, len(members), len(data)))
        return 0
    if not os.path.exists(PAK):
        print("FAIL %s missing - run: python docs/tools/gen_tileart_pak.py build" % PAK)
        return 1
    if open(PAK, "rb").read() != data:
        print("FAIL %s differs from a rebuild - run: python docs/tools/gen_tileart_pak.py build" % PAK)
        return 1
    print("OK %s: %d members, byte-identical to a rebuild" % (os.path.basename(PAK), len(members)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
