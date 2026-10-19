#!/usr/bin/env python
"""
fix_vo_pools.py - turn same-name alias "pools" into pools the engine can actually pick from.

THE BUG
    [user 2026-09-02] "The allies STILL are constantly saying He's hit... its almost like thats the
    only line they have to say, there is zero variety its just Hes hit constantly. Its so obnoxious."

    Several of our sound files build a random pool by declaring many aliases that all share ONE name,
    and coop_aivoice.scr states the assumption in its own comment:

        // ONE NAME, MANY LINES = a random pool. Alias_ListFindRandomRange picks among same-name
        // entries, which is exactly the coop_av_us_mandown shape immediately above

    That is false. qcommon/alias.c, Alias_ListAdd:

        for (node = list->data_list; node != NULL; node = node->next) {
            if (!strcmp(node->alias_name, alias)) {
                Com_DPrintf("DUPLICATE ALIASES: %s and %s\\n", node->alias_name, alias);
                return qtrue;                       <-- returns WITHOUT adding
            }
        }

    The FIRST declaration of a name registers and every later one is discarded. So each pool is one
    line. The user's own console log carries the proof - "DUPLICATE ALIASES: snd_crate_woodsm2 and
    snd_crate_woodsm2" - which nobody had connected to the voice repetition.

    A real random pool is a PREFIX group: Alias_ListFindRandomRange scans the SORTED alias list for
    every name that starts with the requested one, skipping any whose next character is '_', which is
    why `playsound warn_player_cover` legitimately picks from warn_player_cover01..05. So the fix is to
    give the members distinct names that the base name is a prefix of, and keep playing the base name.

    Two engine details the scheme below depends on, both read from alias.c, not from notes:
      * the dedup is a RAW strcmp against the LOWERCASED stored name, so a duplicate whose name has
        any uppercase letter is never rejected - those "pools" already work and are left alone;
      * Alias_ListFindRandom walks sorted_list[min .. min+numfound), i.e. it assumes the accepted names
        are CONTIGUOUS. A member suffix must therefore sort below '_' so it lands next to the base name,
        never after an excluded base_xxx sibling.

TWO SCHEMES, because the two sets of files are different shapes

  A. coop_aivoice.scr + coop_chatter.scr (bug-2316, 2026-09-02) - UNCHANGED.
     Coop-authored, no retail numbering to collide with. Members are grouped by digit-stripped stem and
     renumbered stem1..N, with ONE counter across both files: they independently build pools under the
     same base names (40 collisions, all different wavs), and numbering each file from 1 produced 1,256
     fresh duplicates in one boot, which is how that was caught.

  B. ubersound.scr + uberdialog.scr (bug-3087, 2026-09-27).
     The mod ships its own copy of both (same filename, the code pak mounts last, so it shadows every
     retail copy in main/Pak0, mainta/pak1-4 and maintt/pak1+pak3). Each is all three games
     concatenated plus coop additions. Scheme A would be WRONG here:
       - retail already numbers its own variants with digits (dog_bark1..3 beside a same-name dog_bark
         pool, snd_step_grass1..4, den_attack_001c01..), so digit suffixes collide, and a lookup of
         dog_bark1 would swallow a new dog_bark10;
       - stem grouping would merge distinct retail aliases (foo1, foo2) into one group and renumber them.
     So B groups by EXACT name, and names members 2..N `<name>#<k>`. '#' appears in no other alias
     name in the tree, sorts below digits and '_' (contiguity holds), cannot be absorbed by any other
     lookup, and marks the tool's own output unambiguously - so the tool strips it on input and
     re-derives everything, which makes the output a pure function of the file. Member 1 keeps the
     bare name, so every exact-name call site and every existing prefix lookup sees what it saw before
     plus the rest of its own pool.

     A group (same file, same exact name, same maps field, same `always`) is renumbered only if ALL of:
       1. it has >= 2 DIFFERENT recordings (an identical repeat gains nothing - it is left as is);
       2. every member is all-lowercase (else the engine already admits them all - see above);
       3. its maps filter admits some map (no maps field and no `always` = never loaded);
       4. NO EARLIER declaration of that name - in this file or in any ubersound/*.scr that loads
          before it - admits any map this group admits. That earlier line is what registers today;
          renaming our members would MIX two sets that were never meant to play together. This is the
          "per-map variant" guard from scheme A, made exact: two maps fields conflict only if some
          token of one is a prefix of a token of the other (bLoadForMap, scriptmaster.cpp:417);
       5. it lies outside every block another generator owns (gen_coop_vo_override.py's tail block);
       6. every new name is unique across all ubersound/*.scr and <= 39 chars (alias_name[40]).
     Everything else is reported and left byte-identical. `report` lists each group and the reason.

WHAT STILL PRINTS "DUPLICATE ALIASES" AFTER THIS, AND WHY THAT IS CORRECT
    * later declarations with the SAME recording as the one that registers (retail's per-game copies
      of one alias, and our widened-maps re-declarations in the generated tail block): renaming them
      would add no recording and would randomise their soundparms;
    * coop_*.scr overrides of retail names (coop_pain.scr's player_deathNN, coop_explosions.scr's
      mortarNN, coop_audio.scr's thunderN): coop_*.scr sorts before uber*.scr, so the duplicate line
      IS the override working;
    * groups refused by rule 4 (map-gated).

USAGE
    python docs/tools/fix_vo_pools.py [build]   rewrite any file that is not in pooled form
    python docs/tools/fix_vo_pools.py check     exit 1 if any file would change (also: --check)
    python docs/tools/fix_vo_pools.py report    build's summary plus every scheme-B group and verdict
    Only files under hzm-mohaa-coop-mod/ubersound/ are read, so build/check are deterministic.
"""
import bisect, os, re, sys

MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
UDIR = os.path.join(MOD, "ubersound")
FILES_A = ["coop_aivoice.scr", "coop_chatter.scr"]
FILES_B = ["ubersound.scr", "uberdialog.scr"]
SEP = "#"
MAX_NAME = 39            # alias_name[MAX_ALIAS_NAME_LENGTH = 40], strncpy'd - 40 chars loses the NUL
# bug-3088: same-name groups whose later members are a DIFFERENT sound, not another take of the same one
# (halftrack idle vs the 3x-louder track start, turret move vs its half-pitch variant, the item drop vs the
# Bangalore assembly). Pooling them mixes the wrong sound into a loop or one-shot, so the first member keeps
# winning alone. bug-3088 made that a hand edit of the generated file, which this --check then reported as
# STALE and build.ps1 refused to pack (bug-3160) - the exclusion has to live here.
KEEP_BARE = {"sdkfz_snd_idle", "tank_snd_move", "item_drop"}
# blocks another generator rewrites on every build; touching a line inside one would fight it
FOREIGN = [(b"// >>> BEGIN GENERATED coop VO override", b"// <<< END GENERATED coop VO override")]


# ================================================================================ scheme A (bug-2316)
ALIAS = re.compile(r'^(\s*)(alias(?:cache)?)\s+(\S+)(\s+.*)$', re.I)
MAPSF = re.compile(r'maps\s+"([^"]*)"', re.I)


def split_keep(raw):
    """[(line_bytes, terminator_bytes)] - every line keeps its OWN ending, so a mixed file survives."""
    parts = re.split(rb"(\r\n|\n)", raw)
    return [(parts[i], parts[i + 1] if i + 1 < len(parts) else b"") for i in range(0, len(parts), 2)]


