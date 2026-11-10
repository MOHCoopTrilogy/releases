"""patch_close73.py <mod ui dir> - v1.10.73: every copy of a 3D room gets its closure models right after the room's floor model
(idempotent), and the attic copies that never had the outside get it.

  hub_floor1 -> hzm_hub_close (close_hub73.py): multiplayer.urc, the hzm_mpui_scene_*.inc copies, hzm_wpnview.urc
  atc_floor1 -> hzm_atc_close (close_ring73.py: the attic's open back end), hzm_atc_cracks (crack_backer73.py: the wing's corner
                crack - the user's 'white sliver'), hzm_hatch + hzm_hatch_below (gen_hatch73.py: the floor has a hole there now,
                so EVERY attic copy needs the stairwell under it): main.urc, the New Game copies, records3d, medals3d
records3d / medals3d: the attic room without its outside - the gable window looked onto the void at 21:9 (voidraster.py). The
weather lines (models + scenewx roles) of main.urc's atticscene are copied in before their scenecam.
"""
import os, re, sys

ui = sys.argv[1]
CLOSE = [("hub_floor1", ["hzm_hub_close"]),
         ("atc_floor1", ["hzm_atc_close", "hzm_atc_cracks", "hzm_hatch", "hzm_hatch_below"])]
n = 0
for f in sorted(os.listdir(ui)):
    if not f.lower().endswith((".urc", ".inc")):
        continue
    p = os.path.join(ui, f)
    t = open(p, encoding="latin-1", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    t0 = t
    for floor, adds in CLOSE:
        new = [a for a in adds if ('"models/menu/%s.tik"' % a) not in t]
        if not new:
            continue
        t = re.sub(r'(scenemodel "models/menu/%s\.tik" 0 0 0 0\r?\n)' % floor,
                   lambda m: m.group(1) + "".join('scenemodel "models/menu/%s.tik" 0 0 0 0' % a + nl for a in new), t)
    if t != t0:
        open(p, "w", encoding="latin-1", newline="").write(t)
        n += 1
        print("  %s" % f)
print("patch_close73: %d files" % n)

mt = open(os.path.join(ui, "main.urc"), encoding="latin-1").read().replace("\r\n", "\n")
blk = re.search(r'(?m)^Scene3D\s*\n\{\nname "atticscene"(.*?)\n\}', mt, re.S).group(1)
WX = [l for l in blk.split("\n") if l.startswith('scenemodel "models/menu/hzm_wx_') or l.startswith("scenewx ")]
for f in ("hzm_records3d.urc", "hzm_medals3d.urc"):
    p = os.path.join(ui, f)
    t = open(p, encoding="latin-1", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    if "hzm_wx_" in t:
        continue
    i = t.index(nl + "scenecam ")
    t = t[:i] + nl + nl.join(WX) + t[i:]
    open(p, "w", encoding="latin-1", newline="").write(t)
    print("  %s: + %d weather lines" % (f, len(WX)))
