"""[fg42hd] the fire clip's tag_eject (the brass spawn) onto the new mesh's ejection port: the right-side face centre of the source's
Ejection_port, through fglib. Edits the adopted copy in the wpnfix sources (both FG 42s fire with coop_fg42_fire.skc).
    python eject_tag.py"""
import os, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import fglib as L, skcread as R, gen_wpnfix_pak as W
p = os.path.join(W.SRC, "models", "weapons", "fg42", "coop_fg42_fire.skc")
b = bytearray(open(p, "rb").read())
ch, fr = R.read(bytes(b))
ci = ch.index("tag_eject pos")
d = np.load(os.path.join(L.BUILD, "tris.npz")); A, obj = d["corners"], d["obj"]
P = A[obj == "Ejection_port"][:, :, :3].reshape(-1, 3)
new = L.to_raw(P[P[:, 0] > 0.005].mean(0))
nf = struct.unpack_from("<i", b, 44)[0]
for f in range(nf):
    ov = struct.unpack_from("<i", b, 48 + 48 * f + 44)[0]
    struct.pack_into("<4f", b, ov + 16 * ci, float(new[0]), float(new[1]), float(new[2]), 0.0)
open(p, "wb").write(bytes(b))
print("tag_eject pos", np.round(fr[0][ci][:3], 3), "->", np.round(new, 3), "in", nf, "frames")
