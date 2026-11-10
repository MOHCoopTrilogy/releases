"""Add the Bren's own reload-hands rows to the adopted fps_anims_mg.txt (wpnfix) - after the VB's vickers_reload_m row.
coopr_bren_reload / cv_bren_reload_s / cv_bren_reload_m: cg_viewmodelanim.c CoopPerWeaponReloadAnim (key "bren" from the weapon
name "Bren", and the "(Finish)"-stripped base for every finish) and the stress-variant step (cv_<key>_reload_s|_m)."""
import shutil
P = r'C:\hzm-newguns\root\docs\tools\assets\wpnfix\models\player\base\fps_anims_mg.txt'
b = open(P, 'rb').read()
nl = b'\r\n' if b.count(b'\r\n') * 2 > b.count(b'\n') else b'\n'
assert b'coopr_bren' not in b
anchor = b'\tvickers_reload_m\t\tviewmodel/Vickers/coop_A_W_Vickers_reload_fps_m.skc\t\t\t\tcrossblend 0.05' + nl
assert b.count(anchor) == 1, b.count(anchor)
rows = [b'\t// HZM coop [newguns 2026-11-09] the Bren\'s OWN reload hands: the VB\'s three clips with the right hand retargeted onto the',
        b'\t// Bren\'s magazine, ~5.7 u behind the VB\'s well (docs/proposals/newguns_2026-11-09/tools/bren_hands.py). Per-weapon rows:',
        b'\t// the VB keeps vickers_reload*; the Bren and its finishes resolve to these (CoopPerWeaponReloadAnim, key "bren").',
        b'\tcoopr_bren_reload\t\tviewmodel/coop_bren/coop_bren_reload_fps.skc\t\t\t\tcrossblend 0.05',
        b'\tcv_bren_reload_s\t\tviewmodel/coop_bren/coop_bren_reload_fps_s.skc\t\t\t\tcrossblend 0.05',
        b'\tcv_bren_reload_m\t\tviewmodel/coop_bren/coop_bren_reload_fps_m.skc\t\t\t\tcrossblend 0.05']
b2 = b.replace(anchor, anchor + nl.join(rows) + nl)
assert len(b2) - len(b) == sum(len(r) + len(nl) for r in rows)
open(P, 'wb').write(b2)
print('added', len(rows), 'lines', 'CRLF' if nl == b'\r\n' else 'LF', len(b), '->', len(b2))
