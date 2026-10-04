"""
audit_actor_surfaces.py - does every skin of every AI character surface actually DRAW?

WHY THIS EXISTS
---------------
User, v1.10.9: "sometimes invisible enemies where you can only see their head and arms... they
appear randomly on several maps."

A character surface draws nothing - not the grey/white default checker, NOTHING - when its shader
is DEFINED in scripts/*.shader but a stage-0 image does not load. Both renderers do the same thing
(tr_shader.c ParseStage -> "R_FindImageFile could not find" -> return qfalse; R_FindShader then
FinishShader()s with zero active stages). An UNDEFINED shader is different: it falls back to an
implicit <name>.tga, and if that is missing too it becomes the visible default shader.

Every AI body surface carries a gore skin ladder (skin 0 clean, 1-3 = _blood1/2/3), and the engine
switches skins per surface as the actor takes damage (sentient.cpp CoopGoreUpdateSkinTier). So a
broken gore-tier shader makes the torso and legs vanish the first time an enemy is wounded, while
the head (exempt/padded) and hands keep drawing: exactly the reported shape, and "random" because it
only shows on enemies that were hit but not killed.

WHAT IT DOES
------------
1. Builds the real virtual filesystem: main < mainta < maintt, paks sorted case-insensitively
   within a dir, a later pak wins (files.cpp paksort). The three hzm_mod paks are replaced by this
   repo's working tree (they are built from it), at the same priority slot.
2. Loads shader text exactly as ScanAndLoadShaderFiles does: one copy of each scripts/*.shader
   (top-priority pak), and on a duplicate shader NAME the highest-priority file wins.
3. Collects every models/human/**.tik (winning copy), follows $include, and lists each surface's
   skin shaders in order (the order IS the gore tier index).
4. Resolves every stage image of every skin shader under each renderer's real loader rules:
     gl1 (tr_image.c R_LoadImage): .tga/.jpg names try .dds (S3TC) -> .jpg -> .tga; others exact.
     gl2 (tr_image.c R_LoadImage): .dds first, .tga tries .jpg, then exact, then png/tga/jpg/...
   A .dds that is the ONLY source is header-checked (DXT1/3/5 load in both; anything else is
   reported, since gl1 then has nothing to fall back to).

Exit 1 if any skin on any AI surface is INVISIBLE in either renderer, so this works as a
regression check.

Usage:
  python docs/tools/audit_actor_surfaces.py              # live install G:\\mohaa-gl2
  python docs/tools/audit_actor_surfaces.py --base "G:\\GOG\\Medal of Honor - Allied Assault War Chest"
  python docs/tools/audit_actor_surfaces.py --retail-only   # main/mainta/maintt retail paks + mod only
  python docs/tools/audit_actor_surfaces.py --verbose       # list every finding, incl. degraded
"""

import argparse
import os
import re
import struct
import sys
import zipfile
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
DEFAULT_BASE = r"G:\mohaa-gl2"
GAME_DIRS = ("main", "mainta", "maintt")
MOD_PAKS = ("zzzzzz_co-op_hzm_mod_assets_snd.pk3", "zzzzzz_co-op_hzm_mod_assets_tex.pk3",
            "zzzzzz_co-op_hzm_mod_code.pk3", "zzzzzz_co-op_hzm_mod_mohaa.pk3")
RETAIL_RE = re.compile(r"^pak\d+\w*\.pk3$", re.I)
# build.ps1 never packs these repo paths
REPO_SKIP = ("_terrain_pack", ".git", "docs", "build_out")

AI_PREFIX = "models/human/"
# Retail defects reported but not failed on: (shader, tik). faces.shader `hand` maps
# textures/models/human/hand.tga, which no retail or mod pak ships; only the e3l4 frogman uses it.
KNOWN_RETAIL = {("hand", "models/human/german_misc_frogman.tik")}


