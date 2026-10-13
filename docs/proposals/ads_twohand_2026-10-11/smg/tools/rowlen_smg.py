"""SERVER TIMING of this lane's STAGED tiks: ..\\..\\integrate\\rowlen_check.py (the integration's gate, untouched) with
the lane's staging tree standing where the fixes working copy stands - every row of the given tiks against the RELEASED
tik's row of the same name (released = the game paks + the mod tree + docs/tools/assets/fixes at git HEAD, which since
2026-10-13 holds the integrated MP40 family). A row the server reads must keep its clip LENGTH; new rows are client-only.

    python rowlen_smg.py --tiks thompson50.tik,thompsonsmg_tommy28.tik [--full] [--intended <rows>]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
INT = os.path.normpath(os.path.join(HERE, '..', '..', 'integrate'))
sys.path.insert(0, INT)
import intlib as L
L.FIX = os.path.normpath(os.path.join(HERE, '..', 'assets'))
if '--released-rev' not in sys.argv:
    sys.argv += ['--released-rev', 'HEAD']
import rowlen_check as RC
if __name__ == '__main__':
    sys.exit(RC.main())
