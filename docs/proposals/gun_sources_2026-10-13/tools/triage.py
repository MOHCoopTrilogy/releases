"""Cheap triage of the weapon set: triangles per mesh and the size of the sheet the biggest surface paints from.

Read-only. Reuses the 2026-10-05 weapon_hd inventory (TIK -> surface -> shader -> image, engine-resolved)
and its pak reader; adds triangle counts from the .skd / .skb headers. Weapon list = the tik column of
ads_twohand_2026-10-11/coverage.md. Writes triage.tsv next to this file's parent folder.

    python triage.py
"""
import os, re, sys, json, struct
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WHD = os.path.join(ROOT, "proposals", "weapon_hd_2026-10-05", "tools")
sys.path.insert(0, WHD)
import vfs  # noqa: E402  (read-only pak index)

SKIP_TEX = ("textures/common/", "textures/coop_skins/", "reflection", "env_")


def surf_tris(b):
    """[(surface name, triangles, verts)] from an SKD / SKB blob (header + surface headers only)."""
    ident = b[:4]
    if ident not in (b"SKMD", b"SKL "):
        return None
    nsurf, nbones, ofsb, ofss, ofse = struct.unpack_from("<5i", b, 72)
    out = []
    off = ofss
    for _ in range(nsurf):
        name = b[off + 4:off + 68].split(b"\0")[0].decode("latin1")
        ntri, nv, _sp, ofst, ofsv, ofsc, ofsend, ofsci = struct.unpack_from("<8i", b, off + 68)
        out.append((name, ntri, nv))
        off += ofsend
    return out, nbones


def main():
    cov = open(os.path.join(ROOT, "proposals", "ads_twohand_2026-10-11", "coverage.md"), encoding="utf-8").read()
    rows = []
    cls = "?"
    for ln in cov.splitlines():
        m = re.match(r"^## (\w+|\?)", ln)
        if m:
            cls = m.group(1)
            continue
        c = [x.strip() for x in ln.split("|")]
        if len(c) > 4 and c[3].startswith("`") and c[3].endswith(".tik`"):
            rows.append((cls, c[2], c[3].strip("`").lower()))
    inv = json.load(open(os.path.join(WHD, "inventory.json"), encoding="utf-8"))
    by = {os.path.basename(e["tik"]).lower(): e for e in inv}
    out = ["class\tweapon\ttik\tmesh\tbones\ttris\tsurfaces\tmain_sheet\tpx\tfmt\twon_by\tall_sheets_px"]
    for cls, name, tik in rows:
        e = by.get(tik)
        if not e:
            out.append("\t".join([cls, name, tik, "NOT IN 2026-10-05 INVENTORY"] + [""] * 8))
            continue
        tris = 0
        bones = 0
        per = {}
        meshes = []
        for sk in e["skel"]:
            vp = (e["path"].rstrip("/") + "/" + sk).lower()
            b = vfs.read(vp)
            if b is None:
                meshes.append(sk + "(missing)")
                continue
            r = surf_tris(b)
            if not r:
                meshes.append(sk + "(?)")
                continue
            meshes.append(sk)
            bones = max(bones, r[1])
            for (sn, nt, nv) in r[0]:
                tris += nt
                per[sn.lower()] = per.get(sn.lower(), 0) + nt
        best = None
        allpx = []
        for s in e["surfaces"]:
            for t in s["textures"]:
                if any(k in t["map"].lower() for k in SKIP_TEX) or not t.get("info"):
                    continue
                i = t["info"]
                px = max(i["w"], i["h"])
                key = (t.get("loads") or t["map"])
                if key not in [a[0] for a in allpx]:
                    allpx.append((key, px))
                w = per.get(s["surface"].lower(), 0)
                if best is None or w > best[0]:
                    best = (w, key, "%dx%d" % (i["w"], i["h"]), i["fmt"], i["pak"])
                break
        if best is None:
            best = (0, "-", "-", "-", "-")
        out.append("\t".join([cls, name, tik, "+".join(meshes), str(bones), str(tris), str(len(per)),
                              best[1].replace("textures/models/weapons/", "~/"), best[2], best[3], best[4],
                              ",".join(str(p) for _, p in allpx)]))
    dst = os.path.join(HERE, "..", "triage.tsv")
    open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
