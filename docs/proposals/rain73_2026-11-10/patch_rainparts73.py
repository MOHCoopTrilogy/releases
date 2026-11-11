"""patch_rainparts73.py <mod ui dir> - rain73: retire the static rain from every scene (the engine's dynamic rain replaces it):
the two scrolling streak sheets (hzm_wx_rain_far / _near) and the two static drop layers (hzm_wx_drops on the gable pane,
hzm_wx_skydrops on the skylight) - their scenemodel and scenewx lines go. Idempotent."""
import os, re, sys

ui = sys.argv[1]
GONE = ("hzm_wx_rain_far", "hzm_wx_rain_near", "hzm_wx_drops", "hzm_wx_skydrops")
n = 0
for f in sorted(os.listdir(ui)):
    if not f.lower().endswith((".urc", ".inc")):
        continue
    p = os.path.join(ui, f)
    t = open(p, encoding="latin-1", newline="").read()
    t0 = t
    for g in GONE:
        t = re.sub(r'(?m)^scenemodel "models/menu/%s\.tik"[^\n]*\n' % g, "", t)
        t = re.sub(r'(?m)^scenewx "%s" [^\n]*\n' % g, "", t)
    if t != t0:
        open(p, "w", encoding="latin-1", newline="").write(t)
        n += 1
print("patch_rainparts73: %d files" % n)
