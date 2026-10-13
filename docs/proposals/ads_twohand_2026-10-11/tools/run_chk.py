"""run_chk.py - the checks nobody ran (pistol lane, 2026-10-13 pm): one harness session, a PLAN of small captures.

    python run_chk.py <session> --overlay <pk3> --cgame cgame_adsnext14 --plan <item>,<item>,... [--set "cvar value;..."]

plan item = <gun>:<what>[:<arg>]      (gun = the weapon tik's stem)
  hipe:<clip>      HIP, fired empty (clip = rounds in the gun): the dry gun at the hip, then its own reload     tag <gun>__hipe
  hipl             HIP, two shots, reload with rounds left                                                    tag <gun>__hipl
  sprint | unaim | fire | switch [:<at>]   an AIMED reload (two shots first), the interruption `at` capture ticks
                   after `reload` (default 60 = 0.96 s): sprint forward / the aim button released / a trigger press /
                   next weapon; every 2nd tick captured                                                        tag <gun>__i<what>
  sprinte | unaime [:<clip>]   the same out of the EMPTIED aimed reload (clip = rounds to fire first)
  tp:<shots>       THIRD PERSON camera (cg_3rd_person 1): <shots> hip shots, the reload, every 2nd tick        tag <gun>__tp
  tpo:<shots>      the same with coop_vmRoundSurfaces 2 = the local gun driven as ANOTHER player's gun is     tag <gun>__tpo
  shot2:<gap>      aimed: a shot, a second trigger press <gap> ticks later (Welrod: inside the bolt cycle), 100 ticks  tag <gun>__shot2
  cyc:<n>          aimed: n shots 75 ticks apart, every tick captured for the first 40 of each (hand-cycled guns)   tag <gun>__cyc
A tick = one 16 ms game frame (coop_isFixed 16). Engine `screenshotJPEG` only, one per step line.
"""
import os, sys, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_2h as RH
A, S, R = RH.A, RH.S, RH.R


def cap(tag, n, i, every=2):
    L = []
    for k in range(n):
        if k % every == 0:
            L += ["screenshotJPEG %s__%04d" % (tag, i[0])]; i[0] += 1
        L += ["wait 1", "wait 1"]
    return L


def press(hold=4):
    return ["+attackprimary"] + ["wait 1", "wait 1"] * hold + ["-attackprimary"]


