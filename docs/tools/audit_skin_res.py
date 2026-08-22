import os, io, glob, re, zipfile, struct, collections

MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
PAKROOTS = [r'G:\mohaa-gl2\main', r'G:\mohaa-gl2\mainta', r'G:\mohaa-gl2\maintt']

# every texture basename any pak provides, and in what format
pak_tex = collections.defaultdict(set)
for root in PAKROOTS:
    for f in sorted(glob.glob(os.path.join(root, '*.pk3'))):
        if 'co-op_hzm' in os.path.basename(f):
            continue
        try: z = zipfile.ZipFile(f)
        except Exception: continue
        for n in z.namelist():
            ln = n.lower()
            if ln.startswith('textures/') and ln.rsplit('.', 1)[-1] in ('dds', 'tga', 'jpg', 'jpeg'):
                stem = os.path.splitext(os.path.basename(ln))[0]
                pak_tex[stem].add((ln.rsplit('.', 1)[-1], os.path.basename(f)))

skin_tex = set()
for tik in glob.glob(os.path.join(MOD, 'models', 'player', '*.tik')):
    try: d = io.open(tik, encoding='utf-8', errors='replace').read()
    except Exception: continue
    for m in re.finditer(r'surface\s+\S+\s+shader\s+(\S+)', d):
        skin_tex.add(m.group(1).lower().strip())

def tga_size(p):
    try:
        with open(p, 'rb') as f: h = f.read(18)
        return struct.unpack('<H', h[12:14])[0], struct.unpack('<H', h[14:16])[0]
    except Exception: return None
def jpg_size(p):
    try:
        d = open(p, 'rb').read(); i = 2
        while i < len(d) - 9:
            if d[i] != 0xFF: i += 1; continue
            if d[i+1] in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
                return struct.unpack('>H', d[i+7:i+9])[0], struct.unpack('>H', d[i+5:i+7])[0]
            i += 2 + struct.unpack('>H', d[i+2:i+4])[0]
    except Exception: pass
    return None

real, shadowed = [], []
for p in glob.glob(os.path.join(MOD, 'textures', '*')):
    b = os.path.basename(p); stem = os.path.splitext(b)[0].lower(); ext = os.path.splitext(b)[1].lower()
    if stem not in skin_tex: continue
    sz = tga_size(p) if ext == '.tga' else jpg_size(p) if ext in ('.jpg', '.jpeg') else None
    if not sz or max(sz) > 256: continue
    dds = [pk for (e, pk) in pak_tex.get(stem, ()) if e == 'dds']
    (shadowed if dds else real).append((max(sz), sz, b, dds[0] if dds else ''))

real.sort(); shadowed.sort()
print('  ALREADY SHADOWED by an HD .dds (upscaling ours would do NOTHING): %d' % len(shadowed))
for mx, sz, b, pk in shadowed[:10]:
    print('    %4dx%-4d %-34s <- %s' % (sz[0], sz[1], b, pk))
if len(shadowed) > 10: print('    ... and %d more' % (len(shadowed) - 10))
print()
print('  === GENUINELY LOW-RES AND VISIBLE - the real upscale list: %d ===' % len(real))
for mx, sz, b, _ in real:
    print('    %4dx%-4d  %s' % (sz[0], sz[1], b))
