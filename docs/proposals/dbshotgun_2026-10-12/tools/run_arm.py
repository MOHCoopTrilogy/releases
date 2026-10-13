"""Harness runs for the double barrel's OWN ARMORY ENTRY, unlock path and world behaviour (overlay built with
`mkov_dbs.py --armory`). run_dbs.py is used as a library; same private copy, port and rules.

    python tools/run_arm.py <session> --overlay <abs pk3> --cgame cgame_dbs8 --parts arm[,world] --set "set coop_lockLoadout 1"

  arm     locked tile + requirement text; a click while locked; an EXISTING unlock (the pump gun, through its own
          challenge) ; the requirement met through the mod's own chal_bump (what a kill calls) -> unlocked; the pick;
          spawn with it; a finish; a map RESTART; a map CHANGE; the Service Record page; coop_dbShotgun 0.
  world   the death drop on the ground and its touch pickup; an AI armed through aihandler.scr::coop_actorArm, killed:
          the Use prompt with the loot picture, the pickup; shells shared with the pump gun both ways.
One engine screenshot per step. Log facts land in <run>/arm.json / world.json.
"""
import os, sys, re, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_dbs as D
R = D.R
shot = D.shot
HEAVY = ["set coop_loNP0 1", "set coop_loP1 0", "set coop_loP2 0", "set coop_loP3 1", "set coop_loP4 0", "set coop_loP5 0", "append name ,w0t3", "exec ui/loadout/lktab3.cfg"]
SEQ = [100]


def loglines(t0, rx):
    return [l.strip()[-230:] for l in R.read_log()[t0:].splitlines() if re.search(rx, l) and "isstep" not in l and "echo" not in l]


def stat(tag, out):
    SEQ[0] += 1
    t = len(R.read_log())
    R.step(["set coop_dbsStat %d" % SEQ[0], "wait 2500"], timeout=60)
    ls = loglines(t, r"DBSSTAT %d|DBSUNLOCKS %d" % (SEQ[0], SEQ[0]))
    s = [l[l.index("DBSSTAT"):] for l in ls if "DBSSTAT" in l]
    u = [l[l.index("DBSUNLOCKS") + len("DBSUNLOCKS %d " % SEQ[0]):] for l in R.read_log()[t:].splitlines() if "DBSUNLOCKS %d" % SEQ[0] in l and "echo" not in l]
    out[tag] = {"stat": s[-1] if s else None, "unlocks": sorted(x for x in (u[-1].strip().split("|") if u else []) if x)}
    R.log("[arm] %s: %s  unlocks=%d" % (tag, out[tag]["stat"], len(out[tag]["unlocks"])))
    return out[tag]


def bump(stat_name, n, wait=6000):
    SEQ[0] += 1
    t = len(R.read_log())
    R.step(["set coop_dbsBumpStat %s" % stat_name, "set coop_dbsBumpN %d" % n, "set coop_dbsBump %d" % SEQ[0], "wait %d" % wait], timeout=90)
    return loglines(t, r"DBSBUMP|Script Error|unlock|UNLOCK")[-6:]


def menu_heavy():
    R.step(["exec ui/loadout/open.cfg", "wait 6000"], timeout=60)            # the server answers ,w0o with the lock cvars
    R.step(HEAVY + ["wait 2500", "exec ui/loadout/lktab3.cfg", "wait 800"], timeout=60)


def cvar(name):
    t = len(R.read_log())
    R.step([name, "wait 400"], timeout=30)
    ls = [l.strip()[-120:] for l in R.read_log()[t:].splitlines() if ('"%s"' % name) in l]
    return ls[-1] if ls else None