# ---------------------------------------------------------------- VFS
class VFS:
    def __init__(self):
        self.layers = []          # low -> high: (label, zipfile|None for dir, root|None)
        self.index = {}           # lower path -> (layer_no, real name)

    def add_pak(self, path):
        try:
            z = zipfile.ZipFile(path)
        except Exception as e:
            print("WARN cannot open %s: %s" % (path, e))
            return
        n = len(self.layers)
        self.layers.append((os.path.basename(path), z, None))
        for name in z.namelist():
            if not name.endswith("/"):
                self.index[name.lower().replace("\\", "/")] = (n, name)

    def add_dir(self, label, root):
        n = len(self.layers)
        self.layers.append((label, None, root))
        for dp, dns, fns in os.walk(root):
            rel_dp = os.path.relpath(dp, root).replace(os.sep, "/")
            if rel_dp == ".":
                dns[:] = [d for d in dns if d not in REPO_SKIP]
                rel_dp = ""
            for f in fns:
                if f.lower().endswith((".pk3", ".bak")):
                    continue
                rel = (rel_dp + "/" + f) if rel_dp else f
                self.index[rel.lower()] = (n, rel)

    def has(self, path):
        return path.lower().replace("\\", "/") in self.index

    def where(self, path):
        e = self.index.get(path.lower().replace("\\", "/"))
        return self.layers[e[0]][0] if e else None

    def read(self, path, limit=None):
        e = self.index.get(path.lower().replace("\\", "/"))
        if not e:
            return None
        label, z, root = self.layers[e[0]]
        if z is not None:
            if limit:
                with z.open(e[1]) as fh:
                    return fh.read(limit)
            return z.read(e[1])
        with open(os.path.join(root, e[1].replace("/", os.sep)), "rb") as fh:
            return fh.read(limit) if limit else fh.read()

    def layer_of(self, path):
        e = self.index.get(path.lower().replace("\\", "/"))
        return e[0] if e else -1

    def list(self, prefix, ext):
        prefix = prefix.lower()
        return sorted(p for p in self.index if p.startswith(prefix) and p.endswith(ext))


def build_vfs(base, retail_only):
    vfs = VFS()
    for d in GAME_DIRS:
        gd = os.path.join(base, d)
        if not os.path.isdir(gd):
            continue
        paks = sorted((f for f in os.listdir(gd) if f.lower().endswith(".pk3")), key=str.lower)
        mod_slot_done = False
        for f in paks:
            if f.lower() in MOD_PAKS:
                if not mod_slot_done and d == "maintt":
                    vfs.add_dir("repo:hzm-mohaa-coop-mod", MOD)
                    mod_slot_done = True
                continue
            if retail_only and not RETAIL_RE.match(f) and f.lower() != "pak0.pk3":
                continue
            vfs.add_pak(os.path.join(gd, f))
        if d == "maintt" and not mod_slot_done:
            vfs.add_dir("repo:hzm-mohaa-coop-mod", MOD)
    return vfs


# ---------------------------------------------------------------- shaders
COMMENT_RE = re.compile(r'"[^"\n]*"|//[^\n]*|/\*.*?\*/', re.S)


def strip_comments(text):
    """Left-to-right like the engine's tokenizer. Stripping /* */ first is WRONG for TIKIs: the
    retail banner `//*** weapon equipment` opens a fake block comment that eats every case block."""
    def sub(m):
        s = m.group(0)
        if s.startswith('"'):
            return s
        return "\n" * s.count("\n") if s.startswith("/*") else ""
    return COMMENT_RE.sub(sub, text)


TOKEN_RE = re.compile(r'"[^"]*"|\{|\}|[^\s{}"]+')


def parse_shader_file(text):
    """Yield (name, body_lines) - body_lines = list of (depth, [tokens])."""
    text = strip_comments(text)
    out = []
    lines = text.splitlines()
    i, n = 0, len(lines)
    name, depth, body = None, 0, []
    for line in lines:
        toks = [t.strip('"') if t not in "{}" else t for t in TOKEN_RE.findall(line)]
        cur = []
        for t in toks:
            if t == "{":
                if cur:
                    if depth == 0:
                        name = cur[-1]
                    else:
                        body.append((depth, cur))
                    cur = []
                depth += 1
                if depth == 2:
                    body.append((2, ["{STAGE"]))
            elif t == "}":
                if cur:
                    if depth > 0:
                        body.append((depth, cur))
                    cur = []
                depth -= 1
                if depth <= 0:
                    depth = 0
                    if name:
                        out.append((name, body))
                    name, body = None, []
            else:
                cur.append(t)
        if cur:
            if depth == 0:
                name = cur[-1]
            else:
                body.append((depth, cur))
    return out


