"""S&W M10: the chambers fill ONE BY ONE (list item C, coordinator 2026-10-12).

  mesh   six surfaces coop_round1..6 (one cartridge head each, on the cylinder bone) appended to the staged m10.skd;
         the old all-six surface coop_m10_heads stays in the file but is hidden for good (tik init).
         Round k (1..5) sits on the chamber k index-steps behind the feed chamber, round 6 on the feed chamber itself.
  clip   coop_m10_single_slow.skc: after the round is seated (frame 20 of 24) the cylinder turns one chamber over the
         last four frames (12 deg a frame; the clip's restart completes the 60) - the loaded chambers walk away from
         the feed position and the next empty one arrives.
  tik    the six shader lines; the two frame commands that showed / hid coop_m10_heads go.
  cgame  (ads-next) draws coop_round<N> iff N <= rounds in the gun, latched during the loop so the new head appears
         when the loop restarts, i.e. once its chamber has turned away from under the hand.

    python m10rounds.py            (after m10face.py / m10build.py; writes into stage/; idempotent)
"""
import sys, os, io, re, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
import m10face as F
R = gunskc.R
np.set_printoptions(precision=3, suppress=True)
STAGE = os.path.join(HERE, 'stage')
GD = os.path.join(STAGE, 'models', 'weapons', 'coop_m10')
fr = json.load(open(os.path.join(HERE, 'm10_frame.json')))
pts = json.load(open(os.path.join(HERE, 'm10_points.json')))
face = json.load(open(os.path.join(HERE, 'm10_face.json')))
A = np.array(fr['A']); S = float(np.linalg.norm(A[0])); M = A / S
c0 = (np.array(fr['cyl_min']) + np.array(fr['cyl_max'])) / 2
rad = (fr['cyl_max'][2] - fr['cyl_min'][2]) / 2
Pg = np.array([c0[0], c0[1] - 0.17, c0[2] + rad + 0.08])            # the crane pivot, as m10build.py

# ---- the open pose, read back from the existing loop clip
LOOP = os.path.join(GD, 'coop_m10_single_slow.skc')
BAK = os.path.join(HERE, '_m10_single_slow_nospin.skc')
if not os.path.isfile(BAK):
    open(BAK, 'wb').write(open(LOOP, 'rb').read())                  # the un-spun clip is the source of every re-run
raw = open(BAK, 'rb').read()
a = R.load(BAK)
cr, cp = a.names.index('coop_cyl rot'), a.names.index('coop_cyl pos')
Rst = R.quat_to_rows(a.V[0, cr]); tl = a.V[0, cp, :3].copy()
best = None
for tr in (False, True):
    Rl = Rst.T if tr else Rst
    Rg = M.T @ Rl @ M
    err = float(np.linalg.norm(((c0 - Pg) @ Rg + Pg)[1:] - np.array(pts['c_open'])[1:]))
    if best is None or err < best[0]:
        best = (err, tr, Rg)
err, TRANSPOSE, Rg = best
assert err < 0.15, err
c1 = (c0 - Pg) @ Rg + Pg
d = np.linalg.lstsq((Rg - np.eye(3)).T, tl @ A, rcond=None)[0]       # (o - Pg)(Rg - I) = tl A
o = Pg + d
assert np.abs(((o - Pg) @ Rg + Pg - o) @ np.linalg.inv(A) - tl).max() < 1e-3
print('open pose: transpose', TRANSPOSE, 'centre', c1, 'err %.3f' % err)

# ---- which chamber is under the hand, and where one index step takes it
ch = [np.array(c) for c in face['chambers']]                         # closed positions (gun space)
op = [(c - Pg) @ Rg + Pg for c in ch]
feed = np.array(pts['feed'])
Fi = int(np.argmin([np.linalg.norm((p - feed)[1:]) for p in op]))
SGN = 1.0
Rs60 = R.axis_angle_rows((1, 0, 0), SGN * 60.0)
moved = (op[Fi] - c1) @ Rs60 + c1
nxt = int(np.argmin([np.linalg.norm((p - moved)[1:]) for p in op]))
step = (nxt - Fi) % 6
assert step in (1, 5), step
order = [(Fi + k * step) % 6 for k in range(1, 6)] + [Fi]            # chamber index of round 1..6
print('feed chamber', Fi, '-> after one step at', nxt, '| chamber of round 1..6:', order)

