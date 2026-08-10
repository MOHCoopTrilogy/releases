# Coop-native challenges — the mod's own systems

**2026-08-08.** Companion to `objective_challenges.md`, and the more promising half of the idea.

That document mines the **retail** maps, and it keeps running into the same wall: the campaign is
heavily scripted, so most of what looks like a player achievement is a cutscene the player cannot
influence. m1l1's checkpoint always goes loud. m5l3's plunger is destroyed by the tank on script.
That is not a research failure — it is what a 2002 single-player campaign is.

This document mines the opposite direction: **the systems this mod added.** Those are feasible by
construction, because we own the code and can bump a stat wherever we like. They are also the only
challenges that could not exist in anyone else's MOHAA install.

## The gap this fills

The 303 shipped challenges are strong on retail objectives, weapon kills, vehicles and headshots. But
against the mod's own feature list they are nearly silent:

| Mod system | Existing challenges |
|---|---|
| Build mode / bunkers / blueprints | **none** |
| Holdout mode | **none** |
| Allied squad DBNO (new today) | **none** |
| Deployable cover / ammo box | one (`Blind Faith`, blindfire) |
| Ladders, wall guns, emplacements | **none** |
| Weather / fog | **none** |
| Lobby, helmets, cosmetics | **none** (they are rewards, not goals) |
| 4-player coordination | one (`Freeze-Tag Only`) |

Every proposal below names a counter the system already keeps, or one line to add to code we own.

---

## Fireteam — things that need more than one player

The mod is a **coop** mod and this is its thinnest category. These are the ones that could not be
earned solo, which is the point.

| Title | Feat | Hook |
|---|---|---|
| All Present and Correct | Finish a mission with four players alive and none ever downed | `$player.size` + `dbno` down count |
| Simultaneous Salvation | Two players revive two different teammates in the same 10 seconds | `dbno.scr` revive path + timestamp |
| Nobody Walks Alone | Every player on the server revives someone in one mission | per-player revive tally, `dbno` |
| Crew Served | Four players manning four different mounted guns at once | turret owner check across `$player` |
| Ring of Steel | Every player alive inside one deployed sandbag ring when a wave breaks | `cover.scr` placement + proximity |
| Last Two Standing | Win a holdout wave with only two players still up | `level.coop_ho_wave`, `coop_ho_state` |
| Field Promotion | Revive the same teammate three times in one mission | `dbno` revive tally per target |

## Allied squad — the system built today

| Title | Feat | Hook |
|---|---|---|
| Not On My Watch | Finish a mission having revived an ally and lost none | `coop_allyDowns`, `ally_revive` |
| Corpsman, Forward | Revive 10 downed allies across the campaign | `ally_revive` count |
| Second Wind | Revive an ally within 10s of them going down | `ally_go_down` timestamp vs revive |
| Held the Line | Finish t2l3 with zero breaches and the full squad alive | `level.coop_leaks` + ally count |
| Nobody Bleeds Out | Complete a mission where every downed ally was recovered | `coop_allyDowns` vs bleed-out deaths |

## Build mode — nothing rewards it today

| Title | Feat | Hook |
|---|---|---|
| Combat Engineer | Place your first structure that scores a kill | `bunker.scr` + kill attribution |
| Sited by Hand | Get 25 kills from emplacements you built | `coop_mgnest*` / `coop_flak*` targetnames |
| Fortress Builder | Place 50 structures across the campaign | `level.coop_build_count` |
| Own Private Atlantic Wall | Have 10 built pieces standing at mission end | `coop_bs_*` structure registry |
| Gunner's Choice | Man an AA gun you placed yourself and kill with it | `coop_aaThink` owner check |
| Blueprint Architect | Save a blueprint and place it on a different map | `blueprint.scr` `bp_save` / `bp_place` |

## Deployables and cover

| Title | Feat | Hook |
|---|---|---|
| Quartermaster | Resupply teammates 25 times from your ammo boxes | `level.coop_ammobox_count` + use hook |
| Sandbag Doctrine | Survive a wave without leaving cover you placed | `level.coop_cover_count` + proximity |
| Dug In | Place cover, take 10 kills from behind it, never leave it | `cover.scr` + blindfire counters |

## Holdout

| Title | Feat | Hook |
|---|---|---|
| Ten Rounds | Reach wave 10 in holdout | `level.coop_ho_wave` |
| Untouched Round | Clear a holdout wave with nobody downed | `coop_ho_wave` + `dbno` |
| Last Man Holding | Finish a wave as the only player still up | `coop_ho_state` + `$player` liveness |

## Feel systems — the things nobody notices are systems

| Title | Feat | Hook |
|---|---|---|
| Ears Still Ringing | Survive an explosion close enough to trigger tinnitus and win the fight | `tinnitus.scr` |
| Weathered | Complete a mission in every weather theme | `level.coop_weatherTheme` |
| Ladder Discipline | Use a placed ladder to reach a spot and kill from it | `level.coop_ladder_n` |
| Gunner and Loader | Ride a vehicle turret while another player drives | `bt_playerTank` / `vehiclehandler` |

## Cosmetic and identity — reward the wardrobe

| Title | Feat | Hook |
|---|---|---|
| Matching Set | Whole squad wearing the same helmet at mission start | `flags[coop_helmetIdx]` across players |
| Out of Uniform | Finish a mission wearing a helmet you unlocked that session | `helmet.scr` + `chal_add_unlock` |

---

## Why these are feasible where the retail ones are not

A retail challenge is feasible only if the map already tracks the thing **and** the player can change
it — two conditions, both outside our control, and the second is why m1l1's checkpoint challenge had
to be deleted.

A coop-native challenge has neither problem. The system is ours: if `ally_revive` should count, we add
the `chal_bump` on the line that already runs. The only real cost is the cvar budget — the Service
Record allocates roughly three archived cvars per row, and `MAX_CVARS` was raised to 8192 today with
the live config near 2720 (bug-1582). That is the number to watch, not the implementation.

**Recommendation:** build these before the retail set. They are cheaper, they cannot be invalidated by
a cutscene, and they reward the parts of the game that are actually this mod's work.
