"""Loudness envelope of a game sound per 1/30 s (the clip frame time): where its clicks are, without hearing it.

    python sndenv.py sound/weapons/foley/Colt45Reload1b.wav [more ...]
"""
import sys, os, io, wave
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
vfs = V.R.vfs
for p in sys.argv[1:]:
    raw = vfs.read(p)
    w = wave.open(io.BytesIO(raw))
    sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
    d = np.frombuffer(w.readframes(n), dtype=np.int16 if sw == 2 else np.uint8).astype(float)
    if sw == 1:
        d = (d - 128) * 256
    if ch > 1:
        d = d.reshape(-1, ch).mean(1)
    hop = int(sr / 30)
    env = np.array([np.abs(d[i:i + hop]).max() for i in range(0, len(d), hop)])
    print(p, sr, 'Hz', round(n / sr, 2), 's;', 'level 0-9 per clip frame:')
    print(' '.join('%d:%d' % (i, round(9 * e / env.max())) for i, e in enumerate(env)))
    on = [i for i in range(1, len(env)) if env[i] > 0.35 * env.max() and env[i] > 2.0 * env[i - 1]]
    print('  onsets (frame):', on)
