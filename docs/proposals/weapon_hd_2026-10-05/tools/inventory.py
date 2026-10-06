"""Inventory every weapon TIK's surfaces -> shader -> texture, as the ENGINE resolves them.

Shader precedence (TRAPS T6, bug-2485): highest-priority pak wins; within one pak the
alphabetically FIRST .shader file wins. Image precedence: .dds before .jpg before .tga, and a
.dds in ANY pak beats a .jpg in any pak (R_LoadImage probes per extension). Surface shader
token containing '.' is prefixed with the tik's own directory (tiki_parse.cpp:1092).
Writes inventory.json next to this file. Read-only against the install.
"""
import vfs, re, os, io, json, struct, sys, collections
from PIL import Image
idx = vfs.index()
paks = vfs.paks()
prio = {p: i for i, p in enumerate(paks)}

# ---- shader index with engine precedence
shaders = {}   # name -> (pak, file, body)
def blocks(text):
    i = 0; n = len(text)
    text2 = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), text)
    for m in re.finditer(r"(?m)^[ \t]*([^\s{}/][^\s{}]*)[ \t]*\r?\n(?:[ \t]*\r?\n)*[ \t]*\{", text2):
        name = m.group(1).strip().lower()
        s = text2.find("{", m.end() - 1); d = 0; j = s
        while j < n:
            c = text2[j]
            if c == "{": d += 1
            elif c == "}":
                d -= 1
                if d == 0: break
            j += 1
        yield name, text[s:j + 1]
by_pak = collections.defaultdict(list)
for k, lst in idx.items():
    if k.endswith(".shader") and k.startswith("scripts/"):
        for (p, n) in lst: by_pak[p].append(n)
for p in paks:
    files = sorted(by_pak.get(p, []), key=lambda s: s.lower(), reverse=True)
    for n in files:
        t = vfs._zips[p].read(n).decode("latin-1", "replace")
        for name, body in blocks(t):
            shaders[name] = (os.path.basename(p), n, body)

def img_info(vpath):
    w = vfs.winner(vpath)
    if not w: return None
    b = vfs._zips[w[0]].read(w[1])
    ext = vpath.rsplit(".", 1)[-1]
    try:
        if ext == "dds":
            h, wd = struct.unpack("<II", b[12:20]); fourcc = b[84:88].decode("latin1")
            mips = struct.unpack("<I", b[28:32])[0]
            if fourcc == "DX10": fourcc = "DX10:%d" % struct.unpack("<I", b[128:132])[0]
            return dict(w=wd, h=h, fmt="dds/" + fourcc, mips=mips, bytes=len(b), pak=os.path.basename(w[0]))
        im = Image.open(io.BytesIO(b))
        return dict(w=im.size[0], h=im.size[1], fmt=ext + "/" + im.mode, bytes=len(b), pak=os.path.basename(w[0]))
    except Exception as e:
        return dict(err=str(e), pak=os.path.basename(w[0]))

def all_versions(stem):
    out = []
    for ext in (".dds", ".jpg", ".tga", ".png"):
        for (p, n) in idx.get(stem + ext, []):
            out.append((ext, os.path.basename(p)))
    return out

def stage_maps(body):
    return [m.group(2) for m in re.finditer(r"(?mi)^\s*(map|clampmap|animmap\s+\S+)\s+(\S+)", body)]

def resolve_shader(sh):
    s = shaders.get(sh.lower())
    if s:
        maps = [m for m in stage_maps(s[2]) if not m.startswith("$")]
        return dict(shader=sh, defined_in="%s:%s" % (s[0], s[1]), maps=maps, body=s[2])
    return dict(shader=sh, defined_in=None, maps=[sh], body=None)   # implicit image shader

FIN = ("_bloody", "_blued", "_camo_desert", "_camo_winter", "_camo_woodland", "_chrome", "_gold")
out = []
for k in sorted(idx):
    if not (k.startswith("models/weapons/") and k.endswith(".tik")): continue
    raw = vfs.read(k).decode("latin-1", "replace")
    nc = re.sub(r"//[^\n]*", "", raw)
    m0 = re.search(r"(?i)\bsetup\s*\{", nc)
    st = ""
    if m0:
        d, j = 0, m0.end() - 1
        while j < len(nc):
            d += {"{": 1, "}": -1}.get(nc[j], 0)
            if d == 0: break
            j += 1
        st = nc[m0.end():j]
    path = re.search(r"(?mi)^\s*path\s+(\S+)", st)
    skel = re.findall(r"(?mi)^\s*skelmodel\s+(\S+)", st)
    surfs = re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+(\S+)", st)
    inc = re.findall(r"(?mi)^\s*\$include\s+(\S+)", raw)
    isweapon = bool(re.search(r"(?mi)^\s*classname\s+Weapon", raw))
    name = re.search(r'(?mi)^\s*name\s+"([^"]+)"', raw)
    tdir = k.rsplit("/", 1)[0] + "/"
    rows = []
    for sname, shname in surfs:
        if "." in shname: shname = tdir + shname
        r = resolve_shader(shname)
        texs = []
        for m in r["maps"]:
            stem = os.path.splitext(m.lower())[0]
            vp, w = vfs.resolve_image(stem)
            texs.append(dict(map=m, loads=vp, info=img_info(vp) if vp else None, versions=all_versions(stem)))
        rows.append(dict(surface=sname, shader=shname, defined_in=r["defined_in"], textures=texs))
    base = os.path.basename(k)[:-4]
    fin = next((f for f in FIN if base.endswith(f)), None)
    out.append(dict(tik=k, tikpak=os.path.basename(vfs.winner(k)[0]), name=name.group(1) if name else None,
                    weapon=isweapon, path=path.group(1) if path else None, skel=skel, include=inc,
                    finish=fin[1:] if fin else None, surfaces=rows))
json.dump(out, open(os.path.join(os.path.dirname(__file__), "inventory.json"), "w"), indent=1)
print(len(out), "tiks;", len(shaders), "shaders")
