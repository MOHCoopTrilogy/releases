"""finishes2 - the PAINT LAYER for the paint / camo finishes (approved 2026-11-09: max side 1024 px (user: higher quality; was 384), the gun's own full-res
texture underneath). Per gun sheet:
  <sheet>_mask.tga      RGBA, alpha = where the coat is (the gun's wear mask: muzzle, bore, sights, bolt and trigger bare,
                        island edges worn) x the chip tile. Shared by every paint / camo finish of that sheet.
  <sheet>_<fin>.jpg     the coat, PREMULTIPLIED by that alpha (black where bare), q85.
The shader draws the gun's own texture, then the mask darkens where the coat goes (GL_ZERO GL_ONE_MINUS_SRC_ALPHA), then the
premultiplied coat is added and lit (GL_ONE GL_ONE, rgbGen lightingSpherical):  out = base*(1-a) + coat*a*light.
    python fs2_layers.py test            Kar98k splitter + whitewash: layers, two variant tiks, a test pak (private client only)
    python fs2_layers.py run <fin>       one boot of the private client: hip shots + the weapon viewer (queue-aware caller)
"""
import io, os, re, shutil, sys, zipfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finishlib as fl  # noqa: E402
import finish_sheet as fs  # noqa: E402
import uvview  # noqa: E402

CAP = 1024                       # user 2026-11-09: "higher quality" (was 384)
PAINT_FINS = ('whitewash', 'dak', 'kriegsmarine', 'airborne', 'splitter', 'pea', 'telo', 'amoeba')
TEST_OUT = os.path.join("H:" + os.sep, "hzm_work", "finishes2_test")
MOD = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "..", "hzm-mohaa-coop-mod")
PAK = "zzzzzzzzzzzzzzzzzzzzzz_fs2_test.pk3"


