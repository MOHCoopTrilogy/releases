"""Weapon HD job table: every weapon texture sheet the engine loads, who uses it, how to rebuild it.

    python docs/tools/weapon_hd/jobs.py        # writes docs/tools/weapon_hd/jobs.json and prints a class summary

A SHEET is the image the engine actually loads for a weapon surface (TIK surface -> shader -> first diffuse stage ->
.dds/.jpg/.tga precedence, vfs.py). First and third person draw the same weapon TIK, so one sheet covers both.

Per sheet:
  cls      1 = LOW (<= 800 px today) used by a base gun     2 = already-HD sheet of a base gun
           3 = used only by skin-variant TIKs (Hobbs/Guan/LV/DH/coop_v3...)   (4 = baked finishes, separate job)
  users    [(tik, skd vpath, [surface names])] - the meshes whose UVs paint from it (edge-wear / coverage masks)
  source   best lossless art on disk: HRRTM Pak4c TGA, else the largest non-DXT copy if >= half the winner's size,
           else the winner itself
  target   (w, h): every gun gets a 4096-square texel budget spread over ITS sheets with one common scale
           s = clamp(4096 / sqrt(sum of the gun's sheet areas), 2, 8), each axis rounded up to a power of two and
           capped at 4096 - one big sheet -> 4096; Johnson's 16 x 640x480 -> 2048x1024 each (not 16 x 4096).
  alpha    True when the source alpha channel carries data (-> DXT5, alpha kept)
Skipped: environment-mapped stages (tcGen environment), textures/common, textures/effects, crates, lenses.
"""
import os, re, io, json, math, struct, collections, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vfs, skd

FIN = ("_bloody", "_blued", "_camo_desert", "_camo_winter", "_camo_woodland", "_chrome", "_gold")
SKIP = ("models/human/", "textures/common/", "textures/effects/", "models/crates/", "lens", "env_sheen", "/k5", "howitzer", "invisible")


def shader_index():
    idx = vfs.index()
    by_pak = collections.defaultdict(list)
    for k, lst in idx.items():
        if k.endswith(".shader") and k.startswith("scripts/"):
            for (p, n) in lst:
                by_pak[p].append(n)
    sh = {}
    for p in vfs.paks():
        for n in sorted(by_pak.get(p, []), key=str.lower, reverse=True):   # alphabetically FIRST file wins in a pak
            t = vfs._zips[p].read(n).decode("latin-1", "replace")
            t2 = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), t)
            for m in re.finditer(r"(?m)^[ \t]*([^\s{}/][^\s{}]*)[ \t]*\r?\n(?:[ \t]*\r?\n)*[ \t]*\{", t2):
                s = t2.find("{", m.end() - 1); d = 0; j = s
                while j < len(t2):
                    d += {"{": 1, "}": -1}.get(t2[j], 0)
                    if d == 0:
                        break
                    j += 1
                sh[m.group(1).strip().lower()] = t2[s + 1:j]
    return sh


def diffuse_map(body):
    """first stage map that is not a lightmap and not environment-mapped"""
    for st in re.finditer(r"\{([^{}]*)\}", body):
        s = st.group(1)
        if re.search(r"(?i)tcGen\s+environment", s):
            continue
        m = re.search(r"(?mi)^\s*(?:map|clampmap)\s+(\S+)", s) or re.search(r"(?mi)^\s*animmap\s+\S+\s+(\S+)", s)
        if m and not m.group(1).startswith("$"):
            return m.group(1)
    return None


def img_info(vpath):
    w = vfs.winner(vpath)
    b = vfs._zips[w[0]].read(w[1])
    if vpath.endswith(".dds"):
        h, wd = struct.unpack("<II", b[12:20])
        return wd, h, "dds:" + b[84:88].decode("latin1"), os.path.basename(w[0])
    from PIL import Image
    im = Image.open(io.BytesIO(b))
    return im.size[0], im.size[1], vpath.rsplit(".", 1)[1] + ":" + im.mode, os.path.basename(w[0])


# Paks whose copies are earlier AI upscales of the retail/xw art (the project's own 2x/4x ESRGAN runs and the
# third-party upscale packs). Running ESRGAN again on them compounds the painterly look, so the ORIGINAL art is
# preferred and these are used only when nothing else exists.
UPSCALE_PAKS = ("zzzzzz_hd_world", "zzzzzzz_dds_override", "zzzzzzz_dds_hdmem", "zzzzzzzzzz_coop_hd_m3l1a",
                "zzzzz-AA_HD_Project")


