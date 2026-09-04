"""Generate mod-owned reload-magazine TIKs carrying a per-finish skin list.

THE DEFECT (bug-2241, open since 2026-08-18)
--------------------------------------------
The magazine in your left hand during a reload is a separate networked entity, attached by a frame
command in the third-person reload alias (models/player/base/anims_smg.txt:14 and siblings). It is
drawn in first person because cg_modelanim.c:2030 whitelists tag_weapon_left/right onto the FPS
model. Entity::AttachModelEvent copies nothing from the parent, and each retail clip TIK declares
exactly ONE shader row - so numskins is 1, tr_model.cpp clamps every index to 0, and the magazine has
always rendered stock while the gun wore its finish.

The engine half (entity.cpp CoopClipFinishIndex) stamps a 0-7 index into the attached entity's
per-surface skin bits. This tool writes the matching skin LISTS so there is something to select.

HOW THE RIGHT SHADER IS DERIVED, NOT GUESSED
--------------------------------------------
A clip TIK wears the same stock shader as the gun's own clip surface - thompson_clip.tik says
`surface all shader ThompsonSMG`, and thompsonsmg.tik says `surface Clip shader ThompsonSMG`. So the
correct finish shader for the clip is simply WHATEVER THE GUN'S OWN VARIANT TIK ASSIGNS TO THAT SAME
SURFACE. That is exact, and it means the magazine can never drift from the gun.

Matching on texture was tried first and is WRONG: gold, chrome and blued tint the stock texture with
an extra multiply stage, so their base map is the stock file, while bloody and the three camos use
purpose-authored art under textures/coop_skins/. A texture match therefore succeeds for three
finishes and fails for four, which is worse than failing cleanly.

The base -> variant mapping is read from coop_mod/loadoutskins.scr's own coop_skinGive table, so this
tool cannot disagree with what the loadout system actually gives the player.

THE CEILING IS EXACTLY EIGHT
----------------------------
MAX_TIKI_SHADER is 8 (tiki/tiki_shared.h:109) and MAX_TIKI_LOAD_SHADERS must track it
(qcommon/tiki.h:65) - raising one alone strncpy's over numskins and hangs the load printing ~2
billion lines (bug-2082). Stock + 7 finishes is exactly 8, so this uses the bus to its limit and an
eighth finish would require raising BOTH constants. The tool refuses to emit a 9th row.
"""

import argparse
import glob
import os
import re
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
OUTDIR = os.path.join(MOD, "models", "ammo")

FINISHES = ["gold", "chrome", "blued", "bloody", "camo_woodland", "camo_winter", "camo_desert"]
MAX_SKINS = 8   # MAX_TIKI_SHADER


# WHICH GUN EACH MAGAZINE BELONGS TO. Explicit, because inferring it is unsafe: the shader is NOT a
# reliable key. textures/models/weapons/m1garand/m1clip.tga is a GENERIC clip sheet worn by ten
# different guns, so a shader-keyed lookup happily returns johnson_m1941 for the Garand's magazine
# and paints it with the wrong finish - silently, and only visible mid-reload. Each row below is the
# gun whose reload alias actually issues the attachmodel (see models/player/base/anims_*.txt).
#
# The rocket and shell props are deliberately absent: bazooka_shell, panzer_shell, piat_shell and
# nagant_pistol_shell are ordnance, not magazines, and no finish is meant to reach them.

# Magazines whose TIK declares NO surface row at all - they inherit the name embedded in the .skd.
# The name was read out of the binary and then CONFIRMED against the gun's own TIK, which declares
# the same surface and names its stock shader. Only confirmed pairs are listed:
#   sten_clip.skd      surface Sten_Clip     -> sten.tik declares sten_clip, shader sten_smg
#   svt_clip.skd       surface svt_riflecull -> svt_rifle.tik declares it, shader svt_riflecull
# g43_clip.skd is deliberately ABSENT: its embedded name reads G43_Clip2 but g43.tik declares
# g43_clip, so the two do not agree and guessing would either do nothing or shift surface indices.
NO_SURFACE_ROW = {
    "models/ammo/sten_clip.tik":      ("Sten_Clip", "sten_smg"),
    "models/ammo/svt_clip_reload.tik": ("svt_riflecull", "svt_riflecull"),
}

