"""audio_levels.py - levels of the debrief's sound cues in an UNMUTED harness capture (run_db2.py --audio).

The client's OpenAL mix was written to a .wav by OpenAL Soft's "wave" backend (nothing reached a speaker). The client
log has one "^~^~^ DB2 snd t=<cg.time> <sound> x<vol>" line per cue. The recording is aligned to cg.time on the rank-up
ping (cross-correlation of the ping's own samples against the recording); then each cue's window is measured.

    python audio_levels.py <capture.wav> <client qconsole.log>
"""
import io, math, re, sys, wave, zipfile
import numpy as np
from scipy import signal

MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
PAK3 = r"G:\GOG\Medal of Honor - Allied Assault War Chest\main\Pak3.pk3"


def read_wav(data):
    from scipy.io import wavfile
    try:   # OpenAL Soft's wave backend writes 32-bit float WAVE_FORMAT_EXTENSIBLE, which the wave module refuses
        sr, a = wavfile.read(io.BytesIO(data) if isinstance(data, bytes) else data)
        if a.dtype == np.int16:
            a = a.astype(np.float32) / 32768.0
        elif a.dtype == np.int32:
            a = a.astype(np.float32) / 2147483648.0
        elif a.dtype == np.uint8:
            a = (a.astype(np.float32) - 128) / 128.0
        else:
            a = a.astype(np.float32)
        if a.ndim == 1:
            a = a[:, None]
        return a, sr
    except Exception:
        if not isinstance(data, bytes):
            data.seek(0)
    w = wave.open(io.BytesIO(data) if isinstance(data, bytes) else data)
    n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
    raw = w.readframes(n)
    if sw == 2:
        a = np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0
    elif sw == 4:
        a = np.frombuffer(raw, "<i4").astype(np.float32) / 2147483648.0
    else:
        a = (np.frombuffer(raw, "u1").astype(np.float32) - 128) / 128.0
    a = a.reshape(-1, ch)
    return a, sr


def src(name):
    if name.startswith("sound/"):
        z = zipfile.ZipFile(PAK3)
        for n in z.namelist():
            if n.lower() == name.lower():
                return read_wav(z.read(n))
        return read_wav(open(MOD + "/" + name, "rb").read())
    m = {"coop_rankup_cine": "sound/coop/coop_rankup_cine.wav"}
    if name in m:
        return read_wav(open(MOD + "/" + m[name], "rb").read())
    k = re.match(r"coop_type_key(\d)", name)
    if k:
        return read_wav(open(MOD + "/sound/items/coop_type_key%s.wav" % k.group(1), "rb").read())
    return None


def db(x):
    return 20 * math.log10(max(x, 1e-6))


def main():
    rec, sr = read_wav(open(sys.argv[1], "rb"))
    log = open(sys.argv[2], encoding="latin-1", errors="replace").read()
    cues = [(int(t), n, float(v)) for t, n, v in re.findall(r"DB2 snd t=(\d+) (\S+) x([\d.]+)", log)]
    if not cues:
        print("no DB2 snd lines")
        return 1
    mono = rec.mean(1)
    # align: the rank-up ping
    pt = [t for t, n, v in cues if n == "coop_rankup_cine"]
    ping, psr = src("coop_rankup_cine")
    ping = ping.mean(1)
    if psr != sr:
        ping = signal.resample_poly(ping, sr, psr)
    seg = ping[: int(1.0 * sr)]
    cor = signal.fftconvolve(mono, seg[::-1], mode="valid")
    lag = int(np.argmax(np.abs(cor)))
    off = lag / sr - pt[0] / 1000.0          # recording seconds = cg.time / 1000 + off
    print("capture %s: %d Hz, %d ch, %.1f s; ping found at %.3f s (cg.time %d)" % (sys.argv[1], sr, rec.shape[1], len(mono) / sr, lag / sr, pt[0]))
    t0 = cues[0][0] / 1000.0 + off
    t1 = cues[-1][0] / 1000.0 + off + 3.2
    a, b = int(max(0, t0 - 0.2) * sr), int(min(len(mono) / sr, t1) * sr)
    win = rec[a:b]
    clip = int((np.abs(win) >= 0.999).sum())
    print("debrief window %.1f-%.1f s: peak %.1f dBFS, rms %.1f dBFS, clipped samples %d" %
          (t0, t1, db(np.abs(win).max()), db(np.sqrt((win ** 2).mean())), clip))
    pre = rec[max(0, a - 2 * sr):a]
    if len(pre):
        print("2 s before it (game bed): peak %.1f dBFS, rms %.1f dBFS" % (db(np.abs(pre).max()), db(np.sqrt((pre ** 2).mean()))))
    by = {}
    for t, n, v in cues:
        s_, ssr = src(n) or (None, None)
        dur = (len(s_) / ssr) if s_ is not None else 0.5
        dur = min(dur, 1.2)
        i0 = int((t / 1000.0 + off) * sr)
        w = rec[i0:i0 + int(dur * sr)]
        if not len(w):
            continue
        key = re.sub(r"\d+(\.wav)?$", "", n.split("/")[-1].lower())
        by.setdefault(key, []).append((db(np.abs(w).max()), db(np.sqrt((w ** 2).mean()))))
    print("%-24s %5s %10s %10s" % ("cue", "n", "peak dBFS", "rms dBFS"))
    for k, v in sorted(by.items()):
        pk = max(x[0] for x in v)
        rm = sum(x[1] for x in v) / len(v)
        print("%-24s %5d %10.1f %10.1f" % (k, len(v), pk, rm))
    return 0


if __name__ == "__main__":
    sys.exit(main())
