# Daily Orders pool v2 (2026-11-03, after user feedback "too easy / not creative / centre on our features").
# Writes daily_challenges.json + daily_challenges.md beside this folder and proves a 364-day schedule.
# Read-only against the mod: it parses existing chal_def titles so no order reuses a Service Record title.
import json, random, os, re, glob
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\coop_mod"
XP = {"Easy": 400, "Medium": 750, "Hard": 1250}
BONUS = 1500

# NEW hook points. Each is ONE line (or a small var) in an existing file; daily.scr does the logic.
NEW = {
 "N1":  ("script", "challenges.scr::chal_ai_killed - one line passing victim, killer and wid to daily.scr::daily_onKill (distance, weather, victim faction, killer downed, per-life and per-map tallies, multikill window)"),
 "N2":  ("script", "ammobox.scr ~:254 (the owner-found branch) - one line passing box owner + the resupplied player to daily.scr::daily_onResupply; 'under fire' reuses xp.scr::xp_revive_underfire's test (2+ Germans within 700 u)"),
 "N3":  ("script", "dbno.scr ~:1054 (beside chal_revive / chal_revive_target) - one line passing reviver + downed + the downed man's bleed clock (flags coop_dbno_elapsed / coop_dbno_timer_actual) to daily.scr::daily_onRevive"),
 "N4":  ("script", "medkit.scr::dbno_selfrevive success point - one line to daily.scr::daily_onSelfRevive"),
 "N5":  ("script", "dbno.scr::dbno_enter + player.scr death path - one line each to daily.scr::daily_onDown (ends the current 'life' for per-life tallies)"),
 "N6":  ("script", "challenges.scr::chal_officer_killed - one line passing officer + killer (fact.location / meansofdeath already there) to daily.scr; plus level.coop_officerWavesCalled++ in officer.scr::coop_officer_reinforcements"),
 "N7":  ("script", "challenges.scr::chal_mission_complete - one line to daily.scr::daily_onMission (map prefix/list, skill, coop_hardcore, coop_lmsLives, $player.size, coop_wentDownMap, level.coop_chalAlarmEver, level.coop_chal_radioPaid, the existing coop_chalL_usedNonPistol / usedNonBolt flags and a new usedNonAxis flag set by N1)"),
 "N8":  ("engine", "player.cpp grenade kick (coop_grenadeKick block, ~:20533): count kicks on the player (script var coop_nadeKicks) and stamp the kicked projectile with its kicker so the kill path can credit 'killed by a kicked grenade'"),
 "N9":  ("engine", "gun bracing: expose the brace envelope (0..1) and the carried-MG heat/overheated latch (STAT_MGHEAT) as player vars read by N1"),
 "N10": ("engine", "Player::EnterTurret / ExitTurret: expose the mounted TurretGun on the player (var coop_onTurret) so N1 can credit mounted-MG kills"),
 "N11": ("script", "alarm.scr::alm_deactivate (has the player) - one line; alarmsnipers.scr spawn - tag the actor coop_asn = 1"),
 "N12": ("script", "surrender.scr::convert local.actor local.player - one line"),
 "N13": ("script", "emotes.scr::emote_play - one line (Tab-wheel emotes ship in v1.10.62)"),
 "N14": ("script", "weaponstate.scr RAISE_WEAPON (already sets flags coop_activeWeapon) - also stamp level.time so N1 can see a kill within 2 s of a draw"),
}