CLIP_GUN = {
    "models/ammo/thompson_clip.tik":           "models/weapons/thompsonsmg.tik",
    "models/ammo/mp40_clip.tik":               "models/weapons/mp40.tik",
    "models/ammo/mp44_clip.tik":               "models/weapons/mp44.tik",
    "models/ammo/p38_clip.tik":                "models/weapons/p38.tik",
    "models/ammo/colt_clip.tik":               "models/weapons/colt45.tik",
    "models/ammo/silencedpistol_clip.tik":     "models/weapons/silencedpistol.tik",
    "models/ammo/ppsh_clip_reload.tik":        "models/weapons/ppsh_smg.tik",
    "models/ammo/garand_clip_reload.tik":      "models/weapons/m1_garand.tik",
    "models/ammo/springfield_clip_reload.tik": "models/weapons/springfield.tik",
    "models/ammo/enfield_clip1.tik":           "models/weapons/enfield.tik",
    "models/ammo/enfield_clip2.tik":           "models/weapons/enfield.tik",
    "models/ammo/kar98_clip_reload.tik":       "models/weapons/kar98.tik",
    "models/ammo/it_w_carcano_clip.tik":       "models/weapons/it_w_carcano.tik",
    "models/ammo/it_w_beretta_clip.tik":       "models/weapons/it_w_beretta.tik",
    "models/ammo/bar_clip.tik":                "models/weapons/bar.tik",
    "models/ammo/sten_clip.tik":               "models/weapons/sten.tik",
    "models/ammo/g43_clip.tik":                "models/weapons/g43.tik",
    "models/ammo/svt_clip_reload.tik":         "models/weapons/svt_rifle.tik",
}

_PAKS = None


def paks():
    global _PAKS
    if _PAKS is None:
        out = []
        for d in ("main", "mainta", "maintt"):
            out += sorted(glob.glob(os.path.join(GOG, d, "*.pk3")))
        _PAKS = out
    return _PAKS


def read_first(relpath, retail_only=False):
    """Highest-priority copy of a pak file: later paks win, so walk in reverse.

    retail_only skips this mod's own pk3s. It is not optional for the clip TIKs: once this tool has
    written a generated clip into the mod pak, a later run would read THAT back as its own "stock"
    source and treat a finish shader as the base - the same compounding footgun as the gore
    generator (bug-2229). The retail copy is the only correct source.
    """
    for p in reversed(paks()):
        if retail_only and "co-op_hzm" in os.path.basename(p).lower():
            continue
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            if n.lower() == relpath.lower():
                return z.read(n).decode("latin-1")
    return None


def all_shader_text():
    """Every shader definition, retail plus the mod's own, name -> body."""
    out = {}
    for p in paks():
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            if not n.lower().endswith(".shader"):
                continue
            try:
                t = z.read(n).decode("latin-1")
            except Exception:
                continue
            for name, body in blocks(t):
                out.setdefault(name.lower(), body)
    for f in glob.glob(os.path.join(MOD, "scripts", "*.shader")):
        t = open(f, encoding="latin-1").read()
        for name, body in blocks(t):
            out.setdefault(name.lower(), body)
    return out


NAME_BRACE = re.compile(r"^[ \t]*([A-Za-z0-9_\-/\.]+)[ \t]*\r?\n[ \t]*\{", re.M)


