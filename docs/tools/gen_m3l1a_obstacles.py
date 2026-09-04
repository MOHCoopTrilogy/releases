"""Generate the Omaha beach-obstacle table that coop placement code tests against.

WHY THIS EXISTS
---------------
Everything the coop layer drops on Omaha - gore chunks, blood pools, dropped kit, ammo crates, bodies,
boats, fires - ends in `droptofloor`, and `Entity::droptofloor` (fgame/entity.cpp:2669) is a BOX trace
against `edict->clipmask`. It stops on the first collidable thing beneath, and the tidal flat is covered
in collidable static models: hedgehogs, minepoles, barbwire, Belgian-gate ramps. So a pool dropped over
a hedgehog does not land on the sand, it lands ON the hedgehog - which is what the user reported as
"blood floating over the tanktraps on omaha", repeatedly.

Two earlier attempts solved this the wrong way, and both failures are the reason this file exists:

  * bug-2209 - five of six Higgins boats were found embedded in obstacles, and the fix was to hand-pick
    new coordinates and write ">=460u clearance" in a comment. No code tested anything.
  * bug-2256 - four MORE boats were then added by eye under that same comment, which by then asserted
    the whole table had been verified. Measured afterwards they cleared 295, 116, 100 and 84 units.
    A comment claiming a property nobody measured is worse than no comment: it stops the next session
    from checking.

The lesson is the OpenWolf rule: an inventory extractable from the data MUST be generated, never
hand-written. So the obstacle set is derived from the BSP here, and placement code tests against it at
runtime instead of trusting a coordinate table somebody eyeballed.

WHAT IT READS
-------------
maps/m3l1a.bsp, LUMP_STATICMODELDEF (lump 25). MOHAA's header is `ident, version, checksum, lumps[28]`,
so the lump directory starts at byte 12, not 8 - getting that wrong yields garbage that still parses.
Record stride is 164 bytes: model name at offset 0 (64 bytes, NUL-padded), origin at offset 128.

FOOTPRINT RADII are taken from each model's own QUAKED box where it declares one, and from the table
below where it does not (several of these ship `(0 0 0) (0 0 0)`, which is not a real footprint). The
radius is the model's own extent; callers add their own pad on top, because what matters is
obstacle_radius + half the thing being placed, not an origin-to-origin distance. The previous prose
margins were origin-to-origin, which is how ">=70u from a hedgehog" ended up overlapping a 64u-radius
hedgehog.

OUTPUT
------
hzm-mohaa-coop-mod/maps/m3l1a/obstacles.scr - a generated Morpheus table, exec'd once at map load,
filling level.coop_obstX/Y/R and level.coop_obstN. Do not hand-edit it; re-run this.
"""

import io
import glob
import os
import re
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
OUT = os.path.join(MOD, "maps", "m3l1a", "obstacles.scr")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"

LUMP_STATICMODELDEF = 25
STRIDE = 164
NAME_OFF, ORIGIN_OFF = 0, 128

# Which statics an infantryman, a corpse or a crate can be left sitting on top of.
#
# [user 2026-09-01, bug-2267] THIS USED TO BE A KEYWORD FILTER AND THAT WAS THE BUG. It listed only the
# beach obstacles - hedgehog / minepole / barbwire / ramp / tetra - which is 229 of the map's 401 static
# models, and the user came back with "its on top of obstacles such as tank tracks, and a few other
# items". The 172 EXCLUDED statics include 32 ammo crates (45cal_crate, 30cal_crate, exp_crate1-3,
# heat_crate, 50cal_crate, fragcrate, cratelid) sitting on the sand at y -1195..527, 33 static bodies
# (body_us01-06, body_usvest03-06) and 34 dropped helmets, every one of them collidable and every one of
# them something droptofloor will happily leave a blood pool or a rifleman standing on.
#
# There is no reason to filter at all: a static model is a static model, and the radius is what decides
# how much room a placement needs. Lights and coronas up in the bunkers get tiny radii and cost nothing.
OBSTACLE_KEYS = None      # None = every static model in the lump