def process_a(raw, seen):
    rows = split_keep(raw)
    lines = [r[0].decode("latin-1") for r in rows]

    # pass 1 - group by digit-stripped stem, and record each member's maps field
    order = {}
    for i, ln in enumerate(lines):
        m = ALIAS.match(ln)
        if not m:
            continue
        name = m.group(3)
        stem = name
        while stem and stem[-1].isdigit():
            stem = stem[:-1]
        mf = MAPSF.search(m.group(4))
        order.setdefault(stem.lower(), []).append((i, name, mf.group(1) if mf else None))

    renamed = skipped = 0
    for key, members in order.items():
        if len(members) < 2:
            continue
        # a group whose members disagree about maps is a per-map variant set, not a pool
        if len(set(x[2] for x in members)) > 1:
            skipped += 1
            continue
        # strip any existing numeric suffix so a re-run renumbers rather than stacking digits
        base = members[0][1]
        while base and base[-1].isdigit():
            base = base[:-1]
        if not base:
            continue
        start = seen.get(base.lower(), 0)
        for n, (i, name, _mf) in enumerate(members, start=1):
            m = ALIAS.match(lines[i])
            lines[i] = "%s%s %s%d%s" % (m.group(1), m.group(2), base, start + n, m.group(4))
            renamed += 1
        seen[base.lower()] = start + len(members)

    out = b"".join(l.encode("latin-1") + t for l, (_old, t) in zip(lines, rows))
    return out, renamed, skipped


# ================================================================================ engine model (B)
def tokenize(data):
    """Events exactly as G_Command_ProcessFile (g_main.cpp) cuts them with COM_ParseExt (q_shared.c):
    `//` and `/* */` comments, quoted strings, `{`/`}` split words, a line = one event, `end`/`server`
    lines skipped. Returns [[(token_bytes, content_start, content_end), ...], ...]."""
    n = len(data)
    ws = re.compile(rb"[\x00-\x20]*")                   # SkipWhitespace compares UNSIGNED: <= ' '
    tail = re.compile(rb"[\x21-\x7a\x7c\x7e\x7f]*")     # word loop: SIGNED char > 32, and not { }

    def parse(pos, allow_lb):
        nl = False
        while True:
            e = ws.match(data, pos).end()
            if not nl and data.find(b"\n", pos, e) >= 0:
                nl = True
            pos = e
            if pos >= n:
                return None, None
            if nl and not allow_lb:
                return None, pos
            c = data[pos]
            if c == 0x2F and data[pos + 1:pos + 2] == b"/":
                e = data.find(b"\n", pos)
                pos = n if e < 0 else e
            elif c == 0x2F and data[pos + 1:pos + 2] == b"*":
                e = data.find(b"*/", pos)
                pos = n if e < 0 else e + 2
            else:
                break
        if c == 0x22:
            s = pos + 1
            e = data.find(b'"', s)
            e = n if e < 0 else e
            return (data[s:e], s, e), min(e + 1, n)
        if c in (0x7B, 0x7D):
            return (data[pos:pos + 1], pos, pos + 1), pos + 1
        e = tail.match(data, pos + 1).end()             # the first byte is always taken, even >= 0x80
        return (data[pos:e].replace(b"\\n", b"\n"), pos, e), e

    events, pos = [], 0
    while pos is not None:
        tok, pos = parse(pos, True)
        if tok is None:
            break
        line = [tok]
        while pos is not None:
            t, pos = parse(pos, False)
            if t is None:
                break
            line.append(t)
        if tok[0].lower() not in (b"end", b"server"):
            events.append(line)
    return events


class Def(object):
    __slots__ = ("file", "seq", "name", "span", "path", "maps", "always", "line", "foreign")


def read_defs(fname, raw, seq0=0):
    """Every alias/aliascache ScriptMaster::RegisterAlias(AndCache) would see, in file order."""
    ranges = []
    for b, e in FOREIGN:
        i = raw.find(b)
        if i >= 0:
            j = raw.find(e, i)
            ranges.append((i, len(raw) if j < 0 else j + len(e)))
    nls = [m.start() for m in re.finditer(b"\n", raw)]
    defs = []
    for ev in tokenize(raw):
        if ev[0][0].lower() not in (b"alias", b"aliascache") or len(ev) < 3:
            continue
        d = Def()
        d.file, d.seq = fname, seq0 + len(defs)
        d.name = ev[1][0].decode("latin-1")
        d.span = (ev[1][1], ev[1][2])
        d.path = ev[2][0].decode("latin-1").replace("\\", "/").lower()
        d.maps, d.always, i = None, False, 3
        while i < len(ev):
            s = ev[i][0].lower()
            if s == b"maps":
                d.maps = ev[i + 1][0].decode("latin-1") if i + 1 < len(ev) else ""
                i += 2
                continue
            if s == b"always":
                d.always = True
            i += 1
        d.line = bisect.bisect_left(nls, d.span[0]) + 1
        d.foreign = any(a <= d.span[0] < b for a, b in ranges)
        defs.append(d)
    return defs


