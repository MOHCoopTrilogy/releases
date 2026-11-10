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

## Not done / open

* Game fire rates are the tiks' (`dm firedelay`): MP40 0.08 = 750 rpm (real 400-550), PPSh 0.09 = 667 rpm (measured
  1050). The pattern uses the real rate for how fast the climb builds; matching the tik rates to reality is a balance
  call left to the user.
* Remote clients see the server's kick one round trip late (as with the authored kick before it); not playtested in MP.
* Not felt by a human yet. Tune knobs: `scale` in recoil_shape.tsv per gun, `coop_recoilCrouch/Prone/Hip/MaxClimb`.

## Merge

Engine `recoil-eng` (C:\hzm-recoil\eng, off rel-1.10.38-engine) -> cgame.dll + game.dll. Mod `recoil-mod`
(C:\hzm-recoil\mod, off hotfix-1.10.53): `coop_mod/recoil_pattern.txt`. Root `recoil` (C:\hzm-recoil\root, off main):
the sources, generator and this folder. `git merge` each into its release branch; no conflicts expected outside
weapon.cpp / player.cpp (new functions + 3 small hunks) and cg_commands.cpp EventViewKick (one block).
