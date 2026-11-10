"""patch_fog73.py <mod ui dir> <fog73_lines.txt> - rain73: the fog banks (gen_fog73.py) in every scene that shows the town (it carries
hzm_wx_town): the model lines after the town's, the scenewx 'fog' roles after the town's role. Idempotent."""
import os, re, sys

ui, lf = sys.argv[1:3]
L = [l.strip() for l in open(lf) if l.strip()]
models = [l for l in L if l.startswith("scenemodel")]
roles = [l for l in L if l.startswith("scenewx")]
n = 0
for f in sorted(os.listdir(ui)):
    if not f.lower().endswith((".urc", ".inc")):
        continue
    p = os.path.join(ui, f)
    t = open(p, encoding="latin-1", newline="").read()
    if 'scenemodel "models/menu/hzm_wx_town.tik"' not in t or "hzm_wx_fog0" in t:
        continue
    nl = "\r\n" if "\r\n" in t else "\n"
    t = re.sub(r'(scenemodel "models/menu/hzm_wx_town\.tik" 0 0 0 0\r?\n)', lambda m: m.group(1) + nl.join(models) + nl, t, count=1)
    t = re.sub(r'(scenewx "hzm_wx_town" tint\r?\n)', lambda m: m.group(1) + nl.join(roles) + nl, t, count=1)
    assert t.count("hzm_wx_fog0") == 2, f
    open(p, "w", encoding="latin-1", newline="").write(t)
    n += 1
print("patch_fog73: %d files" % n)
