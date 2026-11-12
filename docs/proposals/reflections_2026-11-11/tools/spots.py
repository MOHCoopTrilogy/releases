"""spots.py <map> [kind=glass|metal|water] [n] - camera spots in front of a map's reflective world surfaces.

Read-only: opens the retail paks, never writes into the game tree. Prints, per cluster of coplanar reflective faces,
the plane, its extent, and a `tele` / `face` pair that stands the player in front of it.
"""
import os, re, struct, sys, zipfile, math, collections

ROOT = r"G:\GOG\Medal of Honor - Allied Assault War Chest"


def paks():
    out = []
    for d in ("main", "mainta", "maintt"):
        for f in sorted(os.listdir(os.path.join(ROOT, d))):
            if re.match(r"(?i)pak\d.*\.pk3$", f):
                out.append(os.path.join(ROOT, d, f))
    return out


def shaders():
    env, allsh = {}, {}
    for p in paks():
        z = zipfile.ZipFile(p)
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
                    name, body = m.group(1).lower(), t[m.end():j].lower()
                    allsh[name] = body
                    # the engine's rule (tr_hzm_reflect.c HZM_ReflectShaderKind): the FIRST stage is an opaque env stage
                    st = re.search(r"\{([^{}]*)\}", body)
                    first = st.group(1) if st else ""
                    if re.search(r"tcgen\s+environment\s", first + " ") and "blendfunc" not in first and "deformvertexes" not in body:
                        env[name] = 1
                    else:
                        env.pop(name, None)
                    i = j
    return env, allsh


def load_bsp(name):
    data = None
    for p in paks():
        z = zipfile.ZipFile(p)
        for nm in z.namelist():
            if nm.lower() == "maps/%s.bsp" % name:
                data = z.read(nm)
    if data is None:
        raise SystemExit("no such map in the retail paks: " + name)
    return data


def main():
    mp = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 else "glass"
    topn = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    env, allsh = shaders()
    d = load_bsp(mp)
    ver = struct.unpack_from("<i", d, 4)[0]
    lumps = [struct.unpack_from("<ii", d, 12 + 8 * k) for k in range(28)]
    off = 0 if ver > 18 else 1
    so, sl = lumps[0]
    fo, fl = lumps[3 + off]
    vo, vl = lumps[4 + off]
    names = [d[so + 140 * k: so + 140 * k + 64].split(b"\0")[0].decode("latin-1").lower() for k in range(sl // 140)]
    groups = collections.OrderedDict()
    for k in range(fl // 108):
        sn, fog, stype, fv, nv = struct.unpack_from("<5i", d, fo + 108 * k)
        if not (0 <= sn < len(names)) or nv < 3:
            continue
        n = names[sn]
        isglass = bool(re.search(r"window|glass|win|pane", n))
        if kind == "water":
            if not re.search(r"water|river|canal|ocean|sea|sludge", n):
                continue
        elif n not in env or (kind == "glass") != isglass:
            continue
        vs = [struct.unpack_from("<3f8x8x3f", d, vo + 44 * (fv + i)) for i in range(nv)]
        nx = sum(v[3] for v in vs); ny = sum(v[4] for v in vs); nz = sum(v[5] for v in vs)
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nrm = (nx / ln, ny / ln, nz / ln)
        dist = sum(nrm[a] * vs[0][a] for a in range(3))
        fc = [sum(v[a] for v in vs) / len(vs) for a in range(3)]
        key = (round(nrm[0], 2), round(nrm[1], 2), round(nrm[2], 2), round(dist / 2.0), round(fc[0] / 400.0), round(fc[1] / 400.0), round(fc[2] / 400.0))
        g = groups.setdefault(key, {"n": nrm, "d": dist, "mins": [1e9] * 3, "maxs": [-1e9] * 3, "faces": 0, "sh": set()})
        for v in vs:
            for a in range(3):
                g["mins"][a] = min(g["mins"][a], v[a]); g["maxs"][a] = max(g["maxs"][a], v[a])
        g["faces"] += 1; g["sh"].add(n)
    rows = sorted(groups.values(), key=lambda g: -g["faces"])
    print("map %s kind %s groups %d" % (mp, kind, len(rows)))
    for g in rows[:topn]:
        c = [(g["mins"][a] + g["maxs"][a]) * 0.5 for a in range(3)]
        ext = [g["maxs"][a] - g["mins"][a] for a in range(3)]
        n = g["n"]
        if abs(n[2]) > 0.7:      # floor-like (rails, water): look down at it from the side
            pos = (c[0] + 120, c[1], c[2] + 40); yaw, pitch = 180.0, 20.0
        else:
            pos = (c[0] + n[0] * 110, c[1] + n[1] * 110, c[2] - 60)
            yaw, pitch = math.degrees(math.atan2(-n[1], -n[0])), 0.0
        print("faces %3d  n %5.2f %5.2f %5.2f  centre %7.0f %7.0f %7.0f  ext %4.0f %4.0f %4.0f  | tele %d %d %d ; face %d %d 0 | %s" % (
            g["faces"], n[0], n[1], n[2], c[0], c[1], c[2], ext[0], ext[1], ext[2], pos[0], pos[1], pos[2], pitch, yaw,
            ",".join(sorted(g["sh"]))[:70]))


main()
