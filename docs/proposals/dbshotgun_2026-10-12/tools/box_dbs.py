"""The heavy lane's engine centre-box measure (heavy/tools/boxeng.py) on OUR runs (G:/mohaa-hudfeed4/runs):
    python tools/box_dbs.py <session> dbs --sway [--empty] [--cbx] [--json out.json]
Nothing of boxeng.py is changed: only where it looks for the session."""
import os, sys, runpy
HERE = os.path.dirname(os.path.abspath(__file__))
HEAVY = os.path.abspath(os.path.join(HERE, '..', '..', 'ads_twohand_2026-10-11', 'heavy', 'tools'))
sys.path.insert(0, HEAVY)
import hv                                            # noqa: E402
sys.path.insert(0, HERE)
import dbslib as _L      # noqa: E402
hv.RUNS = _L.RUNS
sys.argv[0] = os.path.join(HEAVY, 'boxeng.py')
runpy.run_path(sys.argv[0], run_name='__main__')
