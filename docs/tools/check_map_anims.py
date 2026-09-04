"""Gate: every `anim` and `playsound` a coop map script uses must actually work on that map.

WHY THIS EXISTS
---------------
Four separate defects in one session, all the same shape - a name that looks right, resolves to nothing,
and fails SILENTLY:

  * bug-2253 / bug-2266 - `anim fallen` and eighteen sibling poses were called bare. Most of those
    aliases are ONE-SHOTS: the animation plays, ANIMDONE fires, and the actor falls back to standing. A
    squad of men stood to attention in the surf for three builds running.
  * bug-2275 - `welding_init` is aliased to welding_idle.skc, which LOOPS. A `waittill animdone` after
    it never returns; the thread would have stalled after the props attached but before the torch lit.
  * bug-2248 / bug-2275 - `explode_tank` is declared `maps "m2l2b "` and `welding_torch` is declared
    `maps "m2 ..."`. The engine treats that field as a LOAD FILTER matched as a PREFIX of the map name
    (scriptmaster.cpp:432), so on m3l1a neither alias exists and playsound is silent, with no error.
  * bug-2274 - crate_carry.tik was in an `includes test utils traf holodeck coop` block, and "coop" does
    not prefix-match "m3l1a", so a whole animation pack was simply not loaded.

None of these produce a Script Error. They produce a man standing still, or silence. The only way to be
confident a scene ships working is to resolve the same chains the engine resolves and check the names
against them before shipping - which is what this does.

WHAT IT CHECKS, for every `anim <name>` and `playsound <name>` in the script:

  1. ANIMATION RESOLVES on this map. Walks the model's $include chain exactly as TIKI_ParseIncludes
     does: an `includes <tok...> { }` block is live only if one of its tokens is a PREFIX of the map name
     (tiki_parse.cpp:345, Q_stricmpn(token, mapname, strlen(token))). Same rule for `$mapspec`.
  2. LOOP OR ONE-SHOT, read from the SKC header - flags at offset 8, ANIM_LOOP = 0x20 (animate.h:42).
     Offset 8, not 12: 12 is nBytesUsed (skeletor_animation_file_format.h:37-48), and reading the wrong
     one yields plausible-looking garbage.
  3. THE `waittill animdone` TRAP. A `waittill animdone` within a few lines of a LOOPING anim is
     reported as an error, because that wait never returns.
  4. SOUND ALIASES resolve on this map, maps-field prefix rule included.

The random-alias digit strip is honoured: an alias declared `foo01 ... random` registers as `foo`
(tiki_files.cpp:1046-1057), which is why `prone_beach_idle` is a real name even though only
prone_beach_idle01/02 appear in the .tik text.

USAGE
  python docs/tools/check_map_anims.py                 # m3l1a, the default
  python docs/tools/check_map_anims.py --map m3l1b
Exit code 1 on any failure, so it can gate a build.
"""

import glob
import io
import os
import re
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"

# alias -> the .tik that declared it. Needed because an ANIMATION can fire a sound through a frame
# command, and that name appears nowhere in the map script - see the anim-sound pass in main().
ALIAS_TIK = {}

ANIM_LOOP = 0x20        # animate.h:42
SKC_FLAGS_OFF = 8       # skeletor_animation_file_format.h - 12 is nBytesUsed, not flags
SKC_FRAMETIME_OFF = 16
SKC_NUMFRAMES_OFF = 44

# Aliases the script uses that are NOT model animations - engine states, or names passed to helpers.
NOT_ANIMS = {"start", "stop", "idle"}


# --------------------------------------------------------------------------------- the asset index
_INDEX = None


def index():
    """lower-case path -> bytes, across the mod tree (wins) then the retail paks."""
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    idx = {}
    for d in ("main", "mainta", "maintt"):
        for p in sorted(glob.glob(os.path.join(GOG, d, "*.pk3"))):
            try:
                z = zipfile.ZipFile(p)
            except Exception:
                continue
            for n in z.namelist():
                idx.setdefault(n.lower().replace("\\", "/"), ("zip", p, n))
    # the mod tree overrides retail, exactly as a later-loading pk3 does
    for root, _dirs, files in os.walk(MOD):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, MOD).replace("\\", "/").lower()
            idx[rel] = ("file", full, None)
    _INDEX = idx
    return idx


def read(path):
    e = index().get(path.lower().replace("\\", "/"))
    if not e:
        return None
    if e[0] == "file":
        return open(e[1], "rb").read()
    return zipfile.ZipFile(e[1]).read(e[2])


# --------------------------------------------------------------------------------- the include chain
def prefix_live(tokens, mapname):
    """TIKI_ParseIncludes: live if any token is a PREFIX of the map name."""
    for t in tokens:
        t = t.strip()
        if t and mapname.lower().startswith(t.lower()):
            return True
    return False


