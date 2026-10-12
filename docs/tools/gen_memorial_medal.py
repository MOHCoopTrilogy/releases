"""The launch memorial's badge: the ANIMATED loading medal (old <-> new MOHAA badge), at the top of the card.

[user 2026-10-12] "the top badge should be the animated mohaa badge we built, right now that sits at the bottom. There
should only be one badge, at the top, and it should be the animated one."

The loading screen's morph textures are 256 px, sized for a medal 0.11 of the screen height. On the memorial the
badge is 0.24 of the screen height (352 px at 1440p), which would magnify them 1.5x. This renders the SAME morph
(gen_loadscreen_medal.py, same levels, same waves, same speed and period) at 512 px into ui/hzm_memorial/ and writes
its shader, hzmMemorialMedalMorph, into scripts/coop_memorial.shader after the card's own shader.

usage: python docs/tools/gen_memorial_medal.py [--check]
"""
import os
import sys

os.environ["HZM_MEDAL_SIZE"] = "512"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_loadscreen_medal as g  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
OUTDIR = os.path.join(MOD, "ui", "hzm_memorial")
SHADER = os.path.join(MOD, "scripts", "coop_memorial.shader")
MARK = "// ---- GENERATED below by docs/tools/gen_memorial_medal.py - do not hand-edit ----\n"
SPEED, PERIOD = 45.0, 16.0          # the loading medal's live values (scripts/coop_loadmorph.shader)

assert g.SIZE == 512, "gen_loadscreen_medal.py did not honour HZM_MEDAL_SIZE"
g.MORPH_MODERN_PX = 460             # 230 of 256, doubled: the same margin in texels x2 (mip-safe, bug-3059)
g.MORPH_ORIG_PX = 448               # the 32 px original at exactly 14x
g.MORPH_TEX = "ui/hzm_memorial/morph_%s.tga"
# what the engine needs to know (client/cl_ui.cpp UI_MemorialDraw): the quad is this much larger than the medal
QUAD_GROW = g.SIZE / float(g.MORPH_MODERN_PX)


def shader_text():
    t = g.morph_shader(SPEED, PERIOD)
    assert t.count("hzmLoadMedalMorph") == 1
    t = t.replace("hzmLoadMedalMorph", "hzmMemorialMedalMorph")
    t = t.replace("LOOPING LOADING MEDAL (design v4)", "the same looping medal for the LAUNCH MEMORIAL, 512 px")
    # the card fades by colour (rgbGen global, set by the exe); without the same on every stage the medal stayed at
    # full brightness through the card's fade and popped off at the end (seen in the first in-engine capture)
    n = t.count("\t\ttcMod rotate")
    t = t.replace("\t\ttcMod rotate", "\t\trgbGen global\n\t\ttcMod rotate")
    assert n == 6 and t.count("rgbGen global") == 6
    return t


def main():
    check = "--check" in sys.argv
    files = g.build_morph()
    cur = open(SHADER, "rb").read().decode("ascii")
    head = cur.split(MARK)[0]
    if not head.endswith("\n"):
        head += "\n"
    new = head + MARK + shader_text()
    bad = []
    for name, data in sorted(files.items()):
        p = os.path.join(OUTDIR, name)
        if not os.path.exists(p) or open(p, "rb").read() != data:
            bad.append(p)
            if not check:
                open(p, "wb").write(data)
    if new != cur:
        bad.append(SHADER)
        if not check:
            open(SHADER, "wb").write(new.encode("ascii"))
    if check:
        print("check:", "OK" if not bad else "STALE " + ", ".join(bad))
        return 1 if bad else 0
    print("wrote %d textures (%d px) + shader hzmMemorialMedalMorph; quad grow %.4f" % (len(files), g.SIZE, QUAD_GROW))
    return 0


if __name__ == "__main__":
    sys.exit(main())
