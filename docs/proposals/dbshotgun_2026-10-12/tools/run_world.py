"""World behaviour + server timing of the double barrel on the private harness copy (G:\\mohaa-hudfeed4, port 12761).
run_dbs.py is the library; the overlay must be built with `mkov_dbs.py <pk3> --armory --world --tree`.

    python tools/run_world.py <session> --overlay <abs pk3> --cgame cgame_dbs8 --parts world2[,time] --set "set ui_hud 1"

  world2  the server-script driver tools/dbs_world.scr: death drop seen, touch pickup by a player without the gun,
          shells by touch both ways, an AI armed through the mod's path and killed by a bullet hit, the Use prompt
          (tap = the gun, hold = its shells), both barrels / reload / switch right after the pickup.
          This part answers the driver's "^~^~^ DBSW <seq> <kind> <arg>" lines; ONE engine screenshot per `shot`.
  time    server timing (fixedtime 16): torso state + shell pool whenever they change (`^~^~^ DBST`), coop_fireDebug's
          SHOOT lines, for --tguns (default: the double barrel and the pump gun), from the hip and aimed:
          one barrel + reload, emptied + reload, a reload broken off by the trigger.
Facts -> <run>/world2.json, <run>/time.json.
"""
import os, sys, re, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_dbs as D
R = D.R
shot = D.shot
FIRE = ["+attackprimary", "wait 60", "-attackprimary"]
RX = re.compile(r"\^~\^~\^ DBSW (\d+) (\w+) ?([^\r\n]*)")


def part_world2(a):
    out = {"stats": {}, "marks": [], "lines": []}
    R.step(D.RELEASE + R.give("none") + ["set cg_fov 90", "set cg_drawviewmodel 2", "set coop_lockLoadout 0", "set coop_dbsAck 0", "wait 800"], timeout=60)
    t0 = len(R.read_log())
    R.step(["set coop_dbsW %s" % a.wmode, "wait 200"], timeout=30)      # 1 = everything, 2 = from the AI part on
    pos, done, t_end = t0, False, time.time() + 900
    while not done and time.time() < t_end:
        R.guard()
        lg = R.read_log()
        m = RX.search(lg, pos)
        if not m:
            if re.search(r"\^~\^~\^ DBSW (end|abort)", lg[pos:]):
                done = True
            time.sleep(0.3)
            continue
        pos = m.end()
        seq, kind, arg = int(m.group(1)), m.group(2), m.group(3).strip()
        out["marks"].append([seq, kind, arg])
        R.log("[world2] %d %s %s" % (seq, kind, arg))
        if kind == "shot":
            shot(arg)
        elif kind == "die":
            ok, hits = D._respawn("death " + arg)
            out["death_" + arg] = {"respawned": ok, "log": hits[-8:]}
        elif kind == "fwd":
            R.step(["+forward", "wait %d" % int(arg), "-forward", "wait 300"], timeout=60)
        elif kind == "use":
            R.step(["+use", "wait %d" % int(arg), "-use", "wait 200"], timeout=60)
        elif kind == "fire":
            L = []
            for k in range(int(arg)):
                L += FIRE + ["wait 420"]
            R.step(L, timeout=60)
        elif kind == "cmd":
            R.step({"reload": ["reload", "wait 100"], "rt1": ["set coop_fireDebug 1", "set coop_rtOn 1", "wait 100"],
                    "rt0": ["set coop_rtOn 0", "set coop_fireDebug 0", "wait 100"]}[arg], timeout=30)
        R.step(["set coop_dbsAck %d" % seq, "wait 50"], timeout=30)
    lg = R.read_log()[t0:]
    for l in lg.splitlines():
        if "echo" in l:
            continue
        m = re.search(r"\^~\^~\^ DBSW stat (\S+) (.*)", l)
        if m:
            out["stats"][m.group(1)] = dict(kv.split("=", 1) for kv in m.group(2).split(" ") if "=" in kv)
        elif re.search(r"DBSW (spot|deathdrop|ai|abort|end)|DEATHDROP|cannot be picked up|\^~\^~\^ LOOT|Picked Up|Got \d+ .* Rounds|HELDREG|Script Error|DBST|FIREDBG SHOOT", l):
            out["lines"].append(l.strip()[-200:])
    out["finished"] = bool(re.search(r"\^~\^~\^ DBSW end", lg))
    out["script_errors"] = len(re.findall(r"Script Error", R.read_log()))
    json.dump(out, open(os.path.join(R.RUNS, a.session, "world2.json"), "w"), indent=1, default=str)
    R.log("[world2] finished=%s stats=%d script errors=%d" % (out["finished"], len(out["stats"]), out["script_errors"]))


def _seg(tag, lines, wait_after):
    return (["echo ^~^~^ DBST begin %s" % tag, "set coop_rtOn 1", "wait 300"] + lines + ["wait %d" % wait_after,
            "set coop_rtOn 0", "wait 200", "echo ^~^~^ DBST end %s" % tag])


