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
SESS = [sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "vf1"]
SLOT = os.path.join(SCR, "test_slot.txt")
VF = os.path.join(SCR, "voicefix")
OVERLAY = os.path.join(VF, "zzzzzzzzzzzzzz_voicefixtest.pk3")
R.OVERLAY = "zzzzzzzzzzzzzz_voicefixtest.pk3"
LOGF = os.path.join(VF, "run.log")
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
FILES = ["coop_mod/aivoice.scr", "coop_mod/flchatter.scr", "coop_mod/dbno.scr", "coop_mod/deathvox.scr",
         "coop_mod/paradrop.scr", "coop_mod/flmusic.scr", "coop_mod/ambience.scr", "coop_mod/officer.scr", "global/objectives.scr", "ubersound/coop_flpain.scr", "ubersound/coop_aivoice.scr", "ubersound/coop_audio.scr", "ubersound/coop_chatter.scr",
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
        z.write(os.path.join(VF, os.environ.get("VF_OVERLAY", "overlay"), "coop_mod", "coop_selftest_xp.scr"),
                "coop_mod/coop_selftest_xp.scr")
        for sub, pat in (("frontline", "sting_"), ("coop_flvo", "fl_pain_"), ("coop_amb", "fl_far_")):
            for fn in sorted(os.listdir(os.path.join(MOD, "sound", sub))):
                if fn.startswith(pat) and ("sound/%s/%s" % (sub, fn)) not in z.namelist():
                    z.write(os.path.join(MOD, "sound", sub, fn), "sound/%s/%s" % (sub, fn))
    log("overlay", OVERLAY, len(zipfile.ZipFile(OVERLAY).namelist()), "files")


GAMEDLL = r"C:\mohaa-coop-dev\openmohaa-hzm-voicefix\.cmake\code\server\fgame\Release\game.dll"


def run():
    import shutil
    os.makedirs(VF, exist_ok=True)
    live = os.path.join(R.CLIENT, "games", "game_live.dll")
    os.makedirs(os.path.dirname(live), exist_ok=True)
    if not os.path.exists(live):
        shutil.copyfile(os.path.join(R.CLIENT, "game.dll"), live)
    log("waiting for slot ==", QNAME)
    while open(SLOT).read().strip() != QNAME:
        time.sleep(5)
    log("slot is ours")
    t0 = time.time()
    if "--game" in sys.argv:
        shutil.copyfile(GAMEDLL, os.path.join(R.CLIENT, "game.dll"))
        log("game.dll <- voicefix build")
    rundir = notes = None
    try:
        extra = ["set g_ai 1", "set coop_st_xp 1", "set vf_go 0", "set coop_aiVoiceDebug 1", "set coop_flchatDebug 1",
                 "set s_show_sounds 1", "set coop_aiVoice 1", "set coop_flchatter 1"]
        rundir, notes = S.boot_session(SESS[0], "cgame_live", 1280, 720, extra, OVERLAY)
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
        if "--game" in sys.argv:
            time.sleep(2)
            shutil.copyfile(live, os.path.join(R.CLIENT, "game.dll"))
            log("game.dll restored to live")
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
    path = path or os.path.join(R.RUNS, SESS[0], "qconsole.log")
    L = open(path, "rb").read().decode("latin-1").splitlines()
    pools = load_pools()
    out, fails = [], 0
    cur = None
    snd = re.compile(r"OpenAL: (?:2D - )?\d+ \(#\d+\) - (\S+)")
    events = []
    for ln in L:
        if not ln.startswith("["):
            continue
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
        voice = [f for f in files if "dialogue" in f or "coop_flvo" in f or "coop_deathvox" in f or "coop/radio" in f or "sound/frontline/" in f]
        if kind == "VFPLAY":
            mm = re.search(r"alias (\S+)", txt)
            alias = mm.group(1).lower() if mm else ""
            if re.search(r"nat (de|it) sit suppress", txt):
                out.append("SKIP VFPLAY %s (aivoice never asks de/it for suppress)" % txt)
                continue
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
            want = "none"
            for key, nat in (("soviet", "ru"), ("ital", "it"), ("_uk_", "uk"), ("german", "de"), ("resistance", "none"),
                             ("airborne", "us")):
                if key in txt:
                    want = nat
                    break
            got = re.search(r" nat (\S+)", txt).group(1)
            ok = got == want
            out.append("%s actor %s (expected nat %s)" % ("PASS" if ok else "FAIL", txt, want))
            fails += 0 if ok else 1
    heat = [o for o in out if "[heat_only]" in o and "TAUNT" in o and "coop_flvo" in o]
    out.append("flchatter plays during heat-only phase: %d (must be 0)" % len(heat))
    fails += len(heat)
    out.append("TOTAL FAIL %d" % fails)
    txt = "\n".join(out)
    print(txt)
    open(os.path.join(VF, "analysis.txt"), "w", encoding="utf-8").write(txt)


def analyze_sting():
    path = os.path.join(R.RUNS, SESS[0], "qconsole.log")
    L = open(path, "rb").read().decode("latin-1").splitlines()
    snd = re.compile(r"OpenAL: (?:2D - )?\d+ \(#\d+\) - (\S+)")
    cur, ev = None, collections.OrderedDict()
    for ln in L:
        if not ln.startswith("["):
            continue
        m = re.search(r"\^~\^~\^ (VFEV .*|VF done)$", ln)
        if m:
            cur = m.group(1).strip()
            ev[cur] = {"sting": [], "files": [], "log": []}
            continue
        if cur is None:
            continue
        m = re.search(r"\^~\^~\^ (FLSTING .*)$", ln)
        if m:
            ev[cur]["log"].append(m.group(1).strip())
        s = snd.search(ln)
        if s:
            f = s.group(1).lower()
            if "sound/frontline/" in f or "sound/psx/" in f:
                ev[cur]["sting"].append(f)
            elif "fl_pain_" in f or "/pain/" in f or "/damage/" in f or "fl_far" in f or "coop_amb/" in f:
                ev[cur]["files"].append(f)
    out = []
    for k, v in ev.items():
        extra = ""
        if k.startswith("VFEV pain_draws"):
            n = len(v["files"])
            fl = sum(1 for f in v["files"] if "fl_pain_" in f)
            nat = "de" if k.endswith("de") else "us"
            wrong = sum(1 for f in v["files"] if "fl_pain_" in f and ("fl_pain_%s_" % nat) not in f)
            extra = " draws=%d frontline=%d wrong_nation=%d" % (n, fl, wrong)
            v["files"] = sorted(set(f for f in v["files"] if "fl_pain_" in f))
        out.append("%s: sting=%s log=%s files=%s%s" % (k, v["sting"], v["log"], v["files"][:6], extra))
    txt = "\n".join(out)
    print(txt)
    open(os.path.join(VF, "analysis_sting.txt"), "w", encoding="utf-8").write(txt)

if __name__ == "__main__":
    {"build": build, "run": run, "analyze": lambda: analyze(None), "analyze_sting": analyze_sting}[sys.argv[1]]()
