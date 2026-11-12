"""masks.py [n] - sample glass masks for PAINTED window textures (no separate glass, no env stage), for the user to judge.

Read-only on the game tree. Finds the window-named world shaders with no `tcGen environment` first stage that cover the
most campaign surfaces, loads each one's main texture from the retail paks, derives a glass mask automatically
(dark, low-saturation, reasonably large regions; thin frame lines removed), and writes one sheet per texture:
    texture | mask | texture with the mask tinted
into ../masks/. Nothing here is used by the game: it is the evidence for whether automatic masks are good enough.
"""
import io, os, re, struct, sys, zipfile, collections
import numpy as np
from PIL import Image, ImageFilter

ROOT = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "masks")
OMAHA = ("m3l1a", "m3l1b", "e3l1", "e3l2")


def paks():
    out = []
    for d in ("main", "mainta", "maintt"):
        for f in sorted(os.listdir(os.path.join(ROOT, d))):
            if re.match(r"(?i)pak\d.*\.pk3$", f):
                out.append(zipfile.ZipFile(os.path.join(ROOT, d, f)))
    return out


def main():
    topn = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    zs = paks()
    shaders = {}
    for z in zs:
        for nm in z.namelist():
            if nm.lower().startswith("scripts/") and nm.lower().endswith(".shader"):
                t = re.sub(r"//[^\n]*", "", z.read(nm).decode("latin-1"))
                i, n = 0, len(t)
                rx = re.compile(r"\s*([^\s{}]+)\s*\{")
                while i < n:
                    m = rx.match(t, i)
                    if not m:
                        break
                    depth, j = 1, m.end()
                    while j < n and depth:
                        depth += (t[j] == "{") - (t[j] == "}")
                        j += 1
                    shaders[m.group(1).lower()] = t[m.end():j].lower()
                    i = j
    files = {}
    for z in zs:
        for nm in z.namelist():
            files[nm.lower()] = (z, nm)
    use = collections.Counter()
    for z in zs:
        for nm in z.namelist():
            l = nm.lower()
            if not (l.startswith("maps/") and l.endswith(".bsp") and l.count("/") == 1):
                continue
            base = l[5:-4]
            if not re.match(r"(m\dl\d\w?|t\dl\d\w?|e\dl\d\w?)$", base) or base in OMAHA:
                continue
            d = z.read(nm)
            ver = struct.unpack_from("<i", d, 4)[0]
            lumps = [struct.unpack_from("<ii", d, 12 + 8 * k) for k in range(28)]
            off = 0 if ver > 18 else 1
            so, sl = lumps[0]
            fo, fl = lumps[3 + off]
            names = [d[so + 140 * k: so + 140 * k + 64].split(b"\0")[0].decode("latin-1").lower() for k in range(sl // 140)]
            for k in range(fl // 108):
                sn = struct.unpack_from("<i", d, fo + 108 * k)[0]
                if 0 <= sn < len(names):
                    use[names[sn]] += 1
    cand = []
    total = [0]
    for name, cnt in use.most_common():
        # "pane" but not "panel": the first sweep of the study counted wall and ship panels as windows
        if not re.search(r"window|glass|pane(?!l)", name) or re.search(r"broken|frame|shutter", name):
            continue
        total[0] += cnt
        body = shaders.get(name, "")
        st = re.search(r"\{([^{}]*)\}", body)
        first = st.group(1) if st else ""
        if "tcgen" in first and "environment" in first:
            continue                                   # has separate glass already: not a painted window
        m = re.search(r"\bmap\s+(textures/\S+)", body)
        tex = (m.group(1) if m else name + ".tga")
        stem = os.path.splitext(tex)[0]
        hit = next((files[stem + e] for e in (".tga", ".jpg") if stem + e in files), None)
        if hit:
            cand.append((name, cnt, hit))
    painted = sum(c for n_, c in use.items() if re.search(r"window|glass|pane(?!l)", n_) and not re.search(r"broken|frame|shutter", n_)
                  and not ("tcgen" in (re.search(r"\{([^{}]*)\}", shaders.get(n_, "")) or [None, ""])[1]))
    print("window-named world surfaces without an env first stage (non-Omaha campaign maps): %d" % painted)
    cand = cand[:topn]
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for name, cnt, (z, nm) in cand:
        im = Image.open(io.BytesIO(z.read(nm))).convert("RGB")
        if max(im.size) < 256:
            im = im.resize((im.size[0] * 2, im.size[1] * 2), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32) / 255.0
        lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        sat = (a.max(axis=2) - a.min(axis=2)) / np.maximum(a.max(axis=2), 1e-3)
        thr = np.percentile(lum, 35)
        raw = ((lum < max(thr, 0.08)) & (sat < 0.45)).astype(np.uint8) * 255
        k = max(3, (min(im.size) // 48) | 1)
        m = Image.fromarray(raw).filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))   # open: drop thin lines
        m = m.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))                       # close: fill specks
        mk = np.asarray(m) > 127
        cover = float(mk.mean())
        tint = a.copy()
        tint[mk] = tint[mk] * 0.35 + np.array([0.15, 0.55, 0.75], dtype=np.float32) * 0.65
        w, h = im.size
        sheet = Image.new("RGB", (w * 3 + 16, h), (24, 24, 24))
        sheet.paste(im, (0, 0))
        sheet.paste(Image.fromarray((mk * 255).astype(np.uint8)).convert("RGB"), (w + 8, 0))
        sheet.paste(Image.fromarray((tint * 255).astype(np.uint8)), (2 * w + 16, 0))
        fn = re.sub(r"[^a-z0-9]+", "_", name.replace("textures/", "")) + ".jpg"
        sheet.save(os.path.join(OUT, fn), quality=88)
        rows.append((name, cnt, im.size, round(cover, 2), fn))
        print("%-52s surfaces %4d  %4dx%-4d  mask covers %.0f%%  %s" % (name, cnt, w, h, cover * 100, fn))
    return rows


main()
