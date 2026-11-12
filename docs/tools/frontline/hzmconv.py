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
# [v1.10.69] the converter's own version. Bump it whenever a change alters what a conversion writes: the updater
# (updater.ps1 BYO RE-CONVERT) re-converts every remembered disc silently when this differs from the version that
# wrote the player's paks (maintt\byo_converted.txt). Unchanged = no work at all.
HZMCONV_VERSION = "1.10.78.1"   # .78.1 [v1.10.78] Frontline converter 0.6.0 rounds 9-14 (jeep ambush data, wall breach meshes, mvd key rate from the header, light gain, traced fog and sky, hedge skirts, shader-name dot fix, inverse quaternions, hint text ids, axis record numbers) + EA converter 0.7.21 (MG squads, loudspeakers, scene cue tables, sky box sides, fog, path-node bridges, facings); .77.1 .77.1 [flfix2] Frontline converter 0.6.0 - the world is no longer mirrored (signs read the right way round, bug-10965), build marker in the data script; .76.1 [eapolish] EA converter 0.7.5 - models lit by the level's own night light (light grid from the baked vertex colours); .73.14 [eapolish] EA converter 0.7.4 - night light matched to the disc (world gain divided out), crater rims, silent partisan bark aliases; .73.12 [eapolish] EA converter 0.7.2 - particle sizes are half extents; .73.11 [eapolish] EA converter 0.7.1 - the level's own fog record (night), particle width/height end scales; .73.10 [eapolish] (above flpolish .73.8, .73.9 left free for it): EA converter 0.7.0 - the level's own particle systems (eafx); .73.7 [eapolish] (above flpolish .73.6): EA converter 0.6.1 - the score's own event -> section table (eamusic), original collision 1:1; .73.5 [eapolish] EA converter 0.6.0 - the original voice lines (eavoice); .73.4 [eapolish] (above flpolish .73.3): EA converter 0.5.0 - destroyed variants, hinged gates, relit smart objects; .73.3 [eapolish]: EA converter 0.3.0 - real object-DB names (eadb) + the mission logic tables (eavm) (bug-eap-dbnames)
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
        # [v1.10.68] written to a temp name and renamed only when complete (a failed run never leaves a half pak, and
        # the previous good pak survives it); the marker cfg goes INSIDE the pak, so deleting the pak also hides the map
        tmp = out + ".tmp"
        try:
            flconvert.convert(image, level, tmp, mirror=False, vgm=vgm if os.path.exists(vgm) else None, mohaa_base=mohaa)
            add_marker(tmp, "fl/have_%s.cfg" % level, 'set coop_flHave_%s "1"\nset coop_flHave "1"\n' % level)
            os.replace(tmp, out)
            # [flfix2 bug-10969] the engine caches the AI path graph it built for this map name in <home>/maps/<map>.pth;
            # one left from an older conversion is reused silently (soldiers stand still). A new pak always drops it.
            try:
                os.remove(os.path.join(out_dir, "maps", "coop_fl_%s.pth" % level))
            except OSError:
                pass
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        drop_loose_marker(out_dir, "fl", level)
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
        return files


def add_marker(pk3, name, text):
    """The detection marker (INTEGRATION section 1) as an entry of the level pak itself: autoexec.cfg execs it, so it
    exists exactly as long as the pak does."""
    import zipfile
    with zipfile.ZipFile(pk3, "a", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, text.encode("ascii"))


def drop_loose_marker(out_dir, sub, level):
    """Earlier converter builds wrote the marker loose (maintt/<sub>/have_<l>.cfg); a loose copy would keep the map
    listed after its pak is deleted, so it goes once the pak carries its own."""
    p = os.path.join(out_dir, sub, "have_%s.cfg" % level)
    try:
        if os.path.isfile(p):
            os.remove(p)
            os.rmdir(os.path.dirname(p))
    except OSError:
        pass


