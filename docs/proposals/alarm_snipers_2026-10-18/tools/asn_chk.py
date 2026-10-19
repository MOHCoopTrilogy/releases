"""asn_chk.py <label:map> ... - ONE harness turn: for each map spawn a sniper on EVERY kept spot at once, wait 3 s, judge each (drop, air under feet,
monsterclip floor above the solid floor, sky, roof edge within 24 u), then a side-on shot (300 u, level with the feet) of every survivor.
Writes spotcheck/<map>.json and media/spots/<map>_<i>.jpg."""
import os, re, sys, time, json, shutil, glob, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asnlib as C
G = C.G; R = C.R
TURN = "C:/mohaa-coop-dev/docs/tools/harness_turn.py"
MEDIA = os.path.join(os.path.dirname(C.HERE), "media", "spots")
subprocess.run([sys.executable, TURN, "wait", "alarmsnipers"], check=True)
T0 = time.time()
try:
    for a in sys.argv[1:]:
        if time.time() - T0 > 10.5 * 60 and a != sys.argv[1]:
            print("budget used, skipping", a); continue
        lab, mp = a.split(":")
        rundir = notes = None
        try:
            for attempt in range(4):
                try:
                    own = C.configure_slot()
                    if own is None:
                        time.sleep(30); raise RuntimeError("no free folder")
                    rundir, notes = G.boot("asn_" + lab, mp, extra=["set coop_alarm 1", "set coop_alarmDebug 1", "set cg_fov 70"])
                    break
                except Exception as e:
                    print("boot attempt", attempt, repr(e)[:120])
                    try: G.end(rundir, notes)
                    except Exception: pass
                    rundir = notes = None
            if rundir is None:
                continue
            p0 = len(R.read_log())
            for k in range(14 if mp in ("m1l1", "m4l3") else 3):
                G.cmd("autoplace")
                w = re.findall(r"ASN WHERE [^\r\n]*off=(\d+)", R.read_log()[p0:])
                if w and int(w[-1]) < 100:
                    break
                if re.findall(r"ASN PLACE none", R.read_log()[p0:]) and mp not in ("m1l1", "m4l3"):
                    break
                time.sleep(10)
            G.cmd("allspots")
            t = time.time()
            while time.time() - t < 90 and "SPOTCHK DONE" not in R.read_log()[p0:]:
                time.sleep(3)
            txt = R.read_log()[p0:]
            res = []
            for m in re.finditer(r"\^~\^~\^ SPOTCHK (\d+) \( ([-\d.]+) ([-\d.]+) ([-\d.]+) \) (.*)", txt):
                i = int(m.group(1)); rest = m.group(5).strip()
                verdict = "PASS" if rest.endswith("PASS") else rest[rest.find("FAIL"):] if "FAIL" in rest else rest
                res.append({"i": i, "pos": [float(m.group(2)), float(m.group(3)), float(m.group(4))], "line": rest, "verdict": verdict})
            json.dump(res, open(os.path.join(C.HERE, "spotcheck", mp + ".json"), "w"), indent=1)
            print(mp, len(res), "judged;", sum(1 for r in res if r["verdict"] == "PASS"), "pass", flush=True)
            from PIL import Image, ImageChops
            def grab(tag):
                G.still(tag)
                time.sleep(0.6)
                fs = sorted(glob.glob(os.path.join(R.SHOTS, tag + "*")), key=os.path.getmtime)
                return fs[-1] if fs else None
            for r in res:
                if r["verdict"] != "PASS":
                    continue
                r["photo"] = "none"
                for t in range(16):
                    q0 = len(R.read_log())
                    G.cmd("sidecam", k=r["i"], t=t, rad=300)
                    if re.search(r"SPOTCHK CAM no clear", R.read_log()[q0:]):
                        continue
                    time.sleep(0.9)
                    fa = grab("asc_%s_%d_a%d" % (mp, r["i"], t))
                    G.cmd("hidesn", k=r["i"])
                    time.sleep(0.5)
                    fb = grab("asc_%s_%d_b%d" % (mp, r["i"], t))
                    G.cmd("showsn", k=r["i"])
                    if not fa or not fb:
                        continue
                    ia, ib = Image.open(fa).convert("L").resize((640, 360)), Image.open(fb).convert("L").resize((640, 360))
                    df = ImageChops.difference(ia, ib).point(lambda v: 255 if v > 40 else 0)
                    bb = df.getbbox()
                    if bb and (bb[3] - bb[1]) >= 70 and (bb[2] - bb[0]) >= 20 and bb[1] > 8 and bb[3] < 352:   # whole body incl. feet inside the frame (640x360 scale)
                        shutil.copy(fa, os.path.join(MEDIA, "%s_%d.jpg" % (mp, r["i"])))
                        r["photo"] = "ok dir %d" % t
                        break
                print(mp, r["i"], r["photo"], flush=True)
                if r["photo"] == "none":
                    r["verdict"] = "FAIL no visible angle (floor contact not photographable)"
            json.dump(res, open(os.path.join(C.HERE, "spotcheck", mp + ".json"), "w"), indent=1)
            G.cmd("sidecam_off")
        except Exception as e:
            import traceback; print("FAILED", mp, repr(e), traceback.format_exc()[-500:])
        finally:
            G.end(rundir, notes)
            try:
                shutil.copy(R.LOG, os.path.join(C.HERE, "logs", "chk_%s.log" % mp))
            except Exception:
                pass
finally:
    subprocess.run([sys.executable, TURN, "release", "alarmsnipers"])
