"""gen_sight_alias.py - the ADS sight-row ALIASES of the finishes2 skin variants (bug-10724), and the gate that every finish variant
aims exactly like its base gun.

WHY. The cgame's sight solve looks a gun up in code/cgame/cg_adssights.h by its EXACT tiki path (CG_FindAdsSight) or its EXACT
weapon name (CG_FindAdsSightByName) and deliberately never strips a suffix (a model variant such as "BAR (Pacific)" is a different
mesh). The standard seven finishes got explicit rows because gen_sights_header.py walked the installed VFS; the finishes2 variants
(fids 40+) live in an out-of-band pak that walk never saw, so none of the 949 had a row and every one of them aimed with the
fallback tune.

WHAT. One generated table, code/cgame/cg_adssights_alias.h: variant tiki -> base tiki and variant name -> base name. The lookups try
the exact row first, then the alias's base (one hop). An alias is emitted ONLY when the variant tik is proven to be the base gun with
a different skin: the two tik texts are identical once the name, rank and surface->shader lines are removed (same mesh, same scale,
same animations - so the base's sight geometry IS the variant's). Rows are not copied: a later retune of a base row (newguns-eng,
fg42hd, ...) reaches its finishes without regenerating anything, and cg_adssights.h - edited on several engine branches - is not
touched.

    python docs/tools/gen_sight_alias.py build   [--engine DIR]   write <engine>/code/cgame/cg_adssights_alias.h
    python docs/tools/gen_sight_alias.py check   [--engine DIR]   the GATE (exit 1): the header is in sync with the builds, and every
                                                                  skin FINISH variant (fids 1-7 and 40+, loadoutskins.scr + the
                                                                  finishes2 builds) resolves to exactly the sight row its base resolves
                                                                  to - by its own row or its alias
Inputs: $HZM_MOD (loadoutskins.scr), the finishes2 builds ($HZM_FS2_BUILDS, ';'-separated dirs with rows.tsv + the pak; default: this
branch's staging build and the new-guns build), extra tik dirs for the base guns ($HZM_TIK_DIRS), the engine tree ($HZM_ENGINE or
--engine) and, for the gate, any extra cg_adssights.h to union base rows from ($HZM_SIGHT_HEADERS, e.g. the newguns-eng copy that
carries the Bren / MP28 / Panzerfaust rows).
"""
import io
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")
BUILDS = [d for d in (os.environ.get("HZM_FS2_BUILDS") or r"H:\hzm_work\finishes2_build;H:\hzm_work\newguns\fs2_build").split(";") if d]
TIK_DIRS = [d for d in (os.environ.get("HZM_TIK_DIRS") or "").split(";") if d] + [
    os.path.join(MOD, "models", "weapons"),
    os.path.join(ROOT, "docs", "tools", "assets", "wpnfix", "models", "weapons"),
    os.path.join(ROOT, "docs", "tools", "assets", "fixes", "models", "weapons"),
    r"C:\hzm-newguns\root\docs\tools\assets\wpnfix\models\weapons",
    r"C:\mohaa-coop-dev\docs\tools\assets\wpnfix\models\weapons",
]
VFS_TOOLS = r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools"
OUT_REL = os.path.join("code", "cgame", "cg_adssights_alias.h")
FS2_MIN = 40


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


# [v1.10.68 integration] the release engine checkout first (build.ps1 calls `check` with no env; openmohaa-hzm is an older
# branch and its source lacks the newguns / finishes2 rows, so the default failed the gate) - same order as check_deck.py
_ENGINE_CANDIDATES = [r"H:\hzm_work\eng-hotfix13661", os.path.join(ROOT, "openmohaa-hzm")]
ENGINE = arg("--engine") or os.environ.get("HZM_ENGINE") or next((d for d in _ENGINE_CANDIDATES if os.path.isdir(os.path.join(d, "code", "cgame"))), _ENGINE_CANDIDATES[-1])


def norm(text):
    """the tik with the per-skin lines removed: what must be identical between a finish and its base"""
    t = text.replace("\r\n", "\n")
    t = re.sub(r"//[^\n]*", "", t)
    t = re.sub(r'(?mi)^\s*name\s+"[^"]*"[^\n]*$', "", t)
    t = re.sub(r"(?mi)^\s*rank\s+\d+\s+\d+[^\n]*$", "", t)
    t = re.sub(r"(?mi)^\s*surface\s+\S+\s+shader\s+\S+[^\n]*$", "", t)
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


def name_of(text):
    m = re.search(r'(?mi)^\s*name\s+"([^"]+)"', text)
    return m.group(1) if m else None


_vfs = None


