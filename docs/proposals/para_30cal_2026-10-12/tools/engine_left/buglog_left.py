"""buglog_left.py - append the engine-side entries of the paratroopers' left .30 cal to .wolf/buglog.json (binary I/O,
nothing else in the file is touched; ids are taken from the tail at run time because other sessions append too).
Usage: python buglog_left.py <engine commit hash>"""
import json, re, sys
P = "C:/mohaa-coop-dev/.wolf/buglog.json"
COMMIT = sys.argv[1] if len(sys.argv) > 1 else "uncommitted"
TS = "2026-10-12T20:15:00-06:00"
raw = open(P, "rb").read()
assert raw.rstrip().endswith(b"]")
ids = [int(x) for x in re.findall(rb'"id": *"bug-(\d+)"', raw)]
nxt = max(ids) + 1
if b"coopnoresupply" in raw:
    sys.exit("already logged")
VER = ("Agent, harness G:/mohaa-hudfeed3 (exe + gl2 of the integration set, game.dll + cgame.dll built from game1-next), m3l2, "
       "overlay driver docs/proposals/para_30cal_2026-10-12/tools/engine_left (lg_run.py a3, result.json in G:/mohaa-hudfeed3/runs/lg_a3). ")
E = [
    {
        "error_message": "left .30 cal (parasquad.scr mgLeft): the empty text is the engine's 'BELT EMPTY - resupply from an ammo box' although nothing refills this gun; no dry click; the heat numbers are the MG42's, hard-coded",
        "file": "openmohaa-hzm/code/fgame/weapturret.cpp",
        "root_cause": "the belt (bug-1825) was written for the m3l3 church MG42s, which the ammo box tops up: one text, a centre print re-sent every frame the trigger is held, no sound, and the five heat rates (50 heat, 8 bleed, 25 cool, 2 s lock, 125 hot) were literals in P_ThinkActive and AI_DoFiring",
        "fix": "game1-next " + COMMIT + ": per-gun events on TurretGun, all off / at the MG42's numbers by default - coopnoresupply 1 (the empty line is 'Belt empty' through G_CoopFeedPrint cat 2 key mgbelt, the centre print only for a cgame without the feed or under Hardcore), coopdrysound <alias> (once per trigger pull; bar_snd_noammo resolves on every map), coopheatrates heat bleed cool lock [hot], and the getters .coopammo .coopheat .coopoverheated. A gun with either of the first two takes the empty trigger before the heat branches, so it does not heat. No cgame change, no new stat: the HUD still reads STAT_MGHEAT. parasquad.scr has to set the keys (README, ENGINE SIDE OF THE LEFT GUN).",
        "tags": ["engine", "turret", "belt", "overheat", "feed", "parasquad", "30cal"],
        "verified_by": VER + "Heat 40 8 25 2: a held trigger cooks in 2.5 s / 24 rounds (control without the keys: 1.9 s / 19), dead 2.0 s, fires again while hot, cold 4 s after release. Empty: three pulls = three 'FEED cat=2 key=mgbelt Belt empty' lines, no alias error; with a made-up alias three pulls = three 'Entity::Sound: ... needs an alias' errors; heat fell at 8 / s while the trigger was held on the empty belt. Hardcore (run a2): the centre print 'Belt empty'. The click was not listened to.",
    },
    {
        "error_message": "left .30 cal: once nobody is on it the gun idles with its barrel about 45 degrees up",
        "file": "openmohaa-hzm/code/fgame/weapturret.cpp",
        "root_cause": "TurretGun::ThinkIdle is the retail butt drop: the pitch falls until a trace from the origin to idleCheckOffset (56 u behind the gun) meets the world or 80 degrees. On a sandbag rest the gun is 40 u up, so the butt reaches the ground at asin(40/56) = 45.6 degrees",
        "fix": "game1-next " + COMMIT + ": cooprestpitch <deg> (event, per gun): ThinkIdle eases the pitch to it from either side (5 x the error per second, never under 12 deg / s) instead of dropping the butt. Unset = retail.",
        "tags": ["engine", "turret", "idle", "parasquad", "30cal"],
        "verified_by": VER + "Control: rest pitch -45.56. cooprestpitch 3: 3.0 from spawn; left looking 32.6 up -> 3.0 in 0.8 s (-20.9 -11.0 -5.2 -1.8 0.2 1.4 2.6 3.0 at 0.1 s steps), 35.1 down -> 3.0 in 0.8 s; 3.0 within 0.5 s of the AI gunner's death. Stills a3_old_rest.jpg / a3_new_rest.jpg / a3_death_rest.jpg.",
    },
    {
        "error_message": "left .30 cal: the AI gunner's shots are not counted (the script reckons 11 rounds a second), and there is no getter for belt / heat",
        "file": "openmohaa-hzm/code/fgame/weapturret.cpp",
        "root_cause": "the belt was only decremented in P_ThinkActive. And the script's 11 / s was wrong by four: TurretGun::AI_DoFiring (the non-MOH path) calls Fire() every server frame of a burst and Fire() has no fire-delay test, so an AI gunner's cyclic rate is sv_fps - 40 rounds a second on a live server (measured on the .30 cal, firedelay 0.09: 250 -> 172 in 2 s). True of every AI-manned TurretGun, the maps' MG42 nests included",
        "fix": "game1-next " + COMMIT + ": coopaibelt 1 (event, per gun): the AI's burst fires at the gun's own firedelay (ReadyToFire), each round is taken off the belt at the shot itself (CoopShoot wraps Weapon::Shoot - Fire() calls are not rounds), and at 0 the gun does not fire whatever the tracker or a script startfiring asks. Getters .coopammo .coopheat .coopoverheated. The MG42 nests are NOT changed (they were tuned at one round a frame).",
        "tags": ["engine", "turret", "ai", "belt", "firedelay", "sv_fps", "parasquad", "30cal"],
        "verified_by": VER + "24 s of the turret's own track cycle at three riflemen: belt 241 -> 158 = 83, and 83 'FIREDBG SHOOT .30 Cal' lines; 10.0 rounds / s inside a burst (before the firedelay gate, run a2: 158 = 158 and 40 / s); belt set to 15 under a script startFiring: 15 shoot lines, then 0 in the next 10 s, belt 0, heat 0. After his death .coopammo read 103 and a player's Use mounted it and fired 102 -> 88.",
    },
    {
        "error_message": "a belted MG42 (m3l3 church guns, coopammo) heats to a cook-off while the trigger is held on an EMPTY belt, and the 'BELT EMPTY' centre print is re-sent every other frame",
        "file": "openmohaa-hzm/code/fgame/weapturret.cpp",
        "root_cause": "P_ThinkActive adds the frame's heat before the belt test inside the same branch, and the belt test only clears m_iFiring, which P_UserAim raises again on the next command while the button is down",
        "fix": "OPEN - found while measuring the control gun, left as it is (the task: do not change the maps' own MG42s). The branch that fixes it exists (the left .30 cal takes the empty trigger before the heat branches, once per pull); dropping its opt-in test (m_bCoopNoResupply || m_sCoopDrySound) applies it to every belted gun.",
        "tags": ["engine", "turret", "belt", "overheat", "m3l3", "open"],
        "verified_by": VER + "Control gun (no new key), belt 3, trigger held 3 s: heat 98.75 with the belt at 0.",
    },
]
out = b""
for k, e in enumerate(E):
    d = {"id": "bug-%d" % (nxt + k), "timestamp": TS}
    d.update({x: e[x] for x in ("error_message", "file", "root_cause", "fix", "tags")})
    d["related_bugs"] = ["bug-1825", "bug-3562"]
    d["occurrences"] = 1
    d["last_seen"] = TS
    d["verified_by"] = e["verified_by"]
    body = json.dumps(d, indent=2, ensure_ascii=True)
    out += b",\n" + b"\n".join(b"  " + ln.encode() for ln in body.split("\n"))
i = raw.rstrip().rfind(b"}")
final = raw[:i + 1] + out + b"\n]\n"
a, b = json.loads(raw.decode("utf-8")), json.loads(final.decode("utf-8"))
assert len(b) == len(a) + len(E) and b[:len(a)] == a
open(P, "wb").write(final)
print("appended", [x["id"] for x in b[-len(E):]])
