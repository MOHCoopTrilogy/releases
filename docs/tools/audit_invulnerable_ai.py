#!/usr/bin/env python
"""
audit_invulnerable_ai.py - find enemies the map scripts make invulnerable, and what undoes it.

WHY THIS EXISTS (bug-3188, and the m1l2a "cant kill one enemy" report)
    Vanilla map scripts make actors `nodamage` / `immune` for set pieces (an intro vignette, a
    truck ride, a cutscene) and rely on single-player flow to end the set piece. In coop the players
    are free to leave the flow, so an enemy can be left invulnerable -- and worse, can be shooting
    back while invulnerable. This scanner enumerates every such site in every coop map (AA m*, SH t*,
    BT e*) plus the coop framework itself, decides who the target is, looks for what undoes the
    protection, and says which sites can leave an ENEMY fighting while invulnerable.

WHAT IT REPORTS  (one row per site; `--md` for a table, `--tsv FILE`, `--json FILE`)
    side      HOSTILE   the target is (or resolves to) a german/axis actor
              FRIENDLY  allied actor: escorts / scene cast that MUST survive -> protection is intended
              NONAI     vehicle, turret, prop, trigger, player, invisible-man helper -> not an actor
              UNKNOWN   could not be resolved statically -> reviewed by hand (see REVIEWED)
    undo      where the protection is lifted for the same target: takedamage, or the target being
              removed/killed in the same function.  `-` means nothing ever lifts it.
    passive   the target is switched off (disable_ai / ai_off / threatbias ignoreme / notsolid ...)
              in the same function, i.e. a prop-like set-piece body that is not fighting.
    verdict   OK-FRIENDLY / OK-NONAI            intended protection
              OK-UNDONE                          hostile, protection lifted (still see `where`)
              OK-REVIEWED                        hostile/unknown, judged by hand, note in REVIEWED
              BUG-FIGHTS-INVULN                  hostile, AI live, nothing lifts it
              BUG-NO-UNDO                        hostile, passive, nothing lifts it (a player can meet it)
              REVIEW                             hostile or unknown, not yet judged -> fails the run

    The scanner also lists every other invulnerability mechanism it can see on a hostile target:
    `immune <type>`, a health write >= 1000, and `notsolid` with no `solid` afterwards.

STATIC LIMITS (read before trusting a green run)
    Resolution is textual: `$name` against the map's BSP actor census (docs/tools/invuln_bsp_actors.json,
    regenerated with `--dump-bsp` from the game paks), `local.x`/`level.x` through their assignment in
    the function, `self` through the `$name thread <label>` callers. Anything else is UNKNOWN and must be
    judged by hand. A green run means "no unreviewed hostile site", not "no invulnerable enemy exists":
    engine-side and runtime-only causes (pain buffer, TRAPS on aihandler) are out of reach here.

USAGE
    python docs/tools/audit_invulnerable_ai.py                 # summary + non-OK rows, exit 1 on any BUG/REVIEW
    python docs/tools/audit_invulnerable_ai.py --md            # full markdown table (every site)
    python docs/tools/audit_invulnerable_ai.py --map m1l2a     # one map
    python docs/tools/audit_invulnerable_ai.py --dump-bsp      # rebuild invuln_bsp_actors.json from the game paks
    python docs/tools/audit_invulnerable_ai.py --selftest      # built-in fixtures

Exit 0 = every hostile/unknown site is undone or reviewed; 1 = something needs a fix or a review.
"""
import argparse, glob, json, os, re, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
CENSUS = os.path.join(HERE, "invuln_bsp_actors.json")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"

