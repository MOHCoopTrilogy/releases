"""tileart_run.py - ONE short, quiet staging run for the re-staged sample tiles (TEST ONLY, never shipped).

    python staging/tileart_run.py check     # everything that can be verified WITHOUT the slot (overlay builds, scenes
                                            # resolve, install + guard registration present). Exit 1 on any failure.
    python staging/tileart_run.py wait      # the queue waiter: polls SCRATCH\\test_slot.txt until it reads exactly
                                            # "tileart", then runs `run`. Low CPU (one read every 20 s).
    python staging/tileart_run.py wait_r3   # round 3: t2l1 only (the level's own Panzer IV), no UI test
    python staging/tileart_run.py run       # launch, stage + capture every scene, UI localization test, quit,
                                            # write "free" to the slot file.

Reuses the loadart rig (docs/proposals/bt_loadscreens_2026-09-28/tools/la_client.py + la_overlay.py) by IMPORT, read-only:
its install/owner/port/overlay constants are overridden here, and only its launch/step/cam/spawn helpers are called
(the helpers that write into its own folder - scout/view/stage/scene - are not).

Private client G:\\mohaa-tileart: the LIVE binaries (exe 90e47187, cgame 0a0bb3b4) copied from G:\\mohaa-gl2 (read
only), a fresh home (no qkey or saves copied), basepath = the GOG tree (read only), net_ip 127.0.0.1 via
harness_window policy, DISPLAY2 via launch_background, com_maxfps 60, 1920x1080 windowed, gl2 (the user's renderer).
Nothing under G:\\mohaa-gl2, %APPDATA%\\openmohaa or the GOG tree is written.

Captures: the engine's own `screenshot` (TGA), one per frame (`wait` between shots is milliseconds). No console text:
ui_gmbox 0 / ui_minicon 0 in the config, con_notifytime 0 (the scout frames of 2026-09-28 lacked these).
"""
import json
import math
import os
import shutil
import sys
import threading
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
LA = r"C:\mohaa-coop-dev\docs\proposals\bt_loadscreens_2026-09-28\tools"
sys.path.insert(0, LA)
sys.dont_write_bytecode = True
import la_client as C  # noqa: E402
import la_overlay as LO  # noqa: E402
from ents import ents  # noqa: E402

SCRATCH = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad"
SLOTFILE = os.path.join(SCRATCH, "test_slot.txt")
CLIENT = r"G:\mohaa-tileart"
OWNER = "tileart"
RUNLOG = os.path.join(HERE, "run.log")

# ---- point the loadart client at this install (module globals are read at call time)
C.CLIENT = CLIENT
C.EXE = os.path.join(CLIENT, "openmohaa.exe")
C.HOME = os.path.join(CLIENT, "home")
C.MAINTT = os.path.join(C.HOME, "maintt")
C.LOG = os.path.join(C.MAINTT, "qconsole.log")
C.SHOTS = os.path.join(C.MAINTT, "screenshots")
C.OVERLAY = "zzzzzzzzzzzz_tileart_probe.pk3"
C.STOP = os.path.join(CLIENT, "STOP")
C.STATE = os.path.join(CLIENT, "state.json")
C.OWNER = OWNER
C.RUNS = os.path.join(CLIENT, "runs")
C.PORT = 12530
C.RCONPW = "tileartpw"
C.SLOTFILE = SLOTFILE

# ---- the UI test: an engine-drawn TWO-line tile title through the localization table (review 2026-09-29).
# cLocalization reads every global/localization*.txt at client start (sys/win_localization.cpp); button titles are
# drawn through Sys_LV_CL_ConvertString (uibutton.cpp). If the TikiScript reader turns \n into a newline, the second
# tile shows two lines.
LOCTEST = ('{ "HZMTILE_TEST_ONE" "Single line test" }\n'
           '{ "HZMTILE_TEST_TWO" "Secret Documents\\nof the Kriegsmarine" }\n')


UIPAYLOAD = {"on": False}
MODCFGS = ["m0", "m1", "m2", "m3", "m4", "m5", "m6", "e1", "e2", "e3", "t1", "t2", "t3"]


