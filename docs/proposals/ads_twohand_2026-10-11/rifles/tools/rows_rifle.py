"""Staged models/player/base/fps_anims_rifle.txt = the RELEASED fixes-pak copy + the rifle lane's rows (apply-on-top:
re-run after the fixes copy changes). Each new row goes right after an existing row of the same prefix.

    python rows_rifle.py            writes ../assets/models/player/base/fps_anims_rifle.txt and prints the hunks
"""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
FX = r"C:\mohaa-coop-dev\docs\tools\assets\fixes\models\player\base\fps_anims_rifle.txt"
OUT = os.path.join(HERE, '..', 'assets', 'models', 'player', 'base', 'fps_anims_rifle.txt')
NOTE = '// HZM coop [ads rifles 2026-10-12] '
# (new row, clip, crossblend, after this existing row, note)
ROWS = [
    ('kar98_reload_ads', 'viewmodel/rifle/kar98_reload_ads.skc', '0.1', 'kar98_reload',
     'aimed reload: bolt worked on the sights, charger thumbed in with the rifle lowered under the centre, back to the aim'),
    ('coopr_g_43_irons_charge', 'viewmodel/g43/coop_g43_irons_aim.skc', '0.2', 'g43_charge',
     'iron-sight G43 (weapon name G 43 Irons): its own aim pose = the Garand pose with the support hand 1.1 u left / 1.6 u lower (no fingers right of the receiver); per-weapon row, the scoped G43 keeps g43_charge'),
    # NOT staged: kar98mortar_rechamber_ads / kar98mortar_reload_ads. The rifle-grenade Kar98 (kar98_mortar.tik,
    # 'Gewehrgranate', prefix kar98mortar) has NO aim at all - no ironsight row (`ADSSIGHT norow wpn='Gewehrgranate'`)
    # and no `kar98mortar_charge` row (run rb12: "Couldn't find view model animation kar98mortar_charge", the gun
    # never comes up). Aimed rows without an aim pose would play the Kar98's aimed clips from the hip.
]
# rows that already exist and whose CLIP FILE is replaced by a staged one (no text change): listed for the report
REPLACED = ['kar98_rechamber_ads -> viewmodel/rifle/kar98_rechamber_ads.skc (rebuilt: gun motion from gunphys)']


def main():
    txt = open(FX, 'rb').read().decode('latin-1')
    nl = '\r\n' if '\r\n' in txt else '\n'
    for row, clip, xb, after, note in ROWS:
        assert not re.search(r'(?m)^\s*%s\s' % re.escape(row), txt), row + ' exists already'
        m = re.search(r'(?m)^(\s*)%s\s+\S+[^\r\n]*(\r?\n)' % re.escape(after), txt)
        assert m, after
        line = '%s%s\t%s\t\tcrossblend %s\t%s%s' % (m.group(1), row, clip, xb, NOTE + note, nl)
        txt = txt[:m.end()] + line + txt[m.end():]
        print('+ after `%s`: %s' % (after, line.strip()))
    d = 0
    for ln in txt.splitlines():
        c = ln.split('//')[0]; d += c.count('{') - c.count('}')
    assert d == 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(txt.encode('latin-1'))
    for r in REPLACED:
        print('= clip replaced:', r)
    print('wrote', os.path.normpath(OUT))


if __name__ == '__main__':
    main()
