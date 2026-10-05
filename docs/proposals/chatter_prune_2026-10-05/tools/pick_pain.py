"""pick_pain.py - choose Frontline hurt grunts to add VARIETY to the AI pain pools (2026-10-05).

Candidates: the wordless "efforts" takes of _frontline/vo (files listed in vo_reels_sorted/*_efforts_index.txt).
Filters (all measured, nothing hand-waved):
  * 0.30-0.85 s long, the shape of a hit grunt (death screams and breaths are longer; the deathvox pool's
    150 Frontline efforts were death clips, so this range also keeps clear of them);
  * energy peak in the first 45% and the last 20% at least 9 dB under the peak (a hit, not a sustained effort);
  * voiced, median F0 90-260 Hz (adult male range for a shout; Frontline has no female soldier);
  * whisper-small hears no words (text empty, or only an interjection - ah/ugh/oh/argh/hm);
  * byte-identical duplicates collapsed; at most 3 per VO bank, round-robin, for voice variety.
Output: sound/coop_flvo/fl_pain_de_NN.wav / fl_pain_us_NN.wav (22050 mono s16, active-RMS matched to the retail
pain pool the take joins) + picks.json for the alias generator.
"""
import os, re, glob, json, hashlib, wave, subprocess, collections, zipfile
import numpy as np

FL = r"C:/mohaa-coop-dev/_frontline"
MOD = r"C:/mohaa-coop-dev/hzm-mohaa-coop-mod"
GOG = r"G:/GOG/Medal of Honor - Allied Assault War Chest"
OUT = os.path.join(MOD, "sound", "coop_flvo")
HERE = os.path.dirname(os.path.abspath(__file__))
PER_POOL = 12


def load(path):
    w = wave.open(path)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, w.getnchannels()).mean(1), w.getframerate()


def active_rms(x):
    fl = 256
    e = np.array([np.sqrt(np.mean(x[i:i + fl] ** 2)) for i in range(0, max(1, len(x) - fl), fl)])
    a = e[e > 0.25 * e.max()]
    return 20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-12)


def f0(x, sr):
    fl, hop = int(sr * 0.04), int(sr * 0.01)
    lo, hi = int(sr / 400), int(sr / 70)
    e = np.sqrt(np.mean(x ** 2)) + 1e-9
    out = []
    for i in range(0, len(x) - fl, hop):
        f = x[i:i + fl]
        if np.sqrt(np.mean(f ** 2)) < 0.5 * e:
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, "full")[fl - 1:]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        k = lo + np.argmax(ac[lo:hi])
        if ac[k] > 0.45:
            out.append(sr / k)
    return (float(np.median(out)), len(out)) if out else (0.0, 0)


def candidates():
    eff = []
    for idx in sorted(glob.glob(FL + "/vo_reels_sorted/*_efforts_index.txt")):
        for ln in open(idx, encoding="utf-8"):
            p = ln.strip().split("\t")
            if len(p) == 2 and p[1].endswith(".wav"):
                eff.append(p[1])
    seen, out = set(), []
    for f in eff:
        path = os.path.join(FL, "vo", f)
        if not os.path.exists(path):
            continue
        x, sr = load(path)
        d = len(x) / sr
        if not (0.30 <= d <= 0.85):
            continue
        h = hashlib.md5(x.tobytes()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        n = len(x)
        env = np.array([np.sqrt(np.mean(s ** 2)) for s in np.array_split(x, 20)])
        pk = int(env.argmax())
        if pk > 8 or env[-4:].max() > env.max() * 10 ** (-9 / 20):
            continue
        m, k = f0(x, sr)
        if not (90 <= m <= 260) or k < 6:
            continue
        out.append((f, round(d, 2), round(m), round(20 * np.log10(np.abs(x).max() + 1e-12), 1)))
    return out


def no_words(files):
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)
    ok = {}
    for f in files:
        segs, info = model.transcribe(os.path.join(FL, "vo", f), beam_size=3, language="en",
                                      condition_on_previous_text=False)
        t = " ".join(s.text.strip() for s in segs).strip().lower()
        t2 = re.sub(r"[^a-z ]", "", t).strip()
        ok[f] = (t2 == "" or re.fullmatch(r"((ah+|uh+|ugh+|oh+|argh+|agh+|hm+|mm+|gah+|ow+|oof+|huh+)\s*)+", t2) is not None, t)
    return ok


def pool_target(rx):
    """median active RMS of the retail pool's takes - AA ships them LOOSE in GOG main/sound, not in a pak."""
    vals = []
    for root in (GOG + "/main", MOD):
        for dp, _, fs in os.walk(os.path.join(root, "sound", "dialogue")):
            for fn in fs:
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                if re.search(rx, rel, re.I):
                    x, _ = load(full)
                    vals.append(active_rms(x))
    return float(np.median(vals)), len(vals)


def main():
    cands = candidates()
    print("shape/F0 candidates", len(cands))
    cache = os.path.join(HERE, "_pain_whisper_cache.json")
    if os.path.exists(cache):
        words = json.load(open(cache))
    else:
        words = no_words([c[0] for c in cands])
        json.dump(words, open(cache, "w"))
    cands = [c for c in cands if words[c[0]][0]]
    print("wordless", len(cands))
    bank = collections.defaultdict(list)
    for c in cands:
        bank[c[0].split("load")[0]].append(c)
    order = []
    for r in range(3):
        for b in sorted(bank):
            if len(bank[b]) > r and len(order) < 2 * PER_POOL:
                order.append(bank[b][r])
    tde, nde = pool_target(r"sound/dialogue/generic/g/pain/den_damage_\d+\.wav$")
    tus, nus = pool_target(r"sound/dialogue/generic/a/damage/dfr_damage_\d+[a-z]\.wav$")
    print("targets de %.1f (n=%d) us %.1f (n=%d)" % (tde, nde, tus, nus))
    picks = []
    for i, c in enumerate(order):
        nat = "de" if i % 2 == 0 else "us"
        k = sum(1 for p in picks if p["nat"] == nat) + 1
        name = "fl_pain_%s_%02d.wav" % (nat, k)
        x, sr = load(os.path.join(FL, "vo", c[0]))
        g = (tde if nat == "de" else tus) - active_rms(x)
        g = min(g, -1.0 - c[3])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(FL, "vo", c[0]), "-af",
                        "volume=%.2fdB,afade=t=out:st=%.3f:d=0.05" % (g, max(0, c[1] - 0.05)),
                        "-ar", "22050", "-ac", "1", "-sample_fmt", "s16", os.path.join(OUT, name)], check=True)
        picks.append(dict(nat=nat, file="sound/coop_flvo/" + name, src=c[0], dur=c[1], f0=c[2], gain=round(g, 1),
                          whisper=words[c[0]][1]))
        print(name, c, "gain %.1f" % g, repr(words[c[0]][1]))
    json.dump(picks, open(os.path.join(HERE, "pain_picks.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
