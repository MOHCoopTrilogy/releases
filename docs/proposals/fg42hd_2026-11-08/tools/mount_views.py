"""offline check of the scoped FG 42's scope mount (QA #4: "you're seeing snow" - daylight between mount and receiver): flat-shaded
painter's renders of coop_fg42hd.skd around the scope from the side, from below-left, from behind-below and from the front, on a
bright background so any gap shows as light. -> build/mount_views.png
    python mount_views.py
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
import skd as K

HERE = os.path.dirname(os.path.abspath(__file__))
d = K.read(open(os.path.join(HERE, '..', 'ship', 'models', 'weapons', 'fg42', 'coop_fg42hd.skd'), 'rb').read())
TRIS = []
for s in d['surfaces']:
    P = np.array([v['pos'] for v in s['verts']], float)
    for t in s['tris']:
        q = P[list(t)]
        if q[:, 0].max() > -12 and q[:, 0].min() < 12 and q[:, 2].min() < 1.0:
            TRIS.append((s['name'], q))
COL = {'fg42scope': (70, 74, 82), 'fg42lens': (40, 60, 90), 'coop_handle': (90, 90, 90)}


def view(yaw, pitch, size=420, scale=22.0):
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    R = np.array([[cy, sy, 0], [-sy, cy, 0], [0, 0, 1]]) @ np.eye(3)
    R = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) @ R
    img = Image.new('RGB', (size, size), (235, 238, 242))
    dr = ImageDraw.Draw(img)
    c = np.array([0.5, 0.0, -4.0])
    L = np.array([0.3, -0.5, -0.8]); L /= np.linalg.norm(L)
    items = []
    for name, q in TRIS:
        v = (q - c) @ R.T
        n = np.cross(q[1] - q[0], q[2] - q[0]); ln = np.linalg.norm(n)
        if ln < 1e-9:
            continue
        n = -n / ln                                                # retail winding: cross . n < 0
        if (n @ R.T)[1] > 0.02:                                      # back face (camera looks along +y in view space)
            continue
        shade = 0.35 + 0.65 * max(0.0, float(-(n @ L)))
        base = COL.get(name, (110, 85, 62) if name.startswith('fg42hd') and not name.startswith('fg42hdmt') else (60, 64, 72))
        items.append((v[:, 1].mean(), [(size / 2 + p[0] * scale, size / 2 + p[2] * scale) for p in v],
                      tuple(int(ch * shade) for ch in base)))
    for _dep, pts, col in sorted(items, key=lambda it: -it[0]):
        dr.polygon(pts, fill=col)
    return img


views = [('side (right)', math.radians(0), math.radians(0)), ('below-left', math.radians(-35), math.radians(-30)),
         ('behind-below', math.radians(-80), math.radians(-25)), ('front-below', math.radians(80), math.radians(-25))]
out = Image.new('RGB', (420 * 4, 440), (20, 20, 20))
dr = ImageDraw.Draw(out)
for i, (lab, yw, pt) in enumerate(views):
    out.paste(view(yw, pt), (i * 420, 20))
    dr.text((i * 420 + 6, 4), lab, fill=(230, 230, 230))
out.save(os.path.join(HERE, '..', 'build', 'mount_views.png'))
print('ok')
