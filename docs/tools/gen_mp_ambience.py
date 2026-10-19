#!/usr/bin/env python3
"""Generate coop_mod/mp_ambience_bsp.scr - MP environmental ambience for the BSP-derived Push maps
(Tier-1 + Tier-2). MP runs these campaign maps script-less, so their SP ambience (global/ambience.scr
coord beds + the map script's own ambient loopsounds) never fires. This harvests both and replays them
in MP via mp_ambience.scr::emit, exactly like the hand-authored 7 originals in mp_ambience.scr::start.

SOURCES (in priority):
  1. global/ambience.scr  - the per-map `thread sound (x y z) alias` beds (crickets/wind/fire/water).
     These ARE the environmental system, so every entry is safe to replay wholesale.
  2. maps/<map>.scr       - `$<ent> loopsound <alias>` lines, FILTERED to ambient aliases only
     (radio/fire/wind/water/engine/hum/generator/barn...) and never event sounds (alarm/bomb/tick/
     explo/siren/gun/voice). Replayed as `if($ent!=NULL){ $ent loopsound alias }`.
  3. Fallback            - a map with neither gets a corridor wind bed (mp_ambience.scr::bedWind).

Run:  python docs/tools/gen_mp_ambience.py
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD  = os.path.join(ROOT, "hzm-mohaa-coop-mod")
OUT  = os.path.join(MOD, "coop_mod", "mp_ambience_bsp.scr")

MAPS = ["t3l1","t2l1","t2l3","t2l4","m5l2a","m5l2b","m3l1b",
        "m2l3","m1l3a","m1l3b","e1l1","e3l1","e3l2","e3l3","t1l1","t1l2","t1l3","m5l3"]

AMBIENT_OK = re.compile(r"radio|fire|wind|water|river|ocean|wave|cricket|bird|_hum|hum2|hum1|engine|"
                        r"generator|machin|boiler|steam|flag|ambien|rain|forest|camp|torch|drone|"
                        r"idle|rolling|electrical|spark|surf|creek|waterfall|frog|owl|insect|barn", re.I)
EVENT_BAD  = re.compile(r"alarm|bomb|tick|explo|siren|gun|shot|voice|dialog|footstep|pain|death|"
                        r"scream|whistle|_vo_|radiovox|announce|count", re.I)

# [bug-2780] AA/Spearhead ambient aliases -> the nearest alias that EXISTS in the Breakthrough (maintt,
# com_target_game 2) ubersound set the servers + coop actually load. Left side = harvested-but-invalid,
# right side = verified present in maintt (base pak1/pak3 + the mod's own ubersound.scr). Keep this in sync
# if the harvest surfaces a new alias: any alias not in maintt loopsound-fails silently (no ambience).
MAINTT_ALIAS_REMAP = {
    "wind_trees4": "coop_amb_wind", "wind_trees5": "coop_amb_wind", "wind_trees6": "coop_amb_wind", "wind_trees7": "coop_amb_wind",
    "fire_large": "coop_amb_fire", "fire_med": "coop_amb_fire", "fire_med2": "coop_amb_fire", "fire_small1": "coop_amb_fire",
    "m2l1_radio2": "coop_amb_machine", "m2l1_radio3": "coop_amb_machine",
    "m2l3_radio1": "coop_amb_machine", "m2l3_radio2": "coop_amb_machine", "m3l1b_radio2": "coop_amb_machine",
    "m4l2_radio": "coop_amb_machine", "radio_loop3": "coop_amb_machine",
    "e3l1_machine_loop": "coop_amb_machine", "machine_loop": "coop_amb_machine", "electrical_hum2": "coop_amb_machine",
}

def ambience_beds():
    """map -> list of (x,y,z,alias) from global/ambience.scr. Handles OR'd conditions
    (if(A||B||C){sounds}): all maps named in one block's condition share its sounds."""
    txt = open(os.path.join(MOD, "global", "ambience.scr"), encoding="latin-1").read()
    beds = {}
    pending = []       # map keys of the CURRENT block's condition
    in_body = False    # have we seen this block's sounds yet?
    for ln in txt.splitlines():
        m = re.search(r'level\.script\s*==\s*"maps/([^"]+)\.scr"', ln)
        if m:
            if in_body:            # a new else-if after the previous block's sounds -> reset
                pending = []
                in_body = False
            key = m.group(1).lower().split("/")[-1]
            pending.append(key)
            beds.setdefault(key, [])
            continue
        s = re.search(r'thread\s+sound\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\)\s*([A-Za-z0-9_]+)', ln)
        if s and pending:
            in_body = True
            for k in pending:
                beds[k].append((s.group(1), s.group(2), s.group(3), s.group(4)))
    return beds