def base_of(name):
    """strip this tool's own `#<k>` suffix - '#' occurs in no other alias name in the tree"""
    i = name.find(SEP)
    return name if i < 0 else name[:i]


def mtoks(d):
    return tuple(t.lower() for t in (d.maps or "").split())


def loads_somewhere(d):
    return d.always or bool(mtoks(d))


def overlap(a, b):
    """can one map name pass both filters? (bLoadForMap: token is a case-insensitive PREFIX of the map)"""
    if not (loads_somewhere(a) and loads_somewhere(b)):
        return False
    if a.always or b.always:
        return True
    return any(x.startswith(y) or y.startswith(x) for x in mtoks(a) for y in mtoks(b))


def plan_b(all_defs, target_files):
    """-> ({id(def): new_name}, [group verdicts]). all_defs is every ubersound/*.scr in engine order."""
    by_base = {}
    for d in all_defs:
        by_base.setdefault(base_of(d.name).lower(), []).append(d)
    taken = set(base_of(d.name).lower() for d in all_defs)

    assign, verdicts, counter = {}, [], {}
    for f in target_files:
        groups, order = {}, []
        for d in all_defs:
            if d.file != f:
                continue
            k = (base_of(d.name), mtoks(d), d.always)     # EXACT name - case matters to the engine
            if k not in groups:
                groups[k] = []
                order.append(k)
            groups[k].append(d)
        for k in order:
            mem = groups[k]
            if len(mem) < 2:
                continue
            base = k[0]
            low = base.lower()
            first = mem[0]
            # members that bring a recording the group does not already have
            fresh, seen_paths = [], set([first.path])
            for d in mem[1:]:
                if d.path not in seen_paths:
                    seen_paths.add(d.path)
                    fresh.append(d)
            why = None
            if low in KEEP_BARE:
                why = "kept bare (bug-3088): a different sound, not another take"
            elif any(d.foreign for d in mem):
                why = "inside another generator's block"
            elif not fresh:
                why = "identical recording repeated - nothing to gain"
            elif base != low:
                why = "uppercase name - engine already admits every member"
            elif not loads_somewhere(first):
                why = "no maps field and not always - never loaded"
            else:
                # seq is the GLOBAL load-order index (read_defs numbers across files in engine order)
                earlier = [o for o in by_base[low] if o.seq < first.seq and overlap(o, first)]
                if earlier:
                    o = earlier[0]
                    why = "map-gated: %s:%d (maps \"%s\") registers this name first on shared maps" % (
                        o.file, o.line, (o.maps or "").strip())
            if why is None:
                n = counter.get(low, 1)
                names = []
                for d in fresh:
                    n += 1
                    names.append("%s%s%d" % (base, SEP, n))
                bad = [x for x in names if x.lower() in taken or len(x) > MAX_NAME]
                if bad:
                    why = "new name collides or exceeds %d chars: %s" % (MAX_NAME, bad[0])
                else:
                    counter[low] = n
                    for d, x in zip(fresh, names):
                        assign[id(d)] = x
                        taken.add(x.lower())
            verdicts.append((f, first.line, base, len(mem), len(fresh) + 1, why))
    return assign, verdicts


def rewrite(raw, defs, assign):
    """Replace ONLY name tokens; every other byte, line ending included, is carried over as is."""
    edits = []
    for d in defs:
        want = assign.get(id(d), base_of(d.name))
        if want != d.name:
            s, e = d.span
            assert raw[s:e].decode("latin-1") == d.name, (d.file, d.line)
            edits.append((s, e, want.encode("latin-1")))
    out = bytearray(raw)
    for s, e, b in sorted(edits, reverse=True):
        out[s:e] = b
    return bytes(out), len(edits)


