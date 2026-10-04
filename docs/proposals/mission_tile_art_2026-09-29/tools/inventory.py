"""inventory.py - sweep every coop mission tile and join it with the authored titles (titles.json).

    python tools/inventory.py            # writes inventory.json + INVENTORY.md next to tools/

READ-ONLY on the mod tree and the retail install. Everything here is extracted:
  * slots / shaders / map commands / today's labels  <- hzm-mohaa-coop-mod/ui/coop_start/*.cfg (the dropdown order in coop_start.urc)
  * the image each shader resolves to, its size, md5 <- the mod tree first (it mounts last), else the retail paks
  * retail level titles                               <- each BSP's worldspawn "message"
  * retail checkpoint names                           <- global/savenames.scr (main, mainta, maintt)
  * the mod's own names                               <- coop_mod/variables.scr coop_mapDescription
Only the proposed caption (titles.json) is authored.
"""
import glob
import hashlib
import io
import json
import os
import re
import sys
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
G = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
sys.path.insert(0, HERE)
import fontfit  # noqa: E402


def retail_paks():
    out = []
    for d in ("main", "mainta", "maintt"):
        for p in sorted(glob.glob(os.path.join(G, d, "*.pk3")), key=str.lower):
            b = os.path.basename(p).lower()
            if "coop" in b or "co-op" in b or b.startswith("zz"):
                continue
            out.append(p)
    return out          # mount order: later wins


PAKS = retail_paks()
_INDEX = None


def index():
    global _INDEX
    if _INDEX is None:
        _INDEX = {}
        for p in PAKS:
            for n in zipfile.ZipFile(p).namelist():
                _INDEX[n.lower()] = (p, n)
    return _INDEX


def read_retail(name):
    hit = index().get(name.lower())
    return (zipfile.ZipFile(hit[0]).read(hit[1]), hit[0]) if hit else (None, None)


def resolve_image(shader):
    """menu shader path -> (where, bytes). Engine tries .dds? no - menu art: .jpg before .tga (TRAPS T6)."""
    for ext in (".jpg", ".tga", ".png"):
        p = os.path.join(MOD, shader.replace("/", os.sep) + ext)
        if os.path.exists(p):
            return "mod:" + shader + ext, open(p, "rb").read()
    for ext in (".jpg", ".tga", ".png"):
        b, pak = read_retail(shader + ext)
        if b:
            return "retail:%s:%s%s" % (os.path.relpath(pak, G), shader, ext), b
    return None, None


def worldspawn(bsp):
    b, _ = read_retail("maps/%s.bsp" % bsp)
    if not b:
        return None
    m = re.search(rb'\{[^{}]*"classname" "worldspawn"[^{}]*\}', b)
    if not m:
        return ""
    kv = dict(re.findall(rb'"([^"]+)" "([^"]*)"', m.group(0)))
    return kv.get(b"message", b"").decode("latin1")


def savenames():
    out = {}
    for pak_name in ("global/savenames.scr",):
        for p in PAKS:
            z = zipfile.ZipFile(p)
            if pak_name not in z.namelist():
                continue
            cur = None
            for line in z.read(pak_name).decode("latin1").splitlines():
                m = re.search(r'level\.script == "maps/([^"]+)\.scr"', line)
                if m:
                    cur = m.group(1).lower()
                m = re.search(r'local\.string = "([^"]+)"', line)
                if m and cur:
                    lst = out.setdefault(cur, [])
                    if m.group(1) not in lst:
                        lst.append(m.group(1))
    return out


def mod_descriptions():
    t = open(os.path.join(MOD, "coop_mod", "variables.scr"), encoding="latin-1").read()
    return {k.lower(): v for k, v in re.findall(r'coop_mapDescription\["([^"]+)"\]\s*=\s*"([^"]*)"', t)}


def dropdown_order():
    t = open(os.path.join(MOD, "ui", "coop_start.urc"), encoding="latin-1").read()
    return re.findall(r'addpopup "MENU" "([^"]+)" command "exec ui/coop_start/(\w+)\.cfg"', t)


def slots(cfg):
    t = open(os.path.join(MOD, "ui", "coop_start", cfg + ".cfg"), encoding="latin-1").read()
    live = [l for l in t.splitlines() if not l.strip().startswith("//")]
    txt = "\n".join(live)
    res = []
    for n in range(1, 12):
        sh = re.search(r"globalwidgetcommand coop_startMap%d shader \"?([^\"\s]+)" % n, txt)
        cmd = re.search(r'globalwidgetcommand coop_startMap%d stuffcommand "set ui_dmmap ([^;"]+)' % n, txt)
        ttl = re.search(r'globalwidgetcommand coop_startMap%d title "([^"]*)"' % n, txt)
        if cmd and sh:
            res.append({"slot": n, "shader": sh.group(1), "bsp": cmd.group(1).strip(),
                        "label_today": (ttl.group(1).strip() if ttl else "")})
    mission = re.search(r'globalwidgetcommand coop_missionName title "([^"]*)"', txt).group(1)
    return mission, res


