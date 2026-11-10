"""corner_layout.py - the officer's gramophone corner: every position in one place (attic scene units: 52.5 per metre, the home
camera at x -36.7 y 21 z 102.4 looking +x, +y = screen left).  Used by make_attic_polish.py (the menu) and corner_preview.py.

His own tall side table at the near end of the gap between Weathers' work table and the long desk (its legs run out of the bottom
of the frame), the gramophone on it with the crank towards the room, the sleeve of the record that is playing leaning on the
gramophone's left side, and - while the pick is SHUFFLE - a pencilled tag tucked into the sleeve."""
import math

TABLE = (80.0, 37.0, 0.0)                  # hzm_corner_table (36.6 square, top at z 38.9)
TABLE_TOP = 38.9
TABLE_YAW = 0.0
GRAM_YAW = 90.0                            # crank towards the camera, tone arm on the right
GRAM = (83.5, 33.3, TABLE_TOP)             # model origin (footprint x 64.7..95.3, y 17.0..43.0 at yaw 90)
SPINDLE = (-0.327, 0.341, 13.194)          # gen_gram_model.py -> gram_spindle.txt (model space)
REC_R = 9.1


def _rot(x, y, yaw):
    a = math.radians(yaw)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


_sx, _sy = _rot(SPINDLE[0], SPINDLE[1], GRAM_YAW)
SPIN = (GRAM[0] + _sx, GRAM[1] + _sy, TABLE_TOP + SPINDLE[2] + 0.05)  # top face centre of the record
DISC = (GRAM[0] + _sx, GRAM[1] + _sy, TABLE_TOP)                      # hzm_gram_disc origin (its verts keep their z)
# the record's paper label: the art is an ellipse foreshortened for the home camera; framed on a board of the label's radius
LABEL = (SPIN[0], SPIN[1], SPIN[2], 3.0, 3.0)
# the sleeve: a 12-inch kraft sleeve on the table's left strip, leaning on the gramophone, facing the camera
SLEEVE_HALF = 7.8
SLEEVE = (73.0, 52.0, TABLE_TOP + SLEEVE_HALF + 0.2, SLEEVE_HALF, SLEEVE_HALF)
TAG = (SLEEVE[0] - 0.3, SLEEVE[1] - 3.6, SLEEVE[2] + SLEEVE_HALF + 1.7, 5.4, 2.4)   # the SHUFFLE tag tucked in behind the sleeve's top-right corner
HOT = (SPIN[0] - 6.0, (SPIN[1] + SLEEVE[1]) / 2, TABLE_TOP + 8.0, 17.0)
# v1.10.66 the 3D sleeve (gen_gram_model.py hzm_gram_sleeve3d<n> + hzm_gram_tag3d, its own frame): the bottom edge's centre on the
# table's left strip, turned to face the home camera (yaw 15: its front, local -X, looks back at the camera), the right-hand bottom
# corner tucked against the gramophone's left side, the top leaning back on it
SLEEVE3D = (70.0, 49.8, TABLE_TOP, 15.0)   # one hotspot over the gramophone + the sleeve

MODELS = [  # tik, x, y, z, yaw, anim
    ("models/menu/hzm_corner_table.tik", TABLE[0], TABLE[1], TABLE[2], TABLE_YAW, "none"),
    ("models/menu/hzm_gram.tik", GRAM[0], GRAM[1], GRAM[2], GRAM_YAW, "none"),
    ("models/menu/hzm_gram_disc.tik", DISC[0], DISC[1], DISC[2], 0.0, "idle"),
    # v1.10.62 the tone arm (gen_gram_model.py): its own model so it can lift / drop / track (engine scenemodelanim); an anim
    # value is required - without one Scene3D skips the actors' brightness pull-down and the arm draws brighter than the cabinet
    ("models/menu/hzm_gram_arm.tik", GRAM[0], GRAM[1], GRAM[2], GRAM_YAW, "play"),      # moved onto the pivot below
]
ARM_PIVOT = (-12.9, -0.11, 15.0)           # gen_gram_model.py ARM_PIVOT (model space): the arm model's origin
_px, _py = _rot(ARM_PIVOT[0], ARM_PIVOT[1], GRAM_YAW)
MODELS[-1] = (MODELS[-1][0], GRAM[0] + _px, GRAM[1] + _py, TABLE_TOP + ARM_PIVOT[2], GRAM_YAW, "play")
NEEDLE_LOCAL = (-3.559, -4.801, 14.859)    # gen_gram_model.py -> gram_arm.txt: the reproducer head mid-record (model space)
_nx, _ny = _rot(NEEDLE_LOCAL[0], NEEDLE_LOCAL[1], GRAM_YAW)
NEEDLE_HOT = (GRAM[0] + _nx, GRAM[1] + _ny, TABLE_TOP + NEEDLE_LOCAL[2], 4.5)   # the needle hotspot: the arm's head
# click on the needle (and on the gramophone): the arm lifts, the record changes while it is up, the arm drops on the lead-in
# with the crackle and plays on.  The track change rides `uiafter` (fires early on a key press); the arm's chain does not.
GRAM_SEQ = ("globalwidgetcommand atticscene scenemodelanim hzm_gram_arm lift,drop,play; uiafter 0.3 vstr ui_mmSelNext; "
            "uiafter 0.62 play sound/menu/hzm_gram_drop.wav")
MODELS_PREVIEW = [("hzm_corner_table", TABLE[0], TABLE[1], TABLE[2], TABLE_YAW, (120, 80, 50)),
                  ("hzm_gram", GRAM[0], GRAM[1], GRAM[2], GRAM_YAW, (110, 70, 40)),
                  ("hzm_gram_disc", DISC[0], DISC[1], DISC[2], 0.0, (20, 20, 22))]
# v1.10.61: the hover box naming the record that is playing (title + game), a dark caption plate just above the gramophone,
# shown only while the gramophone is hovered / focused (ui_scene_hot).  Centre over the record, clear of the sleeve and the tag.
HOVERBOX = (SPIN[0] - 2.0, SPIN[1] + 2.0, TABLE_TOP + 25.0, 17.0, 4.0)
LABELS_PREVIEW = [("sleeve", SLEEVE), ("tag", TAG), ("label", LABEL), ("hover", HOVERBOX)]

# ---- v1.10.62: the two former brown buttons' in-world homes (baked by attic62_edit.py; BU metres, Z up)
FIELD_REPORT_BU = (2.96, 4.35, 1.44)        # the FIELD REPORT dispatch board on the right-hand wall between the post and the MP door (0.41 x 0.55 m)
TOOLBOX_BU = (0.45, 1.60, 0.86)
CLOCK_BU = (1.137, 5.412, 2.2336)          # v1.10.62 the wall clock's dial centre (attic_room.blend clock_face): gen_clock.py's origin
FAN_HUB_BU = (1.9164, 4.9000, 2.2060)       # v1.10.62 the wall fan's spinner centre (attic62_edit -> rotor_axis.json): hzm_fan_rotor's origin             # the REPORT A BUG field toolbox on the long desk, where the film reels lay


def bu(p):
    """Blender (BU m) -> attic scene units: game = (y, -x, z) * 52.5"""
    return (p[1] * 52.5, -p[0] * 52.5, p[2] * 52.5)
