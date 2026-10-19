"""asn_scan.py <label:map> ... - ONE harness turn: boot each map, run the engine-side roof scan (asn_drv.scr::asd_scan) over the BSP bounds,
save the ^~^~^ RF lines to rf/<map>.txt. Offline filters + ranking: docs/tools/gen_sniper_spots.py merge-rf."""
import os, re, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asnlib as C
sys.path.insert(0, "C:/mohaa-coop-dev/docs/tools")
import bsptrace as T
G = C.G; R = C.R
TURN = "C:/mohaa-coop-dev/docs/tools/harness_turn.py"
os.makedirs(os.path.join(C.HERE, "rf"), exist_ok=True)
subprocess.run([sys.executable, TURN, "wait", "alarmsnipers"], check=True)
T0 = time.time()
try:
    for a in sys.argv[1:]:
        if time.time() - T0 > 11 * 60 and a != sys.argv[1]:
            print("budget used, skipping", a); continue
        lab, mp = a.split(":")
        rundir = notes = None
        try:
            B = T.BSP.load(mp)
            mn, mx = B.model_bounds(0)
            anc = [T.vec(e["origin"]) for e in B.entities() if e.get("classname") in ("info_pathnode", "info_player_start", "info_waypoint") and T.vec(e.get("origin", ""))]
            zmin = min(a_[2] for a_ in anc) + 128
            for attempt in range(4):
                try:
                    own = C.configure_slot()
                    if own is None:
                        time.sleep(30); raise RuntimeError("no free folder")
                    rundir, notes = G.boot("asn_" + lab, mp, extra=["set coop_alarm 0"])
                    break
                except Exception as e:
                    print("boot attempt", attempt, repr(e)[:120])
                    try: G.end(rundir, notes)
                    except Exception: pass
                    rundir = notes = None
            if rundir is None:
                continue
            p0 = len(R.read_log())
            G.cmd("scan", x0=int(mn[0]), y0=int(mn[1]), x1=int(mx[0]), y1=int(mx[1]), ztop=int(mx[2]) + 16, zbot=int(mn[2]), zmin=int(zmin), step=64)
            t = time.time()
            while time.time() - t < 420:
                txt = R.read_log()[p0:]
                if "RF DONE" in txt:
                    break
                time.sleep(5)
            txt = R.read_log()[p0:]
            lines = re.findall(r"\^~\^~\^ RF [^\r\n]*", txt)
            open(os.path.join(C.HERE, "rf", mp + ".txt"), "w").write("\n".join(lines) + "\n")
            print(mp, len(lines), "RF lines;", lines[-1] if lines else "none")
        except Exception as e:
            import traceback; print("FAILED", mp, repr(e), traceback.format_exc()[-400:])
        finally:
            G.end(rundir, notes)
finally:
    subprocess.run([sys.executable, TURN, "release", "alarmsnipers"])