def newmap(mapname, tag, out, spawnwait=45):
    t = len(R.read_log())
    R.step(["set ui_dmmap %s" % mapname, "ui_startdmmap 2"], timeout=60)
    m = R.wait_log(r"Could not load[^\r\n]*|Detected Coop for", 600, t)
    time.sleep(8)
    joined = R.join()
    time.sleep(spawnwait)                 # the join replay of the archived picks is staggered over ~20 s
    ok = False
    for k in range(5):
        tc = len(R.read_log())
        R.step(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
        if R.wait_log(r"\^~\^~\^ KITGIVE", 15, tc):
            ok = True
            break
    time.sleep(10)
    R.step(["set cg_fov 90", "set cg_drawviewmodel 2", "dog 1", "wait 200", "notarget 1", "wait 1200"], timeout=60)
    out[tag] = {"map": m.group(0) if m else None, "joined": joined, "spawned": ok,
                "log": loglines(t, r"KITGIVE|cache models/weapons/coop_dbshotgun|is LOCKED|switched off|Script Error|not on list")[-8:]}
    R.log("[arm] %s: %s" % (tag, json.dumps(out[tag])[:600]))


def part_arm(a):
    out = {}
    R.step(D.RELEASE + ["set cg_fov 90", "set cg_drawviewmodel 2", "wait 500"], timeout=60)
    stat("1_fresh", out)
    menu_heavy()
    R.step(["exec ui/loadout/req80.cfg", "wait 600"], timeout=30); shot("arm_01_locked_tile_requirement")
    R.step(["exec ui/loadout/t80.cfg", "wait 4000"], timeout=60); shot("arm_02_click_while_locked")
    out["click_locked_coop_lo1"] = cvar("coop_lo1")
    R.step(["popmenu 0", "wait 800"], timeout=30)
    # an EXISTING record: the pump gun through its own challenge (12 Gestapo officers), a rank-free second entry
    out["bump_fac_ss"] = bump("fac_ss", 12)
    before = stat("2_record_before", out)
    # the requirement: 60 shotgun kills
    out["bump_59"] = bump("wpn_shotgun", 59)
    mid = stat("3_at_59_kills", out)
    out["bump_60"] = bump("wpn_shotgun", 1, wait=3500)
    shot("arm_03_unlock_notice")
    after = stat("4_at_60_kills", out)
    out["record_kept"] = sorted(set(before["unlocks"]) - set(after["unlocks"])) == []
    out["record_added"] = sorted(set(after["unlocks"]) - set(before["unlocks"]))
    menu_heavy(); shot("arm_04_unlocked_tile")
    R.step(["exec ui/loadout/t80.cfg", "wait 6000"], timeout=60); shot("arm_05_picked_slot_1")
    out["picked_coop_lo1"] = cvar("coop_lo1"); out["picked_coop_loS1"] = cvar("coop_loS1")
    stat("5_picked", out)
    R.step(["popmenu 0", "wait 800"], timeout=30)
    out["spawn1"] = D._respawn("spawn with the pick")
    R.step(["wait 2500"]); shot("arm_06_spawned_with_it")
    # a finish: WINTER (fid 6) - its own challenge (150 kills on snow maps), the gun's mastery = wpn_shotgun (done above)
    out["bump_winter"] = bump("kill_snow", 150)
    t = len(R.read_log())
    R.step(["append name ,f16", "wait 7000"], timeout=60)
    out["finish_log"] = loglines(t, r"equipped|LOCKED|Script Error|finish")[-4:]
    stat("6_finish_picked", out)
    out["spawn2"] = D._respawn("spawn with the finish")
    R.step(["wait 2500"]); shot("arm_07_finish_winter")
    out["coop_loS1F"] = cvar("coop_loS1F")
    # a map RESTART, then a map CHANGE: the pick and the finish must come back by themselves
    newmap(R.MAP, "restart", out)
    stat("7_after_restart", out); shot("arm_08_after_map_restart")
    newmap(a.map2, "change", out)
    stat("8_after_map_change", out); shot("arm_09_after_map_change")
    # the Service Record: SUPPORT WEAPONS, second page
    R.step(["pushmenu coop_sr", "wait 2500", "exec ui/coop_sr_pg%d.cfg" % a.srpage, "wait 2500"], timeout=60); shot("arm_10_service_record")
    R.step(["popmenu 0", "wait 800"], timeout=30)
    # the master switch
    R.step(["set coop_dbShotgun 0", "wait 500"], timeout=30)
    menu_heavy(); shot("arm_11_switch_off_tile_hidden")
    R.step(["popmenu 0", "wait 800"], timeout=30)
    newmap(R.MAP, "switch_off_restart", out)
    stat("9_switch_off", out); shot("arm_12_switch_off_spawn")
    out["script_errors"] = len(re.findall(r"Script Error", R.read_log()))
    json.dump(out, open(os.path.join(R.RUNS, a.session, "arm.json"), "w"), indent=1, default=str)


def part_armq(a):
    """short armory pass (coop_lockLoadout 1): unlock by the challenge, pick, respawn IN the map, bring it up"""
    out = {}
    R.step(D.RELEASE + ["set cg_fov 90", "set cg_drawviewmodel 2", "wait 500"], timeout=60)
    out["bump"] = bump("fac_ss", 12) + bump("wpn_shotgun", 60)
    menu_heavy()
    R.step(["exec ui/loadout/t80.cfg", "wait 6000", "popmenu 0", "wait 800"], timeout=60)
    stat("q_picked", out)
    t = len(R.read_log())
    out["spawn"] = D._respawn("in-map respawn with the pick")
    out["kit"] = loglines(t, r"KITGIVE|cache models/weapons|coop_dbshotgun")[-6:]
    R.step(["useweaponclass heavy", "wait 3500"], timeout=60); shot("armq_01_respawn_in_map_brought_up")
    json.dump(out, open(os.path.join(R.RUNS, a.session, "armq.json"), "w"), indent=1, default=str)
    # leave no pick behind for the parts that follow ("USE MAP DEFAULT")
    R.step(["append name ,w0c", "wait 5000"], timeout=60)


def die(tag):
    """the harness `give` makes the player invulnerable (nodamage): mortal again, then die and respawn"""
    SEQ[0] += 1
    R.step(["set coop_dbsMortal %d" % SEQ[0], "wait 600"], timeout=30)
    return D._respawn(tag)


def _spot(back=0.0, left=0.0):
    import math
    x, y, z, w = SPOT0[0]
    c, s_ = math.cos(math.radians(w)), math.sin(math.radians(w))
    R.SPOT = (x - back * c - left * s_, y - back * s_ + left * c, z, w)


SPOT0 = [None]
FIRE = ["+attackprimary", "wait 1", "wait 1", "-attackprimary"]


def part_world(a):
    """world behaviour (coop_lockLoadout 0 for this part: the test `give` hands guns over, the kit logic must leave
    them alone). 1 the death drop on the ground + its touch pickup; 2 an AI armed through the mod's AI weapon path,
    killed: the Use prompt with the loot picture, the pickup; 3 shells shared with the pump gun, both ways."""
    out = {}
    SPOT0[0] = R.SPOT
    R.step(["set coop_lockLoadout 0", "wait 300"], timeout=30)
    # ---- 1. death drop, seen, touched
    _spot()
    R.step(D.RELEASE + R.give(D.TIK) + ["wait 4500", "set cg_fov 90", "set cg_drawviewmodel 2"], timeout=90)
    t = len(R.read_log())
    out["death"] = die("died with it at the spot")
    out["deathdrop"] = loglines(t, r"DEATHDROP")[-2:]
    _spot(back=95)
    R.step(R.give("models/weapons/colt45.tik", 32.0) + ["wait 4500"], timeout=90); shot("world_01_death_drop_on_the_ground")
    t = len(R.read_log())
    R.step(["+forward", "wait 800", "-forward", "wait 1500"], timeout=60)
    R.step(R.face(0.0) + ["wait 1200", "useweaponclass heavy", "wait 3200"], timeout=60); shot("world_02_touch_pickup_in_hand")
    out["touch"] = loglines(t, r"Shotgun|coop_dbshotgun|picked|Pickup")[-6:]
    # ---- 2. an AI with the gun, killed: use-to-loot
    _spot()
    R.step(R.give("models/weapons/colt45.tik", 0.0) + ["wait 4500"], timeout=90)
    out["respawn_clean"] = die("fresh inventory (dies with the pistol)")
    _spot()
    R.step(R.give("models/weapons/colt45.tik", 0.0) + ["wait 4500"], timeout=90)
    t = len(R.read_log())
    R.step(["set coop_dbsAI 1", "wait 4500"], timeout=60); shot("world_03_ai_holding_it")
    out["ai_armed"] = loglines(t, r"DBSAI|Script Error")[-3:]
    R.step(["set coop_dbsAI kill", "wait 4000"], timeout=60)
    R.step(["+forward", "wait 330", "-forward", "wait 700", "+lookdown", "wait %d" % a.lookms, "-lookdown", "wait 1500"], timeout=60); shot("world_04_ai_drop_use_prompt")
    t2 = len(R.read_log())
    R.step(["+use", "wait 900", "-use", "wait 2500"], timeout=60); shot("world_05_after_use")
    R.step(["+lookup", "wait %d" % a.lookms, "-lookup", "wait 500", "useweaponclass heavy", "wait 3200"], timeout=60); shot("world_06_looted_in_hand")
    out["ai"] = loglines(t, r"DBSAI|LOOT|loot|Shotgun|coop_dbshotgun")[-10:]
    # ---- 3. shells: one pool. Fresh inventory, the double barrel from the ground (its own start shells), then a pump
    # gun from the ground (its shells go into the same pool), two shots with the double barrel, then the pump gun
    _spot()
    R.step(R.give("models/weapons/colt45.tik", 0.0) + ["wait 4500"], timeout=90)
    out["respawn_clean2"] = die("fresh inventory again")
    _spot(left=-140)
    R.step(R.face(0.0) + ["wait 1500", "set coop_dbsDropTik %s" % D.TIK, "set coop_dbsDropDist 60", "set coop_dbsDropYaw 90", "set coop_dbsDrop 31", "wait 1500",
                          "+forward", "wait 600", "-forward", "wait 1500", "useweaponclass heavy", "wait 3200"], timeout=90); shot("world_07_shells_double_barrel_alone")
    R.step(["set coop_dbsDropTik models/weapons/shotgun.tik", "set coop_dbsDropDist 60", "set coop_dbsDrop 32", "wait 1500",
            "+forward", "wait 600", "-forward", "wait 2500"], timeout=90); shot("world_08_shells_after_pump_gun_pickup")
    R.step(["useweaponclass heavy", "wait 3500"], timeout=60); shot("world_09_other_shotgun_in_hand")
    R.step(FIRE + ["wait 700"] + FIRE + ["wait 6500"], timeout=60); shot("world_10_after_two_shots")
    R.step(["useweaponclass heavy", "wait 3500"], timeout=60); shot("world_11_switched_back")
    _spot()
    json.dump(out, open(os.path.join(R.RUNS, a.session, "world.json"), "w"), indent=1, default=str)


D.PARTS['arm'] = part_arm
D.PARTS['world'] = part_world
D.PARTS['armq'] = part_armq

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--map2", default="m2l1")
    ap.add_argument("--srpage", type=int, default=11)
    ap.add_argument("--lookms", type=int, default=380)
    k, rest = ap.parse_known_args()
    sys.argv = [sys.argv[0]] + rest
    _run = D.run

    def run(a):
        a.map2, a.srpage, a.lookms = k.map2, k.srpage, k.lookms
        assert a.map2 not in ("m3l1a", "m3l1b", "e3l1", "e3l2", "obj_team3")
        return _run(a)
    D.run = run
    D.main()
