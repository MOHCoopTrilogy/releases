"""Generate weapon skin variants: one tik + one shader set per gun per finish.

DESIGN (decided with the user 2026-08-17)

  unlock   a finish is earned account-wide by its own thematic challenge; a GUN accepts finishes
           once you have completed that gun's existing per-weapon kill challenge. 68 guns already
           have one, so 7 new challenges cover every combination instead of one per gun per finish.

  picker   never a new armory tile. Tile ids are baked into every pNN/tNN/wNN filename and every
           coop_loLkVNN cvar, and renumbering them is what caused bugs 755/759/772/787/803. The
           finish is a separate per-slot cvar, resolved against the base gun at spawn.

  art      HYBRID. Finishes that need detail placed by hand (blood, camo) are BAKED into a real
           texture. Finishes that are purely optical (gold, chrome, blued) are SHADER STAGES
           layered over the gun's existing diffuse, so they cost text instead of megabytes and a
           new gun gets them for free.

WHY A VARIANT IS A WHOLE WEAPON
  A live weapon's shader cannot be swapped at runtime, so every finish is its own weapon
  definition. That is only safe because of two things already in the engine:
    - the variant is named "<Base Gun> (<Finish>)", and CoopStripSkinSuffix resolves that back to
      the base gun, so a variant inherits the base gun's first-person hands AND its hand-dialled
      s_adsGunTune entry. A skin must never change how a weapon aims.
    - rank must be UNIQUE. A shared rank hides the gun on the weapon wheel, which is exactly what
      made the imported guns unreachable. Variants are allocated from a high band and asserted
      unique against every rank already in use.

SHADER SYNTAX is verified against renderergl1/tr_shader.c rather than assumed:
  rgbGen const / lightingSpherical, tcGen environment, blendFunc GL_DST_COLOR GL_ZERO, $whiteimage.
"""
import glob
import io
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
GOG = r"G:/GOG/Medal of Honor - Allied Assault War Chest"
WEAPONS = os.path.join(MOD, "models", "weapons")
SHADER_OUT = os.path.join(MOD, "scripts", "coop_skins.shader")
SKIN_TEX = os.path.join(MOD, "textures", "coop_skins")

# variant ranks live well above every stock rank (highest in use is 640)
RANK_BASE = 1000

# key, display name, kind, params
#   stage  -> tint multiplies the base diffuse, env adds a metal sheen through tcGen environment
#   bake   -> a real texture generated from the base by gen_weapon_skins.py's image functions
FINISHES = [
    ("gold",          "Gold",     "stage", {"tint": (1.00, 0.78, 0.30), "env": (0.40, 0.31, 0.12)}),
    ("chrome",        "Chrome",   "stage", {"tint": (0.88, 0.92, 0.98), "env": (0.55, 0.58, 0.64)}),
    ("blued",         "Blued",    "stage", {"tint": (0.44, 0.48, 0.64), "env": (0.10, 0.12, 0.20)}),
    ("bloody",        "Bloody",   "bake",  {}),
    ("camo_woodland", "Woodland", "bake",  {}),
    ("camo_winter",   "Winter",   "bake",  {}),
    ("camo_desert",   "Desert",   "bake",  {}),
]

ENVMAP = "textures/coop_skins/env_sheen.tga"   # shipped once, shared by every stage finish


