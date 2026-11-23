#!/usr/bin/env python3
"""Frontline character animations (EA eMotion, level emt_<level>.emt). Our own code, stdlib only; runs on the PLAYER's
PC inside the converter, output only into the player's own converted pak. Nothing Frontline-derived is shipped.

Reverse-engineered 2026-11-15 on the user's own Xbox USA disc (1_1 level.viv emt_1_1.emt + default.xbe; the XBE's
strings name the format "eMotion", loader at XBE 0x36f40, stream reader 0x384f0, pose decoder 0x3a120, angle lerp
0x3a470). All offsets are from the file start; the loader adds the file base to every pointer.

header  +0 'EMT\\0' (u32 0x454d5400), +4 u32 version 1, +0xc u16 pose count P, +0x10 ptr ANIMS, +0x14 ptr CLIPS,
        +0x18 ptr POSES (P x u32 pose offsets).
ANIMS   u32 n, n x 20 bytes: u16 animation id (the number the level scripts and the AI play, e.g. 6505 = the jeep
        gunner thrown), u16 0, u32 character class (1000 / 1010 / 1001 / 1002 / 1200 / 1300; resolved by the game to
        its class object), ptr VARIANTS, ptr (per-class parameters, shared), ptr (u32 count + 16-byte entries, 0).
VARIANTS u32 k, k x (u16 clip index, u16 w, ptr params): k > 1 = alternatives for the same animation id.
CLIPS   u32 n, n x ptr clip.
clip    +0 u8 frame time (x 1/16; the stream unit, see TIME), u8 (count), u8 flags (see FLAGS), u8 0, +4 ptr SKEL,
        +8 u16 stream: a value whose two top bits are not both set is a POSE index; 0xc000 / 0xc001 end the clip;
        0xc002 marks a loop start, 0xc003 <n> repeats it, 0xc004 <n> adds n/16 to the frame time, 0xc005 / 0xc006 set
        player flags; 0xc800-0xcfff are game ("user animation") opcodes, see OPS. An argument word: 12 bits signed, and
        with 0x1000 set a second u16 below it (0x384a0 / 0x38860).
OPS     (decodeaudit 2026-11-22) the stream reader (0x38625) hands a game opcode to the callback the game installs
        (0x37830 -> 0x34060: 0x37300; jump table 0x376a0 for 0xc803-0xc812, byte table 0x376e8 for 0xca00-0xca5d). The
        callback reads its own argument words from the stream (0x38860); an opcode it does not handle skips one word
        when its 0x1000 bit is set. 0xc803 <n> / 0xc804 / 0xc805 / 0xc807 / 0xc808 / 0xc809 / 0xc80a / 0xc810 /
        0xc811 <n> post object events 0x7e / 0x7d / 0x7f / 0x81 / 0xe2 / 0xe3 / 0xa7 / 0xfc / 0xff to the character's
        script (anim markers); 0xc806 <n> (0x80270) and 0xc80f <n> (0x80f70 -> the PLAYSOUND player 0x80860: sound n
        of the character's animation sound map, 1_1animSnd.som) are sounds; 0xc80b <a> <b>, 0xc80d / 0xc80e <n>
        (0x67d10 on / off), 0xc812 <n> (flags at +0xc30) are state; 0xc900 sets flag 0x10 (0x35e40: the clip's
        last-pose marker); 0xca00-0xca5d <n> (20 of them) send a movement-sound event (0x80150 -> 0x80226, the same
        AEMS block as the player's steps: action = opcode - 0xca01, surface = the ground under the man, source 2 =
        AI; fl_footsteps_notes.md): actions 4-8 steps, 9 land, 0x12 hard land, 22-99 other movement sounds.
SKEL    'SKEL' (0x534b454c), ptr BASE, ptr RANGES, u32 bones (55), u32 0.
BASE    u16 bones, then per bone 3 x int16 angles (x, y, z; 65536 = 360 degrees): the clip's base pose.
RANGES  u16 r, r x (u8 first bone, u8 count): the bones this clip animates. Every other bone holds its BASE angles.
pose    +0 u8 bones, u8 0, then int16: [1] root yaw (65536 = 360), [2] x, [3] y, [4] z, [5] z2 (metres x 1/4096),
        [6] -, [7..9] three angles (<< 8 in the engine; unused by the body), [10..12] a vector (x 1/4096);
        from byte 26: 3 x int16 per animated bone (RANGES order), ADDED to the BASE angles (wrapping int16).
        Bone 0 ('Top') never rotates in the pose; the root yaw / translation are its motion.
FLAGS   clip byte 2: 1 = mirror x, 2 = the root yaw is motion (not pose), 4 = the root x / y are motion (the actor
        travels; the pose stays over the origin), 8 = z2 is a separate channel (else z = z + z2), 0x10 = [7..12]
        are motion too.
bones   the 55 joints of Soldier.skl in its own order (flchar.read_skl); a bone's local rotation is the euler of its
        angles in flchar.EULER_ORDER (y . z . x), exactly as the .dmf bind rotations - which are the same numbers
        (the finger joints of a clip's BASE equal the bind but for the curl axis).
TIME    poses are spaced by the clip's frame time in 60 Hz ticks (64/16 = 4 ticks = 15 poses per second); the engine
        interpolates between neighbouring poses with 0x3a470 (int16 angle lerp, t in 1/4096, shortest way round).
"""
import struct

