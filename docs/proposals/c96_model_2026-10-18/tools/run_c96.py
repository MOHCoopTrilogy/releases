"""The heavy lane's measuring runner (ads_twohand_2026-10-11/heavy/tools/run_h.py: stance demos that boxeng.py can
measure, hip demos, break-offs, third-person close-ups) as a LIBRARY, repointed at OUR private copy:
G:\\mohaa-hudfeed2, slot owner "hudfeed2", net_port 12721. Its parts, flags and capture format are unchanged.

    python tools/run_dbsh.py <session> --overlay <abs pk3> --cgame cgame_dbs6 --guns dbs --parts stills \
        --stdemo stand,crouch,prone,standL,standR,braced --tail 360:4 --shots 1 --demoreload 150 --demoyaw 165
    (emptied gun: --shots 2 --demoempty)      --sthip = the same captures from the hip      --hipdemo L,E   --tpc
Frames: G:/mohaa-hudfeed2/runs/<session>/ ; measure with tools/box_dbs.py <session> dbs --sway [--empty]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
HEAVY = os.path.abspath(os.path.join(HERE, '..', '..', 'ads_twohand_2026-10-11', 'heavy', 'tools'))
sys.path.insert(0, HEAVY)
import run_h as RH                                   # noqa: E402   (import only: nothing is launched)

R, A, S, T2 = RH.R, RH.A, RH.S, RH.T2
HUD = os.environ.get("C96_HUD", "5")
PORTS = {"2": 12721, "4": 12761, "5": 12781}
CLIENT = r"G:\mohaa-hudfeed" + HUD
R.OWNER = "hudfeed" + HUD
R.CLIENT = CLIENT
R.EXE = os.path.join(CLIENT, "openmohaa_c96.exe")
R.HOME = os.path.join(CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(CLIENT, "pristine")
sys.path.insert(0, HERE)
R.RUNS = os.environ.get('C96_RUNS', r"C:/Users/curry/AppData/Local/Temp/claude/C--mohaa-coop-dev/0ef9c092-ae3c-4811-a8c8-d3c6c827d23b/scratchpad/c96runs")
os.makedirs(R.RUNS, exist_ok=True)
R.PORT = PORTS[HUD]
A.LOGF = os.path.join(HERE, '..', 'build', 'run_h.log')
for _f in ("", "_gold", "_chrome", "_blued", "_bloody", "_camo_woodland", "_camo_winter", "_camo_desert"):
    A.GUNS["c96" + _f] = "models/weapons/mauser_c96%s.tik" % _f
A.GUNS["colt45"] = "models/weapons/colt45.tik"


def take(opt, n=1):
    if opt not in sys.argv:
        return None
    k = sys.argv.index(opt)
    v = sys.argv[k + 1:k + 1 + n]
    del sys.argv[k:k + 1 + n]
    return v[0] if n == 1 else (v or True)


def flag(opt):
    if opt in sys.argv:
        sys.argv.remove(opt)
        return True
    return False


if __name__ == "__main__":
    assert R.CLIENT.lower().endswith("hudfeed" + HUD)
    for opt, lst in (("--stdemo", RH.STDEMO), ("--brk", RH.BRK), ("--hipdemo", RH.HIPDEMO), ("--wallstill", RH.WALLSTILL)):
        v = take(opt)
        if v:
            lst[:] = v.split(",")
    if flag("--sthip"):
        RH.STHIP.append(1)
    if flag("--tpc"):
        RH.TPC.append(1)
    if flag("--tprel"):
        RH.TPREL.append(1)
    if flag("--ground"):
        RH.GROUND.append(1)
    if flag("--hipstill"):
        RH.HIPSTILL.append(1)
    v = take("--hold")
    if v:
        RH.SMG_HOLD[0] = int(v)
    v = take("--rel")
    if v:
        RH.SMG_REL[0] = int(v)
    v = take("--tail")
    if v:
        t = v.split(":")
        RH.TAIL[:] = [int(t[0]), int(t[1]) if len(t) > 1 else 4]
    v = take("--map")
    if v:
        assert v not in ("m3l1a", "m3l1b", "e3l1", "e3l2", "obj_team3")
        R.MAP = v
    v = take("--spot")
    if v:
        R.SPOT = tuple(float(x) for x in v.split(","))
    v = take("--pitch")
    if v:
        _give, _p = R.give, float(v)
        R.give = lambda tik, pitch=0.0: _give(tik, _p if pitch == 0.0 else pitch)
    # our binaries (run_dbs.py's set): the engine DLLs of the copy's `integ` build
    import shutil
    shutil.copyfile(os.path.join(CLIENT, "games", "game_c96.dll"), os.path.join(CLIENT, "game.dll"))
    shutil.copyfile(os.path.join(CLIENT, "renderers", "gl2_c96.dll"), os.path.join(CLIENT, "renderer_opengl2.dll"))
    T2.main()
