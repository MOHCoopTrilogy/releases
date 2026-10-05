"""beltsched.py - ONE timeline per belt gun, shared by the world reload anim (beltgun.py) and the hands (recipes_keyed.py),
so the hand is on the cover / charging handle on exactly the frames they move. 98 frames at 1/30 s = the BAR torso.
Gun frame: x fwd, y right, z down, game units."""
import math
import numpy as np


def ease(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def curve(keys, f):
    for (fa, a), (fb, b) in zip(keys, keys[1:]):
        if fa <= f <= fb:
            return a + (b - a) * ease((f - fa) / float(max(1, fb - fa)))
    return keys[-1][1] if f > keys[-1][0] else keys[0][1]


GUNS = {
    'm1919': dict(
        cover_box=((1.8, 17.2), (-3.0, 3.0), (-6.4, -4.6)), hinge=(17.2, 0.0, -4.8),
        handle_box=((8.8, 10.2), (1.2, 4.2), (-3.4, -2.0)), handle_knob=(9.5, 3.6, -2.7),
        # cover: latch pressed f13, lifted by the hand to 25 deg f15-20, flicked on up to 75 deg f20-23 (polish: 3 frames later,
        # so the hand has 9 frames to leave the fore-end - it twisted 30 deg a frame) (a 15 u cover's
        # rear edge would leave the arm's reach), held open, pulled down near the hinge and pressed shut f63-70
        cover=[(0, 0.0), (15, 0.0), (20, 25.0), (23, 75.0), (63, 75.0), (70, 0.0), (97, 0.0)],
        # charging handle x travel: two pulls, each released under spring
        handle=[(0, 0.0), (74, 0.0), (77, -3.2), (78, -3.2), (80, 0.0), (81, 0.0), (84, -3.2), (85, -3.2), (87, 0.0), (97, 0.0)],
        belt_pt=(14.3, -2.4, -4.6), latch=(2.0, 0.0, -6.7),
        prop=(32, 58), gun_belt_hidden=(34, 56), clip_fill=72),
    'mg42': dict(
        cover_box=((2.3, 10.8), (-3.0, 3.0), (-6.6, -3.9)), hinge=(10.6, 0.0, -4.0),
        handle_box=((3.6, 4.9), (1.8, 2.6), (-4.1, 0.3)), handle_knob=(4.2, 2.3, -1.9),
        # MG42 drill: cock first (handle back, pushed forward by hand), then cover, belt, cover shut
        cover=[(0, 0.0), (24, 0.0), (32, 60.0), (34, 75.0), (74, 75.0), (81, 0.0), (97, 0.0)],
        handle=[(0, 0.0), (16, 0.0), (20, -4.0), (22, -4.0), (25, 0.0), (97, 0.0)],   # polish: f16 - the hand turns over first
        belt_pt=(7.6, -4.2, -3.9), latch=(2.6, 0.0, -6.5),
        prop=(43, 69), gun_belt_hidden=(45, 67), clip_fill=82),
}


def cover_angle(gun, f):
    return curve(GUNS[gun]['cover'], f)


def handle_dx(gun, f):
    return curve(GUNS[gun]['handle'], f)


def rot_y(a_deg):
    """the cover rotation: + = rear edge UP (z- is up) - matches beltgun's skc (skdlib quat (0, sin a/2, 0, cos a/2))"""
    a = math.radians(a_deg)
    return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])


def cover_point(gun, f, p):
    """where a cover point p (closed-cover gun frame) is at frame f"""
    H = np.array(GUNS[gun]['hinge'])
    Rm = rot_y(cover_angle(gun, f))
    return H + (np.asarray(p) - H) @ Rm


def handle_point(gun, f, p):
    return np.asarray(p) + np.array([handle_dx(gun, f), 0.0, 0.0])
