"""water_audit.py - GENERATED audit of water on every campaign map (AA, SH, BT). Writes ../WATER_AUDIT.md.

Read-only on the game tree and the engine tree. For every campaign BSP in the retail paks it applies the engine's own
rules offline (renderercommon/hzm_waterwet.h allowlist; tr_hzm_water.c R_HZMWaterBuildPlanar levels):
  * the allowlisted water shaders the map uses and how many surfaces,
  * the water levels (flat sheets grouped by height), the dominant one, its extent,
  * whether that body RUNS OFF THE MAP (its extent reaches the edge of the map's geometry within 512 units) - the rule
    that switches the far water plane on - and on which sides,
  * scripted cameras (func_camera entities) and how many of them stand over or beside that water: a cinematic camera
    sees far past anything a player can reach,
  * boats (script objects / models named boat) - how the rowboat map is found.
The per-map numbers are also what the engine prints at map load as `^~^~^ HZMWATERFAR`.
"""
import os, re, struct, zipfile, collections

ROOT = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
ENG = os.environ.get("HZM_ENG", r"H:\hzm_work\eng-hotfix13661\code")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "WATER_AUDIT.md")
OMAHA = ("m3l1a", "m3l1b", "e3l1", "e3l2")
ICE = "textures/central_europe_winter/frozenriver"


def allowlist():
    t = open(os.path.join(ENG, "renderercommon", "hzm_waterwet.h"), encoding="latin-1").read()
    a = t.index("allow[HZM_WATER_NUM_ALLOW]")
    b = t.index("};", a)
    return [s.lower() for s in re.findall(r'"([^"]+)"', t[a:b])]


