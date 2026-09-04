#!/usr/bin/env python
"""
find_panic_vo.py - catalogue the fear / panic / prayer dialogue that is actually PLAYABLE on a map.

WHY
    [user 2026-09-01] "I hear allies repeating lines like 'He's hit' over and over again... there's
    probably better dialogue to use for this... having them use dialogue of being afraid, freaking
    out, praying, being scared, anything we can find that sounds concerning."

    The trilogy ships a large scripted-dialogue library, and MOHAA's dialogue .tik files carry the
    ENGLISH SUBTITLE IN A COMMENT directly above each anim block:

        //(MORPH)   //*** It's a firing squad up there!
            dfr_panic_05g               actor_m3l1_panic_05.skc
            {  client {  first sound dfr_panic_05g  }  }

    So the line's text, the animation that performs it, and the sound alias it fires can all be read
    straight out of the .tik. That is the whole catalogue - no guessing which line is which.

WHAT IT CHECKS
    A line is only usable if THREE things hold, and all three have burned this project before:
      1. the anim alias is reachable on the map (the includes-prefix rule, tiki_parse.cpp:345)
      2. the sound alias it fires is DECLARED, and its `maps` field admits this map (the maps-field
         load filter, scriptmaster.cpp:432 - five separate outages so far)
      3. the audio file actually ships (m3l1a has 11 dialogue anims whose .lip and .skc ship but
         whose .wav does not - they animate a mouth in total silence)
    Anything failing one of those is reported separately rather than silently dropped, because
    "there is no panic dialogue" and "the panic dialogue is unaliased" need opposite fixes.

USAGE
    python docs/tools/find_panic_vo.py [--map m3l1a] [--all]
"""
import io, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_map_anims as C

# what "sounds concerning" means, as words that actually appear in these subtitles
WANT = re.compile(
    r"\b(oh god|my god|jesus|christ|lord|pray|hail mary|mother|mama|momma|"
    r"help me|somebody help|get me out|i can'?t|we'?re gonna die|gonna die|we'?re all|"
    r"dying|i'?m hit|hit bad|my leg|my arm|medic|corpsman|"
    r"scared|afraid|no no|please|don'?t want|slaughter|butcher|massacre|"
    r"firing squad|pinned|can'?t move|stay here and die|murder|"
    r"get off the beach|move move|run|go go)\b", re.I)

SKIP = re.compile(r"^\s*$")


def blocks(txt):
    """(subtitle, anim_alias, [fired sounds]) for every anim block in a dialogue tik."""
    out = []
    lines = txt.splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]+(\S+\.skc)", ln)
        if not m:
            continue
        alias = m.group(1)
        # the subtitle lives in a comment on this line or the one above, after ***
        sub = ""
        for probe in (ln, lines[i - 1] if i else ""):
            s = re.search(r"\*\*\*\s*(.+?)\s*$", probe)
            if s:
                # these files are latin-1 and use Word smart quotes (\x92 etc); the Windows console
                # is cp1252 and cannot print several of them, so fold to ASCII before anything else
                sub = (s.group(1).strip()
                       .replace("\x92", "'").replace("\x91", "'")
                       .replace("\x93", '"').replace("\x94", '"')
                       .replace("\x96", "-").replace("\x97", "-").replace("\x85", "..."))
                sub = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in sub)
                break
        # its brace block, for the frame commands
        j, depth, started, buf = i + 1, 0, False, []
        while j < len(lines) and j < i + 40:
            buf.append(lines[j])
            depth += lines[j].count("{")
            if "{" in lines[j]:
                started = True
            depth -= lines[j].count("}")
            if started and depth <= 0:
                break
            j += 1
        snd = re.findall(r"\bsound\s+([A-Za-z_][A-Za-z0-9_]*)", "\n".join(buf))
        out.append((sub, alias, snd))
    return out


def main():
    mapname = sys.argv[sys.argv.index("--map") + 1] if "--map" in sys.argv else "m3l1a"
    show_all = "--all" in sys.argv

    models = ["models/human/dday_29th_private.tik", "models/human/dday_ranger_private.tik",
              "models/human/dday_ranger_captain.tik", "models/human/dday_engineer.tik",
              "models/human/dday_ranger_medic.tik"]
    aliases = {}
    for m in models:
        aliases.update(C.collect_aliases(m, mapname))
    snd_ok, snd_seen = C.sound_aliases(mapname)

    # every dialogue tik that the model chain actually pulled in
    tiks = sorted({t for v in C.ALIAS_TIK.values() for t in v if "dialogue" in t.lower()})
    good, unaliased, noaudio = [], [], []

    for tik in tiks:
        raw = C.read(tik)
        if raw is None:
            continue
        for sub, alias, snd in blocks(raw.decode("latin-1")):
            if not sub or not (show_all or WANT.search(sub)):
                continue
            if alias.lower() not in aliases:
                continue                                    # anim not reachable on this map
            rec = (sub, alias, snd[0] if snd else "", os.path.basename(tik))
            if not snd:
                good.append(rec)                            # silent pose, still usable
                continue
            s = snd[0].lower()
            group = [a for a in snd_seen if a.startswith(s) and (len(a) == len(s) or a[len(s)] != "_")]
            if not group:
                unaliased.append(rec)
            elif not any(snd_ok.get(a) for a in group):
                noaudio.append(rec)
            else:
                good.append(rec)

    print("\n=== PLAYABLE on %s: anim reachable, sound aliased, map admits it ===" % mapname)
    for sub, alias, s, t in sorted(set(good)):
        print("  %-34s %s" % (alias, sub[:96]))
    print("  (%d lines)" % len(set(good)))

    if unaliased:
        print("\n=== HAS ANIM, SOUND ALIAS NOT DECLARED (mouth moves, silence) ===")
        for sub, alias, s, t in sorted(set(unaliased)):
            print("  %-34s fires '%s'  %s" % (alias, s, sub[:70]))
    if noaudio:
        print("\n=== ALIASED BUT NOT LOADABLE HERE (the maps-field filter) ===")
        for sub, alias, s, t in sorted(set(noaudio)):
            print("  %-34s fires '%s'  %s" % (alias, s, sub[:70]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
