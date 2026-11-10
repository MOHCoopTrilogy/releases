#!/usr/bin/env python3
"""European Assault mission-intro film -> a local pak the MOHAA engine plays (Frontline's flmovies.py recipe).
Our own code; runs on the PLAYER's PC.

EA's films are DATA/SHARED/MOVIES/<name>.vp6: EA 'SCHl'/'MVhd' chunks around VP6 640x448 29.97 fps video plus EA
ADPCM R2 stereo 44.1 kHz audio (ffmpeg's electronicarts demuxer and vp6 decoder read them; both LGPL). The engine
plays id RoQ through the stock briefing path (playmovie / cinematic); its decode buffer is sized for 512x512, so
the film is scaled to 512x256 (retail RoQ size: the renderer's Draw_StretchRaw takes power-of-2 frames only and
aborts on 512x352; the frame is stretched back to the 4:3 screen on playback) with 22.05 kHz RoQ audio.
The briefing MAP is a copy of the player's own maps/briefing/briefinge1.bsp (a stock briefing room) with our
script maps/briefing/briefingea<level>.scr (mod side) - the stock coop briefing recipe, unchanged.
Output: zzzz_coop_ea_<l>_film.pk3 = video/ea<l>intro.roq + maps/briefing/briefingea<l>.bsp. Local only.
usage: eamovies.py <ea.iso> <level> <out.pk3> --mohaa <MOHAA dir> [--ffmpeg ffmpeg]"""
import argparse
import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xdvdfs  # noqa: E402
from flmovies import find_in_install, ZIP_TIME  # noqa: E402

FILMS = {"1_11": "data/shared/movies/rusmintr.vp6"}


def build(image, film, level, out, ffmpeg, mohaa=None):
    film = film.lower()
    disc = xdvdfs.XDVDFS(image)
    entry = None
    for path, size, sector, isdir in disc.walk():
        if not isdir and path.lower() == film:
            entry = (int(sector), int(size))
    if entry is None:
        raise RuntimeError("no %s on this disc" % film)
    tmp = tempfile.mkdtemp(prefix="eamov_")
    lv = level.replace("_", "")
    src, roq = os.path.join(tmp, "src.vp6"), os.path.join(tmp, "ea%sintro.roq" % lv)
    with open(src, "wb") as f:
        f.write(disc.read(*entry))
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-threads", "1", "-i", src,
                    "-vf", "scale=512:256:flags=lanczos", "-r", "30",
                    "-c:v", "roqvideo", "-c:a", "roq_dpcm", "-ar", "22050", "-ac", "2",
                    "-fflags", "+bitexact", "-flags", "+bitexact", roq], check=True,
                   creationflags=0x08000000 | 0x00000040 if os.name == "nt" else 0)
    # the engine never plays RoQ's own audio: S_SetupMovieAudio streams video/<name>.mp3, else .wav, beside the film
    # (retail: video/EAlogo.mp3). Without it the film is silent. 22.05 kHz 16-bit stereo PCM, bit-exact.
    wav = roq[:-4] + ".wav"
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-threads", "1", "-i", src, "-vn",
                    "-c:a", "pcm_s16le", "-ar", "22050", "-ac", "2", "-map_metadata", "-1",
                    "-fflags", "+bitexact", "-flags", "+bitexact", wav], check=True,
                   creationflags=0x08000000 | 0x00000040 if os.name == "nt" else 0)
    members = [("video/ea%sintro.roq" % lv, open(roq, "rb").read()), ("video/ea%sintro.wav" % lv, open(wav, "rb").read())]
    bsp = find_in_install(mohaa, "maps/briefing/briefinge1.bsp") if mohaa else None
    if bsp is not None:
        members.append(("maps/briefing/briefingea%s.bsp" % lv, bsp))
        # [v1.10.70, bug-10803] the briefing room's footsteps (snd_step_* / snd_landing_* are filtered to campaign map
        # names): bridged from the player's own install with the briefing room's name as the token
        import flpack
        members.append(("ubersound/ea_filmbridge%s.scr" % lv, flpack.alias_bridge(
            mohaa, "briefing/briefingea%s" % lv, token="briefing/briefingea%s" % lv, only=("snd_step", "snd_landing")).encode("latin-1")))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        for arc, data in sorted(members):
            z.writestr(zipfile.ZipInfo(arc, ZIP_TIME), data)
    for p in (src, roq, wav):
        os.remove(p)
    os.rmdir(tmp)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("level")
    ap.add_argument("out")
    ap.add_argument("--mohaa")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    a = ap.parse_args()
    build(a.image, FILMS[a.level], a.level, a.out, a.ffmpeg, a.mohaa)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
