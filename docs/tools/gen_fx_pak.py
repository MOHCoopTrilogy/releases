#!/usr/bin/env python3
"""gen_fx_pak.py - builds zzzzzzzzzzzzz_coop_fx.pk3, the smoke & fire pak, from tracked sources (smoke & fire update,
docs/proposals/smokefire_2026-11-24/PLAN.md, Phase 0 D0/D1).

    python docs/tools/gen_fx_pak.py build    # write hzm-mohaa-coop-mod/zzzzzzzzzzzzz_coop_fx.pk3
    python docs/tools/gen_fx_pak.py check    # exit 1 on drift (pak vs sources, base pin, shadow copies)

WHY THIS PAK HOLDS THE EFFECT TIKS. fx_1025 (v1.10.37) shipped its 64 effect tiks in the mod tree, so build.ps1 put
them in zzzzzz_co-op_hzm_mod_assets_tex/_tey.pk3 (six z). Retail-named ones (grenexp_base, bazookaexp_base and the
mod's grenexp_snow) LOST to zzzzzz_hd_fx / zzzzzzzz_hd_fxfix ("co-op" < "hd", eight z), so hand-grenade and bazooka
blasts stayed retail for nine releases. split_tex.py then stripped every added models/ file from the tree at release,
and mod commit 1a4cddf50 committed the stripped tree: the sources existed only inside the tey pak. Here they are
tracked again (docs/tools/assets/fx/pak/, restored byte-for-byte from mod e61c056de) and ship in a pak that sorts
after every HD fx pak (13 z > 8 z). `fx_coverage.py check` verifies the winner over the shipped set.

MEMBERS = the pinned base pak (docs/tools/assets/fx/base/, the v1.10.37..v1.10.91 release copy: the fx_1025 flipbooks
plus 4 unrelated files) + every file under docs/tools/assets/fx/pak/ (overrides a base member of the same name).
Deterministic: members sorted, ZIP_DEFLATED, fixed timestamp.

⚠ TRAP: a lower-priority SHADOW copy (mod tree models/fx/grenexp_snow.tik, the tey pak) is NOT what the game loads.
Edit docs/tools/assets/fx/pak/<relpath>. `check` fails when a mod-tree shadow differs from its pin in
fx_pak_manifest.json, so an edit in the wrong place cannot pass silently.
"""
import hashlib, io, json, os, re, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(HERE, "assets", "fx", "pak")
BASE = os.path.join(HERE, "assets", "fx", "base", "zzzzzzzzzzzzz_coop_fx_v11037.pk3")
BASE_SHA256 = "9edb5e1b701f97cde71eeadf593fd6755b93630eba323188ab41c0e027ef3167"   # = manifests v1.10.91 entry
MANIFEST = os.path.join(HERE, "assets", "fx", "fx_pak_manifest.json")
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
PAK = os.path.join(MOD, "zzzzzzzzzzzzz_coop_fx.pk3")
# [2026-11-24] Until the user signs off the Phase 0 look (the grenade/bazooka blasts change for every player), `build`
# writes the STAGING copy, the mod tree keeps the v1.10.91 release pak, and build.ps1 does not run this check yet.
# Sign-off: set STAGE = None, `build`, wire `check` into build.ps1, flip the 3 D1 rules in fx_coverage.json.
STAGE = r"H:/hzm_work/smokefire/paks/zzzzzzzzzzzzz_coop_fx.pk3"
if STAGE:
    PAK = STAGE
STAMP = (2026, 11, 24, 0, 0, 0)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def members():
    fails = []
    base = open(BASE, "rb").read()
    if sha(base) != BASE_SHA256:
        fails.append("base pak %s sha256 %s != pinned %s" % (BASE, sha(base), BASE_SHA256))
    out = {}
    with zipfile.ZipFile(io.BytesIO(base)) as z:
        for n in z.namelist():
            if not n.endswith("/"):
                out[n] = z.read(n)
    lower = {k.lower(): k for k in out}
    overlay = set()
    for dp, _dn, fn in os.walk(SRC):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), SRC).replace(os.sep, "/")
            if rel.lower() in lower:
                del out[lower[rel.lower()]]
            out[rel] = open(os.path.join(dp, f), "rb").read()
            overlay.add(rel)
    return out, fails, overlay


