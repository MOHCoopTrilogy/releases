"""gifs.py <rundir> <outdir> [label] - one GIF per captured event (ac_<map>_<ev>_NNN.jpg), 640x360, kept < 20 MB."""
import collections, os, re, sys
from PIL import Image

run, out = sys.argv[1], sys.argv[2]
label = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(run.rstrip("/\\"))
os.makedirs(out, exist_ok=True)
groups = collections.defaultdict(list)
for m in sorted(os.listdir(run)):
    d = os.path.join(run, m)
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        mm = re.match(r"ac_(\w+?)_(para|binoc|stuka|down)_(\d+)\.jpg$", fn)
        if mm:
            groups[(mm.group(1), mm.group(2))].append(os.path.join(d, fn))
for (m, ev), files in sorted(groups.items()):
    files.sort()
    W, H = 640, 360
    frames = [Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS) for f in files]
    p = os.path.join(out, "%s_%s_%s.gif" % (label, m, ev))
    while True:
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=110, loop=0, optimize=True)
        if os.path.getsize(p) < 19 * 1024 * 1024 or W <= 320:
            break
        W, H = int(W * 0.8), int(H * 0.8)
        frames = [f.resize((W, H), Image.LANCZOS) for f in frames]
    print(p, len(frames), os.path.getsize(p))
