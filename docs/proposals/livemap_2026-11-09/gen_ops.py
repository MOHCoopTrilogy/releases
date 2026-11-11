"""gen_ops.py - LIVE OPERATIONS (PLAN.md): bot-match contracts that pop up on the NEW GAME war map, CRIME.NET style.

ONE source for every generated piece, so the engine, the menus and the MP script cannot disagree:
  * the contract POOL (which map, which mode, how many bots, which side plants) - authored below, from ops_locations.json
    (the location evidence table) and the Phase 0 sweep (tools/ops_sweep.py, H:/hzm_work/liveops-test/sweep.json)
  * the LAYOUT pass over the real wall view (warmap.py allmap_markers.json): every slot's loop, stamp and hover slip clear
    every campaign pin, tag, printed name, the toggle, the legend and each other; slots whose marks overlap become one
    EXCLUSION GROUP (never live together). Any problem fails the build.
  * the ROLL: the shared-world contract generator, seeded from the UTC minute (decision 3a). roll(utc) here is the
    REFERENCE; the engine's cl_hzm_ops.cpp runs the same integer maths on the table this script writes, and
    `hzm_ops dump <utc>` prints its roll so the two can be compared byte for byte (`python gen_ops.py dump <utc>`).

Writes (make_ng3campaigns.py calls build_textures + ng3d + flat; `engine` is run on its own):
  textures/menu/hzm_ops_*.tga + entries in scripts/hzm_ng3campaigns.shader   (loops, timer rings, stamps, slip, card)
  ui/hzm_newgame3d.urc / ui/hzm_ngflat.urc contract widgets                    (through make_ng3campaigns.py)
  coop_mod/mp_ops_table.scr                                                     (MP-owned: per-map sapper side + charges)
  <engine>/code/client/cl_hzm_ops_table.h                                       (python gen_ops.py engine <engine dir>)

    python -P -E gen_ops.py check  [--sheet DIR]      layout verdict for every slot + a 24 h roll census
    python -P -E gen_ops.py dump   <utc>              the reference roll at that UTC second
    python -P -E gen_ops.py engine <engine dir>       write cl_hzm_ops_table.h
    python -P -E gen_ops.py mp     <mod dir>          write coop_mod/mp_ops_table.scr
"""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FD = r"C:\Windows\Fonts"
LOCS = {m["map"]: m for m in json.load(open(os.path.join(HERE, "ops_locations.json"), encoding="utf-8"))["maps"]}
M64 = (1 << 64) - 1

# ------------------------------------------------------------------------------------------------ the pool (authored)
# map -> {mode: (bots min, bots max)}; bots are odd so the human makes the sides even ("You + 5 vs 6"). Sized by map.
# Only maps the Phase 0 sweep passed (bots spawned, navigated and killed each other, 0 Script Errors) may appear here.
# Sweep 2026-11-10 (tools/ops_sweep.py, 10 bots, H:/hzm_work/liveops-test/sweep.json): DROPPED for no fighting at 300 s -
# Malta (2 kills), Berlin TDM (3), Omaha OBJ (2, the beach is too big for 10 bots). Monte Cassino TDM stays (16 kills; its 4
# Script Errors are the stock TOW script's own labels under gt2, not ours).
POOL = {
    "dm/mohdm3": {"TDM": (7, 11)},
    "dm/mohdm6": {"TDM": (7, 11)},
    "dm/mohdm7": {"TDM": (5, 9)},
    "dm/mp_brest_dm": {"TDM": (7, 11)},
    "obj/mp_montecassino_tow": {"TDM": (9, 13)},
    "obj/mp_bologna_obj": {"TDM": (9, 13), "OBJ": (7, 11)},
    # Phase 2 - objective, the player is the sapper (decision 2): his side is the map's planting team
    "obj/obj_team1": {"OBJ": (7, 11)},
    "obj/obj_team2": {"OBJ": (7, 11)},
    "obj/mp_bizertefort_obj": {"OBJ": (7, 11)},
}
# [opsfix2, user rule] every contract is Allied: the Axis-planting OBJ maps (The Bridge obj_team4, Palermo) left the OBJ pool

# [LIBERATION, v1.10.74 - docs/proposals/liberacion_2026-11-10] solo, one life, the co-op kit, Germans that never respawn.
# map -> (Germans min, Germans max, limit min at min Germans, limit min at max Germans). The Germans are placed by mp_ops.scr on
# the map's own spawn points (lib_points.json, from the BSPs), so a map needs only bot navigation, not team spawns: any map
# the Phase 0 / liberacion sweeps saw bots move and fight on. Count by map size (spawn-point spread, lib_points.json) and the
# contract's skill; limits from the bots-only clear test (lib_sweep.py clear), about 2.5x a methodical clear, 6-12 min.
LIB_POOL = {
    "dm/mohdm1": (12, 16, 8, 9),
    "dm/mohdm2": (14, 20, 10, 12),
    "dm/mohdm3": (14, 20, 11, 12),
    "dm/mohdm4": (17, 25, 12, 12),
    "dm/mohdm5": (14, 20, 11, 12),
    "dm/mohdm6": (12, 16, 6, 7),
    "dm/mohdm7": (13, 19, 10, 12),
    "dm/mp_bahnhof_dm": (14, 20, 10, 12),
    "dm/mp_bazaar_dm": (12, 15, 7, 8),
    "dm/mp_brest_dm": (14, 20, 9, 12),
    "dm/mp_gewitter_dm": (17, 25, 12, 12),
    "dm/mp_stadt_dm": (14, 20, 9, 12),
    "dm/mp_unterseite_dm": (12, 16, 7, 8),
    "dm/mp_verschneit_dm": (14, 20, 8, 11),
    "lib/mp_anzio_lib": (14, 20, 10, 12),
    "lib/mp_bizerteharbor_lib": (17, 25, 12, 12),
    "lib/mp_ship_lib": (12, 16, 6, 8),
    "obj/mp_ardennes_tow": (13, 18, 11, 12),
    "obj/mp_berlin_tow": (17, 25, 12, 12),
    "obj/mp_bizertefort_obj": (12, 17, 8, 11),
    "obj/mp_bologna_obj": (17, 25, 12, 12),
    "obj/mp_castello_obj": (14, 20, 10, 12),
    "obj/mp_druckkammern_tow": (17, 25, 12, 12),
    "obj/mp_flughafen_tow": (12, 18, 10, 12),
    "obj/mp_montebattaglia_tow": (14, 20, 8, 11),
    "obj/mp_montecassino_tow": (17, 25, 11, 12),
    "obj/mp_palermo_obj": (14, 20, 8, 11),
    "obj/obj_team1": (12, 18, 9, 11),
    "obj/obj_team2": (14, 20, 9, 12),
    "obj/obj_team3": (17, 25, 11, 12),
    "obj/obj_team4": (12, 18, 7, 9),
}
LIB_SHARE_IN, LIB_SHARE_OUT = 1, 3    # at a place with both kinds, LIB contracts together are picked 1 time in 4 (entry_weights)
LIB_ARRIVE_PCT = 60                   # a place with ONLY LIB contracts opens 60 % of its windows (TDM / OBJ places: 90 %)
LIB_XP_MULT = 2                       # a win pays twice the TDM win XP of that skill; a failure pays nothing
LIB_MIN_D = 1024                      # mp_ops.scr: a German is placed at least this far from the player (relaxed to 0.6x)
# the stock maps' own objective scripts (maintt/pak1 + pak3 maps/obj/*.scr): level.planting_team and the charges' targetnames
# (each runs global/obj_dm.scr::bomb_thinker or its own copy). mp_ops.scr points the bots at these: the defenders hold them,
# the sapper's side escorts toward them.
OBJ_META = {
    "obj/obj_team1": ("allies", ["flak88_weapon1_explosive"], "Destroy the Flak 88"),
    "obj/obj_team2": ("allies", ["v2_explode", "ctrlroom_explode"], "Destroy the V2 and the control room"),
    "obj/obj_team3": ("allies", ["88mm_explosive1", "88mm_explosive2"], "Destroy the two 15cm cannons"),
    "obj/obj_team4": ("axis", ["bridge_bomb", "bridge_bomb2"], "Blow the bridge"),
    "obj/mp_bologna_obj": ("allies", ["bomb1", "bomb2"], "Destroy the underground HQ"),
    "obj/mp_bizertefort_obj": ("allies", ["bomb1"], "Destroy the fort supplies"),
    "obj/mp_palermo_obj": ("axis", ["obj_bomb"], "Blow the documents"),
}
# the slot a map belongs to (maps at one place share one slot: one live contract per place)
SLOT_OF = {"dm/mohdm4": "france", "obj/obj_team4": "france", "obj/mp_bizertefort_obj": "bizerte",
           "lib/mp_bizerteharbor_lib": "bizerte", "lib/mp_ship_lib": "bizerte",
           # [LIBERATION] the censored places share the one censored area they already have on the map: every "Somewhere in
           # Germany" map is the V2 slot's dashed area, every "Somewhere in Normandy" one The Hunt's (one live contract per
           # place, and no new marks crowding the Rhineland / Normandy, where they merged every slot into one group)
           "dm/mohdm5": "v2rocketfacility", "dm/mp_gewitter_dm": "v2rocketfacility", "dm/mp_stadt_dm": "v2rocketfacility",
           "dm/mp_unterseite_dm": "v2rocketfacility", "dm/mp_verschneit_dm": "v2rocketfacility",
           "obj/mp_flughafen_tow": "v2rocketfacility", "obj/mp_druckkammern_tow": "v2rocketfacility",
           "dm/mohdm2": "thehunt", "dm/mp_bahnhof_dm": "thehunt"}
