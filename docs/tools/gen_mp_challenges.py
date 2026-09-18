#!/usr/bin/env python
"""Generate coop_mod/mp_challenges.scr - the MULTIPLAYER challenge table + unlock-derivation, an isolated
MP-owned mirror of the coop challenge system (coop_mod/challenges.scr). Challenges watch the persisted MP
STAT VECTOR (coop_mod/mp_progression.scr: total + 8 class-kill counts + coop_mpStat[]), and when a stat
reaches a challenge's target the challenge's REWARD token is added to the player's derived unlock set
(self.flags["coop_mpUnlocks"], a pipe store). The loadout/cosmetics enforce commits against that store, and
the Service Record shows each challenge's progress + reward.

WHY GENERATED
    Every visible MP artifact is generated (gen_mp_armory.py convention). The weapon-unlock challenges are
    a MECHANICAL ladder over the armory roster (docs/tools/mp_armory_roster.tsv): within each class the
    non-starter weapons get tiers 2..N, and a per-class kill count unlocks each tier for BOTH sides at once.
    The feat / objective / mode / milestone / cosmetic challenges are the AUTHORED spec below. The output
    also precomputes each reward's client unlock cvar so the runtime GSC needs no string parsing and
    gen_mp_armory can gate a tile on the same cvar (coop_mpUw_<class>_<tier>).

    python docs/tools/gen_mp_challenges.py check   # regenerate in memory + byte-compare (exit 1 = drift)
    python docs/tools/gen_mp_challenges.py build   # write the file

ISOLATION
    Output is coop_mod/mp_challenges.scr - an MP file (coop_mod/mp*.scr is in MP_MANIFEST), coop_mpRun-
    guarded, naming only coop_mp* tokens + calling only mp_progression.scr (MP->MP, clause 10). ASCII, LF.
"""
import csv
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
ROSTER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mp_armory_roster.tsv")
OUT = os.path.join(MOD, "coop_mod", "mp_challenges.scr")

# Must match mp_progression.scr: the 8 class-kill stats + "total" + the coop_mpStat[] vector.
CLASS_STATS = ["rifle", "sniper", "smg", "mg", "shotgun", "rocket", "pistol", "nades"]
EXTRA_STATS = [
    "headshot", "melee", "grenade", "rocketk", "capture", "plant", "defuse", "destroy",
    "revive", "flagret", "propsurv", "propfind", "ggwin", "rounds",
    "win_gungame", "win_koth", "win_snd", "win_lms", "win_freezetag", "win_push",
    "win_ctf", "win_demolition", "win_baseassault", "win_buildabase", "win_prophunt",
]
VALID_STATS = set(CLASS_STATS) | {"total"} | set(EXTRA_STATS)

FINISHES = ["gold", "chrome", "blued", "bloody", "camo_woodland", "camo_winter", "camo_desert"]
# class -> Service Record category (tab)
CLASS_CAT = {"rifle": "rifles", "sniper": "marksman", "smg": "smgs", "pistol": "sidearms",
             "mg": "support", "shotgun": "support", "rocket": "support", "nades": "support"}
# per-tier kill thresholds for the weapon ladder (tier 2 = the 2nd weapon in a class, etc.)
TIER_KILLS = {2: 15, 3: 30, 4: 50, 5: 75, 6: 105, 7: 140, 8: 180, 9: 225}


def esc(s):
    return s.replace('"', "'")


def load_roster():
    lines = [l for l in io.open(ROSTER, encoding="utf-8") if not l.startswith("#") and l.strip()]
    rows = list(csv.DictReader(lines, delimiter="\t"))
    # per side, per class-tab: ordered mpids; starter first (tier 1)
    byclass = {}
    for r in rows:
        cls = r["tab"].strip().lower()
        byclass.setdefault(cls, {"a": [], "x": []})
        byclass[cls][r["side"]].append((r["mpid"], r.get("starter", "0") == "1", r["name"]))
    return byclass


