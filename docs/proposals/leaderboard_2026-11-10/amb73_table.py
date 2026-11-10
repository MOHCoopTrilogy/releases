"""amb73_table.py - the attic window ambience vs the menu music, offline (dB), before (v1.10.72 exe) and after (polish73-eng).

Model (snd_openal_new.cpp): music source gain = s_volume * s_musicvolume; a loop's gain = its volume * s_ambientvolume (s_volume
on both, so it cancels in the ratio); thunder is a local one-shot (no ambient factor). Levels = gain (dB) + the file's RMS (dBFS).
Music RMS -20 dBFS (the four menu themes measure -15.2 / -20.0 / -21.1 / -24.2). The user's own settings (G:\\mohaa-gl2 omconfig,
read-only): s_volume 0.9, s_musicvolume 0.797, s_ambientvolume 0.531, ui_wxAmbLevel 2 (MED), ui_wxAmbVol 1.
"""
import math

MUS, AMB = 0.796847, 0.531232
MUSIC_RMS = -20.0
RMS = dict(roof=(-20.0, -23.0), glass=(-20.1, -23.1), heavy=(-20.0, -23.0), drips=(-21.9, -24.9), wind=(-20.0, -23.0), night=(-20.0, -23.0))
THUNDER_RMS = -33.6
NAMES = ["roof", "glass", "heavy", "drips", "wind", "night"]
db = lambda g: 20 * math.log10(g) if g > 1e-9 else float("-inf")  # noqa: E731
music = db(MUS) + MUSIC_RMS


def before(lvl, close, rain, storm, overcast=1.0, wet=0.0, night=0.0):
    user = 0 if lvl <= 0 else (2.0 if lvl >= 2 else 1.0)
    master = user * (0.08 + 0.08 * close)
    bed = 0.35 + 0.65 * close
    lv = [0.55 * rain * (0.7 + 0.3 * storm), 0.45 * rain * (0.25 + 0.75 * close), 0.40 * rain * storm, 0.30 * wet * (1 - rain),
          0.12 + 0.12 * overcast + 0.26 * storm, 0.35 * night * (1 - rain)]
    out = {}
    for i, n in enumerate(NAMES):
        v = lv[i] * master * bed * (1 + close if i <= 2 else 1)
        f = RMS[n][0] if close >= 0.5 else RMS[n][1]
        out[n] = db(v) + db(AMB) + f - music
    th = 0.5 * (0.16 + 0.16 * close) * (2.0 if lvl >= 2 else 1.0)
    out["thunder"] = db(th) + THUNDER_RMS - music if lvl > 0 else float("-inf")
    return out


def after(lvl, close, rain, storm, overcast=1.0, wet=0.0, night=0.0):
    lg = 0 if lvl <= 0 else (0.5 if lvl == 1 else (1.0 if lvl == 2 else 1.8))
    gH = [0.75, 0.55, 0.50, 0.13, 0.10, 0.10]
    gW = [1.00, 1.00, 0.90, 0.30, 0.30, 0.25]
    lv = [rain * (0.55 + 0.45 * storm), rain * (0.65 + 0.35 * storm), rain * (0.45 + 0.55 * storm), wet * (1 - rain),
          0.40 + 0.25 * overcast + 0.35 * storm, night * (1 - rain)]
    out = {}
    for i, n in enumerate(NAMES):
        g = (gW if close >= 0.5 else gH)[i]
        v = min(1.0, lv[i] * lg * g)
        f = RMS[n][0] if close >= 0.5 else RMS[n][1]
        out[n] = db(v) + db(AMB) + f - music
    th = min(1.0, lg * (0.55 + 0.30 * close))
    out["thunder"] = db(th) + THUNDER_RMS - music if lvl > 0 else float("-inf")
    return out


def fmt(x):
    return "off" if x == float("-inf") else "%+.0f" % x


if __name__ == "__main__":
    rows = []
    for view, close in (("home", 0.0), ("LOOK OUTSIDE / UP", 1.0)):
        for wx, rain, storm in (("rain", 1.0, 0.0), ("storm", 1.0, 1.0)):
            for lvl, ln in ((1, "LOW"), (2, "MED"), (3, "HIGH")):
                b, a = before(lvl, close, rain, storm), after(lvl, close, rain, storm)
                rows.append("| %s | %s | %s | %s |" % (view, wx, ln, " | ".join("%s -> **%s**" % (fmt(b[k]), fmt(a[k])) for k in ("roof", "glass", "heavy", "wind", "thunder"))))
    print("| view | weather | level | roof+skylight | window patter | wash outside (heavy) | wind | thunder (RMS) |")
    print("|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))