#  [PLAN D3/D4] line-exact repairs of parse-broken effect tiks. The source member is pinned by md5 in its own pak (we
#  never edit a third-party or retail pak); each edit asserts the old line, so a changed source fails loudly.
_P = "\t\t)"
REPAIRS = [
    # zzzzzzzz_hd_fxfix (bug-1190's hand-built density pak) commented out a lingering-smoke block TOGETHER WITH the ")"
    # that closes the emitter before it: the live emitter never closes and swallows the rest of the file.
    ("models/fx/bh_dirt_hard.tik", "zzzzzzzz_hd_fxfix.pk3", "5885b40948c842105374ca66572353e7", [(109, "//" + _P, _P)]),
    ("models/fx/bh_dirt_lite.tik", "zzzzzzzz_hd_fxfix.pk3", "fd66be5f93ddc905c06d51bf0f16f9e7", [(109, "//" + _P, _P)]),
    ("models/fx/bh_mud_hard.tik", "zzzzzzzz_hd_fxfix.pk3", "866355cd7d43ac7b27992aba5bead05d", [(108, "//" + _P, _P)]),
    ("models/fx/bh_mud_lite.tik", "zzzzzzzz_hd_fxfix.pk3", "4e8c9b2ebb3964ebbc869875864c717c", [(108, "//" + _P, _P)]),
    ("models/fx/bh_wood_hard.tik", "zzzzzzzz_hd_fxfix.pk3", "650d53b83bc2cda2e2bffa102583193a", [(101, "//" + _P, _P)]),
    ("models/fx/bh_wood_lite.tik", "zzzzzzzz_hd_fxfix.pk3", "1b5a36b1c2732f2eefbb92566d941f32", [(101, "//" + _P, _P)]),
    # retail: the mushroom-cloud emitter "test" ends with "(" instead of ")" (m2l3 finale, e2l1 glider ride)
    ("models/emitters/barracks_explosion.tik", "Pak0.pk3", "478eaa4af3decb668eb37c98042b6c89", [(127, "\t\t(", "\t\t)")]),
    # retail: a stray ")" after the third originspawn closes the animation's frame block early (e2l1 glider flak)
    ("models/fx/exp_flak_near_moving.tik", "pak1.pk3", "cde66d987cad17f89770b08a3b8a79dc", [(67, "\t\t\t)", "")]),
]


def repaired(vfs):
    """{rel: bytes} for REPAIRS, from the pinned source members; fails on any pin or line mismatch"""
    out, fails = {}, []
    for rel, srcpak, md5, edits in REPAIRS:
        ents = [e for e in vfs.all(rel) if os.path.basename(e[1]).lower() == srcpak.lower()]
        if not ents:
            fails.append("repair %s: source pak %s not in the shipped set" % (rel, srcpak))
            continue
        raw = vfs.read(ents[-1])
        if hashlib.md5(raw).hexdigest() != md5:
            fails.append("repair %s: %s copy md5 %s != pinned %s" % (rel, srcpak, hashlib.md5(raw).hexdigest(), md5))
            continue
        nl = "\r\n" if b"\r\n" in raw else "\n"
        lines = raw.decode("latin-1").split(nl)
        for ln, old, new in edits:
            if lines[ln - 1].rstrip() != old:
                fails.append("repair %s:%d expected %r, found %r" % (rel, ln, old, lines[ln - 1]))
            else:
                lines[ln - 1] = new + "  // [smoke&fire D3/D4] repaired by gen_fx_pak.py, was: " + old.strip()
        out[rel] = nl.join(lines).encode("latin-1")
    return out, fails


SPRITESIZE = "scripts/coop_fx_spritesize.shader"
SPRITESIZE_SKIP = {
    # bug-2946: the lightglow corona of ~6,000 lamps, every muzzle glow and the headlights, restored under an Omaha
    # byte-identical rule - its 2x is left for the headlight owner to A/B (PLAN D2)
    "corona_util",
    # the only effect user of sandstorm02 is the mod's own weather dust veil (coop_dustveil_*), tuned in game at the
    # 4x size it has drawn at since the discstock upscale - shrinking it would retune the weather, not fix a retail effect
    "sandstorm02",
}


def shipped_vfs():
    """the shipped set WITHOUT this pak, so generated members never feed on their own output"""
    sys.path.insert(0, HERE)
    import fx_coverage as fc
    paks, _ver, _miss = fc.shipped_paks()
    paks = [p for p in paks if os.path.basename(p).lower() != "zzzzzzzzzzzzz_coop_fx.pk3"]
    return fc.PakVFS(paks)


