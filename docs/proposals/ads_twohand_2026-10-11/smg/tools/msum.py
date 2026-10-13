"""measure_run.py's result (reload_<run>_<gun>.json) as ONE line per capture - the lane's table figures:
    python msum.py <run> <harness gun key>
stance | reload length (capture frames) | beyond the sway envelope: whole window (rounds left) / after the first 0.64 s
(emptied; the whole-window figure beside it) | back on the aim (deg) | how much of the box the settled aim covers"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, 'reload_%s_%s.json' % (sys.argv[1], sys.argv[2]))))
ORDER = ['stand', 'crouch', 'prone', 'standL', 'standR', 'crouchL', 'crouchR', 'braced']
for case, word in (('loaded', 'rounds left'), ('empty', 'emptied')):
    print('--', word)
    for st in ORDER:
        r = d.get('%s_%s' % (st, case))
        if not r:
            print('   %-8s NOT CAPTURED' % st); continue
        if case == 'empty':
            fig = 'after 0.64 s %5.2f %% (%d over 2 %%) | whole window %5.2f %%' % (r.get('env_after40', -1), r.get('env_over_after40', -1), r.get('env_max', -1))
        else:
            fig = 'envelope max %5.2f %% (%d frames over 2 %%)' % (r.get('env_max', -1), r.get('env_frames_over', -1))
        print('   %-8s reload %3d fr | %s | back %.3f deg | aim covers %s %% | tail %s' % (st, r['frames'], fig, r['back'], r.get('env_cover'), r.get('env_tail')))
