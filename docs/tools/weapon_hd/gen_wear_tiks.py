"""Per-instance weapon wear (user-approved 2026-10-05): two extra 4096 wear rows per gun's MAIN sheet, selected per weapon
entity by the 3-bit per-surface skin index that game.dll stamps in Weapon::AttachToOwner (seeded per player + gun).

    python docs/tools/weapon_hd/gen_wear_tiks.py mains          print the main sheets that get variants (build list)
    python docs/tools/weapon_hd/gen_wear_tiks.py stage          write patched TIK copies + zz_coop_hd_wear.shader into
                                                                C:/mohaa-weaponhd/build/stage/wear (next to the _w1/_w2 .dds)
    (check)  called by gen_weapon_hd_pak.py check: regenerate in memory, byte-compare with the wear pak's members

HOW. A TIK surface may carry several shader rows (`surface X shader A shader B shader C`, tiki_parse.cpp: every
`shader` token on the line adds a row, MAX_TIKI_SHADER 8) and both renderers draw row
`skinNum + MDL_SURFACE_SKININDEX(surface bits)`, clamped to row 0 when out of range (tr_model.cpp). So:
  row 0 = today's shader (untouched)   row 1 = coop_wear_<h>_w1   row 2 = coop_wear_<h>_w2
where each new shader is a copy of row 0's body with its diffuse map pointed at <sheet>_w1 / _w2 (an implicit shader
becomes `map <sheet>_wN` + `rgbGen lightingDiffuse`, exactly what tr_shader.c builds for an implicit model image).
Every surface whose row-0 shader draws a main sheet gets the rows, so a gun and its own magazine/sight parts on that
sheet always show the SAME variant. A surface whose bits select a row it does not have falls back to row 0.

THE TIKs ARE COPIES, NEVER EDITS. The weapon TIKs live in the assets_tex bucket (1.3 GB, reused by sha256), so the
wear pak carries patched copies generated from the EFFECTIVE source: docs/tools/assets/fixes/<rel> if the fixes pak
overrides it, else the mod tree file, else the winning retail/import pak copy. `check` regenerates them and fails
the build if any differ - so a later TIK edit by anyone forces a regeneration instead of being silently shadowed by
an old copy in this pak (the T6 'what loads is not what you shipped' trap).
"""
import hashlib, json, os, re, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vfs, jobs as J

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
FIXES = os.path.join(ROOT, "docs", "tools", "assets", "fixes")
STAGE = r"C:/mohaa-weaponhd/build/stage/wear"
SHADER_REL = "scripts/zz_coop_hd_wear.shader"
NVAR = 2
SKIPPED = set(json.load(open(os.path.join(HERE, "finishes.json"), encoding="utf-8")).get("skip", {}))


def mains(require_built=True):
    """base-gun TIK -> its main sheet (largest class-1/2 target; shared small parts excluded). With require_built, only
    sheets whose _w1 AND _w2 .dds exist in the wear stage get rows (a failed or skipped variant keeps the gun on row 0)."""
    jl = json.load(open(os.path.join(HERE, "jobs.json")))
    best = {}
    for e in jl:
        if e["cls"] not in (1, 2) or e["stem"] in SKIPPED:
            continue
        if max(e["target"]) < max(e["win"]):
            continue
        area = e["target"][0] * e["target"][1]
        for t in e["base_users"]:
            if t not in best or area > best[t][1]:
                best[t] = (e["stem"], area)
    out = {t: s for t, (s, a) in best.items()}
    if require_built:
        ok = lambda st: all(os.path.exists(os.path.join(STAGE, *(st + "_w%d.dds" % k).split("/"))) for k in (1, 2))
        out = {t: s for t, s in out.items() if ok(s)}
    return out


def effective_tik(rel):
    p = os.path.join(FIXES, *rel.split("/"))
    if os.path.isfile(p):
        return open(p, "rb").read(), "fixes"
    p = os.path.join(MOD, *rel.split("/"))
    if os.path.isfile(p):
        return open(p, "rb").read(), "mod"
    idx = vfs.index()
    for (pk, n) in reversed(idx.get(rel.lower(), [])):
        if "coop_hd_wpn_" in os.path.basename(pk) or "co-op_hzm" in os.path.basename(pk):
            continue
        return vfs._zips[pk].read(n), os.path.basename(pk)
    return None, None


