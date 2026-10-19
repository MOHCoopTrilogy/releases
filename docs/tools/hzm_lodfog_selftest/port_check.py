# -*- coding: utf-8 -*-
"""Line-for-line Python port of renderergl2/tr_hzm_lodfog.c + the properties of hzm_lodfog_selftest.c, runnable with
no compiler. It is NOT a substitute for build.bat (which tests the C itself); it proves the maths is right and that the
P1 test can fail (mutants below must be caught). python port_check.py -> exit 0 = PASS."""
import math, sys

AUTH, GOV, HAND = 0, 1, 2


def floor_(farplane, endScale, fx, fy):
    farEff = farplane * endScale
    if not farEff > 0: return 0.0
    if not (0 < fx < 179 and 0 < fy < 179): return 0.0
    tx = math.tan(fx * math.pi / 360); ty = math.tan(fy * math.pi / 360)
    return farEff * math.sqrt(1 + tx * tx + ty * ty)


def band(floorDist, cap, r, near, rng, scale, mutant=None):
    out = dict(near=near, range=rng, distScale=1.0, gate=0.0, true=False)
    if not floorDist > 0 or not cap > 0: return AUTH, out
    r = max(r, 0.0); scale = scale if scale > 0 else 1.0
    want = floorDist + (0 if mutant == "no_radius" else r)
    if want <= cap:
        out.update(near=max(near, want), distScale=scale, gate=want, true=True)
        return GOV, out
    k = (want - cap) / (0.25 * cap)
    if k >= 1: return AUTH, out
    if mutant == "jump": k = 1.0 if k > 0.5 else 0.0
    nearH = cap * (1 - k) + near * k
    out.update(near=max(near, nearH), distScale=scale * (1 - k) + k, true=True)
    return HAND, out


def fovy(fx, aspect):
    return 2 * math.degrees(math.atan(math.tan(math.radians(fx / 2)) / aspect))


def run(mutant=None):
    fails = []
    for far in (500, 1000, 1500, 1800, 2300, 3000, 5000):
        for fx in (40, 80, 90, 113.3, 130):
            for aspect in (4 / 3, 16 / 9, 3440 / 1440):
                fy = fovy(fx, aspect); fl = floor_(far, 1, fx, fy)
                tx = math.tan(math.radians(fx / 2)); ty = math.tan(math.radians(fy / 2))
                for r in (0, 65, 364, 1069):
                    for near in (0, 256, 900, 2000, 5000):
                        res, b = band(fl, 1e9, r, near, 300, 0.52, mutant)
                        if res != GOV: fails.append("P1 not governed"); continue
                        if b["near"] < near: fails.append("P5")
                        for k in range(81):
                            u = ((k % 9) / 4 - 1) * 1.1; v = ((k // 9) / 4 - 1) * 1.1
                            dx, dy, dz = u * tx, v * ty, 1.0; n = math.sqrt(dx * dx + dy * dy + dz * dz)
                            ox, oy, oz = dx / n * b["gate"], dy / n * b["gate"], dz / n * b["gate"]
                            for j in range(200):
                                t = (j + 0.5) / 200; phi = math.acos(1 - 2 * t); th = j * 2.39996322972865332
                                px = ox + r * math.sin(phi) * math.cos(th); py = oy + r * math.sin(phi) * math.sin(th); pz = oz + r * math.cos(phi)
                                if pz <= 0 or abs(px) > pz * tx or abs(py) > pz * ty: continue
                                if pz < far * 0.9999:
                                    fails.append("P1 far %d fx %.1f r %d z %.1f" % (far, fx, r, pz)); break
    # P3/P4 sweep
    fx = 113.3; fy = fovy(fx, 3440 / 1440); prev = None; seen = set()
    f = 200.0
    while f <= 4000:
        res, b = band(floor_(f, 1, fx, fy), 3500, 1069, 256, 256, 1.0, mutant); seen.add(res)
        if res == AUTH and (b["near"] != 256 or b["distScale"] != 1 or b["true"]): fails.append("P4")
        # continuity: a 1-unit fog step moves near' by at most 4 x edge (the hand-back slope bound) + 1
        edge = floor_(1, 1, fx, fy)
        if prev is not None and abs(b["near"] - prev) > 4 * edge + 1: fails.append("P3 jump at %d" % f)
        prev = b["near"]; f += 1
    if seen != {AUTH, GOV, HAND}: fails.append("P3 zones")
    return fails


OMAHA = ("m3l1a", "m3l1b", "e3l1", "e3l2", "obj_team3")


def name_excluded(n):
    if not n:
        return False
    base = n.replace("\\", "/").split("/")[-1]
    if base.lower().endswith(".bsp"): base = base[:-4]
    if len(base) > 4 and base.lower().endswith("_sml"): base = base[:-4]
    return base.lower() in OMAHA


def cached(name, cache, pointer_bug=False):
    key = "world" if pointer_bug else name          # the bug keyed on the tr.world pointer (&s_worldData, constant)
    if cache.get("valid") and cache["key"] == key:
        return cache["ex"], False
    cache.update(valid=True, key=key, ex=name_excluded(name))
    return cache["ex"], True


def order_check(pointer_bug=False):
    seq = ["maps/m3l1a.bsp", "maps/e2l2.bsp", "maps/m3l1a.bsp", "maps/e2l1.bsp", "maps/e2l1.bsp", "maps/obj/obj_team3.bsp", "maps/m6l1a.bsp"]
    want = [1, 0, 1, 0, 0, 1, 0]
    c = {}; fails = []
    for k, n in enumerate(seq):
        ex, _ = cached(n, c, pointer_bug)
        if int(ex) != want[k]: fails.append("P7 %d %s" % (k, n))
    for n in ("m3l1a", "maps/m3l1a.bsp", "M3L1B", "maps\\e3l1_sml", "e3l2", "maps/obj/obj_team3.bsp"):
        if not name_excluded(n): fails.append("P6 " + n)
    for n in ("", "e2l2", "maps/e2l1.bsp", "m3l1", "m3l1ab", "obj_team1", "e3l3"):
        if name_excluded(n): fails.append("P6 not " + n)
    return fails


if __name__ == "__main__":
    f = run()
    print("port: %s (%d fails)" % ("PASS" if not f else "FAIL", len(f)), f[:5])
    ok = not f
    for m in ("no_radius", "jump"):
        fm = run(m)
        print("mutant %-10s: %s" % (m, "caught (%d fails, e.g. %s)" % (len(fm), fm[0]) if fm else "NOT CAUGHT"))
        ok &= bool(fm)
    fo = order_check()
    print("P6/P7 order: %s" % ("PASS" if not fo else "FAIL %s" % fo))
    fb = order_check(pointer_bug=True)
    print("mutant pointer_cache (the shipped bug): %s" % ("caught (%s)" % fb[0] if fb else "NOT CAUGHT"))
    ok &= (not fo) and bool(fb)
    sys.exit(0 if ok else 1)
