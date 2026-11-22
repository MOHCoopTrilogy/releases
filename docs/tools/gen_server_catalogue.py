#!/usr/bin/env python
"""
gen_server_catalogue.py - the settings catalogue the server host GUI builds its pages from.

Called by docgen.py build (output: docs/generated/server_settings.json). It reuses docgen's own cvar sweep
(the one that produces CVARS_COOP.md / CVARS_ENGINE.md), so a new cvar appears in the GUI on the next
generation with no hand edit. The only hand-authored input is docs/tools/servergui_overlay.json: grouping,
labels, ranges, page placement, exclusions.

Per entry: name, default (what a dedicated boot actually ends with: engine default -> coop_defaults.cfg ->
autoexec.cfg -> coop_mod/cfg/server_rules.cfg, in exec order, TRAPS T7), type, min/max, description (the
cfg comment on the seed line, else the comment block above it), category, page, server (server-relevant),
seed list and anchors.

Also emits the mission boards of the coop start screen (ui/coop_start/*.cfg), with the own-disc (BYO)
missions marked, and the campaign lobby map (coop_mod/cfg/coop_dedcampaign.cfg).

Output is deterministic: sorted keys, sorted entries, no timestamps.
"""
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OVERLAY = os.path.join(HERE, "servergui_overlay.json")
CATALOGUE_VERSION = 1

_TAG = re.compile(r"\[[^\]]*\]")
_NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
_INT = re.compile(r"^-?\d+$")
_FLOAT = re.compile(r"^-?\d*\.\d+$|^-?\d+\.\d*$")
# a name that reads as a quantity is never a checkbox, even at default 0 or 1
_QTY = re.compile(r"(Lives|Lifes|Chance|Count|Max|Min|Time|Delay|Health|Pct|Percent|Radius|Dist|Scale|Rate|Limit"
                  r"|Num|Size|Budget|Life|Secs|Sec|Ms|Level|Tier|Mode|Amount|Mult|Range|Speed|Wave|Interval"
                  r"|Cap|Floor|Ceil|Index|Idx|Slot|Hp|Dmg|Damage)\d*$")

EXEC_ORDER = ["coop_defaults.cfg", "autoexec.cfg", "coop_mod/cfg/server_rules.cfg"]


