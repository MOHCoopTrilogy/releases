"""gen_loadart_pak.py - pack the loading-art pool images into their own out-of-band pak (v1.10.4).

    python docs/tools/gen_loadart_pak.py build    # write hzm-mohaa-coop-mod/zzzzzzzzzz_coop_loadart.pk3
    python docs/tools/gen_loadart_pak.py check    # exit 1 unless the pak on disk is byte-identical to a rebuild

WHY A SEPARATE PAK. build.ps1 puts every file under a top-level textures/ into zzzzzz_co-op_hzm_mod_assets_tex.pk3
(~1.3 GB), and the auto-updater reuses assets per PAK by sha256 - so 3.3 MB of new jpgs there made every player
re-download the whole texture pak (bug-3251). The images therefore live OUTSIDE the mod tree, in
docs/tools/assets/loadart/, and ship in this small pak, which build.ps1 copies and publish_release.ps1 stages like the
foliage / sky / tilefix paks. Its members are NEW names (textures/mohmenu/hzmload/<id>.jpg) that only the
hzmLoadArt_<id> shaders in scripts/coop_loadart.shader (code pak) ask for, so pak order cannot hide them.

Deterministic: members sorted, ZIP_STORED (jpg is already compressed; no zlib-version drift), fixed timestamp.
Gates: every clampMap image the shader file names has exactly one source jpg and vice versa; 2048x1024 baseline or
progressive JPEG (SOF marker read, no PIL needed); plain ASCII lowercase names.
"""
import io, os, re, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "docs", "tools", "assets", "loadart")
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
PAK = os.path.join(MOD, "zzzzzzzzzz_coop_loadart.pk3")
SHADER = os.path.join(MOD, "scripts", "coop_loadart.shader")
PREFIX = "textures/mohmenu/hzmload/"
STAMP = (2026, 9, 28, 0, 0, 0)
SIZE = (2048, 1024)


def jpeg_size(b):
    assert b[:2] == b"\xff\xd8", "not a JPEG"
    i = 2
    while i < len(b):
        assert b[i] == 0xFF, "bad marker at %d" % i
        m = b[i + 1]
        seg = int.from_bytes(b[i + 2:i + 4], "big")
        if m in (0xC0, 0xC1, 0xC2):
            h = int.from_bytes(b[i + 5:i + 7], "big")
            w = int.from_bytes(b[i + 7:i + 9], "big")
            return w, h
        i += 2 + seg
    raise AssertionError("no SOF marker")


def sources():
    fails = []
    names = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".jpg"))
    want = sorted(set(re.findall(r"clampMap\s+" + re.escape(PREFIX) + r"(\S+\.jpg)", open(SHADER, encoding="latin-1").read())))
    if names != want:
        fails.append("source jpgs %s != shader images %s" % (names, want))
    out = []
    for n in names:
        if not re.fullmatch(r"[a-z0-9_]+\.jpg", n):
            fails.append("bad name " + n)
        b = open(os.path.join(SRC, n), "rb").read()
        if jpeg_size(b) != SIZE:
            fails.append("%s is %dx%d, want %dx%d" % ((n,) + jpeg_size(b) + SIZE))
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
        print("FAIL %s missing - run: python docs/tools/gen_loadart_pak.py build" % PAK)
        return 1
    if open(PAK, "rb").read() != data:
        print("FAIL %s differs from a rebuild - run: python docs/tools/gen_loadart_pak.py build" % PAK)
        return 1
    print("OK %s: %d members, byte-identical to a rebuild" % (os.path.basename(PAK), len(members)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
