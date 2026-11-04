# gen_daily_orders.py - HZM Daily Orders (v1.10.63, user 2026-11-03 "Build daily as approved").
#
# The ONE authority for the daily-order pool and its 364-day schedule. Writes, into the mod tree (HZM_MOD, default the
# base checkout):
#   coop_mod/daily_gen.scr          the pool (id, title, description, target, tier, mode, XP, trigger keys) and the
#                                   schedule (row = day mod 364, 5 pool indices each), plus the weapon-class table
#   textures/hud/coop_dly/o<i>.tga  one baked text strip per order (title, +XP, two description lines, mode tags) -
#                                   titles rotate, so the panel and the Service Record tab show them by SHADER cvar
#   textures/hud/coop_dly/panel.tga the lobby panel background (leather + gold frame, matching the Service Record). The panel
#                                   is drawn with ihuddraw by daily.scr::daily_lobbyDraw (a ui_addhud menu is hidden by the
#                                   lobby's drawhud 0); its layout constants below mirror that label. The Service Record tab
#                                   is docs/tools/gen_service_record.py.
# and, with --docs, re-writes the proposal's daily_challenges.json / .md beside the design.
#
# Design: docs/proposals/daily_challenges_2026-11-03/PROPOSAL.md. Day number = floor((unix - 36000) / 86400), from the
# engine builtin getutcday (coop_mod/daily_clock.scr, isolated per TRAPS T1). Runtime: coop_mod/daily.scr.
#
# PHASE: orders whose hook is an ENGINE export (N8 kick credit, N9 brace + MG heat, N10 turret) stay in the pool but
# out of the schedule until those exports ship (set PHASE = 2 then, and re-run).
import json, random, os, re, glob, sys, zlib
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

PHASE = 1
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.environ.get("HZM_MOD") or r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
DOCS = os.path.join(HERE, "..", "proposals", "daily_challenges_2026-11-03")
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
for f in glob.glob(os.path.join(MOD, "coop_mod", "*.scr")):
    for m in re.finditer(r'chal_def\s+"[^"]*"\s+"[^"]*"\s+"([^"]*)"', open(f, encoding="latin1").read()):
        existing.add(m.group(1).lower())
assert len(existing) > 100, "chal_def titles not found under " + MOD
clash = [p["title"] for p in pool if p["title"].lower() in existing]
assert not clash, clash
for p in pool:
    s = p["title"] + p["description"]
    assert all(ord(c) < 128 for c in s), s
    for bad in (";", '"', "//", "|", "~", "^", "\\"):
        assert bad not in s, (bad, s)
    assert 0 < p["target"] < 1000 and len(p["title"]) <= 24, p
    for n in p["new_hooks"]:
        assert n in NEW, n

# ---- runtime trigger keys (daily.scr::daily_fire), comma-separated (xp labels contain spaces). Orders not listed here are evaluated by id in daily.scr's own hook
# labels (daily_onKill / onRevive / onResupply / onMission ...). s: = a challenges.scr::chal_bump stat, c: = a weapon class
# derived from the wpn_<wid> stat, x: = an xp.scr::xp_award label, m: = an mp_progression.scr::mp_bump stat.
TRIG = {
 "e_ammo8": "s:ammoboxuse", "e_sandbag4": "x:Cover Used", "e_revive4": "s:revive,m:revive", "e_allyrevive3": "s:allyrevive",
 "e_patch5": "x:Patched a Squadmate", "e_fieldoff6": "s:fac_officer", "e_bodyguard4": "x:Bodyguard", "e_wave2": "x:Wave Broken",
 "e_obj6": "s:objective", "e_sideobj1": "s:sideobj", "e_missions2": "s:missions", "e_cover20": "s:coverkill",
 "e_blind6": "s:blindfire", "e_mggunner4": "x:MG Gunner", "e_mg30": "c:mg,m:mg", "e_reinf25": "s:reinf",
 "e_head20": "s:headshot,m:headshot", "e_melee4": "s:melee,m:melee", "e_nade6": "s:grenade,m:grenade",
 "e_launcher4": "c:launcher,m:rocketk", "e_rifle40": "c:rifle,m:rifle", "e_smg50": "c:smg,m:smg",
 "e_pistol15": "c:pistol,m:pistol", "e_axis30": "c:axis", "e_longshot8": "s:longshot", "e_streak5x3": "x:Killstreak x5",
 "e_savior4": "s:savior", "e_colonel1": "s:fac_general", "e_firstblood": "x:First Blood", "e_wallbang4": "s:wallbang",
 "e_sniper3": "s:fac_sniper", "e_call2": "s:airstrike,s:reinforce", "e_searchlight2": "x:Searchlight Disabled",
 "e_blueprint1": "s:blueprint", "e_challenge2": "x:Challenge", "e_plant2": "m:plant", "e_clock4": "m:rounds",
 "e_capture3": "m:capture",
 "m_reviveFire": "x:Revive Under Fire", "m_downed3": "s:downedkill", "m_hro2": "s:officer", "m_healdenied": "x:Heal Denied",
 "m_melee10": "s:melee,m:melee", "m_nade15": "s:grenade,m:grenade", "m_streak10": "x:Killstreak x10",
 "m_halftrack": "x:Vehicle Destroyed", "m_airstrike6": "x:Air Strike Kill", "m_barrel2": "s:scripted_havoc",
 "m_objHard": "s:objective", "m_push": "m:win_push", "m_baseassault": "m:win_baseassault", "m_sapper": "m:plant,m:defuse",
 "h_angel": "s:revive,m:revive", "h_ackack": "x:Plane Shot Down", "h_head60": "s:headshot,m:headshot",
}
COND = {"m_objHard": "hard", "m_halftrack": "atweapon"}
for k in TRIG:
    assert k in {p["id"] for p in pool}, k