# Fallbacks for models whose QUAKED box is (0 0 0) (0 0 0). Measured from the meshes' visual extent;
# deliberately generous, because the cost of an over-large radius is one fewer gore cluster and the cost
# of an under-large one is a pool hanging in the air on a tank trap.
FALLBACK_RADIUS = {
    "minepole": 28,          # a stake with a Teller mine lashed to the top
    "ramp_quadleg": 130,     # Belgian gate - the big ones
    "ramp_tripleleg": 120,
    "barbwire": 72,          # wire runs: wide and low, and a body on one reads badly
    "barbwire_post": 40,
    "barbwire_long": 96,
    "barbwire_one_post": 48,
    "barbwire_long_one_post": 96,
    "barbwire_long_two_post": 110,
    "barbwire_two_post": 112,
    # [bug-2267] the families the keyword filter used to drop. Crates and bodies are what the user was
    # seeing blood and men perched on; helmets and coronas are tiny and cost a placement almost nothing.
    "45cal_crate": 34, "30cal_crate": 26, "50cal_crate": 20,
    "exp_crate1": 32, "exp_crate1a": 32, "exp_crate2": 32, "exp_crate2a": 32,
    "exp_crate3": 32, "exp_crate3a": 32, "heat_crate": 30,
    "fragcrate1": 18, "fragcrate1a": 18, "cratelid1": 18, "cratelid2": 24,
    "indycrate": 30, "nazi_crate": 36, "mg42ammoboxwbelt": 22, "supplydropcrate": 160,
    "sandbag_link_main": 90, "sandbag_link_bottomcap": 70, "sandbag_link_topcap": 70,
    "sandbag_small_semicircle": 80, "sandbag_large_semicircle": 130,
    "vent_valve": 30, "lightbulb_caged": 12, "corona_util": 8,
}
# Static CORPSES and dropped helmets are deliberately given a SMALL radius rather than excluded: blood
# pooling around a body is right and wanted, a rifleman standing on one is not, so the pad the caller
# passes (45 for a man, 170 for a big blood plane) does the discriminating.
BODY_RADIUS = 30
HELMET_RADIUS = 14
DEFAULT_RADIUS = 64


def read_bsp():
    for d in ("main", "mainta", "maintt"):
        for p in sorted(glob.glob(os.path.join(GOG, d, "*.pk3"))):
            try:
                z = zipfile.ZipFile(p)
            except Exception:
                continue
            for n in z.namelist():
                if n.lower() == "maps/m3l1a.bsp":
                    return z.read(n)
    # the repo carries a copy too, so the generator still runs without the game installed
    local = os.path.join(REPO, "original-scripts", "mohaa", "maps", "m3l1a.bsp")
    if os.path.exists(local):
        return open(local, "rb").read()
    return None


def quaked_radii():
    """radius per static model name, from the model's own QUAKED bounding box where it has one"""
    out = {}
    for d in ("main", "mainta", "maintt"):
        for p in sorted(glob.glob(os.path.join(GOG, d, "*.pk3"))):
            try:
                z = zipfile.ZipFile(p)
            except Exception:
                continue
            for n in z.namelist():
                ln = n.lower()
                if not (ln.startswith("models/static/") and ln.endswith(".tik")):
                    continue
                base = ln.split("/")[-1][:-4]
                if base in out:
                    continue
                if OBSTACLE_KEYS is not None and not any(k in base for k in OBSTACLE_KEYS):
                    continue
                try:
                    t = z.read(n).decode("latin-1")
                except Exception:
                    continue
                m = re.search(r"QUAKED\s+\S+\s+\([^)]*\)\s+\(([^)]*)\)\s+\(([^)]*)\)", t)
                if not m:
                    continue
                try:
                    mn = [float(x) for x in m.group(1).split()]
                    mx = [float(x) for x in m.group(2).split()]
                except ValueError:
                    continue
                r = max(abs(mn[0]), abs(mx[0]), abs(mn[1]), abs(mx[1]))
                if r > 0:
                    out[base] = r
    return out


def lit(n):
    """Morpheus has no unary minus in an expression - the project writes negatives as `0 - N`."""
    n = int(round(n))
    return str(n) if n >= 0 else "0 - %d" % (-n)


