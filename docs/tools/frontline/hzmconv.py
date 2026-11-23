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
HZMCONV_VERSION = "1.10.91.1"   # .91.1 [v1.10.91] Frontline: Armory change sound = the disc pistol slide rack (ShellBnk stream 36, picked by the user), not the pause-menu click (bug-11463); .89.1 [v1.10.89] disc guns converted from the player's own disc (Frontline 15, European Assault 22: upscaled models, original fire / reload / bolt sounds, own guns pak); EA converter 0.7.49 (sky ceiling so snow and rain fall, the item_drop alias fix, night-to-dawn sky on, blizzard sky key); Frontline 1_3 data; .88.1 [v1.10.88] Frontline: capsule step key (hzm_capsulestep), interrogation-room tunnel crawlable (caps +86, rubble edge carved, north end sealed), Armory pistol cock from the disc (Continue sound) into the mission pak; EA converter 0.7.48 (leader ExplainsPlan clip turned to face the room, held-PPSh hand clips, character light from the disc irradiance probes + bloom share, lightingGrid character shaders, irradiance boxes at full size, zone bloom mix, capsule step key); .87.1 [v1.10.87] Frontline: intact window panes drawn from the disc collision as cells of the level's own window texture (frame bars + glass, static as in the original, bug-11371), Health25 = the disc's medkit case; EA converter 0.7.44 (head-turn scene flags, the disc PPSh held-prop data, closed-mouth jaw rest clip); .86.1 [v1.10.86] Frontline: no edge skirts over drawn ground (Sealed Orders doors and windows, bug-11345), the crunch footstep class plays dirt, nest MG42s on the stock HD turret (user chose B); EA converter 0.7.41 (far ground mist, skyline pull); .85.1 [v1.10.85] Frontline: invisible clips block players and AI but not bullets, footstep surfaces from the disc collision class; EA converter 0.7.40 (dialogue speaker + head turn, squad-objective sends, unstandable objectives moved, footstep surfaces); .84.1 [v1.10.84] Frontline: Sealed Orders disc Panzer IV, MG42, canteen, medkit, field phone (user-approved), see-through foliage cards lose their collision slabs, the shop-front clip sheet kept, flchar bind-rotation offset from the bone count; EA converter 0.7.36 (MMG point and crew heights, crouched-gunner clip); 1_3 groundwork not a listed level; .83.1 [v1.10.83] Frontline: the original sky from the player's disc, mono ambience beds, object meshes over 2000 verts split, smoke sized to the disc sprite; EA converter 0.7.35 (comm-tower charges wait for their group, spawn-point death channels every Nth death); 1_3 groundwork not a listed level; .82.1 [v1.10.82] Frontline: one-shot bank clips registered as alias, not aliascache (sound index table no longer full at load, bug-11266); journal RGB565 page fallback, per-level nav_spacing, extra ammo classes (1_3 groundwork, not a listed level); .81.1 [v1.10.81] Frontline: all 20 disc characters (own models, head shapes, fade copies, upscale), disc cover points, per-record paths, mood timers, particle sizes, journal, careful upscale + CC0 brick/planks; EA converter 0.7.33 (disc locomotion/hit/death/scene/MG clips, talking jaw, MG pole crews, snow Panzer, physics-settled corners, breakables, sounds read by field name, bloom/mix zones, creek mist + glow arc + city skyline, careful upscale, barrel-tile roof); .80.1 [v1.10.80] Frontline: disc particle systems, bombed-house wall piece, area combat lines, disc hedge boxes (upscaled), tree-card hue from the drawn image, water contents, crate roll; EA converter 0.7.30 (all six disc characters upscaled+smoothed, cut-out pass: wire/grass/wheat/decals, creek mist box, distant fires pulled in, 3D winter trees + extra trees, CC0 snow, breakable tombstones, path islands dropped, door clearances, sky 2048); .79.1 [v1.10.79] Frontline: house/bomber at real speed, objective 2 texts, the two German combat cues, trigger message fields; EA converter 0.7.23 (pose points, eachar character models - the woman held back in script); .78.1 .78.1 [v1.10.78] Frontline converter 0.6.0 rounds 9-14 (jeep ambush data, wall breach meshes, mvd key rate from the header, light gain, traced fog and sky, hedge skirts, shader-name dot fix, inverse quaternions, hint text ids, axis record numbers) + EA converter 0.7.21 (MG squads, loudspeakers, scene cue tables, sky box sides, fog, path-node bridges, facings); .77.1 .77.1 [flfix2] Frontline converter 0.6.0 - the world is no longer mirrored (signs read the right way round, bug-10965), build marker in the data script; .76.1 [eapolish] EA converter 0.7.5 - models lit by the level's own night light (light grid from the baked vertex colours); .73.14 [eapolish] EA converter 0.7.4 - night light matched to the disc (world gain divided out), crater rims, silent partisan bark aliases; .73.12 [eapolish] EA converter 0.7.2 - particle sizes are half extents; .73.11 [eapolish] EA converter 0.7.1 - the level's own fog record (night), particle width/height end scales; .73.10 [eapolish] (above flpolish .73.8, .73.9 left free for it): EA converter 0.7.0 - the level's own particle systems (eafx); .73.7 [eapolish] (above flpolish .73.6): EA converter 0.6.1 - the score's own event -> section table (eamusic), original collision 1:1; .73.5 [eapolish] EA converter 0.6.0 - the original voice lines (eavoice); .73.4 [eapolish] (above flpolish .73.3): EA converter 0.5.0 - destroyed variants, hinged gates, relit smart objects; .73.3 [eapolish]: EA converter 0.3.0 - real object-DB names (eadb) + the mission logic tables (eavm) (bug-eap-dbnames)
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
            # [armory change sound 2026-11-22] Frontline's Continue pistol cock (menu_sound_files below) rides the mission pak
            # every Frontline owner gets; the marker switches the Armory to it (autoexec sets the apply.wav default first)
            arm = {}
            try:
                import flcore
                import shutil
                import tempfile
                td = tempfile.mkdtemp(prefix="flarm_")
                try:
                    arm = menu_sound_files(flcore.Disc(image), td, vgm if os.path.exists(vgm) else None)
                finally:
                    shutil.rmtree(td, ignore_errors=True)
            except Exception as e:     # optional: the mod's own Armory sound stays
                progress(step="armory_sound", level=level, skipped=str(e))
            for n, b in arm.items():
                add_marker(tmp, n, b)
            add_marker(tmp, "fl/have_%s.cfg" % level, 'set coop_flHave_%s "1"\nset coop_flHave "1"\n' % level
                       + (MENU_SET if arm else ""))
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
                    flupscale.main(out, level, hp, up, progress=lambda **kv: progress(level=level, **kv))
                    if os.path.exists(hp):
                        files.append(hp)
                    # [flchar] the characters' textures: the European Assault character rules (flcharup.py)
                    import flcharup
                    cp = os.path.join(out_dir, "zzzz_fl_hdchr_%s.pk3" % level)
                    flcharup.main(out, level, cp, up)
                    if os.path.exists(cp):
                        files.append(cp)
                    # [flprops] the disc props' textures (flpropsup.py: ESRGAN / CC0 grain), only if any were built
                    import flpropsup
                    pp = os.path.join(out_dir, "zzzz_fl_hdprops_%s.pk3" % level)
                    flpropsup.main(out, level, pp, up)
                    if os.path.exists(pp):
                        files.append(pp)
                except Exception as e:     # optional too
                    progress(step="upscale", level=level, skipped=str(e))
        return files

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


