"""The MP 28's own hands rows in the adopted fps_anims_smg.txt (wpnfix): its aim pose (left hand under the magazine housing, the
sleeve out of the left third) and its hip reloads (the gun held steady and lower instead of swinging up at the eye).
Key "mp28" (weapon name "MP28"; finishes resolve through the stripped base)."""
P = r'C:\hzm-newguns\root\docs\tools\assets\wpnfix\models\player\base\fps_anims_smg.txt'
b = open(P, 'rb').read()
nl = b'\r\n' if b.count(b'\r\n') * 2 > b.count(b'\n') else b'\n'
assert b'coopr_mp28' not in b
anchor = b'\tsten_reload_empty_m\t\tviewmodel/sten/coop_sten_reload_empty_hip_m.skc\t\tcrossblend 0.1\t// HZM coop [ads-smg] staged' + nl
assert b.count(anchor) == 1, b.count(anchor)
rows = [b'\t// HZM coop [newguns 2026-11-09] the MP 28\'s own hands (docs/proposals/newguns_2026-11-09/tools/mp28_ads.py, mp28_reload.py):',
        b'\t// the aim pose with the left hand under the magazine housing (the Sten\'s sleeve covered the left third of the view) and',
        b'\t// the hip reloads with the gun held steady and lower (the Sten\'s swing brought it up at the eye). Aimed reloads stay the Sten\'s.',
        b'\tcoopr_mp28_charge\t\tviewmodel/coop_bergmann/coop_mp28_ads_mag.skc\t\tcrossblend 0.25',
        b'\tcoopr_mp28_reload\t\tviewmodel/coop_bergmann/coop_mp28_reload_hip.skc\t\tcrossblend 0.1',
        b'\tcoopr_mp28_reload_empty\t\tviewmodel/coop_bergmann/coop_mp28_reload_empty_hip.skc\t\tcrossblend 0.1',
        b'\tcv_mp28_reload_s\t\tviewmodel/coop_bergmann/coop_mp28_reload_hip_s.skc\t\tcrossblend 0.1',
        b'\tcv_mp28_reload_m\t\tviewmodel/coop_bergmann/coop_mp28_reload_hip_m.skc\t\tcrossblend 0.1',
        b'\tcv_mp28_reload_empty_s\t\tviewmodel/coop_bergmann/coop_mp28_reload_empty_hip_s.skc\t\tcrossblend 0.1',
        b'\tcv_mp28_reload_empty_m\t\tviewmodel/coop_bergmann/coop_mp28_reload_empty_hip_m.skc\t\tcrossblend 0.1']
b2 = b.replace(anchor, anchor + nl.join(rows) + nl)
open(P, 'wb').write(b2)
print('added', len(rows), len(b), '->', len(b2))