def _thumb(b):
    from PIL import Image
    import numpy as np
    try:
        im = Image.open(io.BytesIO(b)).convert("L").resize((64, 64), Image.BOX)
        return np.asarray(im, np.float32).ravel()
    except Exception:
        return None


def same_art(a, b):
    import numpy as np
    if a is None or b is None or a.std() < 2 or b.std() < 2:
        return True
    return float(np.corrcoef(a, b)[0, 1]) >= 0.80


def pick_source(stem, win_w, win_h):
    """The best lossless copy OF THE ART THAT LOADS TODAY. A candidate whose 64 px thumbnail does not correlate >= 0.8
    with today's winner is different art (QA round 1: pak1's MG42 is not the hd_world/Omaha MG42 players see) and is
    never used; if nothing lossless matches, the winner itself is the source."""
    idx = vfs.index()
    vpw, ww = vfs.resolve_image(stem)
    win_thumb = _thumb(vfs._zips[ww[0]].read(ww[1])) if ww else None
    best = None
    for ext in (".tga", ".png", ".jpg", ".jpeg"):
        for (p, n) in idx.get(stem + ext, []):
            from PIL import Image
            try:
                im = Image.open(io.BytesIO(vfs._zips[p].read(n)))
            except Exception:
                continue
            if not same_art(_thumb(vfs._zips[p].read(n)), win_thumb):
                continue
            area = im.size[0] * im.size[1]
            up = any(u in os.path.basename(p) for u in UPSCALE_PAKS)
            score = (("HRRTM_Pak4c" in p) * 10 ** 12) + ((not up) * 10 ** 10) + area
            if best is None or score >= best[0]:          # ties -> the HIGHER-priority pak (what loads today)
                best = (score, os.path.basename(p), n, im.size, im.mode, p)
    if best:
        return {"pak": best[1], "pakpath": best[5], "name": best[2], "size": list(best[3]), "mode": best[4],
                "upscale": any(u in best[1] for u in UPSCALE_PAKS)}
    w = vfs.resolve_image(stem)[1]
    return {"pak": os.path.basename(w[0]), "pakpath": w[0], "name": w[1], "size": [win_w, win_h], "mode": "dds",
            "upscale": any(u in w[0] for u in UPSCALE_PAKS)}


def has_alpha(e):
    """True only if a shader drawing the sheet READS alpha (alphaFunc / alpha blends / alphaGen) AND the source
    alpha carries data. Many retail TGAs are RGBA with alpha 255, or alpha a shader never reads."""
    if not e.get("shader_alpha"):
        return False
    if e["source"]["mode"] not in ("RGBA", "LA", "dds"):
        return False
    from PIL import Image
    import numpy as np
    src = e["source"]
    p = src["pakpath"]           # NOT the basename: main/mainta/maintt each have a pak1.pk3
    vfs.index()
    try:
        im = Image.open(io.BytesIO(vfs._zips[p].read(src["name"]))).convert("RGBA")
    except Exception:
        return False
    a = np.asarray(im)[..., 3]
    return bool((a < 250).mean() > 0.002)


def pot_up(x):
    return 1 << max(0, int(math.ceil(math.log2(max(1.0, x)) - 1e-9)))


