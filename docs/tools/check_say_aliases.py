#!/usr/bin/env python
"""
check_say_aliases.py - verify every `say` / `sayd` dialogue alias a map script uses is actually
declared AND loadable on that map.

WHY THIS EXISTS
    [user 2026-09-01, reported twice] "I dont hear the captains dialogue... he may be getting drowned
    out" and then, after a duck was added, "I cant hear the captains dialogue still, i see his mouth
    moving, either it's being overwritten by everything else or idk what".

    "The mouth moves but there is no sound" is a specific, diagnosable failure, not a mixing problem.
    `<actor> say <alias>` drives BOTH the lipsync animation and the audio; the animation comes from
    the .skc/.lip pair and the audio comes from the sound ALIAS. If the alias is missing, or is
    declared with a `maps` field that does not admit this map, the mouth still moves and the line is
    silent. No error is printed for a missing dialogue alias on the `say` path.

    check_map_anims.py already gates `playsound` and animation frame commands. It never looked at
    `say`, which is how essentially ALL scripted dialogue in this game is triggered - so the single
    largest source of dialogue in the trilogy was ungated. This closes that.

THE MAPS-FIELD FILTER (scriptmaster.cpp:432)
    A sound alias may carry `maps "m2 e1 dm"`. Those tokens are matched as PREFIXES of the live map
    name, and an alias whose filter does not match IS NOT LOADED AT ALL. Five separate outages in
    this project so far (explode_tank twice, welding_torch, sledgehammer, impact_leavewater).

USAGE
    python docs/tools/check_say_aliases.py [--map m3l1a]
Exit 1 if any line a map speaks cannot be heard on that map.
"""
import io, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_map_anims as C


def scripts_for(mapname):
    out = []
    for p in (os.path.join(C.MOD, "maps", mapname + ".scr"),
              os.path.join(C.MOD, "maps", mapname, "coopified.scr")):
        if os.path.exists(p):
            out.append(p)
    return out


def audio_index():
    """Every audio file that actually ships, lowercased, from every pk3 and loose path.

    [2026-09-01] THE THIRD FAILURE MODE, and the one that actually silenced the captain. A dialogue
    alias can be perfectly declared and admitted by its maps field while pointing at a .wav that is
    NOT IN THIS EDITION. War Chest ships a different dialogue set from the one uberdialog.scr was
    written against: `streamed_dfr_scripted_M3L1_015g` resolves to sound/dialogue/m3l1/A/
    dfr_m3l1_015h2.WAV, and only dfr_scripted_M3L1_015g.wav is present. The engine prints nothing on
    the `say` path when the file is absent - the lipsync still plays off the .skc, so the mouth moves
    in silence, which is exactly what was reported twice.
    """
    import zipfile
    out = set()
    for root in (GAME_ROOTS):
        for sub in ("main", "mainta", "maintt"):
            d = os.path.join(root, sub)
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                p = os.path.join(d, f)
                if f.lower().endswith(".pk3"):
                    try:
                        z = zipfile.ZipFile(p)
                    except Exception:
                        continue
                    for n in z.namelist():
                        if n.lower().endswith((".wav", ".mp3", ".ogg")):
                            out.add(n.lower().replace("\\", "/"))
                elif os.path.isdir(p):
                    for dp, dn, fn in os.walk(p):
                        for x in fn:
                            if x.lower().endswith((".wav", ".mp3", ".ogg")):
                                rel = os.path.relpath(os.path.join(dp, x), d)
                                out.add(rel.lower().replace("\\", "/"))
    # the mod's own tree ships loose too
    for dp, dn, fn in os.walk(C.MOD):
        for x in fn:
            if x.lower().endswith((".wav", ".mp3", ".ogg")):
                rel = os.path.relpath(os.path.join(dp, x), C.MOD)
                out.add(rel.lower().replace("\\", "/"))
    return out


GAME_ROOTS = [r"G:\GOG\Medal of Honor - Allied Assault War Chest"]