# [LIBERATION] approx pins moved off a campaign tag for a LIB-only place (the evidence table keeps its pin; the reason is here):
# the Bazaar ("Somewhere in North Africa", no city) and the Tunisian desert sat under the bt1 KASSERINE tag
PIN_OVERRIDE = {"dm/mp_bazaar_dm": (36.0, 7.0)}   # nearest clear spot, still the Constantine hinterland the table chose
# NOT in the LIB pool for the same reason, with no clear spot left in their own country: Kasserine (a real place under its
# own bt1 tag), the Tunisian desert (all of the south lies under bt1) and Malta (under bt2). Holland is out because its
# area joined the Remagen and Brest exclusion groups into one (fewer live contracts everywhere in north-west Europe).
# the card's two location lines and the hover slip's place line, per slot. Real places only where the game names one
# (ops_locations.json evidence); a censored place reads "Somewhere in ..." and is never given a town.
PLACE = {
    "remagen": ("REMAGEN, GERMANY", "Remagen, Germany", "Ludendorff Bridge"),
    "stalingrad": ("STALINGRAD, USSR", "Stalingrad, USSR", "now Volgograd"),
    "algiers": ("ALGIERS, ALGERIA", "Algiers, Algeria", "the Casbah"),
    "brest": ("BREST, FRANCE", "Brest, Brittany", "France"),
    "malta": ("VALLETTA, MALTA", "Valletta, Malta", ""),
    "berlin": ("BERLIN, GERMANY", "Berlin, Germany", ""),
    "montecassino": ("MONTE CASSINO, ITALY", "Monte Cassino, Italy", "the abbey"),
    "bologna": ("BOLOGNA, ITALY", "Bologna, Italy", ""),
    "omahabeach": ("OMAHA BEACH, NORMANDY", "Omaha Beach, Normandy", "Colleville sector"),
    "thehunt": ("SOMEWHERE IN NORMANDY", "Somewhere in Normandy", ""),
    "v2rocketfacility": ("SOMEWHERE IN GERMANY", "Somewhere in Germany", ""),
    "france": ("SOMEWHERE IN FRANCE", "Somewhere in France", ""),
    "bizerte": ("BIZERTE, TUNISIA", "Bizerte, Tunisia", "the old fortress"),
    "palermo": ("PALERMO, SICILY", "Palermo, Sicily", ""),
    # [LIBERATION] the places only a Liberation contract opens (ops_locations.json evidence; censored = "Somewhere in ...")
    "southernfrance": ("SOUTHERN FRANCE", "Southern France", "the Provence coast"),
    "destroyedvillage": ("SOMEWHERE IN NORMANDY", "Somewhere in Normandy", "a destroyed village"),
    "snowypark": ("SOMEWHERE IN GERMANY", "Somewhere in Germany", "a park in winter"),
    "bahnhof": ("SOMEWHERE IN NORMANDY", "Somewhere in Normandy", "a railway station"),
    "bazaar": ("SOMEWHERE IN AFRICA", "Somewhere in North Africa", "a bazaar"),
    "gewitter": ("SOMEWHERE IN GERMANY", "Somewhere in Germany", "in a thunderstorm"),
    "holland": ("SOMEWHERE IN HOLLAND", "Somewhere in Holland", ""),
    "stadt": ("SOMEWHERE IN GERMANY", "Somewhere in Germany", "a town"),
    "unterseite": ("SOMEWHERE IN GERMANY", "Somewhere in Germany", ""),
    "verschneit": ("SOMEWHERE IN GERMANY", "Somewhere in Germany", "snowed in"),
    "ardennes": ("THE ARDENNES, BELGIUM", "The Ardennes, Belgium", ""),
    "druckkammern": ("SOMEWHERE IN GERMANY", "Somewhere in Germany", "a U-boat pen"),
    "flughafen": ("SOMEWHERE IN GERMANY", "Somewhere in Germany", "an airfield"),
    "kasserine": ("KASSERINE, TUNISIA", "Kasserine Pass, Tunisia", ""),
    "montebattaglia": ("MONTE BATTAGLIA", "Monte Battaglia, Italy", "the summit"),
    "castello": ("SOMEWHERE IN ITALY", "Somewhere in Italy", "a castle in the snow"),
    "anzio": ("ANZIO, ITALY", "Anzio, Italy", "the beachhead"),
    "tunisia": ("SOMEWHERE IN TUNISIA", "Somewhere in Tunisia", "the desert"),
}
MODE_GT = {"TDM": 2, "OBJ": 4, "LIB": 3}
SKILLS = [("RECRUIT", 25, 100), ("REGULAR", 35, 125), ("VETERAN", 28, 150), ("ELITE", 12, 200)]   # name, weight %, win XP
MODS = [("", 50), ("HARDCORE", 12), ("RIFLES", 12), ("SNIPERS", 8), ("STORM", 18)]                  # name, weight %
MOD_CARD = {"": "NONE", "HARDCORE": "HARDCORE - half health", "RIFLES": "RIFLES ONLY", "SNIPERS": "SNIPERS ONLY",
            "STORM": "STORM - rain, thunder"}
# codenames: two plain words, never a real wartime operation (Anvil, Compass, Torch, Husky, Shingle, Market ... are left out)
ADJ = ["IRON", "COPPER", "SILENT", "GREY", "NORTHERN", "BRASS", "HOLLOW", "WINTER", "STONE", "AMBER", "DISTANT", "BROKEN",
       "SILVER", "QUIET", "FROZEN", "BITTER", "PALE", "EARLY", "SALT", "OAKEN", "WESTERN", "LEADEN", "RUSTY", "SLOW", "COLD",
       "DUSTY", "HIDDEN", "LONELY", "STEEL", "WOODEN", "FADED", "NARROW"]
NOUN = ["KETTLE", "LANTERN", "HARROW", "PLOUGH", "LADDER", "FERRY", "ORCHARD", "MILLSTONE", "SPARROW", "HERON", "BADGER",
        "TOLLGATE", "CHAPEL", "CISTERN", "FURROW", "HAYRICK", "TANKARD", "THIMBLE", "CANDLE", "BARROW", "WHISTLE", "ROOK",
        "OTTER", "HEARTH", "SPINDLE", "CAUSEWAY", "WEATHERVANE", "MILLRACE", "BELLTOWER", "HAYLOFT", "SATCHEL", "WAGON"]
ARRIVE_PCT, LIFE_MIN, LIFE_SPAN, WINDOW, SHOW_MAX = 90, 5, 4, 11, 6   # per group: 90 % of 11-min windows, 5..8 min, cap 6
TIMELIMIT = 10

# ------------------------------------------------------------------------------------------------ data model


def slot_key(mp):
    if mp in SLOT_OF:
        return SLOT_OF[mp]
    return "".join(c for c in LOCS[mp]["name"].lower() if c.isalnum())


