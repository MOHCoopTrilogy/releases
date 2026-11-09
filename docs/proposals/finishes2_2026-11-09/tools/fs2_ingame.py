"""finishes2 - in-game look test (private client G:\\mohaa-wpnview only, never the live install): bake a finish into the gun's own
sheet exactly as the offline preview composites it (finish_sheet.finish_tex + both verified decals), ship it as a TEST pak that
shadows the gun's texture, boot m2l1 with the gun and take hip shots. A look test only - the shipping finishes are shader
composites (shared tiles, per-gun tcMod), built later through gen_skins.
    python fs2_ingame.py bake <fin> [...]          -> H:\\hzm_work\\finishes2_test\\fs2_<fin>.pk3
    python fs2_ingame.py run <fin>                 one boot (the caller holds the display-queue turn); the pak is removed after
Env: FS_TIK (default models/weapons/kar98.tik), FS_CLASS (rifle), FS_GID (03), FS_GUN ("Mauser KAR 98K"), FS_SHADER (KAR98)
"""
import io, os, shutil, sys, zipfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finishlib as fl  # noqa: E402
import finish_sheet as fs  # noqa: E402
import orient_check as oc  # noqa: E402
import uvview  # noqa: E402

OUT = os.path.join("H:" + os.sep, "hzm_work", "finishes2_test")
GUNS = {'kar98': ("models/weapons/kar98.tik", "rifle", "03", "Mauser KAR 98K", "KAR98"),
        'mp40': ("models/weapons/mp40.tik", "smg", "26", "MP40", "MP40")}
TIK, CLS, GID, GUN, SHADER = GUNS['kar98']


def use_gun(key):
    global TIK, CLS, GID, GUN, SHADER
    TIK, CLS, GID, GUN, SHADER = GUNS[key]
PAK = "zzzzzzzzzzzzzzzzzzzzzz_fs2_test.pk3"
MAXW = 2048


def bake(fin, tag=None):
    tag = tag or fin
    g = fl.load_gun(TIK)
    m, path, pk, im, blk = uvview.shader_image(SHADER)
    base = np.asarray(im.convert('RGBA'), float) / 255.0
    if base.shape[1] > MAXW:                                  # a test pak: half res is plenty for a hip shot
        k = MAXW / base.shape[1]
        base = np.asarray(im.convert('RGBA').resize((MAXW, int(base.shape[0] * k)), Image.LANCZOS), float) / 255.0
    ctx = fs.build_ctx(g, SHADER, *base.shape[:2])
    img = np.dstack([fs.finish_tex(fin, base, ctx), base[..., 3:4]])
    german = any(k in TIK.lower() for k in fs.GERMAN)
    dname = fs.DECAL_OF.get(fin) or (('souvenir' if german else 'waa') if fin == 'captured' else None)
    if dname:
        pa = oc.place_verified(g, oc.KIND.get(CLS, 'grip'), side=fl.ARMORY)[0]
        pf = oc.place_verified(g, 'receiver', side=fl.FIRSTPERSON, avoid=[pa] if pa else [], allow_shared=False)[0]
        for pl in (pa, pf):
            if pl is not None and pl['shader'] == SHADER:
                img = fl.stamp(img, pl, fs.decal(dname))
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), 'RGBA')
    os.makedirs(OUT, exist_ok=True)
    out.convert('RGB').resize((out.width // 4, out.height // 4)).save(os.path.join(OUT, 'fs2_%s_preview.jpg' % tag), quality=85)
    buf = io.BytesIO()
    out.save(buf, format='DDS', pixel_format='DXT5')         # DXT5: the renderer's DDS loader rejects Pillow's BGRA uncompressed layout
    pak = os.path.join(OUT, 'fs2_%s.pk3' % tag)
    with zipfile.ZipFile(pak, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(path, buf.getvalue())
    print('baked', tag, path, out.size, os.path.getsize(pak) // 1024, 'KB', flush=True)
    return pak


def run(fin):
    sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools")
    import wpnview_run as W
    W.RES.update({"uw": (3440, 1440, 0)})
    dst = os.path.join(W.MAINTT, PAK)
    shutil.copyfile(os.path.join(OUT, 'fs2_%s.pk3' % fin), dst)
    try:
        s = W.Script()
        s.cmd("echo ^~^~^ FS boot", int(os.environ.get("WV_BOOT", "85000")))
        s.cmd("+attack", 300)                # past the mission briefing ("press fire to join the battle"), as run_ab does
        s.cmd("-attack", 7000)
        s.cmd("exec ui/loadout/w%s_s1.cfg" % GID, 6000)
        s.cmd('use "%s"' % GUN, 3000)
        s.cmd("screenshotJPEG fs_00_hip", 600)
        s.cmd("+left", 120)                 # the view swings: the gun's left side and the light shift
        s.cmd("-left", 600)
        s.cmd("screenshotJPEG fs_01_hip_turn", 400)
        s.cmd("+movedown", 900)
        s.cmd("screenshotJPEG fs_02_crouch", 400)
        s.cmd("-movedown", 600)
        s.cmd("reload", 900)
        s.cmd("screenshotJPEG fs_03_reload", 500)
        s.cmd("quit", 0)
        W.launch("fs2_%s" % fin, os.environ.get("WV_RES", "uw"), s,
                 lines=['seta coop_lo2 ""', 'seta coop_loA2 ""', 'seta coop_loFA2 ""', "set g_gametype 2", "set cheats 1",
                        "set coop_dev 1", "set coop_lockLoadout 0", "set ui_dmmap m2l1", "ui_startdmmap 2"], budget=240)
    finally:
        if os.path.exists(dst):
            os.remove(dst)                  # never leave the test pak on the client (the gun-clipping runs share it)


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    for a in args:                                  # <finish>[@<gun>]  (gun: kar98 / mp40)
        f, _, gk = a.partition('@')
        use_gun(gk or 'kar98')
        tag = f if not gk or gk == 'kar98' else '%s_%s' % (f, gk)
        bake(f, tag) if cmd == 'bake' else run(tag)