def load_shaders(vfs):
    """name.lower() -> (file, layer_label, stages[list of image names per stage], nodraw)."""
    files = {}
    for p in vfs.list("scripts/", ".shader"):
        files[p] = vfs.layer_of(p)
    defs = {}
    # ScanAndLoadShaderFiles: highest-priority file ends up LAST in the text and wins a duplicate
    # name, so process low -> high and let later overwrite.
    for p in sorted(files, key=lambda k: files[k]):
        try:
            text = vfs.read(p).decode("latin-1")
        except Exception:
            continue
        for name, body in parse_shader_file(text):
            stages, nodraw, cur = [], False, None
            for depth, toks in body:
                if toks == ["{STAGE"]:
                    cur = []
                    stages.append(cur)
                    continue
                kw = toks[0].lower()
                if depth == 1:
                    if kw == "surfaceparm" and len(toks) > 1 and toks[1].lower() == "nodraw":
                        nodraw = True
                    continue
                if cur is None:
                    continue
                if kw in ("map", "clampmap", "clampmapx", "clampmapy") and len(toks) > 1:
                    cur.append(toks[1])
                elif kw in ("animmap", "animmaponce") and len(toks) > 2:
                    cur.extend(toks[2:])
                elif kw == "animmapphase" and len(toks) > 3:
                    cur.extend(toks[3:])
            defs[name.lower()] = (p, vfs.layers[files[p]][0], stages, nodraw)
    return defs


# ---------------------------------------------------------------- images
DDS_OK = (b"DXT1", b"DXT3", b"DXT5")


def dds_fourcc(vfs, path):
    head = vfs.read(path, 128)
    if not head or head[:4] != b"DDS ":
        return b"BAD!"
    flags = struct.unpack("<I", head[80:84])[0]
    if flags & 0x4:
        return head[84:88]
    return b"RGB "  # uncompressed: loaded by both


def resolve_image(vfs, name, rend):
    """Return the file that would load, or None. rend in gl1, gl2."""
    if name.startswith("$") or name.startswith("*"):
        return "<builtin>"
    nm = name.replace("\\", "/")
    stem, ext = os.path.splitext(nm)
    ext = ext.lower()
    cands = []
    if rend == "gl1":
        if ext in (".tga", ".jpg"):
            cands = [stem + ".dds", stem + ".jpg", stem + ".tga"]
        elif ext == ".dds":
            cands = [nm]
        else:
            cands = [stem + ".dds", nm]
    else:
        cands = [stem + ".dds"]
        if ext == ".tga":
            cands.append(stem + ".jpg")
        cands.append(nm)
        cands += [stem + e for e in (".png", ".tga", ".jpg", ".jpeg", ".pcx", ".bmp")]
    for c in cands:
        if vfs.has(c):
            if c.lower().endswith(".dds"):
                fc = dds_fourcc(vfs, c)
                if fc not in DDS_OK and fc != b"RGB ":
                    continue  # undecodable -> loader falls through to the next candidate
            return c
    return None


def shader_status(vfs, shaders, sname, rend, cache):
    """-> (status, detail). status in OK, NODRAW, INVISIBLE, DEGRADED, CHECKER."""
    key = (sname.lower(), rend)
    if key in cache:
        return cache[key]
    d = shaders.get(sname.lower())
    if d is None:
        img = resolve_image(vfs, sname if os.path.splitext(sname)[1] else sname + ".tga", rend)
        r = ("OK", "implicit " + img) if img else ("CHECKER", "undefined shader, no image")
    else:
        sfile, slayer, stages, nodraw = d
        if nodraw:
            r = ("NODRAW", "surfaceparm nodraw in %s [%s]" % (sfile, slayer))
        elif not stages:
            r = ("INVISIBLE", "no stages in %s [%s]" % (sfile, slayer))
        else:
            r = ("OK", "%s [%s]" % (sfile, slayer))
            for si, imgs in enumerate(stages):
                miss = [i for i in imgs if not resolve_image(vfs, i, rend)]
                if miss:
                    st = "INVISIBLE" if si == 0 else "DEGRADED"
                    r = (st, "stage %d missing %s (shader in %s [%s])" % (si, ",".join(miss), sfile, slayer))
                    break
    cache[key] = r
    return r


# ---------------------------------------------------------------- TIKIs
SURF_RE = re.compile(r"^\s*surface\s+(\S+)\s+(.*)$", re.I)
SHADER_RE = re.compile(r"\bshader\s+(\S+)", re.I)
INCLUDE_RE = re.compile(r"^\s*\$include\s+(\S+)", re.I | re.M)
DEFINE_RE = re.compile(r"^\s*\$define\s+(\S+)\s+(\S+)", re.I | re.M)