# (id, title, description, target, mode, hook, category, tags[, family])
# tags: squad = needs 2+ players | dbno = needs coop_dbno 1 | theatre = only some maps progress it
E = [
 ("e_ammo8", "Ammo Run", "Squadmates draw 8 resupplies from ammo boxes you placed", 8, "Coop", "chal:ammoboxuse", "Ammo crate", ["squad"]),
 ("e_sandbag4", "Sandbag Detail", "Squadmates fight from sandbags you deployed 4 times", 4, "Coop", "xp:Cover Used", "Ammo crate", ["squad"]),
 ("e_revive4", "Stretcher Bearer", "Revive 4 downed teammates", 4, "Any", "chal:revive + mp:revive", "Revives", ["squad"]),
 ("e_allyrevive3", "Leave No One Behind", "Revive 3 downed allied soldiers", 3, "Coop", "chal:allyrevive", "Revives", []),
 ("e_patch5", "Field Dressing", "Heal squadmates 5 times with your medkit", 5, "Coop", "xp:Patched a Squadmate", "Revives", ["squad"]),
 ("e_fieldoff6", "Shoulder Boards", "Kill 6 German field officers", 6, "Coop", "chal:fac_officer", "Officers", []),
 ("e_bodyguard4", "Through the Escort", "Kill 4 of an officer boss's bodyguards", 4, "Coop", "xp:Bodyguard", "Officers", []),
 ("e_wave2", "Wave Breaker", "Kill the last soldier of 2 reinforcement waves", 2, "Coop", "xp:Wave Broken", "Officers", []),
 ("e_obj6", "Orders Received", "Complete 6 primary objectives", 6, "Coop", "chal:objective (team)", "Objectives", []),
 ("e_sideobj1", "Extra Mile", "Complete a side objective", 1, "Coop", "chal:sideobj (team)", "Objectives", []),
 ("e_missions2", "On the March", "Complete 2 missions", 2, "Coop", "chal:missions (team)", "Objectives", []),
 ("e_cover20", "Keep Your Head Down", "Get 20 kills from wall or low cover", 20, "Coop", "chal:coverkill", "Cover", []),
 ("e_blind6", "Spray and Pray", "Get 6 blind-fire kills from cover", 6, "Coop", "chal:blindfire", "Cover", []),
 ("e_mggunner4", "Silence the Gun", "Kill 4 enemy machine gunners", 4, "Coop", "xp:MG Gunner", "MGs", []),
 ("e_mg30", "Base of Fire", "Get 30 kills with a BAR, MG42, .30 cal or other MG", 30, "Any", "class:mg + mp:mg", "MGs", []),
 ("e_reinf25", "Thin the Ranks", "Kill 25 enemy reinforcements", 25, "Coop", "chal:reinf", "Combat", []),
 ("e_head20", "Between the Eyes", "Get 20 headshots", 20, "Any", "chal:headshot + mp:headshot", "Combat", []),
 ("e_melee4", "Butt Stroke", "Get 4 weapon-bash kills", 4, "Any", "chal:melee + mp:melee", "Combat", []),
 ("e_nade6", "Pineapple Delivery", "Get 6 grenade kills", 6, "Any", "chal:grenade + mp:grenade", "Explosives", []),
 ("e_launcher4", "Backblast Area", "Get 4 kills with the Bazooka, Panzerschreck or PIAT", 4, "Any", "class:launcher + mp:rocketk", "Explosives", []),
 ("e_rifle40", "Rifle Platoon", "Get 40 rifle kills", 40, "Any", "class:rifle + mp:rifle", "Combat", []),
 ("e_smg50", "Room Sweeper", "Get 50 submachine gun kills", 50, "Any", "class:smg + mp:smg", "Combat", []),
 ("e_pistol15", "Sidearm Drill", "Get 15 pistol kills", 15, "Any", "class:pistol + mp:pistol", "Combat", []),
 ("e_axis30", "Battlefield Pickup", "Get 30 kills with Axis weapons taken from the field", 30, "Coop", "class:axis", "Combat", []),
 ("e_longshot8", "Long Range Patrol", "Get 8 kills from more than 50 m", 8, "Coop", "chal:longshot", "Combat", []),
 ("e_pointblank10", "Close Shave", "Get 10 kills from under 3 m", 10, "Coop", "NEW N1 (distance under 128 u)", "Combat", []),
 ("e_streak5x3", "Clean Hands", "Get a 5-kill streak without taking damage, 3 times", 3, "Coop", "xp:Killstreak x5", "Combat", [], "streak"),
 ("e_savior4", "Got Your Back", "Kill 4 enemies who were shooting at a teammate", 4, "Coop", "chal:savior", "Revives", ["squad"]),
 ("e_colonel1", "Top Brass", "Kill a German colonel or station commander", 1, "Coop", "chal:fac_general", "Officers", ["theatre"]),
 ("e_firstblood", "Opening Shot", "Get the first kill of a mission", 1, "Coop", "xp:First Blood", "Combat", []),
 ("e_wallbang4", "Through the Plaster", "Get 4 kills through walls or cover", 4, "Coop", "chal:wallbang", "Combat", []),
 ("e_sniper3", "Spot the Sniper", "Kill 3 enemy snipers", 3, "Coop", "chal:fac_sniper", "Combat", []),
 ("e_call2", "Call It In", "Call in 2 air strikes or paratrooper drops", 2, "Coop", "chal:airstrike + chal:reinforce", "Support", []),
 ("e_searchlight2", "Blackout", "Shoot out 2 enemy searchlights", 2, "Coop", "xp:Searchlight Disabled", "Combat", ["theatre"]),
 ("e_blueprint1", "Paper Chase", "Recover a hidden blueprint", 1, "Coop", "chal:blueprint", "Service Record", []),
 ("e_challenge2", "Earn Your Stripes", "Complete 2 Service Record challenges", 2, "Coop", "xp:Challenge", "Service Record", []),
 ("e_emote5", "Morale Boost", "Use 5 emotes from the Tab wheel during missions", 5, "Coop", "NEW N13", "Squad", []),
 ("e_plant2", "Charges Set", "Plant 2 bombs in Search and Destroy or Demolition", 2, "MP", "mp:plant", "Multiplayer", []),
 ("e_clock4", "Clock In", "Play 4 multiplayer rounds to the end", 4, "MP", "mp:rounds", "Multiplayer", []),
 ("e_capture3", "Take the Ground", "Capture 3 objectives or flags in multiplayer", 3, "MP", "mp:capture", "Multiplayer", []),
]
M = [
 ("m_crateFire", "Under the Gun", "Resupply squadmates 4 times while 2 or more enemies are close", 4, "Coop", "NEW N2 (under fire)", "Ammo crate", ["squad"]),
 ("m_crateSpread", "Spread the Wealth", "Resupply 2 different squadmates from your ammo box in one mission", 2, "Coop", "NEW N2 (distinct receivers per map)", "Ammo crate", ["squad"]),
 ("m_reviveFire", "Corpsman Under Fire", "Revive 3 teammates while enemies are close", 3, "Coop", "xp:Revive Under Fire", "Revives", ["squad"]),
 ("m_reviveSame", "Not on My Watch", "Revive the same squadmate twice in one mission", 1, "Coop", "NEW N3 (per-map reviver/target tally)", "Revives", ["squad"]),
 ("m_reviveLast", "Last Breath", "Revive a squadmate with under 5 seconds of bleed-out left", 1, "Coop", "NEW N3 (bleed clock)", "Revives", ["squad", "dbno"]),
 ("m_payback", "Payback", "Revive a squadmate, then get 3 kills within 15 seconds, twice", 2, "Coop", "NEW N3 + N1 (timestamp)", "Revives", ["squad"]),
 ("m_selfrevive", "Get Up, Soldier", "Revive yourself with a medkit while downed, twice", 2, "Coop", "NEW N4", "DBNO", ["dbno"], "selfrev"),
 ("m_downed3", "Not Dead Yet", "Get 3 kills while downed", 3, "Coop", "chal:downedkill", "DBNO", ["dbno"]),
 ("m_secondwind", "Second Wind", "After being revived, get 5 kills before you go down again, 3 times", 3, "Coop", "NEW N3 + N5 + N1 (per-life tally)", "DBNO", ["dbno"]),
 ("m_hro2", "Brass Hunter", "Kill 2 officer bosses", 2, "Coop", "chal:officer", "Officers", []),
 ("m_healdenied", "Last Drink", "Kill an officer boss before he finishes a heal retreat", 1, "Coop", "xp:Heal Denied", "Officers", []),
 ("m_radio", "Cut the Wire", "Destroy an officer's radio and finish the mission", 1, "Coop", "NEW N7 (level.coop_chal_radioPaid)", "Officers", []),
 ("m_melee10", "Bayonet Drill", "Get 10 weapon-bash kills", 10, "Any", "chal:melee + mp:melee", "Combat", []),
 ("m_alarmoff", "Kill the Siren", "Switch off a live alarm by holding USE on its switch", 1, "Coop", "NEW N11", "Objectives", [], "alarm"),
 ("m_silent", "Silent Running", "Finish a mission that has alarms without the alarm ever sounding", 1, "Coop", "NEW N7 (level.coop_chalAlarmEver + map has alarm switches)", "Objectives", [], "alarm"),
 ("m_nade15", "Grenadier", "Get 15 grenade kills", 15, "Any", "chal:grenade + mp:grenade", "Explosives", []),
 ("m_braced25", "Steady Rest", "Get 25 kills with your weapon braced on cover", 25, "Coop", "NEW N9 + N1", "MGs", [], "braced"),
 ("m_kick5", "Return to Sender", "Kick away 5 live enemy grenades", 5, "Coop", "NEW N8 (kick count)", "Explosives", [], "kick"),
 ("m_nest25", "Nest Gunner", "Get 25 kills on a mounted MG42 or .30 cal", 25, "Coop", "NEW N10 + N1", "MGs", [], "turret"),
 ("m_turngun", "Turn the Gun", "Kill an MG gunner, then get 8 kills on a mounted MG in the same mission", 8, "Coop", "NEW N10 + N1 + xp:MG Gunner", "MGs", [], "turret"),
 ("m_snipers4", "Steeple Sweep", "Headshot 4 enemy snipers, rooftop or alarm snipers included", 4, "Coop", "NEW N1 (headshot + sniper faction)", "Combat", []),
 ("m_multi5", "Two for One", "Kill 2 enemies within 1.5 seconds, 5 times", 5, "Coop", "NEW N1 (multikill window)", "Combat", []),
 ("m_streak10", "Charmed Life", "Get a 10-kill streak without taking damage", 1, "Coop", "xp:Killstreak x10", "Combat", [], "streak"),
 ("m_ironlives", "Iron Lives", "Get 15 kills without going down, 3 times", 3, "Coop", "NEW N5 + N1 (per-life tally)", "DBNO", []),
 ("m_quickdraw", "Quick Draw", "Get 8 pistol kills within 2 seconds of drawing your pistol", 8, "Coop", "NEW N14 + N1", "Combat", []),
 ("m_turncoat", "Turncoat", "Recruit a German who surrendered to you", 1, "Coop", "NEW N12", "Combat", []),
 ("m_halftrack", "Halftrack Hunter", "Destroy an enemy halftrack or tank with a launcher or grenades", 1, "Coop", "xp:Vehicle Destroyed + weapon class at the award", "Vehicles", ["theatre"], "vehicle"),
 ("m_airstrike6", "Danger Close", "Get 6 kills with air strikes you called", 6, "Coop", "xp:Air Strike Kill", "Support", []),
 ("m_barrel2", "Powder Keg", "Kill 2 or more enemies with one exploding barrel, twice", 2, "Coop", "chal:scripted_havoc", "Explosives", ["theatre"]),
 ("m_weather25", "Blind Man's War", "Get 25 kills in rain, snow or a dust storm", 25, "Coop", "NEW N1 (level.coop_weatherTheme)", "Theatres", ["theatre"]),
 ("m_objHard", "Sharp End", "Complete 6 primary objectives on Hard difficulty", 6, "Coop", "chal:objective (team) + skill 2+ read in daily.scr", "Objectives", []),
 ("m_objClean", "Clean Sheet", "Complete 4 primary objectives in a row with nobody in the squad going down", 4, "Coop", "NEW N5 (squad down resets a per-map run) + chal:objective", "Objectives", [], "chal:objective"),
 ("m_uboat", "Silent Service", "Finish a U-boat mission without the alarm sounding", 1, "Coop", "NEW N7 (m2l2* + level.coop_chalAlarmEver)", "Theatres", ["theatre"], "alarm"),
 ("m_bt", "Mediterranean Tour", "Finish a Tunisia, Sicily or Italy mission without going down", 1, "Coop", "NEW N7 (e* map + coop_wentDownMap)", "Theatres", []),
 ("m_sh", "Airborne All the Way", "Finish a Spearhead mission without going down", 1, "Coop", "NEW N7 (t* map + coop_wentDownMap)", "Theatres", []),
 ("m_fullsquad", "Full Squad", "Finish a mission with 4 players in the squad", 1, "Coop", "NEW N7 ($player.size)", "Squad", ["squad"]),
 ("m_riflehead", "Sharpshooter", "Get 15 headshots with a rifle or scoped rifle", 15, "Coop", "NEW N1 (headshot + class)", "Combat", []),
 ("m_push", "Push Through", "Win a Push round on a campaign map", 1, "MP", "mp:win_push", "Multiplayer", []),
 ("m_baseassault", "Base Breaker", "Win a Base Assault round", 1, "MP", "mp:win_baseassault", "Multiplayer", []),
 ("m_sapper", "Sapper", "Plant or defuse 3 bombs in multiplayer", 3, "MP", "mp:plant + mp:defuse", "Multiplayer", []),
]
H = [
 ("h_supplyline", "Supply Line", "Resupply every squadmate (2 or more) from your ammo box in one mission, then finish it", 1, "Coop", "NEW N2 + N7", "Ammo crate", ["squad"]),
 ("h_clutch", "Clutch", "Revive a squadmate while you are the last player standing", 1, "Coop", "NEW N3 (no other player up)", "Revives", ["squad"]),
 ("h_angel", "Angel of Mercy", "Revive 12 downed teammates", 12, "Any", "chal:revive + mp:revive", "Revives", ["squad"]),
 ("h_brink", "Back from the Brink", "Revive yourself with a medkit, then get 5 kills before going down again, twice", 2, "Coop", "NEW N4 + N5 + N1", "DBNO", ["dbno"], "selfrev"),
 ("h_laststand", "Last Stand", "Get 2 kills while downed and be revived in the same down, twice", 2, "Coop", "NEW N1 + N3 (kills this down)", "DBNO", ["dbno", "squad"]),
 ("h_firstwave", "Decapitate the Command", "Kill an officer boss before he calls a single reinforcement wave", 1, "Coop", "NEW N6 (level.coop_officerWavesCalled == 0)", "Officers", []),
 ("h_capbadge", "Cap Badge", "Kill an officer boss with a headshot", 1, "Coop", "NEW N6 (fact.location head)", "Officers", []),
 ("h_coldsteel", "Steel for the Colonel", "Kill an officer boss with a weapon bash", 1, "Coop", "NEW N6 (meansofdeath MOD_BASH)", "Officers", []),
 ("h_hardmission", "Hard Charger", "Finish a mission on Hard without going down", 1, "Coop", "NEW N7 (skill 2+ and coop_wentDownMap)", "Objectives", []),
 ("h_hardcore", "Hardcore Veteran", "Finish a mission with the Hardcore host rule on", 1, "Coop", "NEW N7 (coop_hardcore)", "Objectives", []),
 ("h_nostepback", "Hold At All Costs", "Finish a hold or defend mission with nobody going down", 1, "Coop", "NEW N7 (hold-map list + coop_wentDownMap for all)", "Objectives", ["theatre", "squad"]),
 ("h_omaha", "Bloody Omaha", "Finish the Omaha Beach landing without going down", 1, "Coop", "NEW N7 (m3l1a / m3l1b)", "Theatres", ["theatre"]),
 ("h_snowplow", "Snowplow", "Hold the Norway station until the train leaves, without going down", 1, "Coop", "NEW N7 (m2l3)", "Theatres", ["theatre"]),
 ("h_pistolonly", "Sidearm Only", "Finish a mission with kills from pistols only", 1, "Coop", "NEW N7 (existing coop_chalL_usedNonPistol flag)", "Combat", []),
 ("h_axisonly", "Their Own Guns", "Finish a mission with kills from Axis weapons only", 1, "Coop", "NEW N1 + N7 (new coop_chalL_usedNonAxis flag)", "Combat", []),
 ("h_coolbarrel", "Cool Barrel", "Get 20 braced MG kills in one mission without overheating the gun", 20, "Coop", "NEW N9 + N1 (heat latch)", "MGs", [], "braced"),
 ("h_special", "Special Delivery", "Kill 2 enemies with grenades you kicked back", 2, "Coop", "NEW N8 (kicked-projectile credit)", "Explosives", [], "kick"),
 ("h_ackack", "Ack-Ack", "Shoot down 2 enemy aircraft", 2, "Coop", "xp:Plane Shot Down", "Vehicles", ["theatre"]),
 ("h_head60", "Headhunter", "Get 60 headshots", 60, "Any", "chal:headshot + mp:headshot", "Combat", []),
 ("h_band", "Band of Brothers", "Finish a mission with 3 or more players and nobody going down", 1, "Coop", "NEW N7 ($player.size + coop_wentDownMap)", "Squad", ["squad"]),
]

