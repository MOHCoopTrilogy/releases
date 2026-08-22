#!/usr/bin/env python
"""gen_chatter_pools.py -> ubersound/coop_chatter.scr

Cut-content restoration (2026-08-19 deep scan): folds three never-played retail VO layers
into the existing situational AI-voice driver (coop_mod/aivoice.scr, pools coop_av_<nat>_<sit>):

1. BT "Global Dialog" squad barks (maintt uberdialog, 331 aliases, e-map gated in retail) -
   each line carries a // meaning comment; we CLASSIFY per line into the driver's situations
   by comment keywords and emit extra takes into the matching pools.
2. German personality audio (AA, m-map gated): den_fear takes -> NEW pool coop_av_de_fear;
   laugh+joke idles -> NEW pool coop_av_de_banter; BT "Hands up!" (e1l4-gated) ->
   NEW pool coop_av_de_handsup.
3. Allied shout categories: dfrus/dfruk/dfr _reload takes -> EXISTING us/uk reload pools
   (zero new hooks); dfrus/dfruk/dfr _supress takes -> NEW pools coop_av_us/uk_suppress.

Sound params are copied from the retail alias lines with the maps gate replaced by `always`,
which is the token that actually makes a pool resolve on every map. Stripping `maps` alone does
NOT do that - it makes bLoadForMap fail and the alias is never registered at all. Rerunnable; output is
generated - do not hand-edit coop_chatter.scr.
"""
import re, io, glob, zipfile, os

GOG = r"G:/GOG/Medal of Honor - Allied Assault War Chest"
OUT = os.path.join(os.path.dirname(__file__), "..", "..",
                   "hzm-mohaa-coop-mod", "ubersound", "coop_chatter.scr")

def alias_lines():
    # yields (sub, name, path, rest, groupmeaning) - the BT global section documents each
    # take-GROUP with a preceding "// Alias <base>  <meaning>" comment line; carry it forward
    # so every take in the group classifies by the line it actually speaks.
    for sub in ("main", "mainta", "maintt"):
        for pk in sorted(glob.glob(GOG + "/" + sub + "/[Pp]ak*.pk3")):
            z = zipfile.ZipFile(pk)
            for n in z.namelist():
                if "ubersound" in n.lower() or "uberdialog" in n.lower():
                    meaning_base, meaning = None, ""
                    for ln in z.read(n).decode("latin-1", errors="replace").splitlines():
                        cm = re.match(r'\s*//\s*Alias\s+(\S+)\s+(.*)', ln)
                        if cm:
                            meaning_base, meaning = cm.group(1).lower(), cm.group(2).strip().lower()
                            continue
                        m = re.match(r'\s*alias(?:cache)?\s+(\S+)\s+(\S+)(.*)', ln)
                        if m:
                            gm = meaning if (meaning_base and m.group(1).lower().startswith(meaning_base)) else ""
                            yield sub, m.group(1), m.group(2), m.group(3), gm

# comment-keyword -> driver situation (checked in order; first hit wins)
CLASSIFY = [
    (("grenade", "granate"), "grenade"),
    (("cover", "get down", "take cover", "duck"), "cover"),
    (("fall back", "retreat", "pull back", "fallback"), "fallback"),
    (("man down", "medic", "he's hit", "hes hit", "they got"), "mandown"),
    (("reload", "loading"), "reload"),
    (("over here", "this way", "on me", "follow"), "backup"),
    (("enemy", "contact", "there they", "i see", "spotted", "sighted"), "contact"),
    (("fire", "shoot", "attack", "get them", "kill", "charge"), "attack"),
]
NATMAP = {"allied_american_global": "us", "allied_british_global": "uk",
          "axis_german_global": "de", "axis_italian_global": "it"}

pools = {}   # (nat, sit) -> list of (path, parms)
def add(nat, sit, path, parms):
    # [2026-08-21] STRIPPING `maps` DOES NOT MEAN "LOADS EVERYWHERE" - IT MEANS "LOADS NOWHERE".
    # bLoadForMap (fgame/scriptmaster.cpp:417) on an EMPTY maps buffer prints
    #   "ERROR bLoadForMap: <name> alias with empty maps specification."
    # and returns false, and RegisterAlias only calls GlobalAlias_Add inside that gate unless the
    # line carries `always`. So every line this generator emitted was silently unregistered: 1389
    # aliases, 2778 parse errors per map load, and the AI combat chatter never played once. The
    # intent below was right; the mechanism was exactly inverted.
    #
    # `always` is the token that genuinely means "resolve on every map". It is deliberately NOT
    # paired with a maps list: `always` reaches GlobalAlias_Add unconditionally while leaving
    # CacheResource behind the same gate, so these register WITHOUT precaching. Adding a maps list
    # would precache all 1389 files and blow MAX_SOUNDS (2048, ~1616 already used on a live map).
    # They are `streamed` dialogue, so lazy registration is the right trade.
    parms = re.sub(r'\s*maps\s+"[^"]*"', '', parms).rstrip() + ' always'
    pools.setdefault((nat, sit), []).append((path, parms))