class OpenImage:
    """A disc image path, or a .zip holding one: a zip member is streamed ONCE to a temp file (deflate cannot
    seek), next to `near` and only if that drive has room; the temp copy is always deleted afterwards."""

    def __init__(self, path, near=None, progress=None):
        self.path, self.tmp = path, None
        if path.lower().endswith(".zip"):
            import shutil
            import tempfile
            import zipfile
            z = zipfile.ZipFile(path)
            members = [i for i in z.infolist() if i.filename.lower().endswith((".iso", ".xiso"))]
            if not members:
                raise RuntimeError("the zip holds no .iso/.xiso image")
            m = max(members, key=lambda i: i.file_size)
            base = near if near and os.path.isdir(near) else tempfile.gettempdir()
            if shutil.disk_usage(base).free < m.file_size + (512 << 20):
                raise RuntimeError("not enough free space to unpack the image (%.1f GB needed)" % (m.file_size / 2 ** 30))
            fd, self.tmp = tempfile.mkstemp(prefix="hzmconv_", suffix=".iso", dir=base)
            os.close(fd)
            if progress:
                progress(step="unpack", size=m.file_size)
            with z.open(m) as src, open(self.tmp, "wb") as dst:
                shutil.copyfileobj(src, dst, 8 << 20)
            self.path = self.tmp

    def close(self):
        if self.tmp and os.path.exists(self.tmp):
            os.remove(self.tmp)
        self.tmp = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _ea_modules_first():
    """European Assault ships its own copies of the shared fl*.py modules (docs/tools/ea, bundled as _internal/ea):
    they changed for EA, and a Frontline convert with them is not byte-identical, so the two sets never mix. One
    process converts one game, and nothing from the Frontline set is imported before this runs; a path finder at the
    front of sys.meta_path makes the EA folder win over PyInstaller's frozen (Frontline) modules."""
    import importlib.machinery
    for d in [os.path.join(b, "ea") for b in (getattr(sys, "_MEIPASS", ""), HERE, os.path.dirname(HERE)) if b]:
        if os.path.isfile(os.path.join(d, "hzmconv_ea.py")):
            class _EAFinder:
                @staticmethod
                def find_spec(fullname, path=None, target=None):
                    if "." in fullname or fullname == "hzmconv":
                        return None
                    return importlib.machinery.PathFinder.find_spec(fullname, [d])
            sys.meta_path.insert(0, _EAFinder)
            sys.path.insert(0, d)
            return d
    raise ImportError("no European Assault modules")


def game(name):
    if name == "frontline":
        return FrontlineGame
    if name == "ea":
        try:
            _ea_modules_first()
            import hzmconv_ea   # the EA agent's module (same interface)
        except ImportError as e:
            emit(error="European Assault support is not in this converter build yet (%s)" % e)
            raise SystemExit(3)
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
    sub.add_parser("version")
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
    if o.cmd == "version":
        emit(version=HZMCONV_VERSION, games=["frontline", "ea"])
        return 0
    if o.cmd == "detect":
        emit(candidates=detect())
        return 0
    g = game(o.game)
    home = (o.home or os.path.join(o.mohaa, "maintt")) if o.cmd == "add" else None
    try:
        img = OpenImage(o.image, near=home, progress=lambda **kv: emit(**kv))
    except Exception as e:
        emit(ok=False, error=str(e))
        return 2
    with img:
        ok, why = g.verify(img.path)
        if o.cmd == "verify":
            emit(ok=ok, why=why)
            return 0 if ok else 2
        if not ok:
            emit(error=why)
            return 2
        written = []
        try:
            for lv in (o.level or g.levels()):
                written += g.convert(img.path, lv, home, o.mohaa, lambda **kv: emit(**kv),
                                     {"films": o.films, "upscale": o.upscale})
        except Exception as e:
            emit(error="conversion failed: %s" % e)
            return 1
    emit(done=True, files=written, version=HZMCONV_VERSION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
