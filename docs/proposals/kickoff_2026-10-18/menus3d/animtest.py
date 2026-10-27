"""animtest.py [models] [batch size] - render every candidate stock animation (actor_anims.CAND) on the menu actors (weathers / manon): a row of N actors, one anim each, three shots per batch.
Writes G:/mohaa-hudfeed3/menus3d/animtest/<model>_b<k>_<t>.jpg + legend.json.  Needs gl2env.py install first (ship pk3 for the textures / tiks); the test pk3 is removed at the end."""
import json, os, re, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m3d_run as M
from actor_anims import CAND
E = M.E
E.RES["anim"] = (1920, 720, 0, "s")
MT = os.path.join(E.CLIENT, "home", "maintt")
PK = os.path.join(MT, "zzzzzzzzzzzzzzzz_animtest.pk3")
SHIP = os.path.join(MT, "zzzzzzzzzzzzzz_hzm_menus3d.pk3")
OUT = r"G:\mohaa-hudfeed3\menus3d\animtest"
os.makedirs(OUT, exist_ok=True)
models = (sys.argv[1] if len(sys.argv) > 1 else "weathers,manon").split(",")
N = int(sys.argv[2]) if len(sys.argv) > 2 else 10
names = list(CAND)
batches = [names[i:i + N] for i in range(0, len(names), N)]
zin = zipfile.ZipFile(SHIP)
tik = {m: zin.read("models/human/hzm_menu/%s_menu.tik" % m).decode("latin-1") for m in models}


def make_pk3(model, batch):
    t = tik[model]
    anims = "animations\n{\n\t$path models/human/animation\n" + "".join("\t%s %s\n" % (a, CAND[a]) for a in names) + "}\n"
    t = re.sub(r"animations\s*\{.*\}\s*$", anims, t, flags=re.S)
    sp = 52 if N > 8 else 60
    y0 = (N - 1) / 2.0 * sp
    mods = "".join('scenemodel "models/human/hzm_menu/anim_%s.tik" 0 %.1f 0 180 "%s"\n' % (model, y0 - i * sp, a) for i, a in enumerate(batch))
    urc = ('menu "hzm_animtest" 640 480 NONE 0\nbgcolor 0.12 0.12 0.14 1\nborderstyle NONE\nbgfill 0.12 0.12 0.14 1\nfullscreen 1\nvirtualres 1\n\nresource\nScene3D\n{\nname "animscene"\nrect 0 0 640 480\n'
           + mods + 'scenecam -330 0 52 4 0 0 38\nscenelight -200 0 160 600 1.0 0.95 0.85\nscenelight -250 150 120 500 0.5 0.55 0.7\nscenelight -250 -150 120 500 0.5 0.55 0.7\n}\nend.\n')
    with zipfile.ZipFile(PK, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("models/human/hzm_menu/anim_%s.tik" % model, t)
        z.writestr("ui/hzm_animtest.urc", urc)


legend = {}
w, h, center, lay = E.RES["anim"]
try:
    for model in models:
        for k, batch in enumerate(batches):
            make_pk3(model, batch)
            lines = ["set developer 0", "set ui_menuCenter 0", "wait 9000", "pushmenu hzm_animtest", "wait 1200", "screenshot t0", "wait 1300", "screenshot t1", "wait 1800", "screenshot t2", "echo ^~^~^ MR done", "wait 300", "quit"]
            out = E.launch("animtest_%s_%d" % (model, k), w, h, lines, ["+set", "ui_menuCenter", "0"])
            legend["%s_b%d" % (model, k)] = batch
            for t in ("t0", "t1", "t2"):
                src = os.path.join(out, "%s.tga" % t)
                if os.path.exists(src):
                    from PIL import Image
                    Image.open(src).convert("RGB").save(os.path.join(OUT, "%s_b%d_%s.jpg" % (model, k, t)), quality=88)
            print(model, k, batch, flush=True)
finally:
    if os.path.exists(PK):
        os.remove(PK)
json.dump(legend, open(os.path.join(OUT, "legend.json"), "w"), indent=1)
