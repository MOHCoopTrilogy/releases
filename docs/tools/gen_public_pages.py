#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_public_pages.py - build the PUBLIC GitHub documentation set from source.

Everything here is DERIVED. Nothing in docs/public/ is hand-written, for the same reason
docs/generated/ is not: a hand-maintained list of 1161 bug fixes or 344 challenges is wrong
the day after it is written. Edit this generator, never its output.

Sources, all of them the actual artefact rather than a summary of it:
  .wolf/buglog.json                          -> every logged defect and its fix
  hzm-mohaa-coop-mod/coop_mod/challenges.scr -> every challenge, its category and description
  hzm-mohaa-coop-mod/maps/*.scr              -> which maps are coop-integrated
  docs/FEATURES.md                           -> the authored feature record (headings + entries)
  docs/OPEN.md                               -> open defects and work not yet done

Outputs (docs/public/):
  FEATURES.md    every system built, by domain
  MAPS.md        every map, coop status, and what was fixed on it
  BUGFIXES.md    every logged fix, grouped by subsystem
  CHALLENGES.md  all challenges by Service Record category
  ROADMAP.md     what is planned or in progress

Usage:  python docs/tools/gen_public_pages.py [--check]
        --check regenerates in memory and byte-compares; exit 1 if stale.
"""

import io
import json
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
OUT = os.path.join(ROOT, "docs", "public")

REPO = "https://github.com/MOHCoopTrilogy/releases"

BANNER = (
    "<!-- GENERATED FILE - DO NOT EDIT.\n"
    "     Produced by docs/tools/gen_public_pages.py from buglog.json, challenges.scr,\n"
    "     the map scripts and the authored docs. Edits here are overwritten. -->\n\n"
)


def read(path, enc="utf-8"):
    with io.open(path, encoding=enc, errors="replace") as fh:
        return fh.read()


def esc(s):
    """Make a value safe inside a markdown table cell."""
    s = " ".join(str(s).split())
    return s.replace("|", "\\|")


# ---------------------------------------------------------------- challenges

# Category order and display titles both come from challenges.scr, so the public page
# groups challenges exactly the way the in-game Service Record does.
def load_challenges():
    src = read(os.path.join(MOD, "coop_mod", "challenges.scr"), "latin-1")

    order = []
    for m in re.finditer(r'coop_chal_catOrder\[(\d+)\]\s*=\s*"([a-z_]+)"', src):
        order.append((int(m.group(1)), m.group(2)))
    order = [c for _, c in sorted(order)]

    labels = {}
    for m in re.finditer(r'coop_chal_catLabel\["([a-z_]+)"\]\s*=\s*"([^"]+)"', src):
        labels[m.group(1)] = m.group(2)

    rows = []
    # Capture the reward (7th arg) too - it is what UNLOCKABLES.md is built from. The trailing
    # group is optional so a challenge that grants nothing still parses.
    pat = (r'chal_def\s+"([^"]+)"\s+"([^"]+)"\s+"([^"]*)"\s+"([^"]*)"'
           r'(?:\s+"([^"]*)"\s+(\S+)\s+"([^"]*)")?')
    for m in re.finditer(pat, src):
        rows.append({
            "cid": m.group(1), "cat": m.group(2), "name": m.group(3), "desc": m.group(4),
            "reward": (m.group(7) or ""),
        })
    return order, labels, rows


# A challenge's 7th chal_def argument is its reward - empty for most, an asset path or a perk
# token for the 213 that unlock something. That field IS the unlock table; there is no separate
# list to fall out of step with it.
UNLOCK_KINDS = [
    ("models/weapons", "Weapons", "Usable weapons added to your loadout options."),
    ("perk", "Perks", "Passive squad abilities and extra equipment."),
    ("models/coop_helmets", "Helmets", "Headgear for your soldier, picked in the Helmet selector."),
    ("models/player", "Uniforms & skins", "Player appearances, picked in the Armory."),
    # [user 2026-08-21] finishes were falling through to "Other", which buried the whole
    # 357-finish system under a miscellaneous heading on a public page.
    ("finish", "Weapon finishes", "Gun finishes (gold, chrome, blued, camo...). Unlocking a "
     "finish TYPE makes it available on every gun that supports it - the in-game finish "
     "count multiplies these across the roster."),
]


def variant_rows():
    """Model-variant inventory, derived from the armory's own generated cfg pages
    (ui/loadout/p<NN>.cfg = host gun name, mvp<NN>_<k>_s1.cfg = one variant name each).
    Derived, never hand-listed - wire_mv regenerates these cfgs, so this can not drift.
    The unlock RULE is per-gun (loadoutpick.scr): the gun's ELITE challenge, after
    mastering the gun (its kill challenge)."""
    import glob as _g
    lo = os.path.join(MOD, "ui", "loadout")
    hosts = {}
    for f in sorted(_g.glob(os.path.join(lo, "p[0-9][0-9].cfg"))):
        nn = os.path.basename(f)[1:3]
        for line in io.open(f, encoding="utf-8", errors="replace"):
            m = re.match(r'\s*set coop_loNm\s+"([^"]+)"', line)
            if m:
                hosts[nn] = m.group(1)
                break
    out = {}
    for f in sorted(_g.glob(os.path.join(lo, "mvp[0-9][0-9]_*_s1.cfg"))):
        base = os.path.basename(f)
        nn = base[3:5]
        # chain index 0 is the gun's own STOCK model, not a variant - listing it inflated
        # the public count to 100 when the real credited-variant count is 77 (23 hosts).
        if base[6:8] == "0_":
            continue
        gun = hosts.get(nn)
        if not gun:
            continue
        for line in io.open(f, encoding="utf-8", errors="replace"):
            m = re.match(r'\s*set coop_loNm\s+"([^"]+)"', line)
            if m:
                out.setdefault(gun, []).append(m.group(1))
                break
    return out


def pretty_asset(path):
    """Readable name for an unlock, derived from its asset - never hand-written."""
    if not path.startswith("models/"):
        name = path.split("_", 1)[-1] if path.startswith("perk_") else path
    else:
        name = path.rsplit("/", 1)[-1]
        if name.endswith(".tik"):
            name = name[:-4]
    for pre in ("uk_w_", "it_w_", "us_w_", "ger_w_", "w_"):
        if name.startswith(pre):
            name = name[len(pre):]
    name = name.replace("_", " ").replace("-", " ").strip()

    # Asset names run words together ("arisakasniper", "berettasilenced"). Split the known
    # trailing variants back out so the chart reads like the menus do. Longest first, so
    # "snipersilenced" is not eaten by "sniper".
    for suf in ("snipersilenced", "silencedsniper", "silenced", "sniper", "nohelm", "noheadgear"):
        if len(name) > len(suf) + 2 and name.endswith(suf) and not name.endswith(" " + suf):
            name = name[: -len(suf)].rstrip() + " " + suf
            break

    # Presentation only, and stable because asset names do not change: a handful of real
    # acronyms that would otherwise read as ordinary words ("Bar" for the BAR).
    ACRONYMS = {"bar", "mp40", "mp44", "stg44", "fg42", "bren", "piat", "kar98", "m1", "l42a1"}
    parts = []
    for w in name.split():
        if w.isupper():
            parts.append(w)
        elif w.lower() in ACRONYMS:
            parts.append(w.upper())
        else:
            parts.append(w.capitalize())
    return " ".join(parts)


def kind_of(reward):
    for prefix, title, _ in UNLOCK_KINDS:
        if reward.startswith(prefix):
            return title
    return "Other"


def page_unlockables(rows_full):
    unlocks = [r for r in rows_full if r["reward"].strip()]

    out = [BANNER, "# Unlockables\n\n"]
    out.append(
        "Everything you can earn, and exactly what earns it. Nothing here is bought or random - "
        "every unlock is attached to a specific challenge, and completing that challenge grants it.\n\n"
    )
    out.append(
        "**%d unlocks** across %d kinds. Unlock names are derived from the game assets themselves, "
        "so they match what you see in the menus.\n\n" % (len(unlocks), len(UNLOCK_KINDS))
    )

    out.append("| Kind | Unlocks | What they are |\n|---|---:|---|\n")
    for _, title, blurb in UNLOCK_KINDS:
        n = sum(1 for u in unlocks if kind_of(u["reward"]) == title)
        if n:
            out.append("| **%s** | %d | %s |\n" % (title, n, blurb))
    out.append("\n")

    for _, title, blurb in UNLOCK_KINDS:
        items = [u for u in unlocks if kind_of(u["reward"]) == title]
        if not items:
            continue
        items.sort(key=lambda u: pretty_asset(u["reward"]).lower())
        out.append("## %s\n\n%s\n\n" % (title, blurb))
        out.append("| Unlock | Earned by | How to earn it |\n|---|---|---|\n")
        for u in items:
            out.append("| **%s** | %s | %s |\n" % (
                esc(pretty_asset(u["reward"])), esc(u["name"]), esc(u["desc"])))
        out.append("\n")

    mv = variant_rows()
    if mv:
        total = sum(len(v) for v in mv.values())
        out.append("## Model variants\n\n")
        out.append(
            "**%d community-credited model variants** across %d host guns - different guns "
            "entirely, not reskins, each credited to its original author in the name. They are "
            "not individual challenge rewards: variants for a gun unlock together at that gun's "
            "**ELITE challenge**, after mastering the gun (its kill challenge).\n\n"
            % (total, len(mv)))
        out.append("| Host gun | Variants |\n|---|---|\n")
        for gun in sorted(mv):
            out.append("| **%s** | %s |\n" % (esc(gun), esc(", ".join(mv[gun]))))
        out.append("\n")

    other = [u for u in unlocks if kind_of(u["reward"]) == "Other"]
    if other:
        out.append("## Other\n\n| Unlock | Earned by | How to earn it |\n|---|---|---|\n")
        for u in other:
            out.append("| **%s** | %s | %s |\n" % (
                esc(pretty_asset(u["reward"])), esc(u["name"]), esc(u["desc"])))
        out.append("\n")
    return "".join(out)


def page_challenges(order, labels, rows):
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["cat"]].append(r)

    out = [BANNER, "# Challenges\n\n"]
    out.append(
        "Every challenge in the mod, grouped exactly as the in-game **Service Record** groups them "
        "(Join Game -> Service Record). Challenges marked *(Elite)* are the harder second tier of "
        "the same weapon or feat.\n\n"
    )
    out.append("**%d challenges** across **%d categories**.\n\n" % (len(rows), len(by_cat)))

    out.append("| Category | Challenges |\n|---|---:|\n")
    for cat in order:
        if by_cat.get(cat):
            out.append("| [%s](#%s) | %d |\n" % (labels.get(cat, cat.upper()),
                                                 labels.get(cat, cat).lower().replace(" ", "-").replace("&", ""),
                                                 len(by_cat[cat])))
    out.append("\n")

    # any category present in the data but missing from catOrder still gets printed, so the
    # page can never silently drop challenges just because the taxonomy list fell behind
    for cat in order + sorted(c for c in by_cat if c not in order):
        items = by_cat.get(cat)
        if not items:
            continue
        out.append("## %s\n\n" % labels.get(cat, cat.upper()))
        out.append("| Challenge | How to earn it |\n|---|---|\n")
        for r in items:
            out.append("| **%s** | %s |\n" % (esc(r["name"]), esc(r["desc"])))
        out.append("\n")
    return "".join(out)


# ---------------------------------------------------------------- bug fixes

# Tags are the only classification buglog carries, so the public grouping is derived from
# them rather than invented. The map is ordered: the first rule that matches an entry's tags
# wins, so a m6l2a stealth fix lands under Stealth rather than under Maps.
AREAS = OrderedDict([
    ("Stealth, disguise & contain", ["stealth", "disguise", "contain", "bust", "papers", "cover-blown"]),
    ("AI & enemy behaviour", ["ai", "aihandler", "actor", "officer", "patrol", "pain-handler",
                              "aggro", "reinforcement", "coop_actorarray", "replica"]),
    ("Engine & crashes", ["engine", "crash", "entity-pool", "memory", "protocol", "sdl_glimp",
                          "renderer", "gl2", "postfx", "shader"]),
    ("Weapons & combat", ["weapon", "ads", "ammo", "grenade", "turret", "mg42", "sniper", "bash"]),
    ("Audio", ["audio", "sound", "sound-alias", "music", "openal", "voice", "subtitle"]),
    ("UI, HUD & menus", ["ui", "hud", "menu", "urc", "ihuddraw", "loadout", "service-record",
                         "challenges", "objectives"]),
    ("Vehicles & rides", ["vehicle", "jeep", "tank", "truck", "halftrack", "ride"]),
    ("Multiplayer & networking", ["network", "dedicated", "listen", "client", "server",
                                  "replication", "spawn", "respawn", "dbno"]),
    ("Maps & missions", ["map", "objective", "mission", "trigger", "prop", "build-mode", "precache"]),
    ("Build, deploy & tooling", ["build", "deploy", "tooling", "docgen", "parse-killer",
                                 "verification", "publish"]),
])


def area_for(tags, fname):
    t = set(x.lower() for x in tags)
    blob = " ".join(t) + " " + (fname or "").lower()
    for area, keys in AREAS.items():
        for k in keys:
            if k in t or k in blob:
                return area
    return "Other"


def load_bugs():
    data = json.loads(read(os.path.join(ROOT, ".wolf", "buglog.json")))
    return data["bugs"] if isinstance(data, dict) and "bugs" in data else data


def page_bugfixes(bugs):
    grouped = defaultdict(list)
    for b in bugs:
        grouped[area_for(b.get("tags", []), b.get("file", ""))].append(b)

    def bugnum(b):
        m = re.search(r"(\d+)", str(b.get("id", "")))
        return int(m.group(1)) if m else 0

    # One file per area, plus an index. A single page was 749 KB, which GitHub stops rendering
    # well before - so the split is a hard requirement, not a preference.
    pages = {}
    index = [BANNER, "# Every fix, logged\n\n"]
    index.append(
        "Every defect this project has found and fixed, from the day the log was started. "
        "This is the raw engineering record rather than a changelog: it gives the cause as well "
        "as the symptom, because the cause is usually the useful part.\n\n"
    )
    index.append("**%d fixes logged.**\n\n" % len(bugs))
    index.append("| Area | Fixes |\n|---|---:|\n")

    for area in list(AREAS.keys()) + ["Other"]:
        items = sorted(grouped.get(area, []), key=bugnum, reverse=True)
        if not items:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", area.lower()).strip("-")
        index.append("| [%s](fixes/%s.md) | %d |\n" % (area, slug, len(items)))

        body = [BANNER, "# %s\n\n" % area]
        body.append("[<- back to all fixes](../BUGFIXES.md)\n\n")
        body.append("**%d fixes**, newest first.\n\n" % len(items))
        body.append("| ID | Problem | Cause | Fix |\n|---|---|---|---|\n")
        for b in items:
            body.append("| `%s` | %s | %s | %s |\n" % (
                esc(b.get("id", "")),
                esc(b.get("error_message", ""))[:200],
                esc(b.get("root_cause", ""))[:240],
                esc(b.get("fix", ""))[:240],
            ))
        pages["fixes/%s.md" % slug] = "".join(body)

    index.append("\nEach area links to its own page - the full log is far too large for one.\n")
    pages["BUGFIXES.md"] = "".join(index)
    return pages


# ---------------------------------------------------------------- maps

# "Coop-integrated" has one objective definition: the map script calls coop_mod/main.scr::main.
# Anything else would be an opinion, and opinions drift.
CAMPAIGN = [
    ("m", "Allied Assault"),
    ("t", "Spearhead"),
    ("e", "Breakthrough"),
]


def load_maps(bugs):
    fixes = defaultdict(list)
    for b in bugs:
        blob = " ".join(b.get("tags", [])) + " " + str(b.get("file", ""))
        for m in set(re.findall(r"\b([met]\d+l\d+[a-c]?)\b", blob.lower())):
            fixes[m].append(b)

    maps = {}
    mapdir = os.path.join(MOD, "maps")
    for fn in sorted(os.listdir(mapdir)):
        if not fn.lower().endswith(".scr") or "precache" in fn.lower():
            continue
        name = fn[:-4].lower()
        if not re.match(r"^[met]\d+l\d+[a-c]?$", name):
            continue
        try:
            body = read(os.path.join(mapdir, fn), "latin-1")
        except Exception:
            continue
        maps[name] = {
            "integrated": "coop_mod/main.scr::main" in body,
            "lines": body.count("\n") + 1,
            "fixes": len(fixes.get(name, [])),
        }
    return maps


def page_maps(maps):
    out = [BANNER, "# Maps\n\n"]
    out.append(
        "Every mission in the trilogy that has a coop script, what state it is in, and how much "
        "repair work it has taken. **Coop-integrated** means the map script calls the coop "
        "framework entry point (`coop_mod/main.scr::main`) - that is the single objective test, "
        "not a judgement call.\n\n"
    )
    total = len(maps)
    integ = sum(1 for v in maps.values() if v["integrated"])
    out.append("**%d map scripts, %d coop-integrated.**\n\n" % (total, integ))

    for prefix, title in CAMPAIGN:
        rows = sorted((k, v) for k, v in maps.items() if k.startswith(prefix))
        if not rows:
            continue
        out.append("## %s\n\n" % title)
        out.append("| Map | Coop | Script lines | Logged fixes |\n|---|---|---:|---:|\n")
        for name, v in rows:
            out.append("| `%s` | %s | %d | %d |\n" % (
                name, "yes" if v["integrated"] else "-", v["lines"], v["fixes"]))
        out.append("\n")

    hot = sorted(maps.items(), key=lambda kv: -kv[1]["fixes"])[:15]
    hot = [(k, v) for k, v in hot if v["fixes"]]
    if hot:
        out.append("## Most repaired\n\n")
        out.append(
            "Fix counts are a rough proxy for how much a map fought back. A high count usually "
            "means the map carries a bespoke system - a vehicle, a stealth layer, a scripted "
            "sequence - rather than that it is fragile.\n\n"
        )
        out.append("| Map | Logged fixes |\n|---|---:|\n")
        for name, v in hot:
            out.append("| `%s` | %d |\n" % (name, v["fixes"]))
        out.append("\n")
    return "".join(out)


# ---------------------------------------------------------------- features

# A feature entry in docs/FEATURES.md is a paragraph that opens with **Name**, usually followed
# by a status token in backticks. It is NOT a markdown heading, which is why an earlier version of
# this generator produced an almost-empty page - a reminder to read the format rather than assume it.
FEAT_RE = re.compile(r"^\*\*(?P<name>[^*]+?)\*\*\s*[-—:]*\s*(?:`(?P<status>[A-Z][A-Z0-9 _-]*)`)?\.?\s*(?P<rest>.*)$")

STATUS_TEXT = {
    "SHIPPED-VERIFIED": "shipped, confirmed working in play",
    "SHIPPED-UNVERIFIED": "shipped, not yet confirmed in play",
    "SHIPPED-CODE-DISABLED": "in the build but switched off",
    "BUILT-UNTESTED": "built, untested",
    "REVERTED": "reverted",
    "PLANNED": "planned",
}


def _first_sentence(text, limit=230):
    text = " ".join(text.split())
    text = re.sub(r"`([^`]*)`", r"\1", text)
    m = re.search(r"(?<=[a-z0-9\)])\.\s", text)
    if m and m.end() <= limit + 40:
        text = text[: m.start() + 1]
    if len(text) > limit:
        cut = text.rfind(" ", 0, limit)
        text = text[: cut if cut > 60 else limit].rstrip(" ,;:") + "..."
    return text


def page_features():
    src = read(os.path.join(ROOT, "docs", "FEATURES.md"))

    out = [BANNER, "# Features\n\n"]
    out.append(
        "Every system built for the trilogy coop mod, grouped by domain. Generated from the "
        "project's own feature record, so it stays in step with what is actually in the build - "
        "including the parts that are shipped but not yet confirmed in play.\n\n"
    )

    domain = None
    sections = OrderedDict()
    for ln in src.split("\n"):
        if ln.startswith("## "):
            domain = ln[3:].strip()
            sections.setdefault(domain, [])
        elif domain and ln.startswith("**"):
            m = FEAT_RE.match(ln.strip())
            if m and m.group("name"):
                sections[domain].append((
                    m.group("name").strip(),
                    (m.group("status") or "").strip(),
                    _first_sentence(m.group("rest") or ""),
                ))

    total = sum(len(v) for v in sections.values())
    counts = Counter(s for v in sections.values() for _, s, _ in v if s)
    out.append("**%d systems** across **%d domains**.\n\n" % (
        total, sum(1 for v in sections.values() if v)))
    if counts:
        out.append("| Status | Count |\n|---|---:|\n")
        for st, n in counts.most_common():
            out.append("| %s | %d |\n" % (STATUS_TEXT.get(st, st.replace("-", " ").lower()), n))
        out.append("\n")

    for name, entries in sections.items():
        if not entries or name.lower() == "domain index":
            continue
        out.append("## %s\n\n" % name)
        out.append("| System | Status | What it does |\n|---|---|---|\n")
        for fname, status, desc in entries:
            out.append("| **%s** | %s | %s |\n" % (
                esc(fname),
                esc(STATUS_TEXT.get(status, status.replace("-", " ").lower())) if status else "",
                esc(desc)))
        out.append("\n")
    return "".join(out)


# ---------------------------------------------------------------- roadmap

def page_roadmap():
    src = read(os.path.join(ROOT, "docs", "OPEN.md"))
    out = [BANNER, "# Roadmap and known issues\n\n"]
    out.append(
        "What is planned, in progress, or known to be broken. This is generated from the "
        "project's open-work record, so it is the same list the developers work from - "
        "including the unflattering parts.\n\n"
    )
    out.append(
        "> This project is in **early alpha** and under heavy active development. If something "
        "here is not yet fixed, a bug report against it is still useful: it tells us it matters "
        "to someone.\n\n"
    )

    section = None
    items = OrderedDict()
    for ln in src.split("\n"):
        if ln.startswith("## "):
            section = ln[3:].strip()
            items.setdefault(section, [])
        elif ln.startswith("### ") and section:
            items[section].append(ln[4:].strip())

    for sec, entries in items.items():
        if not entries or sec.lower().startswith("sections"):
            continue
        out.append("## %s\n\n" % sec)
        for e in entries:
            out.append("- %s\n" % e)
        out.append("\n")
    return "".join(out)


# ---------------------------------------------------------------- driver

def build():
    order, labels, chal = load_challenges()
    bugs = load_bugs()
    maps = load_maps(bugs)
    pages = {
        "CHALLENGES.md": page_challenges(order, labels, chal),
        "UNLOCKABLES.md": page_unlockables(chal),
        "MAPS.md": page_maps(maps),
        "FEATURES.md": page_features(),
        "ROADMAP.md": page_roadmap(),
    }
    pages.update(page_bugfixes(bugs))
    return pages


def main():
    check = "--check" in sys.argv
    pages = build()
    if not check:
        for sub in ("", "fixes"):
            d = os.path.join(OUT, sub) if sub else OUT
            if not os.path.isdir(d):
                os.makedirs(d)

    stale = []
    for name, body in pages.items():
        path = os.path.join(OUT, name)
        old = read(path) if os.path.exists(path) else None
        if old == body:
            status = "unchanged"
        else:
            status = "STALE" if check else "written"
            stale.append(name)
            if not check:
                with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(body)
        print("  %-16s %8d bytes  %s" % (name, len(body), status))

    if check and stale:
        print("\nSTALE: %s\nfix with: python docs/tools/gen_public_pages.py" % ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
