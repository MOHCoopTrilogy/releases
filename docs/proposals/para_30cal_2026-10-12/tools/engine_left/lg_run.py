"""lg_run.py <label> [phases] - the engine side of the left .30 cal, measured in one session on m3l2 (never an Omaha map).
phases (comma list, default all): rest,heat,empty,bad,dismount,third,ai,death,old
  rest      the unmanned gun settles on cooprestpitch (still)
  heat      a player holds the trigger: heat / lock-out / rounds per second read from the turret's getters (still)
  empty     the belt runs out: one feed line + one click per pull, no heat while held (still)
  bad       the same with an alias that does not exist: one PlaySound error per pull (the control for the click)
  dismount  looked up, then down, then off the gun: the pitch trace back to rest
  third     the mounted player in third person (still, report item 6)
  ai        an AI gunner fires at three riflemen: belt against the engine's own FIREDBG SHOOT lines; then 15 rounds to 0
  death     he is killed at the gun: pitch after, and a player's Use
  old       the same gun with none of the new keys (the control): rest, heat numbers, empty text
Results: <run folder>/result.json and lg.log. One screenshot per step."""
import json, os, re, sys, time
import lg_lib as G
R = G.R
LABEL = sys.argv[1]
PH = sys.argv[2].split(",") if len(sys.argv) > 2 else "rest,heat,empty,bad,dismount,third,ai,death,old".split(",")
HC = "1" if "hardcore" in PH else "0"          # the harness profile has Hardcore on; the feed line is not drawn there
MAP = "m3l2"
X, Y, Z, YAW = -3608.0, 2303.0, 80.0, 225.0          # the open, level, lit spot the ironsight harness uses
RES = {"label": LABEL, "phases": PH}
rundir = notes = None


