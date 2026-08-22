#!/usr/bin/env python3
"""
Audit: which maps have SCRIPTED SCENE ACTORS that the AI personality roll can break?

[user 2026-08-22, after bug-2032] "I am willing to bet other scripted scenes across the
trilogy received that same break."

THE DEFECT CLASS. With coop_aiDynamic 1 every german Actor gets a combat personality
(aggressive / take cover / flank / prone) from aihandler.scr -> officer.scr::
coop_apply_personality. That label consults coop_isProtectedActor, which matches on:
    * flags["coop_sceneActor"] == 1                (set directly by a map)
    * level.coop_sceneActorNames[...]              (a per-map targetname list)
    * structural tests: targetname ai_alarm, type_attack alarm, alarmthread,
      type_disguise sentry/officer/rover, and salute on disguise maps
Anything else is fair game. m2l2a, m6l2a and the lobbies were retrofitted with the name
list when their scene crews broke; every other map was left as-is. On m1l1 that let the
checkpoint guards open fire on the disguised Americans standing beside them, wander into
the intro truck, and pull the scripted panzerschreck off its mark - freezing the mission.

DETECTION. A map is treating an actor as SCENERY when it does any of:
    exec global/disable_ai.scr      - explicitly switching off his think
    anim_scripted <x>               - driving him with a scripted animation
    threatbias ignoreme             - telling the AI system to ignore him
Those are the same markers m1l1 used. This does NOT prove exposure on its own - the actor
may be american, or covered by a structural test - so the output is a RANKED SUSPECT LIST
for human review, not a verdict.
"""
import io, os, re, sys, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAPS = os.path.join(ROOT, "hzm-mohaa-coop-mod", "maps")

SCENE_MARKERS = [
    (re.compile(r'exec\s+global/disable_ai\.scr', re.I), "disable_ai"),
    (re.compile(r'\banim_scripted\b', re.I), "anim_scripted"),
    (re.compile(r'threatbias\s+ignoreme', re.I), "threatbias ignoreme"),
]
PROTECT = re.compile(r'coop_sceneActorNames|coop_sceneActor', re.I)
# a map that never lets a german near a scene is far less interesting
GERMAN = re.compile(r'\bgerman\b', re.I)


# Whose side is the scripted actor on? The personality gate is `self.team == "german"`, so an
# allied/friendly scene actor is not exposed at all. Classify by the entity NAME the marker is
# applied to - map authors name these things honestly (weh_ = Wehrmacht, friendly/ally/POW etc).
AXIS_HINT = re.compile(r'weh_|german|axis|ger_|nazi|ss_|afrika|wehrmacht', re.I)
ALLY_HINT = re.compile(r'friendly|ally|allied|prisoner|pow|civilian|scientist|manon|american|british|russian', re.I)


def side_of(code):
    """axis / ally / unknown, from the entity the marker is applied to."""
    m = re.match(r"\s*(?:local\.\w+\s*=\s*)?(.+?)\s+(?:exec|anim_scripted|threatbias)", code)
    subj = m.group(1) if m else code
    if ALLY_HINT.search(subj):
        return 'ally'
    if AXIS_HINT.search(subj):
        return 'axis'
    return 'unknown'


def scan(path):
    try:
        txt = io.open(path, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
    except OSError:
        return None
    lines = txt.split("\n")
    hits = collections.Counter()
    sides = collections.Counter()
    for ln in lines:
        code = ln.split("//", 1)[0]
        if not code.strip():
            continue
        for rx, name in SCENE_MARKERS:
            if rx.search(code):
                hits[name] += 1
                sides[side_of(code)] += 1
    if not hits:
        return None
    protected = bool(PROTECT.search(txt))
    german = len(GERMAN.findall(txt))
    return {"hits": hits, "total": sum(hits.values()), "protected": protected,
            "german": german, "sides": sides}


def main():
    rows = []
    # [2026-08-22] Scan SUB-SCRIPTS too. The first version of this tool looked only at
    # maps/*.scr and reported "34 maps exposed"; the user asked whether that covered the whole
    # trilogy, and it did not. Breakthrough in particular keeps almost all of its scene logic in
    # maps/<map>/<Scene>.scr - Courtyard, JailBreak, Intro, prisoner sections, Bunker3, castle -
    # so 68 more files with scene markers were invisible to the audit.
    paths = sorted(glob.glob(os.path.join(MAPS, "*.scr")))
    paths += sorted(glob.glob(os.path.join(MAPS, "*", "*.scr")))
    paths += sorted(glob.glob(os.path.join(MAPS, "*", "*", "*.scr")))
    for p in paths:
        r = scan(p)
        if r:
            r["map"] = os.path.relpath(p, MAPS).replace(os.sep, "/")
            rows.append(r)

    prot = [r for r in rows if r["protected"]]
    expo = [r for r in rows if not r["protected"]]
    # rank by AXIS scripted actors - the only ones the personality gate can touch
    expo.sort(key=lambda r: (-(r["sides"]["axis"]), -(r["sides"]["unknown"]), r["map"]))

    print("  maps with scripted-scene markers : %d" % len(rows))
    print("  already protected                : %d  (%s)"
          % (len(prot), ", ".join(sorted(r["map"] for r in prot))))
    print("  NO protection                    : %d" % len(expo))
    print()
    print("  %-34s %5s %6s %6s %8s" % ("script", "AXIS", "unknown", "ally", "total"))
    print("  " + "-" * 84)
    for r in expo:
        if not (r["sides"]["axis"] or r["sides"]["unknown"]):
            continue   # every scripted actor is allied - the german gate cannot reach them
        det = ", ".join("%s x%d" % (k, v) for k, v in sorted(r["hits"].items()))
        print("  %-34s %5d %6d %6d %8d"
              % (r["map"], r["sides"]["axis"], r["sides"]["unknown"], r["sides"]["ally"],
                 r["total"]))
    skipped = [r["map"] for r in expo if not (r["sides"]["axis"] or r["sides"]["unknown"])]
    if skipped:
        print()
        print("  all-allied scene actors (NOT exposed - gate is team german): %s" % ", ".join(sorted(skipped)))
    print()
    print("  NOTE: a marker is not proof of exposure - the actor may be american, or caught")
    print("  by a structural test (alarm/sentry/officer/rover). Review top rows by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