def item(sess, gun, what, arg):
    tag = "ab__%s__%s__%s__chk__after" % (sess, gun, what)
    i = [0]
    L = S.RELEASE + S.TO_STAND + A.MODE["after"] + ["wait 600", "set cg_adsSightDebug 2", "echo ^~^~^ ABSCEN begin %s" % tag]
    end = []
    if what in ("hipe", "hipl"):
        n = int(arg) if what == "hipe" else 2
        L += cap(tag, 8, i)
        for k in range(n):
            L += press() + ["echo ^~^~^ CHK fire %d" % i[0]] + cap(tag, 24, i, 2 if k >= n - 2 else 12)
        if what == "hipe":
            L += ["echo ^~^~^ CHK dry %d" % i[0]] + cap(tag, 200, i)        # the dry gun, then the reload it starts by itself
        else:
            L += cap(tag, 40, i, 8) + ["reload", "echo ^~^~^ CHK reload %d" % i[0]] + cap(tag, 190, i)
    elif what in ("sprint", "unaim", "fire", "fireh", "switch", "sprinte", "unaime"):
        hip = what == "fireh"                 # fireh = the trigger press out of a HIP reload
        emp = what.endswith("e") and what != "fire"
        kind = "fire" if hip else (what[:-1] if emp else what)
        at = 60 if emp or not arg else int(arg)
        L += ([] if hip else ["+button13"]) + ["wait 1"] * 110
        for k in range(int(arg) if emp else 2):
            L += press() + ["wait 1"] * 54
        if not emp:
            L += ["wait 1"] * 60 + ["reload"]
        L += ["echo ^~^~^ CHK reload %d" % i[0]] + cap(tag, at, i)
        act = dict(sprint=["+speed", "+forward"], unaim=["-button13"], fire=["+attackprimary"], switch=["weapnext"])[kind]
        L += act + ["echo ^~^~^ CHK intr %d" % i[0]] + cap(tag, 12, i)
        if kind == "fire":
            L += ["-attackprimary"]
        L += cap(tag, 150, i)
        end = ["-forward", "-speed", "-button13"] + {"sprint": ["+back", "wait 1300", "-back", "wait 400"], "switch": ["wait 1200", "weapprev", "wait 2500"]}.get(kind, [])
    elif what in ("tp", "tpo"):
        L += ["set cg_3rd_person 1"] + (["set coop_vmRoundSurfaces 2", "set coop_vmRoundOthers 2"] if what == "tpo" else ["set coop_vmRoundSurfaces 1"]) + ["wait 500"]
        L += cap(tag, 8, i)
        for k in range(int(arg)):
            L += press() + ["wait 1"] * 54
        L += ["reload", "echo ^~^~^ CHK reload %d" % i[0]] + cap(tag, 620, i, 4)
        end = ["set cg_3rd_person 0", "set coop_vmRoundSurfaces 1", "set coop_vmRoundOthers 1"]
    elif what == "shot2":
        L += ["+button13"] + ["wait 1"] * 110
        L += press() + ["echo ^~^~^ CHK fire %d" % i[0]] + cap(tag, int(arg), i, 1)
        L += press() + ["echo ^~^~^ CHK second %d" % i[0]] + cap(tag, 110, i, 1)
        end = ["-button13"]
    elif what == "cyc":
        L += ["+button13"] + ["wait 1"] * 110
        for k in range(int(arg)):
            L += press() + ["echo ^~^~^ CHK fire %d" % i[0]] + cap(tag, 40, i, 1) + cap(tag, 35, i, 7)
        end = ["-button13"]
    elif what == "still":                        # two hip frames, then two frames of the settled aim (texture before / after)
        L += cap(tag, 4, i, 2) + ["+button13"] + ["wait 1"] * 120 + cap(tag, 4, i, 2)
        end = ["-button13"]
    else:
        raise SystemExit("unknown plan item " + what)
    L += ["echo ^~^~^ ABSCEN end %s" % tag, "set cg_adsSightDebug 1"] + end + S.RELEASE
    R.step(L, timeout=1800)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session"); ap.add_argument("--overlay", required=True); ap.add_argument("--cgame", required=True)
    ap.add_argument("--plan", required=True); ap.add_argument("--set", default="")
    a = ap.parse_args()
    if os.path.isdir(os.path.join(R.RUNS, a.session)):
        sys.exit("run folder %s/%s exists - pick an unused id" % (R.RUNS, a.session))
    plan = [(p.split(":") + [""])[:3] for p in a.plan.split(",") if p]
    os.makedirs(os.path.dirname(A.LOGF), exist_ok=True)
    A.log("start", a.session, "chk")
    t0 = time.time()
    try:
        extra = ["set cg_drawviewmodel 2", "set cg_weaponBreath 1", "set cg_adsSway 0.1"] + [("set " + x.strip()) for x in a.set.split(";") if x.strip()]
        rundir, notes = S.boot_session(a.session, a.cgame, 1280, 720, extra, a.overlay)
        try:
            R.step(["set coop_isFixed 16", "wait 300"], timeout=30)
            for gun, what, arg in plan:
                A.GUNS.setdefault(gun, "models/weapons/%s.tik" % gun)
                A.log("[%s] chk %s %s %s" % (a.session, gun, what, arg))
                give = S.give(A.GUNS[gun])
                if what == "switch":
                    give = S.give(A.GUNS["colt45"]) + give
                R.step(S.RELEASE + S.TO_STAND + give, timeout=120)       # a fresh gun for every item: full clip, known state
                item(a.session, gun, what, arg)
            R.step(["set coop_isFixed 0", "wait 300"], timeout=30)
        finally:
            S.end_session(rundir, notes)
    except Exception as e:
        A.log("FAILED", repr(e))
    finally:
        try:
            if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                R.CL["proc"].kill()
        except Exception:
            pass
        A.log("run ended after %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