def tiki_text(vfs, path, seen=None):
    seen = seen or set()
    if path.lower() in seen:
        return ""
    seen.add(path.lower())
    raw = vfs.read(path)
    if raw is None:
        return ""
    t = strip_comments(raw.decode("latin-1"))
    out = [t]
    for inc in INCLUDE_RE.findall(t):
        out.append(tiki_text(vfs, inc.strip('"'), seen))
    return "\n".join(out)


def tiki_surfaces(text):
    defs = dict((k, v) for k, v in DEFINE_RE.findall(text))
    for k, v in defs.items():
        text = text.replace("$" + k + "$", v)
    per = defaultdict(list)
    flags = defaultdict(set)
    for line in text.splitlines():
        m = SURF_RE.match(line)
        if not m:
            continue
        name = m.group(1).strip('"').lower()
        rest = m.group(2)
        for s in SHADER_RE.findall(rest):
            per[name].append(s.strip('"'))
        for fl in re.findall(r"([+-]\w+)", rest):
            flags[name].add(fl.lower())
    if "all" in per:
        extra = per.pop("all")
        for k in per:
            per[k] = per[k] + extra
        if not per:
            per["all"] = extra
    return per, flags


# ---------------------------------------------------------------- weapon keys (bug-3306)
# The REAL cause of the v1.10.9 report. Actor::EventGiveWeapon (`gun X`, `.weapon = X`) stores X as
# the loadout key and Actor::setModel rebuilds the composite "weapon|X|headmodel|..|<tik>". Most AI
# tiks build the body ONLY inside `case weapon "<name>"` blocks; TIKI_LoadSetupCase skips a block
# whose value does not match (Q_stricmp, no default), so a key that matches nothing compiles head +
# hands and no body. The shader audit above can never see this - every surface it lists is fine.
#
# Every give in coop_mod/*.scr must therefore be either coop_actorArm (aihandler.scr - weapon.scr
# without the rebuild) or a literal verified here to be a case key of every model that site spawns.
CASE_RE = re.compile(r"(?im)^\s*case\s+weapon\s+([^{\n]+)")
INITW_RE = re.compile(r'(?im)^\s*weapon\s+"?([^"\n]+?)"?\s*$')
_TGT = r'(?:self|local\.\w+(?:\.\w+)?|level\.\w+|group\.\w+|\$\w+)'
GIVE_RE = re.compile(r'(?:^|[\s(])(?:' + _TGT + r'\s+gun|spawn\s.*?\sgun)\s+("[^"]*"|\S+)'
                     r'|(' + _TGT + r')\.weapon\s*=(?!=)\s*(\S.*)$')
# (file, literal key) -> models that site can spawn. Verified below, not trusted.
GIVE_ALLOW = {
    ("coop_mod/bunker.scr", "mg42"): ["models/human/german_wehrmact_grenadier.tik"],
    ("coop_mod/paradrop.scr", "bar"): ["models/human/allied_usa_c47-paratrooper1.tik"],
    ("coop_mod/paradrop.scr", "m1 garand"): ["models/human/allied_usa_c47-paratrooper1.tik"],
    ("coop_mod/paradrop.scr", "thompson"): ["models/human/allied_airborne_soldier.tik"],
    ("coop_mod/paradrop.scr", "springfield '03 sniper"): ["models/human/allied_airborne_soldier.tik"],
    ("coop_mod/paradrop.scr", "none"): ["models/human/dday_ranger_medic.tik"],
}


def case_keys(text):
    ks = set()
    for c in CASE_RE.findall(text):
        ks |= {(x[0] or x[1]).lower() for x in re.findall(r'"([^"]+)"|(\S+)', c)}
    return ks


# [bugsweep 2026-10-04] The first cut of this check called a tik "bodiless" whenever its init weapon was
# not a case key - 58 tiks, every one of which builds its BODY (usarmy.skd, german_worker.skd, ...) outside the
# cases and only loses gear. What a mismatched key really costs is decided per skelmodel: a non-head/hand
# skelmodel outside every case is an unconditional body; identity gear (helmet, cap, radio, medic bag) that
# exists only inside cases is what an unmatched key strips. Both are derived from the setup section with
# includes expanded in place.
HEADISH_RE = re.compile(r"head|hand", re.I)
IDENTITY_SURF = ("us_helmet", "officercap", "backpack", "phone", "m5bag", "helmet")


