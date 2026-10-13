"""one-off edit of tools/dbs_hands.py (fourth pass): the AIMED work pose can be raised (env DBS_ADS_CHAM "fwd,left,up",
DBS_ADS_PITCH) without moving the belt point in the gun frame (the shells' one gun-space path serves hip and aim: it is
taken from the pose of the third pass, WORK_BELT_REF); the hip loading hand can be turned (env DBS_WRIST_HIP)."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dbs_hands.py')
s = open(p, encoding='utf-8').read()
assert 'WORK_BELT_REF' not in s

a = "        'ads': dict(cham=(9.6, -0.2, -3.0), yaw=0.0, pitch=18.0, roll=-4.0)}\n"
assert s.count(a) == 1
s = s.replace(a, a + '''# the aimed work pose of the third pass: the belt point (where the hand fetches a shell) is fixed in the GUN frame from
# this pose, so raising the aimed work pose does not move the shells' path or the hip clips
WORK_BELT_REF = dict(cham=(9.6, -0.2, -3.0), yaw=0.0, pitch=18.0, roll=-4.0)
if os.environ.get('DBS_ADS_CHAM'):
    WORK['ads']['cham'] = tuple(float(x) for x in os.environ['DBS_ADS_CHAM'].split(','))
if os.environ.get('DBS_ADS_PITCH'):
    WORK['ads']['pitch'] = float(os.environ['DBS_ADS_PITCH'])
''')

a = "        self.fit_pinch()\n"
assert s.count(a) == 1
s = s.replace(a, "        w = WORK_BELT_REF\n        self.Gbeltref = hold_G(self.Ec, w['cham'], w['yaw'], w['pitch'], w['roll'], at=self.cham_mid)\n" + a)

a = "    Gwa = rig.Gwork['ads']\n"
assert s.count(a) == 1
s = s.replace(a, "    Gwa = rig.Gbeltref\n")

a = "WRIST_VIEW_HIP = (-0.20, 0.50, -0.84)"
assert s.count(a) == 1
s = s.replace(a, "WRIST_VIEW_HIP = tuple(float(x) for x in os.environ.get('DBS_WRIST_HIP', '-0.20,0.50,-0.84').split(','))")
a = "ODIR = os.path.join(L.ASSETS, 'models', 'human', 'animation', 'viewmodel', 'coop_dbshotgun')\n"
assert s.count(a) == 1
s = s.replace(a, "ODIR = os.environ.get('DBS_ODIR') or os.path.join(L.ASSETS, 'models', 'human', 'animation', 'viewmodel', 'coop_dbshotgun')     # DBS_ODIR: a trial bake elsewhere\n")
a = "    json.dump(paths, open(os.path.join(L.BUILD, 'hand_paths.json'), 'w'))\n"
assert s.count(a) == 1
s = s.replace(a, "    json.dump(paths, open(os.path.join(os.environ.get('DBS_ODIR') or L.BUILD, 'hand_paths.json'), 'w'))\n")
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('dbs_hands.py edited')