# ---- the loop clip with the index turn
n = a.numFrames
keyed = {nm: [list(a.V[f, c]) for f in range(n)] for c, nm in enumerate(a.names)}
for f in range(n):
    th = SGN * 12.0 * max(0, f - (n - 5))                            # frames n-4 .. n-1: 12, 24, 36, 48 deg
    Rs = R.axis_angle_rows((1, 0, 0), th)
    Rtot = Rg @ Rs
    o2 = ((o - Pg) @ Rg + Pg - c1) @ Rs + c1
    Rl2 = M @ Rtot @ M.T
    q = R.rows_to_quat(Rl2.T if TRANSPOSE else Rl2)
    if np.dot(q, a.V[0, cr]) < 0:
        q = -np.asarray(q)
    t2 = (o2 - o) @ np.linalg.inv(A)
    keyed['coop_cyl rot'][f] = [float(x) for x in q]
    keyed['coop_cyl pos'][f] = [float(t2[0]), float(t2[1]), float(t2[2]), 0.0]
gunskc.write(LOOP, raw, n, keyed, frame_time=1.0 / 30.0)
b = R.load(LOOP)
print('loop clip', b.numFrames, 'frames; frame 0 unchanged', bool(np.abs(b.V[0] - a.V[0]).max() < 1e-4))

# ---- the six head surfaces
data = open(F.SKD, 'rb').read()
m = F.SK.read_skd(data)
if any(s.name == 'coop_round1' for s in m.surfaces):
    print('round surfaces already in the skd')
else:
    names = [bn.name for bn in m.bones]
    bi = names.index('coop_cyl')
    t = F.G.parse_tik(F.TIK)
    sc = t['scale']
    skc = F.SK.read_skc(F.PR.vfs.read(F.G._res(t, t['anims']['idle'])))
    mats, _ = F.G.bone_world(m, skc, 0)
    cy, cz = pts['c_closed'][1], pts['c_closed'][2]
    x0 = pts['rear_x']
    for rnd, k in enumerate(order, 1):
        ang = 2 * math.pi * k / F.N_CH
        v, tr = F.disc((cy + F.RING * rad * math.cos(ang), cz + F.RING * rad * math.sin(ang)), rad * F.R_CH * 1.12, x0 - 0.05, 10)
        data = F.append_surface(data, 'coop_round%d' % rnd, v, tr, bi, mats[bi], sc)
    open(F.SKD, 'wb').write(data)
    print('surfaces', [s.name for s in F.SK.read_skd(data).surfaces][-7:])

# ---- the tik
p = os.path.join(STAGE, 'models', 'weapons', 'm10_revolver.tik')
s = io.open(p, encoding='latin-1', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
if 'coop_round1' not in s:
    anc = '\tsurface coop_m10_heads shader coop_m10_heads' + nl
    assert s.count(anc) == 1
    add = ('\t// HZM coop [revolver chambers 2026-10-12] one head per chamber: the cgame draws coop_round<N> iff N <= rounds in the' + nl +
           '\t// gun (m10rounds.py); the all-six surface is kept in the mesh but never drawn (init: +nodraw)' + nl +
           ''.join('\tsurface coop_round%d shader coop_m10_heads%s' % (k, nl) for k in range(1, 7)))
    s = s.replace(anc, anc + add)
    # a surface FLAG is an init command (in `setup` only `surface <name> shader <shader>` is read - run pa3 drew it)
    mi = re.search(r'(?m)^init\r?\n\{\r?\n[ \t]*server\r?\n[ \t]*\{\r?\n', s)
    assert mi
    s = s[:mi.end()] + '\t\tsurface coop_m10_heads +nodraw\t// HZM coop [revolver chambers] replaced by coop_round1..6' + nl + s[mi.end():]
s2 = re.sub(r'[ \t]*(?:\d+|first)[ \t]+surface coop_m10_heads [+-]nodraw[^\r\n]*\r?\n', '', s)
print('tik: frame commands on coop_m10_heads removed:', (len(s) - len(s2)) > 0)
dp = 0
for ln in s2.replace('\r', '').split('\n'):
    c = ln.split('//')[0]
    dp += c.count('{') - c.count('}')
    assert dp >= 0
assert dp == 0
io.open(p, 'w', encoding='latin-1', newline='').write(s2)
