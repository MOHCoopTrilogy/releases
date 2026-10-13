"""An aim pose with the gun held further from the eye (list item D: "Luger: the settled aim sits too large / close").

The pistols that borrow the Colt aim pose sit where the COLT's sights belong. A gun whose rear sight is further back on
its mesh (Luger 1.6 u, Welrod 3.4 u) then stands that much closer to the eye and fills the centre of the screen. The
new pose is the approved two-handed pose with BOTH arms reaching `D` u further along the sight line (two-bone IK from
the unchanged shoulders, hands and fingers exactly as they are on the gun) - made by hold_bake itself: a 3-frame clip
of the pose, the middle frame keyed `back = -D`, that frame written out as the 1-frame pose.

    python pushpose.py <src pose under viewmodel/> <sight key> <D u> <out.skc> [--drop u]
needs IRONSIGHT_EXTRA_PAKS = the pak with the src pose AND _bases.pk3 (the 3-frame copy is put there by this script
on its first call: run it twice if it says so).
"""
import sys, os, zipfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
src, sight, D, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
drop = float(sys.argv[sys.argv.index('--drop') + 1]) if '--drop' in sys.argv else 0.0
tag = os.path.basename(src)[:-4]
b3 = 'viewmodel/pistol/coop_base_%s3.skc' % tag
b3f = os.path.join(HERE, 'bases', 'models', 'human', 'animation', b3.replace('/', os.sep))
if not os.path.isfile(b3f):
    subprocess.check_call([sys.executable, os.path.join(HERE, 'retime.py'), 'models/human/animation/' + src, b3f, '3'])
    with zipfile.ZipFile(os.path.join(HERE, '_bases.pk3'), 'w', zipfile.ZIP_DEFLATED) as z:
        root = os.path.join(HERE, 'bases')
        for d, _, fs in os.walk(root):
            for f in fs:
                z.write(os.path.join(d, f), os.path.relpath(os.path.join(d, f), root).replace(os.sep, '/'))
    print('made the 3-frame base', b3, '- run again'); sys.exit(3)
import revbake as RB
H = RB.H; R = RB.R
AIM = dict(aim=1, fing='aim')
z5 = (0.0,) * 5
rc = dict(gun=sight, hip=b3, charge=src, offhand=(-1, -1), enter=0, exit=0, slide={}, weight=dict(on=False), fixed_right=True,
          dip={0: z5, 1: (drop, 0.0, 0.0, 0.0, -D), 2: z5}, left_path={0: AIM, 1: AIM, 2: AIM}, handover=False,
          elbow_vec={'R': (0.0, -1.0, -0.2), 'L': (0.0, 0.0, -1.0)})
H.RECIPES['coopr_push'] = rc
sk, _ = H.bake('coopr_push', RB.CTL)
tmp = os.path.join(HERE, '_push_tmp.skc')
open(tmp, 'wb').write(R.skc_io.write(sk))
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
subprocess.check_call([sys.executable, os.path.join(HERE, 'retime.py'), tmp, out, 'slice', '1', '1'])
print('pose', out, 'gun', D, 'u further out, drop', drop)
