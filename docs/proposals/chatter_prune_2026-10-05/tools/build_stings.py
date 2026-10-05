"""build_stings.py - render the user-picked Frontline cues into sound/frontline/sting_*.wav (2026-10-05).

Source: C:/mohaa-coop-dev/_frontline/wav/fl_<mission>_<n>.wav (decoded Frontline PS3 score, 22050 stereo). Consecutive
cue files of one mission are CONTIGUOUS segments of a streamed score (sample-level continuity measured: the boundary
jump between fl_1_2_18 and fl_1_2_19 is 2 against a typical sample step of 204), so a cue that "cuts off abruptly" is
extended into its real continuation and released with a raised-cosine fade instead of being truncated.

Output: mono 22050 s16 (the format of the shipped sound/frontline stings), loudness set by EBU R128 integrated
loudness (ffmpeg ebur128) to TARGET LUFS, sample peak capped at -1.5 dBFS.
"""
import os, re, subprocess, wave
import numpy as np

SRC = r"C:/mohaa-coop-dev/_frontline/wav"
DST = r"C:/mohaa-coop-dev/hzm-mohaa-coop-mod/sound/frontline"
SR = 22050

# out name: (cue, continuation cue or None, seconds of continuation, cut at seconds (None = all), fade seconds, LUFS)
PLAN = {
    "sting_newobj":   ("fl_1_2_05", "fl_1_2_06", 2.0, None, 1.5, -20.0),  # user: new objective; "not cut off so abruptly"
    "sting_alarm":    ("fl_1_2_11", None, 0, None, 0.5, -19.0),             # user: alarm being set off
    "sting_objdone":  ("fl_1_2_18", "fl_1_2_19", 2.0, None, 1.5, -20.0),  # user: objective complete; "not so abruptly"
    "sting_stealth":  ("fl_1_3_05", None, 0, None, 0.4, -21.0),             # user: intro to a stealth mission
    "sting_clear1":   ("fl_1_3_10", None, 0, None, 0.3, -19.0),             # user: after a wave / a firefight
    "sting_clear2":   ("fl_1_3_11", None, 0, None, 0.3, -19.0),             # user: after a wave is neutralized
    "sting_clear3":   ("fl_1_3_13", None, 0, None, 0.3, -19.0),             # user: after a wave or tough battle
}


def load(name):
    w = wave.open(os.path.join(SRC, name + ".wav"))
    assert w.getframerate() == SR
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, w.getnchannels()).mean(1)


def lufs(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    return float(m[-1])


def write(path, x):
    y = np.clip(np.round(x * 32767), -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())


def build():
    for out, (cue, cont, csec, cut, fade, target) in PLAN.items():
        x = load(cue)
        if cont:
            x = np.concatenate([x, load(cont)[: int(csec * SR)]])
        if cut:
            x = x[: int(cut * SR)]
        n = int(fade * SR)
        x[-n:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, n)))
        x[:64] *= np.linspace(0, 1, 64)
        tmp = os.path.join(DST, out + ".wav")
        write(tmp, x)
        g = target - lufs(tmp)
        peak = 20 * np.log10(np.abs(x).max() + 1e-12)
        g = min(g, -1.5 - peak)
        x = x * 10 ** (g / 20)
        write(tmp, x)
        print("%-14s %s%s %.2fs gain %+.1f dB -> %.1f LUFS" % (out, cue, "+" + cont if cont else "", len(x) / SR, g, lufs(tmp)))


if __name__ == "__main__":
    build()
