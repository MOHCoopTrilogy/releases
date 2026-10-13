"""Finish / variant coverage of the pistol lane's mesh and texture changes (user: "all of these new guns will need their
camo/variants too").

    python variants.py <staged root> [--md out.md]

A pistol FAMILY = a staged base tik and every weapon tik (staged, mod tree, live paks) named <base>_<something>
(finishes: _bloody _blued _camo_* _chrome _gold; model variants: colt45_coltpa, mauser_c96_c96trench ...). Per tik:
  mesh      staged = the tik's skelmodel is a mesh this lane staged (split slide / toggle / bolt / filler / heads / parts);
            retail = it points at a mesh the lane did not touch
  rows      which client rows the tik has: L reload_ads_loaded, E reload_ads_empty, h reload_empty, i idle_empty, f fire_ads
  surfaces  mesh surfaces the tik gives no shader line (they draw with the mesh's own shader name)
  textures  of the image files its shaders map: how many are files this lane staged (lifted) / how many are other files
            in the same texture folders (a finish with its OWN sheet does not get a lift made on the base sheet)
NOT COVERED = the family has a staged mesh and this tik is on another one, or the family has rows and this tik has
none, or the family has lifted sheets and this tik maps a sheet of the same gun that was not lifted.
"""
import sys, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc, p12
vfs = gunskc.R.vfs
MOD = p12.MOD
ROWS = (('reload_ads_loaded', 'L'), ('reload_ads_empty', 'E'), ('reload_empty', 'h'), ('idle_empty', 'i'), ('fire_ads', 'f'))


def strip(s):
    return '\n'.join(l.split('//')[0] for l in s.replace('\r\n', '\n').split('\n'))


def shader_maps():
    """shader name -> set of mapped image files (mod tree scripts + live paks)"""
    out = {}
    texts = []
    sd = os.path.join(MOD, 'scripts')
    for fn in os.listdir(sd):
        if fn.lower().endswith('.shader'):
            texts.append(open(os.path.join(sd, fn), 'rb').read().decode('latin-1'))
    for k in vfs.glob_paths('scripts/', '.shader'):
        if not os.path.isfile(os.path.join(MOD, k.replace('/', os.sep))):
            b = vfs.read(k)
            if b:
                texts.append(b.decode('latin-1'))
    for tx in texts:
        s = strip(tx)
        for m in re.finditer(r'(?m)^([^\s{}]+)\s*\n\{', s):
            i = m.end(); d = 1
            while i < len(s) and d:
                d += (s[i] == '{') - (s[i] == '}'); i += 1
            body = s[m.end():i]
            out.setdefault(m.group(1).lower(), set()).update(os.path.splitext(x.lower())[0] for x in re.findall(r'(?im)^\s*(?:map|clampmap)\s+(\S+\.\w+)', body))
    return out


def main():
    root = os.path.abspath(sys.argv[1])
    wd = os.path.join(root, 'models', 'weapons')
    staged_tiks = {fn[:-4].lower(): fn for fn in os.listdir(wd) if fn.lower().endswith('.tik')}
    staged_files = set()
    for dp, dn, fns in os.walk(root):
        for fn in fns:
            staged_files.add(os.path.relpath(os.path.join(dp, fn), root).replace(os.sep, '/').lower())
    staged_skd = {f for f in staged_files if f.endswith('.skd')}
    staged_tex = {os.path.splitext(f)[0] for f in staged_files if f.startswith('textures/models/')}   # lifts replace a retail sheet; textures/coop_* are NEW parts' own sheets       # by name, any image extension
    stems = p12.tik_stems()
    smap = shader_maps()

    def text(stem):
        if stem in staged_tiks:
            return open(os.path.join(wd, staged_tiks[stem]), 'rb').read().decode('latin-1'), True
        b = p12.rd('models/weapons/%s.tik' % (stems.get(stem) or stem))
        return (b.decode('latin-1') if b else None), False

    info = {}
    for stem in sorted(set(stems) | set(staged_tiks)):
        tx, st = text(stem)
        if tx is None:
            continue
        s = strip(tx)
        pm = re.search(r'(?im)^\s*path\s+(\S+)', s); km = re.search(r'(?im)^\s*skelmodel\s+(\S+)', s)
        if not pm or not km:
            continue
        surf = {a.lower(): b.lower() for a, b in re.findall(r'(?im)^\s*surface\s+(\S+)\s+shader\s+(\S+)', s)}
        rows = ''.join(c for nm, c in ROWS if re.search(r'(?im)^\s*%s\s+\S+\.skc' % nm, s))
        info[stem] = dict(staged=st, path=pm.group(1).strip('/').lower(), skd=(pm.group(1).strip('/') + '/' + km.group(1)).lower(), surf=surf, rows=rows)
    # families: the staged base tiks (no finish suffix) and everything named <base>_* or sharing its model folder
    fin = re.compile(r'_(bloody|blued|camo_desert|camo_winter|camo_woodland|chrome|gold)$')
    bases = sorted(s for s in staged_tiks if not fin.search(s) and s in info and not any(s.startswith(b + '_') for b in staged_tiks if b != s and not fin.search(b)))
    lines = []
    tot = [0, 0]
    for b in bases:
        fam = sorted(s for s in info if s == b or s.startswith(b + '_'))
        fam_mesh = any(info[s]['skd'] in staged_skd for s in fam)
        fam_rows = any(info[s]['rows'] for s in fam)
        texdirs = set()
        for s in fam:
            for sh in info[s]['surf'].values():
                for f in smap.get(sh, ()):
                    if f in staged_tex:
                        texdirs.add(os.path.dirname(f))
        fam_unstaged = any(not info[s]['staged'] for s in fam)
        if not (fam_mesh or texdirs or fam_unstaged):
            continue
        lines.append('\n### %s (%d tiks; staged mesh: %s; lifted sheets in: %s)\n' % (b, len(fam), 'yes' if fam_mesh else 'no', ', '.join(sorted(texdirs)) or '-'))
        lines.append('| tik | staged tik | mesh | rows | textures lifted / not | covered |')
        lines.append('|---|---|---|---|---|---|')
        for s in fam:
            i = info[s]
            mesh = 'staged' if i['skd'] in staged_skd else 'retail'
            lifted, other = set(), set()
            for sh in i['surf'].values():
                for f in smap.get(sh, ()):
                    if f in staged_tex:
                        lifted.add(f)
                    elif os.path.dirname(f) in texdirs or (texdirs and '/coop_skins/' in f and b.split('_')[0] in f):
                        other.add(f)
            why = []
            if fam_mesh and mesh != 'staged':
                why.append('other mesh (%s)' % os.path.basename(i['skd']))
            if not i['staged']:
                why.append('tik NOT STAGED (its base is: rows / clips / surfaces of the base are missing on it)')
            if fam_rows and not i['rows']:
                why.append('no client rows')
            if texdirs and other:
                why.append('own sheet(s) not lifted: ' + ', '.join(sorted(os.path.basename(f) for f in other))[:90])
            tot[0 if not why else 1] += 1
            lines.append('| %s | %s | %s | %s | %d / %d | %s |' % (s, 'yes' if i['staged'] else 'NO', mesh, i['rows'] or '-', len(lifted), len(other),
                                                           'yes' if not why else 'NO: ' + '; '.join(why)))
    lines.append('\n%d tiks covered, %d not covered' % tuple(tot))
    txt = '\n'.join(lines)
    print(txt)
    if '--md' in sys.argv:
        open(sys.argv[sys.argv.index('--md') + 1], 'w', newline='\n').write(txt + '\n')


if __name__ == '__main__':
    main()