def part_time(a):
    """fixedtime 16; a fresh gun for every segment (full clip); the pool is set to 30 so every shell counted shows"""
    R.step(D.RELEASE + ["set coop_lockLoadout 0", "set coop_isFixed 16", "set coop_fireDebug 1", "set cg_drawviewmodel 2", "wait 400"], timeout=60)
    for gun in a.tguns:
        tik = "models/weapons/%s.tik" % gun
        clip = 2 if "dbshotgun" in gun else 5
        for mode in ("hip", "ads"):
            aim = ["+button13", "wait 1900"] if mode == "ads" else ["wait 500"]
            segs = [("one_shot_reload", FIRE + ["wait 1600", "echo ^~^~^ DBST cmd reload", "reload"], 6500 if clip == 2 else 5000),
                    ("emptied_reload", sum([FIRE + ["wait %d" % (450 if clip == 2 else 1500)] for k in range(clip)], []) + ["echo ^~^~^ DBST cmd lastshot", "reload"], 7000 if clip == 2 else 9000),
                    ("reload_broken_off", FIRE + ["wait 1600", "echo ^~^~^ DBST cmd reload", "reload", "wait 1100", "echo ^~^~^ DBST cmd trigger"] + FIRE, 4500)]
            if clip == 2:
                segs.insert(0, ("two_barrels", FIRE + ["wait 150"] + FIRE + ["wait 150"] + FIRE, 3000))
            for nm, lines, after in segs:
                tag = "%s.%s.%s" % (gun, mode, nm)
                R.log("[time] " + tag)
                R.step(D.RELEASE + R.give(tik) + ["wait 4200"], timeout=90)
                R.step(aim + _seg(tag, lines, after) + D.RELEASE + ["wait 500"], timeout=120)
    R.step(["set coop_isFixed 0", "set coop_fireDebug 0", "wait 300"], timeout=30)
    lg = R.read_log()
    segs, cur = {}, None
    for l in lg.splitlines():
        m = re.search(r"\^~\^~\^ DBST (begin|end|cmd) (\S+)", l)
        if m and "echo ^" not in l:
            if m.group(1) == "begin":
                cur = segs.setdefault(m.group(2), [])
            elif m.group(1) == "end":
                cur = None
            elif cur is not None:
                cur.append(["cmd", m.group(2)])
            continue
        if cur is None:
            continue
        m = re.search(r"\^~\^~\^ DBST t=([\d.]+) st=(\S*) am=(-?\d+)", l)
        if m:                                   # one line per server frame: kept when the state or the pool changed
            tnow = float(m.group(1))
            prev = [e for e in cur if e[0] == "st"]
            if not prev or prev[-1][2] != m.group(2) or prev[-1][3] != int(m.group(3)):
                cur.append(["st", tnow, m.group(2), int(m.group(3))])
            cur.append(["t", tnow]) if not cur or cur[-1][0] != "t" else cur.__setitem__(-1, ["t", tnow])
        elif "FIREDBG SHOOT" in l:
            tl = [e for e in cur if e[0] in ("t", "st")]
            cur.append(["shoot", tl[-1][1] if tl else None])
        elif "FIREDBG TORSO" in l:
            cur.append(["torso", l.split("FIREDBG TORSO")[1].strip()])
    json.dump(segs, open(os.path.join(R.RUNS, a.session, "time.json"), "w"), indent=1)
    R.log("[time] %d segments" % len(segs))


HEAVY = ["set coop_loNP0 1", "set coop_loP1 0", "set coop_loP2 0", "set coop_loP3 1", "set coop_loP4 0", "set coop_loP5 0", "append name ,w0t3", "exec ui/loadout/lktab3.cfg"]


def part_tiles(a):
    """the heavy tab of the armory with the master switch on, then off (the tile is the tab's last: no empty row)"""
    def menu():
        R.step(["exec ui/loadout/open.cfg", "wait 6000"], timeout=60)
        R.step(HEAVY + ["wait 2500", "exec ui/loadout/lktab3.cfg", "wait 800"], timeout=60)
    R.step(D.RELEASE + ["set coop_dbShotgun 1", "wait 500"], timeout=30)
    menu(); shot("tiles_1_heavy_tab_switch_on")
    R.step(["popmenu 0", "wait 800", "set coop_dbShotgun 0", "wait 800"], timeout=30)
    menu(); shot("tiles_2_heavy_tab_switch_off")
    R.step(["popmenu 0", "wait 800", "set coop_dbShotgun 1", "wait 800"], timeout=30)


import run_arm        # noqa: E402  (registers the third pass's parts arm / armq / world on the same runner)
D.PARTS['world2'] = part_world2
D.PARTS['time'] = part_time
D.PARTS['tiles'] = part_tiles

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--tguns", default="coop_dbshotgun,shotgun")
    ap.add_argument("--wmode", default="1")
    k, rest = ap.parse_known_args()
    sys.argv = [sys.argv[0]] + rest
    _run = D.run

    def run(a):
        a.tguns = k.tguns.split(",")
        a.wmode = k.wmode
        return _run(a)
    D.run = run
    D.main()