def fam_of(p):
    if p.get("family"):
        return p["family"]
    h = p["hook"]
    return ("new:" + p["id"]) if h.startswith("NEW") else h.split()[0]

pool = []
for tier, lst in (("Easy", E), ("Medium", M), ("Hard", H)):
    for row in lst:
        i, t, d, n, mode, hook, cat, tags = row[:8]
        news = sorted(set(re.findall(r"\bN\d+\b", hook)), key=lambda s: int(s[1:]))
        pool.append(dict(id=i, title=t, description=d, target=n, difficulty=tier, xp=XP[tier], mode=mode, hook=hook,
                         new_hooks=news, category=cat, tags=tags, family=(row[8] if len(row) > 8 else "")))
for p in pool:
    p["family"] = fam_of(p)
assert len(E) == 40 and len(M) == 40 and len(H) == 20, (len(E), len(M), len(H))
assert len({p["id"] for p in pool}) == 100 and len({p["title"] for p in pool}) == 100

# no order reuses an existing Service Record / medal / generated challenge title
existing = set()
for f in glob.glob(os.path.join(MOD, "*.scr")):
    for m in re.finditer(r'chal_def\s+"[^"]*"\s+"[^"]*"\s+"([^"]*)"', open(f, encoding="latin1").read()):
        existing.add(m.group(1).lower())