def main():
    titles = json.load(open(os.path.join(HERE, "titles.json"), encoding="utf-8"))
    sv = savenames()
    md = mod_descriptions()
    rows, missions = [], []
    seen_md5 = {}
    for label, cfg in dropdown_order():
        mission, ss = slots(cfg)
        missions.append({"cfg": cfg, "dropdown": label, "header_today": mission,
                         **titles["missions"].get(cfg, {})})
        for s in ss:
            where, data = resolve_image(s["shader"])
            size = Image.open(io.BytesIO(data)).size if data else None
            h = hashlib.md5(data).hexdigest() if data else None
            bsp = s["bsp"]
            ws = worldspawn(bsp)
            t = titles["tiles"].get(bsp, {})
            r = dict(s, cfg=cfg, image=where, size=size, bytes=len(data) if data else 0, md5=h,
                     retail_title=ws, retail_checkpoints=sv.get(bsp.split("/")[-1].lower(), []),
                     mod_title=md.get(bsp.lower(), ""), kicker=t.get("kicker"), title=t.get("title"),
                     src=t.get("src"), note=t.get("note", ""))
            r["facfont20_units"] = round(fontfit.engine_width("facfont-20", r["title"] or ""), 1)
            seen_md5.setdefault(h, []).append(bsp)
            rows.append(r)
    for r in rows:
        dup = [b for b in seen_md5.get(r["md5"], []) if b != r["bsp"]]
        r["same_image_as"] = dup
    json.dump({"missions": missions, "tiles": rows}, open(os.path.join(PROP, "inventory.json"), "w", encoding="utf-8"), indent=1)
    write_md(missions, rows)
    missing = [r["bsp"] for r in rows if not r["title"]]
    print("tiles", len(rows), "missions", len(missions), "missing titles", missing)
    return 1 if missing else 0


def write_md(missions, rows):
    L = ["# Coop mission tiles - inventory and proposed titles (GENERATED by tools/inventory.py - do not edit)", ""]
    n_brief = sum(1 for r in rows if r["bsp"].startswith("briefing/"))
    fits = sum(1 for r in rows if r["facfont20_units"] <= 94)
    L += ["%d tiles in %d missions: %d levels + %d briefing rooms." % (len(rows), len(missions), len(rows) - n_brief, n_brief),
          "Titles that fit ONE engine facfont-20 line on today's 100-unit tile (<= 94 units usable): %d of %d." % (fits, len(rows)), ""]
    L += ["## Missions (dropdown)", "", "| cfg | today | retail name | proposed | why |", "|---|---|---|---|---|"]
    for m in missions:
        L.append("| %s | %s | %s | %s | %s |" % (m["cfg"], m["header_today"], m.get("retail", ""), m.get("proposed", ""), m.get("note", "")))
    L += ["", "## Tiles", "",
          "| cfg | slot | bsp | today's image | size | today's label | problem today | proposed **title** | source |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        prob = []
        if r["same_image_as"]:
            prob.append("same image as " + ", ".join(r["same_image_as"][:4]) + ("..." if len(r["same_image_as"]) > 4 else ""))
        if r["bsp"].startswith("briefing/brief") and r["cfg"][0] in "et" and "briefing1" in r["shader"]:
            prob.append("bug-3274: AA mission 1 Torch map")
        src = {"retail-ws": "retail: maps/%s.bsp worldspawn" % r["bsp"], "retail-save": "retail: global/savenames.scr",
               "retail-brief": "retail: maps/%s.bsp worldspawn" % r["bsp"], "mod": "mod: coop_mod/variables.scr",
               "retail-region": "retail: region from the campaign's level worldspawns (briefing BSP has no message)",
               "authored": "authored"}.get(r["src"], r["src"])
        L.append("| %s | %d | %s | `%s` | %s | %s | %s | **%s** | %s |" % (
            r["cfg"], r["slot"], r["bsp"], (r["image"] or "MISSING").split(":")[-1], "x".join(map(str, r["size"] or [])),
            r["label_today"] or "-", "; ".join(prob) or "-", r["title"], src))
    L += ["", "## Retail evidence per tile", "", "| bsp | worldspawn message | savenames checkpoints | mod coop_mapDescription | note |", "|---|---|---|---|---|"]
    for r in rows:
        L.append("| %s | %s | %s | %s | %s |" % (r["bsp"], r["retail_title"] or "-", " / ".join(r["retail_checkpoints"]) or "-",
                                                r["mod_title"] or "-", r["note"] or ""))
    open(os.path.join(PROP, "INVENTORY.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
