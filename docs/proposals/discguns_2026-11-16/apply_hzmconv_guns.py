"""[discguns] wire the Frontline disc-guns stage (docs/tools/frontline/flguns.py) into hzmconv - the exact edits of
flguns_hzmconv.patch, applied in binary mode with a count assert per edit (hzmconv.py is LF, hzmconv.spec is CRLF;
TRAPS T2: never `git apply` these). Idempotent: an already-applied file is reported and left alone.

    python -I docs/proposals/discguns_2026-11-16/apply_hzmconv_guns.py [--check]

After applying: raise HZMCONV_VERSION (conv_guard.py - the new flgun*.py / discguns_*.json files already change the
converter digest), rebuild hzmconv (build_hzmconv.py), and re-convert the live install (no updater there)."""
import os
import sys

FL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools", "frontline")

PY = [
    (b'''        return files


def add_marker(pk3, name, text):''',
     b'''        return files

    @staticmethod
    def convert_guns(image, out_dir, mohaa, progress, opts):
        """[discguns] the disc's first-person guns as cosmetic variants (flguns.py): ONE pak of its own,
        zzzzzzzzzzzzzzzzzzzz_byo_guns_fl.pk3, next to the level paks (which it never touches). Its
        scripts/hzm_adssights_byo_fl.txt is also the ownership marker the engine reads (Com_ByoTokens -> "guns_fl").
        Optional like the films: a failure never fails the conversion."""
        try:
            import flguns
            progress(step="guns")
            vgm = os.path.join(TOOLS, "vgmstream", "vgmstream-cli.exe")
            up = os.path.join(TOOLS, "upscaler", "realesrgan-ncnn-vulkan.exe")
            return flguns.convert(image, out_dir, mohaa, progress,
                                  {"upscale": opts.get("upscale", True), "vgm": vgm if os.path.exists(vgm) else None,
                                   "esrgan": up if os.path.exists(up) else None})
        except Exception as e:
            progress(step="guns", skipped=str(e))
            return []


def add_marker(pk3, name, text):'''),
    (b'''    a.add_argument("--level", action="append")
''',
     b'''    a.add_argument("--level", action="append")
    # [discguns] the disc's guns (own pak) are converted with every add; --no-guns skips them
    a.add_argument("--no-guns", dest="guns", action="store_false", default=True)
'''),
    (b'''                written += g.convert(img.path, lv, home, o.mohaa, lambda **kv: emit(**kv),
                                     {"films": o.films, "upscale": o.upscale})
''',
     b'''                written += g.convert(img.path, lv, home, o.mohaa, lambda **kv: emit(**kv),
                                     {"films": o.films, "upscale": o.upscale})
            if o.guns and hasattr(g, "convert_guns"):
                written += g.convert_guns(img.path, home, o.mohaa, lambda **kv: emit(**kv), {"upscale": o.upscale})
'''),
]
SPEC = [
    (b'''        "flmovies", "flupscale", "flhd", "flchar", "flcharup", "flcover", "flanim", "flanimconv", "mohskel"]\n''',
     b'''        "flmovies", "flupscale", "flhd", "flchar", "flcharup", "flcover", "flanim", "flanimconv", "mohskel"]\n'''
     b'''# [discguns] the disc guns stage (flguns.py and its helpers) + pickle (flgunskc14's Huffman tree cache)\n'''
     b'''mods += ["flguns", "flgunfit", "flgunsight", "flgunup", "flgunvfs", "flgungeo", "flgunskd", "flgunskc14", "pickle"]\n'''),
    (b'''("fl_charprotect.json", "."), ("hd", "hd")],''',
     b'''("fl_charprotect.json", "."), ("hd", "hd"),\n                    ("discguns_sights.json", "."), ("discguns_baserows.json", "."), ("flgun_msg_hdata.txt", ".")],'''),
]


def apply(path, edits, check):
    s = open(path, "rb").read()
    nl = b"\r\n" if b"\r\n" in s else b"\n"
    done = 0
    for a, b in edits:
        a, b = a.replace(b"\n", nl), b.replace(b"\n", nl)
        if s.count(b) == 1 and s.count(a) == (1 if a in b else 0):
            done += 1
            continue
        assert s.count(a) == 1, "%s: anchor not found exactly once: %r" % (path, a[:80])
        s = s.replace(a, b)
    if done == len(edits):
        print("%s: already applied" % os.path.basename(path))
        return
    if check:
        print("%s: would apply %d edit(s)" % (os.path.basename(path), len(edits) - done))
        return
    open(path, "wb").write(s)
    print("%s: applied %d edit(s) (%s)" % (os.path.basename(path), len(edits) - done, "CRLF" if nl == b"\r\n" else "LF"))


if __name__ == "__main__":
    chk = "--check" in sys.argv
    for f in ("flguns.py", "flgunfit.py", "flgunsight.py", "flgunup.py", "flgunvfs.py", "flgungeo.py", "flgunskd.py",
              "flgunskc14.py", "discguns_sights.json", "discguns_baserows.json", "flgun_msg_hdata.txt"):
        assert os.path.exists(os.path.join(FL, f)), "missing docs/tools/frontline/" + f
    apply(os.path.join(FL, "hzmconv.py"), PY, chk)
    apply(os.path.join(FL, "hzmconv.spec"), SPEC, chk)
