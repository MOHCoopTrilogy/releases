"""ride_ingame.py <tag> [--samples N] [--gap ms] [--gif N] [--renderer dll] [--extglsl f]
Coop m3l1a (Omaha) landing-craft ride in the real engine: the player is locked in the craft, so this does not move a camera - it
takes timed B/A pairs (r_hzmWaterPreset 0 = retail water, 1 = the new water) of whatever the ride shows, with
r_hzmWaterDbg 2 logging every water-ish shader + the entity drawing it. Reuses ice_ingame's client/home/overlay setup."""
import os, sys, re, json, time, shutil, argparse
import ice_ingame as I
W = I.W
W.OWNER = "ice1025"

CAM3 = None

def run(tag, samples, gap, gif, post):
    os.makedirs(I.RUNS, exist_ok=True)
    sc0 = dict(map="m3l1a", kind="coop", type="water", path="static", eye=[0, 0, 0], tgt=[100, 0, 0])
    I.setup()
    for fn in os.listdir(W.SHOTS) if os.path.isdir(W.SHOTS) else []:
        os.remove(os.path.join(W.SHOTS, fn))
    os.makedirs(W.SHOTS, exist_ok=True)
    W.hg.acquire_slot(W.OWNER, W.EXE, W.HOME, [W.PORT], minutes=40)
    notes = {"map": "m3l1a", "samples": samples}
    hud = ["set coop_cineHud 5", "set r_hzmWater 1"]
    try:
        c, cmd, nplus = W.launch(sc0)
        if not W.wait_log(r"Detected Coop for", 600):
            raise RuntimeError("map never became ready")
        time.sleep(3)
        notes["joined"] = W.join(sc0)
        for k in range(samples):
            L = hud + (["set cg_3rd_person 1", "set cg_cameradist %s" % CAM3[0], "set cg_cameraheight %s" % CAM3[1], "set cg_camerasideoffset %s" % CAM3[2]] if CAM3 else []) + ["echo ^~^~^ RIDE %d" % k, "set r_hzmWaterDbg 6", "wait 25", "screenshot ride_%s_B_%03d" % (tag, k),
                       "set r_hzmWaterDbg 2", "wait 25", "screenshot ride_%s_A_%03d" % (tag, k)]
            W.step(L, timeout=90)
            time.sleep(gap / 1000.0)
        if gif:
            L = hud + ["set fixedtime 150", "wait 20"]
            for k in range(gif):
                L += ["set r_hzmWaterDbg 6", "wait 1", "screenshot gif_%s_B_%03d" % (tag, k), "set r_hzmWaterDbg 2", "wait 1", "screenshot gif_%s_A_%03d" % (tag, k)]
            L += ["set fixedtime 0", "wait 300"]
            W.step(L, timeout=600)
        if post:
            time.sleep(75)
        for cn in post:
            _, eye, tgt = I.VIEWS[cn]
            sc = dict(eye=eye, tgt=tgt, path="static")
            o, p, y = W.path(sc, 1)[0]
            start = len(W.read_log())
            W.step(W.place(o, p, y) + ["wait 1500", "coord"])
            m = re.findall(r"location: (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)", W.read_log()[start:])
            ok = bool(m) and max(abs(float(m[-1][i]) - o[i]) for i in range(3)) <= 14.0
            print("post cam %s landed=%s" % (cn, ok), flush=True)
            if not ok:
                continue
            for pv, lab in ((0, "B"), (1, "A")):
                W.step(hud + ["set r_hzmWaterDbg %d" % (6 if pv == 0 else 2), "wait 2500"] + hud + ["screenshot post_%s_%s_%s" % (tag, cn, lab)])
        notes["script_errors"] = len(re.findall(r"Script Error", W.read_log()))
    finally:
        proc = W.CLIENT_H["proc"]
        if proc is not None and proc.poll() is None:
            try:
                W.rcon("quit"); proc.wait(40)
            except Exception:
                pass
        cc = W.CLIENT_H["c"]
        if cc is not None:
            cc.close(); rep = cc.report()
            notes["window"] = {"clean": rep["clean"], "violations": rep["violations"]}
        W.CLIENT_H["c"] = W.CLIENT_H["proc"] = None
        out = os.path.join(I.RUNS, tag + "_m3l1a_ride")
        os.makedirs(out, exist_ok=True)
        if os.path.isdir(W.SHOTS):
            for fn in sorted(os.listdir(W.SHOTS)):
                shutil.move(os.path.join(W.SHOTS, fn), os.path.join(out, fn))
        if os.path.exists(W.LOG):
            shutil.copyfile(W.LOG, os.path.join(out, "qconsole.log"))
        json.dump(notes, open(os.path.join(out, "notes.json"), "w"), indent=1)
        W.hg.release_slot(W.OWNER)
        ov = os.path.join(W.MAINTT, W.OVERLAY)
        if os.path.exists(ov):
            os.remove(ov)
        print(json.dumps(notes))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tag"); ap.add_argument("--samples", type=int, default=24); ap.add_argument("--gap", type=int, default=2500)
    ap.add_argument("--gif", type=int, default=0); ap.add_argument("--renderer"); ap.add_argument("--extglsl"); ap.add_argument("--post", default=""); ap.add_argument("--cam3", default="")
    a = ap.parse_args()
    CAM3 = a.cam3.split(",") if a.cam3 else None
    I.RENDERER = a.renderer; I.EXTGLSL = a.extglsl
    run(a.tag, a.samples, a.gap, a.gif, [x for x in a.post.split(",") if x])
