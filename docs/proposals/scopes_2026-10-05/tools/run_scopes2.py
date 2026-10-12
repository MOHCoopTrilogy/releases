"""run_scopes2.py <plan> [args] - the modern scope view (bug-3462) on the scopes-next integrator build.
Private harness G:/mohaa-hudfeed (released v1.10.21 exe + game, basepath = the live install read-only), DISPLAY2,
slot "hudfeed". cgame = cgames/cgame_scopes.dll, gl2 = renderers/gl2_scopes.dll, gl1 = renderers/gl1_scopes.dll (the
root DLLs are restored to the ship set afterwards). The REAL shipping pak zzzzzzzzzz_coop_scopes.pk3 is copied into
the test home for the run and removed after; the only overlay is the place/give driver (coop_selftest_xp.scr).

plans   res WxH [guns]      every optic: hip, scoped, just after the shot, after the bolt, scoped out (one still each)
        ease [guns]         1280x720, fixedtime 16: every frame of scope in / fire / scope out (pop check, GIF frames)
        variants            1280x720: housing (smudge) probe, post effects on, frame generation, retail switch, no post
                            chain, vid_restart at render scale 0.75 / 1.5 while scoped, map change while scoped
        msaa8               1280x720 booted with r_msaa 8 (+ frame generation on top)
        gl1 WxH             cl_renderer opengl1: the 2D fallback and cg_hzmScope 0 (retail)
        extra               1280x720: the other table weapons, a scoped rifle picked up from the ground
"""
import os, re, sys, time, zipfile, shutil, json
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
SCR = R.SCRATCH
MOD = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod"
R.OWNER = "hudfeed"
R.CLIENT = "G:/mohaa-hudfeed"
R.EXE = os.path.join(R.CLIENT, "openmohaa_ironsight.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-hudfeed/runs"
R.PORT = 12701
R.SPOT = R.SPOT[:3] + (int(os.environ.get("SCYAW", "209")),)   # 225 looked into dark foliage: 209 has the house, wall and fence
SLOT = os.path.join(SCR, "test_slot.txt")
LOGF = os.path.join(HERE, "run2.log")
OV = os.path.join(HERE, "ov_scopes2.pk3")
PAK = os.path.join(MOD, "zzzzzzzzzz_coop_scopes.pk3")
PAK_HOME = os.path.join(R.MAINTT, "zzzzzzzzzz_coop_scopes.pk3")
CG = os.environ.get("CG", "cgame_scopes")
GL2 = os.path.join(R.CLIENT, "renderers", os.environ.get("GL2NAME", "gl2_scopes") + ".dll")
GL1 = os.path.join(R.CLIENT, "renderers", os.environ.get("GL1NAME", "gl1_scopes") + ".dll")

GUNS = {
    "kar98s": ("models/weapons/kar98sniper.tik", "zf39", 4.0), "g43s": ("models/weapons/g43sniper.tik", "zf4", 4.0),
    "springfield": ("models/weapons/springfield.tik", "m73b1", 2.5),
    "garands": ("models/weapons/garand_scoped.tik", "m84", 2.2), "mosins": ("models/weapons/nagant_sniper.tik", "pu", 3.5),
    "enfields": ("models/weapons/enfieldsniper.tik", "no32", 3.0),
    "arisakas": ("models/weapons/arisakasniper.tik", "type97", 2.5),
    "carcanos": ("models/weapons/carcanosniper.tik", "carcano", 2.2),
    "l42a1": ("models/weapons/uk_w_l42a1.tik", "no32", 3.0), "svt": ("models/weapons/svt_rifle.tik", "pu", 3.5),
    "fg42": ("models/weapons/FG42.tik", "zf4", 4.0), "mp44s": ("models/weapons/mp44scoped.tik", "zf4", 4.0),
    "g43": ("models/weapons/G43.tik", "zf4", 4.0), "kar98ss": ("models/weapons/kar98snipersilenced.tik", "zf39", 4.0),
    "mosinss": ("models/weapons/nagant_snipersilenced.tik", "pu", 3.5),
    "binoc": ("models/items/binoculars.tik", "-", 0.0),
}
MAIN = ["kar98s", "g43s", "springfield", "garands", "mosins", "enfields", "arisakas", "carcanos"]
OTHER = ["l42a1", "svt", "fg42", "mp44s", "g43", "kar98ss", "mosinss"]
ARGSET = {}                       # +set pairs forced onto the command line (latched / read-at-init cvars)
TOG = ["+button13", "wait 60", "-button13"]      # the scope is a toggle on the ADS press
RX_SC = re.compile(r"\^~\^~\^ SCOPE optic=(\w+) remap=(\d) frac=([\d.]+) fov=([\d.]+) hip=([\d.]+) pupil=(-?[\d.]+),(-?[\d.]+) live=(\d)")
_L = R.launch


def launch(W, H, extra=()):
    orig = R.hw.apply_policy

    def policy(args, **kw):
        args = list(args)
        for k, v in ARGSET.items():
            for i in range(len(args) - 2):
                if args[i] == "+set" and args[i + 1] == k:
                    args[i + 2] = v
                    break
            else:
                args[1:1] = ["+set", k, v]
        return orig(args, **kw)
    R.hw.apply_policy = policy
    try:
        return _L(W, H, extra)
    finally:
        R.hw.apply_policy = orig


R.launch = launch


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    open(LOGF, "a").write(s + "\n")


def shot(name, pre=(), settle=80, timeout=90):
    """ONE engine screenshot per step"""
    return R.step(list(pre) + ["screenshot %s" % name, "wait %d" % settle], timeout=timeout)


def give(gun, mode="give"):
    R.step(S.RELEASE + S.TO_STAND + ["set coop_isMode %s" % mode] + S.give(GUNS[gun][0]), timeout=90)


def last_scope(start):
    m = None
    for m in RX_SC.finditer(R.read_log(), start):
        pass
    return m.groups() if m else None


def cvar(name):
    p0 = len(R.read_log())
    R.step([name, "wait 30"], timeout=30)
    m = re.search(r'"%s" is:"([^"]*)"' % re.escape(name), R.read_log()[p0:])
    return re.sub(r"\^.", "", m.group(1)) if m else None


def stills(sess, gun, res, full=True):
    tag = "%s__%s" % (sess, gun)
    give(gun)
    if full:
        shot(tag + "__0hip")
    p0 = len(R.read_log())
    shot(tag + "__1in", TOG + ["wait 1300"])
    sc = last_scope(p0)
    want = GUNS[gun]
    ok = bool(sc) and sc[0] == want[1] and sc[1] == "1"
    res[gun] = {"scope": sc, "optic_ok": ok}
    log("   %-11s %s %s" % (gun, "OK " if ok else "?? ", sc))
    if full:
        shot(tag + "__2fire", ["+attackprimary", "wait 80", "-attackprimary", "wait 220"])
        shot(tag + "__3bolt", ["wait 1900"])
        p1 = len(R.read_log())
        st = last_scope(p1 - 2000)
        res[gun]["after_bolt"] = st
    shot(tag + "__4out", TOG + ["wait 700"])
    res[gun]["state_out"] = cvar("r_ppScopeState")


def frames(tag, n, idx, every=1):
    out = []
    for _ in range(n):
        out += ["screenshotJPEG %s__%04d" % (tag, idx[0]), "wait 1", "wait 1"]
        for _ in range(every - 1):
            out += ["wait 1", "wait 1"]
        idx[0] += 1
    return out


def ease(sess, gun, res):
    tag = "%s__%s" % (sess, gun)
    give(gun)
    R.step(["set cg_scopeDebug 2", "set coop_isFixed 16", "wait 300"], timeout=30)
    i = [0]
    p0 = len(R.read_log())
    L = ["echo ^~^~^ SCSEQ in %s" % tag] + frames(tag, 3, i) + ["+button13"] + frames(tag, 26, i) + ["-button13"]
    L += ["echo ^~^~^ SCSEQ fire %s" % tag, "+attackprimary"] + frames(tag, 4, i) + ["-attackprimary"] + frames(tag, 20, i, every=3)
    R.step(L, timeout=600)
    # the bolt may have dropped the scope: ask before toggling out
    sc = last_scope(len(R.read_log()) - 600)
    L = ["echo ^~^~^ SCSEQ out %s" % tag]
    if (sc and float(sc[2]) >= 0.99) or os.environ.get("SCOPE0"):
        L += ["+button13"] + frames(tag, 22, i) + ["-button13"]
    else:
        L += frames(tag, 6, i)
    L += ["echo ^~^~^ SCSEQ end %s" % tag, "set coop_isFixed 0", "set cg_scopeDebug 1", "wait 300"]
    R.step(L, timeout=600)
    seg = R.read_log()[p0:]
    fr = [(float(m.group(3)), float(m.group(4))) for m in RX_SC.finditer(seg)]
    res[gun] = {"frames": i[0], "dbg": len(fr), "scoped_before_out": bool(sc and float(sc[2]) >= 0.99)}
    open(os.path.join(HERE, "ease_%s.txt" % gun), "w").write(seg)
    log("   %-11s frames %d dbg lines %d" % (gun, i[0], len(fr)))


def boot(sess, W, H, extra=(), renderer="opengl2"):
    with zipfile.ZipFile(OV, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(HERE, "coop_selftest_xp.scr"), "coop_mod/coop_selftest_xp.scr")
    shutil.copyfile(os.path.join(R.CLIENT, "games", "game_ship.dll"), os.path.join(R.CLIENT, "game.dll"))
    shutil.copyfile(GL2, os.path.join(R.CLIENT, "renderer_opengl2.dll"))
    if renderer == "opengl1":
        shutil.copyfile(GL1, os.path.join(R.CLIENT, "renderer_opengl1.dll"))
    ARGSET["cl_renderer"] = renderer
    ex = ["set coop_st_xp 1", "ui_hud 1", "set developer 1", "set cg_scopeDebug 1",
          "set r_ignoreGLErrors %s" % ("1" if (renderer == "opengl1" and not os.environ.get("GL1STRICT")) else "0"),
          "set cl_yawspeed 32", "set cg_weaponBreath 1", "set cg_headbob 1"] + list(extra)
    if not os.environ.get("NOPAK"):
        os.makedirs(R.MAINTT, exist_ok=True)
        shutil.copyfile(PAK, PAK_HOME)
    elif os.path.exists(PAK_HOME):
        os.remove(PAK_HOME)
    rundir, notes = S.boot_session(sess, CG, W, H, ex, OV)
    notes["renderer"] = renderer
    notes["argset"] = dict(ARGSET)
    log("[%s] booted %dx%d %s %s" % (sess, W, H, renderer, notes.get("md5")))
    return rundir, notes


def finish(rundir, notes, res):
    try:
        if rundir:
            notes["res"] = res
            text = R.read_log()
            notes["gl_errors"] = len(re.findall(r"GL_CheckErrors|GL error|GL_INVALID|GL_OUT_OF", text))
            notes["warnings"] = sorted(set(re.findall(r"[^\r\n]*(?:coop_scope|hzmscope)[^\r\n]*", text)))[:12]
            notes["script_errors"] = sorted(set(l[36:140] for l in text.splitlines() if "Script Error" in l))[:6]
            S.end_session(rundir, notes)
            log("[%s] gl_errors=%s scope log lines=%s script errors=%s" % (notes["session"], notes["gl_errors"],
                                                                         notes["warnings"], notes["script_errors"]))
    except Exception as e:
        log("end_session", repr(e))
    try:
        if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
            R.CL["proc"].kill()
    except Exception:
        pass
    time.sleep(2)
    shutil.copyfile(os.path.join(R.CLIENT, "renderers", "gl2_ship.dll"), os.path.join(R.CLIENT, "renderer_opengl2.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "renderers", "gl1_root_orig.dll"), os.path.join(R.CLIENT, "renderer_opengl1.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "cgames", "cgame_ship.dll"), os.path.join(R.CLIENT, "cgame.dll"))
    for _ in range(20):
        try:
            if os.path.exists(PAK_HOME):
                os.remove(PAK_HOME)
            break
        except OSError:
            time.sleep(1)


def fg_stats():
    p0 = len(R.read_log())
    R.step(["fg_stats", "wait 60"], timeout=30)
    return " | ".join(l.strip()[:230] for l in R.read_log()[p0:].splitlines() if l.strip() and "ISSTEP" not in l and "execing" not in l)[:900]


def rejoin():
    R.join()
    time.sleep(15)
    for _ in range(4):
        t = len(R.read_log())
        R.step(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
        if R.wait_log(r"\^~\^~\^ KITGIVE", 15, t):
            return True
    return False


def plan_variants(res):
    g = "kar98s"
    give(g)
    shot("v__00_hip")
    shot("v__01_in", TOG + ["wait 1300"])
    # ---- the housing: 3% of the blurred scene (default), none, all of it; then the same after turning the view
    shot("v__02_outer100", ["set r_ppScopeOuter 1", "wait 200"])
    shot("v__03_outer000", ["set r_ppScopeOuter 0", "wait 200"])
    shot("v__04_outer097", ["set r_ppScopeOuter 0.97", "wait 200"])
    shot("v__05_pan_outer097", ["+right", "wait 500", "-right", "wait 900"])
    shot("v__06_pan_outer000", ["set r_ppScopeOuter 0", "wait 200"])
    shot("v__07_shadow_off_outer000", ["set cg_scopeShadow 0", "wait 900"])
    R.step(["set r_ppScopeOuter 0.97", "set cg_scopeShadow 1", "wait 200"], timeout=30)
    # ---- post effects on (the harness boots with most of them off)
    pp = ["set r_ppBloom 1", "set r_ppFXAA 1", "set r_ppSharpen 1", "set r_ppTonemap 1", "set r_ppGrade 1",
          "set r_ppMotionBlur 1", "set r_ppDoF 1", "set r_ppFilmGrain 1", "set r_ppChromaticAberration 1",
          "set r_ppSSAO 1", "set cg_adsBreathVignette 1", "set coop_ads_vignette 1", "wait 600"]
    shot("v__10_postfx_in", pp)
    shot("v__11_postfx_out", TOG + ["wait 700"])
    shot("v__12_postfx_in_again", TOG + ["wait 1300"])
    R.step(["set r_ppDoF 0", "set r_ppFilmGrain 0", "set r_ppChromaticAberration 0", "set r_ppMotionBlur 0", "wait 200"], timeout=30)
    # ---- retail switch and the no-post-chain path, live, while scoped
    shot("v__20_retail_cg_hzmScope0", ["set cg_hzmScope 0", "wait 700"])
    shot("v__21_modern_back", ["set cg_hzmScope 1", "wait 900"])
    shot("v__22_nopost", ["set r_postProcess 0", "wait 700"])
    res["live_nopost"] = cvar("r_ppScopeLive")
    shot("v__23_post_back", ["set r_postProcess 1", "wait 700"])
    res["live_post"] = cvar("r_ppScopeLive")
    # ---- frame generation
    R.step(TOG + ["wait 700", "set r_hzmFrameGen 1", "wait 2500", "fg_stats reset", "wait 3000"], timeout=60)
    res["fg_hip"] = fg_stats()
    shot("v__30_fg_hip")
    R.step(TOG + ["wait 1300", "fg_stats reset", "wait 3000"], timeout=60)
    res["fg_scoped"] = fg_stats()
    shot("v__31_fg_scoped")
    R.step(["fg_stats reset", "+right", "wait 1500", "-right", "wait 300"], timeout=60)
    res["fg_scoped_turning"] = fg_stats()
    shot("v__32_fg_scoped_after_turn")
    R.step(TOG + ["wait 100", "fg_stats reset", "wait 3000"], timeout=60)
    res["fg_after_out"] = fg_stats()
    shot("v__33_fg_out")
    res["fg_mode"] = cvar("r_hzmFrameGen")
    R.step(["set r_hzmFrameGen 0", "wait 500"], timeout=30)
    log("   fg hip   :", res["fg_hip"])
    log("   fg scoped:", res["fg_scoped"])
    log("   fg turn  :", res["fg_scoped_turning"])
    log("   fg out   :", res["fg_after_out"])
    # ---- vid_restart while scoped, at render scale 0.75 and 1.5, then back
    shot("v__40_in_before_restart", TOG + ["wait 1300"])
    for rs, nm in (("0.75", "41_rs075"), ("1.5", "42_rs150"), ("1", "43_rs100")):
        R.step(["set r_renderScale %s" % rs, "vid_restart"], timeout=120)
        time.sleep(6)
        p0 = len(R.read_log())
        shot("v__%s_scoped_after_restart" % nm, ["wait 1200"])
        res["restart_" + rs] = {"scope": last_scope(p0 - 3000), "live": cvar("r_ppScopeLive"), "rs": cvar("r_renderScale")}
        log("   vid_restart rs=%s ->" % rs, res["restart_" + rs])
    shot("v__44_out_after_restarts", TOG + ["wait 700"])
    # ---- map change while scoped
    shot("v__50_in_before_map", TOG + ["wait 1300"])
    p0 = len(R.read_log())
    R.step(["map m1l1"], timeout=60)
    m = R.wait_log(r"Detected Coop for", 300, p0)
    res["map_ready"] = bool(m)
    time.sleep(8)
    res["map_joined"] = rejoin()
    time.sleep(6)
    res["state_after_map"] = cvar("r_ppScopeState")
    shot("v__51_after_map_hip")
    R.step(["set coop_isMode here"] + S.give(GUNS[g][0]), timeout=90)
    shot("v__52_after_map_weapon")
    p1 = len(R.read_log())
    shot("v__53_after_map_in", TOG + ["wait 1300"])
    res["scope_after_map"] = last_scope(p1)
    shot("v__54_after_map_out", TOG + ["wait 700"])
    log("   map change:", res["map_ready"], res["map_joined"], res["state_after_map"], res["scope_after_map"])


JHOME = os.path.join(R.CLIENT, "home_join")
JMT = os.path.join(JHOME, "maintt")
JLOG = os.path.join(JMT, "qconsole.log")
JSHOTS = os.path.join(JMT, "screenshots")
JPORT = 12702
J = {"c": None, "n": 0}


def jlog():
    try:
        return open(JLOG, "rb").read().decode("latin-1")
    except OSError:
        return ""


def jwait(pat, timeout, start=0):
    rx = re.compile(pat)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if J["c"].proc.poll() is not None:
            raise RuntimeError("joiner exited")
        m = rx.search(jlog(), start)
        if m:
            return m
        time.sleep(0.4)
    return None


def jstep(lines, timeout=120):
    J["n"] += 1
    mk = "^~^~^ JSTEP %d" % J["n"]
    with open(os.path.join(JMT, "isstep.cfg"), "w", newline="\n") as f:
        f.write("\n".join(list(lines) + ["echo %s" % mk]) + "\n")
    start = len(jlog())
    for _ in range(4):
        J["c"].post_key(0x7B)
        if jwait(r"execing isstep\.cfg", 6, max(0, start - 10)):
            break
    else:
        raise RuntimeError("joiner: F12 never executed isstep.cfg")
    if not jwait(re.escape(mk) + r"\b", timeout, max(0, start - 10)):
        raise RuntimeError("joiner step timed out: %s" % lines[:3])
    return start


def launch_joiner(W=1280, H=720):
    os.makedirs(os.path.join(JMT, "configs"), exist_ok=True)
    shutil.copyfile(os.path.join(R.MAINTT, "configs", "omconfig.cfg"), os.path.join(JMT, "configs", "omconfig.cfg"))
    for f in ("autoexec.cfg", "coop_defaults.cfg", "whatsnew_pending.cfg"):
        shutil.copyfile(os.path.join(R.MAINTT, f), os.path.join(JMT, f))
    for fn in os.listdir(JMT):
        if fn.lower().endswith(".pid"):
            os.remove(os.path.join(JMT, fn))
    if os.path.exists(JLOG):
        os.remove(JLOG)
    os.makedirs(JSHOTS, exist_ok=True)
    for fn in os.listdir(JSHOTS):
        os.remove(os.path.join(JSHOTS, fn))
    shutil.copyfile(PAK, os.path.join(JMT, "zzzzzzzzzz_coop_scopes.pk3"))
    sets = [("com_target_game", "2"), ("fs_basepath", R.GOG), ("fs_homepath", JHOME), ("cl_renderer", "opengl2"),
            ("r_ext_framebuffer_multisample", "0"), ("r_ext_multisample", "0"), ("r_mode", "-1"),
            ("r_customwidth", str(W)), ("r_customheight", str(H)), ("r_fullscreen", "0"), ("developer", "1"),
            ("logfile", "2"), ("net_ip", "127.0.0.1"), ("net_port", str(JPORT)), ("name", "Joiner")]
    args = [R.EXE]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+exec", "is_on.cfg", "+connect", "127.0.0.1:%d" % R.PORT]
    args, late = R.hw.apply_policy(args, width=W, height=H)
    boot_ = ["bind F12 \"exec isstep.cfg\"", "set com_maxfps 60", "set ui_gmbox 0", "set s_volume 0", "set s_musicvolume 0",
             "set cg_scopeDebug 2", "set r_ignoreGLErrors 0", "ui_hud 1", "set ui_crosshair 0", "set cg_drawviewmodel 1"] + late
    with open(os.path.join(JMT, "is_on.cfg"), "w", newline="\n") as f:
        f.write("\n".join(boot_) + "\n")
    J["c"] = R.hw.launch_background(args[0], args[1:], R.CLIENT, policy=False, log=log)
    return J["c"]


def plan_mp(res, rundir):
    x, y, z, yaw = R.SPOT
    give("kar98s")
    shot("mp__h0_host_alone_hip")
    h0 = len(R.read_log())
    launch_joiner()
    log("   joiner pid", J["c"].proc.pid)
    if not jwait(r"UI_DrawConnect called", 120):
        raise RuntimeError("joiner never connected")
    time.sleep(40)
    ok = False
    for _ in range(5):
        jstep(["popmenu 0", "wait 10", "primarydmweapon smg", "wait 5", "join_team allies", "wait 20", "popmenu 0", "wait 40",
               "popmenu 0", "wait 20"])
        if R.wait_log(r"Joiner[^\r\n]*has joined the (Allies|Axis|Free)|has joined the (Allies|Axis|Free)", 15, h0):
            ok = True
            break
    res["joiner_joined"] = ok
    time.sleep(12)
    for _ in range(4):
        t = len(R.read_log())
        jstep(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
        if R.wait_log(r"\^~\^~\^ KITGIVE", 15, t):
            break
    time.sleep(6)
    # the joiner in front of the host, looking back at him, with the same rifle
    import math
    d = 150.0
    jx, jy = x + d * math.cos(math.radians(yaw)), y + d * math.sin(math.radians(yaw))
    t = len(R.read_log())
    R.step(["set coop_isX2 %d" % jx, "set coop_isY2 %d" % jy, "set coop_isZ2 %d" % z, "set coop_isYaw2 %d" % ((yaw + 180) % 360),
            "set coop_isSeq2 %d" % int(time.time()), "wait 4500"], timeout=60)
    m = R.wait_log(r"\^~\^~\^ ISTEST2[^\r\n]*", 20, t)
    res["joiner_placed"] = m.group(0)[:160] if m else None
    log("   joiner:", ok, res["joiner_placed"])
    jstep(["screenshot j0_hip_sees_host", "wait 80"])
    # host scopes at the joiner; joiner watches
    shot("mp__h1_host_scoped_at_joiner", TOG + ["wait 1300"])
    jstep(["screenshot j1_sees_host_scoped", "wait 80"])
    shot("mp__h2_host_fired", ["+attackprimary", "wait 80", "-attackprimary", "wait 250"])
    jstep(["screenshot j2_sees_host_fired", "wait 80"])
    res["joiner_state_while_host_scoped"] = None
    p = len(jlog())
    jstep(["r_ppScopeState", "wait 30"])
    mm = re.search(r'"r_ppScopeState" is:"([^"]*)"', jlog()[p:])
    res["joiner_state_while_host_scoped"] = mm.group(1) if mm else None
    shot("mp__h3_host_out", ["wait 1500"] + TOG + ["wait 700"])
    # the joiner (a REMOTE client: snapshots over the socket) scopes in and out; every frame's state is in its log
    p = len(jlog())
    jstep(TOG + ["wait 1300", "screenshot j3_joiner_scoped", "wait 80"])
    jstep(["+attackprimary", "wait 80", "-attackprimary", "wait 250", "screenshot j4_joiner_fired", "wait 80"])
    shot("mp__h4_host_sees_joiner_scoped")
    jstep(["wait 1500"] + TOG + ["wait 700", "screenshot j5_joiner_out", "wait 80"])
    seg = jlog()[p:]
    fr = [(float(a.group(3)), float(a.group(4)), float(a.group(5))) for a in RX_SC.finditer(seg)]
    res["joiner_scope_frames"] = len(fr)
    if fr:
        fracs = [f[0] for f in fr]
        steps = [round(b - a, 3) for a, b in zip(fracs, fracs[1:])]
        res["joiner_optic"] = RX_SC.search(seg).group(1)
        res["joiner_hip_values"] = sorted(set(f[2] for f in fr))
        res["joiner_scopefov_values"] = sorted(set(f[1] for f in fr))
        res["joiner_max_up_step"] = max(steps) if steps else None
        res["joiner_max_down_step"] = min(steps) if steps else None
        res["joiner_reached_full"] = max(fracs) >= 1.0
    log("   joiner scope:", {k: v for k, v in res.items() if k.startswith("joiner_")})
    jt = jlog()
    res["joiner_gl_errors"] = len(re.findall(r"GL_CheckErrors|GL error|GL_INVALID|GL_OUT_OF", jt))
    open(os.path.join(HERE, "mp_joiner.log"), "w", encoding="latin-1", errors="replace").write(jt)
    # stop the joiner (ours, by handle), collect its stills
    try:
        with open(os.path.join(JMT, "isstep.cfg"), "w", newline="\n") as f:
            f.write("quit\n")
        J["c"].post_key(0x7B)
        J["c"].proc.wait(30)
    except Exception:
        pass
    try:
        if J["c"].proc.poll() is None:
            J["c"].proc.kill()
        J["c"].close()
    except Exception:
        pass
    from PIL import Image
    for fn in sorted(os.listdir(JSHOTS)):
        if fn.lower().endswith(".tga"):
            Image.open(os.path.join(JSHOTS, fn)).save(os.path.join(rundir, "mp__" + fn[:-4] + ".png"))
            os.remove(os.path.join(JSHOTS, fn))
    jp = os.path.join(JMT, "zzzzzzzzzz_coop_scopes.pk3")
    if os.path.exists(jp):
        os.remove(jp)


def watchdog():
    """a fatal engine error leaves the client sitting on its error state: stop OUR client (by handle) so the run ends"""
    import threading

    def loop():
        while True:
            time.sleep(2)
            try:
                p = R.CL["proc"]
                if p is not None and p.poll() is None and re.search(r"fatal crashed|Sys_Error|ERR_FATAL", R.read_log()):
                    time.sleep(2)
                    FATAL.append(re.findall(r"[^\r\n]*fatal crashed[^\r\n]*", R.read_log())[-1:])
                    p.kill()
            except Exception:
                pass
    threading.Thread(target=loop, daemon=True).start()


FATAL = []


def main():
    plan = sys.argv[1]
    a = sys.argv[2:]
    watchdog()
    while open(SLOT).read().strip() != "hudfeed":
        time.sleep(5)
    rundir = notes = None
    res = {}
    try:
        if plan == "res":
            W, H = [int(x) for x in a[0].lower().split("x")]
            guns = a[1].split(",") if len(a) > 1 else MAIN
            rundir, notes = boot("sc_res_%dx%d" % (W, H), W, H)
            for g in guns:
                stills("r%dx%d" % (W, H), g, res)
        elif plan == "ease":
            guns = a[0].split(",") if a else MAIN
            rundir, notes = boot("sc_ease" + ("_retail" if os.environ.get("SCOPE0") else ""), 1280, 720,
                                 extra=(["set cg_hzmScope 0"] if os.environ.get("SCOPE0") else []))
            for g in guns:
                ease("e", g, res)
        elif plan == "variants":
            rundir, notes = boot("sc_variants", 1280, 720)
            plan_variants(res)
        elif plan in ("msaa8", "msaa0"):
            ARGSET["r_msaa"] = plan[4:]
            rundir, notes = boot("sc_" + plan, 1280, 720)
            res["r_msaa"] = cvar("r_msaa")
            for g in ("kar98s", "springfield"):
                stills("m8", g, res)
            give("kar98s")
            R.step(["set r_hzmFrameGen 1", "wait 2500"] + TOG + ["wait 1300", "fg_stats reset", "wait 3000"], timeout=60)
            res["fg_scoped"] = fg_stats()
            shot("m8__fg_scoped")
            R.step(TOG + ["wait 300", "fg_stats reset", "wait 3000"], timeout=60)
            res["fg_hip"] = fg_stats()
            shot("m8__fg_out")
            log("   msaa8 fg scoped:", res["fg_scoped"])
            log("   msaa8 fg hip   :", res["fg_hip"])
        elif plan == "gl1":
            W, H = [int(x) for x in a[0].lower().split("x")]
            rundir, notes = boot("sc_gl1_%dx%d" % (W, H), W, H, renderer="opengl1")
            for g in (MAIN if W == 1280 else ["kar98s", "springfield"]):
                stills("g%dx%d" % (W, H), g, res, full=(g == "kar98s"))
            give("kar98s")
            shot("g%dx%d__retail_in" % (W, H), ["set cg_hzmScope 0", "wait 300"] + TOG + ["wait 1300"])
            shot("g%dx%d__retail_out" % (W, H), TOG + ["wait 700"])
        elif plan == "mp":
            rundir, notes = boot("sc_mp", 1280, 720)
            plan_mp(res, rundir)
        elif plan == "nopost":
            rundir, notes = boot("sc_nopost", 1280, 720, extra=["set r_postProcess 0"])
            res["live"] = cvar("r_ppScopeLive")
            for g in ("kar98s", "springfield", "mosins"):
                stills("np", g, res, full=(g == "kar98s"))
        elif plan == "gl1strict":
            # control: does gl1 raise a GL error at map load WITHOUT any scope code or pak? (r_ignoreGLErrors 0)
            os.environ["NOPAK"] = "1"
            os.environ["GL1STRICT"] = "1"
            try:
                rundir, notes = boot("sc_gl1strict_" + CG, 1280, 720, renderer="opengl1")
                res["booted"] = True
            except Exception as e:
                res["booted"] = False
                res["error"] = repr(e)
            res["fatal"] = FATAL[:2]
            res["log_fatal"] = re.findall(r"[^\r\n]*fatal crashed[^\r\n]*", R.read_log())[-1:]
            log("   gl1 strict control (cgame %s, gl1 %s):" % (CG, os.path.basename(GL1)), res)
        elif plan == "nopak":
            os.environ["NOPAK"] = "1"
            rend = a[0] if a else "opengl2"
            rundir, notes = boot("sc_nopak_" + rend, 1280, 720, renderer=rend)
            give("kar98s")
            p0 = len(R.read_log())
            shot("np_%s__1in" % rend, TOG + ["wait 1300"])
            res["scope"] = last_scope(p0)
            res["state"] = cvar("r_ppScopeState")
            shot("np_%s__4out" % rend, TOG + ["wait 700"])
            log("   nopak:", res)
        elif plan == "extra":
            rundir, notes = boot("sc_extra", 1280, 720)
            for g in OTHER:
                stills("x", g, res, full=False)
            give("binoc")
            shot("x__binoc__1in", TOG + ["wait 1300"])
            shot("x__binoc__4out", TOG + ["wait 700"])
            give("mosins", mode="pick")
            shot("x__pick_mosins__0hip")
            p0 = len(R.read_log())
            shot("x__pick_mosins__1in", TOG + ["wait 1300"])
            res["pick_mosins"] = last_scope(p0)
            shot("x__pick_mosins__4out", TOG + ["wait 700"])
            log("   pickup:", res["pick_mosins"])
    except Exception as e:
        import traceback
        log("FAILED", repr(e), traceback.format_exc()[-900:])
    finally:
        finish(rundir, notes or {}, res)
        open(SLOT, "w").write("free")
        log("slot released (free)")


if __name__ == "__main__":
    main()
