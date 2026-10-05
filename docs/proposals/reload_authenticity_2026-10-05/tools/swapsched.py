"""swapsched.py - ONE timeline per magazine-swap gun (drums, Lewis pan, C96 clip), shared by the gun's world reload
(worldanim.py: bolt / cocking-handle bone) and the hands (recipes_keyed.py), so a hand is on a moving part on exactly
the frames it moves. Frames are 1/30 s (= the hand clip and, for the MP18/Lewis/C96, the torso frames).
Gun frame: x fwd, y right, z down, game units.

prop = (frame the prop appears on tag_weapon_left, frame it is removed); the gun hides its own part 2 frames after the
prop appears and shows it 2 frames before it goes (overlap rule, rb2) - hide/show below.
bolt = weight keys 0 (rest = idle position) .. 1 (the other end of its travel); eased between keys.
"""
import numpy as np
from beltsched import curve

GUNS = {
    # Thompson 50rd (thompson50.tik, Bolt bone): the bolt rides home on the emptied gun (spring, f0-4), the left hand
    # pulls the top cocking knob back (f11-16; polish: 2 frames later so the hand leaves the grip without a forearm flip) - a Thompson drum only comes out / goes in with the bolt back - then the
    # drum slides out to the left and a full one slides in.
    'tommy50': dict(knob=(-0.87, -0.72, -5.51), travel=(5.05, 0.0, 0.0),
                    bolt=[(0, 0.0), (4, 1.0), (11, 1.0), (16, 0.0), (83, 0.0)],
                    prop=(24, 60), hide=(26, 58), nframes=84),
    # 1928 Tommy (thompsonsmg_tommy1928d.tik): no bolt bone in the mesh - drum only, same drum window.
    'tommy1928': dict(prop=(22, 60), hide=(24, 58), nframes=84),
    # MP18 (Bone2 = the right-side cocking handle plate): drum swap, then the RIGHT hand cocks it (f52-57), the handle
    # flies home under spring (f58-61) while the left hand still holds the gun by the drum.
    'mp18': dict(knob=(10.1, 1.9, -4.25), travel=(-8.42, 0.0, -0.34),
                 bolt=[(0, 0.0), (52, 0.0), (57, 1.0), (58, 1.0), (61, 0.0), (75, 0.0)],
                 prop=(10, 46), hide=(12, 44), nframes=76),
    # Lewis: top pan lifted off its post and a full one set on with a turn to lock (no bolt motion in the mesh)
    'lewis': dict(prop=(28, 60), hide=(30, 58), nframes=97),
}


def bolt_w(gun, f):
    return curve(GUNS[gun]['bolt'], f)


def knob_point(gun, f, p=None):
    g = GUNS[gun]
    p = np.asarray(g['knob'] if p is None else p, float)
    return p + np.asarray(g['travel']) * bolt_w(gun, f)
