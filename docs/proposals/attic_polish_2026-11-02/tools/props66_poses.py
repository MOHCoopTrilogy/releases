"""props66_poses.py - the v1.10.66 prop-quality QA close-ups as ui_scene_pose strings (BU eye -> BU target), shared by the before
and after runs (attic_run.py still ... "set ui_scene_pose <pose>"). Game = (BU.y, -BU.x, BU.z) * 52.5; pitch down positive."""
import math

SHOTS = [  # name, eye BU, look-at BU, vertical fov
    ("phones", (-0.15, 2.25, 1.45), (0.62, 3.10, 1.02), 40),
    ("papers", (-0.10, 1.95, 1.35), (0.15, 2.95, 0.80), 42),
    ("lamp_ledger_mug", (-0.95, 3.05, 1.45), (-0.25, 3.90, 0.90), 42),
    ("fieldphone_redbox", (-0.15, 3.35, 1.55), (0.50, 4.15, 1.10), 40),
    ("typewriter", (-4.00, 4.60, 1.60), (-4.75, 6.50, 1.00), 34),
    ("gramophone", (-1.05, 0.85, 1.20), (-0.65, 1.62, 0.84), 36),
    ("gramophone_oblique", (-1.25, 1.05, 0.95), (-0.80, 1.55, 0.82), 36),
    ("gramophone_glancing", (-0.45, 0.95, 0.86), (-0.95, 1.40, 0.82), 36),
    ("blueprint", (-2.02, 0.55, 1.75), (-2.02, 1.55, 0.93), 40),
]


def pose(eye, look, fov):
    e = [eye[1] * 52.5, -eye[0] * 52.5, eye[2] * 52.5]
    t = [look[1] * 52.5, -look[0] * 52.5, look[2] * 52.5]
    d = [t[i] - e[i] for i in range(3)]
    h = math.hypot(d[0], d[1])
    return "%.1f %.1f %.1f %.2f %.2f 0.00 %.2f" % (e[0], e[1], e[2], math.degrees(math.atan2(-d[2], h)), math.degrees(math.atan2(d[1], d[0])), fov)


if __name__ == "__main__":
    for n, e, l, f in SHOTS:
        print(n, pose(e, l, f))
