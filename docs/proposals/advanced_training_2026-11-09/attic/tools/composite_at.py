"""composite_at.py <in-game home still> <base render> <prop render> <prop npz> <out.jpg> [crop x0,y0,x1,y1] [model name]
The prop (pixels whose model id is <model name>, default hzm_at_target) pasted over an in-game home-view still, so the actors
(the officer, Manon - atticview cannot draw them) stay in front where the still shows them: an actor pixel is one where the still
differs strongly from the base render inside the actors' screen boxes. QA aid only (no game launch)."""
import sys
import numpy as np
from PIL import Image
a = sys.argv[1:]
still = np.asarray(Image.open(a[0]).convert("RGB").resize((1920, 1080)), np.float32)
base = np.asarray(Image.open(a[1]).convert("RGB"), np.float32)
prop = np.asarray(Image.open(a[2]).convert("RGB"), np.float32)
d = np.load(a[3])
name = a[6] if len(a) > 6 else "hzm_at_target"
ids = [i for i, m in enumerate(d["models"]) if str(m) in (name, name + "_lit")]
pm = np.isin(d["mid"], ids)
diff = np.abs(still - base).sum(-1)
actor = np.zeros_like(pm)
for x0, y0, x1, y1 in ((230, 520, 520, 1080), (830, 440, 920, 720)):      # the officer, Manon (home view, 1080p)
    actor[y0:y1, x0:x1] = diff[y0:y1, x0:x1] > 90
# the shadow decal is blended: take the prop render wherever it differs from the base render there too
sh = (np.abs(prop - base).sum(-1) > 6) & ~pm
out = still.copy()
m = (pm | sh) & ~actor
out[m] = prop[m] if True else out[m]
out[sh & ~actor] = still[sh & ~actor] * (prop[sh & ~actor] / np.maximum(base[sh & ~actor], 1)).clip(0, 1.2)
im = Image.fromarray(np.uint8(out.clip(0, 255)))
if len(a) > 5 and a[5] != "-":
    im = im.crop(tuple(int(v) for v in a[5].split(",")))
im.save(a[4], quality=92)
print(a[4], "prop px", int(pm.sum()), "behind an actor", int((pm & actor).sum()))
