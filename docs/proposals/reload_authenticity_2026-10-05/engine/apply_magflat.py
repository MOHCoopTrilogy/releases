"""apply_magflat.py - ejected magazines come to rest LYING ON THEIR SIDE, not standing on end (fgame object.cpp).

    python apply_magflat.py <engine root> [--check]

CoopMagObject::CoopMagStop zeroed pitch and roll on landing, which is the magazine's in-the-well orientation: long
axis vertical, so it stood on its end on the floor (ADS agent, MP40 prone ab23). Roll it +-90 degrees about its
own forward axis instead (random side; yaw kept), which lays a vertical magazine flat and leaves one modelled along
X lying as it was. coop_magRestFlat 0 = the old upright rest.
"""
import sys, io, os

MARK = "HZM coop [reload audit phase B] magazine rest"
ANCHOR = '''void CoopMagObject::CoopMagStop(Event *ev)
{
    static cvar_t *pSurf = NULL;

    avelocity = vec_zero;
    angles.x  = 0;
    angles.z  = 0;
    setAngles(angles);
'''
NEW = '''void CoopMagObject::CoopMagStop(Event *ev)
{
    static cvar_t *pSurf = NULL;
    static cvar_t *pFlat = NULL;

    avelocity = vec_zero;
    angles.x  = 0;
    angles.z  = 0;
    // HZM coop [reload audit phase B] magazine rest: pitch 0 / roll 0 is the in-the-well pose (long axis up), so the
    // magazine stood on its end on the floor. Lie it on a random side; coop_magRestFlat 0 = the old upright rest.
    if (!pFlat) {
        pFlat = gi.Cvar_Get("coop_magRestFlat", "1", CVAR_ARCHIVE);
    }
    if (pFlat->integer) {
        angles.z = (G_Random() < 0.5f) ? 90.0f : -90.0f;
    }
    setAngles(angles);
'''


def main():
    root = sys.argv[1]
    p = os.path.join(root, "code", "fgame", "object.cpp")
    raw = io.open(p, "rb").read()
    crlf = b"\r\n" in raw
    s = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in s:
        print("already applied:", p)
        return 0
    if s.count(ANCHOR) != 1:
        print("ANCHOR MISMATCH", s.count(ANCHOR))
        return 1
    if "--check" in sys.argv:
        print("check OK:", p)
        return 0
    s = s.replace(ANCHOR, NEW, 1)
    if crlf:
        s = s.replace("\n", "\r\n")
    io.open(p, "wb").write(s.encode("utf-8"))
    print("applied:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
