#!/usr/bin/env python3
"""hzmconv_ea - the European Assault module of the shared BYO converter hzmconv (Frontline agent's hzmconv.py,
INTEGRATION.md section 10). Our code only; runs on the PLAYER's PC and reads their own EA disc image.

Interface (same as hzmconv.FrontlineGame):
  verify(image) -> (ok, why)
  levels()      -> [level ids]
  convert(image, level, out_dir, mohaa, progress, opts) -> [written files]
Writes: zzzz_coop_ea_<l>.pk3 (map, textures, shaders, data script, alias bridge), optional zzzz_ea_hdtex_<l>.pk3
(local upscale), optional zzzz_coop_ea_<l>_film.pk3 (intro film as RoQ), and the marker ea/have_<l>.cfg.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(getattr(sys, "_MEIPASS", None) or __file__))
sys.path.insert(0, HERE)
TOOLS = os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)), "tools")

TITLE_ID = 0x4541005E        # MOH European Assault, Xbox USA (XBE certificate title id, region 1, version 1)
LEVELS = ["1_11"]             # the pilot (RUS1 The Road to Stalingrad); more levels join as they are ported
FILMS = {"1_11": "DATA/SHARED/MOVIES/RusMIntr.vp6"}     # mission intro played before the level


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
                if tid == TITLE_ID:
                    return True, "Medal of Honor: European Assault (Xbox, USA)"
                return False, "not a supported European Assault disc image (title id %08X)" % tid
        return False, "no default.xbe - not an Xbox disc image"
    except Exception as e:
        return False, "cannot read the image: %s" % e


def levels():
    return list(LEVELS)


def convert(image, level, out_dir, mohaa, progress, opts):
    import flconvert
    out = os.path.join(out_dir, "zzzz_coop_ea_%s.pk3" % level)
    progress(step="convert", game="ea", level=level)
    vgm = os.path.join(TOOLS, "vgmstream", "vgmstream-cli.exe")      # built with mpg123 (EALayer3 music)
    # [v1.10.69, the Frontline recipe] temp name, renamed only when complete; the marker ea/have_<l>.cfg goes INSIDE
    # the pak (autoexec.cfg execs it), so deleting the pak also hides the mission
    hzmconv = sys.modules.get("hzmconv") or sys.modules["__main__"]   # add_marker / drop_loose_marker live there
    tmp = out + ".tmp"
    try:
        flconvert.convert(image, level, tmp, game="ea", mohaa_base=mohaa, vgm=vgm if os.path.exists(vgm) else None)
        hzmconv.add_marker(tmp, "ea/have_%s.cfg" % level, 'set coop_eaHave_%s "1"\nset coop_eaHave "1"\n' % level)
        os.replace(tmp, out)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    hzmconv.drop_loose_marker(out_dir, "ea", level)
    files = [out]
    if opts.get("films") and level in FILMS:
        ff = os.path.join(TOOLS, "ffmpeg", "ffmpeg.exe")
        if os.path.exists(ff):
            try:
                progress(step="films", game="ea", level=level)
                import eamovies
                fp = os.path.join(out_dir, "zzzz_coop_ea_%s_film.pk3" % level)
                eamovies.build(image, FILMS[level], level, fp, ff, mohaa)
                files.append(fp)
            except Exception as e:     # films are optional: a failure never blocks the level
                progress(step="films", game="ea", level=level, skipped=str(e))
        else:
            progress(step="films", game="ea", level=level, skipped="no ffmpeg")
    if opts.get("upscale"):
        up = os.path.join(TOOLS, "upscaler")
        if os.path.exists(os.path.join(up, "realesrgan-ncnn-vulkan.exe")):
            try:
                progress(step="upscale", game="ea", level=level)
                os.environ["HZM_GAME"] = "ea"
                import importlib
                import flupscale
                importlib.reload(flupscale)          # GAME is read at import
                hp = os.path.join(out_dir, "zzzz_ea_hdtex_%s.pk3" % level)
                flupscale.main(out, level, hp, up)
                if os.path.exists(hp):
                    files.append(hp)
            except Exception as e:     # optional too
                progress(step="upscale", game="ea", level=level, skipped=str(e))
    return files
