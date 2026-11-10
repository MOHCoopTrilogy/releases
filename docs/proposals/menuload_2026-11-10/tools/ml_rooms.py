r"""ml_rooms.py - frame sequences of every 3D menu room transition, both directions, on the private client G:\mohaa-menuload
(same launch policy as ml_run.py: harness_window guard, 1080p second screen, muted, no mouse / pad / joystick).

    python ml_rooms.py run <tag> [--ingame <map>]    boot -> attic, then every leg below at 20 fps (screenshotJPEG every 50 ms);
                                                     --ingame: start <map> first and take the legs from the in-game Main Menu
A cfg cannot drive the menu (TRAPS: the hotspots' own `uiafter` / Cbuf_AddText run AFTER the whole cfg), so each step is its own
cfg chained by `uiafter <s> exec ml_rNNN.cfg`: the command buffer is empty between steps, exactly as after a real click.
The engine's pop-in check prints "^~^~^ MENULOAD late model|prop <name>" for anything a room draws before it was registered -
the run reports every such line, plus the MENULOAD ready lines. Frames land in RUNS\<tag>\<leg>\.
"""
import os, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ml_run as R  # noqa: E402

URC = r"H:\hzm_work\menuload\urc\ui"      # main.urc / multiplayer.urc / hzm_records3d.urc as shipped (code pak)
FPS_DT = 0.05
LEG_FRAMES = 50                           # 2.5 s of menu time per leg

# (leg name, urc, hotspot | None, raw command when hotspot is None)
LEGS = [
    ("attic_to_mp", "main.urc", "mp", None),
    ("mp_to_bench", "multiplayer.urc", "rack", None),
    ("bench_to_mp", "hzm_wpnview.urc", "@esc", None),
    ("mp_to_attic", "multiplayer.urc", "@esc", None),
    ("attic_to_records", "main.urc", "records", None),
    ("records_to_medals", "hzm_records3d.urc", "medals", None),
    ("medals_to_records", "hzm_medals3d.urc", "@esc", None),
    ("records_to_attic", "hzm_records3d.urc", "@esc", None),
    ("attic_to_film", "main.urc", "film", None),
    ("film_to_attic", None, None, "popmenu 1"),
    ("attic_to_warmap", "main.urc", "newgame", None),
    ("warmap_to_attic", "hzm_newgame3d.urc", "@esc", None),
    ("attic_to_window", "main.urc", "window", None),
    ("window_to_attic", None, None, "globalwidgetcommand atticscene sceneback"),
    ("attic_to_lookup", "main.urc", "lookup", None),
    ("lookup_to_attic", None, None, "globalwidgetcommand atticscene sceneback"),
    ("attic_to_brief", "main.urc", "brief", None),
    ("brief_to_attic", "hzm_newgame3d.urc", "@esc", None),
]


def hot_cmd(urc, name):
    t = open(os.path.join(URC, urc), encoding="latin-1").read()
    if name == "@esc":                      # the menu's own ESC / BACK command (a bare popmenu does nothing: it takes an argument)
        return re.search(r'^escapecommand "([^"]*)"', t, re.M).group(1)
    m = re.search(r'^scenehot "%s" (?:\S+ ){4}"((?:[^"\\]|\\.)*)"' % re.escape(name), t, re.M)
    if not m:
        raise SystemExit("no scenehot %s in %s" % (name, urc))
    return m.group(1).replace('\\"', '"')


def steps():
    """[(cfg lines, delay to the next step in s)] - one screenshot per step"""
    S = []
    only = os.environ.get("ML_LEGS", "").split()          # a subset of the legs, by name (default: all)
    for leg, urc, hot, raw in LEGS:
        if only and leg not in only:
            continue
        cmd = hot_cmd(urc, hot) if hot else raw
        S.append((["echo ^~^~^ MLR leg %s" % leg, cmd, "screenshotJPEG mlr_%s_000" % leg], FPS_DT))
        for k in range(1, LEG_FRAMES):
            S.append((["screenshotJPEG mlr_%s_%03d" % (leg, k)], FPS_DT))
        S.append((["echo ^~^~^ MLR end %s" % leg], 1.0))
        if os.environ.get("ML_INGAME") and leg.endswith("_to_attic"):
            # in a game a room's BACK can close the menu stack down to the game: re-open the Main Menu the way dm_main's
            # button does ("popmenu 0; wait 250; pushmenu main"), so every leg starts in the attic
            S.append((["popmenu 0"], 0.3))
            S.append((["pushmenu main"], 2.0))
    S.append((["echo ^~^~^ ML stage done", "quit"], 0))
    return S


def write_chain(first_exec_line):
    S = steps()
    for i, (lines, dt) in enumerate(S):
        nxt = ["uiafter %.3f exec ml_r%04d.cfg" % (dt, i + 1)] if i + 1 < len(S) else []
        open(os.path.join(R.MAINTT, "ml_r%04d.cfg" % i), "w", newline="\n").write("\n".join(lines + nxt) + "\n")
    return first_exec_line


def run(tag, ingame=None):
    if ingame:
        os.environ["ML_INGAME"] = "1"
    for fn in os.listdir(R.MAINTT):
        if re.match(r"ml_r\d{4}\.cfg$", fn):
            os.remove(os.path.join(R.MAINTT, fn))
    write_chain(None)
    os.environ["ML_TAIL"] = "exec ml_r0000.cfg"       # ml_run appends ML_TAIL after its boot / in-game cycle
    out = R.run(tag, None, ingame or "m2l1", shots=False, cycles=1 if ingame else 0, rooms=bool(ingame))
    # sort frames into one folder per leg
    for fn in os.listdir(out):
        m = re.match(r"mlr_(.+)_\d{3}\.jpg$", fn)
        if m:
            d = os.path.join(out, m.group(1))
            os.makedirs(d, exist_ok=True)
            shutil.move(os.path.join(out, fn), os.path.join(d, fn))
    late = [l.rstrip() for l in open(os.path.join(out, "qconsole.log"), errors="ignore") if "MENULOAD late" in l]
    print("late registrations: %d" % len(late), *late[:30], sep="\n  ")
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "run":
        print(run(a[1], a[3] if len(a) > 3 and a[2] == "--ingame" else None))
