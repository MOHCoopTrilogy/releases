#!/usr/bin/env python3
"""vfs - a read-only model of the OpenMOHAA (Breakthrough, com_target_game 2) virtual filesystem, for the stock-HD
inventory of the two own-disc missions. Our code. Reads the player's paks, writes nothing into them.

Search order (low -> high priority): <base>/main, <home>/main, <base>/mainta, <home>/mainta, <base>/maintt,
<home>/maintt; inside one dir the paks sort case-insensitively and a later name wins.
Image resolution = renderergl2/tr_image.c R_LoadImage: <base>.dds first (compression on), then for a .tga
request <base>.jpg, then the name as asked, then png, tga, jpg, jpeg, pcx, bmp.
"""
import io
import os
import re
import struct
import zipfile

from PIL import Image

LIVE_BASE = r"G:\mohaa-gl2"
LIVE_HOME = r"G:\mohaa-gl2\home"
LOADERS = ["png", "tga", "jpg", "jpeg", "pcx", "bmp"]


class VFS:
    def __init__(self, base=LIVE_BASE, home=LIVE_HOME, extra_home_paks=(), drop=()):
        self.paks = []          # low -> high priority
        for gd in ("main", "mainta", "maintt"):
            for root in (base, home):
                d = os.path.join(root, gd)
                if not os.path.isdir(d):
                    continue
                names = sorted([f for f in os.listdir(d) if f.lower().endswith(".pk3")], key=str.lower)
                for f in names:
                    if f.lower() in drop:
                        continue
                    self.paks.append(os.path.join(d, f))
                if gd == "maintt" and root == home:
                    for p in extra_home_paks:
                        self.paks.append(p)
        self.index = {}         # lower name -> list of (prio, pak, realname, size) high prio LAST
        self._zips = {}
        for prio, p in enumerate(self.paks):
            try:
                z = zipfile.ZipFile(p)
            except Exception:
                continue
            for zi in z.infolist():
                if zi.is_dir():
                    continue
                self.index.setdefault(zi.filename.lower().replace("\\", "/"), []).append((prio, p, zi.filename, zi.file_size))

    def short(self, pak):
        return os.path.basename(pak)

    def find(self, name):
        """highest-priority entry for an exact file name, or None"""
        e = self.index.get(name.lower().replace("\\", "/"))
        return e[-1] if e else None

    def all(self, name):
        return self.index.get(name.lower().replace("\\", "/"), [])

    def read(self, entry):
        prio, pak, real, _ = entry
        z = self._zips.get(pak)
        if z is None:
            z = self._zips[pak] = zipfile.ZipFile(pak)
        return z.read(real)

    def read_name(self, name):
        e = self.find(name)
        return self.read(e) if e else None

    def image_candidates(self, name):
        """the order R_LoadImage tries file names in"""
        name = name.replace("\\", "/")
        base, ext = os.path.splitext(name)
        ext = ext[1:].lower()
        out = [base + ".dds"]
        if ext == "tga":
            out.append(base + ".jpg")
        if ext in LOADERS:
            out.append(name)
            orig = ext
        else:
            orig = None
            base = name if not ext else base
        for l in LOADERS:
            if l != orig:
                out.append(base + "." + l)
        seen, res = set(), []
        for o in out:
            if o.lower() not in seen:
                seen.add(o.lower())
                res.append(o)
        return res

    def resolve_image(self, name):
        """-> (file name, entry) the engine loads, or (None, None)"""
        for c in self.image_candidates(name):
            e = self.find(c)
            if e:
                return c, e
        return None, None

    def image_size(self, entry):
        data = self.read(entry)
        if data[:4] == b"DDS ":
            h, w = struct.unpack("<II", data[12:20])
            return w, h
        try:
            return Image.open(io.BytesIO(data)).size
        except Exception:
            return None

    def best_alternative(self, name):
        """the largest image any pak holds under any candidate name (what COULD load if the order were right)"""
        best = None
        for c in self.image_candidates(name):
            for e in self.all(c):
                s = self.image_size(e)
                if s and (best is None or s[0] * s[1] > best[0][0] * best[0][1]):
                    best = (s, e, c)
        return best

    def list_prefix(self, prefix, ext=None):
        prefix = prefix.lower()
        for k in self.index:
            if k.startswith(prefix) and (ext is None or k.endswith(ext)):
                yield k


