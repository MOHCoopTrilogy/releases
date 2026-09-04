#!/usr/bin/env python
"""
gen_metal_brushes.py - find the collision brushes that wrap a map's METAL obstacles, so the engine
can retype them at load.

WHY
    [user 2026-09-01] "can we ensure the bullet ricochets that hit the tank traps also have the same
    spark effects and sounds if they hit the higgins boats and tanks".

    They cannot, as shipped, and the reason is structural rather than a missing shader:

      * The tank traps are STATIC MODELS (LUMP_STATICMODELDEF). There is no static-model collision
        anywhere in qcommon/ or server/ - they are render-only. Bullets hit a separate CLIP BRUSH the
        mapper placed around each one.
      * A brush's surface type is read from the BSP's own baked shader lump
        (cm_load.c:126 `out->surfaceFlags = LittleLong(in->surfaceFlags)`), NOT from any .shader file
        parsed at runtime. So overriding `static_hedgehog` in the mod's scripts/ cannot change it, and
        neither can the renderer - I checked both before writing this.
      * cgame decides the impact effect from `trace.surfaceFlags & MASK_SURF_TYPE`
        (cg_parsemsg.cpp:83), and sparks + the ricochet whine need SURF_METAL / SURF_ROCK / SURF_GRILL
        (cg_parsemsg.cpp:96). The traps' clip brushes carry none of those.

    So the surface type was decided when the map was compiled in 2001 and the only honest place to
    change it is at clipmap load. This generator finds WHICH brushes to change; the engine half is the
    `cmpatch/<map>_metal.txt` reader in qcommon/cm_load.c, which ORs SURF_METAL into their sides.

HOW THE MATCH WORKS
    For every static model whose name is in METAL_MODELS, take its origin and look for a SOLID brush
    whose bounds contain that point. To avoid grabbing the terrain, the seawall or a building, a brush
    only qualifies if it is small enough to plausibly be one obstacle's clip (MAX_EXTENT) - a hedgehog
    is about 100 units across, so anything over a few hundred is something else and is rejected.

    A brush that wraps two obstacles is listed once. A model with no matching brush is REPORTED, not
    silently skipped, because "no brush found" and "brush found and retyped" need different follow-up.

USAGE
    python docs/tools/gen_metal_brushes.py [--map m3l1a] [--check]
"""
import io, os, struct, sys, zipfile

GAME_ROOTS = [r"G:\GOG\Medal of Honor - Allied Assault War Chest", r"G:\mohaa-gl2"]
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"

LUMP_SHADERS, LUMP_PLANES = 0, 1
LUMP_BRUSHSIDES, LUMP_BRUSHES = 11, 12
LUMP_STATICMODELDEF = 25

SZ_SHADER, SZ_PLANE, SZ_SIDE, SZ_BRUSH, SZ_SMODEL = 140, 16, 12, 12, 164

# THE BIT THAT MATTERS IS WEAPONCLIP, NOT SOLID. The trap clips are textures/common/nodraw carrying
# contents 0x280e2000 = FENCE | MONSTERCLIP | WEAPONCLIP | VEHICLECLIP (+ two high MOHAA bits) and
# NO solid bit at all. Testing CONTENTS_SOLID matched 44 of 210 obstacles and none of the 94
# hedgehogs. WEAPONCLIP is also the correct test on the merits: it is precisely the flag that says
# "a bullet stops here", which is the only kind of brush whose surface type can ever be read by an
# impact effect.
CONTENTS_SOLID = 0x1
CONTENTS_WEAPONCLIP = 0x40000
BULLET_STOPPING = CONTENTS_SOLID | CONTENTS_WEAPONCLIP
MAX_EXTENT = 320.0          # a hedgehog is ~100u across; anything much bigger is not its clip
MATCH_RADIUS = 110.0        # origin-to-clip-centre; measured worst case on this map is ~46

# every static model on this beach that a bullet should spark off. Steel obstacles only - the sandbag
# and body statics are deliberately absent.
METAL_MODELS = ("hedgehog", "ramp_tripleleg", "minepole", "barbwire_post",
                "barbwire_tetra_post", "barbwire_long", "barbwire_long_two_post")


def find_bsp(mapname):
    for root in GAME_ROOTS:
        for sub in ("main", "mainta", "maintt"):
            d = os.path.join(root, sub)
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if not f.lower().endswith(".pk3"):
                    continue
                try:
                    z = zipfile.ZipFile(os.path.join(d, f))
                except Exception:
                    continue
                for n in z.namelist():
                    if n.lower().endswith("maps/%s.bsp" % mapname) or n.lower().endswith("/%s.bsp" % mapname):
                        return z.read(n)
    return None


def lump(bsp, i):
    off, ln = struct.unpack_from("<ii", bsp, 12 + i * 8)
    return bsp[off:off + ln]