class Overlay:
    @staticmethod
    def build(out):
        LO.build(out)                                   # loadart camera/spawn script (TEST ONLY)
        with zipfile.ZipFile(out, "a", zipfile.ZIP_DEFLATED) as z:
            z.writestr("global/localization_zz_tiletest.txt", LOCTEST.encode("latin-1"))
            if UIPAYLOAD["on"]:
                # the STAGED wiring (apply/mod/ui) + the built tile textures, exactly as the shipped mod + tileart pak would
                # carry them; a later-sorting pak than the deployed mod, so the client sees the post-apply menu.
                base = os.path.join(PROP, "apply", "mod")
                for root, _, fs in os.walk(base):
                    for fn in fs:
                        full = os.path.join(root, fn)
                        z.write(full, os.path.relpath(full, base).replace(os.sep, "/"))
                gd = os.path.join(PROP, "set", "game")
                for fn in sorted(os.listdir(gd)):
                    z.write(os.path.join(gd, fn), "textures/mohmenu/hzmtile/" + fn)


C.la_overlay = Overlay

# ---- boot extras: console quiet, 60 fps cap
_boot = C.boot_cfg


def boot_cfg(extra):
    return _boot(extra) + ["set com_maxfps 60", "set con_notifytime 0", "set cg_hudnotify 0"]


C.boot_cfg = boot_cfg

LOADART_SCENES = json.load(open(os.path.join(LA, "scenes.json")))


