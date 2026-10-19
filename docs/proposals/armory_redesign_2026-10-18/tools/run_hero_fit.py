"""run_hero_fit.py <runname> <jobs.json> - ONE private-harness batch that renders every job in the Armory HERO box (1920x1080) for hero_fit.py.

jobs.json = [[name, tik, "x y z scale pitch yaw roll"], ...].  The mod tree is armory-next at HEAD (git archive, read-only), one client in a private
harness copy; every frame is the real hero widget (coop_loHero, coop_loPrev, coop_loXfmHero) over its backdrop; hf_000 = the box with the hero off.
Output: G:\\claude_scratch_archive\\hero_fit\\<run>\\shots\\hf_<name>.tga.  A wall-clock deadline (12.5 min) ends the batch cleanly (the solver re-queues the rest).
"""
import importlib.util, json, os, shutil, subprocess, sys, time

TOOLS = r"C:\mohaa-coop-dev\docs\proposals\joinflood_2026-10-14\tools"
spec = importlib.util.spec_from_file_location("jf", os.path.join(TOOLS, "run_joinflood.py"))
jf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jf)
log, check, read, wait_for, step = jf.log, jf.check, jf.read, jf.wait_for, jf.step
ST = jf.ST
MODWT = r"C:\mohaa-coop-dev\hzm-mod-armory"
jf.MODWT = MODWT
jf.ARCHIVE = r"G:\claude_scratch_archive\hero_fit"
jf.SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad\hero_fit"
T0 = time.time()
DEADLINE_S = 12.5 * 60
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_armory_proof as rp   # code_pak / pick_slot / grab / do / record (same plumbing; its module-level jf is a second load, so re-bind)

rp.jf = jf
rp.MODWT = MODWT


def main():
    name, jobsf = sys.argv[1], sys.argv[2]
    jobs = json.load(open(jobsf))
    ST["run"] = name
    out = os.path.join(jf.ARCHIVE, name)
    os.makedirs(os.path.join(out, "shots"), exist_ok=True)
    code, full = rp.code_pak("HEAD")
    log("code pak", full[:10], "jobs", len(jobs))
    rp.pick_slot()
    ST.update({"usercfg": False, "netdebug": False, "clprobe": False, "clprobe2": False, "listen": False, "mx": {}, "ufps": 30})
    opts = {"srv": "rel", "cl": "rel", "lobby": "fix", "delay": 0, "parkbytes": None, "mx": {}, "ufps": 30, "listen": False, "clprobe": False, "usercfg": False}
    sbins = jf.prep_bins("rel", jf.H)
    cbin = jf.prep_bins("rel", jf.SLOTS[0][1])
    shm, smt = jf.seed_server(opts, code)
    pc = jf.seed_client(1, jf.SLOTS[0][1], code, rp.record())
    shutil.copyfile(os.path.join(MODWT, "coop_defaults.cfg"), os.path.join(pc[1], "coop_defaults.cfg"))
    c = None
    done = 0
    try:
        slog = jf.start_server(sbins, shm, smt)
        c = jf.launch_client(1, cbin, pc[0], fps=30, W=1920, Hh=1080)
        sd = os.path.join(c["mt"], "screenshots")
        wait_for(slog, r"JFTester1[^\r\n]*entered the battery|JFTester1[^\r\n]*entered the battle", 240)
        time.sleep(35)
        rp.do(c, ["exec ui/loadout/open.cfg"], 3.0)
        time.sleep(4)
        rp.do(c, ["set coop_loHero 1", "set coop_loPrev \"\"", "set coop_loHeroLk 0", "set coop_loHeroIc 0", "set coop_loCanEq 0"], 0.6)   # baseline = hero ON with no model (the UNLOCKED text is part of it)
        rp.grab(c, sd, "hf_000")
        for nm, tik, xf in jobs:
            if time.time() - T0 > DEADLINE_S:
                log("deadline: stopping at", nm)
                break
            rp.do(c, ["set coop_loHero 1", "set coop_loPrev \"%s\"" % tik, "set coop_loXfmHero \"%s\"" % xf], 0.55)
            if rp.grab(c, sd, "hf_" + nm):
                done += 1
        log("frames", done, "of", len(jobs), "elapsed %.0fs" % (time.time() - T0))
    except Exception as e:
        check("harness ran to the end", False, repr(e))
    finally:
        if c:
            try:
                jf.stop_client(c)
            except Exception as e:
                log("stop note", e)
        jf.stop_server()
        time.sleep(2)
    if c and os.path.isdir(os.path.join(c["mt"], "screenshots")):
        for f in os.listdir(os.path.join(c["mt"], "screenshots")):
            shutil.copyfile(os.path.join(c["mt"], "screenshots", f), os.path.join(out, "shots", f))
    shutil.rmtree(pc[0], ignore_errors=True)
    log("DONE ->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
