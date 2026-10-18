"""run_loadout.py - private-harness proof for the Loadout (Armory) review + bug-3915 (reuses run_joinflood.py plumbing).
Dedicated server on co_lobby1 (released exe + dlls, the loadout-next mod worktree packed as a code pak), two
fake-identity clients on 127.0.0.1 (G:\\mohaa-hudfeed5 / hudfeed4 slots, DISPLAY2 windows only).
    python -I run_loadout.py <runname>
Client 2 (slot 1) has a KNOWN partial unlock record: skins american_army2 / army3 / army_29id_sgt unlocked
(pages 35, 36, 40), pages 37-39 locked; weapon carbine unlocked, kar98 locked.
"""
import importlib.util, os, re, shutil, sys, time

TOOLS = r"C:\mohaa-coop-dev\docs\proposals\joinflood_2026-10-14\tools"
spec = importlib.util.spec_from_file_location("jf", os.path.join(TOOLS, "run_joinflood.py"))
jf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jf)
_p = os.environ.get("HZPAIR")
if _p:
    _a, _b = _p.split(",")
    jf.SLOTS = [("hudfeed" + _a, r"G:\mohaa-hudfeed" + _a), ("hudfeed" + _b, r"G:\mohaa-hudfeed" + _b)]
    jf.H = jf.SLOTS[0][1]
jf.MODWT = r"C:\mohaa-coop-dev\hzm-mod-gunfit2"
jf.ARCHIVE = r"G:\claude_scratch_archive\loadout_review"
jf.SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad\loadout"
log, check, read, wait_for, step, shot = jf.log, jf.check, jf.read, jf.wait_for, jf.step, jf.shot
ST = jf.ST
SKGO = os.environ.get("SKGO", "coop_loASkin")
HERE_OUT = r"G:\claude_scratch_archive\loadout_review\fit4"
UNL = ("models/player/american_army2.tik|models/player/american_army3.tik|models/player/american_army_29id_sgt.tik|"
       "models/weapons/carbine.tik")


def main():
    name = sys.argv[1]
    ST["run"] = name
    ST.update({"usercfg": False, "netdebug": False, "clprobe": False, "clprobe2": False, "listen": False, "mx": {}, "ufps": 30})
    os.makedirs(jf.SCR, exist_ok=True)
    opts = {"srv": "rel", "cl": "rel", "lobby": "fix", "delay": 100, "parkbytes": None, "mx": {}, "ufps": 30,
            "listen": False, "clprobe": False, "usercfg": False}
    code, rev = jf.fix_codepak()
    sbins = jf.prep_bins("rel", jf.H)
    cbins = [jf.prep_bins("rel", jf.SLOTS[i][1]) for i in range(2)]
    shm, smt = jf.seed_server(opts, code)
    def rec(i):
        r = jf.veteran_record(1000 + i)
        r["unlocks"] = UNL
        r["chal"] = "wpn_garand:50" if i == 0 else ""
        r["pend"] = ""
        return r
    pcs = [jf.seed_client(i + 1, jf.SLOTS[i][1], code, rec(i)) for i in range(2)]
    cfgp = os.path.join(smt, "jf_start.cfg")
    txt = read(cfgp).replace("seta developer 0", "seta developer 1")
    open(cfgp, "w", newline="\n").write(txt)
    try:
        slog = jf.start_server(sbins, shm, smt)
        c1 = jf.launch_client(1, cbins[0], pcs[0][0])
        wait_for(slog, r"JFTester1[^\r\n]*entered the battle", 240)
        c2 = jf.launch_client(2, cbins[1], pcs[1][0])
        m = wait_for(slog, r"JFTester2[^\r\n]*entered the battle", 240)
        check("client 2 entered the lobby", m)
        time.sleep(35)   # record + lock export settle
        jf.shot(c2, "a_lobby_c2")
        # --- open the armory on client 2 (what F7 / the LOADOUT button does)
        jf.step(c2, ["exec ui/loadout/open.cfg", "wait 120"])
        time.sleep(3)
        jf.shot(c2, "b_armory_open")
        import csv
        import json
        jobs = json.load(open(os.environ["FITJOBS"]))   # [[name, tik, xfm], ...]
        jf.step(c2, ["exec ui/loadout/open.cfg", "wait 90"])
        time.sleep(3)
        sd = os.path.join(c2["mt"], "screenshots")
        before = set(os.listdir(sd)) if os.path.isdir(sd) else set()
        q = chr(34)
        q = chr(34)
        def setup(j):
            # j = [name, tik, label, xfmThumb, xfmPreview(unused), pid, slot]; xfmThumb was parsed from the GENERATED w<id>_s<slot>.cfg,
            # the preview transform comes from the GENERATED p<id>.cfg itself (exec below), the finish rows only swap the model.
            nm, tik, lab, xt, xw, pid, sl = j
            return ["exec ui/loadout/p%s.cfg" % pid, "set coop_loPrev " + q + tik + q,
                    "set coop_loS%s " % sl + q + tik + q, "set coop_loN%s " % sl + q + lab + q, "set coop_loXfmT%s " % sl + q + xt + q]
        jf.step(c2, ["exec ui/loadout/s1sel.cfg", "exec ui/loadout/p01.cfg", "set coop_loPrev " + q + q, "set coop_loS1 " + q + q, "set coop_loN1 " + q + q,
                     "set coop_loS3 " + q + q, "set coop_loN3 " + q + q, "set coop_loS4 " + q + q, "set coop_loN4 " + q + q])
        time.sleep(1.2)
        jf.step(c2, ["screenshotJPEG fit_000"])
        for j in jobs:
            jf.step(c2, setup(j))
            time.sleep(1.0)
            jf.step(c2, ["screenshotJPEG fit_" + j[0]])
        new = sorted(f for f in os.listdir(sd) if f.startswith("fit_"))
        os.makedirs(os.path.join(HERE_OUT, name), exist_ok=True)
        for f in new:
            shutil.copyfile(os.path.join(sd, f), os.path.join(HERE_OUT, name, f))
        log("fit screenshots:", len(new))
    except Exception as e:
        check("harness ran to the end", False, repr(e))
    finally:
        for c in ST["clients"]:
            try:
                jf.stop_client(c)
            except Exception as e:
                log("stop note", e)
        jf.stop_server()
        time.sleep(2)
    dst = os.path.join(jf.ARCHIVE, name)
    os.makedirs(dst, exist_ok=True)
    for tag, hm in [("srv", jf.home(jf.H, "srv"))] + [("pc%d" % (i + 1), pcs[i][0]) for i in range(2)]:
        if os.path.isdir(hm):
            shutil.move(hm, os.path.join(dst, tag))
    lf = os.path.join(jf.SCR, name + ".log")
    if os.path.isfile(lf):
        shutil.copyfile(lf, os.path.join(dst, "harness.log"))
    log("DONE ->", dst, "rev", rev[:10])
    return 0


if __name__ == "__main__":
    sys.exit(main())