def coat(fin, base, ctx):
    """(rgb, alpha) of the coat alone - the same recipe as finish_sheet.finish_tex, without the bare metal mixed in"""
    H, W = base.shape[:2]
    m = ctx['mask']
    chips = fs.tiled(fs.tile('wear_chips'), H, W, ctx['rep']('wear_chips'))[..., 3]
    a = m * chips
    if fin == 'airborne':
        rgb = fs.coat(base, (88, 86, 56))
    elif fin == 'dak':
        rgb = fs.coat(base, (194, 166, 106))
    elif fin == 'kriegsmarine':
        rgb = fs.coat(base, (52, 56, 60), keep=0.45)
        from PIL import ImageFilter
        salt = np.asarray(Image.fromarray((fs.tiled(fs.tile('camo_pea'), H, W, ctx['rep']('camo_pea'))[..., 0] * 255)
                                          .astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(1, W // 120))), float) / 255
        rgb = fs.over(rgb, np.array([0.84, 0.86, 0.85]), np.clip((salt - 0.55) * 3.0, 0, 1) * 0.45)
        r = fs.rust_runs(ctx['P'], ctx['lo'], ctx['hi'])
        rgb = fs.over(rgb, np.array([0.46, 0.24, 0.11]) * (0.7 + 0.3 * fs.shade(base)), np.clip(r * 0.75, 0, 0.75))
    elif fin in ('splitter', 'pea', 'telo', 'amoeba'):
        pat = fs.tiled(fs.tile('camo_' + fin), H, W, ctx['rep']('camo_' + fin))[..., :3]
        pat = np.clip(pat * {'splitter': 1.0, 'pea': 1.0, 'telo': 1.0, 'amoeba': 1.0}[fin], 0, 1)   # the tiles carry true colours
        rgb = np.clip(pat * fs.paint_shade(base), 0, 1)
    elif fin == 'whitewash':
        w = fs.tiled(fs.tile('camo_whitewash'), H, W, ctx['rep']('camo_whitewash'))[..., 3]
        rgb = np.clip(np.array([0.84, 0.84, 0.82]) * fs.paint_shade(base) * (0.88 + 0.12 * w[..., None]), 0, 1)
        # hand-brushed: mostly white, the dark showing through BETWEEN the brush strokes (the tile's own streaks) and at the
        # worn edges - no blocky chip patches (coordinator QA: the Colt read as angular splinter patches)
        a = np.clip(np.clip(0.30 + 0.85 * w, 0, 1) * m ** 2 * (0.55 + 0.45 * chips), 0, 0.97)
    else:
        raise KeyError(fin)
    return rgb, a


def layers(g, shader, fins):
    """-> (path of the sheet the shader loads, mask RGBA Image, {fin: premultiplied RGB Image}) at CAP on the long side.
    The mask is the SAME for every finish except whitewash, whose brushed coverage is its own (it ships its own mask)."""
    m, path, pk, im, blk = uvview.shader_image(shader)
    k = min(1.0, CAP / max(im.size))
    W, H = max(8, round(im.width * k)), max(8, round(im.height * k))
    base = np.asarray(im.convert('RGBA').resize((W, H), Image.LANCZOS), float) / 255.0
    ctx = fs.build_ctx(g, shader, H, W)
    out, masks = {}, {}
    for f in fins:
        rgb, a = coat(f, base, ctx)
        out[f] = Image.fromarray((np.clip(rgb * a[..., None], 0, 1) * 255).astype(np.uint8), 'RGB')
        masks[f] = Image.fromarray(np.dstack([np.full((H, W, 3), 255, np.uint8), (np.clip(a, 0, 1) * 255).astype(np.uint8)]), 'RGBA')
    return path, masks, out


def shader_block(name, base_path, mask_path, coat_path):
    base = re.sub(r'\.(dds|jpg|png)$', '.tga', base_path, flags=re.I)        # as the stock shaders name it (.dds wins at load)
    return "\n".join([name, "{", "\tqer_editorimage %s" % base,
                      "\t{", "\t\tmap %s" % base, "\t\trgbGen lightingSpherical", "\t}",
                      "\t{", "\t\tmap %s" % mask_path,
                      # a grey png / jpg mask carries the coverage in its value, a tga (the first look test) in alpha
                      "\t\tblendFunc GL_ZERO %s" % ("GL_ONE_MINUS_SRC_ALPHA" if mask_path.endswith('.tga') else "GL_ONE_MINUS_SRC_COLOR"),
                      "\t}",
                      "\t{", "\t\tmap %s" % coat_path, "\t\tblendFunc GL_ONE GL_ONE", "\t\trgbGen lightingSpherical", "\t}",
                      "}", ""])


def variant_tik(base_text, display, rank, surf_map):
    t = re.sub(r'(?mi)^(\s*name\s+)"([^"]+)"', lambda m: '%s"%s (%s)"' % (m.group(1), m.group(2), display), base_text, count=1)
    t = re.sub(r"(?mi)^(\s*rank\s+)\d+\s+\d+", lambda m: "%s%d %d" % (m.group(1), rank, rank), t, count=1)
    return re.sub(r"(?mi)^(\s*surface\s+\S+\s+shader\s+)(\S+)", lambda m: m.group(1) + surf_map.get(m.group(2), m.group(2)), t)


def test():
    os.makedirs(TEST_OUT, exist_ok=True)
    tik = "models/weapons/kar98.tik"
    g = fl.load_gun(tik)
    fins = ('splitter', 'whitewash')
    path, masks, coats = layers(g, 'KAR98', fins)
    files, shaders = {}, []
    base_text = open(os.path.join(MOD, "models", "weapons", "kar98.tik"), encoding="latin-1").read()
    for i, f in enumerate(fins):
        mp = "textures/coop_skins2/kar98/KAR98_mask%s.tga" % ("_ww" if f == 'whitewash' else "")
        cp = "textures/coop_skins2/kar98/KAR98_%s.jpg" % f
        b = io.BytesIO(); masks[f].save(b, 'TGA'); files[mp] = b.getvalue()
        b = io.BytesIO(); coats[f].save(b, 'JPEG', quality=85); files[cp] = b.getvalue()
        sname = "coop_fs2_kar98_%s" % f
        shaders.append(shader_block(sname, path, mp, cp))
        files["models/weapons/kar98_fs2_%s.tik" % f] = variant_tik(base_text, f.capitalize(), 1240 + i, {'KAR98': sname}).encode('latin-1')
        coats[f].save(os.path.join(TEST_OUT, 'layer_%s.jpg' % f))
        masks[f].split()[3].save(os.path.join(TEST_OUT, 'layer_%s_mask.png' % f))
    files["scripts/coop_fs2_test.shader"] = "\n".join(shaders).encode()
    # one pak per finish: the look test also SHADOWS kar98.tik with that finish's shader (no cheats needed: the normal loadout
    # gives it and the viewer shows it); test paks only go on the private client and come off after each run
    for f in fins:
        over = re.sub(r"(?mi)^(\s*surface\s+\S+\s+shader\s+)KAR98[ \t]*$", lambda m: m.group(1) + "coop_fs2_kar98_" + f, base_text)
        pak = os.path.join(TEST_OUT, "fs2_layers_kar98_%s.pk3" % f)
        with zipfile.ZipFile(pak, 'w', zipfile.ZIP_DEFLATED) as z:
            for n, d in files.items():
                z.writestr(n, d)
            z.writestr("models/weapons/kar98.tik", over.encode('latin-1'))
        print("pak", pak, os.path.getsize(pak) // 1024, "KB")


def run(fin):
    sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools")
    import wpnview_run as W
    W.RES.update({"uw": (3440, 1440, 0)})
    dst = os.path.join(W.MAINTT, PAK)
    shutil.copyfile(os.path.join(TEST_OUT, "fs2_layers_kar98_%s.pk3" % fin), dst)
    try:
        s = W.Script()
        s.cmd("echo ^~^~^ FS boot", 85000)
        s.cmd("+attack", 300)
        s.cmd("-attack", 7000)
        s.cmd("exec ui/loadout/w03_s1.cfg", 6000)       # the normal loadout gives kar98.tik, which the test pak shadows
        s.cmd('use "Mauser KAR 98K"', 3000)
        s.cmd("screenshotJPEG fs_00_hip", 600)
        s.cmd("+left", 120)
        s.cmd("-left", 600)
        s.cmd("screenshotJPEG fs_01_hip_turn", 400)
        s.cmd("reload", 900)
        s.cmd("screenshotJPEG fs_02_reload", 500)
        s.cmd("disconnect", 6000)
        s.cmd("exec ui/hzm_attic_go_rack.cfg", 2500)                     # the attic weapon viewer
        s.cmd("exec ui/wpnview/e020.cfg", 600)
        s.cmd("wait 1", 900)
        s.cmd("screenshotJPEG fs_03_viewer", 400)
        s.cmd("set ui_wvSpin 200", 700)
        s.cmd("screenshotJPEG fs_04_viewer_left", 400)
        s.cmd("quit", 0)
        W.launch("fs2L_%s" % fin, os.environ.get("WV_RES", "uw"), s,
                 lines=['seta coop_lo2 ""', 'seta coop_loA2 ""', 'seta coop_loFA2 ""', "set g_gametype 2", "set cheats 1",
                        "set coop_dev 1", "set coop_lockLoadout 0", "set ui_dmmap m2l1", "ui_startdmmap 2"], budget=260)
    finally:
        if os.path.exists(dst):
            os.remove(dst)


if __name__ == '__main__':
    if sys.argv[1] == 'test':
        test()
    else:
        run(sys.argv[2])
