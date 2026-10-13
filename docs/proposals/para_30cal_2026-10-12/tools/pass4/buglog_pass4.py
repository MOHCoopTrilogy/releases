"""buglog_pass4.py - append the fourth-pass entries of the paratrooper squad to .wolf/buglog.json. Binary append in front
of the closing bracket (the file is mixed LF / CRLF: nothing else is touched); ids are taken from the tail at run time."""
import json, re, time
P = "C:/mohaa-coop-dev/.wolf/buglog.json"
raw = open(P, "rb").read()
ids = [int(m) for m in re.findall(rb'"id": "bug-(\d+)"', raw[-200000:])]
nxt = max(ids) + 1
TS = time.strftime("%Y-%m-%dT%H:%M:%S-06:00")
COMMITS = "mod coop-wip b8c330ff + e277c9bb + 60bc2ca7 + 237adcc2 (NOT DEPLOYED)"
E = [
    ("Paratrooper .30 cal: firing up at windows, the gunner's hand is at his helmet - the grips ~8 u from his hands at 12 degrees of pitch",
     "coop_mod/parasquad.scr",
     "Actor::ThinkHoldGun_TurretGun holds the hands 39 u behind the pivot ON THE GUN'S PITCHED LINE and blends stand / crouch by the grip height - "
     "the pose does follow pitch, but the crouched pose is the floor (hands 38.7 u over his feet). A gun 39.3 u high pitched up takes the grips "
     "39 x sin(pitch) under that: 8 u at 12 deg, 13 u at 20. Not an engine bug; the third pass read it as 'the pose does not follow the pitch'.",
     "mgPivot (script only, works on any game.dll): every frame while somebody is on the gun it is lifted by what is missing below the crouch floor, "
     "the bipod going up with the barrel; pitched down, or on a gun high enough for the blend, nothing moves. A player on the lowest guns (one clip, "
     "no blend) is followed down too. pitchCaps -25 / 12. " + COMMITS,
     "Harness, m3l2 sandbags (run t7) and m3l3 48 u sill (run u2), AI and player, side stills at 0 / +12 / +20 / +25 / -10 deg: hands on. OPEN: a "
     "PLAYER on a gun 45-66 u high (the sill) has one clip - hands ~10 u over the grips, as before this pass.",
     ["paratrooper", "turret", "pitch", "pose", "parasquad"]),
    ("User: 'when no one is using that 30 cal it should be facing upward right' - the level rest (cooprestpitch 3) was wrong for an unmanned bipod gun",
     "coop_mod/parasquad.scr",
     "The third pass and the engine key set a level rest. The engine's own butt drop (TurretGun::ThinkIdle) is not usable either: it tests a point "
     "56 u back on the BORE LINE; this model's stock corner is 63.4 u back and 8.2 u under it, so the drop stops 13 deg late with the stock 11 u in the ground.",
     "mgRest: the pitch at which the underside of the gun meets the world (2 deg steps of a traced line, 60 max): 30 deg on the sandbags, 44 on a 48 u "
     "sill. cooprestpitch through parasquad_gun.scr::rest, maxIdlePitch on an older game.dll. The gun is level while it is set down and before a "
     "trooper takes it (mgMount); a player's Use snaps it to his view in one frame (retail). " + COMMITS,
     "Harness: rest after the gunner's death and after a player got off, m3l2 bags (-30) and m3l3 sill (-44), stills from the side. The old-DLL "
     "maxIdlePitch branch was run (o1) but its rest not looked at.",
     ["paratrooper", "turret", "rest", "user-correction", "parasquad"]),
    ("Paratroopers and grenades: the mounted gunner sat through a grenade; in the harness a man on foot did not move either",
     "coop_mod/parasquad.scr",
     "type_grenade 'machinegunner' does nothing for an American (Think_MachineGunner_TurretGun returns early for TEAM_AMERICAN); a man on foot with "
     "gren_awareness 90 stayed in think=idle for a laid stick grenade that sent ai_event grenade twice a second (test set-up; a thrown one not tried).",
     "nadeWatch, one thread a squad: the entity table 64 slots a frame; a Projectile at rest within 300 u of a man - the gunner leaves the gun and "
     "comes back (mgFlee), a man on foot runs 300 u over looked-at ground (nadeRun). The squad's own grenade for 6 s only moves a man within 150 u. " + COMMITS,
     "Harness m3l2, laid grenade 110 u from the gunner: runs e3, e5 back=1 (he re-manned). Unassisted, m4l3 run c2: a grenade came to rest 90 u from "
     "the mounted gunner in a real fight, he left and re-manned (back=1).",
     ["paratrooper", "grenade", "parasquad"]),
    ("mgFlee first version: the gunner came back to the gun and stopped 25-38 u short of the seat, the gun was given up (back=0)",
     "coop_mod/parasquad.scr",
     "The gun lies on its butt when nobody holds it and the turret is solid: its stock is on the ground where he has to kneel. Same geometry at the "
     "set-down: the butt would come down into the standing gunner's leg.",
     "The gun is levelled (mgRestSet 0) when he is within 110 u, then the last steps; it is level for the whole set-down. " + COMMITS,
     "Runs e3, e5, c2: back=1.", ["paratrooper", "turret", "parasquad"]),
    ("Whole squad teleported 8000 u to a player hanging 3000 u over the map: 18 teleports in 45 s (rescue why=fell, vetted=0)",
     "coop_mod/paradrop.scr",
     "coop_paradrop_landing_check reads 'fell out of the world' as 1200 u under the NEAREST PLAYER. The test flew its player 3000 u up; in the game a "
     "spectator flies the same way and can be the nearest player to a squad that holds far from the living ones.",
     "A spectator is not counted as the nearest player. " + COMMITS,
     "Player 8000 u away at the squad's own height for 45 s (run e5): 0 teleports, 0 rescues. A real spectator was NOT run (one client).",
     ["paratrooper", "teleport", "spectator", "paradrop"]),
    ("m2l1, drop called at the players' first road: four of five paratroopers came down on the cliff tops (154-662 u up), one rescue teleport, two men left up there",
     "coop_mod/paradrop.scr",
     "No path network there: coop_para_lz tested 21 points and none had a path, so lz plan n=0 and every man came down with the old scatter.",
     "A man without a path-connected point gets a point that passed everything else (level, open sky, the squad's height). " + COMMITS,
     "Run r5: lz plan n=5 ground_only=5, five landings within 8 u of the call height and 120-240 u from it, 0 teleports, 0 script errors.",
     ["paratrooper", "landing", "m2l1", "paradrop"]),
    ("A player took the left .30 cal and stood upright behind the sandbag gun, hands in the air, a trooper inside him (run t6)",
     "coop_mod/parasquad.scr",
     "A squad mate stood on the gun's seat. TurretGun::P_ThinkActive does not seat a player into a solid, and CoopUserLow traced the 'ground' on the "
     "mate's head: not a low gun, standing clip.",
     "mgSeatClear: while nobody is on a set-up gun, a squad member within 40 u of its seat who is nobody's steps 90 u back. " + COMMITS,
     "Run t7: player kneeling, hands on - but no mate stood on the seat in that run: the rule did not fire, NOT shown by a positive case.",
     ["paratrooper", "turret", "player", "parasquad", "unverified"]),
    ("Harness: 'No space left on device' on G: twice (2026-10-12 23:5x, 2026-10-13 07:46) - sessions died at boot",
     "docs/proposals/para_30cal_2026-10-12/tools/pass4/p3lib.py",
     "G: (every lane's harness copies and run folders) was at 0 bytes free.",
     "Finished run folders of G:/mohaa-hudfeed5/runs moved (copied, file counts compared, then the source removed) to the session scratchpad "
     "para4/runs_moved_from_G_hudfeed5 (3.4 GB); p3lib writes new runs to scratchpad para4/runs.",
     "", ["harness", "disk"]),
    ("p3lib.py broken by a patch written through a Git-Bash heredoc: backslash-n inside a Python string became a real newline (SyntaxError)",
     "docs/proposals/para_30cal_2026-10-12/tools/pass4/p3lib.py",
     "The known heredoc trap (memory: heredoc-escape-gotcha), walked into again.",
     "Patch scripts written with the Write tool only from there on.", "", ["harness", "heredoc", "repeat"]),
]
out = b""
got = []
for (msg, f, cause, fix, ver, tags) in E:
    d = {"id": "bug-%d" % nxt, "timestamp": TS, "error_message": msg, "file": f, "root_cause": cause, "fix": fix}
    if ver:
        d["verified_by"] = ver
    d.update({"tags": tags, "related_bugs": ["bug-3562"], "occurrences": 1, "last_seen": TS})
    body = json.dumps(d, indent=4, ensure_ascii=True)
    body = "\n".join("  " + l for l in body.split("\n"))
    out += b",\n" + body.encode()
    got.append(d["id"])
    nxt += 1
k = raw.rfind(b"\n]")
assert k > 0 and raw[k - 1:k] == b"}"
new = raw[:k] + out + raw[k:]
json.loads(new.decode("utf-8"))
open(P, "wb").write(new)
print("appended", got[0], "..", got[-1])
