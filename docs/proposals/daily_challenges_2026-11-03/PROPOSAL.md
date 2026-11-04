# Daily Orders: rotating daily challenges with real XP

**Status:** research and design only. No mod, engine or UI file was changed.
**Asked for (user, 2026-11-03):** five daily challenges that rotate, pay real XP toward rank, show with progress bars on
the right-hand side of every lobby, get a "current 5" section in the Service Record, raise the in-game Service Record
toast on completion, and come with a list of about 100. Follow-up: model it on Call of Duty's dailies.

> **Revision 2 (same day), after review of the first 100:** "a bit on the easy side / not very creative", then "make
> more centered around features we have built into the mod", then the pillars to build on: ammo crate, revives, DBNO,
> high-ranking officers, objectives. The pool was rewritten (§3.7): targets roughly doubled, most orders are now
> situational (a condition, a combo or a mission played a set way), and almost every order uses a system only this
> mod has. XP was retuned to match (§3.3). Of the 100, **55 run on hooks that exist today** and **45 need one of 14 new
> hook points** (11 one-line script hooks, 3 small engine exports). The schedule check passes for the full pool and for
> a phase 1 without the engine hooks (94 orders).

Files in this folder:

| file | what |
|---|---|
| `PROPOSAL.md` | this document |
| `daily_challenges.json` | the 100 as data: id, title, description, target, difficulty, xp, mode, hook, new_hooks, category (pillar), tags, family; plus the NEW hook table |
| `daily_challenges.md` | the same 100 as tables grouped by difficulty, plus a sample fortnight from the scheduler |
| `tools/gen_dailies.py` | writes both files, checks every string for wire and parse safety, and builds/validates a 364-day schedule |

---

## 1. How Call of Duty does it, and what we take

| CoD (MW2019 to BO6) | Ours | Why |
|---|---|---|
| **3 dailies per mode** (MP, Zombies, Warzone each have their own), replaced every 24 h at one global reset time | **5 a day, one shared set**, reset at **10:00 UTC** | The user asked for 5. One shared set (not one per mode) because the squad plays together and the lobby panel shows the same orders to everyone. Mode suitability is handled by the scheduler (§3.1). |
| Countdown to reset in the challenge menu | "New orders in 7h 12m" line on the lobby panel and the Service Record tab | Same thing. |
| Short tasks you can finish in one sitting: kills with a weapon class, headshots, play N matches, objectives, use equipment, revive | Same shapes, in our classes (rifle, SMG, sniper, pistol, MG, shotgun, launcher, Axis pickups) and our features (revive, ammo box, medkit, deployed cover, blindfire, bracing, mounted MG, emotes, grenade kick, air strikes, paratroopers, vehicles, planes, objectives, missions) | Revision 2 sizes them harder than CoD's: Easy = one or two missions played for it, Medium = a session, Hard = a mission played a set way (§3.7). |
| XP on each (BO6 at launch: roughly 2,500 per daily, about 3,000 extra for all three; sources disagree) | Easy **400**, Medium **750**, Hard **1250**, **+1500 for all five** (5,050 a day at most) | Scaled to *our* ladder (§3.3), not copied. |
| MW3 (2023): clearing all three unlocks repeatable **bonus challenges** | **All-five bonus** ("Mentioned in Dispatches"), once a day | A repeatable bonus pays most to whoever grinds longest. One payment does the job. |
| Progress bar on each challenge, a pop-up when one completes mid-match, and challenges you can track/pin on the HUD | Bars in the lobby panel and the SR tab; the existing CHALLENGE COMPLETE toast with a **DAILY ORDER COMPLETE** header | We already have the toast and the 0..10 bar art (`textures/hud/coop_bf<n>`). |
| **Rerolling:** Cold War let you swap a daily for a reserve one and keep its progress. MW3 has no reroll (you wait out the 24 h) | **No reroll in v1.** v2 option: one free swap a day to that slot's deterministic reserve | A reroll makes the set per-player, which breaks "everyone in the lobby sees the same orders". The scheduler keeps every day completable instead (§3.1). |
| Per-player dailies (MW2019 said they differ from player to player) | **Not adopted**: one global set | Squad coordination; no server needed for agreement. |
| Dailies in the front-end: a challenges widget on the main menu or lobby, with a full Challenges tab | Right-hand **lobby panel** (in game) + **DAILY ORDERS tab** in the Service Record (works disconnected, showing the last known state) | The same split. |

