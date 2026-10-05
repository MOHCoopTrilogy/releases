#!/usr/bin/env python3
# sky_envelope.py - offline per-map flight envelope for coop aircraft (READ-ONLY on the retail paks).
#
# For each campaign map it measures, straight from the BSP:
#   ground   : z of OUTDOOR pathnodes (percentiles) - the playable ground band
#   ceiling  : the first z above each outdoor node where the point leaves a valid leaf (cluster == -1).
#              That is exactly the server's transmit test (sv_world.c SV_LinkEntity -> numClusters/areanum,
#              sv_snapshot.c: areanum -1 / numClusters 0 => never sent). An entity whose origin box is above
#              it is NEVER transmitted, whatever its loopsound or model.
#   obstacle : highest solid/terrain top under the sky over the play area (static models NOT included)
#   slab     : at the chosen altitude, the longest straight run through the play-area centre that stays in
#              valid leafs (how far a plane can fly in/out before it blinks out at the hull)
#   fog      : runtime fog distance (fog_profiles.tsv dist, else worldspawn farplane, 0 = none)
#
# Usage: python sky_envelope.py [map ...]   (no args = every coop campaign map) -> sky_envelope.tsv
import os, sys, struct, zipfile, math, statistics

ROOTS = [r"G:\GOG\Medal of Honor - Allied Assault War Chest"]
SUBS = ("main", "mainta", "maintt")
HERE = os.path.dirname(os.path.abspath(__file__))
FOG_TSV = r"C:\mohaa-coop-dev\docs\tools\fog_profiles.tsv"

MAPS = ("m1l1 m1l2a m1l2b m1l3a m1l3b m1l3c m2l1 m2l2a m2l2b m2l2c m2l3 m3l1a m3l1b m3l2 m3l3 m4l0 m4l1 "
        "m4l2 m4l3 m5l1a m5l1b m5l2a m5l2b m5l3 m6l1a m6l1b m6l1c m6l2a m6l2b m6l3a m6l3b m6l3c m6l3d m6l3e "
        "e1l1 e1l2 e1l3 e1l4 e2l1 e2l2 e2l3 e3l1 e3l2 e3l3 e3l4 t1l1 t1l2 t1l3 t2l1 t2l2 t2l3 t2l4 t3l1 t3l2").split()

SURF_SKY = 0x4
FT = 16.0  # units per foot (c47fly.tik: "world is in 16 units per foot")

_paks = None
def paks():
    global _paks
    if _paks is None:
        _paks = []
        for r in ROOTS:
            for s in SUBS:
                d = os.path.join(r, s)
                if os.path.isdir(d):
                    for f in sorted(os.listdir(d)):
                        if f.lower().endswith(".pk3"):
                            _paks.append(os.path.join(d, f))
    return _paks

def find_bsp(m):
    hit = None
    for p in paks():  # later paks win, like the engine
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            if n.lower() == "maps/%s.bsp" % m:
                hit = (p, n)
        z.close()
    if not hit:
        return None, None
    z = zipfile.ZipFile(hit[0]); b = z.read(hit[1]); z.close()
    return b, os.path.basename(hit[0])