def setup_section(vfs, path, seen=None):
    seen = seen or set()
    if path.lower() in seen:
        return ""
    seen.add(path.lower())
    raw = vfs.read(path)
    if raw is None:
        return ""
    t = strip_comments(raw.decode("latin-1"))
    t = re.sub(r"(?im)^\s*\$include\s+(\S+)", lambda m: setup_section(vfs, m.group(1).strip('"'), seen), t)
    if len(seen) > 1:
        return t
    m = re.search(r"(?is)setup\s*\{", t)
    if not m:
        return ""
    i, d = m.end(), 1
    j = i
    while j < len(t) and d:
        d += (t[j] == "{") - (t[j] == "}")
        j += 1
    return t[i:j - 1]


def setup_scan(text):
    """-> (skelmodels outside cases, surfaces outside cases, {case key: (skelmodels, surfaces)})"""
    out_sk, out_sf, cases = [], set(), {}
    depth, cdepth, ckeys = 0, None, []
    for tok in re.findall(r"\{|\}|[^\n{}]+", text):
        if tok == "{":
            depth += 1
            continue
        if tok == "}":
            if cdepth is not None and depth == cdepth:
                cdepth = None
            depth -= 1
            continue
        for line in tok.splitlines():
            ln = line.strip()
            m = re.match(r"(?i)case\s+weapon\s+(.*)", ln)
            if m:
                ckeys = [(a or b).lower() for a, b in re.findall(r'"([^"]+)"|(\S+)', m.group(1))]
                cdepth = depth + 1
                for ck in ckeys:
                    cases.setdefault(ck, ([], set()))
                continue
            inside = cdepth is not None and depth >= cdepth
            m = re.match(r"(?i)skelmodel\s+(\S+)", ln)
            if m:
                if inside:
                    for ck in ckeys:
                        cases[ck][0].append(m.group(1))
                else:
                    out_sk.append(m.group(1))
            m = re.match(r"(?i)surface\s+(\S+)\s+shader", ln)
            if m:
                if inside:
                    for ck in ckeys:
                        cases[ck][1].add(m.group(1).lower())
                else:
                    out_sf.add(m.group(1).lower())
    return out_sk, out_sf, cases


