"""buglog_add.py - append (or rewrite) this work's entry in .wolf/buglog.json by text surgery at the end of the array.
The id is taken as max+1 at the moment of writing; run again with the printed id to rewrite the same entry."""
import json, re, sys, time
P = r"C:\mohaa-coop-dev\.wolf\buglog.json"
MARK = "rainfix_2026-10-13"
ENTRY = {
    "id": None,
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S-06:00"),
    "error_message": "User, on the build deployed 2026-10-13: \"confirmed the downpour weather works but the rain doesnt really go to the ground, it stays closer to the top of the screen\"",
    "file": "openmohaa-hzm code/cgame/cg_nature.cpp, cg_beam.cpp, cg_commands.h (branch rainfix-next)",
    "root_cause": "A rain streak is drawn from the drop (its head) back UP its path for rain_length units (BEAM_INVERTED_FAST), and the whole beam was removed the moment the head reached the surface the drop lands on (the wall clamp cuts the path at the first solid and scales the life). So over the last streak-length above the ground the rain thins to nothing: measured on m3l2, standing in the yard, the top of a streak is still 233 units over the ground when the streak is removed (downpour, length 260; 95 with ordinary rain, length 90), streak cover per 32-unit height band rises in a straight line from 0 at the ground to full at one streak length, and in the level view the lower half of the screen holds 0.0-0.1 % streak pixels against 11-13 % in the upper tenths. Old fault (the wall clamp), made plain by the downpour tier's 260-unit streaks. None of the suspects changes the shape when switched one at a time: coop_rainEndGate, coop_rainByTime, coop_rainNearCull, coop_rainSeed, coop_rainSeeOut, the rain shader's depth test. Second, separate fault found on the way: the brushless rain's drops are removed 256 units below the eye whatever is under them, so from a height the rain stops in mid-air in a flat sheet.",
    "fix": "cgame only, engine branch rainfix-next 5376f59e (off integ-1.10.22), cgame md5 01763816; NOT deployed, not merged. (1) coop_rainToGround 1 (default; 0 = as before): the drop lives one streak length longer and is drawn with the new cgame beam flag BEAM_HZM_TAILRUN - the head stops at the surface, the tail runs on into it, the texture is cut (not squeezed) by what has gone in; nothing is drawn beyond the surface. Both rain paths. (2) coop_rainFloor 1024 (default; 256 = as before): a drop that reaches 256 below the eye with nothing solid under it carries on along its own line at its own speed to the first solid or to that depth (one extra trace, only for such drops; a rain drop flatter than 60 degrees from vertical is not drawn, snowflakes are left as they were; a slow snowflake may live 20 s instead of 10). (3) MAX_BEAMS 4096 -> 8192 with coop_rainMaxBeams 4096: rain and snow keep to 4096 live beams (ordinary snow has always kept the pool full; with 8192 and no share it drew twice the flakes), the spawn loops leave when the share is full. After: streak top 4 units over the ground at removal, lower half of the level view 5-13 % streak pixels, same at 30/60/125/231 fps; live streaks in the downpour 1,700 -> 2,700, drops made a second unchanged. Harness trap met on the way: a script trace straight down at the player's own XY hits the player's own bounding box, so a 'snap to ground' teleport alternated between the ground and 94 units up - pass 1 as the trace's third argument. Evidence and numbers: docs/proposals/rainfix_2026-10-13/README.md",
    "tags": ["rain", "weather", "downpour", "wxextreme", "cgame", "beam", "cg_nature", "snow", MARK],
    "related_bugs": ["bug-3529", "bug-3552", "bug-3558", "bug-3466"],
    "occurrences": 1,
    "last_seen": time.strftime("%Y-%m-%dT%H:%M:%S-06:00"),
}
raw = open(P, "rb").read()
txt = raw.decode("utf-8")
ids = [int(x) for x in re.findall(r'"id":\s*"bug-(\d+)"', txt)]
want = sys.argv[1] if len(sys.argv) > 1 else None
if want:
    # rewrite our own entry in place
    i = txt.index('{\n    "id": "%s"' % want)
    j = txt.index("\n  }", i) + len("\n  }")
    assert MARK in txt[i:j], "not our entry"
    ENTRY["id"] = want
    body = json.dumps(ENTRY, indent=2, ensure_ascii=False).replace("\n", "\n  ")
    txt = txt[:i] + body + txt[j:]
else:
    assert MARK not in txt, "already added - pass the id to rewrite"
    ENTRY["id"] = "bug-%d" % (max(ids) + 1)
    body = json.dumps(ENTRY, indent=2, ensure_ascii=False).replace("\n", "\n  ")
    k = txt.rstrip().rindex("]")
    head = txt[:k].rstrip()
    assert head.endswith("}")
    txt = head + ",\n  " + body + "\n]\n"
json.loads(txt)
open(P, "wb").write(txt.encode("utf-8"))
print(ENTRY["id"])