def collect_aliases(tik_path, mapname, seen=None, out=None, depth=0):
    """Resolve a .tik's animation aliases, honouring includes/$mapspec gating."""
    if seen is None:
        seen, out = set(), {}
    key = tik_path.lower()
    if key in seen or depth > 24:
        return out
    seen.add(key)
    raw = read(tik_path)
    if raw is None:
        return out
    text = raw.decode("latin-1")

    # Line comments FIRST, block comments after - and never the other way round. These .tik files are
    # full of `//************` banners, and `//***` contains the substring `/*`, so a naive
    # re.sub(r"/\*.*?\*/") matches from the first banner to the `*/` of the QUAKED block at the end of
    # the file and silently deletes 164 lines, including every $include. That is exactly the class of
    # silent-deletion bug this tool exists to catch, so it should not have one of its own.
    lines = []
    inblock = False
    for ln in text.splitlines():
        ln = ln.split("//")[0]
        if inblock:
            k = ln.find("*/")
            if k < 0:
                lines.append("")
                continue
            ln = ln[k + 2:]
            inblock = False
        while "/*" in ln:
            k = ln.find("/*")
            e = ln.find("*/", k + 2)
            if e < 0:
                ln = ln[:k]
                inblock = True
                break
            ln = ln[:k] + ln[e + 2:]
        lines.append(ln)
    # gating stack: list of (depth_at_open, live)
    stack = []
    brace = 0
    curpath = ""
    for ln in lines:
        bare = ln.split("//")[0]

        m = re.match(r"\s*\$?path\s+(\S+)", bare, re.I)
        if m:
            curpath = m.group(1).strip().rstrip("/")

        m = re.match(r"\s*includes\s+(.+?)\s*\{?\s*$", bare, re.I)
        if m:
            stack.append([brace, prefix_live(m.group(1).split(), mapname), False])
        m = re.match(r"\s*\$mapspec\s+(.+?)\s*$", bare, re.I)
        if m:
            stack.append([brace, prefix_live(m.group(1).split(), mapname), False])

        live = all(s[1] for s in stack)

        m = re.match(r"\s*\$include\s+(\S+)", bare, re.I)
        if m and live:
            collect_aliases(m.group(1).strip(), mapname, seen, out, depth + 1)

        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s+(\S+\.skc)(.*)$", bare)
        if m and live:
            name, skc, tail = m.group(1), m.group(2), m.group(3)
            if name.lower() in ("path", "include", "mapspec"):
                pass
            else:
                rnd = bool(re.search(r"\brandom\b", tail, re.I))
                reg = name
                if rnd:
                    reg = re.sub(r"\d+$", "", name) or name
                full = skc if "/" in skc and skc.lower().startswith("models/") else (curpath + "/" + skc if curpath else skc)
                out.setdefault(reg.lower(), []).append(full)
                ALIAS_TIK.setdefault(reg.lower(), set()).add(tik_path)

        brace += bare.count("{") - bare.count("}")
        # a block's `{` is usually on the line AFTER its `includes`/`$mapspec` header, so it is only
        # closed once we have actually been inside it - otherwise it pops on the very line it opens.
        for e in stack:
            if brace > e[0]:
                e[2] = True
        while stack and stack[-1][2] and brace <= stack[-1][0]:
            stack.pop()
    return out


def skc_info(path):
    b = read(path)
    if b is None or len(b) < 48 or b[:4] != b"SKAN":
        return None
    flags = struct.unpack_from("<i", b, SKC_FLAGS_OFF)[0]
    ft = struct.unpack_from("<f", b, SKC_FRAMETIME_OFF)[0]
    nf = struct.unpack_from("<i", b, SKC_NUMFRAMES_OFF)[0]
    return {"loop": bool(flags & ANIM_LOOP), "frames": nf, "dur": nf * ft}


# --------------------------------------------------------------------------------- sound aliases
def sound_aliases(mapname):
    """alias -> True if it is loadable on this map (maps field prefix rule).

    NOTE the second prefix rule, which is a different one: `playsound foo` does not look for an alias
    called exactly "foo". Alias_ListFindRandomRange (qcommon/alias.c:545) does
    `strncmp(requested, candidate, strlen(requested))` and collects EVERY alias that starts with it
    (skipping any whose next character is '_'), then picks one by weight. So `warn_player_cover`
    legitimately resolves to warn_player_cover01..05 and `arty_leadin` to arty_leadin2..7. A checker
    that demands an exact name reports four false failures on this map alone."""
    ok, seen = {}, set()
    paths = [k for k in index() if k.endswith("ubersound.scr") or k.endswith("uberdialog.scr")
             or ((k.startswith("ubersound/") or "/ubersound/" in k) and k.endswith(".scr"))]
    for p in sorted(paths):
        raw = read(p)
        if raw is None:
            continue
        for line in raw.decode("latin-1").splitlines():
            t = line.strip()
            if not (t.startswith("alias ") or t.startswith("aliascache ")):
                continue
            parts = t.split()
            if len(parts) < 3:
                continue
            name = parts[1]
            seen.add(name.lower())
            m = re.search(r'maps\s+"([^"]*)"', t)
            if m is None:
                ok[name.lower()] = True                     # no maps field = every map
            elif prefix_live(m.group(1).split(), mapname):
                ok[name.lower()] = True
            else:
                ok.setdefault(name.lower(), False)
    return ok, seen