def hold(ms, shot=None, at=None):
    """trigger held for ms; one optional screenshot at `at` ms"""
    seq = ["+attackprimary"]
    if shot:
        seq += ["wait %d" % at, "screenshotJPEG %s" % shot, "wait %d" % max(1, ms - at)]
    else:
        seq += ["wait %d" % ms]
    seq += ["-attackprimary", "wait 100"]
    R.step(seq, timeout=60 + ms // 1000)


def use():
    R.step(["+use", "wait 120", "-use", "wait 900"], timeout=30)
    p = G.cmd("pst")
    return G.since(p, r"LG PST[^\r\n]*")[-1]


def mount():
    G.cmd("behind")
    time.sleep(0.8)
    s = use()
    if "turret=none" in s:
        raise RuntimeError("did not mount: " + s)
    return s


def summarise(rows):
    """heat trace -> the numbers: time to cook, lock length, rounds per second, cool time"""
    out = {}
    if not rows:
        return out
    t0 = next((r["t"] for r in rows if r["heat"] > 0.5), None)
    tc = next((r["t"] for r in rows if r["oh"] == 1), None)
    out["heat_start"], out["cooked_at"] = t0, tc
    if t0 is not None and tc is not None:
        out["sec_to_cook"] = round(tc - t0, 2)
        a0 = next(r["ammo"] for r in rows if r["t"] >= t0)
        a1 = next(r["ammo"] for r in rows if r["t"] >= tc)
        out["rounds_to_cook"] = a0 - a1
        out["rounds_per_sec"] = round((a0 - a1) / max(0.01, tc - t0), 2)
        # the lock: ammo does not move after the cook-off until ...
        aft = [r for r in rows if r["t"] >= tc]
        res = next((r["t"] for r in aft if r["ammo"] < a1), None)
        out["fire_resumed_after"] = round(res - tc, 2) if res else None
        cold = next((r["t"] for r in aft if r["oh"] == 0), None)
        out["cold_after"] = round(cold - tc, 2) if cold else None
    out["heat_max"] = max(r["heat"] for r in rows)
    out["ammo_first"], out["ammo_last"] = rows[0]["ammo"], rows[-1]["ammo"]
    return out


def spawn_gun(tag):
    import math
    gx = X + math.cos(math.radians(YAW)) * 130
    gy = Y + math.sin(math.radians(YAW)) * 130
    p = G.cmd("gun", x=gx, y=gy, z=Z, yaw=YAW, tag=tag)
    G.log(LABEL, G.since(p, r"LG gun at[^\r\n]*")[-1])
    return p


def heat_run(key, belt):
    G.cmd("left", n=belt)
    G.log(LABEL, key, mount())
    p = len(R.read_log())
    hold(7000, "%s_%s_hot" % (LABEL, key) if key == "heat" else None, 3300)
    time.sleep(6.0)
    rows = G.poll(p)
    RES[key] = summarise(rows)
    RES[key + "_trace"] = [(r["t"], r["ammo"], round(r["heat"], 1), r["oh"]) for r in rows][::3]
    G.log(LABEL, key, json.dumps(RES[key]))


try:
    rundir, notes = G.boot("lg_" + LABEL, MAP, extra=["set coop_feedDebug 1", "set coop_hardcore " + HC])
    G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
    time.sleep(1.0)
    pp = G.cmd("purge", timeout=60)
    G.log(LABEL, G.since(pp, r"LG purge[^\r\n]*"))
    G.cmd("poll", n=1)
    R.step(["ui_hud 1", "wait 100"], timeout=20)

    if "old" in PH:
        # THE CONTROL first: no new key set. Rest = the retail butt drop; heat = the MG42's numbers.
        spawn_gun("old")
        p = len(R.read_log())
        time.sleep(4.0)
        rows = G.poll(p)
        RES["old_rest_pitch"] = [r["pitch"] for r in rows][::4]
        G.log(LABEL, "old rest pitch", RES["old_rest_pitch"][-1])
        G.cmd("cam", n=120, yaw=100, z=0)
        time.sleep(0.6)
        G.still(LABEL + "_old_rest")
        heat_run("old_heat", 300)
        G.cmd("belt", n=3)
        p = len(R.read_log())
        hold(3000)
        rows = G.poll(p)
        RES["old_empty"] = {"heat_max_on_empty_hold": max(r["heat"] for r in rows), "ammo": rows[-1]["ammo"],
                            "feed": G.since(p, r"FEED cat=\d key=mgbelt[^\r\n]*"),
                            "resupply_text_in_log": len(G.since(p, r"BELT EMPTY - resupply"))}
        G.log(LABEL, "old empty", json.dumps(RES["old_empty"]))
        time.sleep(5.0)
        G.log(LABEL, "old off:", use())

    if any(k in PH for k in ("rest", "heat", "empty", "dismount", "third", "ai", "death")):
        spawn_gun("new")
    if "rest" in PH:
        p = len(R.read_log())
        time.sleep(3.0)
        rows = G.poll(p)
        RES["rest_pitch"] = [r["pitch"] for r in rows][::3]
        G.log(LABEL, "rest pitch", RES["rest_pitch"])
        G.cmd("cam", n=120, yaw=100, z=0)
        time.sleep(0.6)
        G.still(LABEL + "_new_rest")
    if "heat" in PH:
        heat_run("heat", 250)
    elif any(k in PH for k in ("empty", "dismount", "third")):
        G.cmd("left", n=250)
        G.log(LABEL, mount())
    if "empty" in PH:
        G.cmd("belt", n=10)
        p = len(R.read_log())
        hold(4000, LABEL + "_empty", 2200)
        hold(1200)
        hold(1200)
        time.sleep(0.5)
        rows = G.poll(p)
        t = R.read_log()[p:]
        RES["empty"] = {"ammo": rows[-1]["ammo"], "heat_max_on_empty_hold": max(r["heat"] for r in rows[20:]) if len(rows) > 20 else None,
                        "feed_lines": re.findall(r"FEED cat=\d key=mgbelt[^\r\n]*", t),
                        "resupply_text": len(re.findall(r"BELT EMPTY - resupply", t)),
                        "alias_errors": re.findall(r"[^\r\n]*needs an alias[^\r\n]*", t)}
        G.log(LABEL, "empty", json.dumps(RES["empty"]))
    if "dismount" in PH:
        tr = {}
        for name, key in (("up", "+lookup"), ("down", "+lookdown")):
            if "turret=none" in G.since(G.cmd("pst"), r"LG PST[^\r\n]*")[-1]:
                mount()
            R.step([key, "wait 260", key.replace("+", "-"), "wait 300"], timeout=20)
            p = len(R.read_log())
            time.sleep(0.4)
            s = use()
            time.sleep(1.6)
            rows = G.poll(p)
            tr[name] = [(r["t"], r["pitch"]) for r in rows]
            G.log(LABEL, "dismount", name, s[-60:], [x[1] for x in tr[name]])
        RES["dismount"] = tr
    if "third" in PH:
        if "turret=none" in G.since(G.cmd("pst"), r"LG PST[^\r\n]*")[-1]:
            mount()
        R.step(["set cg_3rd_person 1", "wait 1500", "screenshotJPEG %s_third" % LABEL, "wait 200", "set cg_3rd_person 0",
                "wait 300"], timeout=30)
    if any(k in PH for k in ("heat", "empty", "dismount", "third")):
        if "turret=none" not in G.since(G.cmd("pst"), r"LG PST[^\r\n]*")[-1]:
            G.log(LABEL, "off:", use())

    if "bad" in PH:
        spawn_gun("bad")
        G.cmd("left", n=0)
        mount()
        p = len(R.read_log())
        hold(900)
        hold(900)
        hold(900)
        time.sleep(0.5)
        t = R.read_log()[p:]
        RES["bad"] = {"alias_errors": len(re.findall(r"lg_no_such_alias", t)), "feed_lines": len(re.findall(r"FEED cat=\d key=mgbelt", t)),
                      "sample": (re.findall(r"[^\r\n]*lg_no_such_alias[^\r\n]*", t) or [""])[0][-160:]}
        G.log(LABEL, "bad alias, three pulls:", json.dumps(RES["bad"]))
        use()

    if "ai" in PH or "death" in PH:
        spawn_gun("new")
        G.cmd("cam", n=170, yaw=125, z=0)
        G.cmd("foe", n=500)
        pa = G.cmd("ai")
        G.log(LABEL, G.since(pa, r"LG ai[^\r\n]*"))
    if "ai" in PH:
        R.step(["set coop_fireDebug 1", "wait 100"], timeout=20)
        p = len(R.read_log())
        time.sleep(1.0)
        p = len(R.read_log())
        time.sleep(24.0)
        t = R.read_log()[p:]
        rows = G.poll(p)
        shots = len(re.findall(r"FIREDBG SHOOT \.30 Cal", t))
        step = max((a["ammo"] - b["ammo"]) / max(0.01, b["t"] - a["t"]) for a, b in zip(rows, rows[5:]))
        RES["ai"] = {"sec": round(rows[-1]["t"] - rows[0]["t"], 1), "belt_first": rows[0]["ammo"], "belt_last": rows[-1]["ammo"],
                     "belt_used": rows[0]["ammo"] - rows[-1]["ammo"], "engine_shoot_lines": shots, "rounds_per_sec_in_a_burst": round(step, 1),
                     "heat_max": max(r["heat"] for r in rows), "cooked": sum(1 for a, b in zip(rows, rows[1:]) if b["oh"] and not a["oh"])}
        RES["ai_trace"] = [(r["t"], r["ammo"], round(r["heat"], 1), r["oh"]) for r in rows][::5]
        G.log(LABEL, "ai", json.dumps(RES["ai"]))
        G.still(LABEL + "_ai_fire")
        G.cmd("burst")
        G.cmd("belt", n=15)
        p = len(R.read_log())
        t0 = time.time()
        while time.time() - t0 < 40:
            rows = G.poll(p)
            if rows and rows[-1]["ammo"] == 0:
                break
            time.sleep(1.0)
        p2 = len(R.read_log())
        time.sleep(10.0)
        t = R.read_log()
        rows2 = G.poll(p2)
        RES["ai_empty"] = {"belt": rows2[-1]["ammo"], "shoot_lines_to_empty": len(re.findall(r"FIREDBG SHOOT \.30 Cal", t[p:p2])),
                           "shoot_lines_in_10s_after": len(re.findall(r"FIREDBG SHOOT \.30 Cal", t[p2:])),
                           "heat_10s_after": rows2[-1]["heat"]}
        G.log(LABEL, "ai empty", json.dumps(RES["ai_empty"]))
        R.step(["set coop_fireDebug 0", "wait 100"], timeout=20)
        G.cmd("belt", n=120)
        time.sleep(3.0)
    if "death" in PH:
        p = G.cmd("kill")
        time.sleep(1.0)
        G.cmd("left", n=-1)
        G.log(LABEL, G.since(p, r"LG left[^\r\n]*"))
        G.cmd("nofoe")
        time.sleep(7.0)
        rows = G.poll(p)
        RES["death_pitch"] = [(r["t"], r["pitch"]) for r in rows][::5]
        G.log(LABEL, "pitch after his death", [x[1] for x in RES["death_pitch"]])
        G.still(LABEL + "_death_rest")
        G.cmd("behind")
        time.sleep(0.8)
        s = use()
        RES["death_use"] = s
        G.log(LABEL, "Use after his death:", s)
        if "turret=none" not in s:
            p = len(R.read_log())
            hold(1500)
            rows = G.poll(p)
            RES["death_fire"] = {"ammo_first": rows[0]["ammo"], "ammo_last": rows[-1]["ammo"]}
            G.log(LABEL, "fired", json.dumps(RES["death_fire"]))
            use()
    RES["errors"] = G.errors()
    G.log(LABEL, "script / alias errors:", RES["errors"])
except Exception as e:
    import traceback
    RES["exception"] = repr(e)
    G.log(LABEL, "EXCEPTION", traceback.format_exc())
finally:
    if notes is not None:
        notes["result"] = RES
    if rundir:
        json.dump(RES, open(os.path.join(rundir, "result.json"), "w"), indent=1)
    G.end(rundir, notes)
    G.log(LABEL, "ended", rundir)