def shname(sh, k):
    return "coop_wear_%s_w%d" % (hashlib.md5(sh.lower().encode()).hexdigest()[:10], k)


def generate():
    """-> ({member relpath: bytes}, report)"""
    main_of = mains()
    main_stems = set(main_of.values())
    sh = J.shader_index()
    out, rep, blocks = {}, [], {}
    jl = json.load(open(os.path.join(HERE, "jobs.json")))
    users = {}
    for e in jl:
        if e["stem"] in main_stems:
            for u in e["users"]:
                users.setdefault(u["tik"], set()).add(e["stem"])
    for tik in sorted(users):
        raw, src = effective_tik(tik)
        if raw is None:
            rep.append("%s: no source" % tik)
            continue
        text = raw.decode("latin-1")
        tdir = tik.rsplit("/", 1)[0] + "/"
        changed = 0

        def fix(m):
            nonlocal changed
            line, shader, rest = m.group(0), m.group(2), m.group(3)
            if re.search(r"(?i)\bshader\b", rest):
                return line                                          # already multi-row: leave it alone
            full = tdir + shader if "." in shader else shader
            body = sh.get(full.lower())
            dm = J.diffuse_map(body) if body is not None else full
            if not dm or os.path.splitext(dm.lower())[0] not in main_stems:
                return line
            stem = os.path.splitext(dm)[0]
            ext = os.path.splitext(dm)[1] or ".tga"
            for k in range(1, NVAR + 1):
                n = shname(full, k)
                if n not in blocks:
                    if body is None:
                        blocks[n] = "%s\n{\n\t{\n\t\tmap %s_w%d%s\n\t\trgbGen lightingDiffuse\n\t}\n}\n" % (n, stem, k, ext)
                    else:
                        nb = re.sub(r"(?mi)(^\s*(?:map|clampmap)\s+)" + re.escape(dm) + r"(?=\s)",
                                    lambda mm: mm.group(1) + "%s_w%d%s" % (stem, k, ext), body, count=1)
                        assert nb != body, (tik, shader)
                        blocks[n] = "%s\n{%s}\n" % (n, nb)
            changed += 1
            return "%s%s shader %s shader %s" % (m.group(1), shader, shname(full, 1), shname(full, 2)) + rest
        nt = re.sub(r"(?mi)(^[ \t]*surface[ \t]+\S+[ \t]+shader[ \t]+)(\S+)([^\r\n]*)", fix, text)
        if changed:
            out[tik] = nt.encode("latin-1")
            rep.append("%s: %d surface(s) <- %s" % (tik, changed, src))
    hdr = ("// GENERATED by docs/tools/weapon_hd/gen_wear_tiks.py - per-instance weapon wear rows (do not edit).\n"
           "// Each block is a copy of a weapon's row-0 shader with its diffuse map pointed at the _w1/_w2 sheet.\n\n")
    out[SHADER_REL] = (hdr + "\n".join(blocks[k] for k in sorted(blocks))).encode("latin-1")
    return out, rep


def stage():
    out, rep = generate()
    for rel, data in out.items():
        p = os.path.join(STAGE, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(data)
    for r in rep:
        print(r)
    print("%d member(s) staged" % len(out))


def check():
    pak = os.path.join(MOD, "zzzzzzzzzz_coop_hd_wpn_5wear.pk3")
    if not os.path.exists(pak):
        return []
    out, _ = generate()
    z = zipfile.ZipFile(pak)
    have = {n for n in z.namelist() if n.lower().endswith((".tik", ".shader"))}
    bad = []
    if have != set(out):
        bad.append("wear pak TIK/shader set differs from a regeneration: +%s -%s" %
                   (sorted(set(out) - have)[:5], sorted(have - set(out))[:5]))
    for rel in set(out) & have:
        if z.read(rel) != out[rel]:
            bad.append("wear pak %s is STALE vs its effective source - rerun gen_wear_tiks.py stage + pak build" % rel)
    return bad


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "mains"
    if cmd == "mains":
        m = mains()
        for t, s in sorted(m.items()):
            print("%-48s %s" % (t, s))
        print(len(set(m.values())), "main sheets")
    elif cmd == "stage":
        stage()
