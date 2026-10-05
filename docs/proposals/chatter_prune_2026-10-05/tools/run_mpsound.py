"""run_mpsound.py - ONE in-engine A/B check for "bot sounds are heard map-wide in MP" (queue slot "voicefix").

Listen server on dm/mohdm1, Team Match (g_gametype 2, the mod's MP framework via global/ambient.scr -> mp.scr), 3 bots,
DISPLAY2 harness G:\\mohaa-voicefix (live exe + the voicefix-tree game.dll/cgame.dll, fresh home, no qkey).
Phase A: cg_hzmForeignLocal 0 (retail: every CHAN_LOCAL sound on another client plays 2D, full volume, any distance).
Phase B: cg_hzmForeignLocal 1 (the fix). cg_hzmForeignLocalDebug 1 logs one ^~^~^ FLOCAL line per CHAN_LOCAL sound
with the decision and the distance from our ear to the emitting entity; s_show_sounds 1 logs 2D/3D starts.
"""
import os, re, sys, time, shutil, collections
IS = r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools"
sys.path.insert(0, IS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_voicefix as V      # noqa: E402  (configures R for G:\mohaa-voicefix)
R = V.R
hw = R.hw
CG = r"C:\mohaa-coop-dev\openmohaa-hzm-voicefix\.cmake\code\client\cgame\Release\cgame.dll"
SESS = sys.argv[2] if len(sys.argv) > 2 else "mp1"
PHASE = 150


def launch():
    boot = ["bind F12 \"exec isstep.cfg\"", "set ui_gmbox 0", "set com_maxfps 60", "set coop_dev 1",
            "set cg_hzmForeignLocalDebug 1", "set s_show_sounds 1", "set ui_hud 1"]
    sets = [("com_target_game", "2"), ("fs_basepath", R.GOG), ("fs_homepath", R.HOME), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", "1280"), ("r_customheight", "720"), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2"), ("net_ip", "127.0.0.1"), ("net_port", str(R.PORT)),
            ("g_gametype", "2"), ("sv_maxclients", "8"), ("sv_maxbots", "3"), ("sv_numbots", "3")]
    args = [R.EXE]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+exec", "is_on.cfg", "+map", "dm/mohdm1"]
    args, late = hw.apply_policy(args, width=1280, height=720)
    with open(os.path.join(R.MAINTT, "is_on.cfg"), "w", newline="\n") as f:
        f.write("\n".join(boot + late) + "\n")
    R.hg.acquire_slot(R.OWNER, R.EXE, R.HOME, [R.PORT], 40)
    c = hw.launch_background(args[0], args[1:], R.CLIENT, policy=False, log=R.log)
    R.CL["c"], R.CL["proc"] = c, c.proc
    return c


def run():
    V.log("mpsound: waiting for slot ==", V.QNAME)
    while open(V.SLOT).read().strip() != V.QNAME:
        time.sleep(5)
    t0 = time.time()
    gdll = os.path.join(R.CLIENT, "game.dll")
    live = os.path.join(R.CLIENT, "games", "game_live.dll")
    rundir = os.path.join(R.RUNS, SESS)
    try:
        shutil.copyfile(V.GAMEDLL, gdll)
        os.makedirs(os.path.join(R.CLIENT, "cgames"), exist_ok=True)
        shutil.copyfile(CG, os.path.join(R.CLIENT, "cgames", "cgame_flocal.dll"))
        if os.path.isdir(rundir):
            shutil.rmtree(rundir)
        os.makedirs(rundir)
        R.seed_home("cgame_flocal", V.OVERLAY)
        launch()
        if not R.wait_log(r"MP init|has joined|Detected", 420):
            V.log("map never came up")
        time.sleep(10)
        for k in range(4):
            R.step(["popmenu 0", "wait 10", "primarydmweapon smg", "wait 5", "join_team allies", "wait 40",
                    "popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 200"], timeout=60)
            if R.wait_log(r"has joined the Allies|joined the allies", 10):
                break
        R.step(["dog 1", "wait 100", "echo ^~^~^ MPPHASE A_retail", "set cg_hzmForeignLocal 0"], timeout=60)
        time.sleep(PHASE)
        R.step(["echo ^~^~^ MPPHASE B_fix", "set cg_hzmForeignLocal 1"], timeout=60)
        time.sleep(PHASE)
        R.step(["echo ^~^~^ MPPHASE end"], timeout=60)
    except Exception as e:
        import traceback
        V.log("FAILED", repr(e), traceback.format_exc())
    finally:
        try:
            if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                with open(os.path.join(R.MAINTT, "isstep.cfg"), "w", newline="\n") as f:
                    f.write("quit\n")
                R.CL["c"].post_key(0x7B)
                R.CL["proc"].wait(40)
        except Exception:
            try:
                R.CL["proc"].kill()
            except Exception:
                pass
        try:
            if R.CL["c"] is not None:
                R.CL["c"].close()
        except Exception:
            pass
        if os.path.exists(R.LOG):
            shutil.copyfile(R.LOG, os.path.join(rundir, "qconsole.log"))
        time.sleep(2)
        shutil.copyfile(live, gdll)
        try:
            R.hg.release_slot(R.OWNER)
        except Exception:
            pass
        open(V.SLOT, "w").write("free")
        V.log("mpsound: slot released (free) after %.1f min" % ((time.time() - t0) / 60))


def analyze():
    L = open(os.path.join(R.RUNS, SESS, "qconsole.log"), "rb").read().decode("latin-1").splitlines()
    phase = ""
    stat = collections.Counter()
    ex = {}
    for ln in L:
        m = re.search(r"\^~\^~\^ MPPHASE (\S+)", ln)
        if m:
            phase = m.group(1)
            continue
        m = re.search(r"\^~\^~\^ FLOCAL (\S+) ent=(\d+) me=(\d+) dist=(-?[\d.]+) min=\S+ max=(\S+) name=(\S+)", ln)
        if m and phase:
            act, ent, me, dist, mx, name = m.groups()
            foreign = ent != me and int(ent) < 64
            key = (phase, "foreign" if foreign else "own/world", act, re.sub(r".*/", "", name)[:40])
            stat[key] += 1
            ex.setdefault(key, "dist=%s max=%s" % (dist, mx))
    out = ["%-9s %-9s %-12s %-40s n=%-4d e.g. %s" % (k + (v, ex[k])) for k, v in sorted(stat.items())]
    txt = "\n".join(out)
    print(txt)
    open(os.path.join(os.path.dirname(V.OVERLAY), "analysis_mpsound.txt"), "w").write(txt)


if __name__ == "__main__":
    {"run": run, "analyze": analyze}[sys.argv[1]]()
