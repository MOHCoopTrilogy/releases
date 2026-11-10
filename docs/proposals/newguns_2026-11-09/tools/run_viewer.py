"""Weapon-viewer stills of the new guns (attic -> rack -> e<NNN>), the wpnviewer harness on the private client G:\\mohaa-newguns with
this branch's overlay (run_gun.overlay) and the 3D-menus pak. Controlled light: the in-map stills read near-black on m2l1.
    python run_viewer.py <tag> <first> <last> [<first> <last> ...]
"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_gun as G
W = G.W


def main():
    tag = sys.argv[1]
    rng = [int(x) for x in sys.argv[2:]]
    G.overlay()
    shutil.copyfile(W.MENUS3D, os.path.join(W.MAINTT, "zzzzzzzzzzzzzz_hzm_menus3d.pk3"))
    s = W.Script()
    W.open_viewer(s)
    for a, b in zip(rng[::2], rng[1::2]):
        for n in range(a, b + 1):
            s.cmd("exec ui/wpnview/e%03d.cfg" % n, 700)
            s.cmd("screenshotJPEG w_%03d" % n, 300)
    s.cmd("quit", 0)
    W.launch(tag, os.environ.get("NG_RES", "1080"), s, lines=["set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0"],
             budget=150 + 2 * sum(b - a + 1 for a, b in zip(rng[::2], rng[1::2])))


if __name__ == "__main__":
    main()