def reward_cvar(reward):
    """Client unlock cvar for a reward token (matches gen_mp_armory's tile gate). "" -> ""."""
    if not reward:
        return ""
    parts = reward.split(":")
    kind = parts[0]
    if kind == "wt":       # wt:<class>:<tier>
        return "coop_mpUw_%s_%s" % (parts[1], parts[2])
    if kind == "fin":      # fin:<finish>
        return "coop_mpUfin_%s" % parts[1]
    if kind == "sk":       # sk:<side>:<id>
        return "coop_mpUsk_%s%s" % (parts[1], parts[2])
    if kind == "hl":       # hl:<id>
        return "coop_mpUhl_%s" % parts[1]
    if kind == "gl":       # gl:<id>
        return "coop_mpUgl_%s" % parts[1]
    raise SystemExit("gen_mp_challenges: unknown reward kind %r" % reward)


# [user 2026-09-17] SHARED RANK: coop and MP feed one rank ladder, so a weapon-tier reward is ALSO unlocked
# once the player's coop rank is high enough. tier T unlocks at coop rank WT_RANK_STEP*(T-1) (tier 2 @ r2,
# tier 8 @ r14). ONLY weapon tiers follow rank; cosmetics/finishes stay challenge-only (return -1).
WT_RANK_STEP = 2

def reward_wt_rank(reward):
    """Coop rank that also unlocks a 'wt:<class>:<tier>' reward, or -1 for a non-weapon reward."""
    if not reward or not reward.startswith("wt:"):
        return -1
    parts = reward.split(":")
    if len(parts) != 3:
        return -1
    try:
        tier = int(parts[2])
    except ValueError:
        return -1
    if tier < 2:
        return -1
    return WT_RANK_STEP * (tier - 1)


def reward_name(reward):
    """[user 2026-09-17] Human-readable name of a reward token, for the MP challenge-complete toast (shown
    like coop's 'Unlocked: X'). '' when there is no item reward."""
    if not reward:
        return ""
    parts = reward.split(":")
    kind = parts[0]
    if kind == "wt" and len(parts) == 3:
        return "%s Tier %s weapon" % (parts[1].capitalize(), parts[2])
    if kind == "fin":
        return "%s weapon finish" % parts[1].upper()
    if kind == "sk":
        return "a uniform skin"
    if kind == "hl":
        return "a helmet"
    if kind == "gl":
        return "gloves"
    return ""


def weapon_challenges(byclass):
    """The mechanical ladder: one challenge per class per tier>=2, unlocking that tier on both sides."""
    out = []
    for cls in CLASS_STATS:
        info = byclass.get(cls)
        if not info:
            continue
        # order weapons by roster order, starter is tier 1; count max tiers across both sides
        maxn = max(len(info["a"]), len(info["x"]))
        for tier in range(2, maxn + 1):
            k = TIER_KILLS.get(tier, 225 + (tier - 9) * 60)
            # the weapon name at this tier (prefer allied for the label)
            nm = ""
            for side in ("a", "x"):
                if tier - 1 < len(info[side]):
                    nm = info[side][tier - 1][2]
                    break
            cat = CLASS_CAT[cls]
            cid = "wt_%s_%d" % (cls, tier)
            title = "%s Mastery %d" % (cls.capitalize(), tier)
            desc = "Get %d %s kills to unlock the next %s (%s)" % (k, cls, cls, esc(nm))
            out.append((cid, cat, title, desc, cls, k, "wt:%s:%d" % (cls, tier)))
    return out


