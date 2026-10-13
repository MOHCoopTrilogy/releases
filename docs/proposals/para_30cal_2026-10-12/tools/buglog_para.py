"""buglog_para.py - bug-3562: fill the OPEN entry in place (fix, verified_by, tags). Binary I/O, only that entry."""
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


FIX = ("NOT DEPLOYED. Mod coop-wip e40bfab8 (mod only): parasquad.scr findMgSpot plans A an object in the map (solid WORLD surface 22-56u, "
       "level, 12u deep, nothing on it) under the retail MG42 bipod, B the ground on Breakthrough's 49u tripod (three feet within 6u), "
       "C a non-solid 31u sandbag rest with the bipod (last resort, never on the Omaha maps); gun kept 38-76u over the gunner's feet "
       "(the engine's crouch/stand gun pose band), his seat swept with his hull, mgOpen keeps him out of doorways / corridors / "
       "trenches / stairs / edges, stepped set-down and pack-up, surface re-traced on arrival, a gunner the engine did not seat packs "
       "up at once, mgWalk falls back to a straight info_waypoint walk. New models/statweapons/coop_30cal_para.tik fires WaW30cal at "
       "firedelay 0.09 (retail 30cal.tik plays jeep_snd_fire = 50CalFire2.wav, a .50 cal recording, at the MG42's 0.06). "
       "anim/mg42_idle.scr: crouched traverse clips. Root cause of the floating gun: it was placed 14u SHORT of the cover and 12u "
       "above its top, nothing traced under it, bare-gun model. docs/proposals/para_30cal_2026-10-12/README.md.")
VER = ("Agent, harness G:/mohaa-hudfeed5, real C-47 sticks: m3l2 tripod (B) set up + fired in 3 sessions, packed up in 1; sandbag rest "
       "(C, forced on level ground) set up + fired + packed up in 5 sessions incl. the final script; 0 script errors; scanners clean; "
       "check_mp_isolation 22/22. NOT verified: mode A never completed (the m4l1 bank site is refused by the seat sweep - earlier "
       "builds left the gunner unseated there, hands on nothing); C's natural trigger; the Omaha ban (name test, not booted); the "
       "sound by ear; a second client. The walk-up still fails when he lands 350-600u away with no path (3 of the last 4 sessions).")
out, seen = [], set()
for ln in blk.split(nl):
    s = ln.strip()
    if s.startswith(b'"fix":'):
        out.append(line("fix", FIX) + b",")
        out.append(line("verified_by", VER) + b",")
        seen.add("fix")
    elif s == b'"open",':
        out.append(b'      "staged",')
        seen.add("tag")
    else:
        out.append(ln)
assert seen == {"fix", "tag"}, seen
final = raw[:i] + nl.join(out) + raw[j:]
json.loads(final.decode("utf-8"))
open(P, "wb").write(final)
print("bug-3562 updated, %+d bytes" % (len(final) - len(raw)))
