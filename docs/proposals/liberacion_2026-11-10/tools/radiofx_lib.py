"""radiofx_lib.py - the Liberation radio briefing: the user's own ElevenLabs clip made into a period field-radio transmission.

    python -P -E radiofx_lib.py <in.wav (44.1 kHz mono, decoded from the user's mp3)> <out.wav>

Chain (deterministic, seeded): squelch-open click + a short carrier hiss lead-in -> the voice band-passed to 300-3000 Hz
(4th-order Butterworth, both edges) -> light tanh saturation (drive 2.2, mixed 70/30 so it colours, never fuzzes) -> a bed of
band-limited static under the voice (-30 dB) with sparse crackle pops -> squelch-close click + a tail of hiss. Peak-normalised
to -1 dBFS, then resampled to the mod's VO format: 22050 Hz mono 16-bit (sound/coop_vo/, the same format as
den_coop_m2l2a_assault.wav and the other radio lines).
"""
import sys
import wave

import numpy as np
from scipy.signal import butter, resample_poly, sosfilt

SR = 44100
rng = np.random.default_rng(1944)


def read(p):
    w = wave.open(p, "rb")
    assert w.getnchannels() == 1 and w.getsampwidth() == 2, "mono 16-bit please"
    sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768.0
    assert sr == SR, sr
    return x


def bp(x, lo, hi, order=4):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def static(n, level):
    s = bp(rng.standard_normal(n), 400, 4200, 2)
    s /= np.max(np.abs(s)) + 1e-9
    # a slow flutter in the carrier, the way a field set breathes
    t = np.arange(n) / SR
    s *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.7 * t + 1.3) * np.sin(2 * np.pi * 3.1 * t)
    return s * level


def click(n_ms, level, f=1800.0):
    n = int(SR * n_ms / 1000.0)
    t = np.arange(n) / SR
    env = np.exp(-t * 900.0)
    c = (rng.standard_normal(n) * 0.6 + np.sin(2 * np.pi * f * t)) * env
    return bp(c, 300, 4000, 2) * level


def crackle(n, per_sec, level):
    out = np.zeros(n)
    k = int(n / SR * per_sec)
    for i in rng.integers(0, n - 200, k):
        L = int(rng.integers(20, 140))
        out[i:i + L] += rng.standard_normal(L) * np.exp(-np.arange(L) / (L / 4.0)) * level * rng.uniform(0.4, 1.0)
    return bp(out, 500, 5000, 2)


def main(src, dst):
    v = read(src)
    v = v / (np.max(np.abs(v)) + 1e-9)
    v = bp(v, 300.0, 3000.0, 4)
    v = v / (np.max(np.abs(v)) + 1e-9)
    sat = np.tanh(2.2 * v) / np.tanh(2.2)
    v = 0.7 * sat + 0.3 * v
    lead, tail = int(0.28 * SR), int(0.34 * SR)
    body = np.concatenate([np.zeros(lead), v, np.zeros(tail)])
    n = len(body)
    bed = static(n, 10 ** (-30 / 20.0))
    bed[:lead] *= 2.4                       # the open carrier is louder before the voice lands, and after it
    bed[-tail:] *= 2.4
    out = body + bed + crackle(n, 5.0, 0.10)
    c1 = click(30, 0.55)
    out[int(0.02 * SR):int(0.02 * SR) + len(c1)] += c1
    c2 = click(34, 0.55, 1500.0)
    p2 = n - tail + int(0.16 * SR)
    out[p2:p2 + len(c2)] += c2
    out[p2 + len(c2):] *= np.linspace(1.0, 0.0, n - p2 - len(c2)) ** 2      # the set closes: hiss stops after the click
    out *= 10 ** (-1 / 20.0) / (np.max(np.abs(out)) + 1e-9)
    y = resample_poly(out, 1, 2)
    y = np.clip(y, -1.0, 1.0)
    w = wave.open(dst, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR // 2)
    w.writeframes((y * 32767.0).astype("<i2").tobytes())
    w.close()
    print("wrote", dst, "%.2f s" % (len(y) / (SR / 2.0)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
