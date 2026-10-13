"""patch_lowgun_torso.py - second half of the mod side of the crouched manning pose on a LOW gun. Found in engine
(run b1): on a ground turret the TORSO state owns the whole body - TURRET_IDLE is `movetype anim`, and
Player::EvaluateState runs the legs machine only under MOVECONTROL_LEGS - so the rows patch_lowgun_mod.py put in the
two turret LEGS states are never evaluated there (the same finding as bug-309 for vehicle guns). The pose is the
torso state's action row. This adds: the crouched idle row in TURRET_IDLE, and a state TURRET_FIRE_LOW for the
firing clip (an action row is chosen once, on entering a state, so fire / idle need a state each).
The legs rows stay (harmless, and right if a ground turret ever runs the legs machine); their comment says so.
Binary I/O, the files' own line ends; refuses to run twice."""
MOD = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod/"


def patch(rel, pairs):
    p = MOD + rel
    raw = open(p, "rb").read()
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    assert not raw.startswith(b"\xef\xbb\xbf")
    for old, new, count in pairs:
        old = old.replace(b"\n", nl)
        new = new.replace(b"\n", nl)
        assert raw.count(old) == count, (rel, old[:60], raw.count(old))
        raw = raw.replace(old, new)
    raw.decode("ascii")
    open(p, "wb").write(raw)
    print(rel, "patched,", len(raw), "bytes")


patch("coop_mod/player_Torso.st", [(
    b"\t\tmg42tripod_crouch_aim_straight_straight\t: IS_WEAPON_ACTIVE \"mainhand\" \"Packed MG42 Turret\"\n"
    b"\t\tturret_idle\t\t\t\t: default\n"
    b"\t}\n"
    b"\n"
    b"\tstates\n"
    b"\t{\n"
    b"\t\tSTAND\t\t\t\t\t: !IS_USING_TURRET\n"
    b"\t}\n"
    b"}\n",
    b"\t\tmg42tripod_crouch_aim_straight_straight\t: IS_WEAPON_ACTIVE \"mainhand\" \"Packed MG42 Turret\"\n"
    b"\t\t// HZM coop [bug-3658] a LOW gun (engine condition COOP_TURRET_LOW: one an AI gunner would crouch at,\n"
    b"\t\t// under 55 u over his feet - the .30 cal a paratrooper leaves on a sandbag rest): he crouches behind it\n"
    b"\t\t// with the AI gunner's crouched clip. This state is `movetype anim`: the action row IS the whole body\n"
    b"\t\t// (the legs machine does not run on a turret). turret_idle = the retail standing clip, as before.\n"
    b"\t\tcoop_turret_crouch_idle\t\t\t: COOP_TURRET_LOW\n"
    b"\t\tturret_idle\t\t\t\t: default\n"
    b"\t}\n"
    b"\n"
    b"\tstates\n"
    b"\t{\n"
    b"\t\tSTAND\t\t\t\t\t: !IS_USING_TURRET\n"
    b"\t\tTURRET_FIRE_LOW\t\t\t\t: COOP_TURRET_LOW ATTACK_PRIMARY_BUTTON\t// [bug-3658] never true on a standing-height gun\n"
    b"\t}\n"
    b"}\n"
    b"\n"
    b"// HZM coop [bug-3658] the trigger held on a LOW gun: the crouched firing clip. A state of its own because an\n"
    b"// action row is chosen once, on entering the state.\n"
    b"state TURRET_FIRE_LOW\n"
    b"{\n"
    b"\tmovetype anim\n"
    b"\n"
    b"\taction\n"
    b"\t{\n"
    b"\t\tcoop_turret_crouch_fire\t\t\t: default\n"
    b"\t}\n"
    b"\n"
    b"\tstates\n"
    b"\t{\n"
    b"\t\tSTAND\t\t\t\t\t: !IS_USING_TURRET\n"
    b"\t\tTURRET_IDLE\t\t\t\t: !ATTACK_PRIMARY_BUTTON\n"
    b"\t}\n"
    b"}\n", 1)])

patch("coop_mod/player_legs.st", [(
    b"\t\t// crouches behind it. The engine sets the crouched hull / view height and the seat (Player::EnterTurret).\n",
    b"\t\t// crouches behind it. The engine sets the crouched hull / view height and the seat (Player::EnterTurret).\n"
    b"\t\t// On a ground turret the body is the TORSO state's (player_Torso.st TURRET_IDLE, movetype anim) and this\n"
    b"\t\t// legs state is not evaluated; the rows are here for the day it is.\n", 2)])
