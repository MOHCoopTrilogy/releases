#!/usr/bin/env python
"""
find_dread_vo.py - sweep the WHOLE trilogy alias table for fear / panic / prayer / pleading /
dread VO that is ACTUALLY PLAYABLE on one map.

Companion to find_panic_vo.py, which only reads the dialogue .tik files (i.e. lines an ACTOR
can be told to perform with `anim`). This one reads the far larger source: every
`alias`/`aliascache` declaration in ubersound/*.scr + uberdialog.scr, which is what
`<actor> playsound <name>` actually draws from.

THREE INDEPENDENT GATES, all of which have burned this project:
  1. DECLARED - the alias exists at all.
  2. ADMITTED - its `maps "..."` field prefix-matches the live map name
     (ScriptMaster::RegisterAliasAndCache -> bLoadForMap, fgame/scriptmaster.cpp:432).
     `always` bypasses it; no maps field at all also passes.
  3. SHIPPED  - the .wav/.mp3 it points at is present in this edition. War Chest ships a
     different dialogue set from retail AA; a missing file is SILENT with no console error.

SUBTITLES. The alias table carries `subtitle "..."` on the scripted mission lines, but the
GENERIC soldier reel (the panic/fear/damage pools) carries none. For those the English text is
in a `///` comment above the `first sound <alias>` frame command inside the dialogue .tik, so
this builds the text map from both sources and keys it on the alias name AND on the audio file
basename (the reel aliases are indirections: dfr_panic_35c_114 -> dfr_panic_33h_1.wav).

USAGE
  python docs/tools/find_dread_vo.py [--map m3l1a] [--all] [--audit <alias>] [--dir <path>]
"""
import os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_map_anims as C

MOODS = [
    ("PRAYER / GOD",      r"\b(oh god|my god|god help|dear god|jesus|christ|lord|pray|prayer|hail mary|amen|sweet mother)\b"),
    ("CRYING FOR HELP",   r"\b(help me|somebody help|help us|get me out|medic|corpsman|i'?m hit|hit bad|my leg|my arm|my hand|i'?m bleeding|don'?t leave me)\b"),
    ("FEAR / DREAD",      r"\b(scared|afraid|terrif|fear|panic|nightmare|hell|slaughter|butcher|massacre|murder|firing squad|no chance|we'?re dead|gonna die|we'?re gonna|all gonna|not gonna make|can'?t take|too many|oh no|no no)\b"),
    ("PLEADING / GIVING UP", r"\b(please|i can'?t|can'?t do|i won'?t|don'?t want|leave me|let me|stay here and die|give up|it'?s over|forget it|no more)\b"),
    ("PINNED / TRAPPED",  r"\b(pinned|can'?t move|nowhere to|trapped|cut off|surrounded|no cover|stuck)\b"),
    ("MAN DOWN / LOSS",   r"\b(man down|he'?s hit|he'?s dead|they got|got him|he'?s gone|dead|killed|casualt)\b"),
    ("GET OFF THE BEACH", r"\b(off the beach|get off|move move|keep moving|the wall|the seawall|shingle|run|go go go)\b"),
]
MOOD_RE = [(n, re.compile(p, re.I)) for n, p in MOODS]

ALIAS_RE = re.compile(r'^\s*(alias|aliascache)\s+(\S+)\s+(\S+)\s*(.*)$', re.I)


def ascii_(s):
    s = (s.replace("\x92", "'").replace("\x91", "'").replace("\x93", '"')
          .replace("\x94", '"').replace("\x96", "-").replace("\x97", "-").replace("\x85", "..."))
    return "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in s).strip()


def alias_files():
    idx = C.index()
    return sorted(k for k in idx
                  if k.endswith(".scr") and ("ubersound" in k or "uberdialog" in k))


# ------------------------------------------------------------------ subtitle text, two sources
def subtitle_map():
    """key (lower alias name, and lower audio basename) -> english text."""
    txt = {}
    idx = C.index()
    for k in sorted(idx):
        if not (k.endswith(".tik") and "dialogue" in k):
            continue
        raw = C.read(k)
        if raw is None:
            continue
        lines = raw.decode("latin-1").splitlines()
        for i, ln in enumerate(lines):
            m = re.search(r"\bfirst\s+sound\s+([A-Za-z_][A-Za-z0-9_]*)", ln)
            if not m:
                continue
            name = m.group(1).lower()
            for probe in (lines[i - 1] if i else "", lines[i - 2] if i > 1 else "", ln):
                s = re.search(r"///+\s*(.+?)\s*$", probe)
                if s and s.group(1).strip("/ \t"):
                    t = ascii_(s.group(1)).strip("/ \t")
                    if t and not t.startswith("*") and len(t) > 2:
                        txt.setdefault(name, t)
                    break
    for p in alias_files():
        raw = C.read(p)
        if raw is None:
            continue
        for ln in raw.decode("latin-1").splitlines():
            bare = ln.split("//")[0]
            m = ALIAS_RE.match(bare)
            if not m:
                continue
            s = re.search(r'subtitle\s+"([^"]*)"', bare)
            if s:
                txt.setdefault(m.group(2).lower(), ascii_(s.group(1)))
                txt.setdefault(os.path.splitext(os.path.basename(m.group(3)))[0].lower(),
                               ascii_(s.group(1)))
    return txt


