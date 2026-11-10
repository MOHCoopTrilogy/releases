"""Shared staging for a new gun built on a donor's skeleton (stage_bren.py did the first one by hand): into THIS worktree's wpnfix
sources + manifest pins.
  - the donor's winning tik, re-pointed: setup (own path / skd / shader per surface), name, rank, itemhandler exec, the donor's
    magazine surface renamed in every frame command, a QUAKED name
  - every weapon clip the tik names, copied (v14 -> v13) into the new path under its OWN file name, with tag_barrel moved onto the
    new muzzle (x) and optional tag_eject pos override
  - the baked sheet, a shader block in scripts/coop_newguns.shader, the credit in credits/coop_cc_models.txt
"""
import os, sys, json, re, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools")
import pk
import skc14to13 as C

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SRC = os.path.join(ROOT, 'docs', 'tools', 'assets', 'wpnfix')
MAN = os.path.join(SRC, 'wpnfix_manifest.json')
HEAD = "// HZM coop [newguns 2026-11-09] shaders of the new CC-model guns (docs/proposals/newguns_2026-11-09)\n"


def put(rel, data, man):
    p = os.path.join(SRC, *rel.split('/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data)
    man.setdefault(rel, {'new': True})
    print('  %-60s %8d bytes' % (rel, len(data)))


def clip(rel, local_scale, muzzle=None, eject_local=None):
    """muzzle = (local axis along the bore, value): that component of tag_barrel's position is set in every frame"""
    b = pk.read(rel)
    if struct.unpack_from('<i', b, 4)[0] == 14:
        b = C.convert(b)
    b = bytearray(b)
    ch, fr = pk.skc(bytes(b))
    nf = struct.unpack_from('<i', b, 44)[0]
    ib = ch.index('tag_barrel pos') if 'tag_barrel pos' in ch else None
    ie = ch.index('tag_eject pos') if 'tag_eject pos' in ch else None
    for f in range(nf):
        ov = struct.unpack_from('<i', b, 48 + 48 * f + 44)[0]
        if ib is not None and muzzle is not None:
            v = list(struct.unpack_from('<4f', b, ov + 16 * ib))
            v[muzzle[0]] = float(muzzle[1])
            struct.pack_into('<4f', b, ov + 16 * ib, v[0], v[1], v[2], 0.0)
        if ie is not None and eject_local is not None:
            struct.pack_into('<4f', b, ov + 16 * ie, float(eject_local[0]), float(eject_local[1]), float(eject_local[2]), 0.0)
    return bytes(b)


def stage(cfg):
    """cfg: donor_tik, donor_path, stem, name, rank, ih (class, name), setup_surfaces [(pattern, shader)], mag_from, mag_to,
    skd_file, sheet_file, sheet_rel, shader, shader_note, credit_key, credit, muzzle_local_x, eject_local, extra_subs [(a, b)]"""
    man = json.load(open(MAN))
    t = pk.read(cfg['donor_tik']).decode('latin-1')
    path = 'models/weapons/' + cfg['stem']
    setup = ("setup\n{\n\tscale 0.52\n" + ''.join('\t// %s\n' % l for l in cfg['setup_note']) +
             "\tpath %s\n\tskelmodel %s.skd\n" % (path, cfg['stem']) +
             ''.join('\tsurface %s shader %s\n' % s for s in cfg['setup_surfaces']) + "}\n")
    t = re.sub(r"setup\s*\{.*?\}\s*\n", setup, t, count=1, flags=re.S)
    n0 = re.search(r'\n\s*name\s+"([^"]+)"', t).group(1)
    t = re.sub(r'(\n\s*name\s+)"[^"]+"', r'\1"%s"' % cfg['name'], t, count=1)
    t = re.sub(r"(\n\s*rank\s+)\d+ \d+", r"\g<1>%d %d" % (cfg['rank'], cfg['rank']), t, count=1)
    t = re.sub(r'exec coop_mod/itemhandler.scr "initialiseItem" "[^"]+" "[^"]+"',
               'exec coop_mod/itemhandler.scr "initialiseItem" "%s" "%s"' % cfg['ih'], t)
    t = re.sub(r"(surface\s+)%s(\s+[+-]nodraw)" % re.escape(cfg['mag_from']), r"\g<1>%s\2" % cfg['mag_to'], t, flags=re.I)
    t = re.sub(r"/\*QUAKED.*?\*/", "/*QUAKED weapon_%s (0.0 0.0 0.0) (-65 -40 0) (65 40 120) %s\n*/" % (cfg['stem'], cfg['name']), t, flags=re.S)
    for a, b in cfg.get('extra_subs', []):
        t = t.replace(a, b)
    bad = [l for l in t.splitlines() if n0 in l and not l.strip().startswith('//')]
    assert not bad, bad
    clips = sorted(set(re.findall(r'\n\s*\w+\s+([\w.]+\.skc)', t.split('animations', 1)[1])))
    put('%s/%s.skd' % (path, cfg['stem']), open(cfg['skd_file'], 'rb').read(), man)
    put(cfg['sheet_rel'], open(cfg['sheet_file'], 'rb').read(), man)
    for c in clips:
        put('%s/%s' % (path, c), clip('%s/%s' % (cfg['donor_path'], c), 0.52, cfg.get('muzzle'), cfg.get('eject_local')), man)
    put('models/weapons/%s.tik' % cfg['stem'], t.encode('latin-1'), man)
    sh = os.path.join(SRC, 'scripts', 'coop_newguns.shader')
    s = open(sh, 'rb').read().decode('latin-1') if os.path.isfile(sh) else HEAD
    if '\n%s\n' % cfg['shader'] not in s:
        s = s.rstrip() + '\n\n// %s\n%s\n{\n\tqer_editorimage %s\n\t{\n\t\tmap %s\n\t\trgbGen lightingSpherical\n\t}\n}\n' % (
            cfg['shader_note'], cfg['shader'], cfg['sheet_rel'], cfg['sheet_rel'])
    put('scripts/coop_newguns.shader', s.encode('latin-1'), man)
    cr = os.path.join(SRC, 'credits', 'coop_cc_models.txt')
    c = open(cr, 'rb').read().decode('utf-8')
    if cfg['credit_key'] not in c:
        nl = '\r\n' if '\r\n' in c else '\n'
        open(cr, 'wb').write((c.rstrip() + nl + cfg['credit'].replace('\n', nl)).encode('utf-8'))
    open(MAN, 'w', encoding='utf-8', newline='\n').write(json.dumps(man, indent=2, sort_keys=True) + '\n')
    return clips