clash = [p["title"] for p in pool if p["title"].lower() in existing]
assert not clash, clash
for p in pool:
    s = p["title"] + p["description"]
    assert all(ord(c) < 128 for c in s), s
    for bad in (";", '"', "//", "|", "~", "^"):
        assert bad not in s, (bad, s)
    assert 0 < p["target"] < 1000 and len(p["title"]) <= 24, p
    for n in p["new_hooks"]:
        assert n in NEW, n

def schedule(days, allowed, seed=1944):
    rnd = random.Random(seed)
    tiers = {t: [p for p in pool if p["difficulty"] == t and allowed(p)] for t in ("Easy", "Medium", "Hard")}
    last, out = {}, []
    def ok(c, t, day, picked):
        return (last.get(c["id"], -99) <= day - 14
                and c["id"] not in [x["id"] for x in picked]
                and c["family"] not in [x["family"] for x in picked]
                and not (c["mode"] == "MP" and (t == "Hard" or any(x["mode"] == "MP" for x in picked)))
                and not ("theatre" in c["tags"] and any("theatre" in x["tags"] for x in picked))
                and not ("squad" in c["tags"] and sum("squad" in x["tags"] for x in picked) >= 2)
                and not ("dbno" in c["tags"] and any("dbno" in x["tags"] for x in picked))
                and not (c["category"] == x_cat_full(picked, c["category"])))
    def x_cat_full(picked, cat):
        return cat if sum(x["category"] == cat for x in picked) >= 2 else None
    for day in range(days):
        for attempt in range(200):
            picked = []
            for t in ("Hard", "Medium", "Medium", "Easy", "Easy"):   # most constrained tier first
                c = [p for p in tiers[t] if ok(p, t, day, picked)]
                if not c:
                    break
                if (len(picked) >= 3 or attempt > 50) and not any(x["mode"] in ("Any", "MP") for x in picked):
                    c = [p for p in c if p["mode"] in ("Any", "MP")] or c   # every day has work for a multiplayer player
                # prefer the least recently used, so every order comes round
                c.sort(key=lambda p: (last.get(p["id"], -99), rnd.random()))
                picked.append(c[0] if rnd.random() < 0.7 else rnd.choice(c[:4]))
            if len(picked) == 5 and any(x["mode"] in ("Any", "MP") for x in picked):
                break
        else:
            raise SystemExit("schedule constraints unsatisfiable on day %d" % day)
        picked.sort(key=lambda x: ("Easy", "Medium", "Hard").index(x["difficulty"]))
        for x in picked:
            last[x["id"]] = day
        out.append(picked)
    return out

