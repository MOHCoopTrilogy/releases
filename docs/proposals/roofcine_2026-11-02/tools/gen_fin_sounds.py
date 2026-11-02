"""gen_fin_sounds.py <coop_explosions_dir> <out_sound_dir>  - the Norway ending's rolling-chain + tank-room sounds (sound/coop_fin/*.wav).

Nothing downloaded: every file is DERIVED from the mod's own explosion pool (sound/coop_explosions/coop_ex_*.wav, already shipped in
zzzzzz_co-op_hzm_mod_assets_snd.pk3) plus a procedurally synthesised whoosh (numpy noise, written here). Needs ffmpeg + numpy.

fin_chain01..08  (cut together at the silence beat, see CUT) one detonation each, travelling deeper into the facility. Per step d = 0..1: a 0.45 s pre-roar (filtered noise whose
                 cutoff sweeps DOWN 3400 -> 260 Hz while it swells: the doppler 'something rushing past and away'), then the hit,
                 low-passed 5200 -> 650 Hz, pitched 1.00 -> 0.84, bass lifted, with a longer echo tail the deeper it is, and 0.6 dB
                 quieter per step. Loudness: -16.5 LUFS at step 1 (= coop_ex_large_08, the pool's reference), then the per-step drop.
fin_tankboom     the climax: bomb_01 + large_08 (0.12 s late) + sub_01 (+6 dB) layered, low-passed 3800 Hz, long double echo, 9 s,
                 -13.5 LUFS (3 dB over the pool: the biggest thing in the game).
All 22050 Hz mono 16-bit, peak <= -1 dBFS."""
import os, subprocess, sys, wave
import numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
SR = 22050
TMP = os.path.join(OUT, "_tmp")
os.makedirs(TMP, exist_ok=True)


def ff(*a):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)


def readwav(p):
    with wave.open(p) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2, p
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0


def writewav(p, x):
    x = np.clip(x, -1, 1)
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def whoosh(secs, f0, f1, seed):
    """noise through a one-pole low-pass whose cutoff sweeps f0 -> f1 (exponential), amplitude swelling ^2.2, cut at the hit"""
    rng = np.random.RandomState(seed)
    n = int(secs * SR)
    x = rng.uniform(-1, 1, n).astype(np.float32)
    fc = f0 * (f1 / f0) ** (np.arange(n) / n)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros(n, np.float32); s = 0.0
    for i in range(n):
        s = (1 - a[i]) * x[i] + a[i] * s
        y[i] = s
    env = (np.arange(n) / n) ** 2.2
    y = y * env
    return y / (np.abs(y).max() + 1e-9) * 0.55


def norm(src, dst, lufs):
    ff("-i", src, "-af", "loudnorm=I=%g:TP=-1.0:LRA=11" % lufs, "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", dst)


GAPS = [0.70, 0.60, 0.50, 0.42, 0.36, 0.30, 0.26]          # must match cin_chain's local.g[]
T = [0.0]
for g in GAPS: T.append(T[-1] + g)
CUT = [(T[-1] - t) + 0.65 for t in T]
HITS = ["large_08", "bomb_02", "large_06", "bomb_04", "large_09", "bomb_05", "large_05", "bomb_03"]
for i, h in enumerate(HITS):
    d = i / (len(HITS) - 1)
    lp = 5200 * (650 / 5200) ** d
    pitch = 1.0 - 0.16 * d
    d1, d2 = int(90 + 140 * d), int(210 + 360 * d)
    g1, g2 = 0.30 + 0.25 * d, 0.18 + 0.22 * d
    hit = os.path.join(TMP, "hit%d.wav" % i)
    af = ("asetrate=%d,aresample=%d,lowpass=f=%d,lowpass=f=%d,bass=g=%.1f:f=110,aecho=0.8:0.85:%d|%d:%.2f|%.2f,apad=pad_dur=1.5"
          % (int(SR * pitch), SR, lp, lp, 2 + 5 * d, d1, d2, g1, g2))
    ff("-i", os.path.join(SRC, "coop_ex_%s.wav" % h), "-af", af, "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", hit)
    w = whoosh(0.45, 3400 - 1400 * d, 260, 17 + i)
    hx = readwav(hit)
    pre = int(0.40 * SR)                       # the hit lands 0.40 s in, over the end of the whoosh
    mix = np.zeros(pre + len(hx), np.float32)
    mix[:len(w)] += w
    mix[pre:] += hx
    raw = os.path.join(TMP, "chain%d.wav" % i)
    writewav(raw, mix / (np.abs(mix).max() + 1e-9) * 0.9)
    # THE SILENCE BEAT: every chain file is cut (80 ms fade) at the same wall-clock moment, 0.65 s after the last hit is triggered,
    # so the whole chain ducks out together right before the tank-room flash. CUT[i] = (T8 - Ti) + 0.65, Ti from cin_chain's gaps.
    full = os.path.join(TMP, "chainfull%d.wav" % i)
    norm(raw, full, -16.5 - 0.6 * i)
    cut = CUT[i]
    ff("-i", full, "-af", "atrim=0:%.3f,afade=t=out:st=%.3f:d=0.08" % (cut, max(0.0, cut - 0.08)), "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16",
       os.path.join(OUT, "fin_chain%02d.wav" % (i + 1)))

# the tank-room climax
a = readwav(os.path.join(SRC, "coop_ex_bomb_01.wav"))
b = readwav(os.path.join(SRC, "coop_ex_large_08.wav"))
c = readwav(os.path.join(SRC, "coop_ex_sub_01.wav")) * 2.0
n = max(len(a), int(0.12 * SR) + len(b), len(c))
m = np.zeros(n, np.float32)
m[:len(a)] += a; m[int(0.12 * SR):int(0.12 * SR) + len(b)] += b * 0.8; m[:len(c)] += c
raw = os.path.join(TMP, "tank_raw.wav")
writewav(raw, m / (np.abs(m).max() + 1e-9) * 0.9)
lay = os.path.join(TMP, "tank_lay.wav")
ff("-i", raw, "-af", "lowpass=f=3800,aecho=0.8:0.8:260|620:0.35|0.22,apad=pad_dur=3,atrim=0:9,afade=t=out:st=6.5:d=2.5", "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", lay)
norm(lay, os.path.join(OUT, "fin_tankboom.wav"), -13.5)

for f in os.listdir(TMP):
    os.remove(os.path.join(TMP, f))
os.rmdir(TMP)
for f in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, f)
    with wave.open(p) as w:
        print(f, w.getframerate(), w.getnchannels(), round(w.getnframes() / w.getframerate(), 2), "s")
