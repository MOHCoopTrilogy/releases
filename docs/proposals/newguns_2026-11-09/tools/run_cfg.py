"""In-game stills of the new guns WITHOUT the pad script (user playing 2026-11-09: in_gamepad 0 / in_joystick 0, no virtual pad).
The whole run is one boot cfg of console commands paced by `wait <frames>` (com_maxfpsUnfocused 60 -> 60 frames ~ 1 s): the
Armory route (w<id>_s1.cfg, `use`), +button13 for the aim, `reload`, cg_3rd_person with a side camera so the gun shows, screenshots.
Launched through harness_window.launch_background (never activated, below-normal priority, muted, no input grab) on the
3440x1440 ultrawide (HZM_TEST_RES), private client G:\\mohaa-newguns, overlay = run_gun.overlay().
    python run_cfg.py <tag> [--map m5l1a] [--res uw]
"""
import os, sys, re, time, shutil, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_gun as G  # noqa: E402
W = G.W
FPS = 60


class Cfg:
    def __init__(self):
        self.lines = []

    def cmd(self, c, ms=0):
        self.lines.append(c)
        if ms:
            self.wait(ms)

    def wait(self, ms):
        self.lines.append('wait %d' % ms)       # qcommon/cmd.c: wait counts MILLISECONDS (cmd_wait -= msec)


GUNS = [('82', 'Bren', 'g0'), ('83', 'MP28', 'g1'), ('84', 'Panzerfaust', 'g2')]


def script(turn_ms):
    """[step0, step per gun]: each step is exec'd over rcon once the previous one echoed its marker"""
    steps = []
    s = Cfg()
    s.cmd('+attack', 300); s.cmd('-attack', 4000); s.cmd('+attack', 300); s.cmd('-attack', 5000)
    if turn_ms:
        s.cmd('+right', turn_ms); s.cmd('-right', 900)
    steps.append(s.lines)
    for gid, name, k in GUNS:
        # [ng10] the Armory loadout lands ~25 s after the exec ("Picked Up <gun>"): its own step, waited on in the log
        steps.append((['exec ui/loadout/w%s_s1.cfg' % gid], r'Picked Up %s' % name))
        s = Cfg()
        s.cmd('use "%s"' % name, 3000)
        s.cmd('screenshotJPEG %s_01_hip' % k, 500)
        if gid == '84':
            s.cmd('+button13', 1500); s.cmd('screenshotJPEG %s_03_ads' % k, 400)
            s.cmd('cg_3rd_person 1', 300); s.cmd('cg_cameradist 22', 0); s.cmd('cg_camerasideoffset 58', 0); s.cmd('cg_cameraheight 2', 1200)
            s.cmd('screenshotJPEG %s_07_third' % k, 400)
            s.cmd('cg_3rd_person 0', 300); s.cmd('cg_cameradist 120'); s.cmd('cg_camerasideoffset 18'); s.cmd('cg_cameraheight 18', 600)
            s.cmd('+attack', 500); s.cmd('screenshotJPEG %s_04_adsfire' % k, 100); s.cmd('-attack', 800); s.cmd('-button13', 2500)
            s.cmd('screenshotJPEG %s_08_after' % k, 300)
            steps.append(s.lines)
            continue
        s.cmd('+button13', 1500); s.cmd('screenshotJPEG %s_03_ads' % k, 1000)
        s.cmd('screenshotJPEG %s_03_ads_b' % k, 1000); s.cmd('screenshotJPEG %s_03_ads_c' % k, 400)
        s.cmd('+attack', 500); s.cmd('screenshotJPEG %s_04_adsfire' % k, 100); s.cmd('-attack', 800)
        s.cmd('-button13', 1200)
        s.cmd('reload', 300)
        for i in range(10):
            s.cmd('screenshotJPEG %s_05_reload_%02d' % (k, i), 280)
        s.wait(2000)
        # [QA 2] aim, a burst so the magazine is not full, the aim picture AFTER the first shots, then reload while aiming
        s.cmd('+button13', 1500); s.cmd('+attack', 900); s.cmd('-attack', 1200)
        s.cmd('screenshotJPEG %s_03_ads_aftershot' % k, 300)
        s.cmd('reload', 50)
        for i in range(8):
            s.cmd('screenshotJPEG %s_06_adsreload_%d' % (k, i), 280)
        s.wait(3000)
        s.cmd('-button13', 2500)
        s.cmd('cg_3rd_person 1', 300); s.cmd('cg_cameradist 22', 0); s.cmd('cg_camerasideoffset 58', 0); s.cmd('cg_cameraheight 2', 1200)
        s.cmd('screenshotJPEG %s_07_third' % k, 400)
        s.cmd('+button13', 1500); s.cmd('screenshotJPEG %s_07_third_aim' % k, 400); s.cmd('-button13', 800)
        s.cmd('cg_3rd_person 0', 300); s.cmd('cg_cameradist 120'); s.cmd('cg_camerasideoffset 18'); s.cmd('cg_cameraheight 18', 800)
        steps.append(s.lines)
    return steps


