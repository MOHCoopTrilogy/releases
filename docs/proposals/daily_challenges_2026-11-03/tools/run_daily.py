"""Daily Orders (v1.10.63) in-engine checks on the PRIVATE client G:\\mohaa-dailies (a copy of G:\\mohaa-rel59; never the live
game, the GOG tree is read-only basepath). The overlay pk3 carries the whole code bucket of the dailies mod worktree.

    python run_daily.py stage [new|old]       overlay + game.dll (new = H:\\hzm_work\\dailies-eng build, old = the rel59 one)
    python run_daily.py mission [w h]         selftest on m1l2a (forced five), toasts, debrief, map change, phase 2
    python run_daily.py lobby <w> <h> [tag]   co_lobby1: the panel + the Service Record DAILY ORDERS tab
    python run_daily.py day <D>               boot with coop_dlyForceDay D (rotation check)
"""
import os, sys, zipfile, shutil, subprocess, time
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e5_run_long as E
import harness_guard as hg

CLIENT = r"G:\mohaa-dailies"
hg.HARNESSES[CLIENT] = {"owner": "dailies", "home": CLIENT + r"\home"}
E.CLIENT = CLIENT
E.EXE = os.path.join(CLIENT, "openmohaa.exe")
E.HOME = os.path.join(CLIENT, "home")
E.MAINTT = os.path.join(E.HOME, "maintt")
E.LOG = os.path.join(E.MAINTT, "qconsole.log")
E.SHOTS = os.path.join(E.MAINTT, "screenshots")
E.RUNS = r"G:\mohaa-dailies\runs"
MOD = r"H:\hzm_work\dailies-mod"
NEWDLL = r"H:\hzm_work\dailies-eng\.cmake\code\server\fgame\Release\game.dll"
OLDDLL = os.path.join(CLIENT, "game_rel59_old.dll")
OVERLAY = "zzzzzzzzzzzzzzzzzz_dailies.pk3"
SKIP_TOP = {"sound", "models", "gfx", "env", "_research", "docs", ".git", "music", "video", "textures"}
SKIP_EXT = {".pk3", ".bsp", ".wav", ".mp3", ".ogg", ".dds", ".jpg", ".tga", ".png", ".skc", ".skd", ".roq", ".zip", ".psd", ".blend", ".py", ".md"}
PORT = 12671


def stage(which="new"):
    files = []
    for root, dirs, fns in os.walk(MOD):
        rel = os.path.relpath(root, MOD).replace("\\", "/")
        top = rel.split("/")[0]
        if top in SKIP_TOP:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d != ".git"]
        for fn in fns:
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            files.append((rel + "/" + fn) if rel != "." else fn)
    for root, dirs, fns in os.walk(os.path.join(MOD, "textures", "hud", "coop_dly")):
        for fn in fns:
            files.append("textures/hud/coop_dly/" + fn)
    files.append("textures/mohmenu/coop_sr_daily.tga")
    pak = os.path.join(E.MAINTT, OVERLAY)
    with zipfile.ZipFile(pak, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(set(files)):
            z.write(os.path.join(MOD, f), f)
    for c in ("autoexec.cfg", "coop_defaults.cfg"):
        shutil.copy2(os.path.join(MOD, c), os.path.join(E.MAINTT, c))
    shutil.copy2(NEWDLL if which == "new" else OLDDLL, os.path.join(CLIENT, "game.dll"))
    print("staged", len(files), "files,", os.path.getsize(pak) // 1024, "KB, game.dll =", which)


def pad(lines_fn, name):
    S = ["@hold", "@attach 0"]
    t = [0]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c))
        t[0] += dt

    def at(ms):
        t[0] = ms

    lines_fn(cmd, at)
    sp = os.path.join(E.RUNS, name + ".txt")
    os.makedirs(E.RUNS, exist_ok=True)
    open(sp, "w", newline="\n").write("\n".join(S) + "\n")
    return sp


def join(cmd, at, t0):
    for k in range(4):
        at(t0 + k * 12000)
        for c in ("popmenu 0", "primarydmweapon rifle", "join_team allies", "popmenu 0", "popmenu 0"):
            cmd(c, 400)
        cmd("+attackprimary", 150)
        cmd("-attackprimary", 300)


def boot(tag, w, h, cfg, script):
    base = ["seta coop_dev 1", "set developer 1", "set g_gametype 2", "set net_port %d" % PORT, "set net_ip 127.0.0.1",
            "set sv_maxclients 4", "seta coop_hardcore 0", "set coop_whatsNewSeen 99", "set cl_memorial 0"]
    E.launch(tag, w, h, base + cfg, ["+set", "in_padTestScript", script.replace("\\", "/"), "+set", "in_padTestGo", "1"])


def mission(w=1280, h=720):
    def lines(cmd, at):
        join(cmd, at, 40000)
        at(52000)
        for k in range(100):
            cmd("screenshotJPEG st_%03d" % k, 1000)
        for k in range(40):
            cmd("screenshotJPEG db_%03d" % k, 3000)
        join(cmd, at, 280000)
        at(340000)
        for k in range(10):
            cmd("screenshotJPEG p2_%03d" % k, 3000)
        at(t_end := 420000)
        cmd("quit", 0)
    sp = pad(lines, "mission")
    cfg = ["set coop_dbno 0", "set coop_dlyForceDay 20802", "seta coop_hudFade 0", "set coop_dlySelftest 1", "set coop_dlySelftestLead 40", "set coop_dlyForceIds e_revive4,e_ammo8,e_obj6,m_downed3,h_capbadge",
           "set ui_dmmap m1l2a", "wait 600", "ui_startdmmap 2"]
    boot("mission_%dx%d" % (w, h), w, h, cfg, sp)


def lobby(w, h, tag="lobby"):
    def lines(cmd, at):
        at(60000)
        cmd("screenshotJPEG lobby_a", 4000)
        cmd("screenshotJPEG lobby_b", 8000)
        cmd("pushmenu coop_sr", 2500)
        cmd("exec ui/coop_sr_pgd.cfg", 2500)
        cmd("screenshotJPEG sr_daily", 2500)
        cmd("exec ui/coop_sr_pgm.cfg", 2000)
        cmd("screenshotJPEG sr_medals", 2000)
        cmd("popmenu 0", 2000)
        cmd("quit", 0)
    sp = pad(lines, "lobby")
    boot("%s_%dx%d" % (tag, w, h), w, h, ["set ui_dmmap co_lobby1", "wait 600", "ui_startdmmap 2"], sp)


def day(d):
    def lines(cmd, at):
        at(55000)
        cmd("screenshotJPEG day", 1000)
        cmd("quit", 0)
    sp = pad(lines, "day")
    boot("day_%s" % d, 960, 540, ["set coop_dlyForceDay %s" % d, "set ui_dmmap co_lobby1", "wait 600", "ui_startdmmap 2"], sp)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "stage":
        stage(a[1] if len(a) > 1 else "new")
    elif a[0] == "mission":
        mission(*(int(x) for x in a[1:3])) if len(a) > 2 else mission()
    elif a[0] == "lobby":
        lobby(int(a[1]), int(a[2]), *(a[3:4]))
    elif a[0] == "day":
        day(a[1])
