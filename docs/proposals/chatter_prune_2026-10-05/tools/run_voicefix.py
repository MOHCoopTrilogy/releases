"""run_voicefix.py - ONE batched in-engine proof run for the voice-pool fixes (queue slot "voicefix").

    python run_voicefix.py build      # pack the overlay pk3 from the mod working tree + the test probe
    python run_voicefix.py run        # wait for slot == voicefix, boot m3l2, probe, release the slot
    python run_voicefix.py analyze    # parse the run log into PASS/FAIL lines

Harness G:\\mohaa-voicefix = byte copies of the LIVE G:\\mohaa-gl2 exe/cgame/game/renderers, fresh home from the adsanim
pristine (no qkey, no saves), basepath = GOG read-only, net_ip 127.0.0.1, com_maxfps 60, DISPLAY2 via
harness_window.launch_background (reuses the ironsights harness modules).
The overlay pk3 carries the changed voice scripts/aliases/wavs plus a TEST-ONLY coop_selftest_xp.scr whose st_xp_run
(launched by main.scr when coop_st_xp 1) spawns one actor per nation, registers it with aivoice + flchatter and plays
every situation, then hurts the player as a male and as a Manon model. s_show_sounds 1 + developer 1 make the client log
the FILE of every sound it starts, which is what the analyzer checks.
"""
import os, re, sys, time, zipfile, json, collections
IS = r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
SCR = R.SCRATCH
R.OWNER = "voicefix"
R.CLIENT = r"G:\mohaa-voicefix"
R.EXE = os.path.join(R.CLIENT, "openmohaa_ironsight.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-voicefix/runs"
R.PORT = 12663
R.MAP = "m3l2"
QNAME = "voicefix"
SLOT = os.path.join(SCR, "test_slot.txt")
VF = os.path.join(SCR, "voicefix")
OVERLAY = os.path.join(VF, "zzzzzzzzzzzzzz_voicefixtest.pk3")
R.OVERLAY = "zzzzzzzzzzzzzz_voicefixtest.pk3"
LOGF = os.path.join(VF, "run.log")
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
FILES = ["coop_mod/aivoice.scr", "coop_mod/flchatter.scr", "coop_mod/dbno.scr", "coop_mod/deathvox.scr",
         "coop_mod/paradrop.scr", "ubersound/coop_aivoice.scr", "ubersound/coop_audio.scr", "ubersound/coop_chatter.scr",
         "ubersound/coop_flvo.scr", "ubersound/coop_pain.scr", "ubersound/coop_paintiers.scr", "ubersound/coop_taunt.scr",
         "ubersound/ubersound.scr"]


def log(*a):
    s = time.strftime("%H:%M:%S") + " " + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def build():
    os.makedirs(VF, exist_ok=True)
    with zipfile.ZipFile(OVERLAY, "w", zipfile.ZIP_DEFLATED) as z:
        for f in FILES:
            z.write(os.path.join(MOD, f), f)
        for fn in sorted(os.listdir(os.path.join(MOD, "sound", "coop_flvo"))):
            if fn.startswith("fl_"):
                z.write(os.path.join(MOD, "sound", "coop_flvo", fn), "sound/coop_flvo/" + fn)
        z.write(os.path.join(VF, "overlay", "coop_mod", "coop_selftest_xp.scr"), "coop_mod/coop_selftest_xp.scr")
    log("overlay", OVERLAY, len(zipfile.ZipFile(OVERLAY).namelist()), "files")


def run():
    os.makedirs(VF, exist_ok=True)
    log("waiting for slot ==", QNAME)
    while open(SLOT).read().strip() != QNAME:
        time.sleep(5)
    log("slot is ours")
    t0 = time.time()
    rundir = notes = None
    try:
        extra = ["set g_ai 1", "set coop_st_xp 1", "set vf_go 0", "set coop_aiVoiceDebug 1", "set coop_flchatDebug 1",
                 "set s_show_sounds 1", "set coop_aiVoice 1", "set coop_flchatter 1"]
        rundir, notes = S.boot_session("vf1", "cgame_live", 1280, 720, extra, OVERLAY)
        log("booted", notes)
        R.step(["dog 0", "wait 100", "notarget 1", "wait 100", "echo ^~^~^ VFPHASE probe", "set vf_go 1"], timeout=60)
        if not R.wait_log(r"\^~\^~\^ VF done|VF FAIL", 420):
            log("probe did not finish in 7 min")
        R.step(["dog 1", "wait 100", "echo ^~^~^ VFPHASE heat_only"], timeout=60)
        for k in range(8):                     # fire into the air: combat HEAT without any AI engagement
            R.step(["+attackprimary", "wait 300", "-attackprimary", "wait 1500"], timeout=60)
        R.step(["echo ^~^~^ VFPHASE combat", "notarget 0", "wait 100"], timeout=60)
        time.sleep(90)                         # let m3l2's opening Germans and Ramsey's squad fight
        R.step(["echo ^~^~^ VFPHASE end"], timeout=60)
    except Exception as e:
        import traceback
        log("FAILED", repr(e), traceback.format_exc())
    finally:
        try:
            if rundir:
                S.end_session(rundir, notes or {})
            elif R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                R.CL["proc"].kill()
        except Exception as e:
            log("end_session", repr(e))
        open(SLOT, "w").write("free")
        log("slot released (free) after %.1f min" % ((time.time() - t0) / 60))


# ---------------------------------------------------------------- analysis
def nation_of_file(path, pools):
    return pools.get(path.lower().replace("\\", "/"), set())


def load_pools():
    """file -> set of alias stems that reference it (every ubersound/*.scr in the overlay + the mod tree)."""
    m = collections.defaultdict(set)
    for f in FILES:
        if not f.startswith("ubersound/"):
            continue
        for ln in open(os.path.join(MOD, f), encoding="latin-1"):
            mm = re.match(r"\s*alias(?:cache)?\s+(\S+)\s+(\S+)", ln)
            if mm:
                stem = re.sub(r"(#\d+|fl\d+|\d+)$", "", mm.group(1).lower())
                m[mm.group(2).lower().replace("\\", "/")].add(stem)
    return m


def analyze(path=None):
    path = path or os.path.join(R.RUNS, "vf1", "qconsole.log")
    L = open(path, "rb").read().decode("latin-1").splitlines()
    pools = load_pools()
    out, fails = [], 0
    cur = None
    snd = re.compile(r"OpenAL: (?:2D - )?\d+ \(#\d+\) - (\S+)")
    events = []
    for ln in L:
        m = re.search(r"\^~\^~\^ (VFPLAY|VFPAIN|VFCALL|VFDV|VFPHASE|VF actor|AIVOICE|TAUNT)\b(.*)", ln)
        if m:
            cur = [m.group(1), m.group(2).strip(), []]
            events.append(cur)
            continue
        s = snd.search(ln)
        if s and cur is not None:
            cur[2].append(s.group(1).lower())
    phase = ""
    for kind, txt, files in events:
        if kind == "VFPHASE":
            phase = txt
            out.append("---- phase " + txt)
            continue
        voice = [f for f in files if "dialogue" in f or "coop_flvo" in f or "coop_deathvox" in f or "coop/radio" in f]
        if kind == "VFPLAY":
            mm = re.search(r"alias (\S+)", txt)
            alias = mm.group(1).lower() if mm else ""
            ok = (alias == "" and not voice) or (voice and all(alias in nation_of_file(f, pools) for f in voice[:1]))
            out.append("%s VFPLAY %s -> %s" % ("PASS" if ok else "FAIL", txt, voice[:1] or "(nothing)"))
            fails += 0 if ok else 1
        elif kind in ("VFPAIN", "VFCALL", "VFDV"):
            female = "female" in txt
            manon = [f for f in voice if re.search(r"_\d+n(\.|_)|frdfr_", f)]
            if kind == "VFDV" and female:
                ok = not any("coop_deathvox" in f for f in voice)
            elif female:
                ok = bool(voice) and len(manon) == len(voice)
            else:
                ok = not manon
            out.append("%s %s %s -> %s" % ("PASS" if ok else "FAIL", kind, txt, voice[:2] or "(nothing)"))
            fails += 0 if ok else 1
        elif kind == "AIVOICE" or kind == "TAUNT":
            if "play" in txt.lower() or kind == "AIVOICE":
                out.append("     [%s] %s %s -> %s" % (phase, kind, txt[:110], voice[:1]))
        elif kind == "VF actor":
            out.append("     actor " + txt)
    heat = [o for o in out if "[heat_only]" in o and "TAUNT" in o and "coop_flvo" in o]
    out.append("flchatter plays during heat-only phase: %d (must be 0)" % len(heat))
    fails += len(heat)
    out.append("TOTAL FAIL %d" % fails)
    txt = "\n".join(out)
    print(txt)
    open(os.path.join(VF, "analysis.txt"), "w", encoding="utf-8").write(txt)


if __name__ == "__main__":
    {"build": build, "run": run, "analyze": lambda: analyze(sys.argv[2] if len(sys.argv) > 2 else None)}[sys.argv[1]]()