for k, v in TRIG.items():
    for key in v.split(","):
        assert key[:2] in ("s:", "c:", "x:", "m:") and len(key) > 2, (k, key)
# every order with no NEW hook must be fully described by TRIG (its funnel exists today)
for p in pool:
    if not p["new_hooks"]:
        assert p["id"] in TRIG, ("no trigger for existing-hook order", p["id"])
# x: labels must exist verbatim in the mod (a typo would silently never fire)
_src = "".join(open(f, encoding="latin1").read() for f in glob.glob(os.path.join(MOD, "coop_mod", "*.scr")))
for k, v in TRIG.items():
    for key in v.split(","):
        if key.startswith("x:"):
            lab = key[2:]
            if lab.startswith("Killstreak x"):
                assert '"Killstreak x"' in _src, lab
            else:
                assert '"' + lab + '"' in _src, ("xp label not found in coop_mod", lab)

# ---- weapon classes, keyed on challenges.scr::chal_widFromModel's wids
WCLASS = {
 "rifle": "garand kar98 g43 enfield mosin svt carcano arisaka johnson stg44",
 "smg": "thompson greasegun mp40 sten ppsh type100 moschetto",
 "sniper": "springfield kar98sniper g43sniper mosinsniper carcanosniper arisakasniper l42a1 delisle",
 "pistol": "colt silenced p38 luger ppk webley nagantrev tt33 beretta nambu welrod c96 m10",
 "mg": "bar mg42 thirtycal breda dp28 vickers fg42",
 "shotgun": "shotgun",
 "launcher": "bazooka panzerschreck piat",
}
AXIS = ("kar98 kar98sniper g43 g43sniper mp40 stg44 mg42 fg42 p38 luger ppk c96 panzerschreck carcano carcanosniper breda "
        "beretta moschetto arisaka arisakasniper type100 nambu").split()
_wids = set(re.findall(r'local\.wid = "([a-z0-9]+)"', _src))
_cls = {w: c for c, ws in WCLASS.items() for w in ws.split()}
assert _wids and _wids <= set(_cls), ("wid without a class", sorted(_wids - set(_cls)))
assert set(AXIS) <= set(_cls)

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
SHIP = phase1 if PHASE == 1 else full
for p in pool:
    if p1(p) or PHASE >= 2:
        assert p["id"] in TRIG or set(p["new_hooks"]) - ENGINE, p["id"]

# ---------------------------------------------------------------------------------------------- mod outputs
IDX = {p["id"]: i for i, p in enumerate(pool)}
TIER = {"Easy": 0, "Medium": 1, "Hard": 2}
MODE = {"Any": 0, "Coop": 1, "MP": 2}
NL = chr(10)

def q(s):
    assert '"' not in s and "\\" not in s and all(ord(c) < 128 for c in s), s
    return '"' + s + '"'

def write_bytes(path, data):
    full_p = os.path.join(MOD, path)
    os.makedirs(os.path.dirname(full_p), exist_ok=True)
    try:
        if open(full_p, "rb").read() == data:
            return False
    except OSError:
        pass
    open(full_p, "wb").write(data)
    return True

