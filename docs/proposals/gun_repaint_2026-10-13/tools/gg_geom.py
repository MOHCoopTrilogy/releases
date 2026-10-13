"""Grease gun geometry facts for the painter: the receiver tube's axis and radius profile along x, and for the
stretched islands the 3D direction in which the sheet is coarse (few texels per unit).
    python gg_geom.py"""
import numpy as np
import rplib as L
import gg_probe as G


def main():
    S = L.load_skd(G.SKD)
    b = S["bool_mesh"]
    vi = np.unique(b["tris"][np.isin(b["isl"], [3, 4])])
    P = b["pos"][vi]
    print("tube+barrel verts", len(P))
    for x0 in np.arange(-4, 51, 2.0):
        m = (P[:, 0] >= x0) & (P[:, 0] < x0 + 2.0)
        if not m.any():
            continue
        q = P[m]
        cy = (q[:, 1].min() + q[:, 1].max()) / 2; cz = (q[:, 2].min() + q[:, 2].max()) / 2
        print("x %5.1f n %3d  y %.2f..%.2f  z %.2f..%.2f  centre (%.2f, %.2f)  r %.2f" % (
            x0, m.sum(), q[:, 1].min(), q[:, 1].max(), q[:, 2].min(), q[:, 2].max(), cy, cz,
            max(np.ptp(q[:, 1]), np.ptp(q[:, 2])) / 2))
    xs = np.unique(np.round(P[:, 0], 1))
    print("x stations:", xs.tolist())
    for name, k in (("Mesh_MultiAttached", 4), ("Clip", 0), ("skin1", 0), ("skin1", 1), ("Mesh_MultiAttached", 5),
                    ("Mesh_MultiAttached4", 0), ("bool_mesh", 3)):
        s = S[name]
        m = s["isl"] == k
        T = s["tris"][m]
        Pt = s["pos"][T]; U = s["uv"][T] * 2048
        dirs = []; wts = []
        for i in range(len(T)):
            e1 = Pt[i, 1] - Pt[i, 0]; e2 = Pt[i, 2] - Pt[i, 0]
            A = np.stack([e1, e2], 1)                       # 3x2: (a,b) -> 3D
            Bm = np.stack([U[i, 1] - U[i, 0], U[i, 2] - U[i, 0]], 1)   # 2x2: (a,b) -> uv
            if abs(np.linalg.det(Bm)) < 1e-6:
                continue
            M = A @ np.linalg.inv(Bm)                       # uv px -> 3D
            u, sv, vt = np.linalg.svd(M, full_matrices=False)
            dirs.append(u[:, 0] * np.sign(u[np.argmax(np.abs(u[:, 0])), 0])); wts.append(np.linalg.norm(np.cross(e1, e2)))
            # u[:,0] = the 3D direction that gets the FEWEST texels per unit (largest units per px)
        d = np.array(dirs); w = np.array(wts)
        ax = np.abs(d).T @ w / w.sum()
        nz = np.abs(s["nrm"][np.unique(T)]).mean(0)
        print("%s%d: coarse axis |x y z| weights %s   mean |normal| %s" % (G.LET[name], k, ax.round(2), nz.round(2)))


if __name__ == "__main__":
    main()
