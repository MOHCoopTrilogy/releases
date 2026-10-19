"""build_mockups.py - composite the Armory redesign mock-ups (A and B) from REAL assets: see bm_core.py / layouts.py.

    python build_mockups.py      # ../mockup_A.jpg, ../mockup_B.jpg and the 1024x768 renders (ARM_ASSETS overrides the assets dir)
"""
import os
import layouts
from bm_core import OUTD


def save(im, name):
    p = os.path.join(OUTD, name)
    im.save(p, quality=93)
    print("wrote", p, im.size)


def main():
    for nm, fn in (("A", layouts.build_A), ("B", layouts.build_B)):
        save(fn(1920, 1080), "mockup_%s.jpg" % nm)
        save(fn(1024, 768), "mockup_%s_1024x768.jpg" % nm)


if __name__ == "__main__":
    main()
