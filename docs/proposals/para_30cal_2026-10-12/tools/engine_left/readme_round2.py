"""readme_round2.py - replace the tail of the proposal README (from '## A player on a low gun in third person') with the
round-2 text. One-shot; refuses to run twice."""
P = "C:/mohaa-coop-dev/docs/proposals/para_30cal_2026-10-12/README.md"
raw = open(P, "rb").read()
nl = b"\r\n" if b"\r\n" in raw else b"\n"
key = b"## A player on a low gun in third person (looked at, not fixed)"
assert raw.count(key) == 1
head = raw[:raw.index(key)]
NEW = r"""## Round 2 (engine `277bdb9d`, mod `coop-wip` `7ca17790`)

### bug-3639: the trigger held on an empty belt heats no belted gun

The empty test is one branch in front of the heat branches now, for every belted gun. Measured on a retail
`models/statweapons/mg42_gun.tik` with `coopammo 300`, player on it, this build (runs c1, c2) against the previous one
(`92944d37`, run c0):

| | this build | previous build |
|---|---|---|
| trigger held from cold, rounds in the belt | cooked after 2.0 s, 31 rounds (15.5 / s) | 1.9 s, 30 rounds (15.8 / s) |
| after the cook-off | no round for 2.0 s; cold 9.0 s after it | 2.0 s; 9.0 s |
| belt 3, trigger held 3 s | heat peaked **7-8** (the three rounds) and fell to 0, no cook-off | heat **98.75**, cooked off |
| text | "BELT EMPTY - resupply from an ammo box", centre print | the same |

(1.9 / 2.0 s and 30 / 31 rounds are the 0.1 s sampling: run b1 of this build read 1.9 s and 30.) One difference in
when the text shows, by the code and not measured: it is now also sent while the gun is in its 2 s dead time after a
cook-off.

### bug-3658: a player on a LOW gun crouches behind it

**What decides "low":** the AI gunner's own test (`Actor::ThinkHoldGun_TurretGun`): crouch weight
w = (71.8 - h) / 33.1 for a gun h over the ground the man is held on, crouched at w >= 0.5 - a gun **under 55.25 u**.
Decided once per mount (`Player::EnterTurret` -> `TurretGun::CoopUserLow`). Coop missions only; never a vehicle or a
portable turret; `coop_turretCrouch 0` switches it off; `developer 1` prints `TURRETSEAT enter / exit`.

**What a low gun changes:** hull 54, view height 48 (put back exactly in `ExitTurret`), the AI's crouched seat
(62.4 - 3.0 w back and 10.3 - 1.6 w to the left of the gun, where the standing player is 64 back and 0 left), and
the condition `COOP_TURRET_LOW` for the state files.

**Where the pose really comes from - not the legs states.** The first report above was wrong, and so were bug-304 and
bug-309 before it: on a ground turret the legs states `COOP_TURRET_MAN` / `TURRET_USING` are never evaluated. The
torso state `TURRET_IDLE` is `movetype anim`, `Player::EvaluateState` runs the legs machine only under
`MOVECONTROL_LEGS`, and the debug line the engine already prints says so (`TURRETSTATE legs='STAND'`, once, and never
another). The whole body is the TORSO state's action row (`turret_idle` = the retail `mg42_stand_idle`), chosen once
on entering the state. So the mod commit has: the two aliases (`anims_shared.txt`), the crouched idle row in
`player_Torso.st` `TURRET_IDLE`, a new torso state `TURRET_FIRE_LOW` for the firing clip, and the crouch rows in the
two legs states as asked (dead on a ground turret, commented as such).

**Ship the mod commit and the engine together**: the state file names a condition an older `game.dll` does not have.
The other way round (new `game.dll`, old state file) was not run; by construction it gives the crouched hull and
seat with the standing clip.

Seen in engine (m3l2, run c2 = this build + the mod files, run c0 = the previous build + the deployed state files):

| | low gun (.30 cal, 40.1 u) | standing height (retail MG42 at 60.1 u; the map's own `scene7_mg1` at 61.9 u) |
|---|---|---|
| `TURRETSEAT enter` | `low=1 crouch=0.96 maxsz=54 view=48 psview=48` | `low=0 crouch=0.00 maxsz=94 view=82 psview=82` |
| seat | (-3651.642 2246.965) = the AI gunner's seat on the same gun in run a3, to the unit | the same origin as the previous build, to the unit (both guns) |
| third person | kneeling behind the gun, hands on it, front foot behind the bags; the firing clip with the trigger (before: upright, hands in the air over the gun) | the same frame as the previous build: mean absolute difference 0.0-0.1 of 255 (`scene7_mg1`, both sides) |
| first person | the same frame as the previous build (difference 0.5 of 255) | `scene7_mg1`: difference 1.0 of 255 |
| off it with Use | `TURRETSEAT exit maxsz=94 view=82 psview=82`, hull read back 94, walked away | hull 94 |
| the gun removed under him | exit 94 / 82 / 82, `turret=none`, hull 94 | |
| killed on it | exit 94 / 82 / 82, then the ordinary dead hull (32) | |

**First person needed nothing.** With `g_turretcameras 1` (the mod's setting) the view on a turret is the turret's own
camera, at the gun's origin + its `viewOffset` (-42 0 10): 50 u over the ground on this gun, looking along it, whatever
the body does. The crouched view height (48) is what the third-person camera and anything aiming at his eyes use.

**The 64 u hold distance:** on the crouched seat (59.5 u back for this gun) his front foot is clear of the bags in
the side stills (they reach 16.5 u back from the gun). Nothing sits inside them.

Stills (`media/`, all QA'd at full size): `eng_low_side_before.jpg` / `eng_low_side_after.jpg` (from his left, the
whole man), `eng_low_side_fire.jpg` (from his right, firing; the dark patch on the ground is in this frame only -
probably the muzzle flash's own shadow, not checked), `eng_low_first_person.jpg`, `eng_nest_side_before.jpg` /
`eng_nest_side_after.jpg` (the map's `scene7_mg1`). The side view is a test camera: a script `Camera` whose angles
point across the gun - in third person on a turret the client chases the player along the camera's angles.

**Not verified / to know:**

- **Map guns under 55.25 u now crouch the player too** - that is the rule as asked. m3l2 has two: `scene4_mg42`
  (38.9 u over the ground behind it) and `scene11_mg2` (54.9 u). Neither was mounted. The AI blends between the two
  poses by height; a player gets one or the other, so on a gun between about 45 and 55 u the full crouch puts the
  hands up to half a blend (some 15 u) under the gun.
- A second client watching him, a dedicated server, the pose after a map restart: not run. The pose is an ordinary
  player animation and an ordinary hull, nothing new goes over the wire.
- Leaving a low gun under a ceiling too low to stand under: not tried (he gets the standing hull back regardless).
- Test set-up in these runs: every actor on the map removed (friendly ones walk into the frame), the player made
  undamageable for the stills (something on m3l2 kills a man standing at `scene7_mg1` within seconds), the gun's
  traverse locked to 0 for the side views (the gun follows the test camera's angles otherwise).

Tools: `tools/engine_left/` - `lg_run.py` (round 1), `lg_run2.py` (round 2: `c2 new`, `c0 old mg42,nest,low`),
`lg_drv.scr`, `lg_lib.py`, `patch_lowgun_mod.py` + `patch_lowgun_torso.py` (how the mod files were edited),
`logs/result_c2_new.json`, `logs/result_c0_previous_build.json`.
"""
out = head + NEW.replace("\n", nl.decode()).encode("utf-8")
open(P, "wb").write(out)
print("ok", len(out))
