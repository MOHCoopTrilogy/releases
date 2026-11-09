"""The scoped FG 42 on the new body: adopt models/weapons/FG42.tik into the wpnfix sources (its winner is the scopeglass pak), point it
at coop_fg42hd.skd (build_mesh.py with FG_SCOPE=1: Shorty_Digitan's body without the diopter + the in-house ZFG 42 of scope_mesh.py),
and pin the new skd in the wpnfix manifest. The lens keeps coop_scope_glass_blue; the handle keeps the shipped surface.
    python stage_scoped.py
"""
import json, os, re, shutil, sys
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import gen_wpnfix_pak as W

HERE = os.path.dirname(os.path.abspath(__file__))
REL_TIK = "models/weapons/FG42.tik"
REL_SKD = "models/weapons/fg42/coop_fg42hd.skd"
NOTE = ("// HZM coop [v1.10.66 fg42hd] the body is Shorty_Digitan's FG42 (Sketchfab d699ac259bd74f70a51125a7e4320f4b, CC BY 4.0, modified:\n"
        "// reduced, re-rigged on DaRKaNGeL's FG42 bones, PBR baked into one 2048 sheet) without its diopter and front sight; the scope\n"
        "// is the SHIPPED one (coop_fg42.skd), unchanged on the same bone, so the scope rows and the lens view stay as they were.\n")
SURF = ("surface fg42hd*   shader coop_fg42hd\n"
        "surface fg42clip  shader coop_fg42hd\n"
        "surface fg42scope shader fg42\t// the SHIPPED scope (coop_fg42.skd through v1.10.65) on its own sheet\n"
        "surface fg42lens  shader coop_scope_glass_blue\n"
        "surface coop_handle shader fg42\t// HZM coop [ads heavy] the charging handle (fg42handle.py)\n")


def main():
    man = W.load_manifest()
    tik = os.path.join(W.SRC, *REL_TIK.split("/"))
    if REL_TIK not in man:
        c = W.carriers(REL_TIK)
        os.makedirs(os.path.dirname(tik), exist_ok=True)
        open(tik, "wb").write(c[-1][1])
        import hashlib
        man[REL_TIK] = {"base": c[-1][0], "base_md5": hashlib.md5(c[-1][1]).hexdigest()}
    b = W.carriers(REL_TIK)[-1][1].decode("latin-1")          # always re-derive from the base: the stage is idempotent
    nl = "\r\n" if "\r\n" in b else "\n"
    t = b.replace("\r\n", "\n")
    assert t.count("skelmodel coop_fg42.skd") == 1
    t = t.replace("skelmodel coop_fg42.skd", "skelmodel coop_fg42hd.skd")
    out, done = [], False
    for ln in t.split("\n"):
        if re.match(r"\s*surface\s+(fg42base|fg42barrel|fg42clip|fg42lens|coop_handle|fg42scope|fg42cup|scopeb|scopeg)\s+shader", ln):
            if not done:
                ind = re.match(r"(\s*)", ln).group(1)
                out += [ind + x for x in (NOTE + SURF).rstrip("\n").split("\n")]
                done = True
            continue
        out.append(ln)
    assert done
    open(tik, "wb").write(nl.join(out).encode("latin-1"))
    # the sheet gained the scope's Scope / Rubber tiles (atlas.py; every older tile byte-identical): ship the new one
    shutil.copyfile(os.path.join(HERE, "..", "build", "fg42hd.jpg"),
                    os.path.join(W.SRC, "textures", "models", "weapons", "coop_fg42hd", "fg42hd.jpg"))
    dst = os.path.join(W.SRC, *REL_SKD.split("/"))
    shutil.copyfile(os.path.join(HERE, "..", "ship", *REL_SKD.split("/")), dst)
    assert not W.carriers(REL_SKD)
    man[REL_SKD] = {"new": True}
    txt = json.dumps(man, indent=2, sort_keys=True) + "\n"
    for _ in range(40):                        # Windows sometimes holds the manifest for a moment (Errno 22): retry
        try:
            with open(W.MANIFEST, "w", encoding="utf-8", newline="\n") as f:
                f.write(txt)
            break
        except OSError:
            import time; time.sleep(0.5)
    else:
        raise SystemExit("could not write the manifest")
    print("ok", man[REL_TIK])


if __name__ == "__main__":
    main()