def check(sched, label):
    for d in sched:
        assert len({x["family"] for x in d}) == 5
        assert [x["difficulty"] for x in d] == ["Easy", "Easy", "Medium", "Medium", "Hard"]
        assert sum(x["mode"] == "MP" for x in d) <= 1 and d[4]["mode"] != "MP"
        assert any(x["mode"] in ("Any", "MP") for x in d)
        assert sum("theatre" in x["tags"] for x in d) <= 1
        assert sum("squad" in x["tags"] for x in d) <= 2 and sum("dbno" in x["tags"] for x in d) <= 1
        assert max(Counter(x["category"] for x in d).values()) <= 2
    for i, d in enumerate(sched):
        for x in d:
            for j in range(max(0, i - 13), i):
                assert x["id"] not in [y["id"] for y in sched[j]], (label, x["id"], i, j)
    print("schedule check PASSED:", label, len(sched), "days")

full = schedule(364, lambda p: True)
check(full, "full pool")
cnt = Counter(x["id"] for d in full for x in d)
assert len(cnt) == 100, len(cnt)
ENGINE = {k for k, v in NEW.items() if v[0] == "engine"}
p1 = lambda p: not (set(p["new_hooks"]) & ENGINE)
phase1 = schedule(364, p1, seed=1945)
check(phase1, "phase 1 (no engine hooks)")
n_existing = sum(1 for p in pool if not p["new_hooks"])
n_phase1 = sum(1 for p in pool if p1(p))

