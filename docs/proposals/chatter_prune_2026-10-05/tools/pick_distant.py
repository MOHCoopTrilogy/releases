"""pick_distant.py - cut distant-battle one-shots out of the Frontline ambience beds (2026-10-05).

For the FAR artillery sweetener in coop_mod/ambience.scr, whose four stock takes are half infrasound (bug-2516:
artillery3/4 are >93% below 10 Hz, so half the draws are inaudible). Frontline's war beds carry real distant
explosions; this finds them and cuts each into a standalone one-shot.

Event = a low-band (40-250 Hz) burst >= 10 dB over the bed's rolling median, while the high band (>3 kHz) rises
< 6 dB (far and muffled, not a close shot), and nothing comparable in the 1.5 s before (a clean onset). Window
onset-0.25 s .. +4.0 s, 30 ms fade-in, 1.2 s raised-cosine fade-out, mono 22050, active RMS matched to the audible
stock take artillery1.wav. Whisper-small must hear no words. Max 1 per source bed, 8 total, strongest first.
"""
import os, glob, hashlib, wave, json, subprocess, re
import numpy as np

FL = r"C:/mohaa-coop-dev/_frontline/ambience"
MOD = r"C:/mohaa-coop-dev/hzm-mohaa-coop-mod"
OUT = os.path.join(MOD, "sound", "coop_amb")
HERE = os.path.dirname(os.path.abspath(__file__))
SR = 22050


def load(p):
    w = wave.open(p)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, w.getnchannels()).mean(1), w.getframerate()


def active_rms(x):
    fl = 512
    e = np.array([np.sqrt(np.mean(x[i:i + fl] ** 2)) for i in range(0, len(x) - fl, fl)])
    a = e[e > 0.25 * e.max()]
    return 20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-12)


def bands(x):
    n, hop = 2048, 512
    win = np.hanning(n)
    fr = np.fft.rfftfreq(n, 1 / SR)
    lo, hi = (fr >= 40) & (fr <= 250), fr >= 3000
    L, H = [], []
    for i in range(0, len(x) - n, hop):
        s = np.abs(np.fft.rfft(x[i:i + n] * win)) ** 2
        L.append(s[lo].sum()); H.append(s[hi].sum())
    return 10 * np.log10(np.array(L) + 1e-12), 10 * np.log10(np.array(H) + 1e-12), hop


def events(x):
    L, H, hop = bands(x)
    fps = SR / hop
    w = int(4 * fps)
    out = []
    i = w
    while i < len(L) - int(4.5 * fps):
        medL = np.median(L[i - w:i]); medH = np.median(H[i - w:i])
        if L[i] - medL >= 10 and H[i] - medH < 6 and (L[i - int(1.5 * fps):i] - medL).max() < 5:
            pk = i + int(np.argmax(L[i:i + int(0.5 * fps)]))
            out.append((float(L[pk] - medL), int(i * hop)))
            i += int(5 * fps)
        else:
            i += 1
    return out


def no_words(paths):
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)
    res = {}
    for p in paths:
        segs, info = m.transcribe(p, beam_size=3, vad_filter=True, condition_on_previous_text=False)
        t = " ".join(s.text.strip() for s in segs).strip()
        res[p] = (re.sub(r"[^A-Za-z]", "", t) == "", t)
    return res


def main():
    ref, _ = load(os.path.join(OUT, "artillery1.wav"))
    target = active_rms(ref)
    seen, cands = set(), []
    for f in sorted(glob.glob(FL + "/*.wav")):
        x, sr = load(f)
        assert sr == SR
        h = hashlib.md5(x[: SR * 10].tobytes()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        ev = sorted(events(x), reverse=True)
        if ev:
            prom, s = ev[0]
            cands.append((prom, os.path.basename(f), s))
    cands.sort(reverse=True)
    tmpdir = os.path.join(HERE, "_distant_tmp")
    os.makedirs(tmpdir, exist_ok=True)
    clips = []
    for prom, f, s in cands[:16]:
        x, _ = load(os.path.join(FL, f))
        a, b = max(0, s - int(0.25 * SR)), s + int(4.0 * SR)
        y = x[a:b].copy()
        y[: int(0.03 * SR)] *= np.linspace(0, 1, int(0.03 * SR))
        n = int(1.2 * SR)
        y[-n:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, n)))
        g = target - active_rms(y)
        g = min(g, -1.0 - 20 * np.log10(np.abs(y).max() + 1e-12))
        y *= 10 ** (g / 20)
        p = os.path.join(tmpdir, "%s_%d.wav" % (f[:-4], s))
        with wave.open(p, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes(np.clip(np.round(y * 32767), -32768, 32767).astype(np.int16).tobytes())
        clips.append((prom, f, s, p, round(g, 1)))
    words = no_words([c[3] for c in clips])
    picks = []
    for prom, f, s, p, g in clips:
        if not words[p][0] or len(picks) >= 8:
            print("skip", f, s, words[p][1])
            continue
        name = "fl_far_%02d.wav" % (len(picks) + 1)
        os.replace(p, os.path.join(OUT, name))
        picks.append(dict(file="sound/coop_amb/" + name, src=f, at=round(s / SR, 2), prominence_db=round(prom, 1), gain=g))
        print(name, f, "%.2fs" % (s / SR), "prom %.1f dB gain %.1f" % (prom, g))
    for fn in os.listdir(tmpdir):
        os.remove(os.path.join(tmpdir, fn))
    os.rmdir(tmpdir)
    json.dump(picks, open(os.path.join(HERE, "distant_picks.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
