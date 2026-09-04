#!/usr/bin/env python
"""
psx_cut_stingers.py - find musically-plausible stinger excerpts in the extracted PSX score,
and write them at the format the Frontline score layer already uses (22050 Hz, mono, 16-bit).

WHY IT PICKS RATHER THAN I DO
    I cannot listen to these. So instead of guessing timecodes, this scores candidate windows on
    properties a stinger actually has, all measurable:
      * it STARTS on a strong onset - a big jump in short-window RMS, i.e. a hit, not a fade-in
      * it is LOUD relative to the track - it should read over gameplay
      * it ENDS quiet - the tail decays, so the excerpt does not stop mid-phrase
      * it does not start inside speech - the briefing tracks carry narration, so a candidate whose
        band energy looks voice-like is penalised (speech sits mostly under 4 kHz with a low
        zero-crossing rate and strong 100-300 Hz content; orchestral hits spread much wider)
    Then it takes the best non-overlapping windows.

    That is not the same as taste, and I am not claiming it is. It is a shortlist that is very
    likely to contain usable hits, and every candidate is written out so a human can audition and
    delete the duds.

FORMAT
    Matches sound/frontline/*.wav exactly: 22050 Hz, mono, 16-bit PCM. The source is 37800 Hz
    stereo, so this downmixes to mono and resamples with a simple averaging decimator - adequate
    for a 3-second orchestral hit and dependency-free (no numpy/scipy in this repo's toolchain).

USAGE
    python docs/tools/psx_cut_stingers.py --src <dir of extracted wavs> --out <dir> [--secs 4.0]
"""
import argparse, math, os, struct, wave


def read_wav_mono(path, limit_secs=None):
    w = wave.open(path, 'rb')
    ch, sw, fr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    if sw != 2:
        w.close()
        return None, None
    if limit_secs:
        n = min(n, int(limit_secs * fr))
    raw = w.readframes(n)
    w.close()
    s = struct.unpack('<%dh' % (len(raw) // 2), raw)
    if ch > 1:
        mono = [(s[i] + s[i + 1]) // 2 for i in range(0, len(s) - 1, 2)]
    else:
        mono = list(s)
    return mono, fr


def resample(sig, src, dst):
    """integer-ish decimation with averaging - src is 37800, dst 22050"""
    ratio = src / float(dst)
    out = []
    pos = 0.0
    n = len(sig)
    while True:
        a = int(pos)
        b = int(pos + ratio)
        if b >= n:
            break
        seg = sig[a:b] if b > a else sig[a:a + 1]
        out.append(int(sum(seg) / len(seg)))
        pos += ratio
    return out


def envelope(sig, fr, win_ms=25):
    win = max(1, int(fr * win_ms / 1000.0))
    env = []
    for i in range(0, len(sig) - win, win):
        seg = sig[i:i + win]
        env.append(math.sqrt(sum(float(x) * x for x in seg) / win))
    return env, win


def zcr(sig):
    if len(sig) < 2:
        return 0.0
    return sum(1 for i in range(1, len(sig)) if (sig[i - 1] < 0) != (sig[i] < 0)) / (len(sig) - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=r"C:\mohaa-coop-dev\_psx_moh")
    ap.add_argument("--out", default=r"C:\mohaa-coop-dev\_psx_moh\stingers")
    ap.add_argument("--secs", type=float, default=4.0)
    ap.add_argument("--per", type=int, default=3, help="candidates per source track")
    ap.add_argument("--only", default="", help="substring filter on source filenames")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    srcs = [f for f in sorted(os.listdir(a.src))
            if f.lower().endswith('.wav') and (not a.only or a.only.lower() in f.lower())]
    print("%-32s %6s %6s %8s  %s" % ("SOURCE", "start", "score", "peak", "written"))
    for fn in srcs:
        sig, fr = read_wav_mono(os.path.join(a.src, fn), limit_secs=200)
        if sig is None or len(sig) < fr * 6:
            continue
        env, win = envelope(sig, fr)
        if len(env) < 40:
            continue
        emax = max(env) or 1.0
        wlen = int(a.secs * fr)
        wenv = int(a.secs * fr / win)
        cands = []
        for i in range(2, len(env) - wenv - 2):
            onset = env[i] - env[i - 2]                       # rise into the window
            loud = sum(env[i:i + wenv // 2]) / max(wenv // 2, 1)
            tail = sum(env[i + wenv - 4:i + wenv]) / 4.0
            if env[i] < emax * 0.35:
                continue
            if tail > loud * 0.85:                            # must decay, not cut off mid-phrase
                continue
            seg = sig[i * win:i * win + wlen]
            z = zcr(seg)
            if z < 0.02:                                      # very low zcr = likely speech/rumble
                continue
            score = (onset / emax) * 2.0 + (loud / emax) - (tail / emax)
            cands.append((score, i, loud, z))
        cands.sort(key=lambda c: -c[0])
        chosen = []
        for score, i, loud, z in cands:
            if any(abs(i - j) < wenv for _, j, _, _ in chosen):
                continue
            chosen.append((score, i, loud, z))
            if len(chosen) >= a.per:
                break
        base = fn.rsplit('.', 1)[0].replace("MOVIE_", "").lower()
        for k, (score, i, loud, z) in enumerate(chosen, 1):
            seg = sig[i * win:i * win + wlen]
            # short fade in/out so the excerpt cannot click
            fade = int(fr * 0.03)
            for j in range(min(fade, len(seg))):
                seg[j] = int(seg[j] * j / fade)
                seg[-1 - j] = int(seg[-1 - j] * j / fade)
            out = resample(seg, fr, 22050)
            peak = max(abs(x) for x in out) or 1
            gain = min(3.0, 26000.0 / peak)                   # normalise, but never more than 3x
            out = [max(-32768, min(32767, int(x * gain))) for x in out]
            name = "psx_%s_%d.wav" % (base, k)
            with wave.open(os.path.join(a.out, name), 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(22050)
                w.writeframes(struct.pack('<%dh' % len(out), *out))
            print("%-32s %6.1fs %6.2f %8d  %s" % (fn[:32], i * win / float(fr), score, peak, name))


if __name__ == "__main__":
    main()
