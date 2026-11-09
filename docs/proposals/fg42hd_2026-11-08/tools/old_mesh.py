"""dump the shipped FG 42 meshes (load-order winners) per surface: bone, raw bone-local bounds -> build/old_<name>.npz"""
import sys, os, struct, json
import numpy as np
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
import gen_wpnfix_pak as W
import skd as K
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build")


def bones(b):
    nsurf, nbones, ofsb = struct.unpack_from("<3i", b, 72)
    out = []; off = ofsb
    for _ in range(nbones):
        nm = b[off:off + 32].split(b"\0")[0].decode(); par = b[off + 32:off + 64].split(b"\0")[0].decode()
        typ, ofsdata, ofsch, ofsrc, ofsend = struct.unpack_from("<5i", b, off + 64)
        out.append((nm, par, typ, b[off + 84: off + ofsend]))
        off += ofsend
    return out


for rel in sys.argv[1:]:
    w, b = W.carriers(rel)[-1]
    m = K.read(b)
    print("==", rel, w, len(b))
    for nm, par, typ, data in bones(b):
        print("  bone %-12s parent %-10s type %d data %d bytes %s" % (nm, par, typ, len(data), data[:24].hex()))
    for s in m["surfaces"]:
        P = np.array([v["pos"] for v in s["verts"]]); bi = sorted(set(v["bone"] for v in s["verts"]))
        print("  surf %-12s v %4d t %4d bones %s min %s max %s" % (s["name"], len(P), len(s["tris"]), bi, np.round(P.min(0), 2), np.round(P.max(0), 2)))
    np.savez(os.path.join(B, "old_%s.npz" % os.path.basename(rel)[:-4]),
             **{s["name"]: np.array([v["pos"] for v in s["verts"]]) for s in m["surfaces"]})
