"""QA 3: (1) build_bren.py - no ghost ring any more: the eye now looks through the source's own aperture leaf (the ring showed as a
thin bright arc across the aim view); (2) fps_anims_mg.txt - aimed reload rows for the Bren (the same retargeted clips), so a reload
started while aiming is an AIMED reload (the ADS framing holds) instead of the hip clip played under the aim rig, which swung the
gun sideways across the view at its start (ng21 / ng23 adsreload_1)."""
P1 = r'C:\hzm-newguns\root\docs\proposals\newguns_2026-11-09\tools\build_bren.py'
s = open(P1, 'rb').read()
nl = b'\r\n' if b'\r\n' in s else b'\n'
old = b'    A = np.concatenate([A[keep], ring]); part = np.concatenate([part[keep], np.full(len(ring), 49)])'
assert s.count(old) == 1
new = (b'    # [newguns QA 3] no ghost ring: the sight row looks through the source aperture leaf (part 34), the disc (49) stays out' + nl +
       b'    A = A[keep]; part = part[keep]' + nl + b'    _unused_ring = ring')
s = s.replace(old, new)
open(P1, 'wb').write(s)

P2 = r'C:\hzm-newguns\root\docs\tools\assets\wpnfix\models\player\base\fps_anims_mg.txt'
b = open(P2, 'rb').read()
nl = b'\r\n' if b.count(b'\r\n') * 2 > b.count(b'\n') else b'\n'
anchor = b'\tcv_bren_reload_m\t\tviewmodel/coop_bren/coop_bren_reload_fps_m.skc\t\t\t\tcrossblend 0.05' + nl
assert b.count(anchor) == 1 and b'coopr_bren_reload_ads' not in b
rows = [b'\t// aimed: the same clips as AIMED reload rows (the ADS framing holds; the hip row under the aim rig swung the gun across the view)',
        b'\tcoopr_bren_reload_ads\t\tviewmodel/coop_bren/coop_bren_reload_fps.skc\t\t\t\tcrossblend 0.1',
        b'\tcv_bren_reload_s_ads\t\tviewmodel/coop_bren/coop_bren_reload_fps_s.skc\t\t\t\tcrossblend 0.1',
        b'\tcv_bren_reload_m_ads\t\tviewmodel/coop_bren/coop_bren_reload_fps_m.skc\t\t\t\tcrossblend 0.1']
open(P2, 'wb').write(b.replace(anchor, anchor + nl.join(rows) + nl))
print('ok')