def alias_paths():
    """alias name (lower) -> the sound path it points at, across every ubersound/uberdialog."""
    import zipfile
    out = {}
    pat = re.compile(r'^\s*alias(?:cache)?\s+(\S+)\s+(\S+\.(?:wav|mp3|ogg))', re.I)

    def feed(txt, overwrite=False):
        # LAST DECLARATION WINS, because that is how the engine resolves it: the mod's pk3 sorts after
        # every retail pak, so a re-pointed alias in hzm-mohaa-coop-mod/ubersound overrides Pak0's.
        # This used to setdefault unconditionally, which made the tool report the RETAIL path even
        # after the mod had corrected it - a checker lying about a fix it was built to verify.
        for ln in txt.splitlines():
            m = pat.match(ln)
            if m:
                k, v = m.group(1).lower(), m.group(2).lower().replace("\\", "/")
                if overwrite or k not in out:
                    out[k] = v

    # the mod's copies win, so read them LAST
    for root in GAME_ROOTS:
        for sub in ("main", "mainta", "maintt"):
            d = os.path.join(root, sub)
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if not f.lower().endswith(".pk3"):
                    continue
                try:
                    z = zipfile.ZipFile(os.path.join(d, f))
                except Exception:
                    continue
                for n in z.namelist():
                    if re.search(r"ubersound|uberdialog", n, re.I) and n.lower().endswith(".scr"):
                        feed(z.read(n).decode("latin-1"))
    ud = os.path.join(C.MOD, "ubersound")
    if os.path.isdir(ud):
        for f in sorted(os.listdir(ud)):
            if f.lower().endswith(".scr"):
                feed(io.open(os.path.join(ud, f), encoding="latin-1").read(), overwrite=True)
    return out


def main():
    mapname = sys.argv[sys.argv.index("--map") + 1] if "--map" in sys.argv else "m3l1a"
    snd_ok, snd_seen = C.sound_aliases(mapname)
    have = audio_index()
    apath = alias_paths()

    # `say`/`sayd` take a bare alias; the actor may be $foo, self, local.x or a targetname
    SAY = re.compile(r"\b(say|sayd)\s+([A-Za-z_][A-Za-z0-9_\-]*)", re.I)

    missing, filtered, noaudio, ok = [], [], [], 0
    for path in scripts_for(mapname):
        base = os.path.basename(path)
        for i, raw in enumerate(io.open(path, encoding="latin-1").read().splitlines()):
            line = raw.split("//")[0]
            for m in SAY.finditer(line):
                alias = m.group(2)
                a = alias.lower()
                # dialogue aliases resolve as PREFIX GROUPS the same way sound aliases do
                group = [x for x in snd_seen
                         if x.startswith(a) and (len(x) == len(a) or x[len(a)] not in "abcdefghijklmnopqrstuvwxyz0123456789_")]
                if a in snd_seen:
                    group = [a]
                if not group:
                    missing.append((base, i + 1, alias, raw.strip()[:88]))
                elif not any(snd_ok.get(x) for x in group):
                    filtered.append((base, i + 1, alias, raw.strip()[:88]))
                else:
                    # declared and admitted - but does the file it points at actually ship here?
                    live = [x for x in group if snd_ok.get(x)]
                    paths = [apath.get(x) for x in live if apath.get(x)]
                    if paths and not any(p in have for p in paths):
                        noaudio.append((base, i + 1, alias, paths[0]))
                    else:
                        ok += 1

    print("  %d `say` lines checked on %s - %d resolve" % (ok + len(missing) + len(filtered), mapname, ok))
    if missing:
        print("\n  NO SUCH DIALOGUE ALIAS - the mouth animates, the line is SILENT:")
        for b, ln, a, txt in missing:
            print("    %s:%-6d %-40s %s" % (b, ln, a, txt))
    if filtered:
        print("\n  DECLARED BUT ITS `maps` FIELD EXCLUDES %s - also silent:" % mapname)
        for b, ln, a, txt in filtered:
            print("    %s:%-6d %-40s %s" % (b, ln, a, txt))
    if noaudio:
        # [2026-09-01, bug-2299] ADVISORY ONLY - THIS CHECK HAS BEEN WRONG BEFORE, and confidently.
        # It compares an alias's literal path against a pak sweep, and that sweep missed real files:
        # it indexed the GOG tree while the game actually runs from G:/mohaa-gl2, and it ignored the
        # .wav/.mp3 fallback the codec layer does. On that basis I told the user five dialogue lines
        # "have no audio in this edition". They replied "there sno way the sound files dont exist,
        # ive heard them before", and they were right.
        # THE AUTHORITATIVE TEST IS THE ENGINE'S OWN LOG: a sound that genuinely fails to load prints
        # "Couldn't load sound: <path>" to qconsole.log. Check that before believing anything here.
        print("\n  [ADVISORY - confirm against qconsole.log \"Couldn't load sound\" before trusting]")
        print("  alias resolves, but this sweep did not find its file:")
        for b, ln, a, p in noaudio:
            print("    %s:%-6d %-40s -> %s" % (b, ln, a, p))
    if not missing and not filtered and not noaudio:
        print("\n  OK - every spoken line on this map can actually be heard.")
    return 1 if (missing or filtered or noaudio) else 0


if __name__ == "__main__":
    sys.exit(main())
