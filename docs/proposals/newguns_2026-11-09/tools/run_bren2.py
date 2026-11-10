"""In-game check of the rebuilt Bren sights (newguns2 2026-11-09, BREN_SIGHTS.md C.3) on the PRIVATE client G:\\mohaa-newguns.
Same harness as run_cfg.py (harness_window.launch_background: never activated, guard ENFORCED, muted, in_mouse 0, in_nograb 1,
in_gamepad 0, in_joystick 0; console steps over loopback rcon only), but the gun comes by the Armory route (w82_s1.cfg) and the steps are the sight checks:
  ADS x3; a sway series (5 frames 0.3 s apart, standing, then strafing); a burst and the ADS after the first shots;
  an aimed reload (10 frames); the hip reload (10 frames); cg_adsSightDebug 1 throughout (ADSSIGHT F / R px in the log).
The window is 2 px shorter than the display (bug-10735: a window covering the display exactly made the guard read the
user's own display-wide cursor clip as ours).
    python run_bren2.py <tag> [--map m5l1a]
"""
import os, sys, re, time, shutil, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_gun as G  # noqa: E402
G.MODWT = r"H:\hzm_work\newguns2-mod"
import run_cfg as RC  # noqa: E402
W = G.W
W.RUNS = r"H:\hzm_work\newguns2\runs"
Cfg = RC.Cfg


def script(turn_ms):
    steps = []
    s = Cfg()
    s.cmd('+attack', 300); s.cmd('-attack', 4000); s.cmd('+attack', 300); s.cmd('-attack', 5000)
    if turn_ms:
        s.cmd('+right', turn_ms); s.cmd('-right', 900)
    steps.append(s.lines)
    # `give` needs cheats, which ui_startdmmap clears: the Armory route (the loadout lands ~25 s after the exec)
    steps.append((['exec ui/loadout/w82_s1.cfg'], r'Picked Up Bren'))
    s = Cfg()
    s.cmd('use "Bren"', 3000)
    s.cmd('screenshotJPEG b_01_hip', 600)
    s.cmd('+button13', 2000)
    for i in range(3):
        s.cmd('screenshotJPEG b_03_ads_%d' % i, 700)
    for i in range(5):
        s.cmd('screenshotJPEG b_04_sway_%d' % i, 300)
    s.cmd('+moveleft', 400)
    for i in range(5):
        s.cmd('screenshotJPEG b_04_swaymove_%d' % i, 300)
    s.cmd('-moveleft', 1500)
    s.cmd('+attack', 120); s.cmd('screenshotJPEG b_05_adsfire_0', 120); s.cmd('screenshotJPEG b_05_adsfire_1', 300)
    s.cmd('-attack', 1500)
    s.cmd('screenshotJPEG b_05_ads_aftershot', 600)
    s.cmd('reload', 50)
    for i in range(10):
        s.cmd('screenshotJPEG b_06_adsreload_%02d' % i, 300)
    s.wait(3500)
    s.cmd('screenshotJPEG b_06_ads_afterreload', 400)
    s.cmd('-button13', 2500)
    s.cmd('+attack', 600); s.cmd('-attack', 1500)
    s.cmd('reload', 300)
    for i in range(10):
        s.cmd('screenshotJPEG b_07_reload_%02d' % i, 280)
    s.wait(2500)
    steps.append(s.lines)
    return steps


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('tag'); ap.add_argument('--map', default='m5l1a'); ap.add_argument('--turn', type=int, default=600)
    a = ap.parse_args()
    G.overlay()
    w, h = 3440, 1438
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
            '+set', 'cheats', '1', '+set', 'net_enabled', '1', '+set', 'net_ip', '127.0.0.1', '+set', 'net_port', str(RC.PORT), '+exec', 'ng_run.cfg']
    args, late = W.hw.apply_policy(args, width=w, height=h)
    joined = ' '.join(args) + ' ' + ' '.join(late)
    assert 'in_padTestScript' not in joined and 'in_mouse' in joined, joined   # the policy forces in_mouse 0 / in_nograb 1
    lines = list(late) + ['set developer 1', 'set in_mouse 0', 'set in_nograb 1', 'set in_gamepad 0', 'set in_joystick 0', 'set s_volume 0',
                          'set s_musicvolume 0', 'set s_ambientvolume 0',
                          'seta coop_lo2 ""', 'seta coop_loA2 ""', 'set g_gametype 2', 'set coop_dev 1', 'set coop_lockLoadout 0', 'seta coop_hardcore 0',
                          'set cg_adsSightDebug 1', 'set coop_vmTrace 1', 'set r_weaponProjAlways 1', 'set r_weaponznear 0.6',
                          'set rconpassword %s' % RC.RCONPW, 'set ui_dmmap %s' % a.map, 'ui_startdmmap 2']
    steps = script(a.turn)
    open(os.path.join(W.MAINTT, 'ng_run.cfg'), 'w', newline='\n').write('\n'.join(lines) + '\n')
    if W.hg.user_game_running():
        raise SystemExit('user game running')
    c = W.hw.launch_background(args[0], args[1:], W.CLIENT, policy=False, log=W.log)
    ok = True
    try:
        if not RC.wait_for(r'SELFTEST (OK|FAIL)', 150, c):
            W.log('no map load'); ok = False
        else:
            time.sleep(15)
            for i, st in enumerate(steps):
                rx = None
                if isinstance(st, tuple):
                    st, rx = st
                mk = '^~^~^ NGSTEP %d' % i
                open(os.path.join(W.MAINTT, 'ngstep.cfg'), 'w', newline='\n').write('\n'.join(st + ['echo ' + mk]) + '\n')
                RC.rcon('exec ngstep.cfg')
                if not RC.wait_for(re.escape(mk) + r'(?![0-9])', 150, c):
                    W.log('step', i, 'timed out'); ok = False; break
                if rx:
                    n0 = len(RC.log_text()); t0 = time.time()
                    while time.time() - t0 < 90 and not re.search(rx, RC.log_text()[n0 - 2000:]):
                        time.sleep(0.5)
                    time.sleep(2)
                if c.watcher.violations:
                    W.log('VIOLATION', c.watcher.violations[:3]); ok = False; break
            RC.rcon('quit'); time.sleep(3)
    finally:
        if c.proc.poll() is None:
            c.proc.kill()
        rep = c.report() if hasattr(c, 'report') else {}
        c.close()
    out = os.path.join(W.RUNS, a.tag)
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    for fn in sorted(os.listdir(W.SHOTS)):
        shutil.move(os.path.join(W.SHOTS, fn), os.path.join(out, fn))
    if os.path.exists(W.LOG):
        shutil.copyfile(W.LOG, os.path.join(out, 'qconsole.log'))
    W.log('run', a.tag, 'ok' if ok else 'FAILED', 'shots', len(os.listdir(out)) - 1, 'violations', (rep or {}).get('violations'))


if __name__ == '__main__':
    main()
