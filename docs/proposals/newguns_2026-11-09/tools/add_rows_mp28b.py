"""The MP 28's aimed-reload rows: the Sten's aimed clips under the per-weapon names (cgame appends _ads to the row it picked, so
a per-weapon hip row without its _ads sibling would lose the aimed reload)."""
P = r'C:\hzm-newguns\root\docs\tools\assets\wpnfix\models\player\base\fps_anims_smg.txt'
b = open(P, 'rb').read()
nl = b'\r\n' if b.count(b'\r\n') * 2 > b.count(b'\n') else b'\n'
assert b'coopr_mp28_reload_ads' not in b
anchor = b'\tcv_mp28_reload_empty_m\t\tviewmodel/coop_bergmann/coop_mp28_reload_empty_hip_m.skc\t\tcrossblend 0.1' + nl
assert b.count(anchor) == 1
rows = [b'\t// aimed: the Sten\'s own aimed clips under the per-weapon names (cgame appends _ads to the row it picked)',
        b'\tcoopr_mp28_reload_ads\t\tviewmodel/sten/coop_sten_reload_ads.skc\t\tcrossblend 0.1',
        b'\tcoopr_mp28_reload_empty_ads\t\tviewmodel/sten/sten_reload_empty_ads.skc\t\tcrossblend 0.1',
        b'\tcv_mp28_reload_s_ads\t\tviewmodel/sten/coop_sten_reload_ads_s.skc\t\tcrossblend 0.1',
        b'\tcv_mp28_reload_m_ads\t\tviewmodel/sten/coop_sten_reload_ads_m.skc\t\tcrossblend 0.1',
        b'\tcv_mp28_reload_empty_s_ads\t\tviewmodel/sten/coop_sten_reload_empty_ads_s.skc\t\tcrossblend 0.1',
        b'\tcv_mp28_reload_empty_m_ads\t\tviewmodel/sten/coop_sten_reload_empty_ads_m.skc\t\tcrossblend 0.1']
open(P, 'wb').write(b.replace(anchor, anchor + nl.join(rows) + nl))
print('added', len(rows))