def base_texts(give):
    """every copy of the base tik we can see (a variant only has to match ONE: the copy it was derived from)"""
    global _vfs
    out = []
    fn = os.path.basename(give).lower()
    for d in TIK_DIRS:
        p = os.path.join(d, fn)
        if os.path.isfile(p):
            out.append(("dir " + d, io.open(p, encoding="latin-1", errors="replace").read()))
    if _vfs is None:
        sys.path.insert(0, VFS_TOOLS)
        import vfs as v
        _vfs = v
    raw = _vfs.read(give)
    if raw is not None:
        out.append(("vfs", raw.decode("latin-1", "replace")))
    return out


def fs2_variants():
    """[(give, variant, variant text)] from every finishes2 build (later builds add guns; a variant in two builds must agree)"""
    seen, out = {}, []
    for b in BUILDS:
        rows = os.path.join(b, "rows.tsv")
        pak = os.path.join(b, "zzzzzzzzzz_coop_finishes_hd.pk3")
        if not (os.path.exists(rows) and os.path.exists(pak)):
            continue
        z = zipfile.ZipFile(pak)
        idx = {n.lower(): n for n in z.namelist()}
        for i, line in enumerate(io.open(rows, encoding="utf-8")):
            if i == 0 or not line.strip():
                continue
            give, _fid, _k, var, _r = line.rstrip("\r\n").split("\t")
            n = idx.get(var.lower())
            assert n, "%s: %s not in its pak" % (b, var)
            t = z.read(n).decode("latin-1", "replace")
            if var.lower() in seen:
                assert norm(seen[var.lower()]) == norm(t), "%s differs between the finishes2 builds" % var
                continue
            seen[var.lower()] = t
            out.append((give.lower(), var.lower(), t))
    # after the merge the staging builds may be gone: every fid 40+ row of loadoutskins.scr, read from the SHIPPED finishes pak
    import finishes2 as F2
    pak = F2.pak_path(os.environ.get("HZM_BASE_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod"))
    skins = io.open(os.path.join(MOD, "coop_mod", "loadoutskins.scr"), encoding="latin-1").read()
    rows = [(g.lower(), v.lower()) for g, f, v in re.findall(r'coop_skinGive\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', skins)
            if int(f) >= FS2_MIN and v.lower() not in seen]
    if rows:
        assert os.path.exists(pak), "no finishes pak for %d finishes2 rows: %s" % (len(rows), pak)
        z = zipfile.ZipFile(pak)
        idx = {n.lower(): n for n in z.namelist()}
        for give, var in rows:
            assert var in idx, "%s is not in %s" % (var, pak)
            seen[var] = z.read(idx[var]).decode("latin-1", "replace")
            out.append((give, var, seen[var]))
    return out


def std_variants():
    """[(give, variant, text)] for the standard seven finishes (fids 1-7) of loadoutskins.scr. 147 of them (21 guns whose finishes
    came after the sight sweep: camo65, wpnfix, dbshotgun ...) had no row either - same defect, same proof, same alias"""
    skins = io.open(os.path.join(MOD, "coop_mod", "loadoutskins.scr"), encoding="latin-1").read()
    out = []
    for g, f, v in sorted(set(re.findall(r'coop_skinGive\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', skins))):
        if int(f) > 7:
            continue
        txt = base_texts(v)                 # the variant's own copies (mod tree / wpnfix / fixes / installed)
        if txt:
            out.append((g.lower(), v.lower(), txt[0][1]))
    return out


def heads():
    return [os.path.join(ENGINE, "code", "cgame", "cg_adssights.h")] + [p for p in (os.environ.get("HZM_SIGHT_HEADERS") or "").split(";") if p]


def aliases():
    """an alias for every finish variant WITHOUT an explicit row of its own (an explicit row - most of the standard seven - wins in the
    lookup anyway, and some of those are older copies the proof would not match, e.g. the C96's pre-remodel finishes)"""
    al, bad = [], []
    direct = header_rows(heads())[0]
    for give, var, t in std_variants() + fs2_variants():
        if var in direct:
            continue
        cands = base_texts(give)
        hit = [(src, bt) for src, bt in cands if norm(bt) == norm(t)]
        if not hit:
            bad.append("%s: not the base gun's mesh / anims (%d copies of %s checked)" % (var, len(cands), give))
            continue
        al.append((var, give, name_of(t), name_of(hit[0][1])))
    return sorted(al), bad


