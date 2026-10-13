"""SMG lane: copy the shared harness tools from ..\\..\\tools into this folder, repointed at the lane's own test game
(G:\\mohaa-adsanim3, harness owner "adsanim3", net_port 12578, run log SCRATCH\\adssmg\\run.log). Re-run to pick up a
shared tool's update; the lane's own edits live in run_smg.py's SMG block, which is appended, not patched in.

    python takeover.py
"""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
SH = os.path.normpath(os.path.join(HERE, '..', '..', 'tools'))
BS = chr(92)

PLAIN = ['centrebox.py', 'dgif.py', 'gifsheet.py', 'animmarks.py', 'democheck.py', 'sheet.py', 'loopreact.py']
for fn in PLAIN:
    s = open(os.path.join(SH, fn), encoding='latin-1').read()
    n = s.count('G:/mohaa-adsanim/runs')
    assert n >= 1 or fn == 'gifsheet.py', fn
    s = s.replace('G:/mohaa-adsanim/runs', 'G:/mohaa-adsanim3/runs')
    open(os.path.join(HERE, fn), 'w', encoding='latin-1', newline='\n').write(s)
    print('took', fn, 'repointed', n)

# the runner: run_2h.py -> run_smg.py
s = open(os.path.join(SH, 'run_2h.py'), encoding='latin-1').read()
anchor = "S, R = A.S, A.R\n"
assert s.count(anchor) == 1
rep = anchor + '\n'.join([
    "# ---- SMG lane repoint (takeover.py): the lane's own test game, never G:" + BS + BS + "mohaa-adsanim ----",
    "R.OWNER = 'adsanim3'",
    "R.CLIENT = 'G:' + chr(92) + 'mohaa-adsanim3'",
    "R.EXE = os.path.join(R.CLIENT, 'openmohaa_ironsight.exe')",
    "R.HOME = os.path.join(R.CLIENT, 'home')",
    "R.MAINTT = os.path.join(R.HOME, 'maintt')",
    "R.LOG = os.path.join(R.MAINTT, 'qconsole.log')",
    "R.SHOTS = os.path.join(R.MAINTT, 'screenshots')",
    "R.PRISTINE = os.path.join(R.CLIENT, 'pristine')",
    "R.RUNS = 'G:/mohaa-adsanim3/runs'",
    "R.PORT = 12578",
    "A.LOGF = os.path.join(A.SCR, 'adssmg', 'run.log')",
    "A.GUNS.update(mp40s='models/weapons/mp40silenced.tik', pps43='models/weapons/ppsh43silenced.tik',",
    "              greasegun='models/weapons/greasegun.tik', greaseguns='models/weapons/greasegun_silenced.tik',",
    "              m38='models/weapons/moschetto.tik', mp18='models/weapons/mp40_mp18.tik', mp40r='models/weapons/mp40_mp40r2.tik',",
    "              thompson50='models/weapons/thompson50.tik', thompsongold='models/weapons/thompsonsmg_gold.tik',",
    "              thompsonm1a1='models/weapons/thompsonsmg_m1a1dk.tik', thompson1928d='models/weapons/thompsonsmg_tommy1928d.tik',",
    "              thompson28='models/weapons/thompsonsmg_tommy28.tik')",
    "",
]) + '\n'
s = s.replace(anchor, rep)
# the unused lock / foreign-process helpers of the pistol lane are dropped (they name the other install)
a = s.index('def other_test_games():')
b = s.index('def main():')
s = s[:a] + s[b:]
assert 'mohaa-adsanim"' not in s and "heavy_lock" not in s
# a view yaw for the whole session (light backdrop) and braced reloads
s = s.replace('ap.add_argument("--set", action="append", default=[])',
              'ap.add_argument("--set", action="append", default=[]); ap.add_argument("--yaw", type=int, default=None)')
s = s.replace('    a = ap.parse_args()\n', '    a = ap.parse_args()\n    if a.yaw is not None:\n        R.SPOT = R.SPOT[:3] + (a.yaw,)\n', 1)
s = s.replace('"""Two-handed pistol aim: harness runs on G:' + BS + BS + 'mohaa-adsanim (slot word "adsbolt", run_adsbolt\'s own boot / steps).',
              '"""SMG lane runner = ..' + BS + BS + 'tools' + BS + BS + 'run_2h.py taken over by takeover.py (GENERATED - edit takeover.py): harness runs on\nG:' + BS + BS + 'mohaa-adsanim3 (owner adsanim3, net_port 12578), run_adsbolt\'s own boot / steps.')