def main():
    mapname = sys.argv[sys.argv.index("--map") + 1] if "--map" in sys.argv else "m3l1a"
    bsp = find_bsp(mapname)
    if not bsp:
        print("  %s.bsp not found in any install" % mapname)
        return 1

    shaders = lump(bsp, LUMP_SHADERS)
    planes = lump(bsp, LUMP_PLANES)
    sides = lump(bsp, LUMP_BRUSHSIDES)
    brushes = lump(bsp, LUMP_BRUSHES)
    smodels = lump(bsp, LUMP_STATICMODELDEF)

    shader_contents = []
    for i in range(len(shaders) // SZ_SHADER):
        sf, cf = struct.unpack_from("<ii", shaders, i * SZ_SHADER + 64)
        shader_contents.append((sf, cf))

    plane = []
    for i in range(len(planes) // SZ_PLANE):
        nx, ny, nz, d = struct.unpack_from("<4f", planes, i * SZ_PLANE)
        plane.append((nx, ny, nz, d))

    side = []
    for i in range(len(sides) // SZ_SIDE):
        pn, sn, _ = struct.unpack_from("<iii", sides, i * SZ_SIDE)
        side.append((pn, sn))

    # brush bounds from its AXIAL planes, which is how CM_BoundBrush does it
    binfo = []
    for i in range(len(brushes) // SZ_BRUSH):
        fs, ns, sn = struct.unpack_from("<iii", brushes, i * SZ_BRUSH)
        mn = [1e30, 1e30, 1e30]
        mx = [-1e30, -1e30, -1e30]
        for k in range(fs, fs + ns):
            if k < 0 or k >= len(side):
                continue
            pn = side[k][0]
            if pn < 0 or pn >= len(plane):
                continue
            nx, ny, nz, d = plane[pn]
            for ax, nv in enumerate((nx, ny, nz)):
                if nv > 0.999:
                    mx[ax] = d
                elif nv < -0.999:
                    mn[ax] = -d
        contents = shader_contents[sn][1] if 0 <= sn < len(shader_contents) else 0
        binfo.append((mn, mx, contents, fs, ns))

    # the obstacles
    targets = []
    for i in range(len(smodels) // SZ_SMODEL):
        nm = smodels[i * SZ_SMODEL: i * SZ_SMODEL + 64].split(b"\0")[0].decode("latin-1")
        base = nm.replace("\\", "/").split("/")[-1].lower().replace(".tik", "")
        if base in METAL_MODELS:
            ox, oy, oz = struct.unpack_from("<3f", smodels, i * SZ_SMODEL + 128)
            targets.append((base, ox, oy, oz))

    # NEAREST QUALIFYING BRUSH, not containment. A static model's origin sits at its BASE while the
    # clip hull is built around the body, so the origin is routinely a few tens of units outside the
    # brush - containment matched only 95 of 210 and missed 42 hedgehogs that plainly do have a clip
    # (measured: the nearest one is 46 units from the origin, 45x138x95, textures/common/nodraw).
    # Nearest-centre-within-MATCH_RADIUS is both more accurate here and easier to reason about: it
    # cannot silently attach an obstacle to a brush on the far side of the map.
    hit, miss = {}, {}
    for base, ox, oy, oz in targets:
        best = None
        for bi, (mn, mx, contents, fs, ns) in enumerate(binfo):
            if not (contents & BULLET_STOPPING):
                continue
            if mn[0] > 1e29 or mx[0] < -1e29:
                continue
            if max(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]) > MAX_EXTENT:
                continue
            cx = (mn[0] + mx[0]) * 0.5
            cy = (mn[1] + mx[1]) * 0.5
            cz = (mn[2] + mx[2]) * 0.5
            d2 = (cx - ox) ** 2 + (cy - oy) ** 2 + (cz - oz) ** 2
            if d2 <= MATCH_RADIUS * MATCH_RADIUS and (best is None or d2 < best[0]):
                best = (d2, bi)
        if best is None:
            miss[base] = miss.get(base, 0) + 1
        else:
            hit.setdefault(best[1], base)

    print("  %s: %d metal statics, %d brushes matched, %d unmatched"
          % (mapname, len(targets), len(hit), sum(miss.values())))
    for k in sorted(miss):
        print("    unmatched: %-24s %d" % (k, miss[k]))

    out = [
        "# GENERATED by docs/tools/gen_metal_brushes.py - DO NOT HAND-EDIT.",
        "#",
        "# Collision brushes that wrap this map's steel obstacles. The engine ORs SURF_METAL into",
        "# every side of each brush listed here at clipmap load, so bullets striking a tank trap give",
        "# the metal impact effect and the ricochet whine instead of the default.",
        "#",
        "# Needed because the traps are RENDER-ONLY static models with no collision of their own, and",
        "# the clip brush around each one takes its surface type from the BSP's baked shader lump",
        "# (cm_load.c:126) - not from any .shader file, so it cannot be overridden from the mod pk3.",
        "#",
        "# %d brushes, matched against %d static models of type: %s"
        % (len(hit), len(targets), " ".join(sorted(set(v for v in hit.values())))),
    ]
    for bi in sorted(hit):
        out.append("%d" % bi)

    dst = os.path.join(MOD, "cmpatch", "%s_metal.txt" % mapname)
    text = "\n".join(out) + "\n"
    if "--check" in sys.argv:
        cur = io.open(dst, encoding="latin-1").read() if os.path.exists(dst) else ""
        if cur != text:
            print("  STALE - run without --check")
            return 1
        print("  up to date")
        return 0
    io.open(dst, "w", encoding="latin-1", newline="\n").write(text)
    print("  wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