# ------------------------------------------------------------------ the declaration table
def declarations(mapname):
    out = []
    for p in alias_files():
        raw = C.read(p)
        if raw is None:
            continue
        for n, ln in enumerate(raw.decode("latin-1").splitlines(), 1):
            bare = ln.split("//")[0]
            m = ALIAS_RE.match(bare)
            if not m:
                continue
            kind, name, snd, tail = m.group(1).lower(), m.group(2), m.group(3), m.group(4)
            mm = re.search(r'maps\s+"([^"]*)"', tail)
            always = bool(re.search(r"\balways\b", tail, re.I))
            if mm is None:
                admitted, mapsfield = True, "(none)"
            else:
                mapsfield = mm.group(1).strip()
                admitted = always or C.prefix_live(mapsfield.split(), mapname)
            if always:
                admitted = True
            sub = re.search(r'subtitle\s+"([^"]*)"', tail)
            out.append(dict(file=p, line=n, kind=kind, name=name, snd=snd,
                            maps=mapsfield, always=always, admitted=admitted,
                            subtitle=ascii_(sub.group(1)) if sub else "",
                            ships=C.read(snd) is not None))
    return out


def main():
    mapname = sys.argv[sys.argv.index("--map") + 1] if "--map" in sys.argv else "m3l1a"
    audit = sys.argv[sys.argv.index("--audit") + 1] if "--audit" in sys.argv else None
    subdir = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else None
    show_all = "--all" in sys.argv

    txt = subtitle_map()
    decls = declarations(mapname)
    print("  %d alias declarations across %d alias files" % (len(decls), len(alias_files())))
    print("  %d admitted on %s, %d of those with audio present\n"
          % (sum(1 for d in decls if d["admitted"]), mapname,
             sum(1 for d in decls if d["admitted"] and d["ships"])))

    if audit:
        a = audit.lower()
        grp = [d for d in decls if d["name"].lower().startswith(a)
               and (len(d["name"]) == len(a) or d["name"][len(a)] != "_")]
        print("=== PREFIX GROUP '%s' - %d declaration(s) the engine may draw" % (audit, len(grp)))
        for d in grp:
            base = os.path.splitext(os.path.basename(d["snd"]))[0].lower()
            t = d["subtitle"] or txt.get(d["name"].lower(), "") or txt.get(base, "")
            print("  %-26s %-54s adm=%d ships=%d  %s"
                  % (d["name"], d["snd"], d["admitted"], d["ships"], t[:58]))
        real = [d for d in grp if d["admitted"] and d["ships"] and "null.wav" not in d["snd"].lower()]
        wavs = sorted({d["snd"].lower() for d in real})
        print("  -> %d draws are real audio, %d DISTINCT files" % (len(real), len(wavs)))
        return 0

    if subdir:
        s = subdir.lower().replace("\\", "/")
        rows = []
        for d in decls:
            if s not in d["snd"].lower().replace("\\", "/"):
                continue
            base = os.path.splitext(os.path.basename(d["snd"]))[0].lower()
            t = d["subtitle"] or txt.get(d["name"].lower(), "") or txt.get(base, "")
            rows.append((d["snd"].lower(), d["name"], d["admitted"], d["ships"], t))
        byfile = {}
        for snd, name, adm, sh, t in rows:
            k = snd
            if k not in byfile or len(byfile[k][0]) > len(name):
                byfile[k] = (name, adm, sh, t)
            else:
                p = byfile[k]
                byfile[k] = (p[0], p[1] or adm, p[2], p[3] or t)
        for k in sorted(byfile):
            name, adm, sh, t = byfile[k]
            print("  %-26s %-46s adm=%d ships=%d  %s"
                  % (name, os.path.basename(k), adm, sh, t[:70]))
        print("  -> %d distinct audio files, %d admitted+shipping"
              % (len(byfile), sum(1 for v in byfile.values() if v[1] and v[2])))
        return 0

    seen = {}
    for d in decls:
        if not (d["admitted"] and d["ships"]):
            continue
        if "null.wav" in d["snd"].lower():
            continue
        base = os.path.splitext(os.path.basename(d["snd"]))[0].lower()
        t = d["subtitle"] or txt.get(d["name"].lower(), "") or txt.get(base, "")
        if not t:
            continue
        key = d["snd"].lower()
        if key in seen and len(seen[key]["name"]) <= len(d["name"]):
            continue
        seen[key] = dict(name=d["name"], snd=d["snd"], text=t, maps=d["maps"])

    buckets = collections.OrderedDict((n, []) for n, _ in MOOD_RE)
    for k, v in sorted(seen.items()):
        for n, rx in MOOD_RE:
            if rx.search(v["text"]):
                buckets[n].append(v)
                break

    total = 0
    for n, rows in buckets.items():
        if not rows and not show_all:
            continue
        print("=== %s  (%d lines playable on %s)" % (n, len(rows), mapname))
        for v in sorted(rows, key=lambda r: r["text"].lower()):
            print("   %-30s %-44s %s" % (v["name"], os.path.basename(v["snd"]), v["text"][:88]))
        total += len(rows)
        print("")
    print("TOTAL %d distinct playable lines matched a dread/fear/prayer mood on %s" % (total, mapname))
    return 0


if __name__ == "__main__":
    sys.exit(main())
