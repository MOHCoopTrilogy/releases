"""buglog_left2.py - round 2 of the engine side of the left .30 cal: (1) bug-3639 goes from OPEN to fixed (fix /
verified_by / last_seen / tags of that one entry replaced in place), (2) one new entry for the crouched manning pose on
a low gun, id taken from the tail at run time (other sessions append too). Binary I/O; nothing else is touched.
Usage: python buglog_left2.py <engine commit> [<mod commit>]   - prints the id it took."""
import json, re, sys
P = "C:/mohaa-coop-dev/.wolf/buglog.json"
ENG = sys.argv[1]
MODC = sys.argv[2] if len(sys.argv) > 2 else "(not committed yet)"
TS = "2026-10-12T20:45:00-06:00"
raw = open(P, "rb").read()
if b"COOP_TURRET_LOW" in raw:
    sys.exit("already logged")
before = json.loads(raw.decode("utf-8"))
VER = ("Agent, harness G:/mohaa-hudfeed3, m3l2, overlay driver docs/proposals/para_30cal_2026-10-12/tools/engine_left "
       "(lg_run2.py: c2 = this build + the mod's state files, c0 = the previous build 92944d37 + the deployed state files). ")

# ---- (1) bug-3639 in place
i = raw.find(b'"id": "bug-3639"')
assert i > 0 and raw.count(b'"id": "bug-3639"') == 1
j = raw.find(b"\n  }", i)
blk = raw[i:j]
nl = b"\r\n" if b"\r\n" in blk else b"\n"


def line(key, val):
    return b'    "' + key.encode() + b'": ' + json.dumps(val, ensure_ascii=True).encode()


FIX = ("game1-next " + ENG + ": the empty-belt test is one branch in FRONT of the heat branches for every belted gun "
       "(TurretGun::P_ThinkActive): the gun is not firing, so the barrel cools. TurretGun::CoopDryPull gives the line: a gun "
       "the ammo box refills keeps its centre print 'BELT EMPTY - resupply from an ammo box', re-sent on every frame the "
       "trigger is held as before (it now also shows during the 2 s dead time after a cook-off); the dead copies of the test "
       "inside the two firing branches are gone.")
V39 = (VER + "Retail models/statweapons/mg42_gun.tik, coopammo 300, player on it. With rounds in the belt, this build / the "
       "previous one: cooked after 1.9-2.0 s and 30-31 rounds (15.5-15.8 a second) / 1.9 s and 30 rounds, no round for 2.0 s / "
       "2.0 s, cold 9.0 s / 9.0 s after the cook-off. Belt 3, trigger held 3 s: heat peaked 7.1-8.4 and fell to 0, no cook-off "
       "/ 98.75 and a cook-off. The centre print is in the log in both.")
out, seen = [], set()
for ln in blk.split(nl):
    s = ln.strip()
    if s.startswith(b'"fix":'):
        out.append(line("fix", FIX) + (b"," if s.endswith(b",") else b""))
        seen.add("fix")
    elif s.startswith(b'"verified_by":'):
        out.append(line("verified_by", V39) + (b"," if s.endswith(b",") else b""))
        seen.add("ver")
    elif s.startswith(b'"last_seen":'):
        out.append(line("last_seen", TS) + (b"," if s.endswith(b",") else b""))
        seen.add("seen")
    elif s == b'"open"':
        out.append(ln.replace(b'"open"', b'"fixed"'))
        seen.add("tag")
    else:
        out.append(ln)
assert seen == {"fix", "ver", "seen", "tag"}, seen
raw = raw[:i] + nl.join(out) + raw[j:]