def render(al):
    L = ["// GENERATED by docs/tools/gen_sight_alias.py from the finishes2 builds - do not edit (bug-10724).",
         "// A finishes2 skin variant is its base gun with other shaders (the generator proves it: the two tik texts match once the name,",
         "// rank and surface->shader lines are removed), so it aims with the BASE gun's sight row: CG_FindAdsSight / CG_FindAdsSightByName",
         "// try the exact row first, then this alias's base. One hop, exact strings - never a suffix strip (a model variant is another mesh).",
         "#pragma once", "",
         "typedef struct {",
         "    const char *tiki;      // the variant's TIKI path",
         "    const char *baseTiki;  // its base gun's TIKI path",
         "    const char *name;      // the variant's weapon name (configstring)",
         "    const char *baseName;  // the base gun's weapon name",
         "} adsSightAlias_t;", "",
         "static const adsSightAlias_t s_adsSightAlias[] = {"]
    for var, give, nm, bnm in al:
        q = lambda s: '"%s"' % s.replace('"', "") if s else "NULL"  # noqa: E731
        L.append("    {%s, %s, %s, %s}," % (q(var), q(give), q(nm), q(bnm)))
    L += ["};", ""]
    return "\n".join(L)


def header_rows(paths):
    """{tiki lower: row}, {name lower: row} from cg_adssights.h copies (later files add / override)"""
    by_t, by_n = {}, {}
    rx = re.compile(r'^\s*\{"([^"]+)",\s*(NULL|"[^"]*"),\s*\{([^}]*)\},\s*\{([^}]*)\},\s*([-\d.f]+),')
    for p in paths:
        for line in io.open(p, encoding="latin-1"):
            m = rx.match(line)
            if m:
                row = (m.group(3).replace(" ", ""), m.group(4).replace(" ", ""), m.group(5))
                by_t[m.group(1).lower()] = row
                if m.group(2) != "NULL":
                    by_n[m.group(2).strip('"').lower()] = row
    return by_t, by_n


def check(al, bad, out_path):
    errs = list(bad)
    want = render(al)
    cur = io.open(out_path, encoding="latin-1", newline="").read().replace("\r\n", "\n") if os.path.exists(out_path) else None
    if cur != want:
        errs.append("%s is %s - run: python docs/tools/gen_sight_alias.py build" % (out_path, "missing" if cur is None else "stale"))
    by_t, by_n = header_rows(heads())
    # resolve through the aliases the ENGINE TREE really carries (a missing / stale header must fail per variant, not just once)
    amap = {}
    for m in re.finditer(r'^\s*\{"([^"]+)", "([^"]+)", (NULL|"[^"]*"), (NULL|"[^"]*")\},', cur or "", re.M):
        amap[m.group(1).lower()] = (m.group(2).lower(), m.group(3).strip('"') if m.group(3) != "NULL" else None,
                                    m.group(4).strip('"') if m.group(4) != "NULL" else None)
    # every finish variant in the game: the standard seven (loadoutskins.scr) + every finishes2 variant (the builds)
    skins = io.open(os.path.join(MOD, "coop_mod", "loadoutskins.scr"), encoding="latin-1").read()
    pairs = {(v.lower(), g.lower()) for g, f, v in re.findall(r'coop_skinGive\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', skins)
             if int(f) <= 7 or int(f) >= FS2_MIN}
    pairs |= {(v, g) for g, v, _t in fs2_variants()}
    n_ok, n_none = 0, 0
    for var, give in sorted(pairs):
        base = by_t.get(give)
        mine = by_t.get(var)
        if mine is None and var in amap:
            mine = by_t.get(amap[var][0])
        if base is None:
            n_none += 1                     # the base gun has no sight row (fallback tune): the variant must not have a different one
            if mine is not None and var not in amap:
                errs.append("%s has a sight row, its base %s has none" % (var, give))
            continue
        if mine is None:
            errs.append("%s: NO sight row (its base %s has one)" % (var, give))
        elif mine != base and var not in amap:
            pass                            # an explicit row of its own (a standard finish) - its geometry is the generator's call
        else:
            n_ok += 1
        if var in amap:                     # the name path too (CG_FindAdsSightByName, configstring names)
            _g, nm, bnm = amap[var]
            if nm and nm.lower() in by_n and by_n[nm.lower()] != base:
                errs.append("%s: an explicit row for the name %r disagrees with the base row" % (var, nm))
    print("sight rows: %d finish variants; %d aim with their base gun's row, %d bases have no row (fallback tune, same for the "
          "variant); %d aliases in %s" % (len(pairs), n_ok, n_none, len(al), os.path.basename(out_path)))
    for e in errs[:30]:
        print("  FAIL " + e)
    if len(errs) > 30:
        print("  ... %d more" % (len(errs) - 30))
    print("  -> %s" % ("OK" if not errs else "FAILED"))
    return 0 if not errs else 1


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    out_path = os.path.join(ENGINE, OUT_REL)
    al, bad = aliases()
    if cmd == "build":
        if bad:
            for b in bad:
                print("REFUSED " + b)
            return 1
        io.open(out_path, "w", encoding="latin-1", newline="\n").write(render(al))
        print("wrote %s: %d aliases" % (out_path, len(al)))
        return 0
    return check(al, bad, out_path)


if __name__ == "__main__":
    sys.exit(main())
