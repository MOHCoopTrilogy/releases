"""finish.py - third pass wrap-up: append the bug entries to .wolf/buglog.json (binary I/O, appended before the closing
bracket, ids taken at write time), then append the THIRD PASS section to the proposal README with those ids."""
import io, json, re, time
BL = "C:/mohaa-coop-dev/.wolf/buglog.json"
RD = "C:/mohaa-coop-dev/docs/proposals/para_30cal_2026-10-12/README.md"
raw = open(BL, "rb").read()
assert b"paratroopers rush: the leash never held" not in raw, "already appended"
ids = [int(x) for x in re.findall(rb'"id":\s*"bug-(\d+)"', raw)]
nxt = max(ids) + 1
NOW = time.strftime("%Y-%m-%dT%H:%M:%S-06:00")
HAR = "Agent, harness G:/mohaa-hudfeed5 (game.dll 4fbcc3b9, real C-47 sticks, the map's own Germans unless said). "
MOD = "NOT DEPLOYED. Mod coop-wip "
E = [
    dict(error_message="paratroopers rush: the leash never held (user 2026-10-12: 'they do sometimes brainlessly rush. Make them tactical and extremely realistic')",
         file="hzm-mohaa-coop-mod/coop_mod/parasquad.scr",
         root_cause="member set leash 640 and the brain called resetleash on every order; the engine itself re-homes an actor on every new enemy (Actor::Begin_Cover -> SetLeashHome(origin)), and an American whose enemy is beyond maxdist always charges (Turret_SelectState: the hold-at-leash branch is German-only). The leash therefore followed the man. m3l2: the squad ended 1000u past the hold point (farthest man avg 749u, max 1014u).",
         fix=MOD + "cd54b05a: every man's leash is tethered (engine `tether`: Actor::Think sets m_vHome to the tether entity each frame) to a POST the brain moves, leash 170-240; maxdist 3000; no resetleash anywhere (it clears the tether). CONTACT: wedge faces the enemy and stays beside / behind the players, base of fire (.30 cal in arc, else BAR with a line, else two rifles) or nobody moves up, bounds of 300u to cover one fire team at a time, pinned 4s, man down 6s, lanes (player muzzle, gun muzzle), cover-at-once on first contact (fd54ab32).",
         verified_by=HAR + "m3l2: before (8a35ddcd) farthest man avg 749u max 1014u; after avg 206u, men 1-4 in a line beside the hold point, all alive at full health. m4l3 after: avg 244-312u, squad intact. Single runs. NOT verified: a second client; an in-game before/after capture (the tactical GIFs are plots of logged positions).",
         tags=["parasquad", "ai", "leash", "tether", "tactics"]),
    dict(error_message="paratroopers land on roofs / in places with no pathnodes and are teleported (user 2026-10-12: 'they teleport if they get stuck or fall off map.... Which tends to happen if they land in a bad spot')",
         file="hzm-mohaa-coop-mod/coop_mod/paradrop.scr",
         root_cause="no landing point was chosen: each man came down where the aircraft's speed left him (m3l2: a roof and a sunken lane with no pathnodes; m5l1a, m4l3, m3l3: roofs 280-690u up). coop_paradrop_landing_check then moved any man 700u from a player, idle and not closing for 8s, onto ground nobody had looked at (m3l2: two men teleported onto a spot with no pathnode; a flying test camera: 127 teleports into the air; m4l3: the whole squad teleported 5700u).",
         fix=MOD + "cd54b05a + fd54ab32: coop_para_lz picks five points while the C-47s are inbound (ground at the squad's level, open sky over it and 44u round it, level, hull room, dry, 110u apart, out of the enemy's sight first, and path-connected: a hidden scout actor is stood on each and ordered to the smoke - his pathdist is the test); the canopy is steered onto the point; the teleport is a last resort (fell out of the world, or the brain's LOST after two orders + two straight walks + no path to landing point / mate / anchor) and its destination is path-tested with the man himself (coop_paradrop_rescue).",
         verified_by=HAR + "80 landings in 16 runs on m3l2 / m5l1a / m4l3 / m3l3 all within 3.1u of their points, none on a roof. Teleports per drop before: m3l2 5 / 2 / 3, m5l1a 1, m4l3 7, m3l3 1; rescues after: 0 in 13 runs, 1 in m5l1a a4 (a man one map cell from his landing point in a nodeless cell - walkOut now walks him back, not re-run), medic rescues in k1 / a5 caused by the test's player being 5700-8000u away (rule fixed, not re-run).",
         tags=["paradrop", "landing", "teleport", "pathnodes"]),
    dict(error_message="mg walk how=2 left=42 ok=0 - the gunner is pulled off his walk to the gun site",
         file="hzm-mohaa-coop-mod/coop_mod/parasquad.scr",
         root_cause="mgPlan set coop_psqBusy only in mgReach, after a 0.2-0.6s search; a bound / room-clearing order the brain started in that window ran against the walk (moveTo had no busy test, and room clearing took member 3 - the gunner since the second pass - as its second man).",
         fix=MOD + "cd54b05a: mgPlan sets coop_psqBusy at its start; moveTo refuses a busy or mounted man; room clearing order is Thompson, BAR, gunner, sniper.",
         verified_by=HAR + "m3l2: nine unassisted set-ups with path walks of 50-287u.",
         tags=["parasquad", "race", "mg"]),
    dict(error_message="the crouched .30 cal gunner's hands are at his face, not on the gun (still p2_sandbag_m3l2_b.jpg)",
         file="hzm-mohaa-coop-mod/coop_mod/parasquad.scr",
         root_cause="TurretGun::ThinkIdle tips an unmanned gun barrel-up; in the 0.3s of the scripted set-down it tipped 13 degrees and, with no enemy, nothing levelled it - the engine holds the gunner's hands 39u behind the pivot at one height, so the grips sank 10u under them. Also TurretGun::AI_MoveToDefaultPosition pitches the gun at client 0.",
         fix=MOD + "cd54b05a: cooprestpitch 3 (engine key; maxIdlePitch 0 on an older game.dll), pitchCaps -12 12 and sites planned for 12 degrees, mgHold WATCH (targettype none + a level aim target down his arc) whenever he has had nobody in sight for 9s. 8ade3c9c: bipod prop at 0.75 and bags at 1.2 so the gun sits 13.5u over the top bag and 39.3u over his ground.",
         verified_by=HAR + "side and telephoto stills on m3l2 (bags) and m3l3 (sill): hands at the rear of the receiver, bipod feet on the support. Remaining: at 12 degrees of pitch the grips are ~8u from his hands (engine pose).",
         tags=["parasquad", "mg", "pose", "turret"]),
    dict(error_message="the gunner plans the same cover site every 13s and never arrives (m3l3: mg setup abort=not_reached six times)",
         file="hzm-mohaa-coop-mod/coop_mod/parasquad.scr",
         root_cause="mgLeg's stall test was 'the straight distance to the seat did not shrink by 4u in 0.25s'; a path that leads round a building first grows it, so a running man was declared stalled after 2s.",
         fix=MOD + "fd54ab32: stalled = he moved less than 5u; the leg's time limit follows the path's length; a seat he did not reach is not planned again for 60s.",
         verified_by=HAR + "m3l3 a8: path walk 227u (path 474u) reached, set up.",
         tags=["parasquad", "mg", "pathing"]),
    dict(error_message="the m3l3 window sill is refused (squad_in_front) and the gun would hold its fire there",
         file="hzm-mohaa-coop-mod/coop_mod/parasquad.scr",
         root_cause="mateInFront / playerInFront are flat tests: squad mates in the street 200u under the window counted as in front of the muzzle.",
         fix=MOD + "8ade3c9c: a man more than 110u under or over the muzzle (and outside a 14 degree cone) is not in front of it; same rule in the brain's gun lane.",
         verified_by=HAR + "m3l3 g3 / g4 / k3: the sill planned and set up with the squad in the street below.",
         tags=["parasquad", "mg"]),
    dict(error_message="the .30 cal packs up and sets up again every 24s (m4l3: five set-ups in 110s, each left 12s after its last burst)",
         file="hzm-mohaa-coop-mod/coop_mod/parasquad.scr",
         root_cause="mgTend counted 15s of 'the squad's NEAREST enemy is masked from this gun' although the gun was suppressing another one.",
         fix=MOD + "fd54ab32: no count while the gun has fired in the last 20s (coop_psqMgFireT), and 25s not 15.",
         verified_by=HAR + "m4l3 a6: one set-up (cover 46u), stayed.",
         tags=["parasquad", "mg"]),
    dict(error_message="the medic is teleported although he stands with the squad (rescue why=medic_stuck)",
         file="hzm-mohaa-coop-mod/coop_mod/paradrop.scr",
         root_cause="first version of the new last resort read the medic's pathdist without giving him an order: his own loop only follows a player inside 2000u, so pathdist was 0 whenever the player was farther.",
         fix=MOD + "8ade3c9c + fd54ab32: he is ordered to the player first, and counts as stuck only with no path to the player and none to a squad mate.",
         verified_by="NOT re-run with a player 5000u away (that is the harness: the map sends the teleported test player back).",
         tags=["paradrop", "medic", "teleport", "own-regression"]),
    dict(error_message="lz plan n=0 tests=0 - the first landing-point search refused every point",
         file="hzm-mohaa-coop-mod/coop_mod/paradrop.scr",
         root_cause="the ground was traced DOWN from a guessed height (smoke + 2400u), which is above the sky brush: the first hit was the top of the sky. level.ac_env['sky'] was not set on that map.",
         fix=MOD + "cd54b05a: ground from 100u over the smoke's ground down 320u, then the sky is looked for UPWARD from that ground (nothing for 4000u, or a sky surface), at five points.",
         verified_by=HAR + "lz plan n=5 tests=5 on four maps.",
         tags=["paradrop", "landing", "trace", "edited-more-than-twice"]),
    dict(error_message="python heredoc in Git-Bash turned \\n inside a patch script into real newlines (ed3.py SyntaxError)",
         file="docs/proposals/para_30cal_2026-10-12/tools/pass3/edits/ed3.py",
         root_cause="a fixer was fed through a bash heredoc although the session notes say to write patch scripts with the Write tool; also three text substitutions failed on a wrong guess of the tab depth.",
         fix="patch scripts written with the Write tool; edlib.py matches the old text with any leading-tab depth and re-indents the new text by the difference.",
         verified_by="ed4..ed16 applied with edlib, scanners clean after each.",
         tags=["tooling", "heredoc", "patch-script"]),
]
out = []
for k, e in enumerate(E):
    o = {"id": "bug-%d" % (nxt + k), "timestamp": NOW}
    o.update(e)
    o.update({"related_bugs": ["bug-3562"], "occurrences": 1, "last_seen": NOW})
    out.append(json.dumps(o, indent=2, ensure_ascii=True).replace("\n", "\n  "))