# --- authored non-weapon challenges: (id, cat, title, desc, stat, target, reward) ---
def authored():
    A = []
    # FEATS -> finishes + cosmetics
    A += [
        ("feat_hs1", "feats", "Marksman's Eye", "Get 25 headshot kills", "headshot", 25, "sk:a:03"),
        ("feat_hs2", "feats", "Deadeye", "Get 75 headshot kills to unlock the BLUED finish", "headshot", 75, "fin:blued"),
        ("feat_hs3", "feats", "Sharpshooter", "Get 150 headshot kills", "headshot", 150, "hl:03"),
        ("feat_hs4", "feats", "Cranial", "Get 300 headshot kills to unlock the GOLD finish", "headshot", 300, "fin:gold"),
        ("feat_ml1", "feats", "Cold Steel", "Get 15 melee kills", "melee", 15, "gl:1"),
        ("feat_ml2", "feats", "Red Right Hand", "Get 50 melee kills to unlock the BLOODY finish", "melee", 50, "fin:bloody"),
        ("feat_ml3", "feats", "Trench Fighter", "Get 120 melee kills", "melee", 120, "hl:04"),
        ("feat_gr1", "feats", "Frag Out", "Get 20 grenade kills", "grenade", 20, "sk:x:03"),
        ("feat_gr2", "feats", "Shrapnel", "Get 60 grenade kills", "grenade", 60, "hl:05"),
        ("feat_rk1", "feats", "Tank Buster", "Get 15 rocket kills", "rocketk", 15, "sk:a:04"),
        ("feat_rk2", "feats", "Demolisher", "Get 40 rocket kills to unlock the CHROME finish", "rocketk", 40, "fin:chrome"),
    ]
    # OBJECTIVES -> cosmetics + camo finishes
    A += [
        ("obj_cap1", "objectives", "Ground Taker", "Capture 15 objective points", "capture", 15, "sk:x:04"),
        ("obj_cap2", "objectives", "Territorial", "Capture 50 objective points", "capture", 50, "hl:06"),
        ("obj_plant1", "objectives", "Sapper", "Plant 10 charges", "plant", 10, "gl:2"),
        ("obj_plant2", "objectives", "Combat Engineer", "Plant 30 charges to unlock WOODLAND camo", "plant", 30, "fin:camo_woodland"),
        ("obj_defuse1", "objectives", "Wire Cutter", "Defuse 10 charges", "defuse", 10, "sk:a:05"),
        ("obj_destroy1", "objectives", "Wrecker", "Destroy 5 enemy bases/sites", "destroy", 5, "hl:07"),
        ("obj_destroy2", "objectives", "Siege Master", "Destroy 20 bases/sites to unlock DESERT camo", "destroy", 20, "fin:camo_desert"),
        ("obj_revive1", "objectives", "Medic", "Revive 10 downed teammates", "revive", 10, "gl:3"),
        ("obj_revive2", "objectives", "Guardian Angel", "Revive 40 downed teammates", "revive", 40, "hl:08"),
        ("obj_flagret1", "objectives", "Flag Runner", "Return 10 flags", "flagret", 10, "sk:x:05"),
        ("obj_propsurv1", "objectives", "Wallflower", "Survive 5 Prop Hunt rounds as a prop", "propsurv", 5, "sk:a:06"),
        ("obj_propsurv2", "objectives", "Master of Disguise", "Survive 20 Prop Hunt rounds to unlock WINTER camo", "propsurv", 20, "fin:camo_winter"),
        ("obj_propfind1", "objectives", "Prop Hunter", "Find 15 props as a hunter", "propfind", 15, "hl:09"),
        ("obj_ggwin1", "objectives", "Gun Runner", "Finish 3 Gun Game ladders", "ggwin", 3, "sk:x:06"),
        ("obj_ggwin2", "objectives", "Golden Gun", "Finish 10 Gun Game ladders", "ggwin", 10, "hl:10"),
    ]
    # MODE WINS -> cosmetics (one per mode)
    modewins = [
        ("win_gungame", "Gun Slinger", "Gun Game", "sk:a:07"),
        ("win_koth", "Hill King", "King of the Hill", "sk:x:07"),
        ("win_snd", "Bomb Squad", "Search & Destroy", "sk:a:08"),
        ("win_lms", "Sole Survivor", "Last Man Standing", "sk:x:08"),
        ("win_freezetag", "Cold Warrior", "Freeze Tag", "sk:a:09"),
        ("win_push", "Frontline", "Push", "sk:x:09"),
        ("win_ctf", "Flag Bearer", "Capture the Flag", "sk:a:10"),
        ("win_demolition", "Demolition Man", "Demolition", "sk:x:10"),
        ("win_baseassault", "Base Breaker", "Base Assault", "sk:a:11"),
        ("win_buildabase", "Architect", "Build-A-Base", "sk:x:11"),
        ("win_prophunt", "Best in Hide", "Prop Hunt", "sk:a:12"),
    ]
    for stat, title, mode, rw in modewins:
        A.append(("cwin_" + stat, "modes", title, "Win 5 rounds of %s" % mode, stat, 5, rw))
    # second-tier mode wins -> helmets/gloves for variety
    A += [
        ("cwin_koth_e", "modes", "Hill Lord", "Win 20 rounds of King of the Hill", "win_koth", 20, "hl:03"),
        ("cwin_ctf_e", "modes", "Flag Master", "Win 20 rounds of Capture the Flag", "win_ctf", 20, "gl:4"),
        ("cwin_snd_e", "modes", "Demolition Expert", "Win 20 rounds of Search & Destroy", "win_snd", 20, "sk:x:12"),
    ]
    # MILESTONES -> premium cosmetics + finishes
    A += [
        ("ms_kills1", "milestones", "Blooded", "Get 100 total kills", "total", 100, "gl:5"),
        ("ms_kills2", "milestones", "Veteran", "Get 500 total kills", "total", 500, "hl:03"),
        ("ms_kills3", "milestones", "Legend", "Get 1000 total kills to unlock the CHROME finish", "total", 1000, "fin:chrome"),
        ("ms_rounds1", "milestones", "Enlisted", "Finish 25 matches", "rounds", 25, "gl:6"),
        ("ms_rounds2", "milestones", "Career Soldier", "Finish 100 matches", "rounds", 100, "hl:04"),
    ]
    return A