seen = set()
# [user 2026-08-21 / bug-2021] EXISTENCE FILTER. Retail's own alias files reference 34 mp3s
# (dfr_supress_* under Mission_N/Allies) that were cut MORE deeply than their aliases - the
# takes exist in no pak and no loose tree. Emitting them produced aliases that error at play
# time on every machine. An alias only makes it into the pool if its file is actually present
# in a retail pak or in the mod source tree (what build.ps1 packs) - the SHIPPED set, never
# the dev machine's loose files, which is exactly the trap that hid 1,623 dead refs (bug-2020).
MOD = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'hzm-mohaa-coop-mod'))
_have = set()
for _sub in ('main', 'mainta', 'maintt'):
    for _pk in glob.glob(GOG + '/' + _sub + '/[Pp]ak*.pk3'):
        try:
            for _n in zipfile.ZipFile(_pk).namelist():
                _have.add(_n.lower())
        except Exception:
            pass
for _dp, _, _fs in os.walk(MOD):
    for _fn in _fs:
        _have.add(os.path.relpath(os.path.join(_dp, _fn), MOD).replace(os.sep, '/').lower())
_dropped = []

for sub, name, path, rest, groupmeaning in alias_lines():
    if path.lower() not in _have:
        _dropped.append(path)
        continue
    lo = name.lower()
    key = (lo, path.lower())
    if key in seen:
        continue
    seen.add(key)
    # 1. global dialog, classified by meaning comment
    for pref, nat in NATMAP.items():
        if lo.startswith(pref):
            cm = rest.split("//", 1)
            comment = groupmeaning or (cm[1].lower() if len(cm) > 1 else "")
            parms = cm[0]
            sit = "attack"
            for keys, s in CLASSIFY:
                if any(k in comment for k in keys):
                    sit = s
                    break
            add(nat, sit, path, parms)
            break
    else:
        # 2. personality
        if lo.startswith("den_fear"):
            add("de", "fear", path, rest.split("//", 1)[0])
        elif lo.startswith("snd_den_laugh_generic") or lo.startswith("snd_den_joke_generic"):
            add("de", "banter", path, rest.split("//", 1)[0])
        elif lo.startswith("snd_den_handups_generic"):
            add("de", "handsup", path, rest.split("//", 1)[0])
        # 3. allied shouts
        elif re.match(r'dfrus_sup+ress', lo):
            add("us", "suppress", path, rest.split("//", 1)[0])
        elif re.match(r'dfruk_sup+ress', lo):
            add("uk", "suppress", path, rest.split("//", 1)[0])
        elif re.match(r'dfr_sup+ress', lo):
            add("us", "suppress", path, rest.split("//", 1)[0])
            add("uk", "suppress", path, rest.split("//", 1)[0])
        elif lo.startswith("dfrus_reload"):
            add("us", "reload", path, rest.split("//", 1)[0])
        elif lo.startswith("dfruk_reload"):
            add("uk", "reload", path, rest.split("//", 1)[0])
        elif lo.startswith("dfr_reload"):
            add("us", "reload", path, rest.split("//", 1)[0])
            add("uk", "reload", path, rest.split("//", 1)[0])

L = ["// GENERATED by docs/tools/gen_chatter_pools.py - DO NOT EDIT.",
     "// Cut-content VO folded into the aivoice pools. Every line carries `always`: the retail maps",
     "// gate is replaced, NOT merely stripped - an alias with no maps and no always fails",
     "// bLoadForMap and is never registered at all (that bug cost 1389 dead aliases).",
     ""]
total = 0
for (nat, sit) in sorted(pools):
    takes = pools[(nat, sit)]
    L.append("// %s / %s - %d takes" % (nat, sit, len(takes)))
    for path, parms in takes:
        L.append("alias coop_av_%s_%s %s%s" % (nat, sit, path, (" " + parms.strip()) if parms.strip() else ""))
    L.append("")
    total += len(takes)
io.open(OUT, "wb").write(("\r\n".join(L) + "\r\n").encode("latin-1"))
summary = {}
for (nat, sit), t in pools.items():
    summary.setdefault(sit, 0)
    summary[sit] += len(t)
print("coop_chatter.scr: %d takes across %d pools" % (total, len(pools)))
print("by situation:", dict(sorted(summary.items(), key=lambda x: -x[1])))
if _dropped:
    print("  dropped %d aliases whose files exist nowhere shipped" % len(set(_dropped)))