def main():
    write = "--write" in sys.argv
    bsp = read_bsp()
    if bsp is None:
        print("m3l1a.bsp not found (looked in the GOG paks and original-scripts/)")
        return 1

    off, ln = struct.unpack_from("<ii", bsp, 12 + LUMP_STATICMODELDEF * 8)
    boxes = quaked_radii()

    rows, counts = [], {}
    for i in range(ln // STRIDE):
        b = bsp[off + i * STRIDE: off + (i + 1) * STRIDE]
        name = b[NAME_OFF:NAME_OFF + 64].split(b"\x00")[0].decode("latin-1", "replace")
        base = name.lower().replace("\\", "/").split("/")[-1]
        if base.endswith(".tik"):
            base = base[:-4]
        if OBSTACLE_KEYS is not None and not any(k in base for k in OBSTACLE_KEYS):
            continue
        x, y, z = struct.unpack_from("<fff", b, ORIGIN_OFF)
        if base.startswith("body_"):
            r = BODY_RADIUS
        elif base.startswith("static_us-helmet"):
            r = HELMET_RADIUS
        else:
            r = boxes.get(base, FALLBACK_RADIUS.get(base, DEFAULT_RADIUS))
        rows.append((x, y, r, z))
        counts[base] = counts.get(base, 0) + 1

    rows.sort(key=lambda t: t[0])          # sorted by X so a future bucketed scan stays cheap
    for k in sorted(counts):
        print("  %-28s %3d  r=%d" % (k, counts[k], boxes.get(k, FALLBACK_RADIUS.get(k, DEFAULT_RADIUS))))
    print("  %-28s %3d" % ("TOTAL", len(rows)))

    # Z IS CARRIED TOO [bug-2282]. A static model sits ON the ground, so the nearest one's z is a local
    # ground reference that works anywhere on the map - including the bluff, where a single height per
    # y-band is meaningless and the perched test had to be switched off. That is how rifles ended up
    # sitting on top of the barbed wire at y 3200-5900.
    body = "\n".join(
        "\tlocal.n++; level.coop_obstX[local.n] = %s; level.coop_obstY[local.n] = %s; "
        "level.coop_obstR[local.n] = %d; level.coop_obstZ[local.n] = %s"
        % (lit(x), lit(y), int(r), lit(z)) for x, y, r, z in rows)

    text = (
        "// HZM coop [2026-09-01, bug-2262] OMAHA BEACH OBSTACLE TABLE.\n"
        "// GENERATED by docs/tools/gen_m3l1a_obstacles.py - DO NOT HAND-EDIT, re-run the generator.\n"
        "//\n"
        "// Every hedgehog, minepole, barbwire run and Belgian-gate ramp on the tidal flat, read out of\n"
        "// LUMP_STATICMODELDEF in maps/m3l1a.bsp with its own footprint radius. coop_dropClear in\n"
        "// maps/m3l1a/coopified.scr tests every placement against this, because droptofloor is a BOX\n"
        "// trace against clipmask and will happily leave a blood pool sitting on a tank trap - which is\n"
        "// exactly what the user kept reporting.\n"
        "//\n"
        "// Sorted by X. The radius is the OBSTACLE's own extent; callers add their own pad, since what\n"
        "// matters is obstacle_radius + half the thing being placed. The two hand-picked margins this\n"
        "// replaces were origin-to-origin, which is how \">=70u from a hedgehog\" overlapped a 64u one.\n"
        "//=========================================================================\n"
        "init:{\n"
        "//=========================================================================\n"
        "\tlocal.n = 0\n"
        + body + "\n"
        "\tlevel.coop_obstN = local.n\n"
        "}end\n"
    )
    out = text.encode("ascii")
    assert b"\r" not in out and max(out) < 128

    if write:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        open(OUT, "wb").write(out)
        print("\n  wrote %s (%d obstacles, %d bytes)" % (os.path.relpath(OUT, REPO), len(rows), len(out)))
    else:
        print("\n  DRY RUN - %d obstacles; pass --write" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