def gen_scr():
    sig = "%08x" % (zlib.crc32(("|".join(p["id"] for p in pool) + "#" + ",".join(
        "".join("%03d" % IDX[x["id"]] for x in d) for d in SHIP)).encode()) & 0xffffffff)
    L = ["//GENERATED by docs/tools/gen_daily_orders.py - Daily Orders pool + schedule. DO NOT EDIT; re-run the generator.",
         "//Read by coop_mod/daily.scr::daily_init once per map. Pool index i: id, title, target, tier (0 Easy 1 Medium 2 Hard),",
         "//mode (0 Any 1 Coop 2 MP), xp, trig (comma-separated keys for daily_fire), cond (extra test by name). Strip: textures/hud/coop_dly/o<i>.",
         "//Schedule: level.coop_dlyRow[day mod %d] = five 3-digit pool indices (Easy Easy Medium Medium Hard). Phase %d." % (len(SHIP), PHASE),
         "main:{",
         "\tif( level.coop_dlyGenLoaded == 1 ){ end }",
         "\tlevel.coop_dlyGenLoaded = 1",
         "\tlevel.coop_dlyGenSig = %s" % q(sig),
         "\tlevel.coop_dlyN = %d" % len(pool),
         "\tlevel.coop_dlyRows = %d" % len(SHIP),
         "\tlevel.coop_dlyBonusXp = %d" % BONUS]
    for i, p in enumerate(pool):
        L.append("\tlevel.coop_dlyId[%d] = %s" % (i, q(p["id"])))
        L.append("\tlevel.coop_dlyTitle[%d] = %s" % (i, q(p["title"])))
        L.append("\tlevel.coop_dlyDesc[%d] = %s" % (i, q(p["description"])))
        L.append("\tlevel.coop_dlyTgt[%d] = %d" % (i, p["target"]))
        L.append("\tlevel.coop_dlyTier[%d] = %d" % (i, TIER[p["difficulty"]]))
        L.append("\tlevel.coop_dlyMode[%d] = %d" % (i, MODE[p["mode"]]))
        L.append("\tlevel.coop_dlyXp[%d] = %d" % (i, p["xp"]))
        L.append("\tlevel.coop_dlyTrig[%d] = %s" % (i, q(TRIG.get(p["id"], ""))))
        L.append("\tlevel.coop_dlyCond[%d] = %s" % (i, q(COND.get(p["id"], ""))))
    for r, d in enumerate(SHIP):
        L.append("\tlevel.coop_dlyRow[%d] = %s" % (r, q("".join("%03d" % IDX[x["id"]] for x in d))))
    for c, ws in WCLASS.items():
        for w in ws.split():
            L.append("\tlevel.coop_dlyCls[%s] = %s" % (q(w), q(c)))
    for w in AXIS:
        L.append("\tlevel.coop_dlyAxis[%s] = 1" % q(w))
    L.append("}end")
    txt = NL.join(L) + NL
    assert "-" not in re.sub(r'"[^"]*"', "", txt.split("main:{", 1)[1]).replace("//", ""), "a bare minus in generated code"
    return write_bytes("coop_mod/daily_gen.scr", txt.encode("ascii")), sig

# ---- baked text strips: one per order, 1024x128 (8:1), transparent, drawn over the panel / SR tab
FONT_DIR = "C:/Windows/Fonts/"
def font(name, sz):
    return ImageFont.truetype(FONT_DIR + name, sz)
TITLE_C = (0xE8, 0xE0, 0xCA, 255)
DESC_C = (0xC0, 0xB0, 0x92, 255)
XP_C = (0xE6, 0xBE, 0x58, 255)
TAG_C = {"MULTIPLAYER": (0x9c, 0xc4, 0xe8, 255), "SQUAD": (0xd8, 0xa0, 0x78, 255), "DBNO ON": (0xd8, 0x84, 0x84, 255),
         "SOME MAPS": (0xb8, 0xc0, 0x90, 255)}

def wrap(d, text, f, w1, w2):
    words = text.split()
    lines, cur, lim = [], "", w1
    for wd in words:
        trial = (cur + " " + wd).strip()
        if d.textlength(trial, font=f) > lim and cur:
            lines.append(cur)
            cur, lim = wd, w2
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines

def strip_img(p):
    im = Image.new("RGBA", (1024, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ft, fx, fg, fd = font("verdanab.ttf", 38), font("verdanab.ttf", 30), font("verdanab.ttf", 19), font("verdana.ttf", 28)
    d.text((6, 0), p["title"], font=ft, fill=TITLE_C)
    xs = "+%d XP" % p["xp"]
    d.text((1018 - d.textlength(xs, font=fx), 5), xs, font=fx, fill=XP_C)
    tags = []
    if p["mode"] == "MP":
        tags.append("MULTIPLAYER")
    if "squad" in p["tags"]:
        tags.append("SQUAD")
    if "dbno" in p["tags"]:
        tags.append("DBNO ON")
    if "theatre" in p["tags"]:
        tags.append("SOME MAPS")
    tx = 1018
    for t in reversed(tags):
        tw = d.textlength(t, font=fg)
        tx -= tw
        d.text((tx, 48), t, font=fg, fill=TAG_C[t])
        tx -= 18
    w1 = (tx - 14) if tags else 1012
    for sz in (28, 26, 24):
        fd = font("verdana.ttf", sz)
        lines = wrap(d, p["description"], fd, w1, 1012)
        if len(lines) <= 2:
            break
    assert len(lines) <= 2, ("description does not fit two lines", p["id"], lines)
    assert d.textlength(p["title"], font=ft) + d.textlength(xs, font=fx) + 24 < 1012, ("title too long", p["id"])
    for j, ln in enumerate(lines):
        d.text((8, 48 + j * 38), ln, font=fd, fill=DESC_C)
    return im

def save_tga(im, rel):
    import io
    b = io.BytesIO()
    im.save(b, "TGA", compression="tga_rle")
    return write_bytes(rel, b.getvalue())

# ---- the lobby panel: 244 x 244 units, 1024 x 1024 px (uniform 4.2 px/unit); rows as daily.scr::daily_lobbyDraw draws them
PW = 244
ROW0, ROWH = 24, 38
BONUS_Y = ROW0 + 5 * ROWH    # 214
S = 1024.0 / PW

def panel_img():
    im = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # leather, darker at the bottom, with the Service Record's gold double frame
    for y in range(1024):
        t = y / 1023.0
        c = (int(0x2c - 0x10 * t), int(0x20 - 0x0b * t), int(0x14 - 0x07 * t), 246)
        d.line([(0, y), (1023, y)], fill=c)
    gold, gold2 = (0xC8, 0xA0, 0x50, 255), (0x7a, 0x5c, 0x28, 255)
    d.rectangle([2, 2, 1021, 1021], outline=gold, width=5)
    d.rectangle([13, 13, 1010, 1010], outline=gold2, width=2)
    fh = font("georgiab.ttf", 46)
    d.text((30, 18), "DAILY ORDERS", font=fh, fill=(0xE6, 0xC0, 0x62, 255))
    y = int(ROW0 * S) - 10
    d.line([(26, y), (998, y)], fill=gold2, width=3)
    y = int(BONUS_Y * S) - 6
    d.line([(26, y), (998, y)], fill=gold2, width=3)
    # the bar tracks (the coop_bf<n> fills are drawn over them; bf0 is empty): daily.scr draws the fill at x 12, w 160, h 6
    for k in range(5):
        ty = (ROW0 + k * ROWH + 29) * S
        d.rectangle([int(12 * S) - 2, int(ty) - 2, int(172 * S) + 2, int(ty + 6 * S) + 2], fill=(0x0e, 0x0a, 0x06, 255), outline=gold2, width=2)
    fb, fx, fs = font("verdanab.ttf", 34), font("verdanab.ttf", 30), font("verdana.ttf", 26)
    by = int(BONUS_Y * S)
    d.text((int(11.5 * S), by + 2), "Mentioned in Dispatches", font=fb, fill=TITLE_C)
    xs = "+%d XP" % BONUS
    d.text((998 - d.textlength(xs, font=fx), by + 6), xs, font=fx, fill=XP_C)
    d.text((int(11.5 * S), by + 46), "Clear every order you can do today", font=fs, fill=DESC_C)
    return im

def write_docs():
    with open(os.path.join(DOCS, "daily_challenges.json"), "w", encoding="ascii", newline="\n") as f:
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

def day_of(unix):
    return (unix - 36000) // 86400

if __name__ == "__main__":
    if "--day" in sys.argv:
        dd = int(sys.argv[sys.argv.index("--day") + 1])
        r = dd % len(SHIP)
        print("day", dd, "row", r, "ids", ",".join(x["id"] for x in SHIP[r]))
        sys.exit(0)
    if "--docs" in sys.argv:
        write_docs()
    ch, sig = gen_scr()
    nimg = 0
    for i, p in enumerate(pool):
        nimg += save_tga(strip_img(p), "textures/hud/coop_dly/o%d.tga" % i)
    nimg += save_tga(panel_img(), "textures/hud/coop_dly/panel.tga")
    import time
    today = day_of(int(time.time()))
    print("daily_gen.scr %s (sig %s), %d strip/panel images rewritten" % ("written" if ch else "unchanged", sig, nimg))
    print("phase %d: %d of 100 orders schedulable; today = day %d, row %d: %s" % (
        PHASE, n_phase1 if PHASE == 1 else 100, today, today % len(SHIP), ", ".join(x["id"] for x in SHIP[today % len(SHIP)])))