def main():
    allow = set(allowlist())
    rows = []
    seen = set()
    for d in ("maintt", "mainta", "main"):          # the highest-priority copy of a map wins
        for f in sorted(os.listdir(os.path.join(ROOT, d)), reverse=True):
            if not re.match(r"(?i)pak\d.*\.pk3$", f):
                continue
            z = zipfile.ZipFile(os.path.join(ROOT, d, f))
            for nm in z.namelist():
                l = nm.lower()
                if not (l.startswith("maps/") and l.endswith(".bsp") and l.count("/") == 1):
                    continue
                base = l[5:-4]
                if not re.match(r"(m\dl\d\w?|t\dl\d\w?|e\dl\d\w?)$", base) or base in seen:
                    continue
                seen.add(base)
                b = z.read(nm)
                ver = struct.unpack_from("<i", b, 4)[0]
                lumps = [struct.unpack_from("<ii", b, 12 + 8 * k) for k in range(28)]
                off = 0 if ver > 18 else 1
                so, sl = lumps[0]
                fo, fl = lumps[3 + off]
                vo, vl = lumps[4 + off]
                eo, el = lumps[14 + off] if False else (0, 0)
                names = [b[so + 140 * k: so + 140 * k + 64].split(b"\0")[0].decode("latin-1").lower() for k in range(sl // 140)]
                levels, used = [], collections.Counter()
                mb = [1e30, 1e30, -1e30, -1e30]
                for k in range(fl // 108):
                    sn, fog, stype, fv, nv = struct.unpack_from("<5i", b, fo + 108 * k)
                    if not (0 <= sn < len(names)) or nv < 3:
                        continue
                    n = names[sn]
                    xs, ys, zs = [], [], []
                    for i in range(nv):
                        x, y, zz = struct.unpack_from("<3f", b, vo + 44 * (fv + i))
                        xs.append(x); ys.append(y); zs.append(zz)
                    if n not in allow:
                        if "sky" not in n and "common/" not in n:
                            mb = [min(mb[0], min(xs)), min(mb[1], min(ys)), max(mb[2], max(xs)), max(mb[3], max(ys))]
                        continue
                    used[n] += 1
                    if n == ICE or max(zs) - min(zs) > 8:
                        continue
                    a = (max(xs) - min(xs)) * (max(ys) - min(ys))
                    zc = 0.5 * (max(zs) + min(zs))
                    L = next((L for L in levels if abs(L["z"] - zc) < 6), None)
                    if L is None:
                        L = {"z": zc, "area": 0.0, "box": [1e30, 1e30, -1e30, -1e30], "best": 0.0, "sh": n}
                        levels.append(L)
                    L["area"] += a
                    L["box"] = [min(L["box"][0], min(xs)), min(L["box"][1], min(ys)), max(L["box"][2], max(xs)), max(L["box"][3], max(ys))]
                    if a > L["best"]:
                        L["best"], L["sh"] = a, n
                # entity lump: find by content (the lump index differs between BSP versions)
                ents = ""
                for (o, ln) in lumps:
                    if ln > 16 and b[o:o + 1] == b"{" and b"classname" in b[o:o + 4096]:
                        ents = b[o:o + ln].decode("latin-1", "replace")
                        break
                cams = [tuple(float(v) for v in m.group(1).split()) for m in re.finditer(
                    r'\{[^{}]*"classname"\s+"func_camera"[^{}]*?"origin"\s+"([-\d. ]+)"[^{}]*\}|\{[^{}]*"origin"\s+"([-\d. ]+)"[^{}]*?"classname"\s+"func_camera"[^{}]*\}', ents)
                    if m.group(1)]
                cams += [tuple(float(v) for v in m.group(2).split()) for m in re.finditer(
                    r'\{[^{}]*"origin"\s+"([-\d. ]+)"[^{}]*?"classname"\s+"(func_camera)"[^{}]*\}', ents)] if False else []
                scr = os.path.join(r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\maps", base + ".scr")
                if os.path.exists(scr):
                    st = open(scr, encoding="latin-1").read()
                    cams += [tuple(float(v) for v in m.groups()) for m in re.finditer(
                        r"movetopos\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\)", st)]
                boat = len(re.findall(r'(?i)"(?:model|targetname)"\s+"[^"]*boat[^"]*"', ents))
                if not used:
                    continue
                r = {"map": base, "used": used, "levels": levels, "cams": len(cams), "boat": boat, "omaha": base in OMAHA}
                if levels:
                    D = max(levels, key=lambda L: L["area"])
                    bx = D["box"]
                    touch = [s for s, c in (("-x", bx[0] <= mb[0] + 512), ("+x", bx[2] >= mb[2] - 512),
                                            ("-y", bx[1] <= mb[1] + 512), ("+y", bx[3] >= mb[3] - 512)) if c]
                    diag = ((bx[2] - bx[0]) ** 2 + (bx[3] - bx[1]) ** 2) ** 0.5
                    near = sum(1 for c in cams if bx[0] - 1500 < c[0] < bx[2] + 1500 and bx[1] - 1500 < c[1] < bx[3] + 1500 and c[2] > D["z"])
                    r.update(z=D["z"], area=D["area"], box=bx, mapbox=mb, touch=touch, diag=diag, sh=D["sh"], camsnear=near,
                             far=bool(touch) and diag >= 1500 and base not in OMAHA)
                rows.append(r)
    rows.sort(key=lambda r: (not r.get("far", False), -r.get("area", 0)))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Water audit - GENERATED by tools/water_audit.py, do not edit\n\n")
        f.write("Campaign maps with allowlisted water: %d. Far water plane switches on for: %s.\n\n" % (
            len(rows), ", ".join(r["map"] for r in rows if r.get("far")) or "none"))
        f.write("Look: every non-Omaha map gets the cold-sea preset; `frozenriver` stays ice; Omaha keeps its own presets.\n\n")
        f.write("| map | water surfaces | levels | waterline z | extent (x by y) | runs off the map | far plane | cameras (near water / all) | boats | main shader |\n")
        f.write("|---|---:|---:|---:|---|---|---|---|---:|---|\n")
        for r in rows:
            if "z" not in r:
                f.write("| %s | %d | 0 (ice or sloped only) | - | - | - | no | -/%d | %d | %s |\n" % (
                    r["map"], sum(r["used"].values()), r["cams"], r["boat"], next(iter(r["used"])).replace("textures/", "")))
                continue
            f.write("| %s%s | %d | %d | %.0f | %.0f by %.0f | %s | %s | %d/%d | %d | %s |\n" % (
                r["map"], " (Omaha: untouched)" if r["omaha"] else "", sum(r["used"].values()), len(r["levels"]), r["z"],
                r["box"][2] - r["box"][0], r["box"][3] - r["box"][1], " ".join(r["touch"]) or "no",
                "ON" if r["far"] else "no", r["camsnear"], r["cams"], r["boat"], r["sh"].replace("textures/", "")))
    for r in rows:
        if "z" in r:
            print("%-6s z %6.0f box %6.0f %6.0f %6.0f %6.0f touch %-12s far %-3s cams %d/%d boats %d %s" % (
                r["map"], r["z"], r["box"][0], r["box"][1], r["box"][2], r["box"][3], " ".join(r["touch"]) or "-",
                "ON" if r["far"] else "no", r["camsnear"], r["cams"], r["boat"], r["sh"]))
        else:
            print("%-6s (no flat non-ice water) %s" % (r["map"], list(r["used"])[:2]))


main()
