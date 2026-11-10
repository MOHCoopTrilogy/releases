#!/usr/bin/env python3
r"""at_attic_run.py - in-game QA of the attic TRAINING prop (practice target, hotspot 20) and its two-card sheet, on the
PRIVATE client G:\mohaa-advtrain (A) only.                                                            [advtrain 2026-11-10]

Everything about the client comes from ..\..\tools\at_test.py (imported, untouched): byte copy of the live exe/DLLs, basepath =
the GOG tree read-only, its own home, started ONLY through harness_window.launch_background (at_test.client: the test display
picked by RESOLUTION - HZM_TEST_RES=1920x1080, the 1080p second screen -, never focused, guard watcher + job object, muted,
in_mouse 0, in_nograb 1, in_gamepad 0, in_joystick 0). Any guard trip stops every later launch. No pad script, no input
except console binds posted to OUR window (the launch cases), never the user's game.

    python at_attic_run.py setup                     menus pak (ship_at) -> A's home maintt; at_test.build_pak() (the mod override)
    python at_attic_run.py attic                     3D attic (ui_atticMain 1): home, hover 20, hover 19 (OWN DISCS still 19),
                                                     close-ups, the hotspot's own click -> sheet, ESC back, sheet direct, back home
    python at_attic_run.py launch_basic              click -> sheet -> the Basic card's own stuffcommand: map training loads
    python at_attic_run.py launch_adv                ... the Advanced card's: m4l0 loads with the course on (ATRAIN branch on)
    python at_attic_run.py all                       setup + attic + launch_basic + launch_adv

Every command a shot runs is READ from the built files (main.urc's hot_training proxy, coop_training.urc's card buttons), so
the test exercises the shipped strings, not a copy. Results: H:\hzm_work\advtrain-test\runs\attic_<case>\ (jpg stills,
qconsole.log, result.json) - local only, never committed.
"""
import json, os, re, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "tools")))
os.environ["HZM_TEST_RES"] = "1920x1080"
import at_test as AT  # noqa: E402   (the advtrain harness: client(), guard(), build_pak(), errors(), atrain())
from PIL import Image  # noqa: E402

MENUS = r"H:\hzm_work\advtrain-ship\ship_at\zzzzzzzzzzzzzz_hzm_menus3d.pk3"
HOME = os.path.join(AT.A, "home")
MT = os.path.join(HOME, "maintt")
RUNS = AT.RUNS
IDX = 20
UI = os.path.join(AT.MOD, "ui")


def urc_cmd(f, widget):
    t = open(os.path.join(UI, f), "rb").read().decode("latin-1").replace("\r\n", "\n")
    m = re.search(r'resource\n\w+\n\{\nname "%s"\n.*?\nstuffcommand "([^"]*)"\n' % re.escape(widget), t, re.S)
    assert m, (f, widget)
    return m.group(1)


def scene_pose(name):
    return json.load(open(r"H:\hzm_work\advtrain-ship\ship_at\target_at_urc.json"))[name]


def setup():
    os.makedirs(MT, exist_ok=True)
    shutil.copyfile(MENUS, os.path.join(MT, "zzzzzzzzzzzzzz_hzm_menus3d.pk3"))
    files = AT.build_pak()
    need = ["ui/main.urc", "ui/coop_training.urc"]
    miss = [f for f in need if f not in files]
    assert not miss, ("the override pak lacks %s - commit or keep them in the mod worktree" % miss)
    print("setup: menus pak + override (%d files) in %s" % (len(files), MT))


BOOT = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter 0", "set ui_camslow 1",
        "set coop_hardcore 0", "set ui_wxHour 12.5", "set ui_wxWeather 1", "wait 12000", "echo ^~^~^ ATQ start"]


def run_client(tag, lines, out, until=None, timeout=240, post=None):
    """lines run from a boot cfg (waits are MILLISECONDS here); until = a log regex that ends the wait early (then `post`
    keys are posted to our window); the client quits itself at the end of `lines` otherwise"""
    if AT.TRIPPED:
        raise SystemExit("GUARD TRIPPED earlier - no more launches: %s" % AT.TRIPPED)
    open(os.path.join(MT, "at_attic.cfg"), "w", newline="\n").write("\n".join(lines) + "\n")
    shots = os.path.join(MT, "screenshots")
    shutil.rmtree(shots, ignore_errors=True)
    sets = [("ui_atticMain", "1"), ("ui_menuRoom", "1"), ("ui_menuCenter", "0"), ("s_musicvolume", "0"), ("s_ambientvolume", "0"),
            ("com_maxfpsUnfocused", "30")]
    c = AT.client(AT.A, HOME, sets, ["+exec", "at_attic.cfg"], [], "AT_Alpha", size=(1920, 1080))
    t0, hit = time.time(), None
    try:
        while c.alive() and time.time() - t0 < timeout:
            if AT.guard(c):
                break
            if until and hit is None:
                m = re.search(until, AT.read(AT.lp(HOME)))
                if m:
                    hit = m.group(0)
                    time.sleep(20)
                    for k in post or ():
                        c.post_key(AT.VK[k])
                        time.sleep(4)
            time.sleep(2)
    finally:
        if c.alive():
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
    shutil.copyfile(AT.lp(HOME), os.path.join(out, "qconsole.log"))
    for f in sorted(os.listdir(shots)) if os.path.isdir(shots) else []:
        if f.lower().endswith((".tga", ".jpg")):
            Image.open(os.path.join(shots, f)).convert("RGB").save(os.path.join(out, os.path.splitext(f)[0] + ".jpg"), quality=90)
    return hit


