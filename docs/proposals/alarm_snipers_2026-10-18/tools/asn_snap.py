"""asn_snap.py <label:map> ... - ONE harness turn: boot each map and run an in-engine point test over the candidates in coop_mod/asn_cands_test.scr
(from gen_sniper_spots.py cands / roofcands). ASNMODE=snap (default): asd_snap, vanilla candidates onto the engine floor -> snap/<map>.txt (^~^~^ SNAP lines).
ASNMODE=dpre: asd_dpre, roof-deck candidates whose roof really exists for the engine -> dpre/<map>.txt (^~^~^ DPRE i OK lines)."""
import os, re, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asnlib as C
G = C.G; R = C.R
MODE = os.environ.get("ASNMODE", "snap")
TAG = "SNAP" if MODE == "snap" else "DPRE"
SUB = "snap" if MODE == "snap" else "dpre"
TURN = "C:/mohaa-coop-dev/docs/tools/harness_turn.py"
os.makedirs(os.path.join(C.HERE, SUB), exist_ok=True)
LINE = re.compile(r"\^~\^~\^ " + TAG + r" [^\r\n]*")
subprocess.run([sys.executable, TURN, "wait", "alarmsnipers"], check=True)
T0 = time.time()
try:
    for a in sys.argv[1:]:
        if time.time() - T0 > 11 * 60 and a != sys.argv[1]:
            print("budget used, skipping", a); continue
        lab, mp = a.split(":")
        rundir = notes = None
        try:
            ceil = 0
            try:
                t = open(os.path.join(C.HERE, "rf", mp + ".txt")).read()
                m = re.search(r"RF CEIL (\S+)", t)
                if m and float(m.group(1)) < 90000:
                    ceil = float(m.group(1))
            except Exception:
                pass
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
            G.cmd(MODE, ceil=int(ceil))
            t = time.time()
            while time.time() - t < 240 and (TAG + " DONE") not in R.read_log()[p0:]:
                time.sleep(3)
            lines = LINE.findall(R.read_log()[p0:])
            open(os.path.join(C.HERE, SUB, mp + ".txt"), "w").write("\n".join(lines) + "\n")
            print(mp, len(lines), lines[0] if lines else "none", lines[-1] if lines else "", flush=True)
        except Exception as e:
            import traceback; print("FAILED", mp, repr(e), traceback.format_exc()[-400:])
        finally:
            G.end(rundir, notes)
finally:
    subprocess.run([sys.executable, TURN, "release", "alarmsnipers"])