# ---- (2) the new entry
nxt = max(int(x) for x in re.findall(rb'"id": *"bug-(\d+)"', raw)) + 1
d = {
    "id": "bug-%d" % nxt,
    "timestamp": TS,
    "error_message": "a player on the LOW .30 cal a paratrooper leaves (gun 40 u up on a sandbag rest) stands upright behind a knee-high gun in third person, hands in the air over it",
    "file": "openmohaa-hzm/code/fgame/player.cpp",
    "root_cause": "a player on any ground TurretGun gets one pose, the retail standing clip (player_Torso.st TURRET_IDLE action turret_idle = mg42_stand_idle), a standing hull and a seat 64 u straight behind the gun, whatever the gun's height; an AI gunner is blended to a crouch by the gun's height (Actor::ThinkHoldGun_TurretGun). And the place everyone looked was wrong (bug-304, bug-309, this session's first report): the legs states COOP_TURRET_MAN / TURRET_USING are never evaluated on a ground turret - TURRET_IDLE is `movetype anim`, and Player::EvaluateState runs the legs machine only under MOVECONTROL_LEGS - so the TORSO state's action row is the whole body, and it is chosen once, on entering the state",
    "fix": ("engine game1-next " + ENG + ": Player::EnterTurret asks TurretGun::CoopUserLow (the AI's test: crouch weight (71.8 - h) / 33.1 "
            "of 0.5 and over = a gun under 55.25 u over the ground he is held on) once per mount; low = hull 54, view height 48, the "
            "AI's crouched seat (62.4 - 3.0 w back, 10.3 - 1.6 w left), condition COOP_TURRET_LOW; ExitTurret puts back the hull and "
            "view heights he had (Use, killed on it, the gun removed under him). Coop missions only, not vehicle or portable turrets; "
            "coop_turretCrouch 0 = off. Mod coop-wip " + MODC + ": aliases coop_turret_crouch_idle / _fire (retail MG42_crouch_idle_a(loop) / "
            "MG42_crouch_shooting), player_Torso.st TURRET_IDLE crouched idle row + new state TURRET_FIRE_LOW, and crouch rows in the two "
            "turret legs states (not evaluated on a ground turret; kept for the day they are). SHIP TOGETHER: the state file names a "
            "condition an older game.dll does not have."),
    "tags": ["engine", "mod", "turret", "statemap", "torso", "third-person", "parasquad", "30cal"],
    "related_bugs": ["bug-304", "bug-309", "bug-3562", "bug-3636"],
    "occurrences": 1,
    "last_seen": TS,
    "verified_by": (VER + "Low gun (40.1 u): TURRETSEAT enter low=1 crouch=0.96, hull 54, view 48 / 48, seat = the AI gunner's own seat "
                    "to the unit; side stills: kneeling behind the gun, hands on it, clear of the bags (before: upright, hands over it); "
                    "the firing clip plays with the trigger. Off it by Use, by removing the gun, by death: TURRETSEAT exit hull 94, view "
                    "82 / 82 each time (then the dead hull 32 after the death), and he walked away. First person: the same frame as "
                    "before (mean abs difference 0.5 of 255) - it is the turret camera on the gun. Standing height: a retail MG42 at "
                    "60.1 u and the map's own scene7_mg1 at 61.9 u: low=0, hull 94, view 82, the same seat to the unit as the previous "
                    "build, side stills the same frame (mean abs difference 0.0-0.1). Not run: a second client watching, a dedicated "
                    "server, a gun between 45 and 55 u (the full crouch there is about half a blend low), the m3l2 map guns that ARE "
                    "under 55.25 u (scene4_mg42 38.9, scene11_mg2 54.9 - they now crouch the player too)."),
}
body = json.dumps(d, indent=2, ensure_ascii=True)
k = raw.rstrip().rfind(b"}")
final = raw[:k + 1] + b",\n" + b"\n".join(b"  " + ln.encode() for ln in body.split("\n")) + b"\n]\n"
after = json.loads(final.decode("utf-8"))
assert len(after) == len(before) + 1
assert [x["id"] for x in after[:len(before)]] == [x["id"] for x in before]
changed = [x["id"] for x, y in zip(before, after) if x != y]
assert changed == ["bug-3639"], changed
open(P, "wb").write(final)
print("updated bug-3639; appended", d["id"])
