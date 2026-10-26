"""m2run.py <label> [stages]  - m2l2c finale on the private harness client (one player). stages: start,craneA,craneB,radio"""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
STAGES = (sys.argv[2] if len(sys.argv) > 2 else "start,craneA,craneB,radio").split(",")
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
T0 = time.time()
def log(*a):
    s = "%5.0fs " % (time.time() - T0) + " ".join(str(x) for x in a)
    G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
def tp(x, y, z, yaw=0, pitch=0): G.cmd("tp", x=x, y=y, z=z, yaw=yaw, pitch=pitch)
def aim(x, y, z): G.cmd("aim", x=x, y=y, z=z)
def hold(ms): R.step(["+use", "wait %d" % ms, "-use", "wait 200"], timeout=60)
def state():
    p0 = G.cmd("m2state")
    for l in G.since(p0, r"\^~\^~\^ (OX M2[^\r\n]*)"): log("  ", l)
    p0 = G.cmd("foepos")
    for l in G.since(p0, r"\^~\^~\^ (OX foepos[^\r\n]*)"): log("  ", l[:230])
def wait(pat, t): return R.wait_log(pat, t, 0)
def panel(name): R.step(["pushmenu coop_objectives", "wait 700", "screenshotJPEG %s" % name, "wait 300", "popmenu 0", "wait 300"], timeout=30)
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c", extra=["set coop_counterDebug 1", "set coop_objxFailsafe 900"] + (["set coop_m2Test 1"] if "test" in os.environ.get("M2FLAGS","") else []) + [x for x in os.environ.get("M2EXTRA","").split(";") if x])
    G.cmd("god"); G.cmd("kit")
    time.sleep(6)
    state()
    if "start" in STAGES:
        ok = wait(r"M2L2C crane A ready", 30); log("crane A ready:", bool(ok))
        tp(-1456, -6360, -496, 90, 0)
        G.still("m2_start")
        panel("m2_panel_start")
        G.frames("m2_gate_closed", 1, 100, pre=[])
    for ci, nm in enumerate(("craneA", "craneB")):
        if nm not in STAGES: continue
        c = ci + 1
        dx, dy, dz = (792, -3740, -452) if c == 1 else (3225, -3600, -452)
        log("-- " + nm + ": at the control panel")
        tp(dx - 45, dy, -512, 0, 0)            # on the walkway, facing the wall switch (east)
        aim(dx, dy, dz)
        time.sleep(0.5)
        G.still("m2_%s_panel" % nm)
        hold(3200)
        ok = wait(r"M2L2C PANEL %s used" % ("A" if c == 1 else "B"), 10); log("panel used:", bool(ok))
        # watch the cycle from the pier edge on the far side with a clear view of the whole route
        if c == 1: tp(748, -4000, -512, 90, -10)
        else: tp(3190, -3850, -512, 90, -10)
        handled = 0
        for k in range(60):
            for q in range(4):
                G.cmd("camhook", k=c)
                G.frames("m2_%s_%02d_%d" % (nm, k, q), 1, 120)
            if k % 4 == 0: state()
            nj = len(re.findall(r"M2L2C crane %s JAMMED" % ("A" if c == 1 else "B"), R.read_log()))
            if nj > handled:
                handled = nj; log("JAMMED (auto-handled)", nm)
                G.cmd("killwave"); time.sleep(1.0)
                tp(dx - 45, dy, -512, 0, 0); aim(dx, dy, dz); time.sleep(0.5)
                hold(2200)
                if c == 1: tp(748, -4000, -512, 90, -10)
                else: tp(3190, -3850, -512, 90, -10)
            if wait(r"M2L2C crane %s IMPACT" % ("A" if c == 1 else "B"), 0.2): break
        G.frames("m2_%s_impact" % nm, 10, 250)
        ok = wait(r"OBJX DONE crane%s" % ("A" if c == 1 else "B"), 20); log("objective done:", bool(ok))
        panel("m2_panel_%s_done" % nm)
    if "jam" in STAGES:
        log("-- defend demo: crane A, player stays at the panel, waves converge, jam, clear, re-activate")
        tp(748, -3790, -512, 0, 0); aim(792, -3740, -452); time.sleep(0.5)
        hold(3200)
        ok = wait(r"M2L2C PANEL A used", 10); log("panel used:", bool(ok))
        tp(748, -3800, -512, 90, 4)
        handled = 0
        for k in range(80):
            G.frames("m2_jam_%02d" % k, 3, 300)
            if k % 3 == 0: state()
            nj = len(re.findall(r"M2L2C crane A JAMMED", R.read_log()))
            if nj > handled:
                handled = nj; log("JAMMED seen at loop", k)
                G.frames("m2_jam_hit", 6, 250)
                p0 = G.cmd("killwave")
                time.sleep(1.0)
                tp(748, -3790, -512, 0, 0); aim(792, -3740, -452); time.sleep(0.5)
                hold(2200)
                ok = wait(r"M2L2C crane A re-activated", 10); log("re-activated:", bool(ok))
                tp(748, -3800, -512, 90, 4)
            if wait(r"M2L2C crane A IMPACT", 0.1): break
        G.frames("m2_jam_end", 8, 250)
    if "gategif" in STAGES:
        log("-- gate opening on camera")
        ok = wait(r"OBJX ACTIVE radio", 40); log("radio active:", bool(ok))
        tp(3656, -3615, -512, 90, 0); aim(3656, -3540, -470); time.sleep(0.4)
        hold(3800)
        ok = wait(r"M2L2C RADIO used", 10); log("radio used:", bool(ok))
        tp(3372, -3640, -512, 270, 6)
        G.frames("m2_gategif", 170, 150)
        log("gate frames done")
    if "exit" in STAGES:
        log("-- exit trigger with the objectives unfinished")
        time.sleep(4)
        tp(3768, -4042, -30, 0, 0)
        ok = wait(r"OBJX GATE closed", 30); log("GATE closed seen:", bool(ok))
        time.sleep(2)
        G.still("m2_exit_refused")
    if "meshgif" in STAGES:
        log("-- mesh gate: before the fake / with the fake, then the gate opening with Axis coming through")
        ok = wait(r"OBJX ACTIVE radio", 40); log("radio active:", bool(ok))
        for nm, (x, y, yaw) in (("m2_mesh_view_a", (3450, -3300, 0)), ("m2_mesh_view_b", (3330, -3250, 0)), ("m2_mesh_view_c", (3500, -3440, 20))):
            tp(x, y, -505, yaw, 0); time.sleep(0.5); G.still(nm)
        tp(3656, -3615, -512, 90, 0); aim(3656, -3540, -470); time.sleep(0.4)
        hold(3800)
        ok = wait(r"M2L2C RADIO used", 10); log("radio used:", bool(ok))
        tp(3430, -3330, -512, 0, 3)
        if os.environ.get("M2NOTGT") == "1": G.cmd("notgt")
        toggled = False
        for ch in range(70):
            G.frames("m2_meshgif_%02d" % ch, 6, 120)
            if os.environ.get("M2NOTGT") == "1" and not toggled and R.wait_log(r"M2L2C mesh gate OPEN", 0.05, 0):
                G.cmd("notgt"); toggled = True; log("targeting back on at chunk", ch)
            if ch % 5 == 4:
                p0 = G.cmd("foepos")
                for l in G.since(p0, r"\^~\^~\^ (OX foepos[^\r\n]*)"): log("  ", l[:260])
        log("mesh frames done")
    if "doorgif" in STAGES:
        log("-- barrel-room door burst")
        ok = wait(r"OBJX ACTIVE radio", 40); log("radio active:", bool(ok))
        tp(3340, -3560, -512, 0, 0); time.sleep(0.4); G.still("m2_door_open_before")
        tp(3656, -3615, -512, 90, 0); aim(3656, -3540, -470); time.sleep(0.4)
        hold(3800)
        ok = wait(r"M2L2C RADIO used", 10); log("radio used:", bool(ok))
        tp(3640, -3700, -512, 170, 3)
        for ch in range(14):
            G.frames("m2_doorgif_%02d" % ch, 20, 130)
            p0 = G.cmd("foepos")
            for l in G.since(p0, r"\^~\^~\^ (OX foepos[^\r\n]*)"): log("  ", l[:260])
        log("door frames done")
    if "jamtest" in STAGES:
        log("-- jam/resume x3 on crane A, plus a man behind the wall and a dead body (must not jam)")
        ok = wait(r"M2L2C crane A ready", 30)
        tp(748, -3790, -512, 0, 0); aim(792, -3740, -452); time.sleep(0.5)
        hold(3200)
        ok = wait(r"M2L2C PANEL A used", 10); log("panel used:", bool(ok))
        tp(748, -3790, -512, 0, 0)
        time.sleep(4)
        # behind the wall (x 860, corridor side of the pier): alive, 110 u from the panel, no line to it
        G.cmd("mkfoe", x=980, y=-3740, z=-512); time.sleep(7)
        log("behind-wall man (alive, 80 u from the panel through the pier wall): jammed =", bool(re.search(r"crane A JAMMED", R.read_log())))
        G.cmd("killwave"); time.sleep(1)
        # dead body in front of the panel: spawn + kill, must not count
        G.cmd("mkfoe", x=745, y=-3690, z=-512); G.cmd("killwave"); time.sleep(7)
        log("dead body: jammed =", bool(re.search(r"crane A JAMMED", R.read_log())))
        for cyc in range(3):
            n0 = len(re.findall(r"crane A JAMMED", R.read_log())); r0 = len(re.findall(r"crane A RESUMED", R.read_log()))
            G.cmd("mkfoe", x=745, y=-3690, z=-512)
            for i in range(30):
                time.sleep(0.5)
                if len(re.findall(r"crane A JAMMED", R.read_log())) > n0: break
            log("cycle", cyc + 1, "jammed:", len(re.findall(r"crane A JAMMED", R.read_log())) > n0)
            time.sleep(1.5); G.cmd("killwave")
            t1 = time.time()
            for i in range(40):
                time.sleep(0.5)
                if len(re.findall(r"crane A RESUMED", R.read_log())) > r0: break
            log("cycle", cyc + 1, "resumed after %.1fs:" % (time.time() - t1), len(re.findall(r"crane A RESUMED", R.read_log())) > r0)
            G.frames("m2_jt_%d" % cyc, 6, 250)
        ok = wait(r"M2L2C crane A IMPACT", 60); log("crane A completed after 3 jam/resume cycles:", bool(ok))
        state()
    if "cranegif" in STAGES:
        log("-- crane A full cycle, real models, one jam/resume")
        ok = wait(r"M2L2C crane A ready", 30)
        tp(748, -3790, -512, 0, 0); aim(792, -3740, -452); time.sleep(0.5)
        G.still("m2_cg_panel")
        hold(3200)
        ok = wait(r"M2L2C PANEL A used", 10); log("panel used:", bool(ok))
        tp(748, -4000, -512, 90, -10)
        jam_done = False
        for k in range(90):
            for q in range(3):
                G.cmd("camhook", k=1)
                G.frames("m2_cg_%02d_%d" % (k, q), 1, 100)
            if k == 12 and not jam_done:
                G.cmd("mkfoe", x=745, y=-3690, z=-512); jam_done = True
            if k == 22 and jam_done:
                G.cmd("killwave")
            if wait(r"M2L2C crane A IMPACT", 0.1): break
        G.frames("m2_cg_impact", 10, 200)
        state()
    if "walkpier" in STAGES:
        if os.environ.get("M2CTRL") != "1": wait(r"M2L2C crane B ready", 40)
        time.sleep(2)
        for nm, (x, y0) in (("A walkway", (748, -4300)), ("B walkway", (3190, -4300))):
            res = []
            for yaw, y1 in ((90, y0), (270, y0 + 1000)):
                tp(x, y1, -505, yaw, 0); time.sleep(0.4)
                R.step(["+forward", "wait 7000", "-forward", "wait 300"], timeout=40)
                p0 = G.cmd("here")
                h = G.since(p0, r"\^~\^~\^ OX here \( ([-\d.]+) ([-\d.]+)")
                res.append((yaw, y1, round(float(h[0][1])) if h else None))
            log("WALK", nm, "ctrl" if os.environ.get("M2CTRL") == "1" else "rig", res)
    if "sinkgif" in STAGES:
        log("-- crane A impact -> burn -> list -> sink; a player standing on the hull must be put ashore")
        ok = wait(r"M2L2C crane A ready", 30)
        tp(748, -3790, -512, 0, 0); aim(792, -3740, -452); time.sleep(0.5)
        hold(3200)
        ok = wait(r"M2L2C PANEL A used", 10); log("panel used:", bool(ok))
        tp(-240, -3900, -512, 0, 6)
        for k in range(60):
            G.frames("m2_sk_pre_%02d" % k, 3, 150)
            if wait(r"M2L2C crane A IMPACT", 0.05): break
        G.frames("m2_sk_imp", 8, 200)
        ok = wait(r"SINKING starts", 20); log("sinking started:", bool(ok))
        tp(230, -3720, -449, 0, 8)     # onto the deck
        time.sleep(1.2)
        p0 = G.cmd("here"); h = G.since(p0, r"\^~\^~\^ OX here \( ([-\d.]+) ([-\d.]+) ([-\d.]+)")
        log("player after 1.2 s on the hull:", h)
        tp(-240, -3900, -512, 0, 6)
        for k in range(150):
            G.frames("m2_sk_%03d" % k, 1, 60)
            if k % 25 == 0: state()
            if wait(r"SUNK, hidden", 0.05): break
        G.frames("m2_sk_end", 10, 250)
        state()
    if "offwave" in STAGES:
        log("-- 3 officer reinforcement calls (hook: real mesh gate -> ring round the officer)")
        tp(792 - 45, -3740, -512, 0, 0)
        for k in range(3):
            G.cmd("offwave"); log("call", k + 1); time.sleep(45)
        for _ in range(30):
            txt = G.R.read_log()
            sp = len(re.findall(r"OFFMAN w=\d+ #\d+ spawned", txt)); dn = len(re.findall(r"OFFMAN w=\d+ #\d+ (?:ARRIVED|FAILED)", txt))
            if sp > 0 and dn >= sp: break
            time.sleep(10)
        for l in re.findall(r"(?:OFFMAN|officer wave|OFFICER wave)[^\r\n]*", G.R.read_log()): log("  ", l[:200])
    if "subs" in STAGES:
        log("-- radio subtitles")
        ok = wait(r"OBJX ACTIVE radio", 40); log("radio active:", bool(ok))
        tp(3656, -3615, -512, 90, 0); aim(3656, -3540, -470); time.sleep(0.5)
        for al, ts in (("m2l2c_radio_call", (0.6, 3.8)), ("m2l2c_radio_mid", (0.8, 3.0, 4.3, 5.2, 6.8)), ("m2l2c_radio_late", (0.8, 3.8)), ("m2l2c_radio_confirm", (1.0, 4.5, 6.0))):
            G.cmd("m2say", s=al); t0 = time.time()
            for i, t in enumerate(ts):
                time.sleep(max(0, t0 + t - time.time())); G.still("m2_sub_%s_%d" % (al[11:], i))
            time.sleep(max(0, t0 + 9 - time.time()))
        G.still("m2_sub_after")
    if "cw" in STAGES:
        log("-- crane A waves: player at the panel, then walking around the quay")
        tp(748 - 0, -3790, -512, 0, 0); aim(792, -3740, -452); time.sleep(0.5)
        hold(3200)
        ok = wait(r"M2L2C PANEL A used", 10); log("panel used:", bool(ok))
        spots = [(748, -3790, 0), (700, -3500, 90), (748, -4100, 270), (600, -3800, 0), (748, -3790, 0)]
        for k in range(14):
            x, y, yw = spots[k % len(spots)]
            tp(x, y, -512, yw, 0); time.sleep(5)
            if k == 3: G.still("m2_cw_still")
            if wait(r"M2L2C crane A IMPACT", 0.1): break
        for l in re.findall(r"M2L2C crane A (?:wave|man)[^\r\n]*|OFFMAN w=2\d\d[^\r\n]*", R.read_log()): log("  ", l[:210])
    if "rnf" in STAGES:
        log("-- rnf_entry from the crane A panel")
        tp(748, -3790, -512, 0, 0); time.sleep(1.0)
        for i in range(4):
            G.cmd("rnftest"); time.sleep(4)
        for l in re.findall(r"RNF entry[^\r\n]*|OX RNFTEST[^\r\n]*", R.read_log()): log("  ", l[:260])
    if "cranev" in STAGES:
        log("-- crane views: start / mid-carry / drop from the panel, the north quay and the west quay")
        cc = 1 if "B" not in os.environ.get("M2CR", "A") else 2
        if cc == 1:
            views = [("panel", (748, -3790, 175, 8), (-100, -3800, 100)), ("north", (748, -4500, 150, 6), (-100, -3800, 100)), ("west", (-215, -3800, 0, 12), (520, -3800, 100))]
            px, py = 792, -3740
        else:
            views = [("panel", (3190, -3590, 175, 8), (2600, -3400, 100)), ("north", (3190, -4300, 150, 6), (2600, -3400, 100)), ("west", (2215, -3400, 0, 12), (3000, -3400, 100))]
            px, py = 3225, -3600
        tp(views[0][1][0], views[0][1][1], -512, 0, 0); aim(px, py, -452); time.sleep(0.5)
        hold(3200)
        ok = wait(r"M2L2C PANEL %s used" % ("A" if cc == 1 else "B"), 10); log("panel used:", bool(ok))
        t0 = time.time()
        for tag, when in (("start", 1.5), ("mid", 14), ("late", 23)):
            time.sleep(max(0, t0 + when - time.time()))
            for nm, (x, y, yw, pt), tgt in views:
                tp(x, y, -512, yw, pt); aim(tgt[0], tgt[1], tgt[2]); time.sleep(0.5)
                G.still("m2_cv_%s_%s" % (tag, nm))
        wait(r"M2L2C crane %s IMPACT" % ("A" if cc == 1 else "B"), 30)
    if "radiov" in STAGES:
        log("-- radio stills")
        ok = wait(r"OBJX ACTIVE radio", 40); log("radio active:", bool(ok))
        for nm, (x, y, yw, pt) in (("front", (3656, -3640, 90, 5)), ("close", (3656, -3590, 90, 15)), ("entrance", (3372, -3640, 20, 5)), ("side", (3560, -3610, 60, 8))):
            tp(x, y, -512, yw, pt); aim(3656, -3540, -480); time.sleep(0.7)
            G.still("m2_rv_" + nm)
        G.cmd("m2ents") if False else None
    if "bartest" in STAGES:
        log("-- barrier test: the gate is open; a player set inside the gate opening must be put back west of it")
        tp(3650, -3300, -512, 0, 0); time.sleep(1.2)
        p0 = G.cmd("m2state")
        for l in G.since(p0, r"\^~\^~\^ (OX M2[^\r\n]*)"): log("  after tp into the opening:", l[l.find("me="):l.find("me=") + 48])
        G.still("m2_barrier_after")
    if "hudtest" in STAGES:
        log("-- crane HUD at 16:9 / 4:3 / 21:9 while jammed")
        ok = wait(r"M2L2C crane A ready", 30)
        tp(748, -3790, -512, 0, 0); aim(792, -3740, -452); time.sleep(0.5)
        hold(3200)
        wait(r"M2L2C PANEL A used", 10)
        G.cmd("mkfoe", x=745, y=-3690, z=-512)
        wait(r"crane A JAMMED", 20)
        for nm, (w, h) in (("169", (1280, 720)), ("43", (1024, 768)), ("219", (2560, 1080))):
            R.step(["set r_customwidth %d" % w, "set r_customheight %d" % h, "vid_restart", "wait 6000"], timeout=60)
            time.sleep(2)
            R.step(["screenshotJPEG m2_hud_%s" % nm, "wait 300"], timeout=20)
            log("hud still", nm)
        G.cmd("killwave")
        time.sleep(6)
        R.step(["screenshotJPEG m2_hud_resume", "wait 300"], timeout=20)
    if "postsink" in STAGES:
        log("-- both boats sink, then 60 s of watching for a reappearing hull")
        for c, (px, py) in ((1, (792, -3740)), (2, (3225, -3600))):
            wait(r"M2L2C crane %s ready" % ("A" if c == 1 else "B"), 40)
            tp(px - 45, py, -512, 0, 0); aim(px, py, -452); time.sleep(0.5)
            hold(3200)
            wait(r"M2L2C PANEL %s used" % ("A" if c == 1 else "B"), 10)
        ok = wait(r"u-boat B SUNK", 150); log("both sunk:", bool(ok), "A", bool(wait(r"u-boat A SUNK", 1)))
        t0 = time.time()
        for k in range(8):
            for nm, (x, y, yaw) in (("A", (-240, -3900, 0)), ("B", (2200, -3400, 0))):
                tp(x, y, -512, yaw, 6); time.sleep(0.3)
                R.step(["screenshotJPEG m2_ps_%s_%d" % (nm, k), "wait 200"], timeout=20)
            log("t+%.0fs" % (time.time() - t0))
            time.sleep(6)
        state()
    if "radio" in STAGES:
        log("-- radio")
        ok = wait(r"OBJX ACTIVE radio", 40); log("radio active:", bool(ok))
        tp(3656, -3615, -512, 90, 0)
        aim(3656, -3540, -470)
        time.sleep(0.5)
        G.still("m2_radio_view")
        tp(3372, -3640, -512, 270, 8); time.sleep(0.4); G.still("m2_gate_closed")
        tp(3656, -3615, -512, 90, 0); aim(3656, -3540, -470); time.sleep(0.4)
        panel("m2_panel_radio")
        hold(3800)
        ok = wait(r"M2L2C RADIO used", 10); log("radio used:", bool(ok))
        tp(3560, -3880, -512, 90, 0)
        for k in range(70):
            G.frames("m2_radio_%02d" % k, 4, 350)
            R.step(["+attackprimary", "wait 600", "-attackprimary", "wait 100"], timeout=20)
            if k % 4 == 0: state()
            if k == 8:
                tp(3372, -3640, -512, 270, 8); time.sleep(0.4); G.still("m2_gate_open_view")
                tp(3560, -3880, -512, 90, 0)
            if k == 3: G.still("m2_gate_open")
            if wait(r"OBJX DONE radio", 0.2): break
        ok = wait(r"OBJX ALL DONE", 20); log("all done:", bool(ok))
        G.frames("m2_exfil", 6, 300)
        panel("m2_panel_final")
        tp(3372, -3640, -512, 270, 8); time.sleep(0.4); G.still("m2_gate_after")
        tp(3768, -4042, -30, 0, 0)       # the exit trigger
        ok = wait(r"OBJX GATE open|COUNTER skip m2l2c|mission", 40); log("exit chain:", bool(ok))
        time.sleep(4)
    ox = G.objx_lines()
    log("---- OBJX log ----")
    for l in ox:
        if "tick" in l: continue
        log(l[:230])
    t = R.read_log()
    for l in re.findall(r"\^~\^~\^ (M2L2C [^\r\n]*)", t):
        if "tick" in l: continue
        log(l[:230])
    errs = G.errors()
    log("script errors:", len(errs), errs[:8])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)
