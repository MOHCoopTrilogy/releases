"""polish_pak.py <in menus3d pk3> <add dir> <out pk3> - the attic art pass applied to the out-of-band menus3d pak.

BUILD ORDER of zzzzzzzzzzzzzz_hzm_menus3d.pk3:  make_stage3 / build_models2 (attic) -> make_mphub3d.py (hub) -> make_newgame3d.py
(new game map) -> THIS (adds / replaces the files under <add dir>: the gramophone card art, re-cut attic models, retouched atlases).
Every entry of the input is copied byte-for-byte unless <add dir> has the same path; entries are written sorted with a fixed
timestamp so the same inputs give the same pak (the updater compares sha256)."""
import os, sys, zipfile

src, add, out = sys.argv[1:4]
files = {}
with zipfile.ZipFile(src) as z:
    for i in z.infolist():
        if not i.is_dir():
            files[i.filename] = z.read(i)
n_rep = n_new = 0
for r, _, fs in os.walk(add):
    for f in fs:
        p = os.path.join(r, f)
        k = os.path.relpath(p, add).replace("\\", "/")
        if k.split("/")[0] not in ("models", "textures", "scripts", "sound", "ui", "video"):      # video: v1.10.68 the screen preview (RoQ)
            continue                    # notes beside the add dir (gram_spindle.txt) never go in the pak
        if k in files:
            n_rep += 1
        else:
            n_new += 1
        files[k] = open(p, "rb").read()
os.makedirs(os.path.dirname(out), exist_ok=True)
tmp = out + ".tmp"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
    for k in sorted(files):
        zi = zipfile.ZipInfo(k, (2026, 11, 2, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, files[k])
os.replace(tmp, out)
print("%s: %d entries (%d replaced, %d new), %d bytes" % (out, len(files), n_rep, n_new, os.path.getsize(out)))