def _clean_desc(s):
    s = _TAG.sub("", s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s[:400]


def _cfg_comment(lines, idx):
    """Trailing // comment on line idx (0-based), else the contiguous // block just above it (<= 3 lines)."""
    line = lines[idx] if idx < len(lines) else ""
    in_q = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_q = not in_q
        elif not in_q and line.startswith("//", i):
            return _clean_desc(line[i + 2:])
    block = []
    j = idx - 1
    while j >= 0 and len(block) < 3:
        t = lines[j].strip()
        if not t.startswith("//"):
            break
        block.insert(0, t.lstrip("/").strip())
        j -= 1
    return _clean_desc(" ".join(block))


def _infer_type(name, default, desc):
    if default in ("0", "1") and not _QTY.search(name):
        nums = [n for n in _NUM.findall(_TAG.sub("", desc or "")) if n not in ("0", "1")]
        return "bool" if not nums else "int"
    if _INT.match(default or ""):
        return "int"
    if _FLOAT.match(default or ""):
        return "float"
    return "string"


def build(root, mod, engine_regs, script_use, cfg_seed, ui_ref, read_text):
    ov = json.loads(read_text(OVERLAY))
    ex_name = [re.compile(p) for p in ov["exclude_name_regex"]]
    ex_file = [re.compile(p) for p in ov["exclude_files_regex"]]
    fcat = ov["file_categories"]
    fpre = ov["file_prefix_categories"]
    byo_re = re.compile(ov["byo_map_regex"])
    server_tab = {n.lower() for n in ov["server_tab"]}
    tuning_tab = {n.lower() for n in ov["tuning_tab"]}
    overrides = {k.lower(): v for k, v in ov["overrides"].items()}

    cfg_lines = {}

    def lines_of(short):
        if short not in cfg_lines:
            cfg_lines[short] = read_text(os.path.join(root, mod, short)).replace("\r\n", "\n").split("\n")
        return cfg_lines[short]

    eng = defaultdict(list)
    for r in engine_regs:
        eng[r.name.lower()].append(r)
    seeds = defaultdict(list)
    for n, rows in cfg_seed.items():
        seeds[n.lower()].extend(rows)
    uses = defaultdict(list)
    for n, rows in script_use.items():
        uses[n.lower()].extend(rows)
    canon = {}
    for src in (eng, ):
        for k, rows in src.items():
            canon.setdefault(k, rows[0].name)
    for n in list(script_use) + list(cfg_seed) + list(ui_ref):
        canon.setdefault(n.lower(), n)

    def category_for(name, reads):
        files = [u[0] for u in reads]
        if not files:
            return None
        votes = defaultdict(int)
        for f in files:
            base = f.split("/")[-1]
            if f.startswith("maps/"):
                stem = base[:-4]
                votes["Own-disc missions" if byo_re.match(stem) else "Mission tuning"] += 1
                continue    # a map script votes once; a coop_mod system twice (it owns the feature)
            c = fcat.get(base)
            if not c:
                for p, pc in fpre.items():
                    if base.startswith(p):
                        c = pc
                        break
            if not c and byo_re.match(base[:-4]):
                c = "Own-disc missions"
            votes[c or "Other"] += 2
        return sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    def engine_server(regs):
        dirs = set(ov["engine_server_dirs"])
        return any(r.file.split("/")[0] in dirs for r in regs)

    out = []
    client_only = []
    unknown_overlay = sorted(k for k in overrides if k not in canon)
    counts = defaultdict(int)
    for key in sorted(canon):
        name = canon[key]
        is_coop = key.startswith("coop_")
        regs = eng.get(key, [])
        reads = [u for u in uses.get(key, []) if u[2] == "getcvar"]
        if not is_coop:
            # engine cvars: only the server-side ones (a renderer or client cvar has no place on a server)
            if not regs:
                continue
            if not (engine_server(regs) or name in ov["engine_qcommon_include"] or key in tuning_tab
                    or key in server_tab):
                continue
            flags = " ".join(r.flags for r in regs)
            if any(f in flags for f in ov["engine_exclude_flags"]) and key not in server_tab:
                continue
        if any(p.search(name) for p in ex_name):
            counts["excluded_name"] += 1
            continue
        if reads and all(any(p.search(u[0]) for p in ex_file) for u in reads) and not regs:
            counts["excluded_test_only"] += 1
            continue

        # what a dedicated boot ends with, in exec order
        default = regs[0].default if regs else None
        if regs:
            srv = [r for r in regs if r.file.split("/")[0] in ("server", "fgame", "gamespy", "qcommon")]
            if srv:
                default = srv[0].default
        seed_rows = []
        desc = ""
        for p, ln, verb, val in sorted(seeds.get(key, [])):
            if p in EXEC_ORDER or p.endswith("dedicated_example.cfg"):
                seed_rows.append({"cfg": p, "line": ln, "value": val, "verb": verb})
        by_cfg = {s["cfg"]: s for s in seed_rows}
        for cfgname in EXEC_ORDER:
            s = by_cfg.get(cfgname)
            if s:
                default = s["value"]
        for cfgname in EXEC_ORDER + sorted(by_cfg):
            s = by_cfg.get(cfgname)
            if s and not desc:
                try:
                    desc = _cfg_comment(lines_of(cfgname), s["line"] - 1)
                except OSError:
                    pass
        unseeded = default is None
        if unseeded:
            default = ""

        engine_client_only = bool(regs) and not engine_server(regs) and key not in tuning_tab and key not in server_tab
        server = bool(reads) or engine_server(regs) or key in tuning_tab or key in server_tab
        if is_coop and not reads and engine_client_only:
            server = False
        if is_coop and not reads and not regs:
            server = False      # menu-only / cfg-only state: nothing on the server reads it

        if key in server_tab:
            page = "server"
        elif key in tuning_tab:
            page = "tuning"
        else:
            page = "gameplay"
        if not server:
            client_only.append(name)
            counts["client_only"] += 1
            continue
        if is_coop:
            cat = category_for(name, reads) or ("Engine coop features" if regs else "Other")
        else:
            cat = "Engine game rules" if any(r.file.startswith("fgame/") for r in regs) else "Engine server"
        if unseeded and server and page == "gameplay":
            cat = "No shipped default"

        e = {
            "name": name,
            "default": default,
            "type": _infer_type(name, default, desc),
            "description": desc,
            "category": cat,
            "page": page,
            "server": server,
            "unseeded": unseeded,
            "flags": regs[0].flags if regs else "",
            "engine_anchor": f"{regs[0].file}:{regs[0].line}" if regs else "",
            "script_reads": len(reads),
            "script_anchor": f"{sorted(reads)[0][0]}:{sorted(reads)[0][1]}" if reads else "",
            "seeds": seed_rows,
            "ui": bool(ui_ref.get(name)),
        }
        o = overrides.get(key)
        if o:
            for k2, v2 in o.items():
                e[k2] = v2
        out.append(e)
        counts["page_" + page] += 1
        counts["server"] += 1

    # ---- mission boards (the coop start screen) -------------------------------------------------
    order = {"m": 0, "t": 1, "e": 2, "fl": 3, "ea": 4}
    boards = []
    sdir = os.path.join(root, mod, "ui", "coop_start")
    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith(".cfg") or fn == "disableInfo.cfg":
            continue
        txt = read_text(os.path.join(sdir, fn)).replace("\r\n", "\n")
        m = re.search(r'coop_missionName\s+title\s+"([^"]*)"', txt)
        maps = []
        last_comment = {}
        for ln in txt.split("\n"):
            c = re.match(r"\s*//\s*([A-Za-z0-9_/]+)\s+-\s+(.+?)\s*$", ln)
            if c:
                last_comment[c.group(1)] = _clean_desc(c.group(2))
            sc = re.search(r'stuffcommand\s+"([^"]*set ui_dmmap [^"]*)"', ln)
            if sc:
                extra = {}
                mp = ""
                for part in sc.group(1).split(";"):
                    kv = re.match(r"\s*set\s+([A-Za-z0-9_]+)\s+(\S+)\s*$", part)
                    if not kv:
                        continue
                    if kv.group(1) == "ui_dmmap":
                        mp = kv.group(2)
                    else:
                        extra[kv.group(1)] = kv.group(2)      # e.g. coop_advTraining 1 picks a variant of m4l0
                if mp:
                    # spec = map plus the tile's own cvars, "m4l0|coop_advTraining=1": what the GUI starts
                    spec = mp + "".join(f"|{k}={v}" for k, v in sorted(extra.items()))
                    maps.append({"map": mp, "spec": spec, "title": last_comment.get(mp, mp),
                                 "byo": bool(byo_re.match(mp))})
        if not maps:
            continue
        stem = fn[:-4]
        pre = re.match(r"[a-z]+", stem).group(0)
        boards.append({"board": stem, "title": m.group(1) if m else stem, "maps": maps,
                       "byo": all(x["byo"] for x in maps), "_k": (order.get(pre, 9), stem)})
    boards.sort(key=lambda b: b["_k"])
    for b in boards:
        del b["_k"]
    lobby = "co_lobby1"
    try:
        t = read_text(os.path.join(root, mod, "coop_mod", "cfg", "coop_dedcampaign.cfg"))
        mm = re.search(r"^\s*set ui_dmmap (\S+)", t, re.M)
        if mm:
            lobby = mm.group(1)
    except OSError:
        pass

    cat_order = ov["category_order"]
    present = sorted({e["category"] for e in out}, key=lambda c: (cat_order.index(c) if c in cat_order else 99, c))
    doc = {
        "_README": "DO NOT EDIT - generated by docs/tools/gen_server_catalogue.py via docs/tools/docgen.py build. "
                   "Hand-authored grouping/labels/ranges live in docs/tools/servergui_overlay.json.",
        "catalogue_version": CATALOGUE_VERSION,
        "categories": present,
        "counts": dict(sorted(counts.items())),
        "overlay_unknown": unknown_overlay,
        "campaign": {"lobby_map": lobby},
        "missions": boards,
        "settings": out,
        "client_only": client_only,
    }
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def _generate():
    import sys
    sys.path.insert(0, HERE)
    import docgen
    files = docgen.sweep()
    regs, _dyn, _sc = docgen.scan_engine_cvars(files)
    su, cs, ui, _dp = docgen.scan_mod_cvars(files)
    return build(docgen.ROOT, docgen.MOD, regs, su, cs, ui, docgen.read_text)


if __name__ == "__main__":
    # python gen_server_catalogue.py --check <docs/generated/server_settings.json>   exit 1 = stale (publish_release.ps1)
    # python gen_server_catalogue.py --print                                          the catalogue on stdout
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "--check":
        fresh = _generate().encode("utf-8")
        try:
            with open(sys.argv[2], "rb") as fh:
                have = fh.read()
        except OSError:
            have = b""
        if have != fresh:
            print("server_settings.json is STALE - run: python docs/tools/docgen.py build")
            sys.exit(1)
        print("server_settings.json is current")
        sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == "--print":
        sys.stdout.write(_generate())
        sys.exit(0)
    print(__doc__)