# ------------------------------------------------------------------------------------------------
# HAND JUDGEMENTS (2026-09-29 sweep). Rules are (map, function-regex, subject-regex, TAG, note).
# A hostile/unknown site matching a rule is OK-REVIEWED with that tag; anything new fails the run until a
# human reads it and adds (or fixes) it here. Delete a rule when its site goes away.
#   FRIENDLY    allied/escort/scene cast: protection is the point
#   PLAYER      a player is made nodamage on purpose (ride, eject, drop window)
#   NONAI       vehicle, turret, prop, tree, trigger, plane: not an actor
#   PROP        hostile-looking body that is hidden / notsolid / AI-off scenery, never fights invulnerable
#   DYING       nodamage is set AFTER the killing blow, during a scripted death fall / mortar flip
#   UNDONE      lifted unconditionally in the same scripted sequence before the body can fight
#   COOP-GUARDED coop code already restores it (failsafe / removal), named in the note
#   BY-DESIGN   invulnerable on purpose (stealth mission: cover blown = players drop to 1 hp and the mission
#               fails, or a scripted finale); documented, left alone
#   FIXED       was a bug, fixed in the v1.10.5 staging (see docs/proposals/invuln_ai_audit_2026-09-29/README.md)
# ------------------------------------------------------------------------------------------------
RULES = [
    # ---- e1l1
    ("e1l1", r"tankfixerguy|jeep2guy", None, "PROP", "intro cinematic props: notsolid, looped anim, removed at the end of the intro"),
    ("e1l1", r"bazookashoot", None, "UNDONE", "removed at the end of the gag (BazookaShoot.scr)"),
    ("e1l1", r"playergetin", None, "PLAYER", "player driving the tank"),
    ("e1l1", r"init", r"\$driver", "PROP", "scene6 jeep driver, AI off, ignoreme"),
    ("e1l1", r"tossguy", None, "UNDONE", "takedamage two lines later in the same function"),
    # ---- e1l2
    ("e1l2", r"bazookaguygo", None, "UNDONE", "takedamage in the same function once he has run to his node"),
    # ---- e1l3 : stealth mission, cover blown = players to 1 hp + missionfailed
    ("e1l3", r"makeinvulnerable", None, "FRIENDLY", "briefing cast (Briefing.scr)"),
    ("e1l3", r"loadboat|gunnergetinboat", None, "FRIENDLY", "US boat crew"),
    ("e1l3", r"coverguysbridgegag_thread", None, "UNDONE", "CoverGuyAssaultThink_Single: AI off while running to the assault point, then takedamage"),
    ("e1l3", r"spawncourtyardguy|truckguard1|truckguard2|spawnbiggerman", None, "BY-DESIGN",
        "courtyard guards of the papers/disguise gauntlet: nodamage + 10000 hp until the cover is blown; enableEnemyOnAll then sets every player to 1 hp and coop missionfailed runs (courtyard.scr:171-225)"),
    ("e1l3", r"loadpassenger", None, "PROP", "Sneakers convoy passengers: AI disabled by EntityIterateCommand, never unload, removed by convoyVehicleRemove"),
    ("e1l3", r"clausruns", None, "FRIENDLY", "Claus, the friendly spy"),
    # ---- e1l4
    ("e1l4", r"doorclosingguy", None, "UNDONE", "takedamage three lines later"),
    ("e1l4", r"initmaproom", None, "PROP", "hidden, AI off, notsolid until the alarm (alarmguy takedamage + attackplayer)"),
    # ---- e2l1
    ("e2l1", r"ab41_motion", None, "PROP", "hidden, notsolid AB41 driver, removed at the end of the scene"),
    ("e2l1", r"spawn_damaged_new", None, "NONAI", "wreck model"),
    ("e2l1", r"bringtruck|starttruck", None, "COOP-GUARDED", "truck crew is nodamage only while seated with AI off; vehicles_thinkers::truck_unload lifts it and coop_unloadFailsafe covers a stuck unload (bug-1315)"),
    ("e2l1", r"coop_handleplayerglidereject|coop_chutedrop", None, "PLAYER", "eject / chute-drop window, coop restores it"),
    # ---- e2l2 / e2l3
    ("e2l2", r"fireshots", None, "UNDONE", "one-frame nodamage around a scripted shot"),
    ("e2l3", r"init", r"battlehousegunner_front", "COOP-GUARDED", "coop_battleHouseGunnerArm failsafe (user 08-02) lifts it"),
    ("e2l3", r"think", r"self", "FRIENDLY", "Johnson"),
    ("e2l3", r"monitorlandinghealth|diedintheair", None, "FRIENDLY", "82nd paratroopers (allied); DiedInTheAir is the death path"),
    ("e2l3", r"createinvisibletarget", None, "PROP", "hidden notsolid decoy target for AI fire"),
    # ---- e3l1
    ("e3l1", r"attachtojeep|passengergetinjeep", None, "FRIENDLY", "British jeep crew"),
    ("e3l1", r"startaagun", None, "FRIENDLY", "British AA gun crew"),
    ("e3l1", r"initjeepstuck|initp47", None, "NONAI", "pillars / triggers / plane"),
    ("e3l1", r"dobalconydeath", None, "DYING", "nodamage only during the scripted balcony fall after the hit"),
    ("e3l1", r"initintro", r"ambushgunners", "UNDONE", "intro cutscene: takedamage + enable_ai when the ambush anim ends (Intro.scr:434)"),
    # ---- e3l2
    ("e3l2", r"mcpow1runtobriefing|mcpowescape|exitstageleft|runforcover", None, "FRIENDLY", "POWs"),
    ("e3l2", r"playerdismountcannon", None, "NONAI", "cannon"),
    ("e3l2", r"mybalconyfall", None, "DYING", "balcony fall after the hit"),
    # ---- e3l3
    ("e3l3", r"killtree|finishjumpthread|kfiveinit", None, "NONAI", "tree / destroyed AB41 / K5"),
    ("e3l3", r"balconyguy|fallerguy", None, "DYING", "balcony fall after the hit"),
    ("e3l3", r"explosioninit", None, "BY-DESIGN", "scripted finale: the two tower guards shoot, then die in Left/RightSideExplosion; every player is nodamage for the finale"),
    # ---- e3l4
    ("e3l4", r"passengergetinwillys|forcecrewintojeep", None, "FRIENDLY", "Allied jeep crew"),
    ("e3l4", r"createmrinvisible", None, "PROP", "hidden notsolid shooter helper, removed at the trigger"),
    # ---- m1l1 / m1l2a
    ("m1l1", r"main", r"barrel_guy", "FIXED", "bug-3188 (v1.10.4): scenery recipe + leave-the-box invariant"),
    ("m1l2a", r"canteen|flagthread19", None, "FRIENDLY", "SAS agent / Jury"),
    ("m1l2a", r"spothide", None, "NONAI", "spotdamage trigger"),
    # ---- m1l3b / m2l1
    ("m4l3", r"ai_prep", r"realtruck_driver", "PROP", "opel driver: AI off, notsolid, weapon none, seated in a static truck"),
    ("t1l3", r"balcony_death_nazi_deathcheck", None, "DYING", "10000 hp until the first hit, then the scripted balcony fall (nodamage only during the fall)"),
    ("m1l3b", r"strafing_loop", None, "NONAI", "plane"),
    ("m2l1", r"super_sniper_init", None, "UNDONE", "scene1 removes $super_sniper in coop (m2l1.scr:247), so the immune/nodamage body never exists"),
    # ---- m3l1a / m3l1b / m3l2 / m3l3
    ("m3l1a", r"sequence_5_.*|dragging_guys_blow|coop_vigspawn|coop_flanklandings|coop_hedgecrowdspawn|sequence_7_spawn_shingle|sequence_12_bunker_base", None, "FRIENDLY", "Ranger landing/beach vignette cast (allied)"),
    ("m3l1b", r"coop_ally_spawn", None, "FRIENDLY", "allied ranger (kind 4 is the protected escort)"),
    ("m3l2", r"scene1|scene2|ramsey_setup", None, "FRIENDLY", "Ramsey / Paulsen"),
    ("m3l3", r"captainramsey|airborneguys|scene3_spawn1_hint", None, "FRIENDLY", "Ramsey / Harrison / Tomlin"),
    # ---- m5 / m6 / t*
    ("m5l1b", r"medic_prep", None, "FRIENDLY", "medic"),
    ("m5l2b", r"coop_immunisefrombullets", None, "NONAI", "tanks / flaks (Smithy: stop small arms killing them)"),
    ("m5l2a", r"coop_immunisefrombullets", None, "NONAI", "tanks / flaks"),
    ("m6l3a", r"scene4_jailswitch_activate", None, "PROP", "hidden notsolid AI-off helper"),
    ("m6l3a", r"scene5_rangerteam_setup", None, "FRIENDLY", "ranger team"),
    ("m6l3a", r"main", r"scene4_mg[12]_gunner", "UNDONE", "hidden + notsolid until scene4, which does show/solid/takedamage (m6l3a.scr:1628-1635)"),
    ("t2l1", r".*", r"nebel\d_turret0", "NONAI", "nebelwerfer turrets"),
    ("t2l2", r".*", r"s1_truck1\.driver", "FRIENDLY", "allied supply-truck crew (2nd Ranger)"),
    ("t2l3", r"playertreethink", None, "NONAI", "tree"),
    ("t2l3", r"initthemap|kommanderinitwave3|kommanderthink", r"enemy|newguy|halftrack1_gunner", "BY-DESIGN",
        "immune to EXPLOSION only (their own mortars/barrels); bullets kill them. halftrack1_gunner: hidden until wave 3, then takedamage (t2l3.scr:1622)"),
    ("t3l2", r"coop_t3l2_seatrider", None, "PLAYER", "tank rider"),
    # ---- global scripts (shared by many maps)
    ("global", r"transform", None, "NONAI", "TransformActor option table, applied only when the map asks for it"),
    ("global", r"init_autoplane|startplane|stukastraferun|stukastrafetrigger", None, "NONAI", "planes"),
    ("global", r"init_autotanks|init|starttruck", None, "NONAI", "autotank/autotruck hulls"),
    ("global", r"loadpassenger", None, "COOP-GUARDED", "autotruck crew is nodamage only when the map sets passengerstakedamage 0 (no map does) or inside a jeep with AI off"),
    ("global", r"checkdeath", None, "DYING", "cabinet gag: the hidden guard plays cabinet_hiding_death"),
    ("global", r"canteen|heal", None, "FRIENDLY", "friendly.scr canteen / heal window (one frame to seconds)"),
    ("global", r"initlandmines", None, "NONAI", "landmines"),
    ("global", r"stickybombhide", None, "NONAI", "sticky bombs"),
    ("global", r"coop_setdriverfortank", None, "PLAYER", "tank driver"),
    ("global", r"player_jeep_controller", None, "NONAI", "player jeep"),
    ("global", r"enemy_half-trak_think", None, "BY-DESIGN", "half-track hull immune to bullets/grenades (rockets kill it), its MG gunner is armour-shielded and dies with the hull"),
]


