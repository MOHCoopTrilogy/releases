#!/usr/bin/env python3
"""BRING-YOUR-OWN-DISC GUARD (v1.10.68). Fails (exit 1) if anything converted from - or copied off - a Medal of Honor:
Frontline or European Assault disc is about to be built, committed, published or deployed to a public server.

  python docs/tools/byo_guard.py PATH [PATH ...]     (files, folders, .pk3/.zip archives; folders are walked)

The rule (user 2026-11-08/09): those missions exist ONLY on a PC that converted its own disc. Git, the release zips,
the updater payload and the public servers never carry the converted paks, their textures/audio/text/films, or raw disc
files. What is checked:
  * names  - the converter's own pak names (zzzz_coop_fl_*, zzzz_coop_ea_*, zzzz_fl_*, zzzz_ea_*), disc images and raw
             disc containers (.iso .xiso .xbe .viv .big);
  * paths  - every path the converter writes (maps/coop_fl_*.bsp, textures/fl/..., sound/ea/..., video/flbrief*, the
             fl/ea markers ...), loose in a folder or as an entry of any .pk3/.zip;
  * bytes  - the first 4 bytes of loose files and archive entries that do not have a known-safe extension, against the
             disc container magics (BIGF/BIG4 viv, SCHl EA audio, SHPX/SHPS shapes, MPCh EA music, XBEH executables).
Our own committed scripts for those maps (maps/coop_fl_1_1.scr, maps/briefing/briefingfl1.scr ...) are NOT matched:
they are our code, and only read the data the converter generates locally.
"""
import fnmatch
import os
import sys
import zipfile

LEAF = ["zzzz_coop_fl_*", "zzzz_coop_ea_*", "zzzz_fl_*", "zzzz_ea_*", "*.iso", "*.xiso", "*.xbe", "*.viv", "*.big"]
PATHS = ["maps/coop_fl_*.bsp", "maps/coop_ea_*.bsp", "maps/coop_fl_*_data.scr", "maps/coop_ea_*_data.scr",
         "maps/briefing/briefingfl*.bsp", "maps/briefing/briefingea*.bsp",
         "textures/fl/*", "textures/ea/*", "sound/fl/*", "sound/ea/*", "sound/music/fl_*", "sound/music/ea_*",
         "scripts/fl_*.shader", "scripts/ea_*.shader", "ubersound/fl_*.scr", "ubersound/ea_*.scr",
         "video/flbrief*", "video/ea*intro*", "fl/have_*", "ea/have_*"]
# User decision (2026-11-09, again at v1.10.69): the Frontline SOUNDTRACK already in the shipped music pak stays -
# zzzzzzzzzzzzz_coop_music.pk3 :: sound/music/frontline_*.mp3 and sound/frontline/*. It is never flagged.
EXEMPT = ["sound/music/frontline_*", "sound/frontline/*"]
MAGIC = [b"BIGF", b"BIG4", b"SCHl", b"SHPX", b"SHPS", b"MPCh", b"XBEH"]
SAFE = {".tga", ".jpg", ".jpeg", ".dds", ".png", ".bmp", ".wav", ".mp3", ".ogg", ".tik", ".skd", ".skc", ".skb", ".ska",
        ".scr", ".cfg", ".urc", ".inc", ".shader", ".txt", ".md", ".json", ".tsv", ".csv", ".bsp", ".roq", ".tik",
        ".py", ".pyc", ".pyd", ".dll", ".exe", ".zip", ".pk3", ".ps1", ".vbs", ".ini", ".st", ".str", ".ttf", ".ritualfont",
        ".lip", ".mdl", ".spr", ".def", ".map", ".anim", ".h", ".c", ".cpp", ".sh", ".spec", ".html", ".css", ".js",
        ".svg", ".gif", ".mp4", ".log", ".bak", ".pdb", ".lib", ".manifest", ".cat", ".typed", ".pyi", ".gz", ".dat"}


def leaf_hit(name):
    n = os.path.basename(name).lower()
    return next((p for p in LEAF if fnmatch.fnmatch(n, p)), None)


def path_hit(rel):
    r = rel.replace("\\", "/").lower().lstrip("/")
    if any(fnmatch.fnmatch(r, e) or fnmatch.fnmatch(r, "*/" + e) for e in EXEMPT):
        return None
    # a folder of paks is checked relative to every level, so maintt/maps/... and maps/... both match
    parts = r.split("/")
    for i in range(len(parts)):
        sub = "/".join(parts[i:])
        for p in PATHS:
            if fnmatch.fnmatch(sub, p):
                return p
    return None


def magic_hit(head, name):
    ext = os.path.splitext(name)[1].lower()
    if ext in SAFE:
        return None
    return next((m.decode() for m in MAGIC if head.startswith(m)), None)


def scan_archive(path, label, bad):
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as e:
        if path.lower().endswith(".pk3"):
            bad.append("%s: unreadable archive (%s)" % (label, e))
        return
    with z:
        for i in z.infolist():
            if i.is_dir():
                continue
            if any(fnmatch.fnmatch(i.filename.lower(), e) for e in EXEMPT):
                continue
            why = leaf_hit(i.filename) or path_hit(i.filename)
            if not why and os.path.splitext(i.filename)[1].lower() not in SAFE and i.file_size >= 4:
                try:
                    with z.open(i) as f:
                        why = magic_hit(f.read(4), i.filename)
                except Exception:
                    why = None
            if why:
                bad.append("%s :: %s  (%s)" % (label, i.filename, why))


def scan(target, bad):
    if os.path.isfile(target):
        files = [(target, os.path.basename(target))]
        base = os.path.dirname(target)
    else:
        base = target
        files = []
        for d, dirs, fs in os.walk(target):
            dirs[:] = [x for x in dirs if x != ".git"]
            for n in fs:
                p = os.path.join(d, n)
                files.append((p, os.path.relpath(p, target)))
    for p, rel in files:
        why = leaf_hit(rel) or path_hit(rel)
        if why:
            bad.append("%s  (%s)" % (p, why))
            continue
        low = p.lower()
        if low.endswith((".pk3", ".zip")):
            scan_archive(p, p, bad)
        elif os.path.splitext(low)[1] not in SAFE:
            try:
                with open(p, "rb") as f:
                    why = magic_hit(f.read(4), p)
            except OSError:
                why = None
            if why:
                bad.append("%s  (%s)" % (p, why))


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    bad = []
    for t in argv:
        if not os.path.exists(t):
            print("byo_guard: missing %s" % t)
            return 2
        scan(t, bad)
    if bad:
        print("BYO GUARD: %d item(s) from a Frontline / European Assault disc are staged - they must never ship:" % len(bad))
        for b in bad[:60]:
            print("  " + b)
        if len(bad) > 60:
            print("  ... and %d more" % (len(bad) - 60))
        return 1
    print("byo guard: pass (%d path(s) checked)" % len(argv))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
