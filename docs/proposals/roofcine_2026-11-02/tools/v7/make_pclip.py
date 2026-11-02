"""make_pclip.py <spec.json> - append invisible PLAYERCLIP-only brush submodels (no draw surfaces) as script_objects.
spec: {"src","dst","boxes":[{"name","min":[x,y,z],"max":[x,y,z]}], "ent_keys": {"notsolid": "1"}}"""
import os, sys, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bspedit as E
def build(spec):
    b = E.Bsp(open(spec["src"], "rb").read()); sh = b.shaders()
    cands = [i for i, s in enumerate(sh) if s[0] == "textures/common/playerclip" and (s[2] & 0x10000) and not (s[2] & 0x20001)]
    assert cands, "no playerclip-only shader"
    pcs = cands[0]
    plL, bl, sl, mdl = (b.lumps[E.IX[n]] for n in ("planes", "brushes", "brushsides", "models"))
    nsurf = len(b.get("surfaces")) // 108; ents = bytes(b.get("ents")); add = ""
    modelnum = len(mdl) // 40; out = []
    for B in spec["boxes"]:
        mn, mx = B["min"], B["max"]; o = [(mn[i] + mx[i]) / 2 for i in range(3)]; h = [(mx[i] - mn[i]) / 2 for i in range(3)]
        p0 = len(plL) // 16
        for ax in range(3):
            n = [0, 0, 0]; n[ax] = -1; plL.extend(struct.pack("<4f", *n, h[ax]))
            n = [0, 0, 0]; n[ax] = 1; plL.extend(struct.pack("<4f", *n, h[ax]))
        s0 = len(sl) // 12; b0 = len(bl) // 12
        bl.extend(struct.pack("<3i", s0, 6, pcs))
        for k in range(6): sl.extend(struct.pack("<3i", p0 + k, pcs, 0))
        mdl.extend(struct.pack("<6f4i", *[-v for v in h], *h, nsurf, 0, b0, 1))
        keys = [("model", "*%d" % modelnum), ("classname", spec.get("entity_class", "script_object")), ("targetname", B["name"]), ("origin", "%g %g %g" % tuple(o))] + list(spec.get("ent_keys", {}).items())
        add += chr(123) + chr(10) + "".join("\"%s\" \"%s\"" % kv + chr(10) for kv in keys) + chr(125) + chr(10)
        out.append((B["name"], modelnum, o, h)); modelnum += 1
    b.lumps[E.IX["ents"]] = bytearray(ents[:-1] + add.encode("latin1") + b"\x00")
    open(spec["dst"], "wb").write(b.tobytes()); return out
if __name__ == "__main__":
    for r in build(json.load(open(sys.argv[1]))): print(r)
