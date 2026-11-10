"""anims_vickers.txt (wpnfix): the Bren's three torso reloads also remove the magazine prop and give the gun back to the main hand on
EXIT (animate.cpp DoExitCommands: runs when the animation is left for any reason). An interrupted reload (weapon switch, aim, the
pickup auto-reload cut by `use`) skipped the `last` commands, so coop_bren_clip.tik stayed on tag_weapon_right: in the aim pose
it sat ~8 u in front of the eye, a dark magazine end-on over the sights (ng11-ng14)."""
P = r'C:\hzm-newguns\root\docs\tools\assets\wpnfix\models\player\base\anims_vickers.txt'
b = open(P, 'rb').read()
nl = b'\r\n' if b.count(b'\r\n') * 2 > b.count(b'\n') else b'\n'
old = b'\t\t\tlast\tremoveattachedmodel tag_weapon_right 0 models/weapons/coop_bren_clip.tik' + nl
n = b.count(old)
assert n == 3, n
new = old + (b'\t\t\texit\tremoveattachedmodel tag_weapon_right 0 models/weapons/coop_bren_clip.tik\t// [newguns] also when the reload is cut short' + nl +
             b'\t\t\texit\tweaponcommand mainhand attachtohand mainhand' + nl)
assert b'exit\tremoveattachedmodel' not in b
open(P, 'wb').write(b.replace(old, new))
print('rows', n)
