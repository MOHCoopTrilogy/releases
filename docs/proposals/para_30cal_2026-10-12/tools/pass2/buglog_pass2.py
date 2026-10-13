"""buglog_pass2.py - bug-3562: replace fix / verified_by / last_seen of that one entry in place (binary I/O, nothing
else in the file is touched), after the second pass (mod coop-wip 8a35ddcd)."""
import json
P = "C:/mohaa-coop-dev/.wolf/buglog.json"
raw = open(P, "rb").read()
i = raw.find(b'"id": "bug-3562"')
assert i > 0 and raw.count(b'"id": "bug-3562"') == 1
j = raw.find(b"\n  }", i)
blk = raw[i:j]
nl = b"\r\n" if b"\r\n" in blk else b"\n"


def line(key, val):
    return b'    "' + key.encode() + b'": ' + json.dumps(val, ensure_ascii=True).encode()


FIX = ("NOT DEPLOYED. Mod coop-wip e40bfab8 (first pass: traced supports, the .30 cal sample - coop_30cal_para.tik fires WaW30cal at "
       "firedelay 0.09 where retail 30cal.tik plays a .50 cal recording) + 8a35ddcd (second pass, user: 'go to the nearest existing "
       "cover he could prop it to with a bipod and suppress enemies or place the sandbag'): parasquad.scr mgPlan replaces findMgSpot - "
       "A existing world cover 21-53u high under the retail bipod (a window sill counts), C a closed three-bag sandbag rest only when no "
       "cover passes (never on a player's trail, ahead of the squad, in a gap, or on the five Omaha maps), tripod behind "
       "coop_paraMgTripod 1; every site needs a traced field of fire (mgFire), the engine's own seat free over the traverse (mgSeat), "
       "and a way there (mgReach: runto + pathdist, else a straight walk over traced ground). Walk-up root cause: "
       "PathSearch::NearestStartNode/NearestEndNode only look in the 256u map cell the man / goal is in - no pathnode there = no path "
       "at all; unreachable sites are now refused before he commits, and a stuck squad member walks out straight (walkOut). The "
       "rifleman (member 3) carries it, the BAR man keeps his BAR. A gunner killed at the gun leaves it with what was left of a "
       "250-round belt (coopammo) for the players. New generated models/static/coop_mg_bags.tik + scripts/coop_mgbags.shader "
       "(docs/tools/gen_coop_mgbags.py): the first pass's sandbag was the retail wall end cap, an open shell on a baked-vertex-light "
       "shader. Mod only, no engine change. docs/proposals/para_30cal_2026-10-12/README.md, section SECOND PASS.")
VER = ("Agent, harness G:/mohaa-hudfeed5 (integration binaries), real C-47 sticks. Second pass: cover = a window sill on m3l3, set up "
       "standing + packed up in 2 sessions (gunner stood near it by the test driver: that room has no pathnodes); sandbag rest on m3l2 "
       "in 3 sessions with real landings and path walks of 345 / 135 / 80u, and naturally on m3l3 in 2; gunner killed at the gun on "
       "m3l2: belt 241 left, a player mounted with Use, fired, emptied a 40-round test belt, dismounted and walked on; m3l1a: four "
       "searches, bags=0, nothing placed; an unreachable site refused 8 times; sandbag walk-round strip closed from 17 views; 0 script "
       "errors from this code; scanners clean; check_mp_isolation 22/22. NOT verified: a second client; a clean GIF; the gun firing "
       "from a cover site and the script suppression bursts (never ran); a crouched cover site; a player on the low gun seen in third "
       "person; the 15s re-site; the sound by ear. NOT done (handover in the README): grease gun, engine polish of the left gun, the "
       "tactical squad brain, landing without teleports.")
out, seen = [], set()
skip = False
for ln in blk.split(nl):
    s = ln.strip()
    if s.startswith(b'"fix":'):
        out.append(line("fix", FIX) + b",")
        seen.add("fix")
    elif s.startswith(b'"verified_by":'):
        out.append(line("verified_by", VER) + b",")
        seen.add("ver")
    elif s.startswith(b'"last_seen":'):
        out.append(line("last_seen", "2026-10-12T19:45:00-05:00") + (b"," if s.endswith(b",") else b""))
        seen.add("seen")
    else:
        out.append(ln)
assert seen == {"fix", "ver", "seen"}, seen
final = raw[:i] + nl.join(out) + raw[j:]
d = json.loads(final.decode("utf-8"))
assert len(d) == len(json.loads(raw.decode("utf-8")))
open(P, "wb").write(final)
print("bug-3562 updated, %+d bytes, %d entries" % (len(final) - len(raw), len(d)))
