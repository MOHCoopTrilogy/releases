"""run_armory_proof.py - private-harness PROOF of the built Showroom Armory (armory-next): real in-game screenshots at 1080p and 720p,
every tab, a locked item, the compare bars, a finish, and the frames of a browsing GIF.

    python run_armory_proof.py <runname> [--rev <mod commit>] [--sizes 1920x1080,1280x720] [--skip-gif]

ONE batch: dedicated server on co_lobby1 (RELEASED exe + dlls, the armory-next mod worktree packed from a pinned commit as a code pak) and
ONE fake-identity client per size in a private harness copy (G:\\mohaa-hudfeed*), never the live install. The record is a mid-progress
player (XP 8750 = rank 6, some challenge progress) so the sort, the locks and the progress bars all have something to show.
Output: <archive>\\<run>\\<WxH>\\*.tga|jpg and frames_<WxH>\\*.jpg + the client's qconsole.log (script errors are grepped into proof.json).
The harness has no mouse: every "click" is the command its widget runs (stuffcommand), through the F12-exec'd step cfg.
"""
import importlib.util, json, os, re, shutil, subprocess, sys, time

TOOLS = r"C:\mohaa-coop-dev\docs\proposals\joinflood_2026-10-14\tools"
spec = importlib.util.spec_from_file_location("jf", os.path.join(TOOLS, "run_joinflood.py"))
jf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jf)
log, check, read, wait_for, step = jf.log, jf.check, jf.read, jf.wait_for, jf.step
ST = jf.ST

MODWT = r"C:\mohaa-coop-dev\hzm-mod-armory"
jf.MODWT = MODWT
jf.ARCHIVE = r"G:\claude_scratch_archive\armory_build"
jf.SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad\armory_build"
T0 = time.time()
DEADLINE_S = 13 * 60


def code_pak(rev):
    os.makedirs(jf.SCR, exist_ok=True)
    full = subprocess.run(["git", "-C", MODWT, "rev-parse", rev], capture_output=True, check=True).stdout.decode().strip()
    code = os.path.join(jf.SCR, "code_%s.pk3" % full[:10])
    if not os.path.isfile(code):
        tops = [t for t in subprocess.run(["git", "-C", MODWT, "ls-tree", "--name-only", full], capture_output=True, check=True).stdout.decode().splitlines()
                if t not in ("sound", "textures", "models", "gfx", "env") and not t.lower().endswith(".pk3") and not t.startswith(".git")]
        subprocess.run(["git", "-C", MODWT, "archive", "--format=zip", "-1", "-o", code, full, "--"] + tops, check=True)
    return code, full


def pick_slot():
    for _try in range(60):
        for owner, d in (("hudfeed5", r"G:\mohaa-hudfeed5"), ("hudfeed4", r"G:\mohaa-hudfeed4"), ("hudfeed2", r"G:\mohaa-hudfeed2")):
            try:
                jf.hg.acquire_slot(owner, os.path.join(d, "x.exe"), os.path.join(d, "home_probe"), [12892], 1)
                jf.hg.release_slot(owner)
            except Exception as e:
                log("slot", owner, "busy:", str(e)[:80])
                continue
            jf.SLOTS[:] = [(owner, d)]
            jf.H = d
            jf.PRISTINE = os.path.join(d, "pristine")
            jf.SPORT, jf.CPORTS[:] = 12891, [12892, 12893]
            log("using slot", owner)
            return
        time.sleep(15)
    raise RuntimeError("no free harness slot")


def grab(c, sd, name):
    step(c, ["screenshot " + name], timeout=30)
    for _ in range(40):
        p = os.path.join(sd, name + ".tga")
        if os.path.isfile(p):
            s = os.path.getsize(p)
            time.sleep(0.25)
            if os.path.getsize(p) == s and s > 1000:
                return p
        time.sleep(0.25)
    log("screenshot missing", name)
    return None


def do(c, lines, settle=0.8):
    step(c, lines)
    time.sleep(settle)


def record():
    r = jf.veteran_record(1001)
    r["xp"] = "8750"
    r["chal"] = "wpn_garand_v2:121|wpn_thompson_v:74|wpn_mp40:31|wpn_kar98_e:88|wpn_enfield:22|wpn_g43_e:60|wpn_mosin:12"
    r["unlocks"] = ""
    r["pend"] = ""
    return r


# what each shot does: (name, [console lines]).  A "click" is the command the card / tab / slot button runs.
SHOTS = [
    ("a_rifle_open", []),
    ("b_rifle_inspect_kar98k", ["exec ui/loadout/t03.cfg"]),
    ("c_rifle_locked_enfield", ["exec ui/loadout/t05.cfg"]),
    ("d_rifle_finish_gold", ["exec ui/loadout/s1sel.cfg", "exec ui/loadout/t03.cfg", "exec ui/loadout/finp03_1.cfg", "exec ui/loadout/fin1_s1.cfg"]),
    ("e_sniper", ["exec ui/loadout/lktab1.cfg", "exec ui/loadout/t12.cfg"]),
    ("f_smg", ["exec ui/loadout/lktab2.cfg", "exec ui/loadout/t24.cfg"]),
    ("g_smg_locked_drum", ["exec ui/loadout/t25.cfg"]),
    ("h_heavy", ["exec ui/loadout/lktab3.cfg", "exec ui/loadout/t43.cfg"]),
    ("i_pistol", ["exec ui/loadout/s3sel.cfg", "exec ui/loadout/t50.cfg"]),
    ("j_nades", ["exec ui/loadout/s4sel.cfg", "exec ui/loadout/t64.cfg"]),
    ("j2_nades_mills", ["exec ui/loadout/t66.cfg"]),
    ("k_equip_smg", ["exec ui/loadout/s2sel.cfg", "exec ui/loadout/lktab2.cfg", "exec ui/loadout/t28.cfg", "vstr coop_loCcur"]),
]
GIF = [
    ["exec ui/loadout/s1sel.cfg"], ["exec ui/loadout/t03.cfg"], ["exec ui/loadout/t04.cfg"], ["exec ui/loadout/t05.cfg"],
    ["exec ui/loadout/lktab1.cfg"], ["exec ui/loadout/t12.cfg"], ["exec ui/loadout/lktab2.cfg"], ["exec ui/loadout/t24.cfg"],
    ["exec ui/loadout/t25.cfg"], ["exec ui/loadout/lktab3.cfg"], ["exec ui/loadout/t43.cfg"], ["exec ui/loadout/s3sel.cfg"],
    ["exec ui/loadout/t50.cfg"], ["exec ui/loadout/s4sel.cfg"], ["exec ui/loadout/s1sel.cfg", "exec ui/loadout/t03.cfg", "exec ui/loadout/finp03_1.cfg"],
    ["exec ui/loadout/finp03_2.cfg"], ["exec ui/loadout/finp03_3.cfg"],
]


