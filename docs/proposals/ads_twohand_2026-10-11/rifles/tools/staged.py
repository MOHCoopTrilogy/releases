"""`import staged` (before any tool that reads game files): the offline tools' read-only file system (ironsights vfs
over the live install's pk3s) then sees every file staged under rifles/assets FIRST, as loose files - a staged tik's
`rechamber_ads` row and its gun clip are found without building an overlay pk3. Nothing is written anywhere.
`staged.off()` / `staged.on()` switch it (boltcap.py reads the RELEASED tik / clip with it off).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools")
import vfs  # noqa: E402
ASSETS = os.path.normpath(os.path.join(HERE, '..', 'assets'))
_read = vfs.read
STATE = {'on': True}
OVERRIDE = {}     # lower-case game path -> bytes (in-process candidates, boltcap.py's solve)


def path(rel):
    return os.path.join(ASSETS, rel.replace('/', os.sep))


def read(p, root=vfs.ROOT):
    k = p.lower().replace(chr(92), '/')
    if k in OVERRIDE:
        return OVERRIDE[k]
    if STATE['on']:
        f = path(p)
        if os.path.isfile(f):
            return open(f, 'rb').read()
    return _read(p, root)


def on():
    STATE['on'] = True


def off():
    STATE['on'] = False


vfs.read = read