def all_challenges():
    byclass = load_roster()
    ch = weapon_challenges(byclass) + authored()
    # validate
    seen = set()
    for (cid, cat, title, desc, stat, tgt, rw) in ch:
        if cid in seen:
            raise SystemExit("gen_mp_challenges: duplicate id %s" % cid)
        seen.add(cid)
        if stat not in VALID_STATS:
            raise SystemExit("gen_mp_challenges: %s watches unknown stat %r" % (cid, stat))
        if tgt <= 0:
            raise SystemExit("gen_mp_challenges: %s has non-positive target" % cid)
        reward_cvar(rw)  # raises on a malformed token
    return ch


TEMPLATE_FOOTER = r'''

//=========================================================================
// RUNTIME. derive(p) recomputes challenge completion + the unlock set from the player's persisted stats
// (called from mp_progression.scr::applyUnlocks). The pipe store self.flags["coop_mpUnlocks"] is the
// SERVER-authoritative unlock set the loadout/cosmetics check; per-reward client cvars (pushed diff-
// guarded) let the armory tiles un-grey; per-challenge coop_mpChD<i> done cvars drive the Service Record
// badge. Reaching mp_progression.scr is MP->MP (both in MP_MANIFEST, isolation clause 10).
//=========================================================================
derive local.p:{
	if( local.p == NULL ){ end }
	if( level.coop_mpRun != 1 ){ end }
	waitthread mpc_init

	local.store = "|"
	local.pushed = local.p.flags["coop_mpUpushed"]
	if( local.pushed == NIL ){ local.pushed = "|" }

	for( local.i = 0; local.i < level.coop_mpChalN; local.i++ ){
		local.val = waitthread coop_mod/mp_progression.scr::mp_statVal local.p level.coop_mpChalStat[local.i]
		local.tgt = level.coop_mpChalTarget[local.i]
		local.done = 0
		if( local.val >= local.tgt ){ local.done = 1 }

		//per-challenge done cvar for the SR badge (diff-guarded)
		local.dkey = ( "coop_mpChD" + local.i )
		local.pd = local.p.flags[local.dkey]
		if( local.pd == NIL ){ local.pd = 0 }
		if( local.done != local.pd ){
			local.p.flags[local.dkey] = local.done
			local.p stufftext ( "seta " + local.dkey + " " + local.done )
			if( local.done == 1 && local.pd == 0 ){
				waitthread mpc_toast local.p level.coop_mpChalTitle[local.i] level.coop_mpChalRewardName[local.i]
				println( "^~^~^ MPCHAL done e" + local.p.entnum + " id=" + level.coop_mpChalId[local.i] )
			}
		}

		//[user 2026-09-17] SHARED RANK: the weapon UNLOCK (store + armory tile) also fires when the player's
		//coop rank meets the reward's tier (coop_mpChalWtRank[i] >= 0; -1 = a non-weapon reward). Additive -
		//it never revokes a challenge unlock, and the DONE badge above stays stats-only ("challenge done").
		local.unlocked = local.done
		if( local.unlocked == 0 ){
			local.wr = level.coop_mpChalWtRank[local.i]
			if( local.wr != NIL && local.wr >= 0 ){
				local.crank = local.p.flags["coop_xp_rank"]
				if( local.crank == NIL ){ local.crank = 0 }
				if( local.crank >= local.wr ){ local.unlocked = 1 }
			}
		}

		if( local.unlocked == 1 ){
			local.rw = level.coop_mpChalReward[local.i]
			if( local.rw != "" && local.rw != NIL ){
				//dedupe into the store
				if( waitthread storeHas local.store local.rw == 0 ){
					local.store = ( local.store + local.rw + "|" )
				}
				//push the reward's client unlock cvar once (armory tile un-grey)
				local.rc = level.coop_mpChalRCvar[local.i]
				if( local.rc != "" && local.rc != NIL ){
					if( waitthread storeHas local.pushed local.rc == 0 ){
						local.pushed = ( local.pushed + local.rc + "|" )
						local.p stufftext ( "seta " + local.rc + " 1" )
					}
				}
			}
		}
	}

	local.p.flags["coop_mpUnlocks"] = local.store
	local.p.flags["coop_mpUpushed"] = local.pushed
}end


//is "|needle|" present in the pipe store local.hay (which begins and ends with "|")? 1/0 in a local
//before end (bug-2603).
storeHas local.hay local.needle:{
	local.found = 0
	if( local.hay == NIL || local.needle == NIL || local.needle == "" ){ end local.found }
	local.probe = ( "|" + local.needle + "|" )
	if( waitthread coop_mod/mp_progression.scr::containsSub local.hay local.probe == 1 ){ local.found = 1 }
}end local.found


//is a reward token currently unlocked for this player? The loadout/cosmetics call this to gate a commit.
isUnlocked local.p local.token:{
	local.ok = 0
	if( local.p == NULL ){ end local.ok }
	local.store = local.p.flags["coop_mpUnlocks"]
	if( local.store == NIL ){ end local.ok }
	if( waitthread storeHas local.store local.token == 1 ){ local.ok = 1 }
}end local.ok


//[user 2026-09-17] MP challenge-complete TOAST - the SAME on-screen style as coop's CHALLENGE COMPLETE toast
//(challenges.scr::chal_toast_show): "CHALLENGE COMPLETE" + the challenge title + the unlocked item. MP-owned;
//ihuddraw slots 76-78 are free in MP (the coop toast never runs here). Threaded hold+clear so it never blocks
//derive. No coop code called; no coop_mp* naming issue.
mpc_toast local.p local.title local.reward:{
	if( local.p == NULL ){ end }
	ihuddraw_virtualsize local.p 76 1
	ihuddraw_align       local.p 76 center top
	ihuddraw_font        local.p 76 "verdana-10"
	ihuddraw_color       local.p 76 1 0.85 0.3
	ihuddraw_rect        local.p 76 0 100 0 0
	ihuddraw_string      local.p 76 "CHALLENGE COMPLETE"
	ihuddraw_alpha       local.p 76 1

	ihuddraw_virtualsize local.p 77 1
	ihuddraw_align       local.p 77 center top
	ihuddraw_font        local.p 77 "verdana-12"
	ihuddraw_color       local.p 77 1 1 1
	ihuddraw_rect        local.p 77 0 112 0 0
	ihuddraw_string      local.p 77 local.title
	ihuddraw_alpha       local.p 77 1

	ihuddraw_virtualsize local.p 78 1
	ihuddraw_align       local.p 78 center top
	ihuddraw_font        local.p 78 "verdana-10"
	ihuddraw_color       local.p 78 0.8 0.85 0.95
	ihuddraw_rect        local.p 78 0 126 0 0
	if( local.reward != "" && local.reward != NIL ){
		ihuddraw_string  local.p 78 ( "Unlocked: " + local.reward )
	}
	else{
		ihuddraw_string  local.p 78 "Recorded in your Service Record"
	}
	ihuddraw_alpha       local.p 78 1

	thread mpc_toast_hold local.p
}end


//hold the toast ~4s then clear its per-client ihuddraw slots.
mpc_toast_hold local.p:{
	wait 4
	if( local.p == NULL ){ end }
	ihuddraw_alpha local.p 76 0
	ihuddraw_alpha local.p 77 0
	ihuddraw_alpha local.p 78 0
}end
'''