# --------------------------------------------------------------------------------- the scan
def main():
    mapname = "m3l1a"
    if "--map" in sys.argv:
        mapname = sys.argv[sys.argv.index("--map") + 1]
    script = os.path.join(MOD, "maps", mapname, "coopified.scr")
    if not os.path.exists(script):
        print("no such coop script: %s" % script)
        return 1

    # every model the coop script plays an animation ON, not just the humans - `removeguys` is the
    # Higgins hull's, and checking humans alone reports it as missing
    models = ["models/human/dday_29th_private.tik", "models/human/dday_ranger_private.tik",
              "models/human/dday_engineer.tik", "models/human/dday_ranger_medic.tik",
              "models/human/dday_29th_private_patient.tik",
              "models/vehicles/higginslite_soldiers.tik", "models/vehicles/higgins_damage.tik",
              "models/vehicles/higginsdoor.tik"]
    aliases = {}
    for m in models:
        aliases.update(collect_aliases(m, mapname))
    print("  include chain for %s resolves %d animation aliases" % (mapname, len(aliases)))

    snd_ok, snd_seen = sound_aliases(mapname)
    print("  %d sound aliases declared, %d loadable here\n" % (len(snd_seen), sum(1 for v in snd_ok.values() if v)))

    src = io.open(script, encoding="latin-1").read().splitlines()
    fails, warns = [], []
    used_anims = set()

    for i, line in enumerate(src):
        bare = line.split("//")[0]

        for m in re.finditer(r'\banim\s+"?([A-Za-z_][A-Za-z0-9_]*)"?(?![\w."])', bare):
            name = m.group(1).lower()
            if m.group(0).rstrip().endswith('"'):
                pass                                    # a quoted literal is still a real alias name
            if bare[m.end():m.end() + 1] == ".":
                continue                                # `anim local.anim` - the name is a variable
            if name in NOT_ANIMS:
                continue
            if name not in aliases:
                fails.append((i + 1, "ANIM NOT REACHABLE on %s: '%s'" % (mapname, m.group(1))))
                continue
            used_anims.add(name)
            infos = [skc_info(p) for p in aliases[name]]
            infos = [x for x in infos if x]
            if not infos:
                warns.append((i + 1, "anim '%s' resolves but its .skc could not be read" % m.group(1)))
                continue
            if any(x["loop"] for x in infos):
                # the welding_init trap: a waittill animdone after a looping anim never returns
                for j in range(i + 1, min(i + 6, len(src))):
                    if re.search(r"waittill\s+animdone", src[j].split("//")[0]):
                        # WARN, not FAIL, and the distinction is real: a looping animation never fires
                        # ANIMDONE, so the wait parks the thread there forever. That is FATAL if the
                        # thread had anything left to do (bug-2275 - the welder would have stalled
                        # before lighting his torch) and BENIGN if it was only holding a pose, which is
                        # what a parked pose-keeper wants. A tool cannot tell those apart; a human can.
                        warns.append((i + 1, "LOOPING anim '%s' followed by `waittill animdone` at line "
                                             "%d - the thread parks there permanently. Fatal if it had "
                                             "more to do; fine if it was only holding a pose."
                                             % (m.group(1), j + 1)))
                        break

        for m in re.finditer(r'\bplaysound\s+"?([A-Za-z_][A-Za-z0-9_]*)"?(?![\w.])', bare):
            name = m.group(1).lower()
            group = [a for a in snd_seen if a.startswith(name) and (len(a) == len(name) or a[len(name)] != "_")]
            if not group:
                fails.append((i + 1, "SOUND ALIAS DOES NOT EXIST: '%s'" % m.group(1)))
            elif not any(snd_ok.get(a) for a in group):
                fails.append((i + 1, "SOUND ALIAS NOT LOADABLE on %s (maps field): '%s' - %d declaration(s), "
                                     "none whose maps list prefixes this map" % (mapname, m.group(1), len(group))))

    # ---- MODEL PATHS. The third silent-failure class: bug-2246, where a spawn of
    # models/fx/dudimpact.tik produced 710 script errors because the TIKI declares no classname, and the
    # general case where a path is simply wrong. A missing model spawns nothing and the guard that tests
    # `!= NULL` passes anyway, because a failed spawn returns 'none', which is NIL, not NULL.
    # comment-stripped, or a `models/...` mentioned in a prose comment is reported as a missing asset
    body = chr(10).join(l.split("//")[0] for l in src)
    mods = set()
    for pat in (r'spawn\s+script_model\s+model\s+"([^"]+)"',
                r'spawn\s+"([^"]+\.tik)"',
                r'model\s+"(models/[^"]+)"',
                r'attachmodel\s+"?(models/[A-Za-z0-9_/.]+)"?'):
        for m in re.finditer(pat, body):
            mods.add(m.group(1))
    for p in sorted(mods):
        q = p if p.lower().endswith(".tik") else p + ".tik"
        if read(q) is None:
            fails.append((0, "MODEL NOT FOUND: '%s'" % p))
    if not any("MODEL NOT FOUND" in f[1] for f in fails):
        print("  %d model paths referenced, all resolved\n" % len(mods))

    # ---- SOUNDS FIRED BY AN ANIMATION, not by our script.
    #
    # [bug-2280] This is the hole that shipped 115 console errors in a single playtest. workers.tik's
    # sledge_hammer_action carries `18 sound sledgehammer` as a frame command; the name appears nowhere
    # in coopified.scr, so a gate that only reads `playsound` lines cannot see it - and every retail
    # declaration of sledgehammer1..4 is gated to maps "m2 ..." and so does not exist on m3l1a.
    # PlaySound then logs an ERROR once per swing.
    #
    # For every alias the script actually uses, scan the .tik that declared it for `sound <name>` and
    # put those names through the same maps-field prefix test.
    fired = {}
    for name in used_anims:
        for tik in ALIAS_TIK.get(name, ()):
            raw = read(tik)
            if raw is None:
                continue
            txt = raw.decode("latin-1")
            # [2026-09-01] SCOPE TO THIS ANIM'S OWN BLOCK. This used to scan the WHOLE tik, so one used
            # alias dragged in the frame commands of every other anim in the file - on m3l1a a single
            # reference to dfr_panic_05g reported 11 hard FAILures for dialogue lines the map never
            # plays (verified: zero references to any of them in m3l1a.scr or coopified.scr). A gate
            # that cries wolf gets ignored, which is worse than not having one. The block shape is
            #     <alias>   <file>.skc
            #     {  client {  first sound <name>  }  }
            # so read from the declaration line to the end of its brace block, and no further.
            m = re.search(r"^[ \t]*" + re.escape(name) + r"[ \t]+\S+\.skc[^\n]*\n",
                          txt, re.I | re.M)
            if not m:
                continue
            i, depth, started = m.end(), 0, False
            while i < len(txt):
                if txt[i] == "{":
                    depth += 1
                    started = True
                elif txt[i] == "}":
                    depth -= 1
                    if started and depth <= 0:
                        i += 1
                        break
                i += 1
            for mm in re.finditer(r"\bsound\s+([A-Za-z_][A-Za-z0-9_]*)", txt[m.end():i]):
                fired.setdefault(mm.group(1).lower(), set()).add(os.path.basename(tik))
    for name in sorted(fired):
        group = [a for a in snd_seen if a.startswith(name) and (len(a) == len(name) or a[len(name)] != "_")]
        if not group:
            fails.append((0, "ANIM-FIRED SOUND DOES NOT EXIST: '%s' (from %s)"
                          % (name, ", ".join(sorted(fired[name])))))
        elif not any(snd_ok.get(a) for a in group):
            fails.append((0, "ANIM-FIRED SOUND NOT LOADABLE on %s: '%s' (from %s) - %d declaration(s), "
                             "none whose maps list prefixes this map"
                          % (mapname, name, ", ".join(sorted(fired[name])), len(group))))
    if fired:
        print("  %d sound(s) fired by animation frame commands, all resolved\n" % len(fired)
              if not any("ANIM-FIRED" in f[1] for f in fails) else "")

    for ln, msg in warns:
        print("  WARN  %s:%d  %s" % (os.path.basename(script), ln, msg))
    for ln, msg in fails:
        print("  FAIL  %s:%d  %s" % (os.path.basename(script), ln, msg))

    if fails:
        print("\n  %d FAILURE(S) - these would ship silently broken." % len(fails))
        return 1
    print("\n  OK - every anim and playsound in %s resolves on this map." % os.path.basename(script))
    return 0


if __name__ == "__main__":
    sys.exit(main())
