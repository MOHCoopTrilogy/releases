"""make_overlay.py - test overlay pk3 = the ironsights polling weather.scr + the listed mod files (working tree).
    python make_overlay.py <out.pk3> <mod-relative path> ...
"""
import sys, zipfile, os
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
out = sys.argv[1]
src = zipfile.ZipFile(r'G:\mohaa-adsanim\home\maintt\zzzzzzzzzzzz_ironsighttest.pk3')
z = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
z.writestr('coop_mod/weather.scr', src.read('coop_mod/weather.scr'))
for f in sys.argv[2:]:
    arc = 'coop_mod/player_Torso.st' if f.lower() == 'coop_mod/player_torso.st' else f
    z.write(os.path.join(MOD, f), arc)
z.close()
print('wrote', out, len(sys.argv) - 2, 'files')