POSE_HEADER = 26
TICKS_PER_SECOND = 60.0
# game opcodes -> the argument words their handler reads (OPS above); every 0xca opcode the byte table routes to
# the movement-sound case takes one
OP_ARGS = {0xc803: 1, 0xc806: 1, 0xc80b: 2, 0xc80d: 1, 0xc80e: 1, 0xc80f: 1, 0xc811: 1, 0xc812: 1}
OP_ARGS.update({0xca00 + k: 1 for k in (0x00, 0x0a, 0x13, 0x16, 0x18, 0x19, 0x1e, 0x22, 0x24, 0x29, 0x2f, 0x34, 0x38,
                                         0x39, 0x3b, 0x3d, 0x43, 0x53, 0x5a, 0x5d)})


class Emt:
    def __init__(self, data):
        if data[:4] != b"\x00TME":
            raise ValueError("not an eMotion EMT file")
        self.d = data
        u32 = lambda o: struct.unpack_from("<I", data, o)[0]
        npose = struct.unpack_from("<H", data, 0xc)[0]
        self.poses = list(struct.unpack_from("<%dI" % npose, data, u32(0x18)))
        co = u32(0x14)
        self.clips = list(struct.unpack_from("<%dI" % u32(co), data, co + 4))
        ao = u32(0x10)
        self.anims = {}
        for i in range(u32(ao)):
            aid, _z, cls, vp, pp, _x = struct.unpack_from("<HHIIII", data, ao + 4 + 20 * i)
            var = []
            for j in range(u32(vp)):
                ci, w, prm = struct.unpack_from("<HHI", data, vp + 4 + 8 * j)
                var.append((ci, w, prm))
            self.anims[aid] = {"cls": cls, "variants": var, "params": pp}

    def clip_info(self, ci):
        d = self.d
        p = self.clips[ci]
        ft, cnt, flags, _ = d[p:p + 4]
        sk = struct.unpack_from("<I", d, p + 4)[0]
        if struct.unpack_from("<I", d, sk)[0] != 0x534B454C:
            raise ValueError("clip %d: no SKEL" % ci)
        base_p, rng_p, nb = struct.unpack_from("<3I", d, sk + 4)
        nbase = struct.unpack_from("<H", d, base_p)[0]
        base = [struct.unpack_from("<3h", d, base_p + 2 + 6 * i) for i in range(nbase)]
        nr = struct.unpack_from("<H", d, rng_p)[0]
        ranges = [(d[rng_p + 2 + 2 * k], d[rng_p + 3 + 2 * k]) for k in range(nr)]
        return {"frame_time": ft / 16.0 if ft else 1.0, "count": cnt, "flags": flags, "base": base,
                "ranges": ranges, "stream": p + 8}

    def _arg(self, o):
        w = struct.unpack_from("<H", self.d, o)[0]
        v = w & 0xfff
        if v & 0x800:
            v -= 0x1000
        if w & 0x1000:
            return (v << 16) + struct.unpack_from("<H", self.d, o + 2)[0], o + 4
        return v, o + 2

    def events(self, ci, max_words=4096):
        """the clip's stream as [(kind, value, tick)]: kind 'pose' (pose index) or 'op' (opcode, arg) - loops expanded
        once (a loop's repeat count is honoured, capped at 64)"""
        info = self.clip_info(ci)
        d = self.d
        o = info["stream"]
        ft = info["frame_time"]
        out, tick, stack, words = [], 0.0, [], 0
        while words < max_words:
            words += 1
            w = struct.unpack_from("<H", d, o)[0]
            o += 2
            if (w & 0xc000) != 0xc000:
                out.append(("pose", w, tick))
                tick += ft
                continue
            if w & 0x800:                       # game opcode (OPS): its handler reads its own argument words
                args = []
                for _k in range(OP_ARGS.get(w, 0)):
                    v, o = self._arg(o)
                    args.append(v)
                if w not in OP_ARGS and w & 0x1000:
                    args.append(struct.unpack_from("<H", d, o)[0])
                    o += 2
                out.append(("op", (w, args[0] if len(args) == 1 else (tuple(args) or None)), tick))
                continue
            k = w - 0xc000
            if k in (0, 1):
                out.append(("end", k, tick))
                break
            if k == 2:
                stack.append([o, None])
            elif k == 3:
                n, o = self._arg(o)
                if stack:
                    top = stack[-1]
                    if top[1] is None:
                        top[1] = min(max(n, 0), 64)
                    if top[1] > 0:
                        top[1] -= 1
                        o = top[0]
                    else:
                        stack.pop()
            elif k == 4:
                n, o = self._arg(o)
                ft += n / 16.0
            elif k in (5, 6):
                out.append(("flag", k, tick))
            elif (w & 0xe000) == 0xe000 and (w & 0x1000):
                o += 2
        return out

    def pose(self, ci, pi, info=None):
        """pose index pi under clip ci -> (root dict, [55 x (ax, ay, az) int16 angles])"""
        info = info or self.clip_info(ci)
        d = self.d
        p = self.poses[pi]
        nb = min(d[p], 0x50)
        h = struct.unpack_from("<13h", d, p)
        ang = [[0, 0, 0]] + [list(info["base"][i]) for i in range(1, nb)]
        q = p + POSE_HEADER
        for first, cnt in info["ranges"]:
            for b in range(first, first + cnt):
                dx, dy, dz = struct.unpack_from("<3h", d, q)
                q += 6
                if b < nb:
                    a = ang[b]
                    ang[b] = [((a[0] + dx + 32768) & 0xffff) - 32768, ((a[1] + dy + 32768) & 0xffff) - 32768,
                              ((a[2] + dz + 32768) & 0xffff) - 32768]
        f = info["flags"]
        sgn = -1.0 if f & 1 else 1.0
        z = (h[5] if f & 8 else h[4] + h[5]) / 4096.0
        root = {"yaw": h[1] * 360.0 / 65536.0 * (1 if f & 2 else -1), "x": sgn * h[2] / 4096.0, "y": h[3] / 4096.0,
                "z": z, "yaw_motion": bool(f & 2), "xy_motion": bool(f & 4), "raw": h}
        return root, [tuple(a) for a in ang]

    def frames(self, ci):
        """[(tick, root, angles)] for the clip's poses in play order"""
        info = self.clip_info(ci)
        return [(t, *self.pose(ci, v, info)) for k, v, t in self.events(ci) if k == "pose"]
