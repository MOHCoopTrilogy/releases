"""Point the adopted FG 42 Irons tik (wpnfix sources) at the new mesh, add its shader, pin the new files in the wpnfix manifest.
    python stage_irons.py
"""
import io, json, os, re, sys
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import gen_wpnfix_pak as W

SRC = W.SRC
TIK = os.path.join(SRC, "models", "weapons", "coop_fg42_irons.tik")
SH = os.path.join(SRC, "scripts", "coop_wpnfix.shader")
NOTE = ("// HZM coop [v1.10.66 fg42hd] the mesh is Shorty_Digitan's FG42 (Sketchfab d699ac259bd74f70a51125a7e4320f4b, CC BY 4.0,\n"
        "// modified: reduced to 5.4k triangles, re-rigged on DaRKaNGeL's FG42 bones, PBR baked into one 2048 sheet), fitted to the shipped\n"
        "// gun (docs/proposals/fg42hd_2026-11-08). Same bones, same clips; the magazine is `fg42clip`, the handle the shipped `coop_handle`.\n")
SURF = ("surface fg42hd*   shader coop_fg42hd\n"
        "surface fg42clip  shader coop_fg42hd\n"
        "surface coop_handle shader fg42\t// HZM coop [ads heavy] the charging handle (fg42handle.py)\n")
SHADER = """
// [v1.10.66 fg42hd] the FG 42 Irons' new sheet: Shorty_Digitan's FG42 (CC BY 4.0, modified), PBR baked to one diffuse
coop_fg42hd
{
	qer_editorimage textures/models/weapons/coop_fg42hd/fg42hd.jpg
	{
		map textures/models/weapons/coop_fg42hd/fg42hd.jpg
		rgbGen lightingSpherical
	}
}
"""


def main():
    b = open(TIK, "rb").read().decode("latin-1")
    nl = "\r\n" if "\r\n" in b else "\n"
    t = b.replace("\r\n", "\n")
    assert t.count("skelmodel coop_fg42_irons.skd") == 1
    t = t.replace("skelmodel coop_fg42_irons.skd", "skelmodel coop_fg42hd_irons.skd")
    lines = t.split("\n")
    out, done = [], False
    for ln in lines:
        if re.match(r"\s*surface\s+(fg42base|fg42barrel|fg42clip|coop_sight|coop_handle)\s+shader", ln):
            if not done:
                ind = re.match(r"(\s*)", ln).group(1)
                out += [ind + x for x in (NOTE + SURF).rstrip("\n").split("\n")]
                done = True
            continue
        out.append(ln)
    assert done
    open(TIK, "wb").write(nl.join(out).replace("\n", nl).encode("latin-1") if nl == "\n" else "\r\n".join(out).encode("latin-1"))
    s = open(SH, encoding="latin-1").read()
    if "coop_fg42hd\n{" not in s.replace("\r\n", "\n"):
        open(SH, "a", encoding="latin-1", newline="").write(SHADER.replace("\n", "\r\n" if "\r\n" in s else "\n"))
    man = W.load_manifest()
    for rel in ("models/weapons/fg42/coop_fg42hd_irons.skd", "textures/models/weapons/coop_fg42hd/fg42hd.jpg"):
        assert not W.carriers(rel)
        man[rel] = {"new": True}
    open(W.MANIFEST, "w", encoding="utf-8", newline="\n").write(json.dumps(man, indent=2, sort_keys=True) + "\n")
    print("ok")


if __name__ == "__main__":
    main()