def main():
    name = sys.argv[1]
    a = sys.argv[2:]
    rev = a[a.index("--rev") + 1] if "--rev" in a else "HEAD"
    sizes = [tuple(int(v) for v in s.split("x")) for s in (a[a.index("--sizes") + 1] if "--sizes" in a else "1920x1080,1280x720").split(",")]
    ST["run"] = name
    out = os.path.join(jf.ARCHIVE, name)
    os.makedirs(out, exist_ok=True)
    code, full = code_pak(rev)
    log("code pak", full[:10])
    pick_slot()
    ST.update({"usercfg": False, "netdebug": False, "clprobe": False, "clprobe2": False, "listen": False, "mx": {}, "ufps": 30})
    opts = {"srv": "rel", "cl": "rel", "lobby": "fix", "delay": 0, "parkbytes": None, "mx": {}, "ufps": 30,
            "listen": False, "clprobe": False, "usercfg": False}
    sbins = jf.prep_bins("rel", jf.H)
    cbin = jf.prep_bins("rel", jf.SLOTS[0][1])
    # HZM_CLIENT_EXE / HZM_SERVER_EXE: private copies of the armory-engine build (never the live install)
    for env, dst in (("HZM_CLIENT_EXE", "openmohaa_jf.exe"), ("HZM_SERVER_EXE", "omohaaded_jf.exe")):
        if os.environ.get(env):
            shutil.copyfile(os.environ[env], os.path.join(cbin, dst))
            log(env, os.environ[env], jf.md5f(os.path.join(cbin, dst))[:12])
    shm, smt = jf.seed_server(opts, code)
    proof = {"rev": full, "sizes": [], "errors": []}
    slog = None
    try:
        slog = jf.start_server(sbins, shm, smt)
        for (W, H) in sizes:
            if time.time() - T0 > DEADLINE_S:
                break
            tag = "%dx%d" % (W, H)
            pc = jf.seed_client(1, jf.SLOTS[0][1], code, record())
            # the pristine copy predates the mod: use the worktree's coop_defaults.cfg (it execs ui/loadout/armory_defaults.cfg), as a real install does
            shutil.copyfile(os.path.join(MODWT, "coop_defaults.cfg"), os.path.join(pc[1], "coop_defaults.cfg"))
            c = jf.launch_client(1, cbin, pc[0], fps=30, W=W, Hh=H)
            sd = os.path.join(c["mt"], "screenshots")
            m = wait_for(slog, r"JFTester1[^\r\n]*entered the battle", 240)
            check("client %s entered the lobby" % tag, m)
            time.sleep(40)                  # record + lock/progress export settle
            do(c, ["exec ui/loadout/open.cfg"], 3.0)
            time.sleep(6)                   # the open token re-export (sort commands, progress) + refill
            od = os.path.join(out, tag)
            os.makedirs(od, exist_ok=True)
            got = []
            for nm, lines in SHOTS:
                if lines:
                    do(c, lines)
                if grab(c, sd, nm):
                    got.append(nm)
                do(c, ["echo CVCOUNT " + nm, "cvarlist"], 0.3)      # the engine holds 8192 cvars in all: watch the count
            frames = []
            if "--skip-gif" not in a and W >= 1280 and H <= 720:
                for i, lines in enumerate(GIF):
                    do(c, lines, 0.5)
                    if grab(c, sd, "gif_%02d" % i):
                        frames.append("gif_%02d" % i)
            proof["sizes"].append({"size": tag, "shots": got, "frames": frames})
            lg = read(c["log"])
            errs = [l for l in lg.splitlines() if re.search(r"Script Error|Could not|vstr: |Unknown command|not found", l)]
            proof["errors"] += ["%s: %s" % (tag, l[:160]) for l in errs[:40]]
            jf.stop_client(c)
            time.sleep(3)
            for f in os.listdir(sd):
                shutil.copyfile(os.path.join(sd, f), os.path.join(od, f))
            shutil.copyfile(c["log"], os.path.join(od, "qconsole.log"))
            shutil.rmtree(pc[0], ignore_errors=True)
    except Exception as e:
        check("harness ran to the end", False, repr(e))
    finally:
        for cc in list(ST["clients"]):
            try:
                jf.stop_client(cc)
            except Exception:
                pass
        jf.stop_server()
        time.sleep(2)
    json.dump(proof, open(os.path.join(out, "proof.json"), "w"), indent=1)
    if slog and os.path.isfile(slog):
        shutil.copyfile(slog, os.path.join(out, "server_qconsole.log"))
    log("DONE ->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
