"""check_mpui.py [--mod DIR] - static checks for the mpui menus (no game client needed).

  * every file: ASCII only, uniform CRLF, no UTF-8 BOM
  * urc/inc: brace depth never negative and 0 at the end, every `resource` is followed by a class line and `{`,
    every include resolves to a file in the mod (or a retail include), `end.` present in menus
  * every `exec <cfg>` / `pushmenu <menu>` named in a stuffcommand resolves (a mod file / a menu in the mod or retail paks)
  * every multi-word title without digits has a localization entry (developer 1 prints LOCALIZATION ERROR otherwise)
  * the coop_start contract: hostRulesBtn rect = docs/tools/gen_menu_fieldsettings.py OPENER_RECT; Apply -> mission_start.cfg
    -> start_server.cfg ending in ui_startdmmap 2; the field cvars seeded in coop_defaults.cfg
Exit 1 on any problem."""
import glob, os, re, sys, zipfile

MOD = sys.argv[sys.argv.index("--mod") + 1] if "--mod" in sys.argv else r"C:\mohaa-coop-dev\hzm-mod-mpui"
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
UI = os.path.join(MOD, "ui")
FILES = ["joingame.urc", "coop_start.urc", "coop_maps.inc", "multiplayerstart.urc", "coop_mp_options.urc", "multiplayer.urc"] + \
        sorted(os.path.basename(p) for p in glob.glob(os.path.join(UI, "hzm_mpui_scene_*.inc")))
P = []

retail_ui = set()
menus = {}
for pk in glob.glob(os.path.join(GOG, "main*", "pak*.pk3")) + glob.glob(os.path.join(GOG, "main*", "Pak*.pk3")):
    try:
        z = zipfile.ZipFile(pk)
    except Exception:
        continue
    for n in z.namelist():
        if n.lower().startswith("ui/"):
            retail_ui.add(n.lower())
            if n.lower().endswith(".urc"):
                m = re.search(rb'(?m)^menu\s+"([^"]+)"', z.read(n)[:400])
                if m:
                    menus[m.group(1).decode("latin-1").lower()] = n
for p in glob.glob(os.path.join(UI, "*.urc")):
    m = re.search(r'(?m)^menu\s+"([^"]+)"', open(p, encoding="latin-1").read())
    if m:
        menus[m.group(1).lower()] = p

loc = open(os.path.join(MOD, "global", "localization_coop.txt"), encoding="latin-1").read()
keys = set(re.findall(r'\{ "([^"]*)" "', loc))
for g in glob.glob(os.path.join(GOG, "main*", "*.pk3")):
    pass   # the retail global/localization.txt keys: retail strings already exist there; only new ones are checked below

