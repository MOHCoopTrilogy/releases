#!/usr/bin/env python3
"""hzmconv - the HZM coop mod's bring-your-own-disc converter (our code only; runs on the PLAYER's PC).

Packaged standalone (PyInstaller one-folder, hzmconv.spec) so players need no Python. Nothing from Frontline or
European Assault is in it: it reads the player's own disc image and writes local paks next to their install.

  hzmconv detect                                    -> JSON list of candidate images (drive roots, Downloads, Desktop, Documents)
  hzmconv verify --game G --image P                 -> JSON {"ok": bool, "why": ...}
  hzmconv add    --game G --image P --mohaa DIR [--home DIR] [--films] [--upscale]
                                                    -> JSON-lines progress, then {"done": ...}

Per-game modules implement:  verify(image) -> (ok, why);  levels() -> [level ids];
                              convert(image, level, out_dir, mohaa, progress, opts) -> [written files]
G = "frontline" (this file's FrontlineGame) or "ea" (European Assault, the EA agent's module hzmconv_ea.py)."""
import argparse
import glob
import json
import os
import string
import struct
import sys

HERE = os.path.dirname(os.path.abspath(getattr(sys, "_MEIPASS", None) or __file__))
sys.path.insert(0, HERE)
TOOLS = os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)), "tools")


def emit(**kv):
    print(json.dumps(kv), flush=True)


# ---------------------------------------------------------------- Frontline
class FrontlineGame:
    TITLE_ID = 0x4541001A           # MOH Frontline, Xbox USA (XBE certificate title id)
    LEVELS = ["1_1"]                 # the pilot; more levels join as they are ported

    @staticmethod
    def verify(image):
        import xdvdfs
        try:
            d = xdvdfs.XDVDFS(image)
            for p, sz, sec, isdir in d.walk():
                if p.lower() == "default.xbe":
                    b = d.read(sec, 0x2000)
                    base = struct.unpack_from("<I", b, 0x104)[0]
                    cert = struct.unpack_from("<I", b, 0x118)[0] - base
                    tid = struct.unpack_from("<I", b, cert + 8)[0]
                    if tid == FrontlineGame.TITLE_ID:
                        return True, "Medal of Honor: Frontline (Xbox, USA)"
                    return False, "not a supported Frontline disc image (title id %08X)" % tid
            return False, "no default.xbe - not an Xbox disc image"
        except Exception as e:
            return False, "cannot read the image: %s" % e

    @staticmethod
    def levels():
        return list(FrontlineGame.LEVELS)

    @staticmethod
    def convert(image, level, out_dir, mohaa, progress, opts):
        import flconvert
        out = os.path.join(out_dir, "zzzz_coop_fl_%s.pk3" % level)
        vgm = os.path.join(TOOLS, "vgmstream", "vgmstream-cli.exe")
        progress(step="convert", level=level)
        flconvert.convert(image, level, out, mirror=True, vgm=vgm if os.path.exists(vgm) else None, mohaa_base=mohaa)
        files = [out]
        if opts.get("films"):
            ff = os.path.join(TOOLS, "ffmpeg", "ffmpeg.exe")
            if os.path.exists(ff):
                try:
                    progress(step="films", level=level)
                    import subprocess
                    mission = int(level.split("_")[0])
                    bp = os.path.join(out_dir, "zzzz_coop_fl_m%d_brief.pk3" % mission)
                    me = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, os.path.abspath(__file__)]
                    subprocess.run(me + ["_flmovies", image, str(mission), bp, "--mohaa", mohaa, "--ffmpeg", ff], check=True)
                    files.append(bp)
                except Exception as e:     # films are optional: a failure never blocks the level
                    progress(step="films", level=level, skipped=str(e))
        if opts.get("upscale"):
            up = os.path.join(TOOLS, "upscaler")
            if os.path.exists(os.path.join(up, "realesrgan-ncnn-vulkan.exe")):
                try:
                    progress(step="upscale", level=level)
                    import flupscale
                    hp = os.path.join(out_dir, "zzzz_fl_hdtex_%s.pk3" % level)
                    flupscale.main(out, level, hp, up)
                    if os.path.exists(hp):
                        files.append(hp)
                except Exception as e:     # optional too
                    progress(step="upscale", level=level, skipped=str(e))
        mk = os.path.join(out_dir, "fl")
        os.makedirs(mk, exist_ok=True)
        with open(os.path.join(mk, "have_%s.cfg" % level), "w", newline="\n") as f:
            f.write('set coop_flHave_%s "1"\n' % level)
        files.append(os.path.join(mk, "have_%s.cfg" % level))
        return files


def game(name):
    if name == "frontline":
        return FrontlineGame
    if name == "ea":
        import hzmconv_ea       # the EA agent's module (same interface)
        return hzmconv_ea
    raise SystemExit("unknown game %r" % name)


def detect():
    roots = ["%s:\\" % c for c in string.ascii_uppercase if os.path.exists("%s:\\" % c)]
    home = os.path.expanduser("~")
    roots += [os.path.join(home, d) for d in ("Downloads", "Desktop", "Documents")]
    found = []
    for r in roots:
        for pat in ("*.iso", "*.xiso", "*.zip"):
            try:
                for p in glob.glob(os.path.join(r, pat)):
                    found.append({"path": p, "size": os.path.getsize(p)})
            except OSError:
                pass
    return found


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "_flmovies":          # internal: the film step re-uses this exe
        import flmovies
        sys.argv = ["flmovies"] + argv[1:]
        return flmovies.main()
    ap = argparse.ArgumentParser(prog="hzmconv")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("detect")
    v = sub.add_parser("verify")
    v.add_argument("--game", required=True)
    v.add_argument("--image", required=True)
    a = sub.add_parser("add")
    a.add_argument("--game", required=True)
    a.add_argument("--image", required=True)
    a.add_argument("--mohaa", required=True)
    a.add_argument("--home", help="where the paks go (default: <mohaa>/maintt)")
    a.add_argument("--films", action="store_true")
    a.add_argument("--upscale", action="store_true")
    a.add_argument("--level", action="append")
    o = ap.parse_args(argv)
    if o.cmd == "detect":
        emit(candidates=detect())
        return 0
    g = game(o.game)
    ok, why = g.verify(o.image)
    if o.cmd == "verify":
        emit(ok=ok, why=why)
        return 0 if ok else 2
    if not ok:
        emit(error=why)
        return 2
    home = o.home or os.path.join(o.mohaa, "maintt")
    written = []
    try:
        for lv in (o.level or g.levels()):
            written += g.convert(o.image, lv, home, o.mohaa, lambda **kv: emit(**kv),
                                 {"films": o.films, "upscale": o.upscale})
    except Exception as e:
        emit(error="conversion failed: %s" % e)
        return 1
    emit(done=True, files=written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