def assert_shape(fname, old, new, defs_old):
    """T2 gates: endings untouched, same declarations, and only name tokens differ."""
    for pat in (b"\r\n", b"\n"):
        assert old.count(pat) == new.count(pat), "%s: line endings changed" % fname
    defs_new = read_defs(fname, new)
    assert len(defs_new) == len(defs_old), "%s: declaration count changed" % fname
    for a, b in zip(defs_old, defs_new):
        assert (a.path, a.maps, a.always, a.line) == (b.path, b.maps, b.always, b.line), (fname, a.line)
        assert base_of(a.name) == base_of(b.name), (fname, a.line)
    # with every `#<k>` removed the two must be byte-identical: nothing else was touched
    strip = re.compile(re.escape(SEP.encode()) + rb"\d+")
    assert strip.sub(b"", old) == strip.sub(b"", new), "%s: bytes other than #k suffixes changed" % fname


# ================================================================================ driver
def main():
    argv = [a.lower() for a in sys.argv[1:]]
    check = "check" in argv or "--check" in argv
    report = "report" in argv                      # read-only, like check, but always exits 0

    names = sorted((f for f in os.listdir(UDIR) if f.lower().endswith(".scr")), key=lambda s: s.lower())
    raw = dict((f, open(os.path.join(UDIR, f), "rb").read()) for f in names)
    new = dict(raw)

    # ---- A: coop voice files, one counter across both
    seen, total_a = {}, 0
    for f in FILES_A:
        if f not in raw:
            print("  %-22s not found" % f)
            continue
        new[f], r, s = process_a(raw[f], seen)
        total_a += r
        print("  %-22s %4d aliases numbered into pools, %d map-gated groups left alone" % (f, r, s))

    # ---- B: the retail-shaped files, planned against EVERY ubersound/*.scr in engine load order
    #      (G_RegisterSounds / CG_RegisterSounds: FS list, sorted case-insensitively), post-A
    all_defs, per = [], {}
    for f in names:
        per[f] = read_defs(f, new[f], len(all_defs))
        all_defs.extend(per[f])
    # the '#' marker must stay ours alone, or stripping it on input would rename someone else's alias
    for d in all_defs:
        if SEP in d.name and (d.file not in FILES_B or not re.match(r"^[^#]+#\d+$", d.name)):
            print("  REFUSING: %s:%d alias '%s' uses the reserved '%s' - rename it" % (d.file, d.line, d.name, SEP))
            return 1
    targets = [f for f in names if f in FILES_B]
    assign, verdicts = plan_b(all_defs, targets)
    for f in targets:
        out, nedit = rewrite(new[f], per[f], assign)
        assert_shape(f, new[f], out, per[f])
        new[f] = out
        vs = [v for v in verdicts if v[0] == f]
        pools = [v for v in vs if v[5] is None]
        gated = [v for v in vs if v[5] and v[5].startswith("map-gated")]
        print("  %-22s %4d aliases numbered into %d pools, %d map-gated groups left alone, "
              "%d other groups left alone" % (f, sum(v[4] - 1 for v in pools), len(pools), len(gated),
                                               len(vs) - len(pools) - len(gated)))
    total_b = len(assign)
    print("  %d recordings are reachable that the engine was discarding (%d coop voice + %d ubersound)"
          % (total_a + total_b, total_a, total_b))

    if report:
        for f, line, base, k, fresh, why in verdicts:
            print("    %-15s %5d  %-32s %3d decl %3d rec  %s" % (f, line, base, k, fresh,
                                                              "POOL" if why is None else why))

    stale = [f for f in names if new[f] != raw[f]]
    if check or report:
        for f in stale:
            print("  STALE: %s" % f)
        if stale:
            print("  STALE - run: python docs/tools/fix_vo_pools.py build")
        return 1 if (check and stale) else 0
    for f in stale:
        open(os.path.join(UDIR, f), "wb").write(new[f])
        print("  wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