tail = raw.rstrip()
assert tail.endswith(b"]")
body = tail[:-1].rstrip()
assert body.endswith(b"}")
new = body + b",\n  " + (",\n  ".join(out)).encode("ascii") + b"\n]\n"
json.loads(new.decode("latin-1"))
open(BL, "wb").write(new)
print("buglog: bug-%d..bug-%d" % (nxt, nxt + len(E) - 1))

sec = io.open("readme_p3.md", encoding="utf-8").read()
sec = sec.replace("bug-3686..3695", "bug-%d..%d" % (nxt, nxt + len(E) - 1))
sec = sec.replace("all 45 landings within 2 u of their points", "all 45 landings within 3.1 u of their points")
sec = sec.replace("| 0 | 3117 / 3104 | 749 u (1014) | 17.3 / 6.8 s |", "| 0 | 3101 / 3117 / 3104 | 749 u (1014; b2) | 3.0 / 17.3 / 6.8 s |")
r = io.open(RD, encoding="utf-8", newline="").read()
assert "# THIRD PASS" not in r
nl = "\r\n" if "\r\n" in r else "\n"
io.open(RD, "w", encoding="utf-8", newline="").write(r.rstrip("\r\n") + nl + sec.replace("\n", nl))
print("README appended", len(sec.splitlines()), "lines")
