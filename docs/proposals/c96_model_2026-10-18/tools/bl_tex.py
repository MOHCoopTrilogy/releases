# Downsample the downloaded 4K PBR maps (untrusted data, read-only) to 2048 and keep them as uint8 arrays for the sheet painter.
#   blender --background --factory-startup --disable-autoexec --python bl_tex.py -- <textures_dir> <out_dir>
import bpy, sys, os
import numpy as np

tdir, out = sys.argv[sys.argv.index('--') + 1:][:2]
os.makedirs(out, exist_ok=True)
names = {'base': 'Mauser_L_Baker_BaseColor.1001.png', 'normal': 'Mauser_L_Baker_Normal.1001.png',
         'rough': 'Mauser_L_Baker_Roughness.1001.png', 'metal': 'Mauser_L_Baker_Metallic.1001.png'}
res = {}
for k, fn in names.items():
    im = bpy.data.images.load(os.path.join(tdir, fn))
    im.colorspace_settings.name = 'Non-Color'
    w, h = im.size
    a = np.empty(w * h * im.channels, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(h, w, im.channels)[:, :, :3]
    if a.shape[2] < 3:
        a = np.repeat(a[:, :, :1], 3, 2)
    # 2x2 box downsample 4096 -> 2048
    a = a.reshape(h // 2, 2, w // 2, 2, 3).mean((1, 3))
    # rows from Blender are bottom-up; flip so row 0 = top (image convention)
    a = a[::-1]
    res[k] = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    print(k, im.size, im.channels, a.shape, res[k].mean((0, 1)))
    bpy.data.images.remove(im)
np.savez_compressed(os.path.join(out, 'maps2048.npz'), **res)