class BSP:
    def __init__(s, b):
        s.b = b
        s.ver = struct.unpack_from("<i", b, 4)[0]
        def L(i):
            if s.ver <= 18 and i > 12:
                i += 1
            off, ln = struct.unpack_from("<ii", b, 12 + i * 8)
            return b[off:off + ln]
        sh = L(0)
        s.shflags = [struct.unpack_from("<ii", sh, i * 140 + 64) for i in range(len(sh) // 140)]
        pl = L(1)
        s.planes = [struct.unpack_from("<4f", pl, i * 16) for i in range(len(pl) // 16)]
        nd = L(9)
        s.nodes = [struct.unpack_from("<3i", nd, i * 36) for i in range(len(nd) // 36)]
        lf = L(8)
        lsz = 64 if len(lf) % 64 == 0 and s.ver > 17 else 48
        if len(lf) % lsz:
            lsz = 48 if lsz == 64 else 64
        s.leafs = []
        for i in range(len(lf) // lsz):
            c, a = struct.unpack_from("<2i", lf, i * lsz)
            fb, nb = struct.unpack_from("<2i", lf, i * lsz + 40)
            s.leafs.append((c, a, fb, nb))
        lb = L(6)
        s.leafbrushes = struct.unpack_from("<%di" % (len(lb) // 4), lb, 0)
        br = L(12)
        s.brushes = [struct.unpack_from("<3i", br, i * 12) for i in range(len(br) // 12)]
        bs = L(11)
        s.sides = [struct.unpack_from("<3i", bs, i * 12) for i in range(len(bs) // 12)]
        s.skybrush = {}
        md = L(13)
        s.world = struct.unpack_from("<6f", md, 0)
        s.ents = L(14).decode("latin-1", "replace")
        s.terrain = {}
        tr = L(22)
        for psz in (388, 372, 369):
            if len(tr) and len(tr) % psz == 0:
                for i in range(len(tr) // psz):
                    o = i * psz
                    x, y = struct.unpack_from("<2b", tr, o + 20)
                    base = struct.unpack_from("<h", tr, o + 22)[0]
                    hm = tr[o + 288:o + 369]
                    hmax = base + 2 * max(hm)
                    hmin = base + 2 * min(hm)
                    s.terrain[(x << 6, y << 6)] = (hmin, hmax)
                break

    def leaf(s, x, y, z):
        n = 0
        while n >= 0:
            pn, c0, c1 = s.nodes[n]
            nx, ny, nz, d = s.planes[pn]
            n = c0 if nx * x + ny * y + nz * z - d >= 0 else c1
        return -n - 1

    def valid(s, x, y, z):
        c, a, fb, nb = s.leafs[s.leaf(x, y, z)]
        return c != -1 and a != -1

    def is_sky_leaf(s, li):
        c, a, fb, nb = s.leafs[li]
        for k in range(fb, fb + nb):
            bi = s.leafbrushes[k]
            v = s.skybrush.get(bi)
            if v is None:
                f, n, shn = s.brushes[bi]
                v = False
                for j in range(f, f + n):
                    sn = s.sides[j][1]
                    if 0 <= sn < len(s.shflags) and s.shflags[sn][0] & SURF_SKY:
                        v = True; break
                s.skybrush[bi] = v
            if v:
                return True
        return False

    def terrain_top(s, x, y):
        k = (int(math.floor(x / 512.0)) * 512, int(math.floor(y / 512.0)) * 512)
        t = s.terrain.get(k)
        return t[1] if t else None

def parse_ents(t):
    out = []; i = 0
    while True:
        a = t.find("{", i)
        if a < 0: break
        b = t.find("}", a)
        if b < 0: break
        body = t[a + 1:b]; d = {}; j = 0
        while True:
            k1 = body.find('"', j)
            if k1 < 0: break
            k2 = body.find('"', k1 + 1); v1 = body.find('"', k2 + 1); v2 = body.find('"', v1 + 1)
            if min(k2, v1, v2) < 0: break
            d[body[k1 + 1:k2].lower()] = body[v1 + 1:v2]; j = v2 + 1
        out.append(d); i = b + 1
    return out

def fog_rows():
    r = {}
    for ln in open(FOG_TSV, encoding="utf-8"):
        if ln.startswith("#") or ln.startswith("map\t") or not ln.strip():
            continue
        f = ln.rstrip("\n").split("\t")
        r[f[0].lower()] = (f[1], float(f[2]))
    return r

def pct(v, p):
    v = sorted(v)
    if not v: return float("nan")
    return v[min(len(v) - 1, max(0, int(round(p / 100.0 * (len(v) - 1)))))]

def analyse(m, fogs):
    b, pak = find_bsp(m)
    if b is None:
        return {"map": m, "note": "bsp not found"}
    s = BSP(b)
    ents = parse_ents(s.ents)
    ws = ents[0] if ents else {}
    nodes = []
    for e in ents:
        if e.get("classname", "").lower() == "info_pathnode" and "origin" in e:
            try: nodes.append(tuple(float(v) for v in e["origin"].split()[:3]))
            except Exception: pass
    ZCAP = {"t3l1": 500, "t3l2": 500}
    if m in ZCAP:
        nodes = [n for n in nodes if n[2] < ZCAP[m]]
    if len(nodes) > 1600:
        nodes = nodes[::max(1, len(nodes) // 1600)]
    wmin, wmax = s.world[:3], s.world[3:]
    out_g, out_c, roof = [], [], 0
    pts = []
    for (x, y, z) in nodes:
        zz = z + 48
        if not s.valid(x, y, zz):
            continue
        top = wmax[2] + 64
        while zz < top and s.valid(x, y, zz):
            zz += 64
        lo, hi = zz - 64, zz
        for _ in range(5):  # refine to ~2u
            mid = (lo + hi) / 2
            if s.valid(x, y, mid): lo = mid
            else: hi = mid
        li = s.leaf(x, y, hi + 1)
        if s.is_sky_leaf(li):
            out_g.append(z); out_c.append(lo); pts.append((x, y, z, lo))
        else:
            roof += 1
    res = {"map": m, "pak": pak, "ver": s.ver, "nodes": len(nodes), "outdoor": len(pts), "indoor": roof,
           "farplane_ws": float(ws.get("farplane", "0") or 0), "cull_ws": ws.get("farplane_cull", "-"),
           "skyportal": "1" if any(e.get("classname", "").lower() == "info_skyorigin" or "skyorigin" in e.get("classname", "").lower() for e in ents) else "0"}
    fr = fogs.get(m)
    res["fog"] = fr[1] if fr and fr[1] > 0 else res["farplane_ws"]
    res["fogsrc"] = (fr[0] if fr and fr[1] > 0 else ("ws" if res["farplane_ws"] > 0 else "none")) + ("/scripted" if fr and fr[0] == "colour-only" else "")
    if not pts:
        res["note"] = "no outdoor pathnodes"
        return res
    res["g05"], res["g50"], res["g95"] = pct(out_g, 5), pct(out_g, 50), pct(out_g, 95)
    clr = [c - g for (_, _, g, c) in pts]
    res["c_min"], res["c10"], res["c50"] = min(out_c), pct(out_c, 10), pct(out_c, 50)
    res["c25"] = pct(out_c, 25)
    res["_pts"] = pts
    res["clr10"], res["clr50"] = pct(clr, 10), pct(clr, 50)
    # obstacle tops over the outdoor play area (grid), below the sky ceiling
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs) - 512, max(xs) + 512, min(ys) - 512, max(ys) + 512
    step = 384
    tops = []
    gx = x0
    while gx <= x1:
        gy = y0
        while gy <= y1:
            # start just under the local sky (median ceiling) and march down to the first solid
            zz = res["c50"] - 32
            if s.valid(gx, gy, zz):
                floor = res["g05"] - 600
                while zz > floor and s.valid(gx, gy, zz):
                    zz -= 48
                cand = []
                if zz > floor:
                    cand.append(zz)
                tt = s.terrain_top(gx, gy)
                if tt is not None and tt < res["c50"]:
                    cand.append(tt)
                if cand:
                    tops.append(max(cand))
            gy += step
        gx += step
    res["top95"] = pct(tops, 95) if tops else float("nan")
    res["topmax"] = max(tops) if tops else float("nan")
    res["cx"], res["cy"] = statistics.median(xs), statistics.median(ys)
    res["span"] = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    s_ref = s
    res["_bsp"] = s_ref
    return res

def slab_run(s, cx, cy, z, maxr=40000):
    """longest straight run through (cx,cy) at altitude z staying in valid leafs; returns (len, yaw, back, fwd)."""
    best = (0, 0, 0, 0)
    if not s.valid(cx, cy, z):
        return best
    for yaw in range(0, 180, 15):
        dx, dy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        ext = []
        for sg in (1, -1):
            r = 0
            while r < maxr and s.valid(cx + sg * dx * (r + 128), cy + sg * dy * (r + 128), z)                     and abs(cx + sg * dx * (r + 128)) < 8000 and abs(cy + sg * dy * (r + 128)) < 8000:
                r += 128
            ext.append(r)
        if ext[0] + ext[1] > best[0]:
            best = (ext[0] + ext[1], yaw, ext[1], ext[0])
    return best

def choose(res):
    """altitude band + chosen altitude (absolute z) per the PLAN rules."""
    if "g50" not in res:
        return
    g = res["g50"]; F = res["fog"] or 0
    ceil = res["c10"] - 96                      # origin link box +-32, plus margin; 10th pct of outdoor sky
    floor = max(res["top95"] + 256, g + 640)    # 95th-pct structure top + 16 ft, never under 40 ft
    vis = g + (0.55 * F if F > 0 else 99999)    # slant range to a player under the track stays well inside fog
    hi = min(ceil, vis, g + 4000)
    res["band_lo"], res["band_hi"] = floor, hi
    if hi >= floor:
        alt = floor + 0.6 * (hi - floor)
        res["fit"] = "ok" if hi - floor >= 400 else "tight"
    else:
        alt = hi
        res["fit"] = "LOW-CEIL" if ceil < floor else "FOG"
    res["alt"] = alt
    H = alt - g
    res["H"] = H
    pts = res["_pts"]
    cand = sorted(pts, key=lambda p: math.hypot(p[0] - res["cx"], p[1] - res["cy"]))[:12] + pts[::max(1, len(pts) // 12)]
    run = (0, 0, 0, 0)
    for p in cand:
        r2 = slab_run(res["_bsp"], p[0], p[1], alt)
        if r2[0] > run[0]:
            run = r2
    # TODAY: what the shipped code does on this map
    g2 = res["g50"]
    c47z = g2 + 2200
    res["c47_today"] = ("ABOVE-SKY" if c47z > res["c50"] else "under-sky") + ("/past-fog" if F > 0 and 2200 > F else "")
    fp = F if F > 0 else 8000
    balt = min(1100, fp * 0.7 * 0.45)
    res["bomb_alt"], res["bomb_low"] = balt, balt * 0.4
    res["bomb_today"] = ("peak-ABOVE-SKY" if g2 + balt > res["c10"] else "ok") + ("/low=%d" % (balt * 0.4))
    res["run"], res["run_yaw"], res["run_back"], res["run_fwd"] = run
    # visible half-track inside fog for a player under the centre (slant <= 0.8 F)
    res["vis_half"] = math.sqrt(max(0.0, (0.8 * F) ** 2 - H * H)) if F > 0 else 99999

def main():
    maps = [a.lower() for a in sys.argv[1:]] or MAPS
    fogs = fog_rows()
    cols = ["map", "ver", "nodes", "outdoor", "indoor", "fog", "fogsrc", "farplane_ws", "skyportal", "g05", "g50", "g95",
            "c_min", "c10", "c25", "c50", "clr10", "clr50", "top95", "topmax", "span", "band_lo", "band_hi", "fit", "alt", "H",
            "run", "run_yaw", "run_back", "run_fwd", "vis_half", "c47_today", "bomb_alt", "bomb_today", "note"]
    rows = []
    for m in maps:
        r = analyse(m, fogs)
        try:
            choose(r)
        except Exception as ex:
            r["note"] = "choose failed: %s" % ex
        r.pop("_bsp", None); r.pop("_pts", None)
        rows.append(r)
        print("\t".join(str(int(r[c]) if isinstance(r.get(c), float) and not math.isnan(r[c]) else r.get(c, "")) for c in cols), flush=True)
    with open(os.path.join(HERE, "sky_envelope.tsv"), "w", encoding="utf-8") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(int(r[c]) if isinstance(r.get(c), float) and not math.isnan(r[c]) else r.get(c, "")) for c in cols) + "\n")

if __name__ == "__main__" and not os.environ.get("PLAN_TABLE"):
    main()

# ---------------------------------------------------------------- PLAN table (rules in PLAN.md section 3)
def plan_rows(tsv):
    lines = open(tsv, encoding="utf-8").read().splitlines()
    hdr = lines[0].split("	")
    out = []
    for ln in lines[1:]:
        r = dict(zip(hdr, ln.split("	")))
        m = r["map"]
        if not r.get("g50") or int(r.get("outdoor") or 0) < 40:
            out.append((m, "-", "-", (r["fog"] if r["fog"] not in ("", "0") else "none"), "-", "-", "-", "-", "-", "-",
                        "D", "interior / sky opening too small (%s outdoor nodes): engine audio + flak + shadow only" % r.get("outdoor")))
            continue
        f = lambda k: float(r[k]) if r.get(k) not in ("", "nan", None) else float("nan")
        g, g05, g95, c10, c50, F = f("g50"), f("g05"), f("g95"), f("c10"), f("c50"), f("fog")
        top, tmax = f("top95"), f("topmax")
        obs = max(0.0, (top - g)) if top == top else 0.0
        omax = max(0.0, (tmax - g)) if tmax == tmax else 0.0
        clr = c10 - g
        hmin = max(obs + 384, 640)
        hfog = 0.5 * F if F > 0 else 1e9
        hsky = clr - 128
        hc = min(hfog, 2400)
        above = False
        if hsky >= hmin + 200:
            hc = min(hc, hsky)
        elif hc > hsky:
            above = True
        cls = "A" if (F == 0 or F >= 6000) else "B"
        if above:
            cls = "C"
        note = []
        s_ = max(0.25, min(1.0, hc / 8000.0))
        v = s_ * 2600
        if F > 0:
            half = math.sqrt(max(0.0, (0.8 * F) ** 2 - hc ** 2))
            lvis = min(2 * half, float(r["run"] or 0) if not above else 2 * half)
            entry = "fog edge +-%d" % math.sqrt(max(0.0, (1.05 * F) ** 2 - hc ** 2))
        else:
            lvis = min(float(r["run"] or 0), 16000)
            entry = "edge, yaw %s: -%s/+%s" % (r["run_yaw"], r["run_back"], r["run_fwd"])
        tvis = lvis / v if v else 0
        hpass = max(hmin, 0.6 * hc)
        if above:
            note.append("sky brush only +%d over ground: fly ABOVE it with svflags +broadcast (gate G3)" % clr)
        if g95 - g05 > 1200:
            note.append("ground %d..%d: altitude follows LOCAL ground" % (g05, g95))
        if c10 < c50 - 200:
            note.append("low-sky pockets (sky %d..%d)" % (c10, c50))
        if omax > obs + 600:
            note.append("isolated tall structure +%d: track trace must clear it" % omax)
        today = []
        today.append("C-47 " + ("above sky" if r["c47_today"].startswith("ABOVE") else "under sky") + (", past fog" if "past-fog" in r["c47_today"] else ""))
        bt = r["bomb_today"]
        today.append("bomber " + ("peak above sky" if bt.startswith("peak") else "ok") + ", dives to " + bt.split("low=")[1] + "u")
        out.append((m, "%d (%d..%d)" % (g, g05, g95), "%d / +%d" % (c10, clr), ("%d" % F) if F > 0 else "none",
                    "+%d / +%d" % (obs, omax), "+%d (s %.2f, looks %d ft)" % (hc, s_, hc / s_ / 16), "+%d" % hpass,
                    "%d u, %.1f s at %d u/s" % (lvis, tvis, v), entry, "; ".join(today), cls, "; ".join(note)))
    return out

if __name__ == "__main__" and os.environ.get("PLAN_TABLE"):
    for row in plan_rows(os.path.join(HERE, "sky_envelope.tsv")):
        print("| " + " | ".join(str(x) for x in row) + " |")
