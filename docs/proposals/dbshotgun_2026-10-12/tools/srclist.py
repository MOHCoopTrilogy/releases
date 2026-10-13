"""Which paks carry a texture stem (engine order, first = lowest priority = retail). Read-only.
    python tools/srclist.py textures/models/weapons/kar98/kar98 [more stems]      add --save to write the RETAIL copy
    (first entry from a pak named pak*.pk3 in main / mainta / maintt) to build/src/<name>_retail.png
"""
import os, sys, io, importlib.util
from PIL import Image
import dbslib as L

sp = importlib.util.spec_from_file_location('weapon_hd_vfs', os.path.join(L.DOCS, 'tools', 'weapon_hd', 'vfs.py'))
HV = importlib.util.module_from_spec(sp); sp.loader.exec_module(HV)


def main():
    save = '--save' in sys.argv
    idx = HV.index()
    best = {}          # keep the LARGEST retail copy
    for st in [a for a in sys.argv[1:] if not a.startswith('--')]:
        for ext in ('.dds', '.jpg', '.tga', '.png'):
            for pak, real in idx.get(st.lower() + ext, []):
                data = HV._zips[pak].read(real)
                try:
                    im = Image.open(io.BytesIO(data)); size = im.size
                except Exception as e:
                    im = None; size = str(e)[:40]
                base = os.path.basename(pak)
                retail = base.lower().startswith('pak') and base.lower().endswith('.pk3')
                print('%-46s %-34s %-9s %s %s' % (st + ext, base, len(data), size, 'RETAIL' if retail else ''))
                if save and retail and im is not None and im.size[0] > best.get(st, 0):
                    best[st] = im.size[0]
                    os.makedirs(os.path.join(L.BUILD, 'src'), exist_ok=True)
                    out = os.path.join(L.BUILD, 'src', os.path.basename(st) + '_retail.png')
                    im.convert('RGB').save(out)
                    print('   saved', out)


if __name__ == '__main__':
    main()
