"""g1lib.py - shared harness glue for the game1 agent (bug-3560 prone, bug-3562 .30 cal).
Private harness G:/mohaa-hudfeed5, DISPLAY2, slot owner hudfeed5, port 12781."""
import os, re, sys, time, zipfile, shutil, math
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod"
BUILD = "C:/mohaa-coop-dev/openmohaa-hzm-game1/.cmake"
R.OWNER = "hudfeed5"
R.CLIENT = "G:/mohaa-hudfeed5"
R.EXE = os.path.join(R.CLIENT, "openmohaa_integ.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-hudfeed5/runs"
R.PORT = 12781
LOGF = os.path.join(HERE, "g1.log")


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def install(game, cgame):
    """game: 'integ' (baseline, games/game_integ.dll) or 'new' (the game1 worktree build). Returns the cgame name
    to hand to boot_session (a file in cgames/)."""
    if game == "new":
        shutil.copyfile(os.path.join(BUILD, "code/server/fgame/Release/game.dll"), os.path.join(R.CLIENT, "games", "game_game1.dll"))
        g = "games/game_game1.dll"
    else:
        g = "games/game_%s.dll" % game
    shutil.copyfile(os.path.join(R.CLIENT, g), os.path.join(R.CLIENT, "game.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "renderers/gl2_integ.dll"), os.path.join(R.CLIENT, "renderer_opengl2.dll"))
    if cgame == "new":
        shutil.copyfile(os.path.join(BUILD, "code/client/cgame/Release/cgame.dll"), os.path.join(R.CLIENT, "cgames", "cgame_game1.dll"))
        return "cgame_game1"
    return "cgame_" + cgame


def restore_ship():
    for f, d in (("games/game_ship.dll", "game.dll"), ("renderers/gl2_ship.dll", "renderer_opengl2.dll"),
                 ("cgames/cgame_ship.dll", "cgame.dll")):
        shutil.copyfile(os.path.join(R.CLIENT, f), os.path.join(R.CLIENT, d))


def overlay(name, driver, extra=()):
    ov = os.path.join(HERE, name)
    with zipfile.ZipFile(ov, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(HERE, driver), "coop_mod/coop_selftest_xp.scr")
        for rel in extra:
            if isinstance(rel, tuple):
                z.write(rel[0], rel[1])
            else:
                z.write(os.path.join(MOD, rel), rel)
    return ov


def cmd(what, timeout=60, **kv):
    """run a driver command; returns the log offset it started at"""
    p0 = len(R.read_log())
    lines = ["set g1_%s %s" % (k, v) for k, v in kv.items()] + ["set g1_cmd %s" % what]
    R.step(lines, timeout=30)
    if not R.wait_log(r"\^~\^~\^ G1 did %s" % what, timeout, p0):
        raise RuntimeError("driver never did %s" % what)
    return p0


def state(tag, pl=1):
    p0 = cmd("st", tag=tag, pl=pl)
    time.sleep(0.2)
    m = re.search(r"\^~\^~\^ G1 ST %s pl=\d+ pos=(\w+) mov=(\w+) org=\(([^)]*)\) ang=\(([^)]*)\) hp=([-\d.]+)" % re.escape(tag),
                  R.read_log()[p0:])
    if not m:
        return None
    return {"pos": m.group(1), "mov": m.group(2), "org": [float(x) for x in m.group(3).split()],
            "ang": [float(x) for x in m.group(4).split()], "hp": float(m.group(5))}


def tp(x, y, z, yaw, pl=1):
    cmd("tp", x="%.1f" % x, y="%.1f" % y, z="%.1f" % z, yaw="%.1f" % yaw, pl=pl)
    time.sleep(0.8)


def scan(tag, cx, cy, ztop, n=41, s=64):
    p0 = cmd("scan", timeout=120, tag=tag, x="%.1f" % cx, y="%.1f" % cy, z="%.1f" % ztop, n=n, s=s)
    time.sleep(0.3)
    rows = {}
    for m in re.finditer(r"\^~\^~\^ G1 ROW %s (\d+)((?: -?\d+)+)" % re.escape(tag), R.read_log()[p0:]):
        rows[int(m.group(1))] = [int(v) for v in m.group(2).split()]
    wrows = {}
    for m in re.finditer(r"\^~\^~\^ G1 WROW %s (\d+)((?: (?:-?\d+|x))+)" % re.escape(tag), R.read_log()[p0:]):
        wrows[int(m.group(1))] = m.group(2).split()
    grid, water = {}, {}
    for i, vals in rows.items():
        for j, zv in enumerate(vals):
            k = (cx + (i - n * 0.5) * s, cy + (j - n * 0.5) * s)
            grid[k] = zv
            wv = wrows.get(i, [])
            if j < len(wv) and wv[j] != "x" and int(wv[j]) > zv:
                water[k] = int(wv[j]) - zv
    return grid, water


def slopes(grid, s):
    """per interior grid point: (angle deg, downhill yaw deg, local roughness) from central differences"""
    out = {}
    for (x, y), z in grid.items():
        nb = [grid.get((x + s, y)), grid.get((x - s, y)), grid.get((x, y + s)), grid.get((x, y - s))]
        if None in nb:
            continue
        gx = (nb[0] - nb[1]) / (2.0 * s)
        gy = (nb[2] - nb[3]) / (2.0 * s)
        g = math.hypot(gx, gy)
        ang = math.degrees(math.atan(g))
        down = math.degrees(math.atan2(-gy, -gx)) if g > 1e-6 else 0.0
        # roughness: how far the centre is from the plane through the neighbours (a wall or a step shows as large)
        rough = max(abs(z - (nb[0] + nb[1]) * 0.5), abs(z - (nb[2] + nb[3]) * 0.5))
        out[(x, y)] = (ang, down, rough, z)
    return out