def weapon_key_audit(vfs, verbose):
    fails = 0
    keys = {}
    bodiless = []
    gear = []
    for tp in vfs.list(AI_PREFIX, ".tik"):
        text = tiki_text(vfs, tp)
        ks = case_keys(text)
        keys[tp] = ks
        if not ks:
            continue
        iw = [w.strip().lower() for w in INITW_RE.findall(text)]
        out_sk, out_sf, cases = setup_scan(setup_section(vfs, tp))
        body_out = [x for x in out_sk if not HEADISH_RE.search(x)]
        init = iw[0] if iw else None
        init_body = [x for x in cases.get(init, ([], set()))[0] if not HEADISH_RE.search(x)] if init else []
        if not body_out and not init_body:
            bodiless.append((tp, init or "<none>", vfs.where(tp)))
        # identity gear the model LOSES when it spawns on its own init key (or on no key at all)
        init_sf = cases.get(init, ([], set()))[1] if init else set()
        at_risk = sorted({sf for ck, (_sk, sfs) in cases.items() for sf in sfs
                          if sf not in out_sf and sf not in init_sf
                          and any(sf == g or sf.endswith(g) for g in IDENTITY_SURF)})
        if at_risk and body_out:
            gear.append((tp, init or "<none>", at_risk, vfs.where(tp)))
    ncase = sum(1 for k in keys.values() if k)
    print("WEAPONKEY: %d of %d AI tiks have `case weapon` blocks" % (ncase, len(keys)))
    print("WEAPONKEY: %d of them spawn BODILESS unless given a matching key (no body outside the cases and the "
          "init weapon builds none)" % len(bodiless))
    for tp, iw, src in bodiless if verbose else [b for b in bodiless if b[2].startswith("repo:")]:
        print("  bodiless-at-spawn  %-60s init=%s [%s]" % (tp, iw, src))
    print("WEAPONKEY: %d tiks spawn WITHOUT identity gear (helmet/cap/radio/medic bag) on their own init key: it "
          "lives only in cases the init key does not name (repo overrides FAIL)" % len(gear))
    for tp, iw, sfs, src in gear:
        if src.startswith("repo:"):
            print("WEAPONKEY FAIL gear-in-case  %-52s init=%s %s" % (tp, iw, sfs))
            fails += 1
        elif verbose:
            print("  gear-in-case  %-60s init=%s %s [%s]" % (tp, iw, sfs, src))

    for dp, _dns, fns in os.walk(os.path.join(MOD, "coop_mod")):
        for f in sorted(fns):
            if not f.endswith(".scr"):
                continue
            rel = "coop_mod/" + f
            text = strip_comments(open(os.path.join(dp, f), "rb").read().decode("latin-1"))
            for ln, line in enumerate(text.splitlines(), 1):
                if re.match(r"^\s*\w[\w.]*\s+local\.\w+.*:\s*\{", line) or line.rstrip().endswith(":{"):
                    continue  # label header with a local.gun parameter
                for m in GIVE_RE.finditer(line):
                    if m.group(2) is not None and m.group(2).lower() in ("local", "level", "game", "group"):
                        continue
                    arg = (m.group(1) or m.group(3)).strip()
                    lit = arg.startswith('"') and arg.endswith('"') and arg.count('"') == 2
                    key = arg.strip('"').lower()
                    models = GIVE_ALLOW.get((rel, key)) if lit else None
                    if models is None:
                        print("WEAPONKEY FAIL %s:%d  %s  (use coop_mod/aihandler.scr::coop_actorArm, or verify "
                              "the key and add it to GIVE_ALLOW)" % (rel, ln, line.strip()[:90]))
                        fails += 1
                        continue
                    for mp in models:
                        if keys.get(mp) and key not in keys[mp]:
                            print("WEAPONKEY FAIL %s:%d  key %r is not a `case weapon` value of %s %s"
                                  % (rel, ln, key, mp, sorted(keys[mp])))
                            fails += 1
    print("WEAPONKEY: %d unsafe give site(s) in coop_mod" % fails)
    return fails


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--retail-only", action="store_true",
                    help="drop third-party paks: retail paks + this repo only")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    vfs = build_vfs(args.base, args.retail_only)
    if not vfs.layers:
        print("no paks under %s" % args.base)
        return 2
    shaders = load_shaders(vfs)
    tiks = vfs.list(AI_PREFIX, ".tik")
    print("VFS: %d layers, %d files; %d shader defs; %d AI tiks (%s)"
          % (len(vfs.layers), len(vfs.index), len(shaders), len(tiks), args.base))

    cache = {}
    # (status, rend, shader) -> list of "tik:surface#skin"
    hits = defaultdict(list)
    nodraw_body = []
    for tp in tiks:
        per, flags = tiki_surfaces(tiki_text(vfs, tp))
        for surf, skins in per.items():
            for idx, sn in enumerate(skins):
                for rend in ("gl1", "gl2"):
                    st, det = shader_status(vfs, shaders, sn, rend, cache)
                    if st != "OK":
                        hits[(st, rend, sn.lower(), det)].append("%s:%s#%d" % (tp, surf, idx))
            if "+nodraw" in flags.get(surf, ()) and re.search(r"tunic|pant|torso|body|leg|coat|jacket|uniform", surf):
                nodraw_body.append("%s:%s" % (tp, surf))

    bad = 0
    order = {"INVISIBLE": 0, "NODRAW": 1, "CHECKER": 2, "DEGRADED": 3}
    for key in sorted(hits, key=lambda k: (order[k[0]], k[2], k[1])):
        st, rend, sn, det = key
        users = hits[key]
        if st in ("INVISIBLE", "NODRAW") and not all((sn, u.split(":")[0]) in KNOWN_RETAIL for u in users):
            bad += 1
        if st == "DEGRADED" and not args.verbose:
            continue
        tiks_n = len(set(u.split(":")[0] for u in users))
        print("%-9s %s  %-40s %3d tiks  %s" % (st, rend, sn, tiks_n, det))
        if args.verbose or st in ("INVISIBLE", "NODRAW"):
            for u in users[: (None if args.verbose else 6)]:
                print("            " + u)
            if not args.verbose and len(users) > 6:
                print("            ... +%d more" % (len(users) - 6))
    for nb in nodraw_body:
        print("SPAWN-NODRAW body surface: " + nb)
    print("RESULT: %d invisible/nodraw (shader,renderer) pairs on AI surfaces" % bad)
    wk = weapon_key_audit(vfs, args.verbose)
    return 1 if (bad or wk) else 0


if __name__ == "__main__":
    sys.exit(main())