def blocks(t):
    """(name, body) for every top-level block, brace-matched - never a non-greedy regex."""
    t = "\n".join(l.split("//")[0] for l in t.splitlines())
    i, n = 0, len(t)
    while i < n:
        m = NAME_BRACE.search(t, i)
        if not m:
            return
        open_at = t.index("{", m.end() - 1)
        depth, j = 0, open_at
        while j < n:
            if t[j] == "{":
                depth += 1
            elif t[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            return
        yield m.group(1), t[open_at + 1:j]
        i = j + 1


def first_map(body):
    m = re.search(r"(?m)^\s*(?:clampmap\w*|map)\s+(\S+)", body)
    return m.group(1).lower() if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    SH = all_shader_text()
    print("  shader definitions visible: %d" % len(SH))

    # every models/ammo/* model the player anim files actually attach
    clips = set()
    for p in paks():
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            if not (n.lower().endswith(".txt") and "/player/" in n.lower()):
                continue
            try:
                t = z.read(n).decode("latin-1")
            except Exception:
                continue
            for m in re.finditer(r"attachmodel\s+(models/ammo/\S+\.tik)", t, re.I):
                clips.add(m.group(1).lower())
    print("  clip models attached by player anims: %d" % len(clips))

    # base gun tik -> {finish index: variant tik}, straight out of the loadout system's own table
    give = {}
    ls = open(os.path.join(MOD, "coop_mod", "loadoutskins.scr"), encoding="latin-1").read()
    for m in re.finditer(r'coop_skinGive\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', ls):
        give.setdefault(m.group(1).lower(), {})[int(m.group(2))] = m.group(3).lower()
    print("  guns with a finish table: %d" % len(give))

    def surfaces_of(tikrel):
        """surface -> shader, from the mod's copy if it has one, else the pak's."""
        local = os.path.join(MOD, tikrel.replace("/", os.sep))
        t = open(local, encoding="latin-1").read() if os.path.exists(local) else read_first(tikrel)
        if t is None:
            return None
        return {a.lower(): b for a, b in re.findall(r"(?m)^\s*surface\s+(\S+)\s+shader\s+(\S+)", t)}

    made, skipped = [], []
    for clip in sorted(clips):
        src = read_first(clip, retail_only=True)
        if src is None:
            skipped.append((clip, "tik not found in any pak"))
            continue
        rows = re.findall(r"(?m)^\s*surface\s+(\S+)\s+shader\s+(\S+)", src)
        if not rows:
            known = NO_SURFACE_ROW.get(clip)
            if not known:
                skipped.append((clip, "no surface row, and its skd name is not confirmed"))
                continue
            rows = [known]

        # resolve every surface via the gun that wears the same stock shader
        gun = CLIP_GUN.get(clip)
        if not gun:
            skipped.append((clip, "ordnance, not a magazine - no finish applies"))
            continue
        if gun not in give:
            skipped.append((clip, "gun %s has no finish table" % gun))
            continue
        gunsurfs = surfaces_of(gun) or {}

        plan, ok = [], True
        for surf, stock in rows:
            # the gun surface wearing the SAME stock shader is the one to follow through the variants
            # exact shader-name match first, then fall back to matching the TEXTURE it paints.
            # The fallback matters: some magazines carry their own shader NAME while painting the
            # gun's own sheet - It_W_Beretta_clip maps it_w_beretta.tga, the file the gun body
            # wears - so a name-only match would send them to the art pile for nothing.
            gunsurf = next((gs for gs, sh in gunsurfs.items() if sh.lower() == stock.lower()), None)
            if not gunsurf:
                want = first_map(SH.get(stock.lower()) or "")
                if want:
                    gunsurf = next((gs for gs, sh in gunsurfs.items()
                                    if first_map(SH.get(sh.lower()) or "") == want), None)
            if not gunsurf:
                # Last resort: this magazine is painted from a sheet the gun body never wears (the
                # shared m1clip, barclip, mauserammo). docs/tools/gen_clip_art.py bakes finishes for
                # exactly those and names them coop_skin_<gun>_<finish>_clip.
                stem = os.path.splitext(os.path.basename(gun))[0]
                picks = ["coop_skin_%s_%s_clip" % (stem, f) for f in FINISHES]
                if all(p in SH for p in picks):
                    plan.append((surf, stock, picks))
                    continue
                ok = False
                skipped.append((clip, "%s paints no surface with %s, and no _clip art exists"
                                % (os.path.basename(gun), stock)))
                break
            picks = []
            for idx in range(1, 8):
                var = give.get(gun, {}).get(idx)
                vs = surfaces_of(var) if var else None
                pick = vs.get(gunsurf) if vs else None
                if not pick:
                    ok = False
                    break
                picks.append(pick)
            if not ok:
                skipped.append((clip, "gun %s has no finish %d for surface %s" % (gun, idx, gunsurf)))
                break
            plan.append((surf, stock, picks))
        if not ok:
            continue

        assert 1 + len(FINISHES) <= MAX_SKINS, "skin list would exceed MAX_TIKI_SHADER"

        base = os.path.basename(clip)
        body_lines = []
        for surf, stock, picks in plan:
            body_lines.append("\tsurface %s shader %s" % (surf, stock))
            for f, pick in zip(FINISHES, picks):
                body_lines.append("\tsurface %s shader %s\t// %s" % (surf, pick, f))

        setup = re.search(r"setup\s*\{(.*?)\n\}", src, re.S)
        keep = []
        for l in (setup.group(1).splitlines() if setup else []):
            if re.match(r"\s*surface\s+", l):
                continue
            if l.strip():
                keep.append("\t" + l.strip())

        text = (
            "TIKI\n"
            "// HZM coop [2026-09-01, bug-2241] RELOAD MAGAZINE, per-finish skin list.\n"
            "// GENERATED by docs/tools/gen_clip_skins.py - do not hand-edit, re-run the generator.\n"
            "//\n"
            "// The retail copy of this file declares ONE shader row per surface, so numskins is 1 and\n"
            "// tr_model.cpp clamps every skin index back to 0 - which is why the magazine in your hand\n"
            "// stayed stock while the gun wore its finish. Each surface now carries 8 rows: index 0 is\n"
            "// the untouched retail shader, 1-7 are the finishes, in the order loadoutskins.scr declares\n"
            "// them. Entity::AttachModelEvent stamps the index onto the attached entity.\n"
            "//\n"
            "// Each finish shader is WHATEVER THE GUN'S OWN VARIANT TIK ASSIGNS to the surface wearing\n"
            "// this clip's stock shader, so the magazine can never drift from the gun. Matching on the map\n"
            "// TEXTURE was tried and is wrong: gold/chrome/blued tint the stock file while bloody and the\n"
            "// camos use their own art, so it succeeds for three finishes and fails for four.\n"
            "//\n"
            "// EIGHT IS THE CEILING. MAX_TIKI_SHADER is 8 and MAX_TIKI_LOAD_SHADERS must track it;\n"
            "// raising one alone corrupts memory and hangs the load (bug-2082). An eighth finish needs\n"
            "// both raised.\n"
            "setup\n{\n" + "\n".join(keep) + "\n" + "\n".join(body_lines) + "\n}\n"
        )
        anim = re.search(r"animations\s*\{.*?\n\}", src, re.S)
        if anim:
            text += "\n" + anim.group(0) + "\n"

        outp = os.path.join(OUTDIR, base)
        made.append((clip, len(plan), outp))
        if args.write:
            os.makedirs(OUTDIR, exist_ok=True)
            open(outp, "wb").write(text.encode("ascii"))

    print()
    print("  COVERED %d clip(s):" % len(made))
    for c, ns, _ in made:
        print("     %-42s %d surface(s) x 8 skins" % (c, ns))
    print()
    print("  SKIPPED %d clip(s):" % len(skipped))
    for c, why in skipped:
        print("     %-42s %s" % (c, why))
    if not args.write:
        print("\n  DRY RUN - pass --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
