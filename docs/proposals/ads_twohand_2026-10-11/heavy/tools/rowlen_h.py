"""SERVER-READ ROW LENGTHS of the heavy lane's staged weapon tiks: every animation row of every tik under
heavy/assets/models/weapons against the RELEASED tik's row of the same name (frames, seconds) - the rifle lane's
rowlen.py as a library, pointed at this lane's staging tree. The server plays a weapon tik's rows by NAME (`reload`
holds WEAPON_RELOADING until its clip ends, `fire` -> idle at its end), so a row whose clip got longer / shorter would
change server state; a row the released tik does not have is only ever shown by the cgame.
A NEW tik (coop_fg42_irons*) is compared with the scoped FG 42 tik of the same finish.

    python rowlen_h.py [--all]      -> ../evidence/rowlen_staged_vs_released.tsv   (--all lists equal rows too)
"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hv
RT = os.path.normpath(os.path.join(hv.LANE, '..', 'rifles', 'tools'))
sys.path.insert(0, RT)
import staged
staged.ASSETS = hv.ASSETS                     # the loose-file layer of the offline file system = OUR staging tree
import rowlen as RL
RL.WDIR = os.path.join(hv.ASSETS, 'models', 'weapons')
RL.HERE = HERE


def ref(tk):
    m = re.match(r'(?i)coop_fg42_irons(_.+)?\.tik$', tk)
    if m:
        return 'FG42.tik' if not m.group(1) else 'fg42%s.tik' % m.group(1)
    return tk


RL.REF = ref

if __name__ == '__main__':
    RL.main()