PORT, RCONPW = 12391, 'ngstills'      # loopback only (net_ip 127.0.0.1): a test value for this private client


def rcon(cmd):
    import socket
    so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); so.settimeout(1.5)
    try:
        so.sendto(b'\xff\xff\xff\xff\x02rcon ' + RCONPW.encode() + b' ' + cmd.encode(), ('127.0.0.1', PORT))
        try:
            so.recvfrom(16384)
        except socket.timeout:
            pass
    finally:
        so.close()


def log_text():
    try:
        return open(W.LOG, 'rb').read().decode('latin-1')
    except OSError:
        return ''


def wait_for(rx, timeout, c):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if c.watcher.violations or c.proc.poll() is not None:
            return False
        if re.search(rx, log_text()):
            return True
        time.sleep(0.5)
    return False


def script_adstest(turn_ms):
    """[ng14] Bren aim picture vs view pitch (ng13: level = a receiver block at the eye, -4 deg = clean)"""
    steps = []
    s = Cfg()
    s.cmd('+attack', 300); s.cmd('-attack', 4000); s.cmd('+attack', 300); s.cmd('-attack', 5000)
    if turn_ms:
        s.cmd('+right', turn_ms); s.cmd('-right', 900)
    steps.append(s.lines)
    steps.append((['exec ui/loadout/w82_s1.cfg'], r'Picked Up Bren'))
    s = Cfg()
    s.cmd('use "Bren"', 3000)
    s.cmd('+button13', 2000)
    for i, cv in enumerate(['', '', '', 'cg_adsRigReliefBias -1', 'cg_adsRigReliefBias 1', 'cg_adsRigReliefBias 0']):
        if cv:
            for c_ in cv.split('; '):
                s.cmd(c_)
            s.wait(1200)
        s.cmd('screenshotJPEG a_bren_%d' % i, 500)
    s.cmd('-button13', 1000)
    s.cmd('give models/weapons/uk_w_vickers.tik', 1500); s.cmd('use "Vickers-Berthier"', 3000)
    s.cmd('+lookup', 160); s.cmd('-lookup', 800)
    s.cmd('+button13', 2000)
    for i, ms in enumerate([0, 40, 40, 40, 40]):
        if ms:
            s.cmd('+lookdown', ms); s.cmd('-lookdown', 800)
        s.cmd('screenshotJPEG a_vb_%d' % i, 500)
    s.cmd('-button13', 500)
    steps.append(s.lines)
    return steps


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('tag'); ap.add_argument('--map', default='m5l1a'); ap.add_argument('--res', default='uw')
    ap.add_argument('--turn', type=int, default=600); ap.add_argument('--adstest', action='store_true'); ap.add_argument('--only', default='')
    a = ap.parse_args()
    G.overlay()
    w, h, center = W.RES[a.res]
    os.makedirs(os.path.join(W.MAINTT, 'configs'), exist_ok=True)
    shutil.copyfile(os.path.join(W.CLIENT, 'pristine', 'omconfig.cfg'), os.path.join(W.MAINTT, 'configs', 'omconfig.cfg'))
    for fn in os.listdir(W.MAINTT):
        if fn.lower().endswith('.pid') or fn == 'whatsnew_pending.cfg':
            os.remove(os.path.join(W.MAINTT, fn))
    if os.path.exists(W.LOG):
        os.remove(W.LOG)
    shutil.rmtree(W.SHOTS, ignore_errors=True); os.makedirs(W.SHOTS, exist_ok=True)
    args = [os.path.join(W.CLIENT, 'openmohaa.exe'), '+set', 'com_target_game', '2', '+set', 'fs_basepath', W.E.GOG, '+set', 'fs_homepath', W.HOME,
            '+set', 'cl_renderer', 'opengl2', '+set', 'r_mode', '-1', '+set', 'r_customwidth', str(w), '+set', 'r_customheight', str(h),
            '+set', 'r_fullscreen', '0', '+set', 'cl_memorial', '0', '+set', 'logfile', '2', '+set', 'r_picmip', '0', '+set', 'com_maxfps', '60',
            '+set', 'cheats', '1', '+set', 'net_enabled', '1', '+set', 'net_ip', '127.0.0.1', '+set', 'net_port', str(PORT), '+exec', 'ng_run.cfg']
    args, late = W.hw.apply_policy(args, width=w, height=h)
    assert 'in_padTestScript' not in ' '.join(args)
    lines = list(late) + ['set developer 1', 'set in_gamepad 0', 'set in_joystick 0', 'set s_volume 0', 'set s_musicvolume 0', 'set s_ambientvolume 0',
                          'seta coop_lo2 ""', 'seta coop_loA2 ""', 'set g_gametype 2', 'set coop_dev 1', 'set coop_lockLoadout 0',
                          'set cg_adsSightDebug 1', 'set coop_vmTrace 1', 'set r_weaponProjAlways 1', 'set r_weaponznear 0.6',
                          'set rconpassword %s' % RCONPW, 'set ui_dmmap %s' % a.map, 'ui_startdmmap 2']
    if a.only:
        GUNS[:] = [g for g in GUNS if g[0] in a.only.split(',')]
    steps = script_adstest(a.turn) if a.adstest else script(a.turn)
    open(os.path.join(W.MAINTT, 'ng_run.cfg'), 'w', newline='\n').write('\n'.join(lines) + '\n')
    if W.hg.user_game_running():
        raise SystemExit('user game running')
    c = W.hw.launch_background(args[0], args[1:], W.CLIENT, policy=False, log=W.log)
    try:
        if not wait_for(r'SELFTEST (OK|FAIL)', 150, c):
            W.log('no map load'); raise SystemExit(1)
        time.sleep(15)
        for i, st in enumerate(steps):
            rx = None
            if isinstance(st, tuple):
                st, rx = st
            mk = '^~^~^ NGSTEP %d' % i
            open(os.path.join(W.MAINTT, 'ngstep.cfg'), 'w', newline='\n').write('\n'.join(st + ['echo ' + mk]) + '\n')
            rcon('exec ngstep.cfg')
            if not wait_for(re.escape(mk) + r'(?![0-9])', 120, c):
                W.log('step', i, 'timed out'); break
            if rx:
                n0 = len(log_text())
                t0 = time.time()
                while time.time() - t0 < 90 and not re.search(rx, log_text()[n0 - 2000:]):
                    time.sleep(0.5)
                time.sleep(2)
            if c.watcher.violations:
                W.log('VIOLATION', c.watcher.violations[:3]); break
        rcon('quit'); time.sleep(3)
    finally:
        if c.proc.poll() is None:
            c.proc.kill()
        c.close()
    out = os.path.join(W.RUNS, a.tag)
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    for fn in sorted(os.listdir(W.SHOTS)):
        shutil.move(os.path.join(W.SHOTS, fn), os.path.join(out, fn))
    shutil.copyfile(W.LOG, os.path.join(out, 'qconsole.log'))
    W.log('run', a.tag, 'shots', len(os.listdir(out)) - 1)


if __name__ == '__main__':
    main()
