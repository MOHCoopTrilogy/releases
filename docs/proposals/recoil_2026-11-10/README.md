# Per-gun recoil patterns (2026-11-10) - UNMERGED, awaiting playtest

User: "We can make recoil patterns realistic to their actual weapons." Follow-up: use measured data wherever it exists.

## What it is

Every gun gets a learnable, mostly deterministic recoil pattern: round N of a burst kicks the same way every time
(first-round kick, a climb that builds with the rate of fire and tapers once the stock is in the shoulder, a horizontal
drift and sway), with a little jitter. Server-authoritative: `Weapon::CoopApplyPatternKick` moves the real view after
the round has left (the shot goes where the crosshair was, the next where the climbed crosshair is). Recovery waits
while the burst runs; the player's own pull-down pays the climb off, so releasing never throws the sights under the
target; semi-autos, bolts and pistols recover between deliberate rounds (hold 0.06 s at fire delay >= 0.125 s).

Shooter terms kept from the authored kick (balance unchanged): `coop_recoilScale`, breath hold (`g_breathRecoilMult`),
brace / bipod (`coop_braceKick`, `coop_braceKickMG`). Added: stance `coop_recoilCrouch` 0.80, `coop_recoilProne` 0.55;
per-gun hip multiplier (x `coop_recoilHip` 1.0); climb ceiling `coop_recoilMaxClimb` 12. Hardcore touches none of this.

**Toggle: `coop_recoilPattern` (default 1, archived, server).** 0 = the previous authored kick exactly (A/B).
`coop_recoilDebug 1` prints `^~^~^ RECOILPAT` per kick and `^~^~^ RECOILSHOT` per round (real traced direction).

The camera: MOHAA fires along the CAMERA (`cg.refdefViewAngles` is sent as the eye angles), so the TIK `viewkick` was
real, random aim - on a Thompson it rode -4.8 deg above the server aim by round 10. While the server publishes
`coop_recoilPatOn 1` (stufftext, change-only + every 3 s, no protocol change) the cgame trims it to a punch:
`cg_recoilPatCam` 0.3 pitch, `cg_recoilPatCamYaw` 0.15, recentre >= 20 deg/s, no scatter, ceiling 2.5. Measured
after: vk 0.19 per round, gone in 2 frames; camera = aim between rounds. Never on a turret.

## Data (nothing hand-written into code)

* `docs/tools/recoil_research.tsv` - published specs per real gun, with sources.
* `docs/tools/recoil_measured.tsv` - per-figure MEASURED / DERIVED / ANECDOTAL rows with sources (Aberdeen 1942
  Thompson trials, Soviet Dec 1941 SMG trial, US ETO Ordnance Oct 1944 StG 44 report, Soviet MG 42 manual, ...).
  A MEASURED rate / weight / velocity / charge overrides the spec.
* `docs/tools/recoil_shape.tsv` - the authored part: stem -> physics row, class, magazine, stock line, device, hip,
  drift / sway / jitter, each with its basis ([M] measured, [D] derived, [A] anecdotal).
* `python docs/tools/gen_recoil_pattern.py build|check [--mod DIR]` -> `coop_mod/recoil_pattern.txt` (92 rows; finish
  variants share their base by suffix stripping) + `derived.tsv` + `RESEARCH.md` (the per-gun research table).
  `check` fails if the table is stale or any roster gun / recoil_table base has no row.

Directions from documents: PPSh-41 and MP 28 burst groups shift RIGHT (Soviet 1941 trial); StG 44 climbs (ETO 1944);
Thompson climb from the dropped stock (Aberdeen 1942: an in-line stock raised 50 yd hits 61 -> 81 pct; the Cutts gave
no net gain, smoke on the sights); Thompson up-and-right is ANECDOTAL only; FG 42: little climb in short bursts,
long bursts walk off (McCollum); MG 42: cone leaves the target after 7 rounds even from the bipod.

## Evidence

