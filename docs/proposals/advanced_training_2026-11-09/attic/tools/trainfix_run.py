#!/usr/bin/env python3
"""trainfix_run.py - v1.10.72 user report: on the TRAINING sheet (ui/coop_training.urc) the card pictures vanish on hover.
[trainfix 2026-11-10]

Cause: UIButtonBase::MouseEntered -> UIWindowManager::ActivateControl -> BringToFrontPropogated() (uilib/uibutton.cpp:130,
uiwinman.cpp:429): the hovered card Button is moved to the FRONT and drawn last, and it was opaque (paper bgcolor) with the
mpui_glow_paper hover shader - so it covered its own art, caption and text. The widget event `activate` is the same
ActivateControl call, so `globalwidgetcommand <button> activate` reproduces a hover with no mouse (in_mouse 0, no input).

    python trainfix_run.py [shipped|fixed] ...     default: both
  shipped = the live v1.10.72 paks only (the bug); fixed = + an override pk3 carrying the fixed ui/coop_training.urc
  Each at 16:9 (1920x1080), 21:9 (1920x822) and 4:3 (1440x1080): sheet, hover Basic, hover Advanced, hover BACK, re-hover
  Basic -> stills in H:\\hzm_work\\advtrain-test\\runs\\trainfix_<variant>_<aspect>\\
Clients: at_test.client (harness_window.launch_background, the 1080p screen, muted, input off, local guard judgement).
"""
import os
import shutil
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import at_test as AT  # noqa: E402

FIXED_URC = r"H:\hzm_work\trainfix-mod\ui\coop_training.urc"
H = os.path.join(AT.A, "home")
ASPECTS = {"169": (1920, 1080), "219": (1920, 822), "43": (1440, 1080)}
STEPS = [("sheet", None), ("hover_basic", "F5"), ("hover_adv", "F6"), ("hover_back", "F7"), ("rehover_basic", "F5")]
BINDS = ['bind F5 "globalwidgetcommand cardBasic activate"', 'bind F6 "globalwidgetcommand cardAdv activate"',
         'bind F7 "globalwidgetcommand backBtn activate"', 'bind F8 "pushmenu coop_training"']


def prep(variant):
    mt = os.path.join(H, "maintt")
    os.makedirs(mt, exist_ok=True)
    for fn in os.listdir(mt):          # nothing of the advtrain runs may shadow the live paks here
        if fn.lower().endswith(".pk3"):
            os.remove(os.path.join(mt, fn))
    if variant == "fixed":
        with zipfile.ZipFile(os.path.join(mt, "zzzzzzzzzzzzzzzzzzzzzzzz_trainfix.pk3"), "w", zipfile.ZIP_STORED) as z:
            z.write(FIXED_URC, "ui/coop_training.urc")


def run(variant, asp):
    prep(variant)
    out = os.path.join(AT.RUNS, "trainfix_%s_%s" % (variant, asp))
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    if AT.TRIPPED:
        return {"skipped": "guard"}
    c = AT.client(AT.A, H, [("developer", "1")], [], BINDS, "TF_Alpha", ASPECTS[asp])
    res = {"variant": variant, "aspect": asp}
    with c:
        time.sleep(25)                  # the main menu (3D attic) up
        c.post_key(AT.VK["F8"])
        time.sleep(3)
        for tag, key in STEPS:
            if key:
                c.post_key(AT.VK[key])
                time.sleep(1.5)
            AT.shoot(c, out, tag)
            if AT.guard(c):
                break
    res["tripped"] = AT.TRIPPED
    res["foreign"] = AT.FOREIGN[:5]
    shutil.copyfile(AT.lp(H), os.path.join(out, "qconsole.log"))
    return res


def main():
    variants = sys.argv[1:] or ["shipped", "fixed"]
    for v in variants:
        for asp in ASPECTS:
            print(v, asp, run(v, asp))
            if AT.TRIPPED:
                print("GUARD TRIPPED - stop")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