# ---------------------------------------------------------------- shader / texture index -------
def build_index():
    shaders, pak_files = {}, set()

    def index_text(text):
        for m in re.finditer(r"(?m)^[ \t]*([^\s{}/][^\s{}]*)[ \t]*\r?\n[ \t]*\{", text):
            name = m.group(1).strip().lower()
            i = text.find("{", m.end() - 1)
            depth, j = 0, i
            while j < len(text):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            body = text[i:j]
            mm = (re.search(r"(?mi)^\s*(?:map|clampmap)\s+(\S+)", body)
                  or re.search(r"(?mi)^\s*qer_editorimage\s+(\S+)", body))
            if mm and name not in shaders:
                tex = mm.group(1).strip()
                if not tex.startswith("$"):
                    shaders[name] = tex

    for p in sorted(glob.glob(os.path.join(MOD, "scripts", "*.shader"))):
        index_text(io.open(p, encoding="latin-1", errors="replace").read())
    for f in sorted(glob.glob(GOG + "/main*/*.pk3")):
        try:
            z = zipfile.ZipFile(f)
        except Exception:
            continue
        for n in z.namelist():
            pak_files.add(n.lower().replace("\\", "/"))
            if n.lower().endswith(".shader"):
                try:
                    index_text(z.read(n).decode("latin-1", "replace"))
                except Exception:
                    pass
    for p in glob.glob(os.path.join(MOD, "**", "*"), recursive=True):
        if os.path.isfile(p):
            pak_files.add(os.path.relpath(p, MOD).lower().replace("\\", "/"))
    return shaders, pak_files


def texture_exists(pak_files, t):
    base = re.sub(r"\.(tga|jpg|jpeg|dds|png)$", "", t.lower().lstrip("/"))
    for ext in (".tga", ".jpg", ".jpeg", ".dds", ".png"):
        if base + ext in pak_files:
            return base + ext
    return None


# ---------------------------------------------------------------- weapon parsing ----------------
def weapon_tiks():
    out = []
    for p in sorted(glob.glob(os.path.join(WEAPONS, "*.tik"))):
        t = io.open(p, encoding="latin-1", errors="replace").read()
        if not re.search(r"(?mi)^\s*classname\s+Weapon", t):
            continue
        nm = re.search(r'(?mi)^\s*name\s+"([^"]+)"', t)
        if not nm or " (" in nm.group(1):
            continue          # already a variant - never make a variant of a variant
        out.append((p, t, nm.group(1)))
    return out