# ------------------------------------------------------------------ shaders
_TOK = re.compile(r'"[^"]*"|\S+')


def strip_comments(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def parse_shader_file(text):
    """-> {lower name: (name, body text)}"""
    t = strip_comments(text)
    out = {}
    i, n = 0, len(t)
    toks = [(m.group(0), m.start(), m.end()) for m in re.finditer(r'"[^"]*"|[{}]|[^\s{}]+', t)]
    k = 0
    while k < len(toks):
        tok = toks[k][0]
        if tok in "{}":
            k += 1
            continue
        if k + 1 < len(toks) and toks[k + 1][0] == "{":
            depth, j = 0, k + 1
            while j < len(toks):
                if toks[j][0] == "{":
                    depth += 1
                elif toks[j][0] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            body = t[toks[k + 1][1]:toks[j][2]] if j < len(toks) else t[toks[k + 1][1]:]
            out.setdefault(tok.strip('"').lower(), (tok.strip('"'), body))
            k = j + 1
        else:
            k += 1
    return out


def shader_images(body):
    """image names a shader body loads, with the stage keyword"""
    res = []
    lines = body.splitlines()
    for ln in lines:
        w = _TOK.findall(ln.strip())
        if not w:
            continue
        kw = w[0].lower()
        if kw in ("map", "clampmap", "nextbundle"):
            for a in w[1:2]:
                a = a.strip('"')
                if not a.startswith("$"):
                    res.append((kw, a))
            if kw == "nextbundle" and len(w) > 2:
                pass
        elif kw in ("animmap", "animmaponce", "animmapphase", "clampanimmap"):
            args = [a.strip('"') for a in w[1:]]
            # freq [phase] images...
            imgs = [a for a in args if re.search(r"[a-z_/]", a.lower()) and not re.match(r"^-?[\d.]+$", a)]
            for a in imgs:
                res.append((kw, a))
        elif kw == "skyparms":
            if len(w) > 1 and w[1] != "-":
                for s in ("rt", "bk", "lf", "ft", "up", "dn"):
                    res.append(("sky", w[1].strip('"') + "_" + s + ".tga"))
    return res


def shader_spritescale(body):
    m = re.search(r"(?im)^\s*spritescale\s+([-\d.]+)", body)
    return float(m.group(1)) if m else None


class Shaders:
    def __init__(self, vfs):
        self.vfs = vfs
        # FS_ListFiles: one copy per file NAME (highest priority); a name defined in several files: the file from the
        # highest-priority pak wins (gl2 fixed to match gl1, tr_shader.c FindShaderInShaderText)
        files = {}
        for k, ents in vfs.index.items():
            if k.startswith("scripts/") and k.endswith(".shader"):
                files[k] = ents[-1]
        self.defs = {}   # lower name -> (prio, file, pak, name, body)
        for k, e in sorted(files.items(), key=lambda kv: kv[1][0]):
            try:
                txt = vfs.read(e).decode("latin-1")
            except Exception:
                continue
            for ln, (nm, body) in parse_shader_file(txt).items():
                cur = self.defs.get(ln)
                if cur is None or e[0] >= cur[0]:
                    self.defs[ln] = (e[0], k, e[1], nm, body)

    def get(self, name):
        n = name.replace("\\", "/").lower()
        d = self.defs.get(n)
        if d is None:
            d = self.defs.get(os.path.splitext(n)[0])
        return d

    def images(self, name):
        """-> list of (stage kw, image name); an undefined shader is its own image"""
        d = self.get(name)
        if d is None:
            return [("implicit", name)]
        return shader_images(d[4])
