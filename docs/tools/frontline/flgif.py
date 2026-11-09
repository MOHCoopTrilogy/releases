#!/usr/bin/env python3
"""Short gameplay GIFs of a converted Frontline level from the private test client. Our own code.

Each clip: teleport the (noclip, god, notarget) camera to pos/ang, wait `delay` s, then grab `secs` s of frames of
OUR window only (PrintWindow - never a desktop grab) at `fps`, and write a GIF (<= 12 s, <= 8 MB, shrinking the
frame size until it fits). Muted, controller off, test display - launch/policy is flharness.launch.
GIFs of Frontline-derived pixels stay local (H:\\hzm_work); never upload them.
usage: flgif.py <map> <clips.json> <outdir>
  clips.json: {"name": {"pos": [x,y,z], "ang": [p,y,0], "delay": 2, "secs": 10, "fps": 8, "w": 640}}"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flharness as fh     # noqa: E402


def write_gif(frames, path, fps, w):
    from PIL import Image
    while True:
        h = int(round(w * frames[0].size[1] / frames[0].size[0]))
        seq = [f.convert("RGB").resize((w, h), Image.LANCZOS).quantize(colors=128, method=Image.Quantize.MEDIANCUT,
                                                                      dither=Image.Dither.NONE) for f in frames]
        seq[0].save(path, save_all=True, append_images=seq[1:], duration=int(1000 / fps), loop=0, optimize=True)
        if os.path.getsize(path) <= 8 * 1024 * 1024 or w <= 360:
            return w, os.path.getsize(path)
        w = int(w * 0.8)


def main(mapname, clips_path, out):
    from PIL import Image
    os.makedirs(out, exist_ok=True)
    clips = json.load(open(clips_path))
    fh.hg.acquire_slot(fh.OWNER, fh.EXE, fh.HOME, [fh.PORT], minutes=30)
    try:
        c = fh.launch(mapname, "opengl2", False, 1280, 720,
                      extra_sets=[x.strip() for x in os.environ.get("FL_SETS", "").split(";") if x.strip()])
        with c:
            if not fh.wait_log(r"Spawning Entities Done|FLAI", 300):
                raise RuntimeError("map never loaded")
            time.sleep(8)
            fh.join()
            time.sleep(14)
            fh.step(["noclip", "wait 5", "god", "wait 5", "notarget", "wait 10", "cg_drawhud 0", "cg_draw2d 0", "fps 0", "wait 5"])   # clean frames: no HUD, hints or fps text
            for name, v in clips.items():
                x, y, z = v["pos"]
                fh.step(["popmenu 0", "tele %.1f %.1f %.1f" % (x, y, z), "wait 5", "face %.1f %.1f 0" % (v["ang"][0], v["ang"][1]), "wait 5"])
                time.sleep(float(v.get("delay", 2)))
                fps = float(v.get("fps", 8))
                secs = min(12.0, float(v.get("secs", 10)))
                frames, t0, k = [], time.time(), 0
                tmp = os.path.join(out, "_f.png")
                while time.time() - t0 < secs:
                    tk = t0 + k / fps
                    if time.time() < tk:
                        time.sleep(tk - time.time())
                    if c.capture_png(tmp):
                        frames.append(Image.open(tmp).copy())
                    k += 1
                if frames:
                    frames[len(frames) // 2].save(os.path.join(out, name + "_mid.jpg"), quality=88)
                    w, sz = write_gif(frames, os.path.join(out, name + ".gif"), fps, int(v.get("w", 640)))
                    fh.log("gif", name, len(frames), "frames", w, "px", sz, "bytes")
            fh.shutil.copyfile(fh.LOG, os.path.join(out, "qconsole.log"))
    finally:
        fh.hg.release_slot(fh.OWNER)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