for f in FILES + ["../coop_defaults.cfg", "../global/localization_coop.txt"]:
    p = os.path.normpath(os.path.join(UI, f))
    raw = open(p, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        P.append("%s: UTF-8 BOM" % f)
    bad = [i for i, c in enumerate(raw) if c > 127]
    if bad:
        P.append("%s: %d non-ASCII bytes (first at %d)" % (f, len(bad), bad[0]))
    if raw.count(b"\r\n") != raw.count(b"\n"):
        P.append("%s: mixed line endings" % f)
    if not f.endswith((".urc", ".inc")):
        continue
    t = raw.decode("latin-1").replace("\r\n", "\n")
    body = re.sub(r"//[^\n]*", "", t)
    depth = 0
    for ln, line in enumerate(body.split("\n"), 1):
        q = re.sub(r'"[^"]*"', "", line)
        depth += q.count("{") - q.count("}")
        if depth < 0:
            P.append("%s:%d brace depth negative" % (f, ln))
            break
    if depth != 0:
        P.append("%s: brace depth %d at end" % (f, depth))
    for m in re.finditer(r"(?m)^resource\n(\w+)\n(.)", body):
        if m.group(2) != "{":
            P.append("%s: resource %s not followed by {" % (f, m.group(1)))
    if f.endswith(".urc") and not re.search(r"(?m)^end\.\s*$", body):
        P.append("%s: no end." % f)
    for inc in re.findall(r'(?m)^include\s+"([^"]+)"', body):
        if not os.path.exists(os.path.join(MOD, inc)) and inc.lower() not in retail_ui:
            P.append("%s: include %s not found" % (f, inc))
    for cmd in re.findall(r'(?:stuffcommand|escapecommand|showcommand)\s+"([^"]*)"', body):
        for c in [x.strip() for x in cmd.split(";")]:
            c = re.sub(r"^uiafter \S+ ", "", c)
            m = re.match(r"exec\s+(\S+)", c)
            if m and not os.path.exists(os.path.join(MOD, m.group(1))) and m.group(1) not in ("net_cl.cfg", "net_sv.cfg"):
                P.append("%s: exec %s - no such file in the mod" % (f, m.group(1)))
            m = re.match(r"pushmenu\s+(\S+)", c, re.I)
            if m and m.group(1).lower() not in menus:
                P.append("%s: pushmenu %s - no such menu" % (f, m.group(1)))
    for title in re.findall(r'(?m)^\s*title\s+"([^"]*)"', body):
        s = title.replace("\\n", " ").strip()
        if " " in s and not re.search(r"\d", s) and s not in keys:
            P.append("%s: title '%s' has no localization entry" % (f, s))

# net_cl.cfg / net_sv.cfg: the retail-era network presets the old menus exec'd (mod root)
for c in ("net_cl.cfg", "net_sv.cfg"):
    if not os.path.exists(os.path.join(MOD, c)):
        P.append("exec %s: not in the mod root" % c)

cs = open(os.path.join(UI, "coop_start.urc"), encoding="latin-1").read().replace("\r\n", "\n")
fs = open(r"C:\mohaa-coop-dev\docs\tools\gen_menu_fieldsettings.py", encoding="utf-8").read()
want = re.search(r'"hostRulesBtn", \((\d+), (\d+), (\d+), (\d+)\)', fs).groups()
got = re.search(r'name "hostRulesBtn"\nrect (\d+) (\d+) (\d+) (\d+)', cs).groups()
if want != got:
    P.append("hostRulesBtn rect %s != gen_menu_fieldsettings OPENER_RECT %s" % (got, want))
if 'stuffcommand "wait 250;exec coop_mod/cfg/mission_start.cfg"' not in cs:
    P.append("coop_start apply no longer execs mission_start.cfg")
ms = open(os.path.join(MOD, "coop_mod", "cfg", "mission_start.cfg"), encoding="latin-1").read()
ss = [l.strip() for l in open(os.path.join(MOD, "coop_mod", "start_server.cfg"), encoding="latin-1").read().splitlines() if l.strip() and not l.strip().startswith("//")]
if "exec coop_mod/start_server.cfg" not in ms or "ui_startdmmap 2" not in ss:
    P.append("mission_start.cfg -> start_server.cfg -> ui_startdmmap 2 chain broken")
dflt = open(os.path.join(MOD, "coop_defaults.cfg"), encoding="latin-1").read()
for cv in re.findall(r'name "fld_(\w+)"', cs):
    if cv in ("sv_hostname", "password"):
        continue
    if not re.search(r"(?m)^seta %s " % cv, dflt):
        P.append("coop_start field %s is not seeded in coop_defaults.cfg (shows empty on a clean profile)" % cv)
if re.search(r'(?m)^shader "textures/menu/checkbox_(un)?checked"', cs) or "CheckBox" in cs:
    P.append("coop_start still has a stock CheckBox (renders as a black square on the paper sheet)")
if "nomap" in open(os.path.join(UI, "multiplayerstart.urc"), encoding="latin-1").read():
    P.append("multiplayerstart still opens coop_start with ui_dmmap nomap")

print("\n".join(P) if P else "check_mpui: OK (%d files)" % len(FILES))
sys.exit(1 if P else 0)
