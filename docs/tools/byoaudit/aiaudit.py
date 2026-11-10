#!/usr/bin/env python3
"""aiaudit - run a converted own-disc map on a private DEDICATED server with one or two background clients and log
every AI's state (coop_mod/aiaudit.scr, cvar coop_aiaudit 1), then judge it. Our code; logs are LOCAL ONLY.

  python aiaudit.py <map> <outdir> faceoff            Allies and Germans spawned in view of each other, players parked
                                                       far away (the map's coop_<x>test 8 hook): do they fight alone?
  python aiaudit.py <map> <outdir> mission [--clients 2] [--test 1] [--minutes 12]
                                                       the map's self-test walk with the AI log on, whole mission
  python aiaudit.py --parse <server qconsole.log>      judge an existing log

Verdict per actor (from the ^~^~^ AIA lines): engaged (ever an enemy / attack state), moved (> 96u from spawn),
died; IDLE = alive at the end, never engaged and never moved. Summary: kills per team, engagement counts, idle list.
Paks: the server and client homes must already hold the local converted pak and the test pak (see README).
"""
import argparse
import collections
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import byoclient  # noqa: E402

AIA = re.compile(r"\^~\^~\^ AIA t=([\d.]+) n=(\d+) e=(\d+) team=(\w+) hp=(-?[\d.]+) st=(\S*) en=(\S+) pos=\( ?(-?[\d.]+) (-?[\d.]+) (-?[\d.]+) ?\) d=([\d.]+)")
DEATH = re.compile(r"\^~\^~\^ AIA_DEATH n=(\d+) team=(\w+) t=([\d.]+)")


def parse(text):
    act = {}
    for m in AIA.finditer(text):
        t, n, e, team, hp, st, en, x, y, z, d = m.groups()
        a = act.setdefault(int(n), {"team": team, "first": float(t), "engaged": False, "attack": False,
                                    "maxd": 0.0, "dead": False, "last": None, "states": collections.Counter()})
        a["last"] = float(t)
        a["states"][st] += 1
        if en != "-":
            a["engaged"] = True
        if st == "attack":
            a["attack"] = True
        a["maxd"] = max(a["maxd"], float(d))
        a["pos"] = (float(x), float(y), float(z))
    for m in DEATH.finditer(text):
        n = int(m.group(1))
        if n in act:
            act[n]["dead"] = True
            act[n]["died_t"] = float(m.group(3))
        else:
            act[n] = {"team": m.group(2), "dead": True, "engaged": True, "attack": True, "maxd": 0.0, "states": {}}
    sums = [m.groups() for m in re.finditer(r"AIA_SUM t=([\d.]+) alive=(\d+) attack=(\d+) withEnemy=(\d+) moved=(\d+)", text)]
    rep = {"actors": len(act)}
    for team in ("german", "american"):
        A = [a for a in act.values() if a["team"] == team]
        rep[team] = {"n": len(A), "engaged": sum(a["engaged"] for a in A), "attack_state": sum(a["attack"] for a in A),
                     "moved": sum(a["maxd"] > 96 for a in A), "died": sum(a["dead"] for a in A)}
    idle = [(n, a["team"], a.get("pos")) for n, a in sorted(act.items())
            if not a["dead"] and not a["engaged"] and a["maxd"] <= 96]
    rep["idle"] = len(idle)
    rep["idle_list"] = idle
    rep["peak_attack"] = max((int(s[2]) for s in sums), default=0)
    rep["peak_withEnemy"] = max((int(s[3]) for s in sums), default=0)
    rep["samples"] = len(sums)
    rep["kills_of_german"] = rep["german"]["died"]
    rep["kills_of_american"] = rep["american"]["died"]
    rep["spawn_lines"] = re.findall(r"\^~\^~\^ FLSPAWN [^\n]*", text)[:200]
    sp = re.findall(r"FLSPAWN (\w+) \d+ at .*? visible=(\d) waited=([\d.]+)", text)
    rep["deferred_spawns"] = len(sp)
    rep["spawned_in_view"] = sum(1 for _s, v, _w in sp if v == "1")
    rep["squad_joined"] = len(re.findall(r"FLSQUAD joined", text))
    rep["groups_started"] = len(re.findall(r"FLGRP start", text))
    rep["jeep"] = re.findall(r"FLJEEP [^\n]*", text)[:6]
    return rep


def run(mapname, outdir, mode, clients=1, test="1", minutes=12.0, game="fl"):
    os.makedirs(outdir, exist_ok=True)
    sets = [("coop_aiaudit", "1"), ("coop_dbno", "0"), ("coop_health", "20000")]
    if mode == "faceoff":
        sets += [("coop_%stest" % game, "8")]
    else:
        sets += [("coop_%stest" % game, test), ("coop_%stestPlayers" % game, str(clients))]
    names = ["AIA_Alpha", "AIA_Bravo"][:clients]
    # BYO_SRVPORT: a private port block per agent - on the shared default 12391 the clients of one run joined
    # ANOTHER agent's audit server (2026-11-10: the flpolish clients loaded coop_ea_1_11 and dropped)
    base = int(os.environ.get("BYO_SRVPORT", "12391"))
    with byoclient.Server(mapname, sets=sets, port=base) as srv:
        if not srv.wait(r"Spawning Entities Done|AIA_START|FLAI ", 420):
            raise RuntimeError("server never loaded the map")
        cl = []
        try:
            for i, nm in enumerate(names):
                home = os.path.join(srv.folder, "home" if i == 0 else "home%d" % (i + 1))
                c = byoclient.Client(mapname, sets=[("cheats", "1")], connect="127.0.0.1:%d" % srv.port, name=nm,
                                     home=home, port=base + 1 + i, w=640, h=360)
                c.__enter__()
                cl.append(c)
                time.sleep(15)
            for c, nm in zip(cl, names):
                byoclient.join_client(srv, c, nm, 300)
            t0 = time.time()
            end_pat = r"FLFACEOFF spawned" if mode == "faceoff" else r"FLTEST end|FLMISSION complete"
            limit = minutes * 60
            done_at = None
            while time.time() - t0 < limit:
                for c in cl:
                    c.check()
                s = srv.text()
                if done_at is None and re.search(end_pat, s):
                    done_at = time.time()
                if done_at and time.time() - done_at > (150 if mode == "faceoff" else 30):
                    break
                time.sleep(5)
        finally:
            for c in cl:
                c.__exit__(None, None, None)
            text = srv.text()
            open(os.path.join(outdir, "server_qconsole.log"), "w", encoding="latin-1").write(text)
    rep = parse(text)
    rep["mode"] = mode
    rep["script_errors"] = len(re.findall(r"Script Error", text))
    json.dump(rep, open(os.path.join(outdir, "aiaudit.json"), "w"), indent=1, default=str)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("map", nargs="?")
    ap.add_argument("outdir", nargs="?")
    ap.add_argument("mode", nargs="?", default="mission")
    ap.add_argument("--clients", type=int, default=1)
    ap.add_argument("--test", default="1")
    ap.add_argument("--minutes", type=float, default=12.0)
    ap.add_argument("--game", default="fl")
    ap.add_argument("--parse")
    a = ap.parse_args()
    if a.parse:
        r = parse(open(a.parse, encoding="latin-1").read())
    else:
        r = run(a.map, a.outdir, a.mode, a.clients, a.test, a.minutes, a.game)
    print(json.dumps({k: v for k, v in r.items() if k not in ("idle_list", "spawn_lines")}, indent=1, default=str))
    print("idle:", r["idle_list"][:40])
