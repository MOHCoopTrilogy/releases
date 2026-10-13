"""SERVER reload timing (the listen server of the private test install): for each gun, one reload with rounds left and
one of an emptied magazine, from the hip and (irons) aimed. No screenshots. The overlay must be made with
srvtime_ov.py (server script probe + the probe commands in the weapon tiks' `reload` row).

    python run_srvtime.py <session> --overlay <abs pk3> --cgame cgame_rifle7 --guns coop_g43_irons,g43 [--parts hip,hipempty,ads,adsempty]
Then:  python srvtime_report.py <session>
Log marks: `^~^~^ RT begin <gun> <part>` / `RT cmd reload` / `RT end`; server lines `RT tick t= reserve=`,
`RT weapon reload row ENTRY|LAST|EXIT t=`, and coop_fireDebug's `FIREDBG TORSO a -> b` / `FIREDBG SHOOT`.
"""
import os, sys, argparse, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_rifle as RR      # repoints the shared harness to G:\mohaa-adsanim2 (owner adsanim2, port 12558)
A, S, R = RR.A, RR.S, RR.R

SHOT = ["+attackprimary", "wait 90", "-attackprimary"]


def part(gun, name, shots, after):
    ads = name.startswith("ads")
    L = S.RELEASE + S.TO_STAND + ["wait 400"] + (["+button13", "wait 1900"] if ads else ["wait 700"])
    L += ["echo ^~^~^ RT begin %s %s" % (gun, name), "set coop_rtOn 1", "wait 300"]
    if shots == 1:
        L += SHOT + ["wait 1500", "echo ^~^~^ RT cmd reload", "reload", "wait %d" % after]
    else:
        for k in range(shots):
            L += SHOT + ["wait 450"]
        L += ["echo ^~^~^ RT cmd lastshot", "wait %d" % after]
    L += ["set coop_rtOn 0", "wait 200", "echo ^~^~^ RT end %s %s" % (gun, name)] + S.RELEASE + ["wait 500"]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--overlay", required=True); ap.add_argument("--cgame", default="cgame_rifle7")
    ap.add_argument("--guns", default="coop_g43_irons,g43"); ap.add_argument("--parts", default="hip,hipempty,ads,adsempty")
    ap.add_argument("--clip", type=int, default=10); ap.add_argument("--after", type=int, default=5500)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(A.LOGF), exist_ok=True)
    A.log("start", a.session, "srvtime")
    t0 = time.time()
    rundir, notes = S.boot_session(a.session, a.cgame, 1280, 720, ["set cg_drawviewmodel 2", "set coop_rtPoll 1", "set coop_fireDebug 1"], a.overlay)
    try:
        R.step(["set coop_isFixed 16", "set coop_fireDebug 1", "wait 300"], timeout=30)
        for gun in a.guns.split(","):
            tik = A.GUNS.get(gun, "models/weapons/%s.tik" % gun)
            for p in a.parts.split(","):
                A.log("[%s] srvtime %s %s" % (a.session, gun, p))
                # a fresh weapon for every part: full magazine, full reserve
                R.step(S.RELEASE + S.TO_STAND + S.give(tik), timeout=90)
                R.step(part(gun, p, a.clip if p.endswith("empty") else 1, a.after), timeout=300)
        R.step(["set coop_isFixed 0", "wait 300"], timeout=30)
    except Exception as e:
        A.log("FAILED", repr(e))
    finally:
        S.end_session(rundir, notes)
        try:
            if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                R.CL["proc"].kill()
        except Exception:
            pass
        A.log("run ended after %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