def main():
    idx = vfs.index()
    sh = shader_index()
    bases = set()
    tiks = {}
    for k in sorted(idx):
        if not (k.startswith("models/weapons/") and k.endswith(".tik")):
            continue
        raw = vfs.read(k).decode("latin-1", "replace")
        if not re.search(r"(?mi)^\s*classname\s+Weapon", raw):
            continue
        nc = re.sub(r"//[^\n]*", "", raw)
        m0 = re.search(r"(?i)\bsetup\s*\{", nc)
        if not m0:
            continue
        d, j = 0, m0.end() - 1
        while j < len(nc):
            d += {"{": 1, "}": -1}.get(nc[j], 0)
            if d == 0:
                break
            j += 1
        st = nc[m0.end():j]
        path = (re.search(r"(?mi)^\s*path\s+(\S+)", st) or [None, ""])[1].strip("/")
        skels = re.findall(r"(?mi)^\s*skelmodel\s+(\S+)", st)
        surfs = re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+(\S+)", st)
        base = os.path.basename(k)[:-4].lower()
        tiks[k] = dict(base=base, path=path, skels=skels, surfs=surfs, fin=any(base.endswith(f) for f in FIN))
        if not tiks[k]["fin"]:
            bases.add(base)

    def root_of(b):
        best = None
        for c in bases:
            if c != b and b.startswith(c + "_") and (best is None or len(c) > len(best)):
                best = c
        return best

    sheets = {}
    tdir = lambda k: k.rsplit("/", 1)[0] + "/"
    for k, t in tiks.items():
        if t["fin"]:
            continue
        variant = root_of(t["base"]) is not None
        skdp = [(t["path"] + "/" + s).lower() for s in t["skels"]]
        skdp = [p for p in skdp if p in idx]
        for sname, shname in t["surfs"]:
            if "." in shname:
                shname = tdir(k) + shname
            body = sh.get(shname.lower())
            m = diffuse_map(body) if body is not None else shname
            if not m:
                continue
            stem = os.path.splitext(m.lower())[0]
            if any(s in stem for s in SKIP):
                continue
            vp, w = vfs.resolve_image(stem)
            if not vp:
                continue
            e = sheets.setdefault(stem, dict(stem=stem, loads=vp, users={}, base_users=set(), var_users=set(),
                                             shader_alpha=False))
            if body and re.search(r"(?i)alphaFunc|SRC_ALPHA|alphaGen|blendfunc\s+blend", body):
                e["shader_alpha"] = True
            u = e["users"].setdefault(k, {"skd": skdp, "surfaces": []})
            if sname not in u["surfaces"]:
                u["surfaces"].append(sname)
            (e["var_users"] if variant else e["base_users"]).add(k)

    # per-gun texel budget
    for e in sheets.values():
        w, h, fmt, pak = img_info(e["loads"])
        e.update(win=[w, h], fmt=fmt, pak=pak)
        e["source"] = pick_source(e["stem"], w, h)
    gun_sheets = collections.defaultdict(set)
    for st, e in sheets.items():
        for k in e["users"]:
            gun_sheets[k].add(st)
    for st, e in sheets.items():
        best = 0
        for k in e["users"]:
            area = sum(sheets[s]["source"]["size"][0] * sheets[s]["source"]["size"][1] for s in gun_sheets[k])
            best = max(best, min(8.0, max(2.0, 4096.0 / math.sqrt(area))))
        sw, shh = e["source"]["size"]
        e["scale"] = round(best, 3)
        lng = min(4096, pot_up(max(sw, shh) * best))
        if len(e["users"]) >= 3 and max(sw, shh) <= 512:      # shared small parts (clips, sights): 2048 is plenty
            lng = min(lng, 2048)
        r = min(sw, shh) / max(sw, shh)
        sht = 1 << max(0, int(round(math.log2(max(1.0, lng * r)))))
        e["target"] = [lng, sht] if sw >= shh else [sht, lng]
        e["cls"] = 3 if not e["base_users"] else (1 if max(e["source"]["size"]) <= 800 else 2)
        if e["cls"] == 3:                       # skin variants: <= 2048 (the approved ~190 MB scope)
            e["target"] = [min(2048, t) for t in e["target"]]
        e["alpha"] = has_alpha(e)
        e["base_users"] = sorted(e["base_users"]); e["var_users"] = sorted(e["var_users"])
        e["users"] = [{"tik": k, **v} for k, v in sorted(e["users"].items())]
    out = sorted(sheets.values(), key=lambda e: (e["cls"], e["stem"]))
    json.dump(out, open(os.path.join(HERE, "jobs.json"), "w"), indent=1)
    c = collections.Counter(e["cls"] for e in out)
    nomesh = [e["stem"] for e in out if not any(u["skd"] for u in e["users"])]
    raw = collections.Counter()
    for e in out:
        tw, th = e["target"]
        raw[e["cls"]] += tw * th // 2 * 4 // 3 * (2 if e["alpha"] else 1)
    print("sheets per class:", dict(c), " raw MB:", {k: round(v / 1e6) for k, v in raw.items()})
    print("no mesh found for %d sheets:" % len(nomesh), nomesh[:20])


if __name__ == "__main__":
    main()
