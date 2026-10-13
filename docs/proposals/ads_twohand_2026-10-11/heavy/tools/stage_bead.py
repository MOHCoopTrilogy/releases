r"""Stage the shotgun's brass front bead (user 2026-10-12: "that shotgun needs some kind of sights"; the bead itself was
approved on 2026-10-05 and never left its proposal folders):

  * the mesh: ads_bolt_2026-10-04/tools/add_bead.py (own surface `coop_bead`, every other surface byte-identical) on
    the retail M1897 skd -> assets/<the tik's path>/<skd>
  * shader + texture: weapon_hd_2026-10-05/bead/ -> assets/scripts, assets/textures
  * every weapon tik of the mod tree that loads that skd from that path gets `surface coop_bead shader
    coop_shotgun_bead` after its last surface line -> assets/models/weapons/<tik>  (the mod tree is never written)

    cd heavy/assets; python ../tools/stage_bead.py [--r 0.175] [--lift 0.55]

NOTE: patch_tik_h.py rebuilds a staged tik from the mod tree - a later reload set for the shotgun must keep this line.
"""
import sys, os, re, glob, shutil, subprocess, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
BOLT = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
HD = r'C:\mohaa-coop-dev\docs\proposals\weapon_hd_2026-10-05\bead'
SJ = json.load(open(r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\sights.json'))['shotgun']
LINE = 'surface coop_bead shader coop_shotgun_bead'


def main():
    extra = sys.argv[1:]
    skd_rel = SJ['skd']                                    # models/weapons/shotgun/shotgun.skd
    mesh_path, skd_name = os.path.dirname(skd_rel).lower(), os.path.basename(skd_rel).lower()
    dst = hv.staged(skd_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    r = subprocess.run([sys.executable, os.path.join(BOLT, 'add_bead.py'), 'shotgun', dst] + extra, cwd=BOLT, capture_output=True, text=True)
    print((r.stdout + r.stderr).strip()[-400:])
    assert r.returncode == 0
    for d, _, fs in os.walk(HD):
        for f in fs:
            src = os.path.join(d, f)
            out = hv.staged(os.path.relpath(src, HD).replace(os.sep, '/'))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copyfile(src, out)
            print('copied', os.path.relpath(src, HD))
    n, other = 0, []
    for p in sorted(glob.glob(os.path.join(MOD, 'models', 'weapons', 'shotgun*.tik'))):
        t = open(p, 'rb').read().decode('latin-1')
        mp = re.search(r'(?mi)^\s*path\s+(\S+)', t)
        ms = re.search(r'(?mi)^\s*skelmodel\s+(\S+)', t)
        if not mp or not ms or mp.group(1).lower().rstrip('/') != mesh_path or ms.group(1).lower() != skd_name:
            other.append('%s (path %s, %s)' % (os.path.basename(p), mp.group(1) if mp else '?', ms.group(1) if ms else '?'))
            continue
        assert 'coop_bead' not in t, p
        nl = '\r\n' if '\r\n' in t else '\n'
        last = [m for m in re.finditer(r'(?mi)^[ \t]*surface[^\r\n]*', t[:t.lower().index('init')])][-1]
        t = t[:last.end()] + nl + '\t' + LINE + '\t// HZM coop [heavy lane] brass front bead (stage_bead.py)' + t[last.end():]
        out = hv.staged('models/weapons/' + os.path.basename(p))
        open(out, 'wb').write(t.encode('latin-1'))
        n += 1
        print('tik ->', os.path.basename(p))
    print(n, 'tiks on', mesh_path + '/' + skd_name, '| NOT on this mesh (no bead staged):', '; '.join(other) or '-')


if __name__ == '__main__':
    main()
