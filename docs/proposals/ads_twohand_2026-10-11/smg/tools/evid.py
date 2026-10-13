"""One gun's evidence set from one run_smg session, in one go (after measure_run.py wrote reload_<run>_<gun>.json):
the four FULL-FRAME GIFs (aimed empty / rounds left, hip empty / rounds left; 20 fps, centre box drawn on the aimed
ones), the stance sheets, and ONE decode sheet of the four GIFs (a row per GIF, played back from the file) to LOOK at.

    python evid.py <session> <harness gun key> <evidence name prefix> <decode sheet out.jpg> [--w 440] [--step 3]
                   [--nohip] [--stances]
"""
import sys, os, re, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.normpath(os.path.join(HERE, '..', 'evidence'))
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim3/runs').rstrip('/')


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    sess, gun, pre, sheet = sys.argv[1:5]
    w = arg('--w', '440'); step = arg('--step', '3')
    d = json.load(open(os.path.join(HERE, 'reload_%s_%s.json' % (sess, gun))))
    gifs = []
    for case, key, word in (('E', 'stand_empty', 'empty'), ('L', 'stand_loaded', 'roundsleft')):
        if key not in d:
            print('no %s capture in %s' % (key, sess)); continue
        a, b = d[key]['reload']
        out = os.path.join(EV, '%s_reload_aimed_%s_%s.gif' % (pre, word, sess))
        subprocess.check_call([sys.executable, os.path.join(HERE, 'dgif.py'), sess, '%s__ads%s__' % (gun, case), out,
                               '--frames', '%d:%d:%s' % (max(0, a - 9), b + 30, step), '--w', w, '--box'])
        gifs.append(out)
    if '--nohip' not in sys.argv:
        marks = {}
        cur = None
        for ln in open(RUNS + '/' + sess + '/qconsole.log', encoding='latin-1', errors='replace'):
            if 'echo' in ln:
                continue
            m = re.search(r'ABSCEN begin (ab__%s__%s__hip([LE])__demohip__after)' % (re.escape(sess), re.escape(gun)), ln)
            if m:
                cur = m.group(2)
            m2 = re.search(r'DEMO reload (\d+)', ln)
            if m2 and cur:
                marks[cur] = int(m2.group(1)); cur = None
        for case, word in (('E', 'empty'), ('L', 'roundsleft')):
            if case not in marks:
                print('no hip %s capture in %s' % (case, sess)); continue
            a = marks[case]
            out = os.path.join(EV, '%s_reload_hip_%s_%s.gif' % (pre, word, sess))
            subprocess.check_call([sys.executable, os.path.join(HERE, 'dgif.py'), sess, '%s__hip%s__' % (gun, case), out,
                                   '--frames', '%d:%d:%s' % (max(0, a - 9), a + 190, step), '--w', w])
            gifs.append(out)
    for g in gifs:
        print('%-70s %.2f MB' % (os.path.basename(g), os.path.getsize(g) / 1e6))
    subprocess.check_call([sys.executable, os.path.join(HERE, 'gifrows.py'), sheet, arg('--dstep', '4'), arg('--dw', '200')] + gifs)
    if '--stances' in sys.argv:
        for case, word in (('E', 'empty'), ('L', 'roundsleft')):
            out = os.path.join(EV, '%s_reload_aimed_%s_stances_%s.jpg' % (pre, word, sess))
            r = subprocess.run([sys.executable, os.path.join(HERE, 'stancesheet.py'), sess, gun, out, '--case', case], capture_output=True, text=True)
            print((r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else out)


if __name__ == '__main__':
    main()
