"""block until a harness run log says it ended (or a timeout):  python tools/waitlog.py <log> [seconds=540] [text="run ended"]
prints the last line; exit 0 = ended, 3 = still running"""
import sys, time, os
log = sys.argv[1]
lim = float(sys.argv[2]) if len(sys.argv) > 2 else 540
txt = sys.argv[3] if len(sys.argv) > 3 else 'run ended'
t0 = time.time()
while time.time() - t0 < lim:
    if os.path.isfile(log):
        s = open(log, errors='replace').read()
        if txt in s or 'Traceback' in s:
            print(s.strip().splitlines()[-1][:300]); sys.exit(0)
    time.sleep(3)
print('still running after %d s' % lim); sys.exit(3)