with open(os.path.join(OUT, "daily_challenges.json"), "w", encoding="ascii", newline="\n") as f:
    json.dump(dict(
        schema="hzm.dailyorders.v2",
        reset="10:00 UTC daily; day = floor((unix_time - 36000) / 86400)",
        xp=dict(XP, all_five_bonus=BONUS),
        mix_per_day="2 Easy + 2 Medium + 1 Hard; >=1 order completable in multiplayer; <=1 MP-only and never Hard; <=1 theatre; <=2 squad; <=1 dbno; <=2 per category; one order per stat family; no repeat within 14 days",
        hook_grammar={"chal:<stat>": "existing challenges.scr::chal_bump stat", "class:<c>": "weapon class derived from the existing wpn_<wid> stat inside chal_bump",
                      "xp:<label>": "existing xp.scr::xp_award label", "mp:<stat>": "existing mp_progression.scr::mp_bump stat",
                      "NEW Nn": "a new hook point, see new_hooks"},
        new_hooks={k: dict(kind=v[0], what=v[1]) for k, v in NEW.items()},
        tags={"squad": "needs 2 or more players", "dbno": "needs coop_dbno 1", "theatre": "only some maps can progress it"},
        challenges=pool), f, indent=1)
    f.write("\n")

usage = Counter(n for p in pool for n in p["new_hooks"])
L = ["# Daily Orders - the pool of 100 (v2)", "",
     "Revised after review: harder targets, situational orders, built on the mod's own systems. Generated by `tools/gen_dailies.py` with `daily_challenges.json`.", "",
     "Five a day, **2 Easy + 2 Medium + 1 Hard**, reset **10:00 UTC**. XP: Easy **%d**, Medium **%d**, Hard **%d**, plus **%d** for clearing all five (%d a day at most)."
     % (XP["Easy"], XP["Medium"], XP["Hard"], BONUS, 2 * XP["Easy"] + 2 * XP["Medium"] + XP["Hard"] + BONUS), "",
     "Effort per tier: **Easy** = one or two missions played with the order in mind; **Medium** = a solid session played for it; **Hard** = a mission played a set way, or a demanding streak.", "",
     "Mode: **Any** counts in co-op and multiplayer, **Coop** campaign only, **MP** multiplayer only. Tags: `squad` needs 2+ players, `dbno` needs Down-But-Not-Out on, `theatre` only some maps can progress it.", "",
     "**%d of 100 use hooks that exist today**; %d need one or more of the %d NEW hook points below (%d script hook lines, %d engine)." % (n_existing, 100 - n_existing, len(NEW), sum(v[0] == "script" for v in NEW.values()), sum(v[0] == "engine" for v in NEW.values())), ""]