# ------------------------------------------------------------------ the Armory change sound (user 2026-11-22)
# Frontline's own pistol slide rack: ShellBnk.abk stream 36 (vgmstream index), 0.258 s, mono 44.1 kHz, the shell bank's sound
# the user remembers from selecting "continue game" (user 2026-11-23, picking by ear from all 37 decoded ShellBnk streams:
# "Sound 36 is the slide noise"). Shipped as decoded, alone, no gain change.
# bug-11463: 1.10.88-1.10.90 shipped 1_1 ScrBnk stream 1 (0.157 s), the PAUSE menu's open/CONTINUE click (ref_xemu SDL
# disk-audio capture 2026-11-23: ncc 0.70 / 0.62 over 4 presses each), which the user heard as "a typewriter click". A 1:1 mix of
# ShellBnk streams 2 + 30 (what A on a main-menu carousel item plays; ncc 0.93 on the first press) was tried next and rejected by
# ear: not the slide either. Where stream 36 plays in the original menus was not recorded (the Xbox main menu has no "Continue
# Game" item). FrontlineGame.convert puts the clip into THIS player's Frontline mission pak (zzzz_coop_fl_<l>.pk3, built for every
# Frontline owner) as MENU_WAV, and MENU_SET into the pak's own fl/have_<l>.cfg marker: autoexec.cfg sets the mod default
# (apply.wav) and then execs the marker, and the Armory's ui/coop_armory_snd.cfg is `vstr coop_armorySnd`. No file overrides
# another, so pak load order cannot decide it.
MENU_BANK, MENU_STREAM = "DATA/SHELL/ShellBnk.abk", 36
MENU_WAV = "sound/menu/coop_fl_cock.wav"
MENU_SET = 'set coop_armorySnd "play %s"\n' % MENU_WAV


def menu_sound_files(disc, tmp, vgm):
    """-> {MENU_WAV: wav bytes}; {} without vgmstream or the bank (the mod's own Armory sound then plays)"""
    import flaudio
    if not vgm or not os.path.exists(vgm):
        return {}
    try:
        ab = disc.read(MENU_BANK)
    except Exception:
        return {}
    bnk, ents = flaudio.bnk_entries(ab)
    if not bnk or MENU_STREAM not in {e["stream"] for e in ents}:
        return {}
    src = os.path.join(tmp, "menu.bnk")
    open(src, "wb").write(bnk)
    dst = os.path.join(tmp, "menu_cock.wav")
    if not flaudio.vgm_decode(vgm, src, dst, MENU_STREAM):
        return {}
    return {MENU_WAV: flaudio.wav_mono(dst)}     # the client refuses stereo effect wavs (the disc clip is mono: bytes as decoded)


def add_marker(pk3, name, text):
    """The detection marker (INTEGRATION section 1) as an entry of the level pak itself: autoexec.cfg execs it, so it
    exists exactly as long as the pak does."""
    import zipfile
    with zipfile.ZipFile(pk3, "a", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, text if isinstance(text, bytes) else text.encode("ascii"))


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
    # [flfix2 2026-11-12, user: "Yes for everyone"] the texture upscale runs by default; --no-upscale turns it off
    # (--upscale is still accepted). It skips itself without a usable Vulkan GPU and never fails a conversion.
    a.add_argument("--upscale", action="store_true", default=True)
    a.add_argument("--no-upscale", dest="upscale", action="store_false")
    a.add_argument("--level", action="append")
    # [discguns] the disc's guns (own pak) are converted with every add; --no-guns skips them
    a.add_argument("--no-guns", dest="guns", action="store_false", default=True)
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
            if o.guns and hasattr(g, "convert_guns"):
                written += g.convert_guns(img.path, home, o.mohaa, lambda **kv: emit(**kv), {"upscale": o.upscale})
        except Exception as e:
            emit(error="conversion failed: %s" % e)
            return 1
    emit(done=True, files=written, version=HZMCONV_VERSION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