# settled-aim stills also take the same view WITHOUT the first-person model (the reference for the centre-box measure)
old = '    L += A.frames(tag, 4, i) + ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + S.RELEASE + A.UNAPPLY[st]\n'
assert s.count(old) == 1
s = s.replace(old, '    L += A.frames(tag, 4, i) + ["set cg_drawviewmodel 0", "wait 1", "wait 1", "wait 1", "screenshotJPEG %s__ref" % tag, "wait 1", "wait 1",\n'
              '                                "set cg_drawviewmodel 2", "wait 1", "wait 1", "wait 1", "wait 1"]\n'
              '    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + S.RELEASE + A.UNAPPLY[st]\n')
# --stances a,b,c limits the settled-aim stills
s = s.replace('ap.add_argument("--yaw", type=int, default=None)', 'ap.add_argument("--yaw", type=int, default=None); ap.add_argument("--stances", default=None)')
s = s.replace("        R.SPOT = R.SPOT[:3] + (a.yaw,)\n", "        R.SPOT = R.SPOT[:3] + (a.yaw,)\n    if a.stances:\n        globals()['STANCES'] = tuple(x for x in a.stances.split(',') if x)\n", 1)
assert "globals()['STANCES']" in s
# a --guns key that is not in the table = models/weapons/<key>.tik (finish tiks: sten_gold ...)
old = '    a.guns = [g for g in a.guns.split(",") if g]; a.parts = a.parts.split(",")\n'
assert s.count(old) == 1
s = s.replace(old, '    a.guns = [g for g in a.guns.split(",") if g]; a.parts = a.parts.split(",")\n    for g_ in a.guns:                      # a key that is not in the table = that tik (finish tiks: sten_gold ...)\n        A.GUNS.setdefault(g_, "models/weapons/%s.tik" % g_)\n')
# the SMG lane's own captures (smg_block.py), dispatched per gun from run()
blk = open(os.path.join(HERE, 'smg_block.py'), encoding='latin-1').read()
assert s.count('\ndef run(a):\n') == 1
s = s.replace('\ndef run(a):\n', '\n' + blk + 'def run(a):\n')
hook = '            if "fire" in a.parts:\n'
assert s.count(hook) == 1
s = s.replace(hook, '            smg_parts(a, gun)\n' + hook)
s = s.replace('ap.add_argument("--stances", default=None)',
              'ap.add_argument("--stances", default=None); ap.add_argument("--sstances", default="stand"); '
              'ap.add_argument("--aitik", default="models/human/german_wehrmact_nco.tik"); ap.add_argument("--hold", type=int, default=175); ap.add_argument("--tail", default="0"); '
              'ap.add_argument("--rel", type=int, default=200); ap.add_argument("--cheats", action="store_true")')
s = s.replace("    if a.stances:\n", "    a.sstances = [x for x in a.sstances.split(',') if x]\n    SMG_HOLD[0] = a.hold; SMG_REL[0] = a.rel\n"
              "    SMG_TAIL[:] = [int(a.tail.split(':')[0]), int((a.tail.split(':') + ['4'])[1])]\n"
              "    if a.cheats:\n        cheats_on()\n    if a.stances:\n", 1)
assert 'SMG_HOLD[0] = a.hold' in s
# another map / spot for the whole session (an AI to look at needs a place without the map's friendly actors:
# mapents.py; m6l1a at its player start has none: --map m6l1a --spot 6152,-6528,5440,135)
s = s.replace('ap.add_argument("--cheats", action="store_true")',
              'ap.add_argument("--cheats", action="store_true"); ap.add_argument("--map", default=None); ap.add_argument("--spot", default=None)')
s = s.replace("    if a.cheats:\n", "    if a.map:\n        R.MAP = a.map\n    if a.spot:\n        R.SPOT = tuple(float(x) for x in a.spot.split(','))\n    if a.cheats:\n", 1)
assert 'R.MAP = a.map' in s
open(os.path.join(HERE, 'run_smg.py'), 'w', encoding='latin-1', newline='\n').write(s)
print('wrote run_smg.py')
