"""amb_rain73_table.py - rain73: the attic ambience vs the menu music (dB, offline) at each rain INTENSITY, from the rain73 exe's
own formulas (cl_uiscene.cpp: WxUpdate's derived rain / storm amounts, WxAmbience's three rain layers and wind, the polish73 gains)
and the user's settings (G:\\mohaa-gl2 omconfig, read-only: s_musicvolume 0.797, s_ambientvolume 0.531, ui_wxAmbLevel 2 = MED).
Model as in leaderboard_2026-11-10/amb73_table.py: a loop = volume x s_ambientvolume x the file's RMS; the music = s_musicvolume x
the themes' RMS (-20 dBFS); s_volume on both cancels. Thunder: RMS of the clap file, at the strike's distance (rain73).
"""
import math

MUS, AMB, MUSIC_RMS = 0.796847, 0.531232, -20.0
RMS = dict(roof=(-20.0, -23.0), glass=(-20.1, -23.1), heavy=(-20.0, -23.0), wind=(-20.0, -23.0))
THUNDER_RMS = -33.6
music = 20 * math.log10(MUS) + MUSIC_RMS
db = lambda g: 20 * math.log10(g) if g > 1e-9 else float("-inf")  # noqa: E731
gH = dict(roof=0.75, glass=0.55, heavy=0.50, wind=0.10)
gW = dict(roof=1.00, glass=1.00, heavy=0.90, wind=0.30)


def derived(I):
    rainA = 0.0 if I < 0.03 else (1.0 if I > 0.30 else (I - 0.03) / 0.27)
    stormA = 0.0 if I < 0.70 else (1.0 if I > 0.95 else (I - 0.70) / 0.25)
    rain = rainA * (0.35 + 0.65 * (1.0 if I > 0.6 else I / 0.6))
    overcast = max(0.92, 0.9 + 0.1 * I) if I > 0.05 else 0.92
    return rain, stormA, overcast


def levels(I, view, lvl=2):
    lg = {1: 0.5, 2: 1.0, 3: 1.8}[lvl]
    rain, storm, ovc = derived(I)
    lv = dict(roof=math.sqrt(rain) * (0.45 + 0.55 * I), glass=math.sqrt(rain) * (0.55 + 0.45 * I), heavy=rain * (0.20 + 0.80 * I * I),
              wind=0.40 + 0.25 * ovc + 0.35 * storm)
    g = gW if view == "window" else gH
    out = {}
    for k in lv:
        v = min(1.0, lv[k] * lg * g[k])
        f = RMS[k][0] if view == "window" else RMS[k][1]
        out[k] = db(v) + db(AMB) + f - music
    return out


def thunder(km, view, lvl=2):
    lg = {1: 0.5, 2: 1.0, 3: 1.8}[lvl]
    tv = lg * (0.55 + (0.30 if view == "window" else 0.0))
    tv *= 1.35 if km < 0.8 else max(1.5 / (0.3 + km), 0.35)
    return db(min(tv, 1.0)) + THUNDER_RMS - music


if __name__ == "__main__":
    f = lambda x: "off" if x == float("-inf") else "%+.0f" % x  # noqa: E731
    print("| intensity | view | roof + skylight | window patter | wash outside | wind |")
    print("|---|---|---|---|---|---|")
    for nm, I in (("drizzle 0.10", 0.10), ("light 0.30", 0.30), ("steady 0.50", 0.50), ("heavy 0.78", 0.78), ("storm 1.00", 1.00)):
        for view in ("home", "window"):
            L = levels(I, view)
            print("| %s | %s | %s | %s | %s | %s |" % (nm, "home" if view == "home" else "LOOK OUTSIDE / UP", f(L["roof"]), f(L["glass"]), f(L["heavy"]), f(L["wind"])))
    print()
    print("| strike | delay after the flash | thunder at home | at the window |")
    print("|---|---|---|---|")
    for km in (0.5, 1.0, 2.0, 3.5, 6.0):
        print("| %.1f km | %.1f s | %s | %s |" % (km, km * 2.915 + 0.08, f(thunder(km, "home")), f(thunder(km, "window"))))