def build_pool():
    """slots (sorted, index 1-based in the engine and the menus) and the (map, mode) entries the roll picks from"""
    slots = {}
    pool = {mp: dict(modes) for mp, modes in POOL.items()}
    for mp, (lo, hi, _l0, _l1) in LIB_POOL.items():
        pool.setdefault(mp, {})["LIB"] = (lo, hi)
    for mp, modes in pool.items():
        assert mp in LOCS, mp
        L = LOCS[mp]
        for md in modes:
            # a LIBERATION contract needs bot navigation only (the Germans are placed by script), so any MP map qualifies
            assert md == "TDM" and "TDM" in L["modes"] or md == "OBJ" and "OBJ" in L["modes"] or md == "LIB", (mp, md)
        k = slot_key(mp)
        s = slots.setdefault(k, {"key": k, "pin": tuple(PIN_OVERRIDE.get(mp, L["pin"])), "area": bool(L["area"]), "maps": [],
                                 "campaign": L.get("campaign")})
        assert PLACE.get(k), "no place lines for slot " + k
        s["maps"].append(mp)
    order = sorted(slots)
    entries = []
    for k in order:
        for mp in sorted(slots[k]["maps"]):
            for md in ("TDM", "OBJ", "LIB"):
                if md in pool[mp]:
                    lim = LIB_POOL[mp][2:] if md == "LIB" else (TIMELIMIT, TIMELIMIT)
                    entries.append({"slot": order.index(k), "map": mp, "mode": md, "bots": pool[mp][md],
                                    "name": LOCS[mp]["name"], "side": OBJ_META[mp][0] if md == "OBJ" else ("allies" if md == "LIB" else ""),
                                    "weight": 1, "limit": lim})
    return [slots[k] for k in order], entries


SLOTS, ENTRIES = build_pool()

# ------------------------------------------------------------------------------------------------ the roll (REFERENCE)


def fnv1a64(s):
    h = 0xCBF29CE484222325
    for c in s.encode("ascii"):
        h = ((h ^ c) * 0x100000001B3) & M64
    return h


SALT = fnv1a64("hzm-ops-v1")


def mix(x):
    """splitmix64 finaliser"""
    x = (x + 0x9E3779B97F4A7C15) & M64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & M64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & M64
    return x ^ (x >> 31)


def rnd(t, k):
    return mix(SALT ^ ((t * 0x9E3779B97F4A7C15) & M64) ^ ((k * 0xD1B54A32D192ED03) & M64))


def entry_weights(groups):
    """each entry's pick weight inside its exclusion group: with a LIB entries and b TDM / OBJ ones, a LIB entry weighs
    LIB_SHARE_IN * b and the others LIB_SHARE_OUT * a, so the LIBs together take LIB_SHARE_IN / (IN + OUT) of the picks
    however many maps each kind has there. A group of one kind: all 1. Written into the engine table (hzmOpsEntry_t.weight)."""
    w = []
    for e in ENTRIES:
        g = groups[e["slot"]]
        a = sum(1 for x in ENTRIES if groups[x["slot"]] == g and x["mode"] == "LIB")
        b = sum(1 for x in ENTRIES if groups[x["slot"]] == g and x["mode"] != "LIB")
        if a and b:
            w.append(LIB_SHARE_IN * b if e["mode"] == "LIB" else LIB_SHARE_OUT * a)
        else:
            w.append(1)
    return w


def group_pct(g, groups):
    """a place (exclusion group) with only LIB contracts opens LIB_ARRIVE_PCT of its windows, any other ARRIVE_PCT"""
    ms = [e["mode"] for e in ENTRIES if groups[e["slot"]] == g]
    return LIB_ARRIVE_PCT if ms and all(m == "LIB" for m in ms) else ARRIVE_PCT


def lib_bots(e, skill, key):
    """Germans of a LIB contract: the map's range, placed by skill (RECRUIT low .. ELITE high), +-1 jitter"""
    lo, hi = e["bots"]
    b = lo + (hi - lo) * skill // (len(SKILLS) - 1) + int(rnd(key, 3) % 3) - 1
    return max(lo, min(hi, b))