def rule_for(r):
    for m, fnre, subre, tag, note in RULES:
        if m != r["map"]:
            continue
        if not re.fullmatch(fnre, r["fn"], re.I):
            continue
        if subre and not re.search(subre, r["subj"], re.I):
            continue
        return tag, note
    return None


HOSTILE_RE = re.compile(r"german|afrika|wehrm|nazi|(^|[/_])ss[_/]|axis|kriegs|luftwaffe|fallschirm|panzer_?grenadier|gestapo", re.I)
FRIEND_RE = re.compile(r"allied|american|ranger|brit|oss[_-]|airborne|(^|[^a-z])usa|_us_|french|resistance|prisoner|russian|(^|[^a-z])pow|medic|marine|paratroop|(^|[^a-z])sas|commando|engineer", re.I)


def game_of(name):
    n = name.lower()
    if n == "global":
        return "ALL"
    if n.startswith("t") and n[1:2].isdigit():
        return "SH"
    if n.startswith("e") and n[1:2].isdigit():
        return "BT"
    return "AA"


# ---------------------------------------------------------------------------------------------- BSP
def read_entities(bsp):
    i = bsp.find(b'"classname"')
    if i < 0:
        return []
    i = bsp.rfind(b"{", 0, i)
    j = bsp.find(b"\x00", i)
    txt = bsp[i:j].decode("latin1")
    out = []
    for blk in re.findall(r"\{(.*?)\}", txt, re.S):
        out.append(dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', blk)))
    return out


def side_of(classname, model):
    """The model is what the player sees, so it outranks the entity class (m1l2b Grillo is an
    ai_german_* class wearing allied_oss_man_m1.tik and is script-set to the allied team)."""
    for s in (model or "", classname or ""):
        if HOSTILE_RE.search(s):
            return "hostile"
        if FRIEND_RE.search(s):
            return "friendly"
    return "actor?"


def dump_bsp():
    maps = coop_maps()
    paks = []
    for d in ("main", "mainta", "maintt"):
        paks += sorted(glob.glob(os.path.join(GOG, d, "*.pk3")), key=lambda p: p.lower())
    found = {}
    for pk in paks:
        try:
            z = zipfile.ZipFile(pk)
        except Exception:
            continue
        names = {n.lower(): n for n in z.namelist()}
        for m in maps:
            key = "maps/%s.bsp" % m
            if key in names:
                found[m] = (pk, z.read(names[key]))
    census = {}
    for m, (pk, data) in sorted(found.items()):
        ents = {}
        for e in read_entities(data):
            tn = e.get("targetname", "") or e.get("$targetname", "")
            cn = e.get("classname", "")
            mdl = e.get("model", "")
            isactor = bool(re.search(r"(^|_)ai_|^actor|^Actor$", cn))
            if isactor:
                sd = side_of(cn, mdl)
                if e.get("team") in ("german", "axis"):
                    sd = "hostile"
                if tn:
                    ents[tn.lower()] = {"kind": "actor", "side": sd, "class": cn, "model": mdl}
            elif tn:
                ents[tn.lower()] = {"kind": "other", "class": cn}
        census[m] = ents
    with open(CENSUS, "w") as f:
        json.dump(census, f, separators=(",", ":"), sort_keys=True)
    print("wrote %s (%d maps)" % (CENSUS, len(census)))


def load_census():
    try:
        return json.load(open(CENSUS))
    except Exception:
        return {}


# ---------------------------------------------------------------------------------------------- scripts
def coop_maps():
    out = []
    for p in glob.glob(os.path.join(MOD, "maps", "*.scr")):
        n = os.path.basename(p)
        if n.lower().endswith("_precache.scr"):
            continue
        try:
            if "coop_mod/main.scr::main" in open(p, "rb").read().decode("latin1"):
                out.append(n[:-4].lower())
        except Exception:
            pass
    return sorted(out)


def strip_comments(text):
    """Blank // and /* */ comments (keeping line structure) and leave string contents alone."""
    out = []
    i, n = 0, len(text)
    instr = False
    inblk = False
    while i < n:
        c = text[i]
        if inblk:
            if text.startswith("*/", i):
                inblk = False
                out.append("  ")
                i += 2
            else:
                out.append("\n" if c == "\n" else " ")
                i += 1
            continue
        if instr:
            out.append(c)
            if c == '"' or c == "\n":
                instr = False
            i += 1
            continue
        if c == '"':
            instr = True
            out.append(c)
            i += 1
            continue
        if text.startswith("//", i):
            while i < n and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if text.startswith("/*", i):
            inblk = True
            out.append("  ")
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


LABEL_RE = re.compile(r"^([A-Za-z_][\w\-]*)\b[^\n:{}]*:\s*\{?\s*$")
SUBJ = r"(?:\$\([^)]*\)|\$\w+|local\.\w+|level\.\w+|group\.\w+|self)(?:\[[^\]]*\])?(?:\.\w+)?"
SITE_RE = re.compile(r"(?P<subj>" + SUBJ + r")\s+(?P<cmd>nodamage|takedamage|immune\s+\w+)\b")
CMD_RE = re.compile(r"(?P<subj>" + SUBJ + r")\s+(?P<cmd>exec\s+\S*(?:disable_ai|ai_off)\S*|waitexec\s+\S*disable_ai\S*|threatbias\s+ignoreme|notsolid|hide|physics_off|solid|show|remove|delete|kill|enable_ai|exec\s+\S*enable_ai\S*)\b")
HEALTH_RE = re.compile(r"(?P<subj>" + SUBJ + r")\s*\.health\s*=\s*(?P<n>\d+)\b|(?P<subj2>" + SUBJ.replace("(?:\\.\\w+)?", "") + r")\.health\s*=\s*(?P<n2>\d+)")


SP_ONLY_RE = re.compile(r"(?<!\w)if\s*\(\s*level\.gametype\s*==\s*0\s*\)\s*\{[^}]*$")


HEALTH_CMD_RE = re.compile(r"(" + SUBJ + r")\s+health\s+(\d{4,})\b")


class Fn:
    def __init__(self, name, start):
        self.name, self.start, self.end, self.lines = name, start, start, []


def load_script(path):
    raw = open(path, "rb").read().decode("latin1")
    clean = strip_comments(raw).split("\n")
    fns, cur = [], Fn("<top>", 0)
    fns.append(cur)
    for i, ln in enumerate(clean):
        if ln[:1] not in (" ", "\t", "") and LABEL_RE.match(ln.rstrip()):
            cur = Fn(LABEL_RE.match(ln.rstrip()).group(1).lower(), i)
            fns.append(cur)
        cur.lines.append((i + 1, ln))
        cur.end = i
    return fns


def norm_subj(s):
    s = s.strip()
    s = re.sub(r"\[[^\]]*\]", "", s)
    return s.lower()


def map_files(m):
    """All script files belonging to a map: maps/<m>.scr (any case) + maps/<m>/*.scr."""
    files = []
    for p in glob.glob(os.path.join(MOD, "maps", "*.scr")):
        if os.path.basename(p)[:-4].lower() == m:
            files.append(p)
    d = None
    for c in glob.glob(os.path.join(MOD, "maps", "*")):
        if os.path.isdir(c) and os.path.basename(c).lower() == m:
            d = c
    if d:
        files += sorted(glob.glob(os.path.join(d, "**", "*.scr"), recursive=True))
    return files


# ---------------------------------------------------------------------------------------------- resolution
class Ctx:
    def __init__(self, m, census, allfns):
        self.m, self.census, self.allfns = m, census, allfns

    def bsp(self, name):
        return self.census.get(self.m, {}).get(name.lower())

    def spawned_side(self, text_lines, varpat):
        pass


SPAWN_RE = re.compile(r"spawn\s+(?:actor\s+)?\"?([\w/\.\-]+)\"?(.*)$", re.I)


def side_from_model(model):
    if not model:
        return None
    if HOSTILE_RE.search(model):
        return "hostile"
    if FRIEND_RE.search(model):
        return "friendly"
    return None


def name_guess(nm):
    """Last resort, only for script-spawned names we could not trace. Marked `name-guess` in the table."""
    if re.search(r"german|nazi|enemy|killer|axis|(^|_)ss(_|$)|wehrm|afrika", nm, re.I):
        return "hostile"
    if re.search(r"ranger|engineer|friend|ally|allie|brit|prisoner|pow(\d|_|$)|spy|hudson|cappy|medic|paratroop|glider|pilot|ramsey|grillo|manon", nm, re.I):
        return "friendly"
    return None


def resolve(subj, fn, path, fnmap, ctx, depth=0):
    """-> (side, how)  side in hostile/friendly/nonai/unknown"""
    if depth > 3:
        return "unknown", "depth"
    s = subj.strip()
    base = re.sub(r"\[[^\]]*\]", "", s)
    low = base.lower()
    if low.startswith("$") and not low.startswith("$("):
        nm = low[1:]
        if nm == "player" or nm.startswith("player"):
            return "nonai", "player"
        e = ctx.bsp(nm)
        if e:
            if e["kind"] == "actor":
                return {"hostile": "hostile", "friendly": "friendly"}.get(e["side"], "unknown"), "bsp:%s %s" % (e["class"], e["model"])
            return "nonai", "bsp:%s" % e["class"]
        # script-spawned with a targetname?  (spawn "models/human/x" targetname "name" ...  /  var targetname "name")
        nmre = re.escape(nm)
        for f in ctx.allfns:
            for ln, t in f[1].lines:
                if re.search(r"spawn\b", t, re.I) and re.search(r"targetname\s+\"?%s\"?(\s|$)" % nmre, t, re.I):
                    mdl = re.search(r"(?:model\s+|\")?((?:models/|human/)[\w/\.\-]+)", t, re.I)
                    sd = side_from_model(mdl.group(1)) if mdl else None
                    if sd:
                        return sd, "spawn:" + mdl.group(1)
                mm = re.search(r"(%s)\s+targetname\s+\"%s\"|(%s)\.targetname\s*=\s*\"%s\"" % (SUBJ, nmre, SUBJ, nmre), t, re.I)
                if mm:
                    var = mm.group(1) or mm.group(2)
                    r = resolve(var, f[1], f[0], None, ctx, depth + 1)
                    if r[0] != "unknown":
                        return r[0], "named:" + r[1]
        g = name_guess(nm)
        if g:
            return g, "name-guess"
        return "unknown", "no-bsp-entity"
    if low.startswith("$("):
        return "unknown", "dynamic-name"
    if re.search(r"\.(gun|gun2|turret|usable_cannon|driver|rider)$", low):
        return "nonai", "attachment:" + low.split(".")[-1]
    if low == "self" or low.startswith("self."):
        callers = set()
        pat = re.compile(r"(" + SUBJ + r")\s+(?:thread|waitthread|exec|waitexec)\s+(?:[\w/\.]*::)?" + re.escape(fn.name) + r"\b", re.I)
        for f in ctx.allfns:
            for ln, t in f[1].lines:
                for mm in pat.finditer(t):
                    callers.add((mm.group(1), f[1], f[0]))
        sides = set()
        for c, cfn, cpath in callers:
            if norm_subj(c) == "self" and cfn.name == fn.name:
                continue
            sd, _ = resolve(c, cfn, cpath, fnmap, ctx, depth + 1)
            sides.add(sd)
        if not sides:
            # bsp thread/flagthread key on an actor? unknown
            return "unknown", "self:no-caller"
        if sides == {"friendly"}:
            return "friendly", "self<-callers"
        if "hostile" in sides:
            return "hostile", "self<-callers"
        if sides == {"nonai"}:
            return "nonai", "self<-callers"
        return "unknown", "self<-mixed"
    if low.startswith("local.") or low.startswith("level.") or low.startswith("group."):
        v = re.escape(low)
        for _, t in fn.lines:
            mm = re.match(r"\s*" + v + r"\s*=\s*(.*)$", t, re.I)
            if mm:
                rhs = mm.group(1).strip()
                sp = SPAWN_RE.search(rhs)
                if sp:
                    sd = side_from_model(sp.group(1))
                    if sd:
                        return sd, "spawn:" + sp.group(1)
                r2 = re.match(r"(\$[\w]+(?:\[[^\]]*\])?)", rhs)
                if r2:
                    return resolve(r2.group(1), fn, path, fnmap, ctx, depth + 1)
                r3 = re.match(r"(level\.\w+)", rhs)
                if r3 and r3.group(1).lower() != low:
                    return resolve(r3.group(1), fn, path, fnmap, ctx, depth + 1)
        if low.startswith("level."):
            for f in ctx.allfns:
                for _, t in f[1].lines:
                    mm = re.match(r"\s*" + v + r"\s*=\s*(.*)$", t, re.I)
                    if mm:
                        rhs = mm.group(1).strip()
                        sp = SPAWN_RE.search(rhs)
                        if sp and side_from_model(sp.group(1)):
                            return side_from_model(sp.group(1)), "spawn:" + sp.group(1)
                        r2 = re.match(r"(\$[\w]+(?:\[[^\]]*\])?)", rhs)
                        if r2:
                            return resolve(r2.group(1), f[1], f[0], fnmap, ctx, depth + 1)
            m2 = re.match(r"level\.friend", low)
            if m2:
                return "friendly", "name:level.friend*"
        # param / loop var: look for a for-loop over an array on a hostile targetname
        for _, t in fn.lines:
            mm = re.search(v + r"\s*=\s*(\$\w+)\s*\[", t, re.I)
            if mm:
                return resolve(mm.group(1), fn, path, fnmap, ctx, depth + 1)
        return "unknown", "unresolved-var"
    return "unknown", "other"


# ---------------------------------------------------------------------------------------------- per-map scan
PASSIVE_RE = re.compile(r"disable_ai|ai_off|threatbias\s+ignoreme|\bnotsolid\b|anim_scripted|physics_off|\bhide\b")


def rel(p):
    r = os.path.relpath(p, MOD).replace("\\", "/")
    return r[5:] if r.startswith("maps/") else r


def find_undo(base, fn, path, allfns):
    """What lifts the protection on `base` (normalised subject)?  Returns a short string or '-'.
    1. takedamage on the same subject (same function for local./self, anywhere in the map otherwise)
    2. `<subject> thread|waitthread|exec <G>` where G does `self takedamage`
    3. for `self`: any of 1/2 for each caller subject of this function
    4. the subject is removed/deleted/killed later in the same function"""
    def takedamage_on(b, only_fn=None):
        for p2, f2 in allfns:
            if only_fn is not None and f2 is not only_fn:
                continue
            for ln2, t2 in f2.lines:
                for m2 in SITE_RE.finditer(t2):
                    if m2.group("cmd") == "takedamage" and norm_subj(m2.group("subj")) == b:
                        return "%s:%d (%s)" % (rel(p2), ln2, "same-fn" if f2 is fn else f2.name)
        return None

    def via_thread(b):
        selfundo = {}
        for p2, f2 in allfns:
            for ln2, t2 in f2.lines:
                for m2 in SITE_RE.finditer(t2):
                    if m2.group("cmd") == "takedamage" and norm_subj(m2.group("subj")) == "self":
                        selfundo[f2.name] = "%s:%d (%s)" % (rel(p2), ln2, f2.name)
        for p2, f2 in allfns:
            for ln2, t2 in f2.lines:
                for m2 in re.finditer(r"(%s)\s+(?:thread|waitthread|exec|waitexec)\s+(?:[\w/\.]*::)?([\w\-]+)" % SUBJ, t2, re.I):
                    if norm_subj(m2.group(1)) == b and m2.group(2).lower() in selfundo:
                        return selfundo[m2.group(2).lower()] + " via thread at %s:%d" % (rel(p2), ln2)
        return None

    local_only = base.startswith("local.") or base == "self"
    if local_only:
        r = takedamage_on(base, only_fn=fn)
    else:
        r = takedamage_on(base)
    if r:
        return r
    if base != "self":
        r = via_thread(base)
        if r:
            return r
    else:
        pat = re.compile(r"(%s)\s+(?:thread|waitthread|exec|waitexec)\s+(?:[\w/\.]*::)?%s\b" % (SUBJ, re.escape(fn.name)), re.I)
        callers = set()
        for p2, f2 in allfns:
            for ln2, t2 in f2.lines:
                for m2 in pat.finditer(t2):
                    if norm_subj(m2.group(1)) != "self":
                        callers.add(norm_subj(m2.group(1)))
        for c in sorted(callers):
            r = takedamage_on(c) or via_thread(c)
            if r:
                return r + " [caller %s]" % c
    for ln2, t2 in fn.lines:
        for m2 in CMD_RE.finditer(t2):
            if norm_subj(m2.group("subj")) == base and re.match(r"remove|delete|kill", m2.group("cmd")):
                return "%s:%d (removed)" % (rel(path), ln2)
    return "-"


def global_files():
    return [p for p in sorted(glob.glob(os.path.join(MOD, "global", "*.scr"))) if "original" not in os.path.basename(p).lower()]


def scan_map(m, census):
    files = global_files() if m == "global" else map_files(m)
    allfns = []
    for p in files:
        for fn in load_script(p):
            allfns.append((p, fn))
    ctx = Ctx(m, census, allfns)
    rows = []
    for p, fn in allfns:
        for ln, t in fn.lines:
            for mm in SITE_RE.finditer(t):
                cmd = re.sub(r"\s+", " ", mm.group("cmd"))
                if cmd == "takedamage":
                    continue
                if SP_ONLY_RE.search(t[:mm.start()]):
                    continue    # `if( level.gametype == 0 ){ X nodamage }` : single-player only, coop never runs it
                subj = mm.group("subj")
                side, how = resolve(subj, fn, p, None, ctx)
                key = "%s:%s@%s" % (m, norm_subj(subj), fn.name)
                base = norm_subj(subj)
                undo = find_undo(base, fn, p, allfns)
                passive = ""
                for ln2, t2 in fn.lines:
                    for m2 in CMD_RE.finditer(t2):
                        if norm_subj(m2.group("subj")) == base and PASSIVE_RE.search(m2.group("cmd")):
                            passive = m2.group("cmd").split()[0]
                rows.append({"map": m, "game": game_of(m), "file": rel(p),
                             "line": ln, "fn": fn.name, "subj": subj, "cmd": cmd, "side": side, "how": how,
                             "undo": undo, "passive": passive, "key": key})
    return rows


def verdict(r):
    if r["side"] == "friendly":
        return "OK-FRIENDLY"
    if r["side"] == "nonai":
        return "OK-NONAI"
    rl = rule_for(r)
    if rl:
        r["tag"], r["note"] = rl
        return "OK-REVIEWED"
    if r["cmd"].startswith("immune") and not re.search(r"bullet|shotgun|grenade|rocket|explosion", r["cmd"], re.I):
        return "OK-NONAI"      # bash/crush/vehicle/falling/aagun: not what a player fires
    if r["side"] == "hostile":
        if r["undo"] == "-":
            return "BUG-NO-UNDO" if r["passive"] else "BUG-FIGHTS-INVULN"
        return "REVIEW-UNDONE"   # lifted somewhere, but is that path reachable in coop? judge by hand
    return "REVIEW"


# (map, fn) pairs of the "other mechanisms" list that were read and are fine
EXTRA_OK = {
    ("m1l1", "killtruck"): "dying truck driver, scripted",
    ("m2l3", "sequence2"): "germansoldier1 is AI-off (m2l3.scr:263) and goes solid in sequence3",
    ("t1l3", "balcony_death_nazi_deathcheck"): "10000 hp until the first hit, then the scripted balcony fall",
    ("e1l3", "spawncourtyardguy"): "BY-DESIGN: e1l3 stealth gauntlet, 10000 hp + nodamage until the cover is blown (players then drop to 1 hp)",
    ("e2l3", "createinvisibletarget"): "hidden notsolid decoy target for AI fire",
}


def extra_mechanisms(m, census):
    """immune (handled above), health >= 1000 on a hostile, notsolid on a hostile with no later solid."""
    out = []
    files = map_files(m)
    allfns = []
    for p in files:
        for fn in load_script(p):
            allfns.append((p, fn))
    ctx = Ctx(m, census, allfns)
    for p, fn in allfns:
        solid_after = {}
        for ln, t in fn.lines:
            for mm in CMD_RE.finditer(t):
                if mm.group("cmd") == "solid":
                    solid_after[norm_subj(mm.group("subj"))] = ln
        for ln, t in fn.lines:
            hits = [(m2.group("subj") or m2.group("subj2"), int(m2.group("n") or m2.group("n2"))) for m2 in HEALTH_RE.finditer(t)]
            hits += [(m3.group(1), int(m3.group(2))) for m3 in HEALTH_CMD_RE.finditer(t)]     # `X health 10000` command form
            for subj, n in hits:
                if n < 1000 or subj is None:
                    continue
                side, how = resolve(subj, fn, p, None, ctx)
                if re.search(r"local\.(target|tank|destroyed\w*)$|level\.(pillar|ramsey|harrison|tomlin)\w*$|^self$", subj, re.I):
                    side = "nonai"      # dummy aim targets, tanks, pillars, allied leads, self-thinkers of vehicles/friendlies
                if side in ("hostile", "unknown"):
                    out.append({"map": m, "kind": "health>=1000", "file": rel(p), "line": ln, "fn": fn.name, "subj": subj, "detail": str(n), "side": side})
            for mm in CMD_RE.finditer(t):
                if mm.group("cmd") == "notsolid":
                    subj = mm.group("subj")
                    side, how = resolve(subj, fn, p, None, ctx)
                    # a notsolid body that is ALSO switched off / hidden / scripted is scenery; the hazard is a
                    # notsolid enemy whose AI is live (bullets pass through him, he keeps shooting)
                    passive_here = any(norm_subj(m3.group("subj")) == norm_subj(subj) and PASSIVE_RE.search(m3.group("cmd"))
                                       for _, t3 in fn.lines for m3 in CMD_RE.finditer(t3) if m3.group("cmd") != "notsolid")
                    if side == "hostile" and norm_subj(subj) not in solid_after and not passive_here:
                        out.append({"map": m, "kind": "notsolid-hostile", "file": rel(p), "line": ln, "fn": fn.name, "subj": subj, "detail": "no solid in fn", "side": side})
    return [e for e in out if (e["map"], e["fn"]) not in EXTRA_OK]


def scan_coop_framework():
    """coop_mod/*.scr: nodamage on anything that is not the player."""
    rows = []
    for p in sorted(glob.glob(os.path.join(MOD, "coop_mod", "*.scr"))):
        for fn in load_script(p):
            for ln, t in fn.lines:
                for mm in SITE_RE.finditer(t):
                    if mm.group("cmd") == "takedamage":
                        continue
                    rows.append({"file": "coop_mod/" + os.path.basename(p), "line": ln, "fn": fn.name, "subj": mm.group("subj"), "cmd": mm.group("cmd")})
    return rows


def run(args):
    census = load_census()
    maps = [args.map.lower()] if args.map else coop_maps() + ["global"]
    allrows = []
    extras = []
    for m in maps:
        if not census.get(m):
            print("WARN: no BSP census for %s (run --dump-bsp)" % m, file=sys.stderr)
        for r in scan_map(m, census):
            r["verdict"] = verdict(r)
            allrows.append(r)
        extras += extra_mechanisms(m, census)
    return allrows, extras


def fmt_md(rows):
    lines = ["| game | map | where | subject | cmd | side (how) | undo | passive | verdict |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| %s | %s | %s:%d `%s` | `%s` | %s | %s (%s) | %s | %s | **%s** |" % (
            r["game"], r["map"], r["file"], r["line"], r["fn"], r["subj"], r["cmd"], r["side"], r["how"], r["undo"], r["passive"] or "-", r["verdict"]))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--map")
    ap.add_argument("--mod", help="mod tree to scan instead of hzm-mohaa-coop-mod (e.g. a patched overlay)")
    ap.add_argument("--tsv")
    ap.add_argument("--json")
    ap.add_argument("--dump-bsp", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.mod:
        global MOD
        MOD = os.path.abspath(a.mod)
    if a.dump_bsp:
        dump_bsp()
        return 0
    if a.selftest:
        return selftest()
    rows, extras = run(a)
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    bad = [r for r in rows if r["verdict"].startswith("BUG") or r["verdict"] == "REVIEW"]
    show = rows if a.md else bad + [r for r in rows if r["verdict"] in ("OK-UNDONE", "OK-REVIEWED") and r["side"] != "friendly"]
    if show:
        print(fmt_md(show))
    print()
    print("sites: %d  %s" % (len(rows), "  ".join("%s=%d" % kv for kv in sorted(counts.items()))))
    if extras:
        print("other mechanisms on hostile/unknown targets:")
        for e in extras:
            print("  %s %s:%d %s %s %s (%s)" % (e["map"], e["file"], e["line"], e["fn"], e["subj"], e["kind"], e["detail"]))
    fw = scan_coop_framework()
    print("coop_mod framework nodamage sites (review: must be players/allies only):")
    for r in fw:
        print("  %s:%d %s  %s %s" % (r["file"], r["line"], r["fn"], r["subj"], r["cmd"]))
    if a.tsv:
        with open(a.tsv, "w") as f:
            for r in rows:
                f.write("\t".join(str(r[k]) for k in ("game", "map", "file", "line", "fn", "subj", "cmd", "side", "how", "undo", "passive", "verdict")) + "\n")
    if a.json:
        json.dump({"rows": rows, "extras": extras}, open(a.json, "w"), indent=1)
    print("RESULT: %s" % ("FAIL - %d site(s) need a fix or a REVIEWED entry" % len(bad) if bad else "PASS"))
    return 1 if bad else 0


SELFTEST_SCR = """main:{
	waitthread coop_mod/main.scr::main
	$foe_undone nodamage
	$foe_stuck nodamage
	$friend nodamage
	$foe_undone takedamage
	local.grunt = spawn human/German_afrika_private.tik
	local.grunt nodamage
	local.grunt exec global/disable_ai.scr
	if( level.gametype == 0 ){ $foe_sponly nodamage }
	$foe_hp health 10000
}end
"""


def selftest():
    """Plants the four shapes the audit exists for in a scratch mod tree and checks each verdict, so the scanner
    can be shown to FAIL (a check that cannot fail is worse than none, TRAPS T14)."""
    import shutil
    import tempfile
    global MOD
    old_mod = MOD
    tmp = tempfile.mkdtemp(prefix="ivaudit_")
    try:
        os.makedirs(os.path.join(tmp, "maps"))
        os.makedirs(os.path.join(tmp, "global"))
        os.makedirs(os.path.join(tmp, "coop_mod"))
        open(os.path.join(tmp, "maps", "fake.scr"), "w").write(SELFTEST_SCR)
        MOD = tmp
        census = {"fake": {
            "foe_undone": {"kind": "actor", "side": "hostile", "class": "ai_german_x", "model": "human/german_afrika_private.tik"},
            "foe_stuck": {"kind": "actor", "side": "hostile", "class": "ai_german_x", "model": "human/german_afrika_private.tik"},
            "foe_sponly": {"kind": "actor", "side": "hostile", "class": "ai_german_x", "model": "human/german_afrika_private.tik"},
            "foe_hp": {"kind": "actor", "side": "hostile", "class": "ai_german_x", "model": "human/german_afrika_private.tik"},
            "friend": {"kind": "actor", "side": "friendly", "class": "ai_allied_x", "model": "human/allied_oss_man_m1.tik"},
        }}
        rows = scan_map("fake", census)
        got = {}
        for r in rows:
            r["verdict"] = verdict(r)
            got[(r["subj"], r["line"])] = r["verdict"]
        want = {
            ("$foe_undone", 3): "REVIEW-UNDONE",     # hostile, lifted later: still needs a human
            ("$foe_stuck", 4): "BUG-FIGHTS-INVULN",   # hostile, live AI, nothing lifts it
            ("$friend", 5): "OK-FRIENDLY",
            ("local.grunt", 8): "BUG-NO-UNDO",        # hostile, AI off, nothing lifts it
        }
        ok = True
        for k, v in want.items():
            if got.get(k) != v:
                print("selftest FAIL: %s expected %s got %s" % (k, v, got.get(k)))
                ok = False
        if any(k[0] == "$foe_sponly" for k in got):
            print("selftest FAIL: the level.gametype == 0 guarded site was reported")
            ok = False
        ex = extra_mechanisms("fake", census)
        if not any(e["kind"] == "health>=1000" for e in ex):
            print("selftest FAIL: `health 10000` command form not reported")
            ok = False
        print("selftest", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        MOD = old_mod
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