* `plots/pattern_sheet.png` - offline, the engine's own maths: 18 guns, aimed standing, no pull-down, game fire rates.
* `plots/pattern_stance.png` - hip / aimed / crouched / prone for Thompson, MP40, MG 42, Garand.
* `plots/pattern_single.png` - single rounds: kick and recovery (bolt, semi, pistol, shotgun).
* `impact/impact_sheet_on.png` - IN GAME, every round's server-traced direction from a fixed stand, drawn on a wall at
  10 m, 13 guns x hip / aimed / crouched / prone (`tools/run_recoil.py` + `tools/impact_sheet.py`, private client
  G:\mohaa-recoil, m5l1a). `impact/stills_*.jpg` - mid-burst aimed frames (sight-line lock) and the wall.

## In-game results (10 m wall; climb = highest round, metres; drift = last round, + right)

| gun | aimed | hip | crouched | prone | drift aimed |
|---|---|---|---|---|---|
| Thompson M1A1 | 1.66 | 1.91 | 1.49 | 1.07 | +0.35 |
| MP40 | 1.12 | 1.40 | 0.82 | 0.50 | -0.04 |
| PPSh-41 | 1.13 | 1.44 | 0.82 | 0.61 | +0.52 |
| Sten | 1.17 | 1.37 | 0.82 | 0.69 | -0.04 |
| BAR | 1.14 | 1.46 | 1.13 | 0.70 | +0.24 |
| StG 44 | 2.13 | 2.10 | 2.04 | 1.15 | -0.04 |
| Bren | 0.89 | 1.29 | 0.65 | 0.50 | -0.06 |
| MG 42 (70 rds) | 2.51 | 2.80 | 2.06 | 1.39 | +0.14 |
| Garand / Kar98k / Carbine / Colt (5 rds, 0.7 s apart) | 0.05 / 0.03 / 0.03 / 0.18 | | | | |

A/B with `coop_recoilPattern 0` (`impact/impact_sheet_off.png`): Thompson 3.71 m (same aimed / hip / crouched /
prone: the old model has no stance term), MP40 3.87, PPSh 2.09, MG 42 4.70 - it climbed about twice as far, mostly
through the random camera kick, and drifted LEFT. Aimed frames mid-burst keep the sights on the crosshair line
(`impact/stills_contact.jpg`). FG 42 not in the sheet: equipping it through the Armory crashes the server in v1.10.73
with the RELEASE dlls too (bug-10899, not this branch).

## Not done / open

* Game fire rates are the tiks' (`dm firedelay`): MP40 0.08 = 750 rpm (real 400-550), PPSh 0.09 = 667 rpm (measured
  1050). The pattern uses the real rate for how fast the climb builds; matching the tik rates to reality is a balance
  call left to the user.
* Remote clients see the server's kick one round trip late (as with the authored kick before it); not playtested in MP.
* Not felt by a human yet. Tune knobs: `scale` in recoil_shape.tsv per gun, `coop_recoilCrouch/Prone/Hip/MaxClimb`.

## Real rates of fire (user-approved 2026-11-10) - verified in game 2026-11-10