def spritesize_shader(vfs):
    """[PLAN D2, bug-11244 class] retail spritegen shaders whose stage-0 image now loads LARGER from one of OUR paks
    (zzzzzzzzzz_coop_hd_discstock upscales a texture for its own shader and every other retail shader sharing that
    texture grows with it - puffystuff_light 4x, generalfireball_01 4x, sandstorm02 4x, snowplume_k5 4x) get
    spritescale * retail_w / loaded_w, so the particle keeps its retail world size (tr_sprite.c: width x spritescale)."""
    import fx_coverage as fc
    import discstock_vfs as dv
    sh = dv.Shaders(vfs)
    retail = fc.PakVFS(fc.retail_paks())
    out = []
    for n, (prio, fname, pak, name, body) in sorted(sh.defs.items()):
        if n in SPRITESIZE_SKIP or fc.kind(pak) != "retail" or not re.search(r"(?i)\bspritegen\b", body):
            continue
        imgs = dv.shader_images(body)
        if not imgs:
            continue
        im = imgs[0][1]
        _f, e = vfs.resolve_image(im)
        if not e or fc.kind(e[1]) != "ours":
            continue
        _rf, re_ = retail.resolve_image(im)
        now, ret = vfs.image_size(e), (retail.image_size(re_) if re_ else None)
        if not now or not ret or now[0] <= ret[0]:
            continue
        old = dv.shader_spritescale(body) or 1.0
        new = old * ret[0] / float(now[0])
        if re.search(r"(?im)^\s*spritescale\s+[-\d.]+", body):
            body2 = re.sub(r"(?im)^(\s*spritescale\s+)[-\d.]+", lambda m: m.group(1) + "%.5f" % new, body, count=1)
        else:
            body2 = re.sub(r"(?i)(\bspritegen\b[^\n]*\n)", lambda m: m.group(1) + "\tspritescale %.5f\n" % new, body, count=1)
        out.append("// %s (%s @ %s): stage-0 %s loads %dx%d from %s, retail %dx%d -> spritescale %.4f -> %.5f\n%s\n%s\n"
                   % (name, fname, os.path.basename(pak), im, now[0], now[1], os.path.basename(e[1]), ret[0], ret[1],
                      old, new, name, body2.strip()))
    head = ("// GENERATED by docs/tools/gen_fx_pak.py (spritesize_shader) - do not edit. Keeps retail sprites at their\n"
            "// retail world size where one of our HD paks enlarged their texture (PLAN D2). %d shaders.\n\n" % len(out))
    return (head + "\n".join(out)).replace("\r\n", "\n").encode("latin-1")


def shadows(overlay):
    """mod-tree copies of overlay files must stay at their pin (they ship lower and lose)"""
    man = json.load(open(MANIFEST, encoding="utf-8")) if os.path.isfile(MANIFEST) else {}
    fails = []
    for rel in sorted(overlay):
        p = os.path.join(MOD, *rel.split("/"))
        if os.path.isfile(p):
            m = hashlib.md5(open(p, "rb").read()).hexdigest()
            pin = man.get(rel, {}).get("shadow_md5")
            if pin is None:
                fails.append("%s: a mod-tree shadow exists and is not pinned in %s" % (rel, os.path.relpath(MANIFEST, ROOT)))
            elif m != pin:
                fails.append("%s: the MOD-TREE copy changed (md5 %s, pinned %s) - it does not ship (this pak wins); "
                             "edit docs/tools/assets/fx/pak/%s instead" % (rel, m, pin, rel))
    return fails


def render(mem):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        for name in sorted(mem, key=lambda s: s.lower()):
            zi = zipfile.ZipInfo(name, STAMP)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, mem[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return bio.getvalue()


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "check"
    mem, fails, overlay = members()
    fails += shadows(overlay)
    vfs = shipped_vfs()
    mem[SPRITESIZE] = spritesize_shader(vfs)
    rep, rf = repaired(vfs)
    fails += rf
    for rel, data in rep.items():
        if rel in mem:
            fails.append("repair %s collides with an overlay/base member" % rel)
        mem[rel] = data
    data = render(mem)
    if cmd == "build":
        if fails:
            print("gen_fx_pak: NOT built:\n  " + "\n  ".join(fails))
            return 1
        open(PAK, "wb").write(data)
        print("gen_fx_pak: wrote %s (%d members, %d bytes, sha256 %s)" % (PAK, len(mem), len(data), sha(data)))
        return 0
    cur = open(PAK, "rb").read() if os.path.isfile(PAK) else b""
    if cur != data:
        fails.append("%s differs from its sources - run: python docs/tools/gen_fx_pak.py build" % os.path.relpath(PAK, ROOT))
    for f in fails:
        print("gen_fx_pak FAIL: " + f)
    print("gen_fx_pak: %s (%d members)" % ("OK" if not fails else "%d FAIL" % len(fails), len(mem)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
