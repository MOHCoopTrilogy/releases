"""eadefs.py: the level's definition blocks (archetypes, weapons, bullets) for the BYO converter. Our own code, stdlib only.

Decode audit gap 4 (2026-11-23). A definition block in level_a.str:
    u32 id (CRC32 of the definition's name), u32 class (CRC32 of the class name), u32 byte size, u32 ?, u32 n,
    n x {u32 CRC32(field name), u32 type (0 int, 1 float, 2 / 7 string or ref, 6 typed ref of 8 bytes), u32 size, data}
Classes used here (names recovered by CRC from the XBE's strings): ArchetypeType (the NPCSpawnPoint's word 18 .xdd),
EnemyWeaponType / PlayerWeaponType (word 20; the player's kit), ProjectileBulletType (a weapon's field 40cfd4c1, a
typed ref whose first word is the bullet's id). Field names are NOT on the disc (CRCs only); the readings below are
from the values across the 12 archetypes / 8 weapons and are marked [PROV] where they are inferred:
    bullet 1664515a  Damage per hit (the M1 rocket's ThrownBulletType carries 550 = the known rocket damage; the
                     grenade 150, the tank shell 100) - read as damage for the hitscan bullets too [PROV, strong]
    bullet c49152de  2.0 / 3.0: the head multiplier [PROV]
    arch   c514d0a5  hit points: Germans 50, Allied_Squad 40, Nemesis 800, named partisans 1500 [PROV, strong]
    arch   080cf4ed  skill tier: Green 5, Veteran 7, Elite 8, Nemesis 8, partisans 6 [PROV]
    arch   6a3361d5  reaction time s: Green 2.0, Veteran 1.5, Elite 1.0, Nemesis 0.5, Allied 2.5 [PROV]
    arch   6f3410f9  preferred fighting distance m: Close 25-35, Far 45-50, Sniper 70-80, partisans 20 [PROV]
"""
import re
import struct
import zlib

CLASSES = ("ArchetypeType", "EnemyWeaponType", "PlayerWeaponType", "ProjectileBulletType", "ThrownBulletType")
F = {k: zlib.crc32(k.encode()) & 0xffffffff for k in CLASSES}
F_DMG, F_HEAD, F_BULLET = 0x1664515a, 0xc49152de, 0x40cfd4c1
F_HP, F_TIER, F_REACT, F_RANGE = 0xc514d0a5, 0x080cf4ed, 0x6a3361d5, 0x6f3410f9


def _parse(d, o):
    ident, cls, size, _u, n = struct.unpack_from("<5I", d, o)
    if not (0 < n < 200 and 20 < size < 0x10000):
        return None
    p, at = o + 20, {}
    for _i in range(n):
        if p + 12 > len(d):
            return None
        h, t, s = struct.unpack_from("<3I", d, p)
        if t > 16 or s > 4096:
            return None
        v = d[p + 12:p + 12 + s]
        if t == 1 and s == 4:
            v = struct.unpack("<f", v)[0]
        elif t == 0 and s == 4:
            v = struct.unpack("<i", v)[0]
        elif t == 6 and s >= 4:
            v = struct.unpack_from("<I", v)[0]
        at.setdefault(h, v)
        p += 12 + s
    return ident, cls, at


def read(stream, names=()):
    """-> {class name: {id: {field crc: value}}} for the classes above; names maps id -> name for the ones given"""
    out = {k: {} for k in CLASSES}
    inv = {v: k for k, v in F.items()}
    pat = re.compile(b"|".join(re.escape(struct.pack("<I", c)) for c in F.values()))
    for m in pat.finditer(stream):
        o = m.start() - 4
        if o < 0 or o % 4:
            continue
        r = _parse(stream, o)
        if r and r[1] in inv:
            out[inv[r[1]]].setdefault(r[0], r[2])
    return out


# the co-op kit's own per-hit damage (the mod's weapon tiks, "dm" bulletdamage, what a co-op server uses): the disc's
# PlayerGewehr is our G43, its PlayerPPSH our PPSh. Not disc data: the other half of the shots-to-kill parity
OUR_KIT = {"PlayerGewehr": 50.0, "PlayerPPSH": 24.0}
# [0.7.57, C56 partisans] the German NPC guns as the mod fires them at other actors (gametype 2 = the tiks' "dm
# bulletdamage": models/weapons/g43.tik 50 - the NPC Gewehr is the G43, 0.7.54 - and mp40.tik 24)
NPC_AXIS = {"NpcWpn_Gewehr": 50.0, "NpcWpn_mp40": 24.0}


def crc(name):
    return zlib.crc32(name.encode()) & 0xffffffff


def bullet_damage(defs, weapon_name, cls="EnemyWeaponType"):
    w = defs[cls].get(crc(weapon_name))
    if not w or F_BULLET not in w:
        return None
    b = defs["ProjectileBulletType"].get(w[F_BULLET])
    return (b.get(F_DMG), b.get(F_HEAD)) if b else None


def hp_scale(hp, disc_dmg, our_dmg):
    """[gap 4, the Frontline agent's shots-to-kill parity] a K such that ceil(hp * K / ours) == ceil(hp / disc) for every
    weapon pair, the middle of the feasible range (None when no single K fits)"""
    import math
    lo, hi = 0.0, 1e9
    for d_, o_ in zip(disc_dmg, our_dmg):
        n = math.ceil(hp / d_ - 1e-9)
        lo = max(lo, (n - 1) * o_ / hp)
        hi = min(hi, n * o_ / hp)
    if lo >= hi:
        return None, (lo, hi)
    return round((lo + hi) / 2, 3), (round(lo, 3), round(hi, 3))


def best_scale(hp, disc_dmg, our_dmg):
    """[0.7.54] the hp_scale K when one exists; otherwise the K whose worst relative shots-to-kill error over the weapon
    pairs is smallest (ties: the smaller total error), searched in steps of 0.005. -> (K, [(disc hits, our hits), ...])"""
    import math
    k, _r = hp_scale(hp, disc_dmg, our_dmg)
    want = [math.ceil(hp / d_ - 1e-9) for d_ in disc_dmg]
    if k is None:
        best = None
        for i in range(100, 1000):
            kk = i * 0.005
            got = [math.ceil(hp * kk / o_ - 1e-9) for o_ in our_dmg]
            err = [abs(g - w) / w for g, w in zip(got, want)]
            key = (round(max(err), 4), round(sum(err), 4))
            if best is None or key < best[0]:
                best = (key, round(kk, 3))
        k = best[1]
    return k, [(w, math.ceil(hp * k / o_ - 1e-9)) for w, o_ in zip(want, our_dmg)]