def render(ch):
    L = [
        "//GENERATED by docs/tools/gen_mp_challenges.py -- DO NOT HAND-EDIT (regenerate instead).",
        "//The MP challenge table + unlock derivation (isolated mirror of coop's challenges.scr). Challenges",
        "//watch the mp_progression stat vector; a completed challenge's reward token enters the player's",
        "//derived unlock set. coop_mpRun-guarded; calls only mp_progression.scr (MP->MP, clause 10).",
        "//%d challenges." % len(ch),
        "",
        "alive:{",
        "\tend 1",
        "}end",
        "",
        "main:{",
        "\tif( level.coop_mpRun != 1 ){ end }",
        "\tend",
        "}end",
        "",
        "//One-time table build (idempotent). Parallel arrays indexed 0..coop_mpChalN-1, file order = index.",
        "mpc_init:{",
        "\tif( level.coop_mpChalReady == 1 ){ end }",
        "\tlevel.coop_mpChalReady = 1",
    ]
    for i, (cid, cat, title, desc, stat, tgt, rw) in enumerate(ch):
        rc = reward_cvar(rw)
        L.append('\tlevel.coop_mpChalId[%d] = "%s"' % (i, cid))
        L.append('\tlevel.coop_mpChalCat[%d] = "%s"' % (i, cat))
        L.append('\tlevel.coop_mpChalTitle[%d] = "%s"' % (i, esc(title)))
        L.append('\tlevel.coop_mpChalDesc[%d] = "%s"' % (i, esc(desc)))
        L.append('\tlevel.coop_mpChalStat[%d] = "%s"' % (i, stat))
        L.append('\tlevel.coop_mpChalTarget[%d] = %d' % (i, tgt))
        L.append('\tlevel.coop_mpChalReward[%d] = "%s"' % (i, rw))
        L.append('\tlevel.coop_mpChalRCvar[%d] = "%s"' % (i, rc))
        L.append('\tlevel.coop_mpChalWtRank[%d] = %d' % (i, reward_wt_rank(rw)))
        L.append('\tlevel.coop_mpChalRewardName[%d] = "%s"' % (i, reward_name(rw)))
    L.append('\tlevel.coop_mpChalN = %d' % len(ch))
    L.append('\tprintln( "^~^~^ MPCHAL init n=%d" )' % len(ch))
    L.append("}end")
    return "\n".join(L) + TEMPLATE_FOOTER


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    ch = all_challenges()
    text = render(ch)
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        raise SystemExit("gen_mp_challenges: output is not ASCII")
    if mode == "build":
        io.open(OUT, "wb").write(text.encode("ascii"))
        print("wrote %s (%d challenges, %d bytes)" % (os.path.relpath(OUT, ROOT), len(ch), len(text)))
        return 0
    if not os.path.exists(OUT):
        print("MISSING %s - run: python docs/tools/gen_mp_challenges.py build" % os.path.relpath(OUT, ROOT))
        return 1
    cur = io.open(OUT, "r", encoding="latin-1", newline="").read()
    if cur == text:
        print("EXACT REPRODUCTION (%s, %d challenges)" % (os.path.relpath(OUT, ROOT), len(ch)))
        return 0
    print("DRIFT - run: python docs/tools/gen_mp_challenges.py build")
    return 1


if __name__ == "__main__":
    sys.exit(main())