def shared_shader_names(weapons):
    """Shader names referenced by more than one weapon - sights, shared glass, shared furniture.

    These are deliberately NOT reskinned. They belong to more than one gun (our sights all point at
    the retail thompsite), so tinting one would be tinting all of them, and a hand-made variant we
    already ship - thompson_gold - leaves its `site` surface alone for exactly this reason.
    """
    seen = {}
    for _, t, _ in weapons:
        for _sn, sh in set(re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+(\S+)", t)):
            seen.setdefault(sh.lower(), set()).add(id(t))
    return {k for k, v in seen.items() if len(v) > 1}


def used_ranks():
    ranks = set()
    for p in glob.glob(os.path.join(WEAPONS, "*.tik")):
        t = io.open(p, encoding="latin-1", errors="replace").read()
        for m in re.finditer(r"(?mi)^\s*rank\s+(\d+)", t):
            ranks.add(int(m.group(1)))
    return ranks


# ---------------------------------------------------------------- emitters ---------------------
def shader_block(name, base_tex, kind, params):
    """One shader. A stage finish layers over base_tex; a bake finish just maps its own texture."""
    L = ["", name, "{", "\tqer_editorimage %s" % base_tex,
         "\t{", "\t\tmap %s" % base_tex, "\t\trgbGen lightingSpherical", "\t}"]
    if kind == "stage":
        r, g, b = params["tint"]
        # multiply the diffuse already in the framebuffer by a flat colour: src is $whiteimage
        # scaled by rgbGen const, dst is the base, and GL_DST_COLOR/GL_ZERO gives src*dst.
        L += ["\t{", "\t\tmap $whiteimage", "\t\tblendFunc GL_DST_COLOR GL_ZERO",
              "\t\trgbGen const ( %.2f %.2f %.2f )" % (r, g, b), "\t}"]
        er, eg, eb = params["env"]
        L += ["\t{", "\t\tmap %s" % ENVMAP, "\t\tblendFunc add", "\t\ttcGen environment",
              "\t\trgbGen const ( %.2f %.2f %.2f )" % (er, eg, eb), "\t}"]
    L.append("}")
    return "\n".join(L)


def variant_tik(base_text, base_name, display, rank, surf_map):
    """The base tik with ONLY name, rank and the reskinned surfaces changed.

    Everything else - every animation, every frame command, every tuning number - is copied
    verbatim, which is what guarantees a finish cannot change how the gun behaves.
    """
    t = base_text
    t = re.sub(r'(?mi)^(\s*name\s+)"[^"]+"',
               lambda m: '%s"%s (%s)"' % (m.group(1), base_name, display), t, count=1)
    t = re.sub(r"(?mi)^(\s*rank\s+)\d+\s+\d+",
               lambda m: "%s%d %d" % (m.group(1), rank, rank), t, count=1)

    def sub_surface(m):
        new = surf_map.get(m.group(2))
        return m.group(0) if new is None else "%s%s" % (m.group(1), new)

    t = re.sub(r"(?mi)^(\s*surface\s+\S+\s+shader\s+)(\S+)", sub_surface, t)
    return t


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "list"
    only = sys.argv[2] if len(sys.argv) > 2 else None

    shaders, pak_files = build_index()
    weapons = weapon_tiks()
    shared = shared_shader_names(weapons)
    taken = used_ranks()

    if only:
        weapons = [w for w in weapons if only.lower() in os.path.basename(w[0]).lower()]
        if not weapons:
            raise SystemExit("no weapon tik matches %r" % only)

    blocks, made, skipped = [], [], []
    rank = RANK_BASE
    for gi, (path, text, wname) in enumerate(sorted(weapons)):
        stem = os.path.splitext(os.path.basename(path))[0].lower()
        surfs = re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+(\S+)", text)

        # group the gun's own surfaces by the texture behind them - surfaces that share a texture
        # share a variant shader, which is what the hand-made thompson_gold does
        tex_of = {}
        for _sn, sh in surfs:
            if sh.lower() in shared:
                continue                       # sights and other shared parts stay stock
            tex = texture_exists(pak_files, shaders.get(sh.lower(), sh))
            if tex:
                tex_of[sh] = tex
        if not tex_of:
            skipped.append((stem, "no private textures to reskin"))
            continue

        order = sorted(set(tex_of.values()))
        for key, display, kind, params in FINISHES:
            while rank in taken:
                rank += 1
            taken.add(rank)

            surf_map, my_blocks = {}, []
            for sh, tex in tex_of.items():
                idx = order.index(tex)
                sname = "coop_skin_%s_%s" % (stem, key)
                if len(order) > 1:
                    sname += "_%d" % idx
                surf_map[sh] = sname
                src = tex
                if kind == "bake":
                    src = "textures/coop_skins/%s/%s_%s.jpg" % (
                        stem, os.path.splitext(os.path.basename(tex))[0], key)
                if sname not in [b[0] for b in my_blocks]:
                    my_blocks.append((sname, shader_block(sname, src, kind, params)))

            out_tik = os.path.join(WEAPONS, "%s_%s.tik" % (stem, key))
            if mode == "build":
                io.open(out_tik, "w", encoding="latin-1", newline="\r\n").write(
                    variant_tik(text, wname, display, rank, surf_map))
            blocks += [b[1] for b in my_blocks]
            made.append((os.path.basename(out_tik), wname, display, rank, kind, len(my_blocks)))
            rank += 1

    if mode == "build":
        hdr = io.open(SHADER_OUT, encoding="latin-1").read().split("\ncoop_skin_")[0]
        io.open(SHADER_OUT, "w", encoding="latin-1", newline="\r\n").write(
            hdr.rstrip() + "\n" + "\n".join(blocks) + "\n")

    for n, w, d, r, k, nb in made:
        print("  %-34s %-22s rank %-5d %-6s %d shader(s)" % (n, '"%s (%s)"' % (w, d), r, k, nb))
    for n, why in skipped:
        print("  SKIP %-28s %s" % (n, why))
    print()
    print("%s: %d variant(s) across %d gun(s), %d shader block(s)"
          % (mode, len(made), len(set(m[1] for m in made)), len(blocks)))
    if mode != "build":
        print("(dry run - pass 'build' to write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