def log(*a):
    line = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open(RUNLOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def look(eye, tgt):
    dx, dy, dz = tgt[0] - eye[0], tgt[1] - eye[1], tgt[2] - eye[2]
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = -math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return pitch, yaw


def ring(name, centre, radii, n, eye_dz, tgt_dz):
    """Camera ring around a subject the LEVEL places (a vehicle): n yaws per radius, one TGA each."""
    L = []
    for r in radii:
        for k in range(n):
            a = math.radians(k * 360.0 / n)
            eye = (centre[0] + r * math.cos(a), centre[1] + r * math.sin(a), centre[2] + eye_dz)
            p, w = look(eye, (centre[0], centre[1], centre[2] + tgt_dz))
            L += C.cam_lines(eye[0], eye[1], eye[2], p, w) + ["wait 900", "screenshot %s_r%d_%03d" % (name, r, k * 360 // n),
                                                               "wait 200"]
    C.step(L, timeout=400)


def pathnodes(mp):
    return [[float(v) for v in e["origin"].split()] for e in ents(mp) if e.get("classname") == "info_pathnode"]


def stage_squads(sc, drop_props=(), drop_fx=False):
    """A loadart scene (scenes.json, read only) re-staged: same camera and squads, minus the props/fx the review
    rejected. Returns the axis node list for mortar hits."""
    P = pathnodes(sc["map"])
    al = [P[i] for i in sc["ally_nodes"]]
    ax = [P[i] for i in sc["axis_nodes"]]

    def cen(q):
        return (sum(v[0] for v in q) / len(q), sum(v[1] for v in q) / len(q))
    ca, cx = cen(al), cen(ax)
    L = ["set coop_laClearSeq %d" % C.seq(), "wait 300"]
    L += C.cam_lines(*sc["eye"], sc["pitch"], sc["yaw"]) + ["wait 300"]
    for k, q in enumerate(al):
        yaw = math.degrees(math.atan2(cx[1] - q[1], cx[0] - q[0]))
        L += C.spawn_lines("ally", sc["ally"][k % len(sc["ally"])], q[0], q[1], q[2] + 8, yaw, "", 64)
    for k, q in enumerate(ax):
        yaw = math.degrees(math.atan2(ca[1] - q[1], ca[0] - q[0]))
        L += C.spawn_lines("axis", sc["axis"][k % len(sc["axis"])], q[0], q[1], q[2] + 8, yaw, "", 64)
    for kind, model, x, y, z, yaw in sc.get("props", []):
        if any(d in model for d in drop_props):
            continue
        L += C.spawn_lines(kind, model, x, y, z, yaw)
    if not drop_fx:
        for model, x, y, z in sc.get("fx", []):
            L += C.spawn_lines("fx", model, x, y, z, 0)
    L += ["wait 4000"]
    C.step(L, timeout=180)
    return ax


def burst(name, n, ms, axis=None, every=0, yaw_offsets=(0,), sc=None):
    import random
    rnd = random.Random(len(name) * 31 + n)
    for off in yaw_offsets:
        L = []
        if sc is not None and off:
            L += C.cam_lines(*sc["eye"], sc["pitch"], sc["yaw"] + off) + ["wait 600"]
        for k in range(n):
            if every and axis and k % every == 0:
                q = rnd.choice(axis)
                L += C.spawn_lines("boom", "models/emitters/mortar_dirt_nosound.tik", q[0] + rnd.uniform(-120, 120),
                                   q[1] + rnd.uniform(-120, 120), q[2], 0) + ["wait 200"]
            L += ["screenshot %s_y%+d_%02d" % (name, off, k), "wait %d" % ms]
        C.step(L, timeout=600)


def pull(mp):
    if FULL.get("rt"):
        d = os.path.join(C.RUNS, ("r2_" if FULL["rt"] == "r2" else "rt_") + mp)
    else:
        d = os.path.join(C.RUNS, ("full_" + mp) if mp in SHOTS and FULL["on"] else mp)
    os.makedirs(d, exist_ok=True)
    n = 0
    for fn in sorted(os.listdir(C.SHOTS)):
        shutil.move(os.path.join(C.SHOTS, fn), os.path.join(d, fn))
        n += 1
    log("pulled", n, "->", d)


# ---- the plan: each map's LEVEL-placed subject (retail BSP entity lump) + the re-staged loadart squads
PLAN = [
    # AA m5l2a "The Hunt for the King Tiger - Destroyed Village": the level's own King Tiger
    # (vehicle_german_kingtigertank, vehicles//kingtank.tik, targetname playertank, 3068 -4128 360, angle 90)
    ("m5l2a", lambda: ring("kt", (3068, -4128, 360), (520, 820, 1200), 8, 70, 70)),
    # BT e1l1 "Battle of Kasserine Pass I": the level's own Panzers (panzer_tank_fast_e1l1 at -822 2498 / -1129 2126)
    # and the loadart camera re-staged WITHOUT the spawned Sherman / Panzer props (the floating Sherman, the clipping frame)
    ("e1l1", lambda: (ring("pz", (-822, 2498, 240), (600, 950), 8, 80, 60),
                      burst("ks", 8, 600, stage_squads(LOADART_SCENES["e1l1_kasserine"], drop_props=("sherman", "panzer")),
                            every=3, yaw_offsets=(0, -35, 35), sc=LOADART_SCENES["e1l1_kasserine"]))),
    # SH t2l1 "Panzer Attack": the loadart Bastogne road with its Panzer IV, WITHOUT the smoke sprites (the seam/blob)
    ("t2l1", lambda: burst("bs", 10, 600, stage_squads(LOADART_SCENES["t2l1_bastogne"], drop_fx=True), every=4,
                           yaw_offsets=(0, -12, 12), sc=LOADART_SCENES["t2l1_bastogne"])),
    # SH t3l2 "The Last Stand": both loadart bridge cameras, fx kept low
    ("t3l2", lambda: (burst("br", 8, 600, stage_squads(LOADART_SCENES["t3l2_berlin_rev"], drop_fx=True), every=3,
                            yaw_offsets=(0, -20, 20), sc=LOADART_SCENES["t3l2_berlin_rev"]),
                      burst("bf", 8, 600, stage_squads(LOADART_SCENES["t3l2_berlin"], drop_fx=True), every=3,
                            yaw_offsets=(0, -20, 20), sc=LOADART_SCENES["t3l2_berlin"]))),
    # BT e2l1 (Sicily briefing): the level's bombed CG-4A glider (-3440 -4217 -24) and its glider on the tow (sky)
    ("e2l1", lambda: (ring("gl", (-3440, -4217, -24), (650, 1000), 8, 90, 60),
                      ring("sky", (4422, -2888, 6375), (600,), 6, 20, 0))),
]


# Round 3 (review 2026-09-29): the t2l1 Panzer in PLAN was the loadart SPAWNED prop (3150 4560 1880) and floats. The
# level places its OWN Panzer IV (addon_vehicle_german_snowy-panzeriv, vehicles/panzeriv_w_base.tik, 1738 4867 1744,
# angle 180) directly under the loadart camera. Film that one: a ring for grounded angles, then the loadart squads
# staged WITHOUT the spawned tank and without smoke, from a camera behind/beside the level's tank.
T2 = LOADART_SCENES["t2l1_bastogne"]
T2_BACK = dict(T2, eye=[1330, 4700, 1870], pitch=6, yaw=10)
PLAN_R3 = [
    ("t2l1", lambda: (ring("pz4", (1738, 4867, 1744), (420, 650), 8, 70, 50),
                      burst("pb", 8, 600, stage_squads(T2_BACK, drop_props=("panzer",), drop_fx=True), every=3,
                            yaw_offsets=(0, -15, 15), sc=T2_BACK))),
]


# ---- FULL SET: batched scouting from staging/shotlist.json (the level's own subjects, objective markers, scouts, start)
BATCHES = {
    "A": ["training", "m4l0", "m1l1", "m1l2a", "m1l2b", "m1l3a", "m1l3b", "m1l3c", "m2l1", "m2l2a", "m2l2b", "m2l2c",
          "m2l3", "m3l1a", "m3l1b", "m3l2", "m3l3"],
    "B": ["m4l1", "m4l2", "m4l3", "m5l1a", "m5l1b", "m5l2a", "m5l2b", "m5l3", "m6l1a", "m6l1b", "m6l1c", "m6l2a",
          "m6l2b", "m6l3a", "m6l3b", "m6l3c", "m6l3d", "m6l3e"],
    "C": ["e1l1", "e1l2", "e1l3", "e1l4", "e2l1", "e2l2", "e2l3", "e3l1", "e3l2", "e3l3", "e3l4",
          "t1l1", "t1l2", "t1l3", "t2l1", "t2l2", "t2l3", "t2l4", "t3l1", "t3l2"],
}
SHOTS = json.load(open(os.path.join(HERE, "shotlist.json")))
# RETAKES (2026-09-29, batch A/B review): levels whose scouting lacked the subject the title names (statweapons/ guns were
# skipped by shotlist.py SKIP until now; the U-529 hull, the bridge and the Nebelwerfers are explicit). Written to rt_<map>.
RETAKE = json.load(open(os.path.join(HERE, "retake.json")))
BATCHES["R"] = list(RETAKE)
BATCHES["CR"] = BATCHES["C"] + ["rt:" + m for m in RETAKE]
# RETAKE 2 (2026-10-04, batch C review): four levels whose scouting never left the opening ride - e1l4 (the truck
# camera, trigger_camerause), e3l4 (jeep .30cal turret slot), t2l2 (halftrack turret slot), t3l2 (the T-34 driver
# slot) - so every frame was the same view from the vehicle. Re-shot with the RIDE RELEASE hook below (once per map,
# before the first camera move) and the level's own t2l2 dev cvar coop_dbgNoSeat 1. Written to r2_<map>.
RETAKE2 = json.load(open(os.path.join(HERE, "retake2.json")))
BATCHES["C2"] = ["r2:" + m for m in RETAKE2]
FREE_HOOK = """			if( level.ta_freed != 1 ){
				level.ta_freed = 1
				waitthread ta_free
			}
"""
FREE_LABEL = """
ta_free:{
	//TEST OVERLAY ONLY (tileart retake 2): release the player from the level's opening ride, once
	level.RideOver = 1
	cueplayer
	local.v = NULL
	if( $startjeep != NULL ){ local.v = $startjeep }
	if( level.playerjeep != NIL && level.playerjeep != NULL ){ local.v = level.playerjeep }
	if( local.v != NULL ){
		local.t = local.v queryturretslotentity 0
		if( local.t != NULL ){ local.t unlock }
		local.v unlock
		local.v detachturretslot 0 ( local.v.origin + ( 0 0 120 ) )
	}
	if( $playertank != NULL ){
		$playertank unlock
		$playertank detachdriverslot 0 ( $playertank.origin + ( 0 0 200 ) )
	}
	println( "^~^~^ TAFREE " + level.time )
}end
"""


def arm_free_hook():
    anchor = "\t\t\tlevel.coop_playerGlue = 0\n"
    assert LO.SCRIPT.count(anchor) == 1
    LO.SCRIPT = LO.SCRIPT.replace(anchor, FREE_HOOK + anchor) + FREE_LABEL
    LO.check(LO.SCRIPT)
    _bc = C.boot_cfg
    C.boot_cfg = lambda extra: _bc(extra) + ["set coop_dbgNoSeat 1"]


def jpg_ring(prefix, s):
    L = []
    for r in s["radii"]:
        for k in range(s["n"]):
            a = math.radians(k * 360.0 / s["n"])
            c = s["at"]
            eye = (c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2] + s["eye_dz"])
            p, w = look(eye, (c[0], c[1], c[2] + s["tgt_dz"]))
            L += C.cam_lines(eye[0], eye[1], eye[2], p, w) + ["wait 700", "screenshotJPEG %s_r%d_%03d" % (prefix, r, k * 360 // s["n"]),
                                                               "wait 150"]
    C.step(L, timeout=300)


def scout_map(mp):
    tag = ""
    P = SHOTS.get(mp)
    FULL["rt"] = False
    if mp.startswith("rt:"):
        mp = mp[3:]
        P = RETAKE[mp]
        tag = "rt"
        FULL["rt"] = True
    elif mp.startswith("r2:"):
        mp = mp[3:]
        P = RETAKE2[mp]
        tag = "r2"
        FULL["rt"] = "r2"
    for i, s in enumerate(P["subjects"]):
        jpg_ring("%s%s_s%d%s" % (tag, mp, i, s["name"]), s)
    st = P.get("start")
    if st:
        L = []
        for dz, tag in ((70, "st"), (260, "sthi")):
            for yaw in (0, 90, 180, 270):
                L += C.cam_lines(st[0], st[1], st[2] + dz, 4 if dz > 100 else 0, yaw) + [
                    "wait 700", "screenshotJPEG %s_%s_%03d" % (mp, tag, yaw), "wait 150"]
        C.step(L, timeout=300)
    L = []
    for i, q in enumerate(P.get("scouts", [])):
        for yaw in (0, 90, 180, 270):
            L += C.cam_lines(q[0], q[1], q[2] + 64, 4, yaw) + ["wait 700", "screenshotJPEG %s_sc%d_%03d" % (mp, i, yaw), "wait 150"]
    if L:
        C.step(L, timeout=300)


FULL = {"on": False}


def batch_plan(name):
    FULL["on"] = True
    if name == "C2":
        arm_free_hook()
    return [(mp[3:] if mp[:3] in ("rt:", "r2:") else mp, (lambda m=mp: scout_map(m))) for mp in BATCHES[name]]


def ui_test():
    L = ["pushmenu coop_start", "wait 800", "exec ui/coop_start/m2.cfg", "wait 400",
         'globalwidgetcommand coop_startMap2 title "HZMTILE_TEST_ONE"',
         'globalwidgetcommand coop_startMap3 title "HZMTILE_TEST_TWO"',
         'globalwidgetcommand coop_startMap4 title "Secret Documents\\nof the Kriegsmarine"',
         "wait 800", "screenshot ui_loctest", "wait 400", "popmenu 0"]
    out = C.step(L, timeout=120)
    log("ui test lines:", [ln for ln in out.splitlines() if "ocaliz" in ln][:6])
    pull("ui")


def ui_layout_check():
    """Every mission cfg, both menu layouts, screenshotted from the STAGED wiring (UIPAYLOAD overlay). Also a hover/click probe
    is NOT done here (the Buttons are unchanged); this proves the linkcvartoshader Labels draw the right art and switch layout."""
    L = []
    for lay in (0, 1):
        L += ["set ui_menuCenter %d" % lay, "wait 300"]
        for cfg in MODCFGS:
            L += ["pushmenu coop_start", "wait 900", "exec ui/coop_start/%s.cfg" % cfg, "wait 900",
                  "screenshot ui_%s_c%d" % (cfg, lay), "wait 400", "popmenu 0", "wait 300"]
    C.step(L, timeout=600)
    pull("ui")


def check():
    fails = []
    for p in (C.EXE, os.path.join(CLIENT, "pristine", "omconfig.cfg")):
        if not os.path.exists(p):
            fails.append("missing " + p)
    # the engine writes its OWN fresh qkey (+ saves keyed to it) on first launch; what must never be here is a COPY of
    # the user's. Compare against every qkey the user has.
    import hashlib
    mine = os.path.join(C.HOME, "qkey")
    if os.path.exists(mine):
        h = hashlib.md5(open(mine, "rb").read()).hexdigest()
        for user in (r"G:\mohaa-gl2\home\qkey", os.path.join(os.environ.get("APPDATA", ""), "openmohaa", "qkey")):
            if os.path.exists(user) and hashlib.md5(open(user, "rb").read()).hexdigest() == h:
                fails.append("the private home holds a COPY of the user's qkey (%s)" % user)
    import harness_guard as hg
    if CLIENT not in hg.HARNESSES or hg.HARNESSES[CLIENT]["owner"] != OWNER:
        fails.append("G:\\mohaa-tileart not registered in harness_guard.HARNESSES")
    tmp = os.path.join(HERE, "_overlay_check.pk3")
    try:
        Overlay.build(tmp)
        with zipfile.ZipFile(tmp) as z:
            names = z.namelist()
        if "global/localization_zz_tiletest.txt" not in names or "coop_mod/zz_loadart.scr" not in names:
            fails.append("overlay members missing: %s" % names)
    except Exception as e:
        fails.append("overlay build failed: %r" % (e,))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    for k in ("e1l1_kasserine", "t2l1_bastogne", "t3l2_berlin_rev", "t3l2_berlin"):
        sc = LOADART_SCENES[k]
        n = len(pathnodes(sc["map"]))
        if max(sc["ally_nodes"] + sc["axis_nodes"]) >= n:
            fails.append("scene %s node index out of range (%d nodes)" % (k, n))
    for f in fails:
        print("FAIL", f)
    print("check", "OK" if not fails else "FAILED")
    return 1 if fails else 0


def run(plan=None, ui=True):
    plan = plan or PLAN
    if check():
        raise SystemExit("pre-flight failed - not taking the slot")
    v = open(SLOTFILE).read().strip()
    if v != OWNER:
        raise SystemExit("slot is %r, not %r" % (v, OWNER))
    if os.path.exists(C.STOP):
        os.remove(C.STOP)
    t0 = time.time()
    first = plan[0][0]
    th = threading.Thread(target=C.serve, args=(first,), daemon=True)
    th.start()
    try:
        # wait for serve() to report READY
        while True:
            time.sleep(2)
            st = json.load(open(C.STATE)) if os.path.exists(C.STATE) else {}
            if st.get("state") == "ready":
                break
            if not th.is_alive():
                raise RuntimeError("client did not come up")
            if time.time() - t0 > 900:
                raise RuntimeError("client not ready after 15 min")
        log("ready", st)
        for k, (mp, fn) in enumerate(plan):
            try:
                if k > 0:
                    C.change_map(mp)
                time.sleep(8)
                fn()
                pull(mp)
                log("done", mp, "%.1f min" % ((time.time() - t0) / 60))
            except Exception as e:
                log("MAP FAILED", mp, repr(e))
        try:
            if ui:
                ui_test()
        except Exception as e:
            log("UI TEST FAILED", repr(e))
    finally:
        open(C.STOP, "w").write("stop")
        th.join(120)
        log("client stopped, total %.1f min" % ((time.time() - t0) / 60))
        with open(SLOTFILE, "w") as f:
            f.write("free")
        log("slot -> free")


def wait(plan=None, ui=True):
    log("waiting for the test slot to read exactly 'tileart'")
    while True:
        try:
            v = open(SLOTFILE).read().strip()
        except OSError:
            v = ""
        if v == OWNER:
            log("slot is ours")
            run(plan, ui)
            return
        time.sleep(20)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "wait_batch":
        sys.exit(wait(batch_plan(sys.argv[2]), False) or 0)
    if cmd == "wait_c2ui":
        # retake 2 + the in-engine layout check of the STAGED wiring (both ui_menuCenter values, every mission cfg)
        UIPAYLOAD["on"] = True
        sys.exit(wait(batch_plan("C2") + [("m1l1", ui_layout_check)], False) or 0)
    if cmd == "wait_ui":
        UIPAYLOAD["on"] = True
        sys.exit(wait([("m1l1", ui_layout_check)], False) or 0)
    if cmd == "wait_r3":
        sys.exit(wait(PLAN_R3, False) or 0)
    sys.exit({"check": check, "wait": wait, "run": run}[cmd]() or 0)
