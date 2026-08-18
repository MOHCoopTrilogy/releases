"""For every player weapon, resolve the base diffuse texture of each of its surfaces.

Everything in the finish pipeline depends on this:
  - a BAKED finish (bloody, camo) needs the base texture as the image to process
  - a SHADER-STAGE finish (gold, chrome, blued) needs it as the `map` of its first stage

A weapon tik names a shader per surface (`surface Clip shader coop_skin_x`), and the shader names
the texture (`map textures/...`). Some tiks skip the shader and name a texture-ish shader directly.
So: tik -> shader name -> shader block -> map. Shaders live both in the mod and in the retail pak
set, and the MOD wins (that is what shipping a shader means).

Reports coverage rather than assuming it - if a gun's texture cannot be found, that gun simply
cannot have finishes generated, and it is better to know the number up front than to discover it
476 files in.
"""
import glob
import io
import os
import re
import sys
import zipfile

MOD = "hzm-mohaa-coop-mod/"
GOG = r"G:/GOG/Medal of Honor - Allied Assault War Chest"

# ---------------------------------------------------------------- shader index ----------------
shaders = {}          # lowercased shader name -> first `map` texture path


def index_shader_text(text):
    # a shader block is: NAME \n { ... }
    for m in re.finditer(r"(?m)^[ \t]*([^\s{}/][^\s{}]*)[ \t]*\r?\n[ \t]*\{", text):
        name = m.group(1).strip().lower()
        # find the matching close brace
        i = text.find("{", m.end() - 1)
        depth = 0
        j = i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = text[i:j]
        mm = re.search(r"(?mi)^\s*(?:map|clampmap)\s+(\S+)", body)
        if not mm:
            mm = re.search(r"(?mi)^\s*qer_editorimage\s+(\S+)", body)
        if mm and name not in shaders:
            tex = mm.group(1).strip()
            if not tex.startswith("$") and tex.lower() != "$lightmap":
                shaders[name] = tex


# retail first, mod last so the mod overwrites - but we insert only if absent, so index mod FIRST
for p in sorted(glob.glob(MOD + "scripts/*.shader")):
    index_shader_text(io.open(p, encoding="latin-1", errors="replace").read())
n_mod = len(shaders)
for f in sorted(glob.glob(GOG + "/main*/*.pk3")):
    try:
        z = zipfile.ZipFile(f)
    except Exception:
        continue
    for n in z.namelist():
        if n.lower().endswith(".shader"):
            try:
                index_shader_text(z.read(n).decode("latin-1", "replace"))
            except Exception:
                pass
print("shader index: %d names (%d from the mod)" % (len(shaders), n_mod))

# ---------------------------------------------------------------- texture existence -----------
pak_files = set()
for f in sorted(glob.glob(GOG + "/main*/*.pk3")):
    try:
        z = zipfile.ZipFile(f)
    except Exception:
        continue
    for n in z.namelist():
        pak_files.add(n.lower().replace("\\", "/"))
mod_files = set()
for p in glob.glob(MOD + "**/*", recursive=True):
    if os.path.isfile(p):
        mod_files.add(os.path.relpath(p, MOD).lower().replace("\\", "/"))


def texture_exists(t):
    t = t.lower().lstrip("/")
    base = re.sub(r"\.(tga|jpg|jpeg|dds|png)$", "", t)
    for ext in (".tga", ".jpg", ".jpeg", ".dds", ".png", ""):
        if base + ext in pak_files or base + ext in mod_files:
            return base + ext
    return None


# ---------------------------------------------------------------- walk the weapons -------------
ok, partial, bad = [], [], []
for p in sorted(glob.glob(MOD + "models/weapons/*.tik")):
    name = os.path.basename(p)
    t = io.open(p, encoding="latin-1", errors="replace").read()
    if not re.search(r"(?mi)^\s*classname\s+Weapon", t):
        continue
    surfs = re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+(\S+)", t)
    if not surfs:
        bad.append((name, "no surface..shader lines"))
        continue
    found, miss = {}, []
    for sname, shname in surfs:
        tex = shaders.get(shname.lower())
        if tex is None:
            tex = shname            # some tiks name the texture directly
        real = texture_exists(tex)
        if real:
            found[sname] = real
        else:
            miss.append("%s->%s" % (sname, shname))
    if found and not miss:
        ok.append((name, found))
    elif found:
        partial.append((name, found, miss))
    else:
        bad.append((name, "no surface resolved: " + ", ".join(miss[:3])))

print()
print("weapons fully resolved : %d" % len(ok))
print("weapons partly resolved: %d" % len(partial))
print("weapons unresolved     : %d" % len(bad))
print()
for n, f in ok[:6]:
    print("  OK      %-24s %s" % (n, list(f.values())[0]))
for n, f, m in partial[:6]:
    print("  PARTIAL %-24s missing %s" % (n, ", ".join(m[:2])))
for n, why in bad[:8]:
    print("  BAD     %-24s %s" % (n, why))