* `docs/tools/gen_weapon_rof.py build|check` -> `coop_mod/weapon_rof.txt` (35 automatics + 5 turret MGs) and `ROF.md` (the
  before / after table: rpm, damage, bullets, TTK at 100 and 50 HP, AI burst). Rates from the recoil research (measured beats
  spec); `weapon_rof_tune.tsv` holds the judgement (MP40 500 not the 400 impression, AI burst lengths, MG42 / M1919 one bullet
  a round, 'free' where today's TTK was an artifact); `weapon_rof_turrets.tsv` the turret MGs.
* Engine (`coop_realRof` 1, default; 0 = the tiks exactly): `Weapon::FireDelay` primary = the table's delay; the shot carries
  the TTK-holding damage scale and bullets per shot. AI: an animation `fire` command now stands for its slice of trigger time -
  as many rounds as the real rate allows, the rest queued at the real interval, capped at the gun's real burst length
  (`Sentient::CoopAiRofFire`). AI turret gunners (40 rounds a second before) fire at the gun's real rate with each round
  carrying the rounds it replaces (x2 MG 42, x2.5 cap). `coop_recoilDebug 2` prints every AI round.
* Damage: held inside +-20% of today's average TTK (100 HP) by the smallest integer per-shot change: MP40 24->29, Sten 20->26,
  MP 28 20->25, PPSh 24->20, MAB 38 20->22, Type 100 25->24; everything else unchanged.
* Armory: `gen_weapon_stats.py` applies the table, `gen_loadout.py build` regenerated the pages (rate / damage bars and
  compare deltas: 1,949 changed + 279 new generated cfgs, `gen_loadout check` EXACT). MP isolation 22/0.
* Recoil: the per-round pattern is unchanged (its climb build already used the real rate); per SECOND it now follows the real
  cadence - the MP40 climbs slower, the PPSh faster. The M3 (450 rpm, 0.133 s) is now treated as an automatic by the
  recovery (it recovered between rounds like a semi-auto at the old 0.125 s line).
* Semi-autos and bolts keep their tik delay: they have no cyclic rate; their delay is the trigger cap.
* To verify (harness ready: `tools/run_rof.py player|ai`): measured rpm from the server trace, player vs AI on the same gun,
  AI burst lengths, a co-op fight on a campaign map.

### In-game measurements (tools/run_rof.py, private client G:/mohaa-recoil, server round trace)

| gun | real rpm | player, before the cadence fix | player, final | AI, final (median in burst) | AI burst (final / before) |
|---|---|---|---|---|---|
| Thompson M1A1 | 667 | 600 | 663 | 600 | 6 / up to 155 (one held animation) |
| MP40 | 500 | 480 | 497 | 436 | 5 / up to 24 |
| PPSh-41 | 1050 | 800 | 1046 | - | - |
| Sten | 532 | 480 | 533 | - | - |
| M3 | 450 | 400 | 447 | - | - |
| BAR | 550 | 480 | 549 | - | - |
| StG 44 | 550 | 480 | 549 | 343 (before the mid-burst fix) | 4-5 / 23 |
| FG 42 | 750 | 600 | 748 | - | - |
| Bren | 520 | 480 | 517 | - | - |
| MG 42 (portable) | 1200 | 800 | 1200 | turret nest 1244 (was 2,400) | turret rhythm 20 |
| M1919 | 500 | 480 | 497 | - | - |

* Player rates were rounded UP to whole 25 ms server frames (every interval) until "keep the cadence" (Weapon::Fire): now all
  within 1%. AI SMG medians read 10-15 % low: the queued rounds still land on server frames and the bursts are only 5-6
  rounds long. AI bursts are now the real 4-7 rounds instead of whatever the animation held (a Thompson AI fired 155 rounds
  in one burst before).
* Co-op fight check, m3l3 with the map tester's patrol (5 min): no crash, AI MP40 241 rounds in 51 bursts of <= 5. One
  earlier m3l3 run stopped on `anim/shoot.scr took over 10 seconds` (engine Actor::State_Cover_Shoot watchdog) - a known
  crash class seen without this branch (bug-10935, Norway); the before run and the final after run did not hit it.
* Not felt by a human: whether AI pressure "feels right" needs a playtest.

## Merge

Engine `recoil-eng` (C:\hzm-recoil\eng, off rel-1.10.38-engine) -> cgame.dll + game.dll. Mod `recoil-mod`
(C:\hzm-recoil\mod, off hotfix-1.10.53): `coop_mod/recoil_pattern.txt`. Root `recoil` (C:\hzm-recoil\root, off main):
the sources, generator and this folder. `git merge` each into its release branch; no conflicts expected outside
weapon.cpp / player.cpp (new functions + 3 small hunks) and cg_commands.cpp EventViewKick (one block).
