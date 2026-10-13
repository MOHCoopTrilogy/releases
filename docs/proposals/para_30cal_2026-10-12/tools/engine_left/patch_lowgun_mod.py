"""patch_lowgun_mod.py - the mod half of the crouched manning pose on a LOW gun (engine game1-next, COOP_TURRET_LOW):
two aliases for the retail crouched MG42 clips in models/player/base/anims_shared.txt, and crouch rows above the
standing ones in the two turret legs states of coop_mod/player_legs.st. Binary I/O, the files' own line ends; refuses
to run twice. Only the turret rows are touched."""
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


patch("models/player/base/anims_shared.txt", [(
    b"\tcoop_turret_stand_fire\t\tweapon_mg42/MG42_stand_firing.skc\n",
    b"\tcoop_turret_stand_fire\t\tweapon_mg42/MG42_stand_firing.skc\n"
    b"\t// HZM coop [bug-3658] the same on a LOW gun (engine condition COOP_TURRET_LOW): the AI gunner's crouched clips\n"
    b"\tcoop_turret_crouch_idle\t\tweapon_mg42/MG42_crouch_idle_a(loop).skc\n"
    b"\tcoop_turret_crouch_fire\t\tweapon_mg42/MG42_crouch_shooting.skc\n", 1)])

ROWS_OLD = (b"\t\tcoop_turret_stand_fire\t: ATTACK_PRIMARY_BUTTON\n"
            b"\t\tcoop_turret_stand_idle\t: default\n"
            b"\t}\n"
            b"\n"
            b"\tstates\n"
            b"\t{\n"
            b"\t\tSTAND : !%s\n")
ROWS_NEW = (b"\t\t// HZM coop [bug-3658] a LOW gun (one an AI gunner would crouch at, under 55 u over his feet): he\n"
            b"\t\t// crouches behind it. The engine sets the crouched hull / view height and the seat (Player::EnterTurret).\n"
            b"\t\tcoop_turret_crouch_fire\t: COOP_TURRET_LOW ATTACK_PRIMARY_BUTTON\n"
            b"\t\tcoop_turret_crouch_idle\t: COOP_TURRET_LOW\n"
            b"\t\tcoop_turret_stand_fire\t: ATTACK_PRIMARY_BUTTON\n"
            b"\t\tcoop_turret_stand_idle\t: default\n"
            b"\t}\n"
            b"\n"
            b"\tstates\n"
            b"\t{\n"
            b"\t\tSTAND : !%s\n")
patch("coop_mod/player_legs.st", [
    (ROWS_OLD % b"IS_USING_TURRET", ROWS_NEW % b"IS_USING_TURRET", 1),
    (ROWS_OLD % b"COOP_ON_TURRET", ROWS_NEW % b"COOP_ON_TURRET", 1),
])
