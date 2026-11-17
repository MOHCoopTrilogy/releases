"""M1 Garand / Mosin aimed reload, GUN KEPT UP (2026-11-17, user: "Fix the reload").

The shipped clips (riflereload.py 'garand' / 'mosin', rebaked here byte-identical to the v1.10.86 fixes pak) lower the
rifle 3.5-4.2 u straight down for the loading: the front sight sits just under the centre box but, by perspective, the
receiver - the part being worked - goes off the bottom of the picture (rear sight at 0.97-1.19 of the screen height
for most of the reload; the gun's own pixels fall from 12 % to under 2 %). Standing rule: work LOW but stay ON
TARGET, the gun up and in view, the centre clear.

The fix keeps every hand key, event and timing of the shipped recipe and changes only WHERE the rifle is held:
the butt stays in the shoulder (drop ~0 at the dip pivot, 22 u behind the eye) and the muzzle is lowered about it
(pitch 5-6 deg), the rifle a little forward. The front sight stays where it was (just under the box, still pointing at
the target), the receiver comes up into the lower third of the picture where the clip / charger goes in.

    cd rifles/assets; python ../m1_reload_fix/tools/upreload.py garand_up,mosin_up --root ../m1_reload_fix/stage
"""
import sys, os, copy, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import riflereload as RR

# ---- M1 GARAND ------------------------------------------------------------------------------------------------
g = copy.deepcopy(RR.GUNS['garand'])
g['holds'].update(
    # the pouch trip: the rifle on the left hand alone sags to the reaching side - with its weight - but stays UP, the
    # receiver in the picture (shipped: drop 3.9, rear sight at 1.18 of the screen height = under the frame)
    reach=dict(drop=-0.8, roll=25.0, pitch=5.0, side=-0.7, back=-4.0),
    # the clip is stood on the action and thumbed down HERE. This height is set by the HAND: the clip and the thumb
    # stand above the action, so the action can come no higher than the hand's top at the centre box's lower edge
    # (raised further - drop -1.0 - the clip hand covered 16-24 % of the box). The rifle is lowered to it just
    # before the clip arrives and comes up again once the thumb is clear
    load=dict(drop=0.5, roll=16.0, pitch=5.5, side=0.9, back=-4.5),
    push=dict(drop=-0.3, roll=13.0, pitch=5.5, side=0.7, back=-4.5),
    # the operating-rod handle ridden forward: no hand over the action, the rifle back up
    close=dict(drop=-0.8, roll=9.0, pitch=4.8, side=0.4, back=-4.5))
g['pose'] = [(0, None), (4, 'down'), (9, 'reach'), (16, 'reach'), (23, 'load'), (33, 'load'), (40, 'push'), (45, 'close'),
             (52, 'close'), (56, 'down'), (59, None), (60, None)]
# the pouch trip's cant: the shipped body_reach / body_back knocks (x2.0) rolled the rifle to ~28 deg - unseen while
# the receiver was under the frame, but with the rifle kept in view that reads as the gun tipped over to show its
# action (standing rule: never). Halved, and the hold's own roll with them: the rifle still sags to the reaching
# side with its weight, ~half as far
g['holds']['reach']['roll'] = 14.0
g['events'] = [(e[0], e[1], 1.0) + tuple(e[3:]) if e[1] in ('body_reach', 'body_back') else e for e in g['events']]
RR.GUNS['garand_up'] = g

# ---- MOSIN-NAGANT ---------------------------------------------------------------------------------------------
m = copy.deepcopy(RR.GUNS['mosin'])
m['holds'].update(
    # the rifle comes down after the bolt is opened (shipped: drop 2.5) - butt in the shoulder, muzzle lowered
    low=dict(drop=0.6, roll=13.0, pitch=3.0, side=0.7, back=-3.6),
    # the pouch trip (shipped: drop 3.9 - the receiver went under the frame)
    reach=dict(drop=-0.5, roll=25.0, pitch=4.0, side=-0.7, back=-3.1),
    # the charger brought up / the bolt worked with the action in the picture (shipped: drop 3.5)
    push=dict(drop=0.0, roll=13.0, pitch=4.0, side=0.7, back=-3.6),
    # the charger stood in the guides and thumbed down: the rifle is pressed down with the rounds (as the charger's
    # weight / the thumb's push would), low enough that the turned pressing hand stays under the centre box
    charge=dict(drop=3.0, roll=13.0, pitch=2.0, side=0.7, back=-3.4))
m['pose'] = [(0, None), (5, 'down'), (9, 'bolt'), (16, 'bolt'), (21, 'low'), (27, 'reach'), (36, 'push'), (42, 'charge'),
             (52, 'charge'), (57, 'push'), (62, 'low'), (67, 'close'), (77, 'close'), (83, 'down'), (89, None), (91, None)]
m['holds']['reach']['roll'] = 14.0
m['events'] = [(e[0], e[1], 1.0) + tuple(e[3:]) if e[1] in ('body_reach', 'body_back') else e for e in m['events']]
RR.GUNS['mosin_up'] = m


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('--root', default='.'); ap.add_argument('--set', action='append', default=[])
    a = ap.parse_args()
    for nm in a.gun.split(','):
        RR.bake(nm, a.root, 2.5, a.set)
