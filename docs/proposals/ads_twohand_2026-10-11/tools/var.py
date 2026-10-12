"""variants of a recipe json: python var.py base.json outprefix name:key=json;key=json name2:... -> eye crops sheet"""
import sys, json, subprocess, os
from PIL import Image, ImageDraw
base = json.load(open(sys.argv[1])); pre = sys.argv[2]
ims = []
for spec in sys.argv[3:]:
    name, _, kv = spec.partition(':')
    r = dict(base)
    for item in [x for x in kv.split(';') if x]:
        k, v = item.split('=', 1)
        r[k] = json.loads(v)
    json.dump(r, open('%s_%s.json' % (pre, name), 'w'))
    env = dict(os.environ, V2H='eye')
    o = subprocess.run([sys.executable, 'mk2h.py', 'colt45', '%s_%s.skc' % (pre, name), '--view', '%s_%s.jpg' % (pre, name),
                        '--json', '%s_%s.json' % (pre, name), '--w', '1280'], capture_output=True, text=True, env=env)
    line = [l for l in o.stdout.splitlines() if 'wrist bend' in l]
    print(name, line[0] if line else o.stdout[-300:] + o.stderr[-600:])
    im = Image.open("%s_%s.jpg" % (pre, name)).crop((160, 300, 1120, 720)).resize((640, 280))
    ImageDraw.Draw(im).text((6, 6), name + '  ' + kv[:90], fill=(0, 0, 0))
    ims.append(im)
cols = 2 if len(ims) > 1 else 1
S = Image.new("RGB", (640 * cols, 280 * ((len(ims) + cols - 1) // cols)))
for i, im in enumerate(ims):
    S.paste(im, ((i % cols) * 640, (i // cols) * 280))
S.save(pre + '_sheet.jpg', quality=90)
