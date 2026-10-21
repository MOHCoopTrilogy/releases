"""vo.py <regex> [mapprefix] - SHIPPED alias lines (wav/mp3 present in the retail paks) whose subtitle text matches; maps-field prefix rule applied."""
import re, sys, glob, os, zipfile, pickle
SP = "C:/mohaa-coop-dev/hzm-mod-objectives2/ubersound/"
CACHE = "C:/Users/curry/AppData/Local/Temp/claude/C--mohaa-coop-dev/0ef9c092-ae3c-4811-a8c8-d3c6c827d23b/scratchpad/stock/_pakset.pkl"
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
if os.path.exists(CACHE):
    pak = pickle.load(open(CACHE, "rb"))
else:
    pak = set()
    for d in ("main", "mainta", "maintt"):
        for f in glob.glob(os.path.join(GOG, d, "*.pk3")):
            for n in zipfile.ZipFile(f).namelist():
                if n.lower().startswith("sound/"):
                    pak.add(n.lower())
    pickle.dump(pak, open(CACHE, "wb"))
pat = re.compile(sys.argv[1], re.I)
mp = sys.argv[2] if len(sys.argv) > 2 else None
for fn in ("uberdialog.scr", "ubersound.scr"):
    for ln in open(SP + fn, encoding="latin-1"):
        if not ln.startswith(("alias", "aliascache")):
            continue
        m = re.search(r'subtitle "([^"]*)"', ln)
        if not m or not pat.search(m.group(1)):
            continue
        parts = ln.split()
        a, wav = parts[1], parts[2].lower()
        shipped = wav in pak
        mm = re.search(r'maps "([^"]*)"', ln)
        maps = mm.group(1).split() if mm else []
        always = " always" in ln
        ok = True
        if mp and maps and not always:
            ok = any(mp.startswith(t) for t in maps)
        if ok and shipped:
            print("%-26s [%s] %s" % (a, " ".join(maps), m.group(1)[:100]))