def map_loops(mapname):
    """Ambient loopsounds from maps/<map>.scr, filtered to ambient aliases. Returns (ent, alias)
    for entity-based loops and (None, alias) for LEVELWIDE beds (the map's `$player loopsound`
    replaced by exec replace.scr::loopsound / global/loopsound.scr - played to all players)."""
    p = os.path.join(MOD, "maps", mapname + ".scr")
    if not os.path.exists(p):
        return []
    out = []
    seen = set()
    for ln in open(p, encoding="latin-1", errors="replace"):
        if ln.lstrip().startswith("//"):
            continue
        ent = None; alias = None
        m = re.search(r'\$([A-Za-z0-9_]+)\s+loopsound\s+([A-Za-z0-9_]+)', ln)
        if m:
            ent, alias = m.group(1), m.group(2)
            if ent == "player" or ent.startswith("local"):
                continue
        else:
            lw = re.search(r'(?:replace\.scr::loopsound|global/loopsound\.scr)\s+([A-Za-z0-9_]+)', ln)
            if lw:
                ent, alias = None, lw.group(1)
        if alias is None:
            continue
        if EVENT_BAD.search(alias) or not AMBIENT_OK.search(alias):
            continue
        key = (ent, alias)
        if key in seen:
            continue
        seen.add(key)
        out.append((ent, alias))
    return out

def build():
    beds = ambience_beds()
    per = {}
    for mp in MAPS:
        b = beds.get(mp, [])
        loops = map_loops(mp)
        per[mp] = (b, loops)

    L = []
    L.append("//GENERATED by docs/tools/gen_mp_ambience.py -- DO NOT HAND-EDIT (regenerate instead).")
    L.append("//MP environmental ambience for the BSP-derived Push maps. Harvested from global/ambience.scr")
    L.append("//(coord beds) + each map script's ambient loopsounds. Replayed via mp_ambience.scr::emit /")
    L.append("//::bedWind. Wired from mp_ambience.scr::start as the fallback for maps it does not list.")
    L.append("//coop_mpRun-guarded upstream; a compile canary on every MP boot.")
    L.append("alive:{")
    L.append("\tend 1")
    L.append("}end")
    L.append("")
    L.append("//Start the BSP-derived map's ambience (returns 1 if it handled the map, else 0).")
    L.append("startBsp local.map:{")
    L.append("\tif( level.coop_mpRun != 1 ){ end 0 }")
    L.append("\tswitch( local.map ){")
    for mp in MAPS:
        L.append('\t\tcase "%s":' % mp)
        L.append("\t\t\twaitthread amb_%s" % mp)
        L.append("\t\t\tbreak")
    # [bug-2786] DEFAULT: any map not harvested above (the stock dm/ arenas Freeze Tag / rifles rotate onto,
    # or a new map) still gets the universal levelwide wind bed via bedWind - so no MP map is ever silent.
    L.append("\t\tdefault:")
    L.append("\t\t\twaitthread coop_mod/mp_ambience.scr::bedWind")
    L.append("\t\t\tbreak")
    L.append("\t}")
    L.append("\tend 1")
    L.append("}end 1")
    L.append("")
    summary = []
    for mp in MAPS:
        b, loops = per[mp]
        L.append("amb_%s:" % mp)
        L.append("{")
        n = 0
        for (ent, alias) in loops:
            if ent is None:
                L.append('\twaitthread coop_mod/mp_ambience.scr::emitLevelwide %s' % alias)
            else:
                L.append('\tif( $%s != NULL ){ $%s loopsound %s }' % (ent, ent, alias))
            n += 1
        for (x, y, z, alias) in b:
            L.append("\twaitthread coop_mod/mp_ambience.scr::emit ( %s %s %s ) %s" % (x, y, z, alias))
            n += 1
        if n == 0:
            # nothing harvested -> corridor wind bed so the map is not silent
            L.append("\twaitthread coop_mod/mp_ambience.scr::bedWind")
            src = "windbed"
        else:
            src = "%dloops+%dbeds" % (len(loops), len(b))
        L.append('\tprintln( "^~^~^ MPAMB(bsp) %s (%s)" )' % (mp, src))
        L.append("}end")
        L.append("")
        summary.append("%s:%s" % (mp, src))

    # [bug-2780] TARGET-2 (Breakthrough) alias validity remap. The ambience was harvested from the AA/
    # Spearhead scripts, but the servers + coop run com_target_game 2 whose maintt ubersound.scr is a
    # DIFFERENT, smaller alias set. Harvested aliases that only exist in main/mainta (wind_trees4-7,
    # fire_*, several *_radio*, machine/hum) fail at runtime with "needs an alias in ubersound.scr" and
    # play NOTHING (that is why every ported Push map sounded empty). Remap each to a valid maintt alias.
    text = "\n".join(L)
    for bad, good in MAINTT_ALIAS_REMAP.items():
        text = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(bad) + r"(?![A-Za-z0-9_])", good, text)
    with open(OUT, "w", encoding="latin-1", newline="\n") as f:
        f.write(text)
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    for s in summary:
        print("   " + s)

if __name__ == "__main__":
    build()