for tier in ("Easy", "Medium", "Hard"):
    rows = [p for p in pool if p["difficulty"] == tier]
    L += ["## %s - %d XP (%d)" % (tier, XP[tier], len(rows)), "",
          "| # | Title | Order | Target | Mode | Pillar | Hook | Tags |", "|---:|---|---|---:|---|---|---|---|"]
    for k, p in enumerate(rows, 1):
        L.append("| %d | **%s** | %s | %d | %s | %s | %s | %s |" % (k, p["title"], p["description"], p["target"], p["mode"], p["category"],
                 p["hook"].replace("|", "/"), ", ".join(p["tags"])))
    L.append("")
L += ["## NEW hook points", "", "| id | kind | used by | what |", "|---|---|---:|---|"]
for k, (kind, what) in NEW.items():
    L.append("| %s | %s | %d | %s |" % (k, kind, usage[k], what))
L += ["", "Pillars: " + ", ".join("%s %d" % (c, n) for c, n in Counter(p["category"] for p in pool).most_common()), ""]
L += ["## Sample fortnight (full pool, seed 1944)", "", "| Day | Easy | Easy | Medium | Medium | Hard |", "|---:|---|---|---|---|---|"]
for d in range(14):
    L.append("| %d | %s |" % (d, " | ".join("%s (%s)" % (x["title"], x["mode"]) for x in full[d])))
L += ["", "Schedule check passed for the full pool and for phase 1 (the %d orders that need no engine hook). Appearances per year (full pool): min %d, max %d." % (n_phase1, min(cnt.values()), max(cnt.values())), ""]
open(os.path.join(OUT, "daily_challenges.md"), "w", encoding="ascii", newline="\n").write("\n".join(L))
print("ok", len(pool), "existing-hook orders", n_existing, "phase1", n_phase1, "new hooks", len(NEW), dict(usage))
print(Counter(p["mode"] for p in pool), Counter(p["category"] for p in pool))
