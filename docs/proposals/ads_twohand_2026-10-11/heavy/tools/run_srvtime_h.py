"""SERVER reload timing on the heavy lane's own test copy (G:\\mohaa-adsanim4, owner adsanim4, port 12598): the rifle
lane's run_srvtime.py / srvtime_ov.py / srvtime_report.py used as libraries and repointed. No screenshots.

    python run_srvtime_h.py ov  <in.pk3 from mkov_h.py> <out.pk3> [--ammo mg] <weapon tik> [<weapon tik> ...]
    python run_srvtime_h.py run <session> --overlay <abs pk3> --cgame cgame_heavy8 --guns fg42,fg42irons --clip 20
                                [--parts hip,hipempty,ads,adsempty] [--after 5500]
    python run_srvtime_h.py rep <session> [--raw]         -> ../evidence/srvtime_<session>.tsv

ov: the measure-only overlay (server script probe + two marks in each named tik's `reload` row; the row's clip is not
changed). A tik that is in the input pk3 is taken from it (= STAGED), else the RELEASED one. `--ammo mg` makes the
probe read the reserve of that ammo type (the rifle lane's reads "rifle").
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hv
RT = os.path.normpath(os.path.join(hv.LANE, '..', 'rifles', 'tools'))
sys.path.insert(0, RT)


def main():
    cmd, argv = sys.argv[1], sys.argv[2:]
    if cmd == 'ov':
        import srvtime_ov as SO
        if '--ammo' in argv:
            i = argv.index('--ammo'); ammo = argv[i + 1]; del argv[i:i + 2]
            assert 'getammo "rifle"' in SO.SCR
            SO.SCR = SO.SCR.replace('getammo "rifle"', 'getammo "%s"' % ammo)
        sys.argv = ['srvtime_ov.py'] + argv
        SO.main()
    elif cmd == 'run':
        import run_srvtime as ST          # its import repoints the shared harness to the RIFLE lane's copy ...
        import run_h                      # ... and this one puts it on OURS (same module objects)
        R = ST.R
        assert R is run_h.R and ST.A is run_h.A, 'harness modules differ'
        assert R.CLIENT == hv.CLIENT and R.PORT == hv.PORT and R.OWNER == hv.OWNER and R.RUNS == hv.RUNS, (R.CLIENT, R.PORT, R.OWNER)
        assert 'adsanim4' in R.EXE and 'adsanim4' in R.LOG and 'adsheavy' in ST.A.LOGF
        sys.argv = ['run_srvtime.py'] + argv
        ST.main()
    elif cmd == 'rep':
        os.environ['ADS_RUNS'] = hv.RUNS
        import srvtime_report as SR
        SR.RUNS = hv.RUNS
        SR.HERE = HERE                     # the table goes to OUR evidence folder
        sys.argv = ['srvtime_report.py'] + argv
        SR.main()
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
