"""audio_snd63.py <capture.wav> <qconsole.log> - levels of the attic sounds in an UNMUTED harness capture (attic_run.py snd63).

The client's OpenAL mix went to a .wav through OpenAL Soft's wave backend (alsoft.ini next to the exe; nothing reached a speaker).
The recording starts when the device opens ("OpenAL: Opening device" in the log); the harness echoes '^~^~^ SND <name> on/off'.
Log stamps are whole seconds, so each window is trimmed by 1 s at both ends. Prints RMS / peak dBFS per window and, for the
projector, the level of its 0.48 s re-trigger (the loop's period shows as a peak in the envelope's autocorrelation)."""
import os, re, sys
sys.path = [q for q in sys.path if os.path.abspath(q or ".") != os.path.dirname(os.path.abspath(__file__))]   # tools/queue.py shadows the stdlib queue (scipy)
from datetime import datetime
import numpy as np

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\debrief2_2026-11-03\tools")
from audio_levels import read_wav  # noqa: E402  (handles OpenAL Soft's 32-bit float WAVE_FORMAT_EXTENSIBLE)

wav, logp = sys.argv[1:3]
a, sr = read_wav(open(wav, "rb").read())
mono = a.mean(1)
T = lambda l: datetime.strptime(l[1:20], "%Y-%m-%d %H:%M:%S")  # noqa: E731
t0, marks = None, {}
for l in open(logp, encoding="latin-1"):
    if "OpenAL: Opening device" in l and t0 is None:
        t0 = T(l)
    m = re.search(r"\^~\^~\^ SND (\w+) (on|off)", l)
    if m and t0:
        marks.setdefault(m.group(1), {})[m.group(2)] = (T(l) - t0).total_seconds()
db = lambda x: 20 * np.log10(max(x, 1e-9))  # noqa: E731
print("capture %.1f s, %d Hz, %d ch, whole-file peak %.1f dBFS" % (len(mono) / sr, sr, a.shape[1], db(np.abs(a).max())))
for name, w in marks.items():
    if "on" not in w or "off" not in w:
        continue
    s0, s1 = int((w["on"] + 1.0) * sr), int((w["off"] - 1.0) * sr)
    x = mono[s0:s1]
    if len(x) < sr:
        continue
    rms, pk = np.sqrt(np.mean(x ** 2)), np.abs(a[s0:s1]).max()
    clip = int((np.abs(a[s0:s1]) > 0.999).sum())
    extra = ""
    if name == "projector":
        env = np.sqrt(np.convolve(x ** 2, np.ones(int(0.02 * sr)) / int(0.02 * sr), "same"))
        e = env - env.mean()
        ac = np.correlate(e, e, "full")[len(e) - 1:]
        lo, hi = int(0.3 * sr), int(0.7 * sr)
        lag = (lo + int(np.argmax(ac[lo:hi]))) / sr
        extra = "  envelope period %.3f s (re-trigger 0.48 s)" % lag
    print("%-10s %5.1f..%5.1f s  RMS %6.1f dBFS  peak %6.1f dBFS  clipped samples %d%s" % (name, w["on"] + 1, w["off"] - 1, db(rms), db(pk), clip, extra))