I could not confirm CoD's exact reset hour from the sources; 10:00 UTC is our own choice, explained in §3.1.
Sources: [Treyarch - Daily Challenges Have Arrived (Cold War)](https://www.treyarch.com/game-intel/2020/12/Daily_Challenges_Have_Arrived) ·
[Charlie Intel - MW2019 daily challenges](https://www.charlieintel.com/modern-warfare/modern-warfare-features-daily-challenges-with-xp-rewards-57455/) ·
[GameWith - MW3 challenges / bonus challenges](https://gamewith.net/cod-mw3/42438) ·
[Dot Esports - MW3 dailies cannot be reset](https://dotesports.com/?p=1045522) ·
[Digital Trends - BO6 daily XP](https://digitaltrends.com/?p=3751134) ·
[ONE Esports - BO6 levelling](https://www.oneesports.gg/call-of-duty/how-to-level-up-fast-in-black-ops-6/)

---

## 2. What exists (read from the code, which wins)

### 2.1 Challenge engine: one funnel, already the right shape
- `coop_mod/challenges.scr::chal_bump local.player local.stat local.amount` (:1168) is **the** progress entry point:
  every challenge stat is fed through it, and it walks `level.coop_chal_statIdx[stat]` into `chal_apply` (:1192) →
  `chal_grant` (:1231). `chal_team_bump` (:1392) fans one stat out to every player (objectives, missions, vehicles,
  map completions).
- **`chal_grant` already pays XP** (added today for v1.10.62): 100..600 by target, +250 for an Elite, via
  `thread coop_mod/xp.scr::xp_award local.player local.cxp "challenge" "Challenge"`.
- Stats fed today (all countable by a daily with **no new hook**):
  - from `chal_ai_killed` (:1583): `kill`, `kill_us`, `kill_snow` (m2/m5/t2), `kill_desert` (m1/e1), `fac_*`
    (heer, ss, afrika, kmarine, regio, carab, italy, officer, sniper, general, variety), `wpn_<wid>` (the killer's held
    weapon via `chal_weaponId` → `chal_widFromModel`, :1429/:1452), `headshot`, `melee` (MOD 26), `grenade` (MOD 14),
    `rocket` (MOD 16), `savior`, `scripted_havoc`, `wallbang`, `longshot` (> 2000 u), `blindfire`, `coverkill`,
    `coverown`, `reinf`, `downedkill`
  - elsewhere: `officer` (HRO, :1781), `airstrike` / `reinforce` (support calls, :1796), `objective` (team, :1812),
    `sideobj` (team, :1921), `revive` (:1931), `vehicle` (team, :1980), `missions` / `map_<map>` / `nodeath`
    (`chal_mission_complete` :2174, which already skips briefings and lobbies, bug-722), `allyrevive`
    (allysquad.scr:316), `ammoboxuse` (ammobox.scr:254), `blueprint`.
- **Second funnel**: `xp.scr::xp_award` (:603) carries a specific `label` for each award: `Assist`, `MG Gunner`,
  `Wave Broken`, `First Blood`, `Killstreak x5/10/15/20/25` (`xp_streak_kill` :1325), `Air Strike Kill`,
  `Plane Shot Down` (aircraft.scr:1529), `Vehicle Destroyed`, `Searchlight Disabled`, `Cover Used` (squadmates using
  your deployed cover, :1404), `Patched a Squadmate` (medkit.scr:508), `Paratrooper Alive`, `Deathless`, and others.
- **MP** has its own funnel: `mp_progression.scr::mp_bump local.p local.stat` (:404) with stats `total`, `rifle`,
  `smg`, `sniper`, `pistol`, `mg`, `headshot`, `melee`, `grenade`, `rocketk`, `revive`, `capture`, `plant`, `defuse`,
  `destroy`, `flagret`, `rounds`, `win_<mode>`. MP may not call `challenges.scr` (`docs/tools/check_mp_isolation.py`:
  `challenges` is in `MP_COOP_DENY`; only `MP_COOP_ALLOW` entries such as `xp::xp_award_mp` are callable).

### 2.2 Weapon names (verified against `chal_widFromModel` and the chal_def stats)
Rifles `garand kar98 g43 enfield mosin svt carcano arisaka johnson stg44` · SMGs `thompson greasegun mp40 sten ppsh
type100 moschetto` · snipers `springfield kar98sniper g43sniper mosinsniper carcanosniper arisakasniper l42a1 delisle` ·
pistols `colt silenced p38 luger ppk webley nagantrev tt33 beretta nambu welrod c96 m10` · support `bar mg42 thirtycal
breda dp28 vickers fg42 shotgun bazooka panzerschreck piat`. The `coop_chal_isPistol` / `isBolt` tables at
`chal_init` (:52) are the precedent for a wid → class table.
**The armory locks most guns behind rank** (`xp.scr` `coop_xp_rankUnlock`: Kar98 rank 3, Sten 4, PPSh 6, Grease Gun 8,
Mosin 13, Type 100 17, FG 42 19...). So **per-gun dailies use only guns everyone can hold**: the Garand, Thompson and
Colt, the BAR, and Axis guns picked up off the floor (Kar98k, MP40, StG44). Everything else is by class.

### 2.3 Persistence: progression already follows the player, and its merge rule fits dailies
- Server side: `coop_mod/save/chal_<id>.dat` plus a session cvar `coop_chal_<id>` holding `cid:progress|cid:progress`
  (`chal_serialize` :1012, `chal_deserialize` :976, `chal_save_player` :1033, `chal_flush` every 30 s :1053). Identity
  is `coop_xp_id` = cl_guid, falling back to `n_<netname>` (`xp.scr::xp_identify` :392).
- Follows the player (bug-3903, v1.10.23-28): engine `fgame/g_coopsync.cpp` + `bg_coopsync.h` (seen in the
  `openmohaa-hzm-fix61` worktree; the base checkout's `hzm-coop-working` HEAD predates it). The client uploads its own
  records on join, and the server merges them (they can only add) into its file **and** session cvar. Every later
  `fs_write_content` to `coop_mod/save/<type>_<id>.dat` is sent back down to the owning client. There are 7 record
  types: `xp chal unlocks pins pend medals bpfound`. **`chal` uses `COOPSYNC_MERGE_CHAL`: union of keys, and for a key on
  both sides the larger numeric value wins** (`CoopSync_Merge`, `atol` compare). Limits: 32 KB/record, 2048 tokens,
  160 chars/token. `xp.scr::xp_waitSync` holds the reads until the merge lands.
- `chal_deserialize` loads **any** `cid:value` into `flags["coop_chalP_<cid>"]`, but `chal_serialize` writes only cids in
  the catalog (`level.coop_chal_count`), so a key the catalog does not know is dropped on the next save.

### 2.4 Date and time: no usable UTC source today
- `ScriptThread::GetDate` (`fgame/scriptthread.cpp` :6586) returns **local time** `"dd.mm.yyyy hh:mm:ss AM"`
  (`strftime %d.%m.%Y %r`). `GetTime` (:7480) returns local `"hh:mm:ss"`. `GetTimeZone` (:6600) reads
  `ev->GetInteger(1)` although the event declares no argument, and it compares whole hours only. It breaks across
  midnight and in half-hour zones. **No script in the mod uses any of the three.**
- Two hosts in different time zones would therefore disagree on "today", and the client UI has no clock at all. A
  tiny engine builtin is needed (§3.1).

### 2.5 UI facts that constrain the panel
- **All fade-exempt ihuddraw slots (100-255) are taken** (`_research/hud_slot_map.md`, "Genuinely free: Nothing").
  The lobby already uses: top-left help 112-113, NEW UNLOCKS list 117-126 (left), roster 100-111 (bottom-left), and the
  **next-mission briefing at the top right** (`lobby.scr::lobbyBriefDraw` :840: slots 128-136, `right top`, x -240,
  y 12 + 22·i, up to 9 lines, so down to y ≈ 200). The in-lobby Service Record panel takes 150-249.
  → The daily panel **cannot be ihuddraw**. It has to be a `.urc` added with `ui_addhud`, its labels bound to cvars
  (precedent: `ui/coop_jeepEnter.urc` via `stufftext "ui_addhud coop_jeepEnter"`, maps/M1L3a.scr:664; right-edge
  anchoring with a small menu rect plus `align right top`, as `ui/hud_score.urc` does). Zero HUD slots.
- The Service Record is **one generated menu**, `ui/coop_sr.urc` (692 KB), written by `docs/tools/gen_service_record.py`
  (its header still says `scratchpad/gen_sr4.py`; that is stale). Rows are baked texture pages plus overlay
  Labels bound with `linkcvar coop_uiB<i>` + `linkcvartoshader` (bar) and `linkcvar coop_uiN<i>` (count). The values
  are archived client cvars pushed by `chal_ui_export` / `chal_ui_writeOne` (:1086/:1115), dirty-tracked and paced
  (bug-1670: 1024-deep reliable ring). The **MEDALS** tab (`coop_srMedals` view cvar, its own bg) is the template
  for a new tab. Its generator warns about "String too large" (:928).
- `seta <cvar> <words...>` keeps every word (`Cvar_Set_f` uses `Cmd_ArgsFrom(2)`). Text therefore goes over the wire
  **unquoted** (bug-758: quoted stufftext truncates) and must not contain `;` `"` `//`, nor the debrief's `| ~ ^`. The
  generator asserts all of this.
- Toast: `chal_notify` → `chal_toast_pump` → `chal_toast_show` (:2759) draws in the top-right SR column, slots 76-78
  and 84-87. The header **"CHALLENGE COMPLETE" is hard-coded** (:2791).
- Debrief: `xp.scr::xp_card_categories` (:2192) tallies 7 keys (`challenge` is key 6) but shows **at most 4 lines**. On the
  unmerged `debrief2` branch, `coop_mod/debrief2.scr` sends `~dT~label|xp` tally lines and a CHALLENGES COMPLETED
  sheet from `flags coop_mapChalList` (filled by `db2_chalDone`, as challenge *indices*) as `~dN~` / `~dC~title|desc`.

---

## 3. Recommended design

### 3.1 Rotation: a generated schedule plus an engine UTC day number
- **Day number:** `D = floor((unix_time - 36000) / 86400)`, so the day starts at **10:00 UTC** (04:00 CST, 05:00 EST,
  11:00 CET). UTC midnight would be 18:00 for this user, mid-session, while 10:00 UTC lands where few players in NA or
  EU are playing. It is a **code constant, not a cvar**: a per-server cvar would let two servers disagree.
- **Engine hook (game.dll, ~25 lines in `scriptthread.cpp`):** `getutcday` → int `D`, and `getutcsecs` → seconds until
  the next reset. Both use `time(NULL)` integer arithmetic, so no `localtime`/`gmtime`. Per **TRAPS T1** ("an engine-new
  command fails the WHOLE file on an older game.dll", bug-3423), the two calls live alone in a helper
  `coop_mod/daily_clock.scr`. On an old dll only that helper fails to compile, `daily.scr` sees NIL and turns Daily
  Orders off (no orders, no panel). It does not crash, and it does not guess a local date.
- **Selection is a lookup, not a script RNG.** `tools/gen_dailies.py` (to become `docs/tools/gen_daily_orders.py`)
  emits `coop_mod/daily_gen.scr`: the pool (100 × id/title/desc/target/tier/hook) and a **364-row schedule**, row =
  `D mod 364`, each row 5 pool indices. Every server and client agrees with no network service, script needs no
  integer-overflow-prone hash, and the rules are checked offline:
  - 2 Easy + 2 Medium + 1 Hard; no repeat within 14 days; no two orders on the same stat in one day
  - ≥ 1 order a multiplayer player can do (Any or MP); ≤ 1 MP-only, **never in the Hard slot** (so a coop-only squad loses at most
    one order, and the all-five bonus stays reachable on a day without MP-only orders; see open question 1);
    ≤ 1 map-limited (`theatre` tag); ≤ 2 weapon orders
  - ≤ 2 orders that need a squad (`squad`), ≤ 1 that needs DBNO on (`dbno`), ≤ 2 from one pillar, one order per stat family
    (tiered pairs such as Return to Sender / Special Delivery never share a day)
  - orders whose hook has not shipped stay out of the schedule (the generator's phase filter; phase 1 = no engine hook,
    94 orders, checked for 364 days)
  - the sample run gives every order 11-25 appearances a year (`daily_challenges.md`, bottom)
- **Map-limited orders** (snow, desert, vehicle, plane, barrel) never share a day, and each has several maps where it
  can be done.

### 3.2 Per-player state: ride the existing `chal` record
**Five fixed keys in the chal record, with the day folded into the value:**

```
dly0:20395007|dly1:20395040|dly2:20395000|dly3:20394012|dly4:20395001|dlyB:20395
            ^ day*1000 + progress (targets are < 1000, asserted)     ^ bonus paid on day D
```

- **`COOPSYNC_MERGE_CHAL`'s "larger number wins" does the right thing with no engine change**: a newer day always beats
  an older one, and within one day the higher progress wins. A stale copy on another server, or yesterday's copy on
  the player's PC, can never overwrite today's.
- Read: `v = flags["coop_chalP_dly<k>"]`. If `int(v / 1000) == D`, progress is `v % 1000`, otherwise 0. Done means
  progress ≥ target.
- Write: two one-line hooks in `challenges.scr`. `chal_serialize` appends `waitthread coop_mod/daily.scr::daily_tail
  local.player`, so the keys survive the catalog filter (§2.3) and the existing diff gate, file write and 30 s flush.
  `chal_ensure` needs nothing new: `chal_deserialize` already loads the keys.
- **"Today" is fixed at map load** (`level.coop_dly_day`, read once in `daily_init`). A reset mid-mission does not
  wipe progress under the player's feet. That map's kills count toward the day it started on, and the new orders
  show up in the next lobby (the panel says "New orders at next deployment"). This also stops a "complete a mission"
  order from being paid against an order the player never saw.
- **Host vs client:** the server is authoritative, as for every challenge (`profile.scr` posture). The client only
  holds the mirror, which coopsync uploads on join and receives back after every write. A mid-mission joiner goes
  through `chal_ensure` → `xp_waitSync` like any join and inherits his own progress. A record edited on the client
  can only raise progress; XP is paid only when progress **crosses** the target on the server, and a record that
  arrives already complete is marked done silently (the `chal_ensure` :875 pattern). That is the same exposure every
  existing challenge already carries.
- **MP:** `challenges.scr` is denied to MP, so `daily.scr` must be **mode-neutral** (it touches only `flags`, the chal
  file and xp) and gets two `MP_COOP_ALLOW` entries: `daily::daily_onStat` and `daily::daily_onMpStat`. In MP,
  `daily.scr` does its own read-modify-write of `chal_<id>.dat`: replace the `dly*` tokens, keep everything else,
  write. Coopsync carries it home exactly as in coop. Verify early (test plan T6) that the MP client handshakes
  coopsync the way a coop client does.
- **Rejected:** an 8th coopsync record type `daily`. It is cleaner, but `COOPSYNC_NTYPES` goes into the `begin 2 <7
  digests>` handshake, so cgame and game would both change with a protocol bump. That is the protocol-constant class of
  TRAPS, and it buys nothing over the 5 keys.

### 3.3 XP
| tier | XP | for scale |
|---|---:|---|
| Easy | 400 | rank 1 is 500; one or two missions played for it |
| Medium | 750 | above a long-grind regular challenge (400-600), because it asks for a whole session played for it |
| Hard | 1250 | a mission played a set way, or a demanding streak |
| all five | +1500 | **Mentioned in Dispatches** |
| day max | 5,050 | ≈ 1 % of the top rank (500,000); worth playing for, not a shortcut |

Retuned in revision 2 (was 250 / 500 / 900 / +1000) because the targets roughly doubled and most orders now attach a
condition. The ratio between tiers stays about 1 : 2 : 3.

- Paid with `thread coop_mod/xp.scr::xp_award local.player <xp> "daily" "Daily Order"`. It counts toward rank and
  prestige like any award (rank-up ceremony, unlocks, flush), and the crosshair micro-popup shows "+500 Daily Order".
- **Debrief:** add key 7 `daily` / "Daily Orders" to `xp_card_categories` (raise the loop bound 7 → 8; the 4-line cap
  remains, so the order is kills, valor, objectives, **daily**, ...), and to the same table in `debrief2.scr`. On
  debrief2 the completed orders join the CHALLENGES COMPLETED sheet: a parallel `coop_mapDailyList` (the order's
  pool index), sent as `~dC~Daily Order: <title>|<desc>`. `coop_mapChalList` holds catalog indices and must not mix
  in pool indices.
- **MP:** `xp_award_mp` caps a match at 2,000 (`coop_xp_mpMatchCap`). Reason `"daily"` is **exempt** from the cap
  (one `if` in `xp_award_mp`): dailies are capped by design already, and a capped order would pay nothing at the end
  of a good match.

### 3.4 Hooks: four one-liners into existing funnels, then 14 small new hook points
| where | line | covers |
|---|---|---|
| `challenges.scr::chal_bump`, after the loop | `waitthread coop_mod/daily.scr::daily_onStat local.player local.stat local.amount` | every `chal:` and `class:` order (`wpn_<wid>` → class table in `daily_gen.scr`) and the kill timestamp for multikills |
| `xp.scr::xp_award`, after the bucket add | `waitthread coop_mod/daily.scr::daily_onXp local.player local.label` | every `xp:` order |
| `mp_progression.scr::mp_bump` | `waitthread coop_mod/daily.scr::daily_onMpStat local.p local.stat local.amount` | every `mp:` order |
| `challenges.scr::chal_mission_complete` | `thread coop_mod/daily.scr::daily_onMission local.mapname` | `mis:` rules (campaign by map prefix m/e/t, squad size, all alive) |

`daily_onStat` must cost almost nothing on a kill. A kill already runs ~10 `chal_bump`s, so `daily_init` builds
`level.coop_dly_byStat[<stat>]` covering only today's 5 orders. A stat with no order returns after a single array read.
**New hook points (revision 2).** The situational orders need context the funnels above do not carry: who was
revived and how close to bleeding out, who resupplied whom, whether the killer was downed, how far away the victim was.
Each is one line at a place that already has the data. The full table is in `daily_challenges.json` (`new_hooks`)
and at the end of `daily_challenges.md`.

| id | kind | where | orders using it |
|---|---|---|---:|
| N1 | script | `chal_ai_killed` → `daily_onKill victim killer wid` (distance, weather theme, victim faction, killer downed, per-life/per-map tallies, multikill window) | 16 |
| N2 | script | `ammobox.scr` ~:254, owner-found branch → `daily_onResupply owner receiver` ("under fire" = `xp_revive_underfire`'s 2+ Germans within 700 u) | 3 |
| N3 | script | `dbno.scr` ~:1054 beside `chal_revive` → `daily_onRevive reviver downed` (+ the downed man's `coop_dbno_elapsed`/`coop_dbno_timer_actual`) | 6 |
| N4 | script | `medkit.scr::dbno_selfrevive` success | 2 |
| N5 | script | `dbno_enter` and the player death path (the same two sites that stamp `coop_wentDownMap`) → ends the current "life" | 4 |
| N6 | script | `chal_officer_killed` → officer + killer (`fact.location`, `meansofdeath` are already read there) + a `level.coop_officerWavesCalled` counter in `officer.scr::coop_officer_reinforcements` | 3 |
| N7 | script | `chal_mission_complete` → mission rules: map list/prefix, `skill`, `coop_hardcore`, `$player.size`, `coop_wentDownMap`, `level.coop_chalAlarmEver`, `level.coop_chal_radioPaid`, the existing `coop_chalL_usedNonPistol` flag and a new `usedNonAxis` | 15 |
| N11 | script | `alarm.scr::alm_deactivate` (has the player) | 1 |
| N12 | script | `surrender.scr::convert local.actor local.player` | 1 |
| N13 | script | `emotes.scr::emote_play` (Tab-wheel emotes ship in v1.10.62) | 1 |
| N14 | script | `weaponstate.scr` RAISE_WEAPON: stamp `level.time` next to `coop_activeWeapon` (quick draw) | 1 |
| N8 | engine | grenade kick (`player.cpp` ~:20533): count kicks on the player, stamp the kicked projectile with its kicker | 2 |
| N9 | engine | gun bracing: export the brace envelope and the carried-MG heat/overheat latch as player vars | 2 |
| N10 | engine | `EnterTurret`/`ExitTurret`: export the mounted turret on the player | 2 |

All 11 script hooks are inside phase 1. The 3 engine exports are phase 2. The 6 orders that use them stay
unscheduled until they ship.

### 3.5 UI
**Lobby panel: right-hand side, under the briefing.** `ui/coop_daily.urc` (generated), `menu "coop_daily" 200 200`,
`align right top`, placed below the briefing's last line (y ≈ 210 → 410 in 640×480 virtual). It sits above the roster
(bottom-left) and away from NEW UNLOCKS (top-left). Shown with `stufftext "ui_addhud coop_daily"` from
`lobby.scr::lobbyOnSpawn` and removed with `ui_removehud coop_daily` in `lobbyLaunch` (next to `cg_huddraw_force 0`,
:761), so it never reaches the mission.

```
 DAILY ORDERS                      new orders in 7h 12m
 [ ] Under the Gun            +750   Resupply squadmates 4 times while...
     [#######---]  9/15
 [x] Stretcher Bearer         +400   ...
 ...                                  (5 rows, Easy/Easy/Med/Med/Hard)
 [ ] Mentioned in Dispatches  +1500  clear all five      3/5
```

Per row: tick (box_empty/box_done, which already ship in `textures/hud/coop_sr/`), title, short description, bar
(`coop_bf0..10` art), `n/N`, `+XP`. The cvars are `coop_dlyT<k>` `coop_dlyD<k>` `coop_dlyB<k>` (bar shader) `coop_dlyN<k>`
`coop_dlyX<k>` `coop_dlyK<k>` (tick shader), plus `coop_dlyR` (countdown text) and `coop_dlyDay`. All are **archived**,
so the disconnected Service Record shows the last state. They are pushed by `daily_export`, dirty-tracked per value like
`chal_ui_writeOne`: at most ~32 commands on the first lobby of the day, then only the values that change. The
countdown is re-sent once a minute while in the lobby. Paper/WW2 styling: the panel bg is a generated parchment strip
that matches the SR pages (same `serif()`/`sans()` fonts as `gen_service_record.py`). Check it at 4:3, 16:9 and 21:9
with the right-anchored rect; the SR menu itself is 4:3-centred.
- **Every lobby:** the coop lobby maps (co_lobby1-8 via `lobby.scr`) get the panel. The MP hub/front-end
  (`docs/proposals/mpui_2026-11-02/make_mpui.py`, `mphub3d_2026-11-02/gen_srboard.py`) can include the same widgets.
  They read archived cvars, so offline they show "as of" the last session. Optional client engine hook (cgame/ui, ~15
  lines): publish `ui_utcDay` / `ui_dailyReset` every second, so a disconnected menu can tick the countdown and grey out
  a stale day. Without it, the menu text says "last updated".
- **Service Record "DAILY ORDERS" tab:** add it to `gen_service_record.py` next to MEDALS (view cvar `coop_srDaily`,
  its own baked bg). Its rows are **Labels bound to the same `coop_dly*` cvars**: titles rotate, so they cannot be baked
  like the catalog rows. It shows the 5, the bonus row, the countdown, and "orders completed: N" (lifetime counter key
  `dlyC`, merge-max like the rest).
- **Toast:** `chal_notify` gains an optional header (`chal_notify local.player local.title local.head`, NIL keeps
  "CHALLENGE COMPLETE"), queued in a parallel `coop_chalHeadQ[]`. Daily completions toast **DAILY ORDER COMPLETE** with
  the title, and the bonus toasts **MENTIONED IN DISPATCHES**. They go through the same pump, so they never stack on a
  regular challenge toast.
- **Quarter-progress popups** (`chal_progress_popup`, pinned-only today): show them for the 5 dailies too. Dailies are
  the "tracked" set, as in CoD.

### 3.6 Theme
"Daily Orders", or "Orders of the Day" on the SR tab. The bonus is **Mentioned in Dispatches**. Titles are short and
concrete in CoD style, with a WW2 tone, and none reuses an existing challenge title (checked by hand against
`chal_def`; the generator asserts uniqueness inside the pool). No real person's name and no slurs. "Bazooka Joe" is the
one wink.

### 3.7 The pool, revision 2: harder, situational, built on our systems
**Pace basis.** I found no measured per-map kill census in the maptest or debrief logs: the harness logs I checked
carry `kills=0` bot runs, and the live `qconsole.log` is 74 KB. The targets are therefore estimates. A retail mission
holds roughly 50-120 Germans, and count scaling, reinforcements and officer waves add more. So a solo player gets
roughly 60-120 kills a mission, and each of 2-4 players gets 25-50. **Calibrate before shipping:** have
`daily.scr` print `^~^~^ DAILYPACE map=<m> kills=<n> hs=<n> revives=<n> resupplies=<n> objs=<n>` per player at
mission complete, run the maptest Phase 2 patrol and a few real sessions, then re-run the generator with the measured
numbers. The targets are plain data in `tools/gen_dailies.py`.

**Tiers.** Easy is a count you reach in one or two missions *if you play for it* (20 kills from cover, 8 resupplies,
4 revives). Medium attaches a condition (4 resupplies **while enemies are close**; revive **with under 5 s of
bleed-out left**; **15 kills without going down, 3 times**). Hard is a mission played a set way or a demanding feat
(finish a hold mission with **nobody** going down; an officer boss killed **before his first wave**; **pistols
only** for a whole mission; **20 braced MG kills without overheating**).

**Pillars** (counts in `daily_challenges.md`): Revives 10, Officers 10, Objectives 10, DBNO 6, Ammo crate 5
(+ sandbags), MGs (braced, mounted, enemy gunners) 6, Explosives (kicked grenades, barrels, launchers) 6, Theatres
and signature missions (Omaha, Norway train defence "Snowplow", U-boat stealth, Breakthrough, Spearhead, weather) 6,
Squad 3, Service Record 2, Support (air strikes, paratroopers) 2, Vehicles (halftracks, Stukas) 2, MP on campaign
maps 6, plus Combat 24. Of those, 7 are plain Any-mode class and headshot counts, kept so a multiplayer player always has work; the rest use mod systems: cover, blind fire, alarm and rooftop snipers, surrender/recruit,
quick draw, streaks, Axis pickups.

**Asked for but dropped or reworded, because it cannot be measured or does not exist:**
| idea | verdict |
|---|---|
| artery hits / bleed-outs on enemies | no such system in the code (grep `artery`: none); the DBNO bleed-out is the player's own, and is used (Last Breath) |
| kills on burning enemies | only burning wrecks and scorch marks ship; no AI on-fire state |
| dismemberment | `IN PROGRESS` in FEATURES.md, not shipped. Blast decapitation ships, but has no script signal |
| demo studio (record or save a clip) | entirely client-side (cgame/demo playback); the server never sees it, so nothing to count |
| collateral (two kills with one bullet) | depends on body penetration, which I could not confirm reliable; dropped rather than ship an order that may never fire |
| be the one who plants or triggers an objective | `global/objectives.scr` reports completion without a player; the plant scripts come from the retail paks. Kept only team objectives |
| revive a mate, then kill **his attacker** | the down is not attributed to an attacker in `dbno_enter`; reworded to **Payback** (3 kills within 15 s of the revive) |
| finish downed enemies | Germans do not go down (only allied escorts and players do); surrender/recruit is used instead (Turncoat) |
| kills within N s of leaving cover; kills while sprinting or airborne | needs an exit timestamp or movement state from the engine; not worth a fourth engine export |
| counter-attacks after the main objective | shipped **switched off** (resume list), so not schedulable |

**Caveats kept in the data.** `objective` progresses only where objectives route through `global/objectives.scr`
(the AA-style maps; `cc_objFeat` notes that the SH/BT and Omaha maps use their own hooks). Objective orders
therefore move on most, not all, campaign maps. A `squad` order is impossible solo. Allied-AI revives (Leave No One
Behind) and the per-life orders are the solo-friendly side of the same pillars, and the scheduler allows at most 2
squad orders a day. A `dbno` order needs `coop_dbno 1`.

---

## 4. Alternatives rejected
| option | why not |
|---|---|
| Seed from `getdate` (local date) | Servers in different time zones disagree; `gettimezone` is broken (§2.4) |
| Script-side PRNG from the day number | Morpheus integer overflow is unspecified; the scheduler's rules (tier mix, mode, map limits) are far easier to check offline |
| Per-player orders (MW2019) or rerolls (Cold War) | The squad would see different orders. Kept as a v2 option: one swap a day to a reserve |
| Register dailies as `chal_def` entries | They would join the catalog, the SR pages, medals, `check_challenges.py` and the 30 s `chal_ui_export`, all of which assume fixed ids |
| An 8th coopsync type | A handshake/protocol change in cgame and game for nothing (§3.2) |
| ihuddraw panel | No fade-exempt slots left (§2.5) |
| Day-tagged keys (`d20395_rifle15:7`) | They grow forever (5 tokens a day against a 2048-token / 32 KB record); the 5 rolling keys stay constant |

---

## 5. Effort
| piece | size |
|---|---|
| engine: `getutcday` / `getutcsecs` (game.dll), optional `ui_utcDay` (cgame) | 0.5 day + build/deploy (both installs, public servers) |
| `docs/tools/gen_daily_orders.py` → `coop_mod/daily_gen.scr` + `ui/coop_daily.urc` + panel art | 1 day |
| `coop_mod/daily.scr` (init, onStat/onXp/onMpStat/onMission, grant, bonus, export, MP save) + `daily_clock.scr` | 1.5 days |
| hook lines in challenges/xp/mp_progression, toast header, debrief key, MP cap exemption, allowlist | 0.5 day |
| SR tab in `gen_service_record.py` | 0.5 day |
| revision 2: 11 script hook lines (N1-N7, N11-N14) + the condition logic in `daily.scr` (per-life / per-map tallies, multikill window, revive and resupply context, mission rules) | +1.5 days (phase 1) |
| revision 2: 3 engine exports (N8 kick credit, N9 brace + heat, N10 turret) | +1 day + a game.dll build/deploy (phase 2) |
| tests (§7), plus a check for each hook point | 1.5 days |
| **total** | **~7 days for phase 1 (94 orders), ~8 with the engine exports (all 100)**; revision 1 was ~5 / ~6 |

## 6. Risks
- **Command overflow / hitch (bug-10495):** several dailies can complete in one frame (mission complete pays
  `missions`, `nodeath` and a `mis:` rule together). Grants are therefore **threaded and paced 0.2 s apart**, and a daily
  grant never calls `chal_add_unlock` (no token, so no `containsText` scan of the unlock set).
- **Reliable-command budget (bug-670/1670):** the export is dirty-tracked and paced, and the first push happens in the
  lobby, never at a mission spawn burst.
- **Parse killers (T1):** `daily.scr` is new, so run all four scanners (depthscan2, linecheck, odd-quote, prosecheck)
  plus a server boot with `developer 1` and no `Couldn't compile` lines. Generated text is asserted ASCII with no
  `; " // | ~ ^`. The engine-new commands sit in `daily_clock.scr` only.
- **Mixed binaries:** a client on an old cgame just lacks the optional menu clock. A server on an old game.dll turns
  dailies off cleanly. Public servers run from `public_servers/` and block deploys, so plan the dll roll-out.
- **MP isolation:** `check_mp_isolation.py` must pass with the two new allowlist entries. `daily.scr` must not reach
  coop gameplay state.
- **`ui_addhud` while the HUD is hidden:** `menumirror.scr` notes that `drawhud 0` / `PMF_NO_HUD` hide every
  ui_addhud panel. Confirm the lobby player does not run with either (T3); the lobby already keeps
  `cg_huddraw_force 1`.
- **Gaming it:** a player cannot gain XP by editing his file (§3.2). Squad orders are team-bumped like their regular
  counterparts.

## 7. Test plan (existing harnesses)
- **T1 compile and clock:** a dedicated boot (`server_home`) prints `^~^~^ DAILY day=<D> row=<r> ids=...` and
  `reset_in=<s>`. Compare with the generator's `--day D` output for the same date.
- **T2 determinism:** two dedicated servers, one started with `TZ` set to a far zone, must print the same ids.
- **T3 lobby panel:** a listen host and a second-monitor test client (memory: test on the second monitor) at 4:3,
  16:9 and 21:9 captures; with the briefing showing 9 lines, there is no overlap with the briefing, roster or unlock
  list. Then a visual QA pass (no clipping, no gibberish text).
- **T4 progress and grant:** `coop_selftest_xp.scr`-style self-test (cvar-gated): force day D, bump each tier's stat to
  target - 1, then +1. Expect one XP award of the tier amount, the toast header, the debrief tally line, and the bonus
  on the 5th. Then repeat the +1 and expect **no** second payment.
- **T5 persistence:** finish an order on server A and join server B (the existing coopsync harness from bug-3903):
  the order is done and not paid again. Hand-edit an older-day value onto B and check the merge keeps the newer one.
- **T6 MP:** an MP round with `mp:` orders; check the file round-trip and the cap exemption.
- **T7 rollover:** set the clock helper's offset (a dev cvar read only by `daily_clock.scr`) so the reset falls
  mid-mission: progress keeps counting toward the old day, and the next lobby shows the new set.
- **T8 burst:** the bug-10495 harness, granting several dailies in one frame, must show no `Command overflow` and no
  hitch over 50 ms.
- **Maptest Phase 1 sweep** (54 maps, `coop_maptest 1`) with dailies on: no new Script Error lines.

## 8. Open questions for the user
1. On a day with an MP-only order, should the all-five bonus need **all 5**, or **the 4 your mode can do**? (Proposed:
   all orders your mode can complete, so coop-only players are not shut out.)
2. Reset at **10:00 UTC** (4 am Central): OK, or do you prefer midnight local of some reference zone?
3. XP levels (400 / 750 / 1250 / +1500): OK against the current ladder?
4. A v2 reroll (one free swap a day): yes or no?