def lib_limit(e, bots):
    """the contract's time limit (minutes): the map's limits, linear in the German count"""
    lo, hi = e["bots"]
    l0, l1 = e["limit"]
    return l0 if hi == lo else l0 + ((l1 - l0) * (bots - lo) + (hi - lo) // 2) // (hi - lo)


def contract(g, k, groups):
    """the contract of exclusion group g in its window k, or None. A group's time is cut into WINDOW-minute windows (phase
    shifted per group); each window holds at most one contract, so two contracts of one group can never overlap, and the
    whole schedule is a pure function of the clock - no state, nothing to drift between players."""
    key = k * 64 + g
    if rnd(key, 0) % 100 >= group_pct(g, groups):
        return None
    mine = [i for i, e in enumerate(ENTRIES) if groups[e["slot"]] == g]
    W = entry_weights(groups)
    r = rnd(key, 1) % sum(W[i] for i in mine)
    for i in mine:
        if r < W[i]:
            e = ENTRIES[i]
            break
        r -= W[i]
    life = LIFE_MIN + rnd(key, 2) % LIFE_SPAN
    born = phase(g) + k * WINDOW + rnd(key, 9) % (WINDOW - life + 1)
    lo, hi = e["bots"]
    bots = lo + 2 * (rnd(key, 3) % ((hi - lo) // 2 + 1))
    r = rnd(key, 4) % 100
    acc, skill = 0, 0
    for i, (_n, w, _x) in enumerate(SKILLS):
        acc += w
        if r < acc:
            skill = i
            break
    r = rnd(key, 5) % 100
    acc, mod = 0, 0
    for i, (_n, w) in enumerate(MODS):
        acc += w
        if r < acc:
            mod = i
            break
    if SKILLS[skill][0] == "ELITE" and MODS[mod][0] == "HARDCORE":
        mod = 0
    if e["mode"] == "LIB":
        bots = lib_bots(e, skill, key)
    side = "allies"     # [opsfix2, user 2026-11-10] the humans are always Allied (cl_hzm_ops.cpp does the same)
    return {"t": born, "entry": ENTRIES.index(e), "slot": e["slot"], "group": g, "life": life, "bots": bots, "skill": skill,
            "mod": mod, "side": side, "name": ADJ[rnd(key, 7) % len(ADJ)] + " " + NOUN[rnd(key, 8) % len(NOUN)],
            "serial": 100 + key % 9900}


def phase(g):
    return rnd(g, 10) % WINDOW


def roll(utc, groups):
    """the contracts live at UTC second `utc`, oldest first (at most SHOW_MAX)"""
    now = utc // 60
    live = []
    for g in range(max(groups) + 1):
        k = (now - phase(g)) // WINDOW
        for kk in (k - 1, k):
            c = contract(g, kk, groups)
            if c and c["t"] * 60 <= utc < (c["t"] + c["life"]) * 60:
                c["left"] = (c["t"] + c["life"]) * 60 - utc
                live.append(c)
    live.sort(key=lambda c: (c["t"], c["group"]))
    return live[:SHOW_MAX]


# ------------------------------------------------------------------------------------------------ layout on the wall view
WALL_W, WALL_H = 4096.0, 3072.0          # the markers json is in uv; this pass works in 4096 x 3072 wall pixels
R_LOOP, AREA_K = 84.0, 1.4               # a point loop's radius; a censored area's dashed loop is AREA_K x wider
# [QA 2026-11-10] "Somewhere in France" sits in the narrow band between the BASTOGNE tag and the printed FRANCE: a
# smaller area there keeps its ring and tack off the lettering
R_OVERRIDE = {"france": 72.0}
STAMP = (210.0, 86.0)                    # the TDM / OBJ stamp
SLIP = (860.0, 340.0)                    # the hover slip (four typed lines)


def load_sheet(sheet):
    return json.load(open(os.path.join(sheet, "allmap_markers.json")))


def lonlat_px(js, lat, lon):
    (lo0, lo1), (la0, la1) = js["lon"], js["lat"]
    return ((lon - lo0) / (lo1 - lo0) * WALL_W, (la1 - lat) / (la1 - la0) * WALL_H)


def uv_px(u, v):
    return (u * WALL_W, (1 - v) * WALL_H)


def hit(a, b, m=0.0):
    return a[0] - m < b[2] and a[2] + m > b[0] and a[1] - m < b[3] and a[3] + m > b[1]


def circ_hits_rect(cx, cy, r, b):
    qx, qy = min(max(cx, b[0]), b[2]), min(max(cy, b[1]), b[3])
    return (qx - cx) ** 2 + (qy - cy) ** 2 < r * r


def blockers(js):
    tw, th = js["tag_m"][0] / js["wall_m"][0] * WALL_W, js["tag_m"][1] / js["wall_m"][1] * WALL_H
    out = []
    for m in js["missions"]:
        x, y = uv_px(*m["tag_uv"])
        out.append(("tag " + m["key"], (x - tw / 2, y - th / 2, x + tw / 2, y + th / 2)))
        x, y = uv_px(*m["pin_uv"])
        out.append(("pin " + m["key"], (x - 22, y - 22, x + 22, y + 22)))
    for n, (u0, v0, u1, v1) in js["labels"].items():
        out.append(("name " + n, (u0 * WALL_W, (1 - v1) * WALL_H, u1 * WALL_W, (1 - v0) * WALL_H)))
    x, y = uv_px(*js["toggle"]["uv"])
    hw, hh = js["toggle"]["w"] / js["wall_m"][0] * WALL_W / 2, js["toggle"]["h"] * 1.6 / js["wall_m"][1] * WALL_H / 2
    out.append(("toggle", (x - hw, y - hh, x + hw, y + hh)))
    s = 1.0
    out.append(("legend", (WALL_W - 980 * s, WALL_H - 400 * s, WALL_W - 120 * s, WALL_H - 130 * s)))
    return out


def layout(js):
    """per slot: centre, loop radius, stamp box, slip box (wall px); exclusion groups; problems (any = build failure)"""
    B = blockers(js)
    tags = [(n, r) for n, r in B if n.startswith("tag ")]
    sheet = (70.0, 70.0, WALL_W - 70.0, WALL_H - 70.0)
    dirs = [(1, -1), (1, 1), (-1, -1), (-1, 1), (1, 0), (-1, 0), (0, -1), (0, 1)]
    placed, problems = [], []
    for i, s in enumerate(SLOTS):
        x, y = lonlat_px(js, *s["pin"])
        r = R_OVERRIDE.get(s["key"], R_LOOP * (AREA_K if s["area"] else 1.0))
        if not (r < x < WALL_W - r and r < y < WALL_H - r):
            problems.append((s["key"], "off the sheet"))
        under = [n for n, b in tags if circ_hits_rect(x, y, r, b)]
        if under:
            problems.append((s["key"], "loop under " + ",".join(under)))
        own = [(n, b) for n, b in B if not (n.startswith("pin ") and circ_hits_rect(x, y, r, b))]   # a wrapped campaign pin is fine
        sw, sh = STAMP
        st = None
        # the stamp sits ON the loop's rim (it is stamped beside the circled place, not floating away from it); it may
        # cover the grease line but never the middle, where the ring and the place are
        for k_, (dx, dy) in [(k_, d) for k_ in (1.0, 1.3, 1.7) for d in dirs]:
            cx = x + dx * k_ * (r * 0.62 + sw / 2) if dx else x
            cy = y + dy * k_ * (r * 0.62 + sh / 2) if dy else y
            box = (cx - sw / 2, cy - sh / 2, cx + sw / 2, cy + sh / 2)
            if not (sheet[0] < box[0] and box[2] < sheet[2] and sheet[1] < box[1] and box[3] < sheet[3]):
                continue
            if any(hit(box, b, 6) for _n, b in own) or circ_hits_rect(x, y, r * 0.62, box):
                continue
            st = box
            break
        if not st:
            problems.append((s["key"], "no clear stamp spot"))
            st = (x, y, x + sw, y + sh)
        # the hover slip: beside the stamp, away from the loop, on the sheet (it pops over tags - it is a hover note)
        slw, slh = SLIP
        sx = st[2] + 10 if (st[0] + st[2]) / 2 >= x else st[0] - 10 - slw
        sy = (st[1] + st[3]) / 2 - slh / 2
        if sx < sheet[0]:
            sx = st[2] + 10
        if sx + slw > sheet[2]:
            sx = st[0] - 10 - slw
        sy = min(max(sy, sheet[1]), sheet[3] - slh)
        placed.append({"c": (x, y), "r": r, "stamp": st, "slip": (sx, sy, sx + slw, sy + slh)})
    # exclusion groups: two slots whose marks (loop box + stamp) overlap can never be live together
    def marks(p):
        x, y = p["c"]
        return [(x - p["r"], y - p["r"], x + p["r"], y + p["r"]), p["stamp"]]
    grp = list(range(len(SLOTS)))

    def find(a):
        while grp[a] != a:
            a = grp[a]
        return a
    for a in range(len(SLOTS)):
        for b in range(a + 1, len(SLOTS)):
            if any(hit(m1, m2, 10) for m1 in marks(placed[a]) for m2 in marks(placed[b])):
                grp[find(b)] = find(a)
    roots = sorted({find(a) for a in range(len(SLOTS))})
    groups = [roots.index(find(a)) for a in range(len(SLOTS))]
    return placed, groups, problems


# ------------------------------------------------------------------------------------------------ textures
GREASE = (168, 24, 20)
CARBON = (40, 30, 24)


def F(name, px):
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(FD, name), max(8, int(px)))


def _grease_loop(size, seed):
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = size / 2
    r = size * 0.40
    w = max(3, int(size * 0.05))
    for p in range(2):
        a0 = rng.uniform(0, 2 * math.pi)
        ex, ey = rng.uniform(0.94, 1.06), rng.uniform(0.9, 1.0)
        tilt = rng.uniform(-0.4, 0.4)
        ph = [rng.uniform(0, 6.28) for _ in range(3)]
        pts = []
        for i in range(121):
            t = a0 + 1.12 * 2 * math.pi * i / 120
            rr = r * (1 + 0.03 * math.sin(3 * t + ph[0]) + 0.018 * math.sin(5 * t + ph[1]) + 0.025 * (i / 120) + p * 0.035)
            x, y = rr * ex * math.cos(t), rr * ey * math.sin(t)
            x, y = x * math.cos(tilt) - y * math.sin(tilt), x * math.sin(tilt) + y * math.cos(tilt)
            pts.append((cx + x, cy + y))
        d.line(pts, fill=GREASE + ((235 if p == 0 else 150),), width=w if p == 0 else max(1, int(w * 0.6)), joint="curve")
    return im


def _dashed(size):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = size * 0.42
    c = size / 2
    w = max(3, int(size * 0.026))
    for a in range(0, 360, 15):
        d.arc((c - r, c - r, c + r, c + r), a, a + 8, fill=GREASE + (225,), width=w)
    return im


def _ring(size, k):
    """time left: k eighths, inked clockwise from twelve o'clock over a faint pencil track; red in the last quarter"""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = size * 0.12
    box = (pad, pad, size - pad, size - pad)
    w = max(3, int(size * 0.11))
    d.arc(box, 0, 360, fill=(90, 70, 50, 90), width=max(1, w // 3))
    if k > 0:
        d.arc(box, -90, -90 + 45 * k, fill=(150, 18, 14, 245) if k <= 2 else (30, 22, 16, 245), width=w)
    return im


def _stamp(text, w, h, col=(150, 20, 18), seed=7, rot=0.0, font="courbd.ttf"):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = max(3, int(h * 0.07))
    # inset so the tilted stamp keeps its corners inside the texture: the rotation lifts a corner by about w/2*sin(rot)
    iy = lw * 2 + int(w / 2 * math.sin(math.radians(abs(rot)))) + 2
    ix = lw * 2 + int(h / 2 * math.sin(math.radians(abs(rot)))) + 2
    d.rounded_rectangle((ix, iy, w - ix, h - iy), radius=int(h * 0.1), outline=col + (235,), width=lw)
    px = int((h - 2 * iy) * 0.68)
    f = F(font, px)
    while d.textlength(text, font=f) > w - 2 * ix - 6 * lw and px > 10:
        px -= 2
        f = F(font, px)
    tw = d.textlength(text, font=f)
    bb = d.textbbox((0, 0), text, font=f)
    d.text(((w - tw) / 2, (h - (bb[3] - bb[1])) / 2 - bb[1]), text, font=f, fill=col + (235,))
    rng = random.Random(seed)                # worn rubber: knock specks out of the ink
    a = im.getchannel("A").load()
    for _ in range(int(w * h * 0.05)):
        x, y = rng.randrange(w), rng.randrange(h)
        a[x, y] = int(a[x, y] * 0.3)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC)
    return im


def _paper(w, h, seed, ruled=False, header=None):
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), fill=(240, 232, 212, 252), outline=(150, 128, 100, 255), width=max(2, w // 300))
    px = im.load()
    for _ in range(w * h // 6):                       # paper tooth: faint, irregular, never a uniform noise field
        x, y = rng.randrange(1, w - 1), rng.randrange(1, h - 1)
        r, g, b, a = px[x, y]
        k = rng.randint(-7, 4)
        px[x, y] = (max(0, min(255, r + k)), max(0, min(255, g + k)), max(0, min(255, b + k)), a)
    return im, d


def card_texture(W=512, H=640):
    """the dispatch card: the printed form only (header, rule, the row captions); the typed values are linkcvar labels.
    Row geometry (fractions of the card) is CARD_ROWS, shared with the widgets so the type sits on its ruled lines."""
    from PIL import ImageDraw
    im, d = _paper(W, H, 5)
    d = ImageDraw.Draw(im)
    fh, fs = F("courbd.ttf", W * 0.046), F("PrestigeEliteStd-Bd.otf", W * 0.03)
    d.text((W * 0.04, H * 0.025), "FIELD OPERATIONS  -  DISPATCH", font=fh, fill=CARBON + (255,))
    d.text((W * 0.42, H * 0.075), "PRIORITY: ROUTINE", font=fs, fill=CARBON + (225,))
    y_rule = CARD_HEAD[1] * H
    d.line((W * 0.03, y_rule, W * 0.97, y_rule), fill=(190, 70, 70, 190), width=max(2, W // 250))
    for cap, y0, _h in CARD_ROWS:
        yb = (y0 + _h) * H
        d.line((W * 0.03, yb, W * 0.97, yb), fill=(150, 170, 196, 120), width=1)
        if cap:
            d.text((W * 0.045, y0 * H + _h * H * 0.22), cap + ":", font=fs, fill=(90, 70, 54, 255))
    # the paper clip (top right): two nested rounded loops in steel
    d.rounded_rectangle((W * 0.86, -H * 0.02, W * 0.91, H * 0.085), radius=int(W * 0.022), outline=(120, 124, 130, 255), width=max(2, W // 170))
    d.rounded_rectangle((W * 0.872, -H * 0.01, W * 0.898, H * 0.06), radius=int(W * 0.012), outline=(150, 154, 160, 255), width=max(1, W // 260))
    return im


# card geometry, fractions of the card (x0, y0 of the value column, row height); captions are printed, values typed
CARD_HEAD = (0.075, 0.205)          # serial line y, the red rule under the codename
CARD_ROWS = [("LOCATION", 0.215, 0.052), ("", 0.267, 0.052), ("MAP", 0.319, 0.052), ("MODE", 0.371, 0.052),
             ("FORCES", 0.423, 0.052), ("", 0.475, 0.052), ("BOTS", 0.527, 0.052), ("MODIFIER", 0.579, 0.052),
             ("LIMIT", 0.631, 0.052), ("REWARD", 0.683, 0.052), ("EXPIRES", 0.735, 0.052)]
CARD_VALUES = ["CLoc1", "CLoc2", "CMap", "CMode", "CF1", "CF2", "CSkill", "CMod", "CLimit", "CReward", "CExp"]
CARD_VAL_X = 0.28
CARD_STAMPS = {"deploy": (0.07, 0.83, 0.42, 0.95), "file": (0.60, 0.845, 0.93, 0.935), "res": (0.03, 0.845, 0.59, 0.945)}     # the result is stamped where DEPLOY was (DEPLOY is gone after the operation)


def build_textures(texdir, add_shader):
    """every hzm_ops_* texture (power-of-two sides) and its shader entry, through make_ng3campaigns' add_shader"""
    from PIL import Image
    os.makedirs(texdir, exist_ok=True)
    for fn in os.listdir(texdir):
        if fn.startswith("hzm_ops_"):
            os.remove(os.path.join(texdir, fn))
    out = {}
    for i in range(3):
        out["hzm_ops_loop%d" % i] = _grease_loop(256, 11 + i * 7)
    out["hzm_ops_area"] = _dashed(256)
    for k in range(0, 9):
        out["hzm_ops_ring%d" % k] = _ring(128, k)
    for md, rot in (("TDM", -4), ("OBJ", 3)):
        out["hzm_ops_stamp_" + md.lower()] = _stamp(md, 256, 128, seed=sum(map(ord, md)), rot=rot)
    # [LIBERATION] the solo hunt's stamp: the French word, accent and all (Courier New Bold has the E-acute), in the field
    # green of the result stamp so it reads apart from the red TDM / OBJ ones at a glance
    # drawn at the stamp box's own 2.44:1 (STAMP) so the word is not squeezed when the label stretches it back
    out["hzm_ops_stamp_lib"] = _stamp("LIB\u00c9RATION", 512, 210, col=(40, 84, 44), seed=31, rot=-3)
    tk = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    from PIL import ImageDraw
    ImageDraw.Draw(tk).ellipse((14, 14, 50, 50), fill=(28, 24, 22, 255), outline=(70, 62, 52, 255), width=3)
    out["hzm_ops_tack"] = tk
    sl, _d = _paper(512, 256, 9)
    out["hzm_ops_slip"] = sl
    out["hzm_ops_card"] = card_texture(512, 640).resize((512, 1024), Image.LANCZOS)    # drawn at the card's 4:5, stored POT
    out["hzm_ops_deploy"] = _stamp("DEPLOY", 512, 160, seed=3, rot=2.5)
    out["hzm_ops_deploy_h"] = _stamp("DEPLOY", 512, 160, col=(196, 30, 24), seed=3, rot=2.5)
    out["hzm_ops_file"] = _stamp("FILE AWAY", 512, 128, col=(60, 60, 70), seed=4, rot=-2)
    out["hzm_ops_file_h"] = _stamp("FILE AWAY", 512, 128, col=(30, 30, 40), seed=4, rot=-2)
    out["hzm_ops_won"] = _stamp("MISSION ACCOMPLISHED", 1024, 200, col=(30, 90, 40), seed=5, rot=-1.5)
    out["hzm_ops_failed"] = _stamp("OPERATION FAILED", 1024, 200, seed=6, rot=-1.5)
    for nm, im in out.items():
        w, h = im.size
        pw, ph = 1 << (w - 1).bit_length(), 1 << (h - 1).bit_length()
        if (pw, ph) != (w, h):              # power-of-two sides (the label stretches it back onto its rect)
            im = im.resize((pw, ph), Image.LANCZOS)
        im.save(os.path.join(texdir, nm + ".tga"))
        add_shader(nm, True, "tga", pulse=nm.startswith(("hzm_ops_loop", "hzm_ops_area")))
    return sorted(out)


# ------------------------------------------------------------------------------------------------ menu widgets


def ng3d(api, js):
    """the NEW GAME 3D wall: contract widgets. api = make_ng3campaigns' helpers (conv, map_bu, SCALE, WM, label, hot, DIST,
    FPX). Returns (scene lines, under-the-tags widgets, over-the-tags widgets, card widgets); hot() is called here so the
    contract hotspots are appended AFTER every campaign one (ui_scene_hot is the list position)."""
    placed, groups, problems = layout(js)
    assert not problems, problems
    conv, map_bu, SC, (WLO, WHI) = api["conv"], api["map_bu"], api["SCALE"], api["WM"]
    WX, WZ = WHI[0] - WLO[0], WHI[2] - WLO[2]
    scn, under, over, card = [], [], [], []
    slips = []                              # drawn after EVERY stamp: no stamp of another contract may print over a slip

    def box3(nm, b, dy):
        """a scene label framed to wall-pixel box b"""
        u0, u1 = b[0] / WALL_W, b[2] / WALL_W
        v0, v1 = 1 - b[3] / WALL_H, 1 - b[1] / WALL_H
        c = conv(map_bu(((u0 + u1) / 2, (v0 + v1) / 2), dy=dy))
        scn.append('scenelabel "%s" %.1f %.1f %.1f %.2f %.2f' % (nm, c[0], c[1], c[2], (u1 - u0) * WX / 2 * SC, (v1 - v0) * WZ / 2 * SC))

    def lab(nm, gate, shader=None, link=None, title=None, font=None, fg="1 1 1 1", align=None, shlink=None):
        w = ["resource", "Label", "{", 'name "%s"' % nm, "rect 0 0 8 8", "fgcolor " + fg, "bgcolor 0 0 0 0", 'borderstyle "NONE"']
        if shader:
            w.append('shader "textures/menu/%s"' % shader)
        if shlink:
            w += ['linkcvar "%s"' % shlink, "linkcvartoshader"]
        if link:
            w.append('linkcvar "%s"' % link)
        if title:
            w.append('title "%s"' % title)
        if font:
            w.append('font "%s"' % font)
        if align:
            w.append("textalign " + align)
        if gate:
            w.append('enabledcvar "%s"' % gate)
        return w + ["}"]

    for i, (s, p) in enumerate(zip(SLOTS, placed)):
        n = i + 1
        live = "ui_opsL%d==1" % n
        x, y = p["c"]
        r = p["r"]
        lb = (x - r * 1.25, y - r * 1.25, x + r * 1.25, y + r * 1.25)
        box3("ops_lp%d" % n, lb, 0.0050)
        under += lab("ops_lp%d" % n, live, shader="hzm_ops_area" if s["area"] else "hzm_ops_loop%d" % (i % 3))
        rr = r * (0.62 if not s["area"] else 0.45)
        box3("ops_rg%d" % n, (x - rr, y - rr, x + rr, y + rr), 0.0049)
        under += lab("ops_rg%d" % n, live, shlink="ui_opsR%d" % n)
        if s["area"]:                       # a censored area has no campaign pin under it: its own small tack
            box3("ops_tk%d" % n, (x - 20, y - 20, x + 20, y + 20), 0.0048)
            under += lab("ops_tk%d" % n, live, shader="hzm_ops_tack")
        box3("ops_st%d" % n, p["stamp"], 0.0040)
        over += lab("ops_st%d" % n, live, shlink="ui_opsS%d" % n)
        # the stamp is the click target: hover = the slip, click = the dispatch card
        sb = p["stamp"]
        cu, cv = ((sb[0] + sb[2]) / 2) / WALL_W, 1 - ((sb[1] + sb[3]) / 2) / WALL_H
        ce = conv(map_bu((cu, cv), dy=0.0040))
        hw = (sb[2] - sb[0]) / WALL_W * WX / 2 / api["DIST"] * api["FPX"]
        hh = (sb[3] - sb[1]) / WALL_H * WZ / 2 / api["DIST"] * api["FPX"]
        hi = api["hot"]("ops%d" % n, ce, (sb[2] - sb[0]) / WALL_W * WX / 2 * SC, hw * 1.08, hh * 1.25,
                        "set ui_scene_hot 0; hzm_ops card %d" % n, "", live)
        sl = p["slip"]
        hov = "ui_scene_hot==%d %s" % (hi, live)
        box3("ops_sp%d" % n, sl, 0.0030)
        slips += lab("ops_sp%d" % n, hov, shader="hzm_ops_slip")
        lh = (sl[3] - sl[1] - 30) / 4.0
        for j, (cv_, col) in enumerate((("A", "0.16 0.12 0.09 1"), ("B", "0.16 0.12 0.09 1"), ("M", "0.16 0.12 0.09 1"),
                                        ("E", "0.55 0.07 0.05 1"))):
            tb = (sl[0] + 30, sl[1] + 15 + j * lh, sl[2] - 20, sl[1] + 15 + (j + 1) * lh)
            box3("ops_s%s%d" % (cv_, n), tb, 0.0028)
            slips += lab("ops_s%s%d" % (cv_, n), hov, link="ui_ops%s%d" % (cv_, n), title="M" * 21, font="courier-16", fg=col, align="left")
    # the dispatch card, pinned on the wall away from its contract: right over Russia for a western one, left over the
    # Atlantic for an eastern one (the engine sets ui_opsCSide)
    for side, (cu0, cv1) in (("1", (0.515, 0.95)), ("2", (0.025, 0.95))):     # 1 right, 2 left (enabledcvar compares numbers)
        cw = 0.46                                             # of the wall width: 1.45 x 1.81 m, the open card is the focus
        ox, oy = cu0 * WALL_W, (1 - cv1) * WALL_H
        W_ = cw * WALL_W
        H_ = W_ * (3.149 / WALL_W) * 1.25 / (2.705 / WALL_H)                    # a 4:5 card on the wall (metres)
        gate = "ui_opsCard==1 ui_opsCSide==%s" % side

        def cb(fx0, fy0, fx1, fy1):
            return (ox + fx0 * W_, oy + fy0 * H_, ox + fx1 * W_, oy + fy1 * H_)
        box3("ops_cd%s" % side, cb(0, 0, 1, 1), 0.0020)
        card += lab("ops_cd%s" % side, gate, shader="hzm_ops_card")
        box3("ops_cn%s" % side, cb(0.045, 0.072, 0.40, 0.112), 0.0018)
        card += lab("ops_cn%s" % side, gate, link="ui_opsCNo", title="M" * 9, font="courier-16", fg="0.16 0.12 0.09 1", align="left")
        box3("ops_co%s" % side, cb(0.04, 0.125, 0.96, 0.195), 0.0018)
        card += lab("ops_co%s" % side, gate, link="ui_opsCName", title="M" * 28, font="courier-16", fg="0.13 0.10 0.08 1", align="left")
        for (cap, y0, h), cv_ in zip(CARD_ROWS, CARD_VALUES):
            box3("ops_%s%s" % (cv_, side), cb(CARD_VAL_X, y0 + h * 0.12, 0.97, y0 + h * 0.95), 0.0018)
            col = "0.55 0.07 0.05 1" if cv_ == "CExp" else "0.16 0.12 0.09 1"
            card += lab("ops_%s%s" % (cv_, side), gate, link="ui_ops" + cv_, title="M" * 22, font="courier-16", fg=col, align="left")
        for nm, key, g2, cmd, back in (("dp", "deploy", " ui_opsCRes==0", "set ui_scene_hot 0; hzm_ops deploy", False),
                                       ("fa", "file", "", "set ui_scene_hot 0; hzm_ops close", True)):
            b = cb(*CARD_STAMPS[key])
            box3("ops_%s%s" % (nm, side), b, 0.0016)
            card += lab("ops_%s%s" % (nm, side), gate + g2, shader="hzm_ops_" + key)
            cu, cv = ((b[0] + b[2]) / 2) / WALL_W, 1 - ((b[1] + b[3]) / 2) / WALL_H
            ce = conv(map_bu((cu, cv), dy=0.0016))
            hw = (b[2] - b[0]) / WALL_W * WX / 2 / api["DIST"] * api["FPX"]
            hh = (b[3] - b[1]) / WALL_H * WZ / 2 / api["DIST"] * api["FPX"]
            # [opsfix, v1.10.72 bug] the card's proxy buttons must be emitted AFTER the card's labels: the UI hit-test
            # (UIWidget::FindResponder) takes the LAST widget under the cursor, Labels included, so a card label drawn
            # after the button swallowed every real click on DEPLOY / FILE AWAY. hot_top = emitted after the card.
            hi = api.get("hot_top", api["hot"])("ops%s%s" % (nm, side), ce, (b[2] - b[0]) / WALL_W * WX / 2 * SC, hw, hh, cmd, "", gate + g2, back)
            box3("ops_%sh%s" % (nm, side), b, 0.0015)          # the stamp inks darker under the cursor
            card += lab("ops_%sh%s" % (nm, side), "%s%s ui_scene_hot==%d" % (gate, g2, hi), shader="hzm_ops_%s_h" % key)
        for rv, tex in ((1, "won"), (2, "failed")):
            box3("ops_r%d%s" % (rv, side), cb(*CARD_STAMPS["res"]), 0.0014)
            card += lab("ops_r%d%s" % (rv, side), "%s ui_opsCRes==%d" % (gate, rv), shader="hzm_ops_" + tex)
    return scn, under, over + slips, card


def flat(F_):
    """the flat chooser (ui_atticMain 0): a LIVE OPERATIONS strip of up to six contracts (display rows 1-6, filled by the
    engine) and the same card as plain 2D widgets. Returns urc lines."""
    out = []
    y0 = 418                                   # under the own-disc strip (rect y 378, 24 high) and above BACK (y 448)
    out += ["resource", "Label", "{", 'name "ngf_ops_head"', "rect 44 %d 552 12" % (y0 - 13), 'title "LIVE OPERATIONS - BOT MATCHES, OPEN TO ALL"',
            "fgcolor 0.86 0.30 0.22 1.00", "bgcolor 0 0 0 0", 'font "verdana-12"', "textalign left", 'enabledcvar "ui_opsN!=0"', "}"]
    for k in range(1, SHOW_MAX + 1):
        x, y0 = 44 + ((k - 1) % 3) * 184, 418 + ((k - 1) // 3) * 15     # two rows of three
        g = "ui_opsN>=%d" % k
        gate = 'enabledcvar "ui_opsD%dOn==1"' % k
        out += ["resource", "Label", "{", 'name "ngf_ops%d"' % k, "rect %d %d 182 14" % (x, y0), 'linkcvar "ui_opsD%d"' % k,
                "fgcolor 0.95 0.86 0.70 1.00", "bgcolor 0.30 0.08 0.05 0.90", 'borderstyle "3D_BORDER"', 'font "verdana-12"',
                "textalign center", gate, "}"]
        out += ["resource", "Button", "{", 'name "ngf_opsb%d"' % k, "rect %d %d 182 14" % (x, y0), "fgcolor 0 0 0 0", "bgcolor 0 0 0 0",
                'borderstyle "NONE"', 'clicksound "sound/menu/apply.wav"', 'stuffcommand "hzm_ops cardd %d"' % k, gate, "}"]
        del g
    # the card, flat: same cvars as the wall card
    cx, cy, cw, ch = 352, 44, 240, 300
    gate = 'enabledcvar "ui_opsCard==1"'
    out += ["resource", "Label", "{", 'name "ngf_card"', "rect %d %d %d %d" % (cx, cy, cw, ch), "fgcolor 1 1 1 1", "bgcolor 0 0 0 0",
            'borderstyle "NONE"', 'shader "textures/menu/hzm_ops_card"', gate, "}"]
    for nm, cv_, fy, fh in (("cn", "CNo", 0.072, 0.04), ("co", "CName", 0.125, 0.07)):
        out += ["resource", "Label", "{", 'name "ngf_%s"' % nm, "rect %d %d %d %d" % (cx + 10, cy + int(fy * ch), cw - 20, int(fh * ch)),
                'linkcvar "ui_ops%s"' % cv_, "fgcolor 0.16 0.12 0.09 1", "bgcolor 0 0 0 0", 'font "courier-16"', "textalign left", gate, "}"]
    for (cap, y0_, h), cv_ in zip(CARD_ROWS, CARD_VALUES):
        out += ["resource", "Label", "{", 'name "ngf_%s"' % cv_, "rect %d %d %d %d" % (cx + int(CARD_VAL_X * cw), cy + int(y0_ * ch), int((0.97 - CARD_VAL_X) * cw), int(h * ch)),
                'linkcvar "ui_ops%s"' % cv_, "fgcolor %s" % ("0.55 0.07 0.05 1" if cv_ == "CExp" else "0.16 0.12 0.09 1"), "bgcolor 0 0 0 0",
                'font "courier-16"', "textalign left", gate, "}"]
    for nm, key, extra, cmd in (("dp", "deploy", " ui_opsCRes==0", "hzm_ops deploy"), ("fa", "file", "", "hzm_ops close")):
        b = CARD_STAMPS[key]
        rect = "rect %d %d %d %d" % (cx + int(b[0] * cw), cy + int(b[1] * ch), int((b[2] - b[0]) * cw), int((b[3] - b[1]) * ch))
        out += ["resource", "Button", "{", 'name "ngf_%s"' % nm, rect, "fgcolor 1 1 1 1", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
                'shader "textures/menu/hzm_ops_%s"' % key, 'hovershader "textures/menu/hzm_ops_%s_h"' % key,
                'clicksound "sound/menu/%s.wav"' % ("apply" if key == "deploy" else "back"), 'stuffcommand "%s"' % cmd,
                'enabledcvar "ui_opsCard==1%s"' % extra, "}"]
    for rv, tex in ((1, "won"), (2, "failed")):
        b = CARD_STAMPS["res"]
        out += ["resource", "Label", "{", 'name "ngf_r%d"' % rv, "rect %d %d %d %d" % (cx + int(b[0] * cw), cy + int(b[1] * ch), int((b[2] - b[0]) * cw), int((b[3] - b[1]) * ch)),
                "fgcolor 1 1 1 1", "bgcolor 0 0 0 0", 'borderstyle "NONE"', 'shader "textures/menu/hzm_ops_%s"' % tex,
                'enabledcvar "ui_opsCard==1 ui_opsCRes==%d"' % rv, "}"]
    return out


# ------------------------------------------------------------------------------------------------ engine table + MP table


def c_str(s):
    assert '"' not in s and "\\" not in s
    return '"%s"' % s


def engine_header(path, js):
    placed, groups, problems = layout(js)
    assert not problems, problems
    L = ["// GENERATED by docs/proposals/livemap_2026-11-09/gen_ops.py - do not hand-edit. Live Operations contract table.",
         "// The roll in cl_hzm_ops.cpp must stay the same integer maths as gen_ops.py::roll (compare: hzm_ops dump <utc>).",
         "#pragma once", "",
         "#define HZM_OPS_SALT 0x%016XULL" % SALT,
         "#define HZM_OPS_ARRIVE_PCT %d" % ARRIVE_PCT, "#define HZM_OPS_LIFE_MIN %d" % LIFE_MIN, "#define HZM_OPS_LIFE_SPAN %d" % LIFE_SPAN,
         "#define HZM_OPS_WINDOW %d" % WINDOW, "#define HZM_OPS_SHOW_MAX %d" % SHOW_MAX, "#define HZM_OPS_TIMELIMIT %d" % TIMELIMIT,
         "#define HZM_OPS_NSLOTS %d" % len(SLOTS), "#define HZM_OPS_NENTRIES %d" % len(ENTRIES),
         "#define HZM_OPS_NGROUPS %d" % (max(groups) + 1), "#define HZM_OPS_LIB_XP_MULT %d" % LIB_XP_MULT,
         "#define HZM_OPS_GT_LIB %d" % MODE_GT["LIB"], "",
         "typedef struct { const char *key, *slip, *loc1, *loc2; int group; float lon; } hzmOpsSlot_t;",
         "// gt 3 = LIBERATION (solo hunt): botsMin/botsMax are the Germans, limLo/limHi the time limit (min) at those counts",
         "typedef struct { int slot; const char *bsp, *name; int gt, botsMin, botsMax; const char *side; int weight, limLo, limHi; } hzmOpsEntry_t;",
         "typedef struct { const char *name; int weight, xp; } hzmOpsSkill_t;",
         "typedef struct { const char *name, *card; int weight; } hzmOpsMod_t;", "",
         "static const hzmOpsSlot_t hzmOpsSlots[HZM_OPS_NSLOTS] = {"]
    for s, g in zip(SLOTS, groups):
        a, b, c = PLACE[s["key"]]
        L.append("    {%s, %s, %s, %s, %d, %.3ff}," % (c_str(s["key"]), c_str(a), c_str(b), c_str(c), g, s["pin"][1]))
    L += ["};", "", "static const hzmOpsEntry_t hzmOpsEntries[HZM_OPS_NENTRIES] = {"]
    W = entry_weights(groups)
    for e, w in zip(ENTRIES, W):
        L.append("    {%d, %s, %s, %d, %d, %d, %s, %d, %d, %d}," % (e["slot"], c_str(e["map"]), c_str(e["name"]), MODE_GT[e["mode"]],
                                                               e["bots"][0], e["bots"][1], c_str(e["side"]), w,
                                                               e["limit"][0], e["limit"][1]))
    L += ["};", "", "// per exclusion group: the share of its windows that open a contract",
          "static const int hzmOpsGroupPct[HZM_OPS_NGROUPS] = {" + ", ".join(str(group_pct(g, groups)) for g in range(max(groups) + 1)) + "};",
          "", "static const hzmOpsSkill_t hzmOpsSkills[] = {"]
    L += ["    {%s, %d, %d}," % (c_str(n), w, x) for n, w, x in SKILLS] + ["};", "static const hzmOpsMod_t hzmOpsMods[] = {"]
    L += ["    {%s, %s, %d}," % (c_str(n), c_str(MOD_CARD[n]), w) for n, w in MODS] + ["};"]
    L += ["static const char *const hzmOpsAdj[] = {" + ", ".join(c_str(a) for a in ADJ) + "};",
          "static const char *const hzmOpsNoun[] = {" + ", ".join(c_str(a) for a in NOUN) + "};"]
    open(path, "w", newline="\n").write("\n".join(L) + "\n")


def mp_table(path):
    """coop_mod/mp_ops_table.scr (MP-owned, generated): per OBJ map the sapper side and the charges' targetnames"""
    L = ["//==========================================================================================================//",
         "// GENERATED by docs/proposals/livemap_2026-11-09/gen_ops.py - do not hand-edit. MP-owned (coop_mod/mp*.scr).",
         "// Live Operations, objective contracts: the stock map's planting side and the targetnames of its charges.",
         "//==========================================================================================================//",
         "",
         "alive:{", "\tend 1", "}end", "",
         "side local.m:{", '\tlocal.r = ""']
    for mp, (side, _b, _t) in sorted(OBJ_META.items()):
        L.append('\tif( local.m == "%s" ){ local.r = "%s" }' % (mp, side))
    L += ["}end local.r", "", "charge local.m local.i:{", '\tlocal.r = ""']
    for mp, (_s, bombs, _t) in sorted(OBJ_META.items()):
        for i, b in enumerate(bombs):
            L.append('\tif( local.m == "%s" && local.i == %d ){ local.r = "%s" }' % (mp, i + 1, b))
    L += ["}end local.r", ""]
    # [LIBERATION] the spots a German may be placed on (every team / deathmatch spawn point of the BSP, deduplicated -
    # lib_points.json, `gen_ops.py libpoints`), and the test mode's stand-in player spot
    pts = json.load(open(os.path.join(HERE, "lib_points.json")))
    L += ["// LIBERATION: the hunt spots of each pool map (spawn points from the BSP; mp_ops.scr grounds and sight-checks each)",
          "libpts local.m:{", "\tlocal.r = NIL"]
    for mp in sorted(LIB_POOL):
        L.append('\tif( local.m == "%s" ){' % mp)
        for i, (x, y, z) in enumerate(pts[mp]["spots"]):
            L.append("\t\tlocal.r[%d] = ( %d %d %d )" % (i + 1, x, y, z))
        L.append("\t}")
    L += ["}end local.r", "", "libally local.m:{", "\tlocal.r = NIL"]
    for mp in sorted(LIB_POOL):
        x, y, z = pts[mp]["ally"]
        L.append('\tif( local.m == "%s" ){ local.r = ( %d %d %d ) }' % (mp, x, y, z))
    L += ["}end local.r", ""]
    open(path, "wb").write(("\r\n".join(L) + "\r\n").encode("latin-1"))


def lib_points(gog):
    """lib_points.json: per MP map of the install, every info_player_deathmatch / _allied / _axis origin in its BSP (the
    retail paks only, later paks win as the game mounts them), deduplicated at 48 u, plus the stand-in player spot of the
    dedicated test (the Allied spawn farthest from the Axis spawns' centre). Read straight from the entity lump text."""
    import glob, re, zipfile
    src = {}
    for d in ("main", "mainta", "maintt"):
        for pk in sorted(glob.glob(os.path.join(gog, d, "*.pk3")), key=str.lower):
            if os.path.basename(pk).lower().startswith("zzz"):
                continue
            z = zipfile.ZipFile(pk)
            for n in z.namelist():
                l = n.lower()
                if l.endswith(".bsp") and l.count("/") == 2 and l.split("/")[1] in ("dm", "obj", "lib"):
                    src[l[5:-4]] = (pk, n)
    out = {}
    for mp, (pk, n) in sorted(src.items()):
        b = zipfile.ZipFile(pk).read(n).decode("latin-1")
        cls = {}
        for blk in re.findall(r"\{([^{}]{0,2000})\}", b):
            kv = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', blk))
            c = kv.get("classname", "")
            if c in ("info_player_deathmatch", "info_player_allied", "info_player_axis") and "origin" in kv:
                try:
                    cls.setdefault(c, []).append([int(round(float(v))) for v in kv["origin"].split()[:3]])
                except ValueError:
                    pass
        spots = []
        for c in ("info_player_deathmatch", "info_player_axis", "info_player_allied"):
            for p in cls.get(c, []):
                if all(math.dist(p, q) >= 48 for q in spots):
                    spots.append(p)
        ax = cls.get("info_player_axis") or spots
        cx = [sum(p[i] for p in ax) / len(ax) for i in range(3)]
        al = cls.get("info_player_allied") or cls.get("info_player_deathmatch") or spots
        ally = max(al, key=lambda p: math.dist(p, cx))
        lo = [min(p[i] for p in spots) for i in range(2)]
        hi = [max(p[i] for p in spots) for i in range(2)]
        out[mp] = {"spots": spots, "ally": ally, "spread": int(math.dist(lo, hi)),
                   "counts": {c: len(v) for c, v in sorted(cls.items())}}
        print("%-28s spots %3d  spread %6d u  %s" % (mp, len(spots), out[mp]["spread"], out[mp]["counts"]))
    json.dump(out, open(os.path.join(HERE, "lib_points.json"), "w"), indent=0, sort_keys=True)
    print("wrote", os.path.join(HERE, "lib_points.json"))


# ------------------------------------------------------------------------------------------------ CLI


def describe(c):
    e = ENTRIES[c["entry"]]
    return "t=%d slot=%s map=%s mode=%s bots=%d skill=%s mod=%s side=%s life=%d left=%d name=%s serial=%d" % (
        c["t"], SLOTS[c["slot"]]["key"], e["map"], e["mode"], c["bots"], SKILLS[c["skill"]][0], MODS[c["mod"]][0] or "-",
        c["side"], c["life"], c.get("left", -1), c["name"].replace(" ", "_"), c["serial"])


def main():
    a = sys.argv
    sheet = a[a.index("--sheet") + 1] if "--sheet" in a else r"H:\hzm_work\liveops-warmap"
    js = load_sheet(sheet)
    placed, groups, problems = layout(js)
    if a[1] == "check":
        for s, p, g in zip(SLOTS, placed, groups):
            print("%-18s group %2d  loop (%6.0f,%6.0f) r%3.0f  stamp %s" % (s["key"], g, p["c"][0], p["c"][1], p["r"], tuple(int(v) for v in p["stamp"])))
        print("problems:", problems or "none")
        import time as _t
        t0 = int(_t.time()) // 60 * 60
        counts, maps = [], {}
        for k in range(0, 24 * 60):
            live = roll(t0 + k * 60 + 30, groups)
            counts.append(len(live))
            for c in live:
                maps[ENTRIES[c["entry"]]["map"]] = maps.get(ENTRIES[c["entry"]]["map"], 0) + 1
        print("24h census: live mean %.2f min %d max %d; zero-minutes %d" % (sum(counts) / len(counts), min(counts), max(counts), counts.count(0)))
        print(" ", sorted(maps.items(), key=lambda kv: -kv[1]))
        modes = {}
        for k in range(0, 24 * 60):
            for c in roll(t0 + k * 60 + 30, groups):
                md = ENTRIES[c["entry"]]["mode"]
                modes[md] = modes.get(md, 0) + 1
        tot = sum(modes.values()) or 1
        print("  contract-minutes by mode:", {m: "%.0f%%" % (100.0 * n / tot) for m, n in sorted(modes.items())})
        sys.exit(1 if problems else 0)
    if a[1] == "dump":
        utc = int(a[2])
        for c in roll(utc, groups):
            print("OPS " + describe(c))
    if a[1] == "engine":
        engine_header(os.path.join(a[2], "code", "client", "cl_hzm_ops_table.h"), js)
        print("wrote", os.path.join(a[2], "code", "client", "cl_hzm_ops_table.h"))
    if a[1] == "mp":
        mp_table(os.path.join(a[2], "coop_mod", "mp_ops_table.scr"))
        print("wrote mp_ops_table.scr")
    if a[1] == "libpoints":
        lib_points(a[2] if len(a) > 2 and not a[2].startswith("--") else r"G:\GOG\Medal of Honor - Allied Assault War Chest")


if __name__ == "__main__":
    main()
