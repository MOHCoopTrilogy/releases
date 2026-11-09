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
MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")     # [v1.10.64] HZM_MOD: a worktree
GOG =r"G:/GOG/Medal of Honor - Allied Assault War Chest"
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
            # [v1.10.65 camo] the DIFFUSE: the first stage that is not an environment / gloss layer. Soares93's shaders open with
            # `map textures/effects/s93_gloss1.tga ... tcgen environmentmodel` and paint the gun in the SECOND stage - taking the
            # first map finished the gloss sheet instead of the gun (garand_silenced, springfield_unscoped)
            mm = None
            for st in re.findall(r"\{([^{}]*)\}", body):
                if re.search(r"(?i)tcgen\s+environment", st):
                    continue
                mm = re.search(r"(?mi)^\s*(?:map|clampmap)\s+([^$\s]\S*)", st)
                if mm:
                    break
            mm = (mm or re.search(r"(?mi)^\s*(?:map|clampmap)\s+(\S+)", body)
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
    for p, t, _ in weapons:
        # A gun and its own _lite twin are the SAME gun - they deliberately share a shader, and
        # counting that as "shared" skipped the Garand, Kar98, P38 and TT33 entirely, which are
        # exactly the guns people most want a finish on. Normalise the stem before comparing.
        stem = re.sub(r"_lite$", "", os.path.splitext(os.path.basename(p))[0].lower())
        for _sn, sh in set(re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+(\S+)", t)):
            seen.setdefault(sh.lower(), set()).add(stem)
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
              "\t\trgbGen const %.2f %.2f %.2f" % (r, g, b), "\t}"]
        er, eg, eb = params["env"]
        L += ["\t{", "\t\tmap %s" % ENVMAP, "\t\tblendFunc add", "\t\ttcGen environment",
              "\t\trgbGen const %.2f %.2f %.2f" % (er, eg, eb), "\t}"]
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

    def plan(text):
        """{shader: texture} this gun reskins, and the texture order that numbers its finish shaders (_0, _1 ...)"""
        surfs = re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+(\S+)", text)
        tex_of = {}
        for _sn, sh in surfs:
            if sh.lower() in shared:
                continue
            tex = texture_exists(pak_files, shaders.get(sh.lower(), sh))
            if tex:
                tex_of[sh] = tex
        if not tex_of:
            for _sn, sh in surfs:
                tex = texture_exists(pak_files, shaders.get(sh.lower(), sh))
                if tex:
                    tex_of[sh] = tex
        return tex_of, sorted(set(tex_of.values()))

    # [bug-10532] a SILENCED twin (tt33silenced -> tt33) carries the base gun's body. Its body surfaces use the base's
    # stock shaders, which the shared-shader rule above counts as "shared parts" and leaves stock - so the twin's finish
    # reskinned only the suppressor and the pistol stayed plain. A twin's surface whose stock shader the BASE reskins now
    # takes the base's finish shader for that texture (same texture, same skd surface names: no new shader, no new bake).
    stems = {os.path.splitext(os.path.basename(p))[0].lower(): tx for p, tx, _n in weapons}
    plans = {s: plan(tx) for s, tx in stems.items()}

    def twin_base(stem):
        b = re.sub(r"_?silenced$", "", stem)      # silenced twins only: a _lite twin already reskins its own (unshared) copy
        return b if b != stem and b in plans and plans[b][0] else None

    if only:
        weapons = [w for w in weapons if only.lower() in os.path.basename(w[0]).lower()]
        if not weapons:
            raise SystemExit("no weapon tik matches %r" % only)

    blocks, made, skipped = [], [], []
    rank = RANK_BASE
    for gi, (path, text, wname) in enumerate(sorted(weapons)):
        stem = os.path.splitext(os.path.basename(path))[0].lower()
        surfs = re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+(\S+)", text)
        base = twin_base(stem)
        base_tex, base_order = plans[base] if base else ({}, [])

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
            # Every surface this gun has is shared with another gun - the TT33 borrows the P38's
            # shader, for instance. Skipping the shared ones exists only to keep SIGHTS stock, and
            # a variant gets its own private shader anyway, so reskinning a shared surface harms
            # nobody. Better to reskin all of them than to give the gun no finishes at all, which
            # is what silently dropped the P38 and TT33.
            for _sn, sh in surfs:
                tex = texture_exists(pak_files, shaders.get(sh.lower(), sh))
                if tex:
                    tex_of[sh] = tex
        if not tex_of:
            skipped.append((stem, "no resolvable textures at all"))
            continue

        order = sorted(set(tex_of.values()))
        for key, display, kind, params in FINISHES:
            while rank in taken:
                rank += 1
            taken.add(rank)

            surf_map, my_blocks = {}, []
            for _sn, sh in surfs:
                if sh in base_tex:
                    bname = "coop_skin_%s_%s" % (base, key)
                    if len(base_order) > 1:
                        bname += "_%d" % base_order.index(base_tex[sh])
                    surf_map[sh] = bname
            for sh, tex in tex_of.items():
                if sh in surf_map:
                    continue
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
            if mode == "show":
                print("  %-34s %s" % (os.path.basename(out_tik), " ".join("%s=%s" % kv for kv in sorted(surf_map.items()))))
            rank += 1

    if mode == "build":
        hdr = io.open(SHADER_OUT, encoding="latin-1").read().split("\ncoop_skin_")[0]
        io.open(SHADER_OUT, "w", encoding="latin-1", newline="\r\n").write(
            hdr.rstrip() + "\n" + "\n".join(blocks) + "\n")
        # bug-3397: name every base texture exactly as the gun's own shader does (image cache is case-sensitive)
        import fix_skin_case
        fix_skin_case.main(write=True)

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


# ---------------------------------------------------------------- add ONE gun ------------------
def _put(path, text):
    """write with retries: a Windows indexer / AV lock answers EINVAL (Errno 22) for a moment"""
    import time
    for _i in range(20):
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            return
        except OSError:
            time.sleep(0.5)
    raise SystemExit("could not write " + path)


# [v1.10.65 camo] sheets that stay STOCK under the baked finishes (camo, blood), still tinted by gold / chrome / blued: the retail
# suppressor sheet colt45s2 (Colt / Garand / Beretta / Grease Gun / Mosin silenced) is near-black low-res noise, and a camo bake of
# it reads as a dark smear on the can. A blackened can on a painted gun is also what a field-painted weapon looked like.
BAKE_KEEP_STOCK = {"textures/models/weapons/colt/colt45s2"}

FIN_FID = {"gold": 1, "chrome": 2, "blued": 3, "bloody": 4, "camo_woodland": 5, "camo_winter": 6, "camo_desert": 7}


def _retail(rel):
    """[v1.10.65 camo] the game's own copy of a file the mod never ships: main < mainta < maintt, and inside a folder the
    last-sorting pak wins (the coop paks are skipped - gen_wpnfix_pak.carriers covers those)"""
    best = None
    for d in ("main", "mainta", "maintt"):
        for f in sorted(glob.glob(os.path.join(GOG, d, "*.pk3")), key=lambda s: os.path.basename(s).lower()):
            b = os.path.basename(f).lower()
            if "coop" in b or "co-op" in b or "hzm" in b:
                continue
            try:
                z = zipfile.ZipFile(f)
            except Exception:
                continue
            for n in z.namelist():
                if n.lower() == rel.lower():
                    best = ("%s/%s" % (d, os.path.basename(f)), z.read(n))
    return best


_CTX = {}


def _ctx(W):
    """the expensive indexes, built once per run and shared by every gun (ranks are allocated into the same set)"""
    if _CTX:
        return _CTX
    shaders, pak_files = build_index()
    # [v1.10.66 fg42hd] + the wpnfix pak's own shaders and files (a new mesh's sheet ships there)
    for p in glob.glob(os.path.join(W.SRC, "scripts", "*.shader")):
        t = io.open(p, encoding="latin-1", errors="replace").read()
        for m in re.finditer(r"(?ms)^([^\s{}/][^\s{}]*)\s*\r?\n\s*\{(.*?)^\}", t):
            mm = re.search(r"(?mi)^\s*map\s+([^$\s]\S*)", m.group(2))
            if mm:
                shaders[m.group(1).strip().lower()] = mm.group(1)
    for dp, _dn, fn in os.walk(W.SRC):
        for f in fn:
            pak_files.add(os.path.relpath(os.path.join(dp, f), W.SRC).lower().replace("\\", "/"))
    weapons = weapon_tiks()
    users = {}
    for p, t, _ in weapons:
        st = re.sub(r"_lite$", "", os.path.splitext(os.path.basename(p))[0].lower())
        for _sn, sh in set(re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+(\S+)", t)):
            users.setdefault(sh.lower(), set()).add(st)
    taken = used_ranks()
    tiks = {}
    for d in (os.path.join(ROOT, "docs", "tools", "assets", "fixes", "models", "weapons"), os.path.join(W.SRC, "models", "weapons")):
        for p in glob.glob(os.path.join(d, "*.tik")):
            tiks[os.path.basename(p).lower()] = io.open(p, encoding="latin-1", errors="replace").read()
    for f in os.listdir(W.BASE_MOD):
        if f.lower().endswith(".pk3"):
            try:
                z = zipfile.ZipFile(os.path.join(W.BASE_MOD, f))
            except zipfile.BadZipFile:
                continue
            for n in z.namelist():
                if n.lower().startswith("models/weapons/") and n.lower().endswith(".tik"):
                    tiks.setdefault("pak:" + f + ":" + n.lower(), z.read(n).decode("latin-1", "replace"))
    _CTX.update(shaders=shaders, pak_files=pak_files, users=users, taken=taken, other_tiks=tiks)
    return _CTX


def _existing_blocks():
    """{block name: lower(first map without extension)} of scripts/coop_skins.shader"""
    t = io.open(SHADER_OUT, encoding="latin-1").read()
    out = {}
    for m in re.finditer(r"(?ms)^(coop_skin_\S+)\s*\{(.*?)^\}", t):
        mm = re.search(r"(?m)^\s*map\s+(\S+)", m.group(2))
        if mm:
            out[m.group(1)] = re.sub(r"\.\w+$", "", mm.group(1).lower())
    return out


def add_gun(stem, write):
    """[v1.10.64 wpnfix2, v1.10.65 camo] give ONE gun the standard seven finishes without a full rebuild.

    `build` regenerates every variant tik from the MOD TREE's base tik and rewrites coop_skins.shader wholesale, which is wrong
    for a gun whose shipped tik is an out-of-band pak's newer copy (the Thompson Drum's winner is the stress pak's, with the
    open-bolt rows and the drum reload the mod tree's copy lacks): its finishes must be derived from the copy that LOADS, or a
    finish would play different animations than the base gun. So this mode:
      - derives the seven tiks from the load-order WINNER: the wpnfix pak's own source first (it sorts last), then the coop
        paks / mod tree (gen_wpnfix_pak.carriers), then the game's own paks for a gun the mod never ships (retail carbine, PPK...)
      - the tiks go to the mod tree only when the winner IS the mod tree; otherwise to the wpnfix pak's sources (pinned NEW)
      - a surface whose texture already has a finish shader (a silenced twin's body = its base gun's texture, a texture two guns
        share) REUSES that shader for the same finish - same look as the base gun, no second bake (generalises bug-10532)
      - a texture drawn by 3+ guns (sights: thompsite) stays stock, as in `build`, unless the gun has nothing else
      - picks ranks unique against every weapon tik in the mod tree, the fixes / wpnfix sources AND every coop pak
      - replaces only this gun's blocks in scripts/coop_skins.shader (appends them when new)
      - writes the coop_skinGive rows 1-7 into coop_mod/loadoutskins.scr (after the last finish row) and coop_skinN
    finalize() then fixes the map spellings, bakes, and moves the bakes into the wpnfix pak (mod-repo *.jpg is git-ignored).
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gen_wpnfix_pak as W
    import json
    rel = "models/weapons/%s.tik" % stem
    own = os.path.join(W.SRC, *rel.split("/"))
    if os.path.isfile(own):
        where, raw = "wpnfix source", open(own, "rb").read()
    else:
        car = W.carriers(rel)
        if car:
            where, raw = car[-1]
        else:
            r = _retail(rel)
            assert r, "%s is shipped nowhere" % rel
            where, raw = "retail " + r[0], r[1]
    text = raw.decode("latin-1").replace("\r\n", "\n")       # written back with CRLF: never \r\r\n
    wname = re.search(r'(?mi)^\s*name\s+"([^"]+)"', text).group(1)
    assert " (" not in wname, "a variant cannot get finishes"
    to_tree = where == "mod tree"
    out_dir = WEAPONS if to_tree else os.path.join(W.SRC, "models", "weapons")

    C = _ctx(W)
    shaders, pak_files, users, taken = C["shaders"], C["pak_files"], C["users"], C["taken"]
    mine = ["%s_%s.tik" % (stem, k) for k, _d, _k, _p in FINISHES]
    for name, t in C["other_tiks"].items():
        if name.split("/")[-1] in mine:
            continue                     # this gun's own earlier output: a re-run keeps its ranks
        for m in re.finditer(r"(?mi)^\s*rank\s+(\d+)", t):
            taken.add(int(m.group(1)))
    existing = _existing_blocks()
    by_tex = {}                          # (key, lower texture w/o ext) -> an existing finish block for it, not this gun's
    for name, tx in existing.items():
        mm = re.match(r"coop_skin_(.+?)_(gold|chrome|blued)(_\d+)?$", name)
        # [v1.10.66 fg42hd] this gun's OWN earlier blocks count too: the scoped FG 42 got a new mesh whose body takes the Irons'
        # sheet, but its charging handle still draws the old fg42 sheet, whose finishes (coop_skin_fg42_*) already ship - reuse them
        # (kept in place, not deleted and re-appended, bakes not redone) instead of regenerating identical blocks under new ranks
        if mm:
            for key, _d, _k, _p in FINISHES:
                cand = "coop_skin_%s_%s%s" % (mm.group(1), key, mm.group(3) or "")
                if cand in existing:
                    by_tex.setdefault((key, tx), cand)

    surfs = re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+(\S+)", text)
    tex_all = {}
    for _sn, sh in surfs:
        tex = texture_exists(pak_files, shaders.get(sh.lower(), sh))
        if tex:
            tex_all[sh] = tex
    assert tex_all, "no resolvable textures"
    sight = {sh for sh in tex_all if len(users.get(sh.lower(), set()) - {stem}) >= 2}
    # a shared texture that another gun already finishes (the P38's own P38.tga on the silenced P38) takes that finish too
    tex_of = {sh: t for sh, t in tex_all.items()
              if sh not in sight or (FINISHES[0][0], re.sub(r"\.\w+$", "", t.lower())) in by_tex} or dict(tex_all)
    order = sorted(set(t for sh, t in tex_of.items()
                       if (FINISHES[0][0], re.sub(r"\.\w+$", "", t.lower())) not in by_tex))

    rank = RANK_BASE
    blocks, tiks, rows, reused = [], [], [], set()
    prev = {}                            # [v1.10.66 fg42hd] a finish this gun already ships keeps its rank
    own_prev = [("models/weapons/%s_%s.tik" % (stem, k), (W.carriers("models/weapons/%s_%s.tik" % (stem, k)) or [(0, b"")])[-1][1]
                 .decode("latin-1", "replace")) for k, _d, _k, _p in FINISHES]          # the mod tree's / a pak's shipped copy
    for name, t in list(C["other_tiks"].items()) + own_prev:      # the wpnfix / fixes source first: it is what loads
        for key, _d, _k, _p in FINISHES:
            if name.split("/")[-1].lower() == "%s_%s.tik" % (stem, key):
                m = re.search(r"(?mi)^\s*rank\s+(\d+)", t)
                if m:
                    prev.setdefault(key, int(m.group(1)))
    for key, display, kind, params in FINISHES:
        if key in prev:
            rank_k = prev[key]
        else:
            while rank in taken or rank in prev.values():
                rank += 1
            rank_k = rank
        taken.add(rank_k)
        surf_map = {}
        for sh, tex in tex_of.items():
            if kind == "bake" and re.sub(r"\.\w+$", "", tex.lower()) in BAKE_KEEP_STOCK:
                continue                     # this sheet keeps its stock look under camo / blood (see BAKE_KEEP_STOCK)
            hit = by_tex.get((key, re.sub(r"\.\w+$", "", tex.lower())))
            if hit:
                surf_map[sh] = hit
                reused.add(hit)
                continue
            sname = "coop_skin_%s_%s" % (stem, key) + ("_%d" % order.index(tex) if len(order) > 1 else "")
            surf_map[sh] = sname
            src = tex if kind == "stage" else "textures/coop_skins/%s/%s_%s.jpg" % (
                stem, os.path.splitext(os.path.basename(tex))[0], key)
            if sname not in [b[0] for b in blocks]:
                blocks.append((sname, shader_block(sname, src, kind, params)))
        vt = variant_tik(text, wname, display, rank_k, surf_map)
        tiks.append(("%s_%s.tik" % (stem, key), vt))
        rows.append((FIN_FID[key], "models/weapons/%s_%s.tik" % (stem, key)))
        print("  %-36s rank %d  %s" % (tiks[-1][0], rank_k, " ".join("%s=%s" % kv for kv in sorted(surf_map.items()))))
    print("  base %s (%s) -> %s; %d new shader block(s), %d reused, stock: %s" % (
        rel, where, os.path.relpath(out_dir, ROOT), len(blocks), len(reused), sorted(set(tex_all) - set(tex_of)) or "-"))
    if not write:
        return 0

    for name, vt in tiks:
        io.open(os.path.join(out_dir, name), "w", encoding="latin-1", newline="\r\n").write(vt)
    if not to_tree:
        man = W.load_manifest()
        import hashlib
        for name, _vt in tiks:
            car = W.carriers("models/weapons/" + name)
            # [v1.10.66 fg42hd] a finish another pak already ships (the gun got a NEW mesh): override it, pinned to the copy it replaces
            man["models/weapons/" + name] = ({"base": car[-1][0], "base_md5": hashlib.md5(car[-1][1]).hexdigest()} if car
                                             else {"new": True})
        _put(W.MANIFEST, json.dumps(man, indent=2, sort_keys=True) + "\n")

    sh_txt = io.open(SHADER_OUT, encoding="latin-1", newline="").read()
    nl = "\r\n" if "\r\n" in sh_txt else "\n"
    sh_txt = re.sub(r"(?ms)\r?\n\r?\n(coop_skin_%s_(?:%s)(?:_\d+)?)\r?\n\{.*?^\}" % (
        re.escape(stem), "|".join(k for k, _d, _k, _p in FINISHES)),
        lambda m: m.group(0) if m.group(1) in reused else "", sh_txt)     # a reused own block stays where it is
    if blocks:
        sh_txt = sh_txt.rstrip() + nl + nl.join(b[1].replace("\n", nl) for b in blocks) + nl
    io.open(SHADER_OUT, "w", encoding="latin-1", newline="").write(sh_txt)

    ls_p = os.path.join(MOD, "coop_mod", "loadoutskins.scr")
    ls = io.open(ls_p, encoding="latin-1", newline="").read()
    give = rel.lower()
    have = re.findall(r'(?m)^\tlevel\.coop_skinGive\["%s"\]\[([1-7])\] = "([^"]*)"' % re.escape(give), ls)
    if sorted((int(f), v) for f, v in have) == sorted(rows):
        print("add %s: %d tiks, %d new shader blocks, loadoutskins rows unchanged" % (stem, len(tiks), len(blocks)))
        return 0                             # [v1.10.66 fg42hd] same rows already there: leave them where they are
    ls = re.sub(r'(?m)^\tlevel\.coop_skinGive\["%s"\]\[[1-7]\] = [^\r\n]*\r?\n' % re.escape(give), "", ls)
    last = list(re.finditer(r'(?m)^\tlevel\.coop_skinGive\["[^"]+"\]\[[1-7]\] = [^\r\n]*\r?\n', ls))[-1]
    ins = "".join('\tlevel.coop_skinGive["%s"][%d] = "%s"' % (give, f, v) + nl for f, v in rows)
    ls = ls[:last.end()] + ins + ls[last.end():]
    n = len(re.findall(r'(?m)^\tlevel\.coop_skinGive\["[^"]+"\]\[[1-7]\] = ', ls))
    ls = re.sub(r"level\.coop_skinN = \d+", "level.coop_skinN = %d" % n, ls, count=1)
    io.open(ls_p, "w", encoding="latin-1", newline="").write(ls)
    print("add %s: %d tiks, %d new shader blocks, coop_skinN %d" % (stem, len(tiks), len(blocks), n))
    return 0


def _shipped_bakers():
    """the SHIPPED baked-finish functions: gen_weapon_skins.py's camo() / bloody() with the palettes the committed bake_skins.py
    uses, so a new gun's camo matches the 54 guns already in the release (the CC0 rework in docs/proposals/weapon_finishes_2026-11-01
    is staged, not shipped; when it ships, re-bake everything together)"""
    g = {"__file__": os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_weapon_skins.py"), "__name__": "gws"}
    src = io.open(g["__file__"], encoding="utf-8").read()
    exec(src.split("VARIANTS = [")[0], g)
    return g["from_paks"], {
        "bloody":        lambda im: g["bloody"](im),
        "camo_woodland": lambda im: g["camo"](im, [(58, 66, 40), (86, 92, 56), (44, 40, 30), (104, 98, 66)]),
        "camo_winter":   lambda im: g["camo"](im, [(178, 182, 186), (140, 146, 152), (96, 102, 108), (206, 210, 213)], seed=11),
        "camo_desert":   lambda im: g["camo"](im, [(176, 150, 104), (146, 120, 78), (198, 178, 138), (118, 98, 66)], seed=5),
    }


def finalize(stems):
    """after add_gun: map spellings (bug-3397), then bake every baked block a gun owns straight into the wpnfix pak's sources
    (the mod repo ignores *.jpg). A baked block's base = the map of its gold twin. A sheet under 256 px (a 100 px suppressor,
    a 128 px belt) is baked at 256 px: camo blobs and blood are drawn in output pixels and came out as a few big blocks."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gen_wpnfix_pak as W
    import json
    import numpy as np
    from PIL import Image
    import fix_skin_case
    fix_skin_case.main(write=True)
    from_paks, baked = _shipped_bakers()
    t = io.open(SHADER_OUT, encoding="latin-1").read()
    blocks = {m.group(1): re.findall(r"(?m)^\s*map\s+(\S+)", m.group(2))
              for m in re.finditer(r"(?ms)^(coop_skin_\S+)\s*\{(.*?)^\}", t)}
    man = W.load_manifest()
    made, missing = 0, []
    for stem in stems:
        for name, maps in sorted(blocks.items()):
            mm = re.match(r"coop_skin_%s_(bloody|camo_woodland|camo_winter|camo_desert)(_\d+)?$" % re.escape(stem), name)
            if not mm:
                continue
            gold = blocks.get("coop_skin_%s_gold%s" % (stem, mm.group(2) or ""))
            assert gold, "no gold twin for " + name
            out_rel = maps[0]
            if out_rel not in man and W.carriers(out_rel):
                continue                     # [v1.10.66 fg42hd] a bake another pak / the mod tree already ships: a reused finish
            base = gold[0]
            img = None
            for cand in [base] + [re.sub(r"\.\w+$", e, base) for e in (".tga", ".jpg", ".dds", ".png")]:
                own = os.path.join(W.SRC, *cand.split("/"))          # [fg42hd] a sheet the wpnfix pak itself ships
                img = (Image.open(own).convert("RGB") if os.path.isfile(own) else from_paks(cand)) or img
                if img is not None:
                    break
            if img is None:
                missing.append(base)
                continue
            if min(img.size) < 256:
                k = 256.0 / min(img.size)
                img = img.resize((int(round(img.size[0] * k)), int(round(img.size[1] * k))), Image.LANCZOS)
            arr = np.clip(baked[mm.group(1)](img), 0, 255).astype(np.uint8)
            dst = os.path.join(W.SRC, *out_rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            Image.fromarray(arr).save(dst, quality=92)
            man[out_rel] = {"new": True}
            made += 1
    _put(W.MANIFEST, json.dumps(man, indent=2, sort_keys=True) + "\n")
    print("finalize: %d gun(s), %d baked texture(s)%s" % (len(stems), made, ", MISSING " + ", ".join(missing) if missing else ""))
    return 1 if missing else 0


# ---------------------------------------------------------------- finishes2 (fids 40+): ingest the out-of-band build -----
# [v1.10.68 finishes2] The second finish set (8 paint / camo coats + Airborne 101st, and 4 shader-layered finishes) is BUILT outside
# the mod tree (docs/proposals/finishes2_2026-11-09/tools: fs2_build.py, fs2_finish2.py) into its own pak,
# zzzzzzzzzz_coop_finishes_hd.pk3: variant tiks, masks, coats, tiles and scripts/coop_finishes_hd.shader all live IN THE PAK (190 MB
# would re-hash the assets pak on every change; the updater re-downloads this one only when it changes). The mod tree gets only:
#   coop_mod/loadoutskins.scr  one marked block at the end of skin_init: coop_skinFinName / Stat [40..52], coop_skinGive[give][40..52]
#   scripts/hzm_finish_decals.txt  the finish decal presets for the Customize bench (decals/manifest.json finish_presets)
#     python docs/tools/gen_skins.py fs2 [write]     ingest (dry run without 'write')
#     python docs/tools/gen_skins.py check           the block + decal file match the build, and the pak is whole (exit 1 = not)
FS2_BEGIN = "\t//---- finishes2 (fids 40+) GENERATED by docs/tools/gen_skins.py fs2 - DO NOT EDIT BY HAND"
FS2_END = "\t//---- finishes2 end"
DECALS_TXT = os.path.join(MOD, "scripts", "hzm_finish_decals.txt")
DECAL_MANIFEST = os.path.join(ROOT, "docs", "proposals", "finishes2_2026-11-09", "decals", "manifest.json")
SPOT = {"stock_R": "stock_r", "stock_L": "stock_l", "receiver_L": "receiver_l", "receiver_R": "receiver_r", "grip_R": "grip",
        "grip_L": "grip", "butt": "butt"}


def _f2():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import finishes2
    return finishes2


def fs2_block(nl):
    F2 = _f2()
    tab = F2.table()
    rows = F2.build_rows()
    keys = {r["key"]: r for r in tab}
    L = [FS2_BEGIN, "\tlevel.coop_skinFs2N = %d" % len(rows), "\tlevel.coop_fs2FidN = %d" % len(tab)]
    L += ["\tlevel.coop_fs2Fid[%d] = %d" % (i, r["fid"]) for i, r in enumerate(tab)]   # the Armory's second chip row, in order
    for r in tab:
        L += ['\tlevel.coop_skinFinStat[%d] = "finish_%s"' % (r["fid"], r["key"]), '\tlevel.coop_skinFinName[%d] = "%s"' % (r["fid"], r["name"])]
    for give, fid, key, var, _rank in sorted(rows, key=lambda x: (x[0].lower(), x[1])):
        assert key in keys and keys[key]["fid"] == fid, "build row %s %d %s does not match finishes2.tsv" % (give, fid, key)
        L.append('\tlevel.coop_skinGive["%s"][%d] = "%s"' % (give.lower(), fid, var))
    L.append(FS2_END)
    return nl.join(L) + nl


def fs2_decals_txt():
    import json
    m = json.load(open(DECAL_MANIFEST, encoding="utf-8"))
    names = {d["name"] for d in m["decals"]}
    pre, spots = m["finish_presets"], m["preset_spots"]
    shipped = {r["key"] for r in _f2().table()}
    L = ["// GENERATED by docs/tools/gen_skins.py fs2 from docs/proposals/finishes2_2026-11-09/decals/manifest.json (finish_presets,",
         "// preset_spots) - the default decals of the finishes2 finishes, drawn by the Customize bench (engrave PLAN, 'Decal API').",
         "// decal <finish = variant tik suffix> <decal name> <spot> <size, - = the manifest's recommended size>",
         "// One line per spot in preset_spots order (rifle / sniper / heavy: stock_r then receiver_l, smg / pistol: grip then",
         "// receiver_l); the bench's spot fallback picks the first spot a gun has. CAPTURED is not listed: its decal depends on",
         "// the gun's side (captured_german_gun = souvenir tag, captured_allied_gun = waffenamt stamp), which this format cannot say."]
    order = []
    for cls in ("rifle", "smg"):
        for s in spots[cls]:
            if SPOT[s] not in order:
                order.append(SPOT[s])
    for fin in sorted(pre):
        if fin not in shipped:
            continue                    # ffi / captured_*: designed, not shipped as a finish (or side-dependent, see above)
        assert pre[fin] in names, "finish_presets.%s = %s is not a decal in the manifest" % (fin, pre[fin])
        for sp in order:
            L.append("decal %s %s %s -" % (fin, pre[fin], sp))
    return "\r\n".join(L) + "\r\n"


def fs2_splice(text):
    nl = "\r\n" if "\r\n" in text else "\n"
    t = re.sub(r"(?s)" + re.escape(FS2_BEGIN) + r"\r?\n.*?" + re.escape(FS2_END) + r"\r?\n", "", text)
    m = list(re.finditer(r"(?m)^\}end\r?$", t))
    assert m, "loadoutskins.scr: no closing }end"
    i = m[-1].start()
    return t[:i] + fs2_block(nl) + t[i:]


def fs2_pak_audit():
    """the pak is whole: every row's tik is in it, names / ranks / shaders resolve, no rank collides with any other weapon tik"""
    F2 = _f2()
    import gen_wpnfix_pak as W
    errs = []
    pak = F2.pak_path(W.BASE_MOD)
    if not os.path.exists(pak):
        return ["pak not found: %s" % pak], pak
    z, idx = F2.pak_index(pak)
    sh_txt = z.read(idx["scripts/coop_finishes_hd.shader"]).decode("latin-1")
    defined = set(m.lower() for m in re.findall(r"(?m)^(coop_fs2_\S+)\r?\n\{", sh_txt))
    for m in re.finditer(r"(?m)^\s*map\s+(textures/coop_finishes_hd/\S+)", sh_txt):
        if m.group(1).lower() not in idx:
            errs.append("shader maps a missing texture: " + m.group(1))
    tab = F2.by_fid()
    ranks = {}
    for give, fid, key, var, rank in F2.build_rows():
        n = idx.get(var.lower())
        if not n:
            errs.append("variant not in the pak: " + var)
            continue
        t = z.read(n).decode("latin-1")
        nm = re.search(r'(?mi)^\s*name\s+"([^"]+)"', t)
        if not nm or not nm.group(1).endswith(")") or " (" not in nm.group(1):
            errs.append("%s: name is not '<Base> (<Finish>)'" % var)
        rk = re.search(r"(?mi)^\s*rank\s+(\d+)\s+(\d+)", t)
        if not rk or int(rk.group(1)) != rank:
            errs.append("%s: rank %s, rows.tsv says %d" % (var, rk.group(1) if rk else None, rank))
        for sh in re.findall(r"(?mi)^\s*surface\s+\S+\s+shader\s+(coop_fs2_\S+)", t):
            if sh.lower() not in defined:
                errs.append("%s: shader %s is not defined" % (var, sh))
        if rank in ranks:
            errs.append("rank %d twice: %s %s" % (rank, ranks[rank], var))
        ranks[rank] = var
        if fid not in tab:
            errs.append("%s: fid %d not in finishes2.tsv" % (var, fid))
    # every OTHER weapon tik that can load: the mod tree, the fixes / wpnfix sources, every other coop pak in the base checkout
    others = {}
    for d in (WEAPONS, os.path.join(ROOT, "docs", "tools", "assets", "fixes", "models", "weapons"), os.path.join(W.SRC, "models", "weapons")):
        for p in glob.glob(os.path.join(d, "*.tik")):
            others["models/weapons/" + os.path.basename(p).lower()] = io.open(p, encoding="latin-1", errors="replace").read()
    if os.path.isdir(W.BASE_MOD):
        for f in os.listdir(W.BASE_MOD):
            # the mod's own built paks (zzzzzz_co-op_hzm_mod_*) carry the mod tree, read above; a pak being written is skipped
            if f.lower().endswith(".pk3") and f != F2.PAK_NAME and not f.lower().startswith("zzzzzz_co-op_hzm_mod_"):
                try:
                    zz = zipfile.ZipFile(os.path.join(W.BASE_MOD, f))
                except (zipfile.BadZipFile, OSError):
                    continue
                for n in zz.namelist():
                    if n.lower().startswith("models/weapons/") and n.lower().endswith(".tik"):
                        others.setdefault(n.lower(), zz.read(n).decode("latin-1", "replace"))
    for n, t in others.items():
        if "_fs2_" in n:
            continue
        for m in re.finditer(r"(?mi)^\s*rank\s+(\d+)", t):
            if int(m.group(1)) in ranks:
                errs.append("rank %s of %s collides with %s" % (m.group(1), n, ranks[int(m.group(1))]))
    return errs, pak


def fs2(write, check_only=False):
    F2 = _f2()
    ls_p = os.path.join(MOD, "coop_mod", "loadoutskins.scr")
    cur = io.open(ls_p, encoding="latin-1", newline="").read()
    new = fs2_splice(cur)
    dec = fs2_decals_txt()
    dec_cur = io.open(DECALS_TXT, encoding="latin-1", newline="").read() if os.path.exists(DECALS_TXT) else None
    errs, pak = fs2_pak_audit()
    rows = F2.build_rows()
    print("finishes2: %d rows (%d guns x %d finishes), pak %s" % (len(rows), len({r[0] for r in rows}), len({r[1] for r in rows}), pak))
    print("  loadoutskins.scr block : %s" % ("in sync" if new == cur else "DIFFERS"))
    print("  hzm_finish_decals.txt  : %s" % ("in sync" if dec == dec_cur else "DIFFERS"))
    for e in errs[:20]:
        print("  PAK: " + e)
    if len(errs) > 20:
        print("  ... %d more" % (len(errs) - 20))
    if check_only:
        ok = new == cur and dec == dec_cur and not errs
        print("  -> %s" % ("EXACT" if ok else "DRIFT / BROKEN - run: python docs/tools/gen_skins.py fs2 write"))
        return 0 if ok else 1
    if errs:
        print("refusing to write: the pak is not whole")
        return 1
    if write:
        io.open(ls_p, "w", encoding="latin-1", newline="").write(new)
        io.open(DECALS_TXT, "w", encoding="latin-1", newline="").write(dec)
        print("wrote %s, %s" % (os.path.relpath(ls_p, MOD), os.path.relpath(DECALS_TXT, MOD)))
    else:
        print("(dry run - pass 'fs2 write')")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "add":
        # add <stem>[,<stem>...] [write]
        stems = [s.lower() for s in sys.argv[2].split(",") if s]
        wr = "write" in sys.argv[3:]
        for s in stems:
            add_gun(s, wr)
        if not wr:
            print("(dry run - pass 'add <stems> write')")
            sys.exit(0)
        sys.exit(finalize(stems))
    if len(sys.argv) > 1 and sys.argv[1] == "fs2":
        sys.exit(fs2("write" in sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        sys.exit(fs2(False, check_only=True))
    sys.exit(main())
