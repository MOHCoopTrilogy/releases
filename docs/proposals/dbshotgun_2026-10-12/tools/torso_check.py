"""patch_torso_dbs.py against the three state files that exist today: the DEPLOYED one (game pak in the GOG folder,
read only), the mod TREE's, and an already-patched text (idempotence). Writes nothing.

    python tools/torso_check.py [--rows]
"""
import sys, os, re, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'wiring'))
import patch_torso_dbs as P

PAK = r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\zzzzzz_co-op_hzm_mod_code.pk3"
TREE = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\coop_mod\player_Torso.st"


def main():
    d = zipfile.ZipFile(PAK).read('coop_mod/player_Torso.st').decode('latin-1')
    t = open(TREE, 'rb').read().decode('latin-1')
    for nm, src in (('deployed pak', d), ('mod tree', t)):
        o = P.patch(src)
        rows = re.findall(r'(?m)^\t\tcoop_dbs_\S+', o)
        print('%-12s %6d -> %6d bytes; clip rows %d, aimed-refire row %d, break-off routing rows %d, idempotent %s, other lines changed %d' % (
            nm, len(src), len(o), len(rows), o.count('COOP_DBS_REFIRE_AIM\t\t: +ATTACK'), o.count('an open double barrel is shut'),
            P.patch(o) == o, len(set(src.replace('\r\n', '\n').split('\n')) - set(o.replace('\r\n', '\n').split('\n')))))
        if '--rows' in sys.argv and nm == 'mod tree':
            st = None
            for l in o.replace('\r\n', '\n').split('\n'):
                if l.startswith('state '):
                    st = l
                if 'Shotgun (Double Barrel)' in l:
                    print('   ', st, '|', l.strip()[:150])


if __name__ == '__main__':
    main()
