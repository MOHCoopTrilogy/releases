#!/usr/bin/env python3
"""Frontline mission briefing films -> a local pak the MOHAA engine plays. Our own code; runs on the PLAYER's PC.

Frontline's films are DATA/MOVIES/<name>.mpc: EA 'MPCh' chunks around MPEG-2 640x448 29.97 fps video plus EA
ADPCM R1 stereo 48 kHz audio (ffmpeg's electronicarts demuxer reads them). The engine plays id RoQ through the
same path the stock SH/BT briefings use (playmovie / cinematic, cl_cin.cpp). Stock layout, copied exactly
(every shipped RoQ, e.g. maintt/video/briefinge1.roq): 512x256 video with NO audio chunks, and the sound as a
separate video/<name>.mp3 or .wav that S_SetupMovieAudio streams (snd_openal_new.cpp tries .mp3 then .wav). The
first take (512x352 + embedded roq_dpcm audio) was opened and closed by the engine in the same second.
The briefing MAP is a copy of the player's own maps/briefing/briefinge1.bsp (a stock briefing room) with our
script maps/briefing/briefingfl<m>.scr (mod side) - the stock coop briefing recipe, unchanged.
Output: zzzz_coop_fl_m<m>_brief.pk3 = video/flbrief<m>1.roq + .wav + maps/briefing/briefingfl<m>.bsp. Local only.
usage: flmovies.py <frontline.iso> <mission> <out.pk3> --mohaa <MOHAA dir> [--ffmpeg ffmpeg]"""
import argparse
import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xdvdfs  # noqa: E402

ZIP_TIME = (2002, 5, 28, 0, 0, 0)


def find_in_install(mohaa, member):
    data = None
    for game in ("main", "mainta", "maintt"):
        d = os.path.join(mohaa, game)
        if not os.path.isdir(d):
            continue
        for pk in sorted((p for p in os.listdir(d) if p.lower().endswith(".pk3")), key=str.lower):
            try:
                z = zipfile.ZipFile(os.path.join(d, pk))
                nm = {n.lower(): n for n in z.namelist()}.get(member.lower())
                if nm:
                    data = z.read(nm)                # last in load order wins
            except Exception:
                pass
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("mission", type=int)
    ap.add_argument("out")
    ap.add_argument("--mohaa", required=True)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    a = ap.parse_args()
    name = "brief%d1" % a.mission
    disc = xdvdfs.XDVDFS(a.image)
    entry = None
    for path, size, sector, isdir in disc.walk():
        if not isdir and path.lower() == ("data/movies/%s.mpc" % name):
            entry = (int(sector), int(size))
    if entry is None:
        raise SystemExit("no DATA/MOVIES/%s.mpc on this disc" % name)
    bsp = find_in_install(a.mohaa, "maps/briefing/briefinge1.bsp")
    if bsp is None:
        raise SystemExit("this MOHAA install has no maps/briefing/briefinge1.bsp (Breakthrough) for the briefing room")
    tmp = tempfile.mkdtemp(prefix="flmov_")
    src, roq, wav = (os.path.join(tmp, name + ".mpc"), os.path.join(tmp, "fl%s.roq" % name),
                     os.path.join(tmp, "fl%s.wav" % name))
    with open(src, "wb") as f:
        f.write(disc.read(*entry))
    subprocess.run([a.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-threads", "1", "-i", src,
                    "-vf", "scale=512:256:flags=lanczos", "-r", "30", "-an", "-c:v", "roqvideo",
                    "-fflags", "+bitexact", "-flags", "+bitexact", roq,
                    "-vn", "-c:a", "pcm_s16le", "-ar", "22050", "-ac", "2",
                    "-fflags", "+bitexact", "-flags", "+bitexact", wav], check=True)
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_STORED) as z:
        for arc, data in (("maps/briefing/briefingfl%d.bsp" % a.mission, bsp), ("video/fl%s.roq" % name, open(roq, "rb").read()),
                          ("video/fl%s.wav" % name, open(wav, "rb").read())):
            zi = zipfile.ZipInfo(arc, ZIP_TIME)
            z.writestr(zi, data)
    for p in (src, roq, wav):
        os.remove(p)
    os.rmdir(tmp)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
