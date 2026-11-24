"""fb_to_layer.py <blender smoke dir> <name> <fps> [--n 40] [--px 512] - a rendered smoke set -> the Phase 1 fx layer.

Frames go through flipbook.py (union crop, colour bled into the clear border, straight alpha), are stored as PNG
(the engine's image loader reads png; ~10x smaller than TGA in git) under docs/tools/assets/fx/pak_p1/textures/coop_fx/fx/
<name>NNN.png, and the shader `cfx2_<name>` (animMapOnce <fps>, blend, rgb + alpha from the particle) is (re)written in
docs/tools/assets/fx/pak_p1/scripts/coop_fx_p1_flip.shader. Also writes a hero contact sheet next to the frames source.
Our own renders (Blender, docs/proposals/smokefire_2026-11-24/tools/mk_smoke.py): no third-party art."""
import glob, os, re, subprocess, sys
from PIL import Image

src, name, fps = sys.argv[1], sys.argv[2], float(sys.argv[3])
n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 40
px = int(sys.argv[sys.argv.index("--px") + 1]) if "--px" in sys.argv else 512
HERE = os.path.dirname(os.path.abspath(__file__))
LAYER = os.path.join(HERE, "..", "..", "..", "tools", "assets", "fx", "pak_p1")
TEX = os.path.join(LAYER, "textures", "coop_fx", "fx")
SH = os.path.join(LAYER, "scripts", "coop_fx_p1_flip.shader")
tmp = os.path.join(os.path.dirname(src.rstrip("/\\")), "tga_" + name)
os.makedirs(tmp, exist_ok=True); os.makedirs(TEX, exist_ok=True)
sheet = os.path.join(os.path.dirname(src.rstrip("/\\")), "sheet_%s.jpg" % name)
subprocess.check_call([sys.executable, os.path.join(HERE, "flipbook.py"), src, tmp, name, "--kind", "smoke", "--px", str(px),
                       "--n", str(n), "--sheet", sheet])
for f in glob.glob(os.path.join(TEX, name + "[0-9][0-9][0-9].png")):
    os.remove(f)
frames = sorted(glob.glob(os.path.join(tmp, name + "[0-9][0-9][0-9].tga")))
for f in frames:
    Image.open(f).save(os.path.join(TEX, os.path.basename(f)[:-4] + ".png"), optimize=True)
paths = " ".join("textures/coop_fx/fx/%s%03d.png" % (name, k + 1) for k in range(len(frames)))
# spritescale 256/px: a 512 px set keeps the world size a 256 px fx_1025 puff had at the same tik `scale`
block = ("cfx2_%s\n{\n\tcull none\n\tspriteGen parallel_oriented\n\tspritescale %g\n\t{\n\t\tanimMapOnce %g %s\n"
         "\t\tblendfunc blend\n\t\trgbGen vertex\n\t\talphaGen vertex\n\t}\n}\n" % (name, 256.0 / px, fps, paths))
txt = open(SH, encoding="latin-1").read() if os.path.isfile(SH) else (
    "// [smoke&fire Phase 1] our own smoke flipbooks (mk_smoke.py -> fb_to_layer.py). Generated - do not edit by hand.\n\n")
txt = re.sub(r"(?s)cfx2_%s\n\{.*?\n\}\n" % re.escape(name), "", txt)
open(SH, "w", encoding="latin-1", newline="\n").write(txt.rstrip("\n") + "\n\n" + block)
print("cfx2_%s: %d frames %d px @ %g fps; sheet %s" % (name, len(frames), px, fps, sheet))