def shot_lines(spec, tag):
    L = []
    for name, cmds in spec:
        L += cmds + ["echo ^~^~^ ATQ shot %s" % name, "screenshot atq_%s_%s" % (tag, name), "wait 700"]
    return L


def case_attic(out, res):
    click = urc_cmd("main.urc", "hot_training")
    assert "pushmenu coop_training" in click
    close = scene_pose("fly")
    spec = [("home", ["set ui_scene_hot 0", "wait 1500"]),
            ("hover", ["set ui_scene_hot %d" % IDX, "wait 1800"]),
            ("hover19", ["set ui_scene_hot 19", "wait 1500"]),          # OWN DISCS keeps its index and caption
            ("close", ["set ui_scene_hot 0", 'set ui_scene_pose "%s"' % close, "wait 1500"]),
            ("close_hover", ["set ui_scene_hot %d" % IDX, "wait 1500"]),
            ("back_home", ["set ui_scene_hot 0", 'set ui_scene_pose ""', "wait 3000"]),
            ("click", [click, "wait 3500"]),                              # the proxy's own command: fly in, veil, the sheet
            ("popped", ["popmenu 0", "wait 3500"]),                       # back to the attic (flies home)
            ("direct_sheet", ["pushmenu coop_training", "wait 2500"]),
            ("direct_closed", ["popmenu 0", "wait 3000"])]
    run_client("attic", BOOT + shot_lines(spec, "attic") + ["echo ^~^~^ ATQ done", "wait 1500", "quit"], out, timeout=200)
    log = AT.read(os.path.join(out, "qconsole.log"))
    res["shots"] = sorted(f for f in os.listdir(out) if f.endswith(".jpg"))
    res["done"] = "ATQ done" in log
    res["log_problems"] = [l.strip()[:200] for l in log.splitlines()
                           if re.search(r"(?i)couldn't|can't find|not found|bad menu|unknown command|ERROR|WARNING: .*(urc|menu|shader|model|tik)", l)][:30]
    res["ok"] = res["done"] and len(res["shots"]) == len(spec)


def case_launch(out, res, adv):
    click = urc_cmd("main.urc", "hot_training")
    card = urc_cmd("coop_training.urc", "beginAdv" if adv else "beginBasic")
    want = "m4l0" if adv else "training"
    assert ("ui_dmmap %s" % want) in card and "seta" not in card
    lines = BOOT + ["set developer 1", 'bind F10 "screenshot atq_launch"', 'bind F11 "quit"',
                    click, "wait 3500", "screenshot atq_launch_sheet", "wait 700", "echo ^~^~^ ATQ card", card]
    hit = run_client("launch", lines, out, until=r"Spawning Entities Done|ATRAIN branch on", timeout=420, post=("F10", "F11"))
    log = AT.read(os.path.join(out, "qconsole.log"))
    res.update(AT.errors(log))
    res["loaded"] = bool(hit)
    res["map_seen"] = bool(re.search(r"(?i)maps/%s\.bsp|Server: %s\b|mapname[^\n]*%s" % (want, want, want), log))
    res["advTraining_cvar"] = re.findall(r"coop_advTraining[^\n]{0,40}", log)[:5]
    res["atrain"] = AT.atrain(log)[:20]
    res["branch_on"] = "ATRAIN branch on" in log
    res["shots"] = sorted(f for f in os.listdir(out) if f.endswith(".jpg"))
    res["ok"] = res["loaded"] and res["map_seen"] and not res["compile"] and not res["notloaded"] and (res["branch_on"] == adv)


def main():
    cases = sys.argv[1:] or ["attic"]
    if cases == ["all"]:
        cases = ["setup", "attic", "launch_basic", "launch_adv"]
    rc = 0
    for case in cases:
        if case == "setup":
            setup()
            continue
        if AT.TRIPPED:
            print("GUARD TRIPPED - no further launches:", AT.TRIPPED)
            return 1
        out = os.path.join(RUNS, "attic_" + case)
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        res = {"case": case, "t": time.strftime("%Y-%m-%d %H:%M:%S"), "menus_pak": MENUS}
        t0 = time.time()
        try:
            if case == "attic":
                case_attic(out, res)
            elif case == "launch_basic":
                case_launch(out, res, False)
            elif case == "launch_adv":
                case_launch(out, res, True)
            else:
                print("unknown case", case)
                continue
        except AT.hw.PolicyError as e:
            res["policy_error"] = str(e)
        res["secs"] = int(time.time() - t0)
        res["tripped"] = AT.TRIPPED
        json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1)
        print(json.dumps(res, indent=1)[:3000])
        rc |= 0 if res.get("ok") else 1
    return 1 if AT.TRIPPED else rc


if __name__ == "__main__":
    sys.exit(main())
