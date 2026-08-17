#!/usr/bin/env python3
"""
docgen.py - the HZM MOHAA Coop Mod derived-documentation generator.

GOVERNING PRINCIPLE
    Anything that can be extracted from code, git or buglog.json MUST be
    generated, never hand-maintained. A regenerated doc cannot drift.

    Authored files (docs/SOURCE_OF_TRUTH.md, TRAPS.md, DECISIONS.md, OPEN.md,
    FEATURES.md, ENGINE.md, HISTORY.md) need human judgement and are NEVER
    touched by this tool. Everything this tool writes lands in docs/generated/
    and carries a DO-NOT-EDIT banner.

USAGE
    python docs/tools/docgen.py build          regenerate docs/generated/
    python docs/tools/docgen.py build --force  regenerate even if inputs unchanged
    python docs/tools/docgen.py check          exit 1 if committed docs != fresh generation
    python docs/tools/docgen.py status         print the input fingerprint + staleness

    Wrappers: docs\\tools\\docs.ps1 <mode>   /   docs\\tools\\docs.cmd <mode>

DETERMINISM CONTRACT
    Output must be a pure function of the repository state, otherwise `check`
    is worthless. That means: no wall-clock timestamps in any generated file,
    sorted iteration everywhere, LF newlines, UTF-8 without BOM. The only
    wall-clock lives in .wolf/hooks/docgen-state.json - outside docs/ entirely,
    so it never appears as a perpetually-modified file in the committed tree.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict

# --------------------------------------------------------------------------
# Paths and scope
# --------------------------------------------------------------------------

TOOL_VERSION = "1.0.0"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))      # C:\mohaa-coop-dev
OUT_DIR = os.path.join(ROOT, "docs", "generated")
# Cache/state lives OUTSIDE docs/ on purpose. It holds a wall-clock, so keeping
# it beside the generated files would put a perpetually-modified file in the
# committed tree - and .wolf/ is already excluded from the sweep, so writing it
# there cannot feed back into the fingerprint.
STATE_PATH = os.path.join(ROOT, ".wolf", "hooks", "docgen-state.json")

MOD = "hzm-mohaa-coop-mod"
ENGINE = "openmohaa-hzm"

GIT_REPOS = [
    (".", "release pipeline (build.ps1, manifests, docs)"),
    (MOD, "the mod: scripts, cfg, ui, assets"),
    (ENGINE, "HZM fork of the OpenMOHAA engine"),
]

# Directories never descended into, anywhere in the tree.
#
# `.claude` and `.wolf` are tool state, not project files, and they mutate on
# every single turn. Counting them would mean the census disagrees with the
# input fingerprint - the docs would read as stale for reasons that have nothing
# to do with documentation. `.wolf/buglog.json` is still read directly and is
# fingerprinted by its own size and mtime.
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".cmake", "build_out",
    ".vs", ".idea", "dist", "obj", "CMakeFiles",
    ".claude", ".wolf",
}

# The generator's own output. Excluded from the sweep, from the census and from
# every git dirty count - otherwise the output is an input to itself and the
# generation never reaches a fixed point, which would make `check` meaningless.
SELF_EXCLUDE = "docs/generated"

# Areas that are reference / staging / extraction dumps rather than project
# source. They are still COUNTED in the census (so nothing is invisible) but
# their individual files are not indexed - they churn constantly and indexing
# them would make `docs check` fail on noise.
NON_SOURCE_AREAS = {
    "_frontline": "PS3 Frontline asset extraction (reference)",
    "_hd_staging": "HD texture upscale staging (reference)",
    "sound-browser": "audio browsing scratch tool + copies",
    "UBER-MODS-v8.00-MOHAA": "third-party mod, reference only",
    "original-scripts": "vanilla MOHAA script/asset extraction (reference)",
    "moh-modelviewer": "Node model preview tool (rarely touched)",
    "_menu_pilot": "Photoshop menu round-trip staging",
    "wepcap_home": "weapon-capture profile dir",
    "player1_home": "test client profile dir",
    "player2_home": "test client profile dir",
    "player3_home": "test client profile dir",
    "player4_home": "test client profile dir",
    "helmtest_home": "test client profile dir",
    "vanilla_audio_ref": "vanilla audio reference",
    "_soundcheck": "audio comparison staging",
    "_xw_weapons": "extra WW2 weapon pack import staging",
    "_kun_weapons": "weapon pack import staging",
    "_eaglework": "asset scratch",
    "_blender_kit": "Blender pipeline scratch",
    "_tools": "downloaded third-party binaries",
    "_checkpoints": "manual working-tree checkpoints",
    "texture-preview": "texture preview scratch tool",
    "trees": "foliage asset scratch",
    "research_extracted": "extracted research payloads",
    "installer": "Inno Setup output + payload staging",
}

# Areas that ARE the project. Descriptions here are authored once and shown in
# the census - everything else about them is derived.
SOURCE_AREAS = {
    MOD: "**the mod** - scripts, cfg, ui, tiks, assets",
    ENGINE: "**the engine** - HZM fork of OpenMOHAA (C/C++)",
    "docs": "this documentation set (authored + generated)",
    "_research": "regression rig, audits, plans - `_research/regression/` is the one working automated verification system",
    "manifests": "release manifests consumed by the auto-updater",
    "updater": "auto-updater client",
    "tools": "misc build/debug tooling",
    "watchdog": "server watchdog scripts",
    "map_entities": "per-map entity dumps",
    "extracted-scripts": "extracted vanilla scripts kept for diffing",
    "<root>": "release pipeline: `build.ps1`, `publish_release.ps1`, pk3 build artifacts",
}

TEXT_EXT = {
    ".scr", ".cfg", ".urc", ".txt", ".shader", ".st", ".tik", ".inc",
    ".c", ".cpp", ".cc", ".h", ".hpp", ".inl",
    ".py", ".ps1", ".psm1", ".js", ".ts", ".mjs", ".cjs", ".json", ".md",
    ".bat", ".cmd", ".sh", ".yml", ".yaml", ".cmake", ".in", ".xml", ".css",
    ".html", ".glsl", ".vert", ".frag", ".l", ".y",
}

# Extensions worth a per-file row with line counts and a derived summary.
SOURCE_EXT = {
    ".scr", ".cfg", ".urc", ".shader", ".st", ".tik",
    ".c", ".cpp", ".cc", ".h", ".hpp", ".inl",
    ".py", ".ps1", ".psm1", ".js", ".ts", ".bat", ".cmd", ".sh",
    ".glsl", ".vert", ".frag", ".l", ".y", ".cmake",
}

# Size ceilings for the AUTHORED docs, in KB.
#
# cerebrum.md reached 525 KB because its filling rule ("the bar is LOW, add it")
# had no counterweight, which made its using rule ("read it before generating
# code") physically impossible. A budget is the counterweight. Enforcing it in a
# tool rather than in a paragraph is the whole point: an instruction telling
# someone to prune is the same class of thing that already failed three times.
AUTHORED_CEILINGS_KB = {
    "SOURCE_OF_TRUTH.md": 40,
    "TRAPS.md": 60,
    "DECISIONS.md": 45,
    "OPEN.md": 45,
    "FEATURES.md": 90,
    "ENGINE.md": 40,
    "HISTORY.md": 30,
    "21-user-preferences.md": 12,
}

BANNER_MD = (
    "<!-- ============================================================\n"
    "     DO NOT EDIT - generated by docs/tools/docgen.py\n"
    "     Any edit to this file is destroyed on the next generation.\n"
    "     Regenerate : python docs/tools/docgen.py build\n"
    "     Verify     : python docs/tools/docgen.py check   (exit 1 == stale)\n"
    "     Regenerates automatically on Stop via .wolf/hooks/stop.js\n"
    "     ============================================================ -->\n"
)

BANNER_TSV = (
    "# DO NOT EDIT - generated by docs/tools/docgen.py\n"
    "# Regenerate: python docs/tools/docgen.py build\n"
)


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------

def rel(p: str) -> str:
    """Repo-relative path with forward slashes."""
    return os.path.relpath(p, ROOT).replace("\\", "/")


def read_bytes(path: str) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return b""


_TEXT_CACHE: dict[str, str] = {}


def read_text(path: str) -> str:
    hit = _TEXT_CACHE.get(path)
    if hit is not None:
        return hit
    raw = read_bytes(path)
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    txt = raw.decode("utf-8", errors="replace")
    _TEXT_CACHE[path] = txt
    return txt


def line_starts(text: str) -> list[int]:
    starts = [0]
    idx = text.find("\n")
    while idx != -1:
        starts.append(idx + 1)
        idx = text.find("\n", idx + 1)
    return starts


def line_of(starts: list[int], offset: int) -> int:
    return bisect.bisect_right(starts, offset)


def md_cell(s: str, limit: int = 0) -> str:
    """Escape a value for a markdown table cell."""
    s = (s or "").replace("\r", " ").replace("\n", " ").replace("|", "\\|")
    s = re.sub(r"\s+", " ", s).strip()
    if limit and len(s) > limit:
        s = s[: limit - 1].rstrip() + "\u2026"
    return s


def code(s: str) -> str:
    return "`" + md_cell(s) + "`" if s else ""


def run_git(repo: str, args: list[str], timeout: float = 15.0) -> str:
    path = os.path.join(ROOT, repo)
    if not os.path.isdir(os.path.join(path, ".git")):
        return ""
    try:
        out = subprocess.run(
            ["git", "-C", path] + args,
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return out.stdout or ""
    except Exception:
        return ""


def git_porcelain(repo: str) -> list[str]:
    """Dirty-file list with the generator's own output filtered out."""
    raw = run_git(repo, ["status", "--porcelain"])
    return [l for l in raw.split("\n")
            if l.strip() and SELF_EXCLUDE not in l.replace("\\", "/")]


# --------------------------------------------------------------------------
# Tree sweep - covers EVERY file, no incremental bookkeeping anywhere
# --------------------------------------------------------------------------

class FileRec:
    __slots__ = ("relpath", "size", "ext", "area")

    def __init__(self, relpath: str, size: int, ext: str, area: str):
        self.relpath = relpath
        self.size = size
        self.ext = ext
        self.area = area


def sweep() -> list[FileRec]:
    """Full recursive sweep of the workspace. ~0.1s for 34k files on Windows
    because entry.stat() reuses the FindNextFile data."""
    files: list[FileRec] = []

    def walk(abs_dir: str, area: str) -> None:
        try:
            entries = list(os.scandir(abs_dir))
        except OSError:
            return
        for entry in sorted(entries, key=lambda e: e.name.lower()):
            try:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in SKIP_DIRS:
                        continue
                    sub_area = area if area else entry.name
                    walk(entry.path, sub_area)
                else:
                    r = rel(entry.path)
                    if r.startswith(SELF_EXCLUDE + "/"):
                        continue
                    st = entry.stat()
                    ext = os.path.splitext(entry.name)[1].lower()
                    files.append(FileRec(r, st.st_size, ext, area or "<root>"))
            except OSError:
                continue

    walk(ROOT, "")
    files.sort(key=lambda f: f.relpath)
    return files


def is_indexed(f: FileRec) -> bool:
    """Per-file indexing scope: project source, not reference dumps."""
    return f.area not in NON_SOURCE_AREAS


# --------------------------------------------------------------------------
# Input fingerprint - the cache that makes the Stop hook nearly free
# --------------------------------------------------------------------------

def fingerprint(files: list[FileRec]) -> str:
    """Hash of everything the generated docs are a function of.

    Cheap by construction: path+size for the sweep, mtime+size for buglog.json,
    HEAD sha + dirty-file count per repo. No file contents are read here.
    """
    h = hashlib.sha256()
    h.update(TOOL_VERSION.encode())
    agg: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for f in files:
        if is_indexed(f):
            h.update(f.relpath.encode("utf-8", "replace"))
            h.update(str(f.size).encode())
        else:
            # Reference dumps appear in the census as (count, bytes) only, so
            # that is exactly the granularity they are fingerprinted at. If the
            # fingerprint were coarser than the output, `check` would disagree
            # with the fast path - which is precisely the bug this avoids.
            st = agg[f.area]
            st[0] += 1
            st[1] += f.size
    for area in sorted(agg):
        h.update(f"{area}:{agg[area][0]}:{agg[area][1]}".encode())
    buglog = os.path.join(ROOT, ".wolf", "buglog.json")
    try:
        st = os.stat(buglog)
        h.update(f"buglog:{st.st_size}:{int(st.st_mtime)}".encode())
    except OSError:
        h.update(b"buglog:missing")
    for repo, _desc in GIT_REPOS:
        head = run_git(repo, ["rev-parse", "HEAD"], timeout=5).strip()
        h.update(f"{repo}:{head}:{len(git_porcelain(repo))}".encode())
    return h.hexdigest()


# --------------------------------------------------------------------------
# Comment stripping (so a commented-out Cvar_Get never becomes documentation)
# --------------------------------------------------------------------------

_C_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"' r"|'(?:\\.|[^'\\])*'" r"|//[^\n]*|/\*.*?\*/", re.S)


def _blank_keep_lines(text: str) -> str:
    return re.sub(r"[^\n]", " ", text)


def strip_c_comments(src: str) -> str:
    """Remove // and /* */ comments while preserving every byte offset, so
    line numbers computed afterwards still point at the real source line."""
    def repl(m: re.Match) -> str:
        tok = m.group(0)
        if tok.startswith("//") or tok.startswith("/*"):
            return _blank_keep_lines(tok)
        return tok
    return _C_TOKEN.sub(repl, src)


def strip_script_comments(src: str) -> str:
    """MOHAA .scr / .cfg use // line comments. Offsets preserved."""
    out = []
    for line in src.split("\n"):
        in_str = False
        cut = None
        i = 0
        while i < len(line) - 1:
            ch = line[i]
            if ch == '"':
                in_str = not in_str
            elif not in_str and ch == "/" and line[i + 1] == "/":
                cut = i
                break
            i += 1
        if cut is not None:
            line = line[:cut] + " " * (len(line) - cut)
        out.append(line)
    return "\n".join(out)


def split_call_args(text: str, open_idx: int, budget: int = 4000):
    """Balanced-paren argument split. Returns (args, close_idx) or (None, -1)."""
    i = open_idx + 1
    depth = 1
    cur: list[str] = []
    args: list[str] = []
    n = min(len(text), open_idx + budget)
    while i < n:
        ch = text[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            cur.append(text[i:j + 1])
            i = j + 1
            continue
        if ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth -= 1
            if depth == 0:
                args.append("".join(cur))
                return args, i
            cur.append(ch)
        elif ch == "," and depth == 1:
            args.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    return None, -1


_STR_ARG = re.compile(r'^\s*"((?:\\.|[^"\\])*)"\s*$')


def as_string_literal(arg: str):
    m = _STR_ARG.match(arg or "")
    if not m:
        return None
    return m.group(1)


def norm_flags(arg: str) -> str:
    s = re.sub(r"\s+", " ", (arg or "").strip())
    return s


# --------------------------------------------------------------------------
# 1. Engine cvar inventory
# --------------------------------------------------------------------------

_CVAR_GET = re.compile(
    r"\b(?:ri|gi|cgi|uii|sti)\s*(?:\.|->)\s*Cvar_Get2?\s*\("
    r"|\b(?:trap_|LISTENER_|VO_)?Cvar_Get2?\s*\("
)


class CvarReg:
    __slots__ = ("name", "default", "flags", "file", "line")

    def __init__(self, name, default, flags, file, line):
        self.name = name
        self.default = default
        self.flags = flags
        self.file = file
        self.line = line

    def key(self):
        return (self.name.lower(), self.file, self.line)


def scan_engine_cvars(files: list[FileRec]):
    regs: list[CvarReg] = []
    dynamic = 0
    scanned = 0
    for f in files:
        if not f.relpath.startswith(ENGINE + "/code/"):
            continue
        if f.ext not in (".c", ".cpp", ".cc", ".h", ".hpp", ".inl"):
            continue
        abspath = os.path.join(ROOT, f.relpath)
        raw = read_text(abspath)
        if "Cvar_Get" not in raw:
            continue
        scanned += 1
        src = strip_c_comments(raw)
        starts = line_starts(src)
        anchor = f.relpath[len(ENGINE) + 6:]        # strip "openmohaa-hzm/code/"
        for m in _CVAR_GET.finditer(src):
            open_idx = src.index("(", m.end() - 1) if src[m.end() - 1] != "(" else m.end() - 1
            args, close = split_call_args(src, open_idx)
            if args is None or len(args) < 2:
                continue
            name = as_string_literal(args[0])
            if name is None:
                dynamic += 1
                continue
            default = as_string_literal(args[1])
            if default is None:
                default = norm_flags(args[1])       # e.g. a macro or va() call
            flags = norm_flags(args[2]) if len(args) > 2 else ""
            regs.append(CvarReg(name, default, flags, anchor, line_of(starts, m.start())))
    regs.sort(key=lambda r: (r.name.lower(), r.file, r.line))
    return regs, dynamic, scanned


def gen_cvars_engine(regs, dynamic, scanned) -> str:
    by_name: dict[str, list[CvarReg]] = defaultdict(list)
    for r in regs:
        by_name[r.name].append(r)

    conflicts = []
    for name, rows in by_name.items():
        defaults = {r.default for r in rows}
        if len(defaults) > 1:
            conflicts.append((name, rows))
    conflicts.sort(key=lambda x: x[0].lower())

    prefixes = Counter()
    for name in by_name:
        pre = name.split("_", 1)[0] + "_" if "_" in name else "(no prefix)"
        prefixes[pre] += 1

    L = [BANNER_MD, "# Engine cvar inventory (generated)\n",
         f"Every `Cvar_Get` / `Cvar_Get2` call under `{ENGINE}/code/` whose cvar name is a "
         "string literal. Anchors are `path:line` relative to that directory. Defaults and "
         "flags are verbatim from source.\n",
         f"- **{len(by_name)}** distinct cvars across **{len(regs)}** registration sites "
         f"in **{scanned}** translation units.\n",
         f"- **{dynamic}** call sites use a computed name (a variable or `va()`) and cannot "
         "be listed here. That number is reported rather than hidden - if it grows, something "
         "is registering cvars this inventory cannot see.\n",
         f"- **{len(conflicts)}** cvars are registered with **different defaults** in different "
         "files. Those are real (usually renderergl1 vs renderergl2), not transcription errors.\n"]

    L.append("\n## Registrations by prefix\n")
    L.append("| prefix | distinct cvars |\n|---|---:|\n")
    for pre, n in sorted(prefixes.items(), key=lambda x: (-x[1], x[0])):
        L.append(f"| `{pre}` | {n} |\n")

    if conflicts:
        L.append("\n## Conflicting defaults (same cvar, different value per file)\n")
        L.append("| cvar | default | flags | anchor |\n|---|---|---|---|\n")
        for name, rows in conflicts:
            for r in rows:
                L.append(f"| `{name}` | {code(r.default)} | {code(r.flags)} | `{r.file}:{r.line}` |\n")

    L.append("\n## All registrations\n")
    L.append("| cvar | default | flags | anchor |\n|---|---|---|---|\n")
    for r in regs:
        L.append(f"| `{r.name}` | {code(r.default)} | {code(r.flags)} | `{r.file}:{r.line}` |\n")
    return "".join(L)


# --------------------------------------------------------------------------
# 2. coop_* cvar inventory (scripts + cfg + ui + engine)
# --------------------------------------------------------------------------

_SCR_CVAR = re.compile(
    r"\b(getcvar|setcvar|cvar_set_f)\s*(?:\(\s*)?\"([A-Za-z0-9_]+)\"\s*(.?)",
    re.IGNORECASE | re.S,
)
_CFG_SET = re.compile(
    r"^\s*(set|seta|sets|setu)\s+([A-Za-z0-9_]+)\s*(.*)$",
    re.IGNORECASE,
)
# In a .urc, a bare `coop_*` token is usually a WIDGET NAME, not a cvar. Only
# these directives take a cvar as their first argument. Matching bare tokens
# inflated the inventory by ~600 phantom cvars.
_URC_CVAR = re.compile(
    r"\b(linkcvar|enabledcvar|linkcvartoshader|modelxformcvar|scalecvar"
    r"|modelspincvar|modelattachcvar|modelanimcvar)\s+\"([A-Za-z0-9_]+)\"",
    re.IGNORECASE,
)
_URC_STUFF_SET = re.compile(
    r"\b(set|seta|sets|setu)\s+([A-Za-z0-9_]+)", re.IGNORECASE
)


def scan_mod_cvars(files: list[FileRec]):
    script_use: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    cfg_seed: dict[str, list[tuple[str, int, str, str]]] = defaultdict(list)
    ui_ref: dict[str, set[str]] = defaultdict(set)
    # `getcvar("coop_chal_" + local.id)` builds a name at runtime. The literal is
    # a PREFIX, not a cvar, and must not be inventoried as one.
    dynamic_prefix: dict[str, list[tuple[str, int]]] = defaultdict(list)

    for f in files:
        if not f.relpath.startswith(MOD + "/"):
            continue
        abspath = os.path.join(ROOT, f.relpath)
        short = f.relpath[len(MOD) + 1:]

        if f.ext == ".scr":
            raw = read_text(abspath)
            if "cvar" not in raw.lower():
                continue
            src = strip_script_comments(raw)
            starts = line_starts(src)
            for m in _SCR_CVAR.finditer(src):
                verb, name, nxt = m.group(1).lower(), m.group(2), m.group(3)
                ln = line_of(starts, m.start())
                if nxt == "+":
                    dynamic_prefix[name].append((short, ln))
                    continue
                script_use[name].append((short, ln, verb))

        elif f.ext == ".cfg":
            raw = read_text(abspath)
            src = strip_script_comments(raw)
            for i, line in enumerate(src.split("\n"), 1):
                m = _CFG_SET.match(line)
                if not m:
                    continue
                verb, name, value = m.group(1).lower(), m.group(2), m.group(3).strip()
                value = value.strip('"').strip()
                cfg_seed[name].append((short, i, verb, value))

        elif f.ext == ".urc":
            raw = read_text(abspath)
            if "cvar" not in raw.lower() and "stuffcommand" not in raw.lower():
                continue
            for m in _URC_CVAR.finditer(raw):
                ui_ref[m.group(2)].add(short)
            for m in re.finditer(r'stuffcommand\s+"([^"]*)"', raw, re.I):
                for s in _URC_STUFF_SET.finditer(m.group(1)):
                    ui_ref[s.group(2)].add(short)

    return script_use, cfg_seed, ui_ref, dynamic_prefix


def _seed_class(path: str) -> str:
    p = path.lower()
    if p.endswith("coop_defaults.cfg"):
        return "DEFAULT"       # exec'd BEFORE the saved config -> a real default
    if p.endswith("autoexec.cfg"):
        return "FORCED"        # exec'd AFTER the saved config -> wipes the menu choice
    return "other"


def gen_cvars_coop(script_use, cfg_seed, ui_ref, dynamic_prefix, engine_regs) -> str:
    eng_by_name: dict[str, list[CvarReg]] = defaultdict(list)
    for r in engine_regs:
        eng_by_name[r.name].append(r)

    names = set()
    names |= {n for n in script_use if n.lower().startswith("coop_")}
    names |= {n for n in cfg_seed if n.lower().startswith("coop_")}
    names |= {n for n in ui_ref if n.lower().startswith("coop_")}
    names |= {n for n in eng_by_name if n.lower().startswith("coop_")}
    ordered = sorted(names, key=str.lower)

    n_engine = sum(1 for n in ordered if n in eng_by_name)
    n_cfg = sum(1 for n in ordered if n in cfg_seed)
    unseeded = [n for n in ordered if n not in eng_by_name and n not in cfg_seed]
    # The dangerous bucket: a script reads it, nothing seeds it, so `getcvar`
    # returns "" and a fallback branch silently decides the behaviour.
    unseeded_script = [n for n in unseeded if n in script_use]
    # Menu-only names, set at runtime by the UI or the engine. Not a defect.
    unseeded_ui_only = [n for n in unseeded if n not in script_use]
    forced_and_ui = [
        n for n in ordered
        if n in ui_ref and any(_seed_class(p) == "FORCED" for p, _l, _v, _val in cfg_seed.get(n, []))
    ]

    L = [BANNER_MD, "# `coop_*` cvar inventory (generated)\n",
         "Union of four sources, all swept fresh:\n\n"
         f"1. `getcvar` / `setcvar` sites in `{MOD}/**/*.scr`\n"
         f"2. `set` / `seta` lines in `{MOD}/**/*.cfg`\n"
         f"3. `coop_*` tokens in `{MOD}/**/*.urc` (menu bindings)\n"
         f"4. `Cvar_Get` registrations in `{ENGINE}/code/` (authoritative default when present)\n",
         "\n**Seed class matters.** `coop_defaults.cfg` is exec'd BEFORE the saved player "
         "config, so its values are true defaults a menu change overrides and persists. "
         "`autoexec.cfg` is exec'd AFTER, so anything set there re-forces the shipped value "
         "every launch and wipes the player's menu choice.\n",
         f"\n| metric | count |\n|---|---:|\n"
         f"| distinct `coop_*` cvars | {len(ordered)} |\n"
         f"| registered with a default by the engine | {n_engine} |\n"
         f"| seeded by a shipped cfg | {n_cfg} |\n"
         f"| seeded nowhere at all | {len(unseeded)} |\n"
         f"| **&nbsp;&nbsp;of those, read by a script** | **{len(unseeded_script)}** |\n"
         f"| &nbsp;&nbsp;of those, menu-only (set at runtime by the UI) | {len(unseeded_ui_only)} |\n"
         f"| menu-wired (`.urc`) | {len([n for n in ui_ref if n.lower().startswith('coop_')])} |\n"
         f"| menu-wired but FORCED by autoexec.cfg (cannot persist) | {len(forced_and_ui)} |\n"
         f"| runtime-built name prefixes (not cvars) | {len([n for n in dynamic_prefix if n.lower().startswith('coop_')])} |\n"]

    dyn = sorted((n for n in dynamic_prefix if n.lower().startswith("coop_")), key=str.lower)
    if dyn:
        L.append("\n## Runtime-built names\n")
        L.append("These literals are concatenated with a variable at the call site "
                 "(`getcvar(\"coop_chal_\" + local.id)`), so the real cvar name only exists at "
                 "runtime. They are **not** cvars and are excluded from the table below - listed "
                 "here so the omission is visible rather than silent.\n\n")
        for n in dyn:
            sites = dynamic_prefix[n]
            L.append(f"- `{n}*` — `{sites[0][0]}:{sites[0][1]}`"
                     + (f" (+{len(sites) - 1} more)" if len(sites) > 1 else "") + "\n")

    L.append("\n## Seeded nowhere, but a script reads it\n")
    L.append("**This is the bucket that costs you.** Nothing registers a default and no shipped cfg "
             "seeds it, so on a clean profile `getcvar` returns `\"\"` and a script fallback branch "
             "silently decides the behaviour. Each one is a feature whose real default exists only "
             "as an `if` in a script.\n\n")
    if unseeded_script:
        for i in range(0, len(unseeded_script), 6):
            L.append("- " + ", ".join("`" + n + "`" for n in unseeded_script[i:i + 6]) + "\n")
    else:
        L.append("_none_\n")

    L.append("\n## Seeded nowhere, referenced only by the UI\n")
    L.append("Menu-internal state (`enabledcvar` / `linkcvar` targets) written at runtime by the UI "
             "or the engine. Listed for completeness; an unseeded value here is normal, not a "
             "defect.\n\n")
    if unseeded_ui_only:
        for i in range(0, len(unseeded_ui_only), 8):
            L.append("- " + ", ".join("`" + n + "`" for n in unseeded_ui_only[i:i + 8]) + "\n")
    else:
        L.append("_none_\n")

    if forced_and_ui:
        L.append("\n## Menu-wired but forced by `autoexec.cfg`\n")
        L.append("These have a menu control, but `autoexec.cfg` re-applies the shipped value after "
                 "the saved config loads, so the player's choice never survives a restart. Move the "
                 "seed to `coop_defaults.cfg` to fix.\n\n")
        for n in forced_and_ui:
            seeds = "; ".join(f"`{v}` @ `{p}:{l}`" for p, l, _verb, v in sorted(cfg_seed[n])
                              if _seed_class(p) == "FORCED")
            L.append(f"- `{n}` - {seeds}\n")

    L.append("\n## All `coop_*` cvars\n")
    L.append("| cvar | engine default | flags | engine anchor | cfg seed | script use | ui |\n")
    L.append("|---|---|---|---|---|---|---|\n")
    for n in ordered:
        regs = eng_by_name.get(n, [])
        edef = code(regs[0].default) if regs else ""
        eflags = code(regs[0].flags) if regs else ""
        eanchor = f"`{regs[0].file}:{regs[0].line}`" if regs else ""
        if len(regs) > 1:
            eanchor += f" (+{len(regs) - 1})"
        seeds = sorted(cfg_seed.get(n, []))
        seed_txt = "<br>".join(
            f"{_seed_class(p)} `{md_cell(v, 24) or '(empty)'}` @ `{p}:{l}`"
            for p, l, _verb, v in seeds[:3]
        )
        if len(seeds) > 3:
            seed_txt += f"<br>(+{len(seeds) - 3} more)"
        uses = sorted(script_use.get(n, []))
        use_txt = ""
        if uses:
            use_txt = f"`{uses[0][0]}:{uses[0][1]}`"
            if len(uses) > 1:
                use_txt += f" (+{len(uses) - 1})"
        ui = sorted(ui_ref.get(n, ()))
        ui_txt = f"`{ui[0]}`" + (f" (+{len(ui) - 1})" if len(ui) > 1 else "") if ui else ""
        L.append(f"| `{n}` | {edef} | {eflags} | {eanchor} | {seed_txt} | {use_txt} | {ui_txt} |\n")
    return "".join(L)


# --------------------------------------------------------------------------
# 3. File map - the anatomy.md replacement. Full sweep, never incremental.
# --------------------------------------------------------------------------

_SCR_LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", re.M)

_SUMMARY_COMMENT = {
    ".scr": "//", ".cfg": "//", ".c": "//", ".cpp": "//", ".cc": "//",
    ".h": "//", ".hpp": "//", ".inl": "//", ".js": "//", ".ts": "//",
    ".py": "#", ".ps1": "#", ".psm1": "#", ".sh": "#", ".cmake": "#",
}


def derive_summary(abspath: str, ext: str) -> str:
    """First meaningful comment line - derived, never hand-written."""
    marker = _SUMMARY_COMMENT.get(ext)
    if not marker:
        return ""
    try:
        with open(abspath, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        return ""
    text = head.decode("utf-8", errors="replace")
    for line in text.split("\n")[:24]:
        s = line.strip()
        if not s.startswith(marker):
            continue
        s = s.lstrip(marker + " \t*/=-#").strip()
        s = s.strip("/*-= \t")
        if len(s) < 4:
            continue
        if re.fullmatch(r"[^A-Za-z0-9]+", s):
            continue
        return md_cell(s, 110)
    return ""


_LINES_CACHE: dict[str, int] = {}


def count_lines(abspath: str) -> int:
    hit = _LINES_CACHE.get(abspath)
    if hit is not None:
        return hit
    cached_text = _TEXT_CACHE.get(abspath)
    if cached_text is not None:
        n = cached_text.count("\n") + (0 if cached_text.endswith("\n") or not cached_text else 1)
    else:
        raw = read_bytes(abspath)
        n = 0 if not raw else raw.count(b"\n") + (0 if raw.endswith(b"\n") else 1)
    _LINES_CACHE[abspath] = n
    return n


def gen_filemap(files: list[FileRec]):
    total_files = len(files)
    total_bytes = sum(f.size for f in files)

    # --- census of EVERY area, including the ones not indexed per-file ---
    area_stats: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for f in files:
        st = area_stats[f.area]
        st[0] += 1
        st[1] += f.size

    indexed = [f for f in files if is_indexed(f)]
    src = [f for f in indexed if f.ext in SOURCE_EXT]

    # --- per-directory breakdown inside the indexed scope ---
    dir_stats: dict[str, Counter] = defaultdict(Counter)
    dir_bytes: dict[str, int] = defaultdict(int)
    for f in indexed:
        d = os.path.dirname(f.relpath) or "."
        dir_stats[d][f.ext or "(none)"] += 1
        dir_bytes[d] += f.size

    ext_counter = Counter(f.ext or "(none)" for f in files)

    L = [BANNER_MD, "# File map (generated by full sweep)\n",
         "This file replaces `.wolf/anatomy.md`. The difference that matters: anatomy.md was "
         "built **incrementally** - a file appeared in it only if a session happened to read it - "
         "so complete coverage was structurally impossible under its own rules. This map is a "
         "**full sweep of the workspace on every generation**. It cannot be partial.\n",
         f"\n| metric | value |\n|---|---:|\n"
         f"| files in the workspace | {total_files:,} |\n"
         f"| bytes | {total_bytes / 1e9:.1f} GB |\n"
         f"| files in project scope (indexed per-file) | {len(indexed):,} |\n"
         f"| source files (per-file rows with line counts) | {len(src):,} |\n",
         "\nSkipped directories (never descended, anywhere): "
         + ", ".join("`" + d + "`" for d in sorted(SKIP_DIRS)) + ".\n",
         "\nComplete per-file index: **`filemap.tsv`** in this directory - every in-scope file, "
         "one tab-separated row, greppable. Use it instead of guessing paths.\n"]

    L.append("\n## Workspace census - every area, nothing hidden\n")
    L.append("Areas marked *reference* are counted here but not indexed file-by-file: they are "
             "extraction dumps and staging trees that churn constantly, and indexing them would "
             "make `docs check` fail on noise rather than on real drift.\n\n")
    L.append("| area | files | size | indexed per-file | what it is |\n|---|---:|---:|---|---|\n")
    for area in sorted(area_stats, key=lambda a: (-area_stats[a][0], a.lower())):
        n, b = area_stats[area]
        is_ref = area in NON_SOURCE_AREAS
        note = NON_SOURCE_AREAS.get(area) or SOURCE_AREAS.get(area, "")
        flag = "no - reference" if is_ref else "**yes**"
        L.append(f"| `{area}` | {n:,} | {b / 1e6:.1f} MB | {flag} | {note} |\n")

    L.append("\n## Extension census (whole workspace)\n")
    L.append("| ext | files |\n|---|---:|\n")
    for ext, n in ext_counter.most_common(40):
        L.append(f"| `{ext}` | {n:,} |\n")

    L.append("\n## Directories in project scope\n")
    L.append("| directory | files | size | top extensions |\n|---|---:|---:|---|\n")
    for d in sorted(dir_stats):
        c = dir_stats[d]
        tops = ", ".join(f"{e}\u00d7{n}" for e, n in c.most_common(4))
        L.append(f"| `{d}` | {sum(c.values()):,} | {dir_bytes[d] / 1e6:.2f} MB | {md_cell(tops)} |\n")

    # --- source index, grouped by the directory the reader thinks in ---
    L.append("\n## Source index\n")
    L.append("Line counts and summaries are derived (summary = first meaningful comment line). "
             "A blank summary means the file has no header comment, not that it is unimportant.\n")
    groups: dict[str, list[FileRec]] = defaultdict(list)
    for f in src:
        groups[os.path.dirname(f.relpath) or "."].append(f)
    for d in sorted(groups):
        rows = sorted(groups[d], key=lambda f: f.relpath)
        L.append(f"\n### `{d}/` \u2014 {len(rows)} source files\n\n")
        L.append("| file | lines | size | summary |\n|---|---:|---:|---|\n")
        for f in rows:
            ap = os.path.join(ROOT, f.relpath)
            lines = count_lines(ap)
            summary = derive_summary(ap, f.ext)
            L.append(f"| `{os.path.basename(f.relpath)}` | {lines:,} | "
                     f"{f.size / 1024:.1f} KB | {summary} |\n")

    # --- the complete machine index ---
    T = [BANNER_TSV, "# columns: path\tbytes\text\tlines(0 if not text)\tarea\n"]
    for f in indexed:
        ap = os.path.join(ROOT, f.relpath)
        lines = count_lines(ap) if f.ext in TEXT_EXT else 0
        T.append(f"{f.relpath}\t{f.size}\t{f.ext}\t{lines}\t{f.area}\n")

    return "".join(L), "".join(T)


# --------------------------------------------------------------------------
# 4. Coop subsystem inventory + boot order
# --------------------------------------------------------------------------

_BOOT_CALL = re.compile(
    r"^\s*(waitthread|thread|exec)\s+(\S+)", re.M
)


def gen_subsystems(files: list[FileRec]) -> str:
    coop = [f for f in files if f.relpath.startswith(MOD + "/coop_mod/") and f.ext == ".scr"]
    maps = [f for f in files
            if re.fullmatch(re.escape(MOD) + r"/maps/[^/]+\.scr", f.relpath)]

    # which map scripts are coop-integrated
    integrated = []
    for f in sorted(maps, key=lambda f: f.relpath):
        txt = read_text(os.path.join(ROOT, f.relpath))
        if "coop_mod/main.scr::main" in txt:
            theatre = ("AA" if "coop_aaMap" in txt else
                       "SH" if "coop_shMap" in txt else
                       "BT" if "coop_btMap" in txt else "?")
            integrated.append((os.path.basename(f.relpath), theatre))

    # boot order out of main.scr::main
    boot: list[tuple[int, str, str]] = []
    main_path = os.path.join(ROOT, MOD, "coop_mod", "main.scr")
    if os.path.exists(main_path):
        src = strip_script_comments(read_text(main_path))
        lines = src.split("\n")
        start = None
        for i, line in enumerate(lines):
            if re.match(r"^main\s*:", line):
                start = i
                break
        if start is not None:
            depth = 0
            seen_open = False
            for i in range(start, len(lines)):
                line = lines[i]
                depth += line.count("{") - line.count("}")
                if "{" in line:
                    seen_open = True
                m = _BOOT_CALL.match(line)
                if m:
                    boot.append((i + 1, m.group(1), m.group(2)))
                if seen_open and depth <= 0 and i > start:
                    break

    L = [BANNER_MD, "# Coop subsystem inventory (generated)\n",
         f"| metric | value |\n|---|---:|\n"
         f"| `coop_mod/*.scr` files | {len(coop)} |\n"
         f"| total lines in `coop_mod/` | {sum(count_lines(os.path.join(ROOT, f.relpath)) for f in coop):,} |\n"
         f"| top-level `maps/*.scr` | {len(maps)} |\n"
         f"| of those, coop-integrated (call `coop_mod/main.scr::main`) | {len(integrated)} |\n"]

    L.append("\n## Boot order - `coop_mod/main.scr::main`\n")
    L.append("Extracted from the source in order. Every one of these runs **synchronously in a "
             "single frame** - `wait` and `waitframe` are forbidden in or before this block.\n\n")
    L.append("| # | line | verb | target |\n|---:|---:|---|---|\n")
    for idx, (ln, verb, target) in enumerate(boot, 1):
        L.append(f"| {idx} | {ln} | `{verb}` | `{md_cell(target)}` |\n")
    if not boot:
        L.append("| - | - | - | _main.scr::main not found_ |\n")

    L.append("\n## `coop_mod/` scripts\n")
    L.append("| file | lines | labels | summary |\n|---|---:|---:|---|\n")
    for f in sorted(coop, key=lambda f: f.relpath):
        ap = os.path.join(ROOT, f.relpath)
        txt = read_text(ap)
        labels = len(_SCR_LABEL.findall(strip_script_comments(txt)))
        L.append(f"| `{os.path.basename(f.relpath)}` | {count_lines(ap):,} | {labels} | "
                 f"{derive_summary(ap, '.scr')} |\n")

    L.append("\n## Coop-integrated map scripts\n")
    L.append("| map | theatre flag |\n|---|---|\n")
    for name, theatre in integrated:
        L.append(f"| `{name}` | {theatre} |\n")

    non = sorted({os.path.basename(f.relpath) for f in maps} -
                 {n for n, _t in integrated})
    L.append(f"\n### Not coop-integrated ({len(non)})\n\n")
    for i in range(0, len(non), 10):
        L.append("- " + ", ".join("`" + n + "`" for n in non[i:i + 10]) + "\n")
    return "".join(L)


# --------------------------------------------------------------------------
# 5. Fix ledger + per-file index, from .wolf/buglog.json
# --------------------------------------------------------------------------

_REVERT_RE = re.compile(r"\brevert(ed|ing)?\b|\brolled back\b|\bbacked out\b", re.I)
_VERIFIED_RE = re.compile(r"\buser[- ]confirmed\b|\bconfirmed fixed\b|\bverified\b|\bplaytest(ed)? (ok|good|confirm)", re.I)
_PENDING_RE = re.compile(r"\bnot yet\b|\bpending\b|\buntested\b|\bunverified\b|\bqueued\b|\bawaiting\b", re.I)


def load_buglog():
    path = os.path.join(ROOT, ".wolf", "buglog.json")
    try:
        with open(path, "rb") as fh:
            data = json.loads(fh.read().decode("utf-8", errors="replace"))
    except Exception:
        return []
    if isinstance(data, dict):
        for k in ("bugs", "entries", "items"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
        else:
            return []
    return [e for e in data if isinstance(e, dict)]


def _bug_sort_key(e):
    ts = str(e.get("timestamp") or e.get("last_seen") or "9999")
    return (ts, str(e.get("id") or ""))


def gen_fix_ledger(entries):
    rows = sorted(entries, key=_bug_sort_key)
    dates = [str(e.get("timestamp", ""))[:10] for e in rows if e.get("timestamp")]
    months = Counter(d[:7] for d in dates if len(d) >= 7)

    L = [BANNER_MD, "# Fix ledger (generated from `.wolf/buglog.json`)\n",
         f"**{len(rows)}** entries. `buglog.json` is the one OpenWolf artifact that never rotted, "
         "because it is keyed, schema'd and one-entry-per-event. This ledger is a read-only view of "
         "it - fix the buglog, not this file.\n",
         "\n**Reading an entry in isolation is unsafe.** The schema has no `superseded_by` and no "
         "`status`, so a later entry can silently reverse an earlier one. Always check "
         "`FIX_INDEX.md` for the full history of the file first.\n"]

    if months:
        L.append("\n## Entries per month\n\n| month | entries |\n|---|---:|\n")
        for m in sorted(months):
            L.append(f"| {m} | {months[m]} |\n")

    L.append("\n## Chronological\n")
    L.append("Signals are keyword matches on the entry text, not a status field - `R` revert "
             "language, `V` verification language, `P` pending/untested language. An entry can "
             "carry several. They are hints for where to look, never a verdict.\n\n")
    L.append("| id | date | file | signals | symptom | fix |\n|---|---|---|---|---|---|\n")
    for e in rows:
        blob = " ".join(str(e.get(k, "")) for k in ("error_message", "fix", "root_cause"))
        sig = ""
        if _REVERT_RE.search(blob):
            sig += "R"
        if _VERIFIED_RE.search(blob):
            sig += "V"
        if _PENDING_RE.search(blob):
            sig += "P"
        L.append("| `{id}` | {date} | {file} | {sig} | {sym} | {fix} |\n".format(
            id=md_cell(str(e.get("id", "?"))),
            date=md_cell(str(e.get("timestamp", ""))[:10]),
            file=code(md_cell(str(e.get("file", "")), 70)),
            sig=sig or "-",
            sym=md_cell(str(e.get("error_message", "")), 150),
            fix=md_cell(str(e.get("fix", "")), 150),
        ))
    return "".join(L)


def gen_fix_index(entries):
    by_file: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        raw = str(e.get("file", "")).strip()
        if not raw:
            by_file["(unspecified)"].append(e)
            continue
        for part in re.split(r"[,;]\s*", raw):
            part = part.strip().replace("\\", "/")
            if part:
                by_file[part].append(e)

    by_tag: dict[str, list[str]] = defaultdict(list)
    for e in entries:
        for t in (e.get("tags") or []):
            by_tag[str(t).lower()].append(str(e.get("id", "?")))

    L = [BANNER_MD, "# Fix index by file and tag (generated)\n",
         "The single addition `buglog.json` most needs and does not have: **file -> ordered bug "
         "ids**. Reading one entry tells you what changed once; reading the ordered list tells you "
         "the file's current net state. Consult this before touching any file that appears here.\n",
         f"\n{len(by_file):,} distinct file paths, {len(by_tag):,} distinct tags.\n"]

    L.append("\n## Files with the most history\n\n| file | entries | bug ids (oldest first) |\n|---|---:|---|\n")
    hot = sorted(by_file.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:40]
    for path, es in hot:
        ids = " ".join("`" + str(x.get("id", "?")) + "`" for x in sorted(es, key=_bug_sort_key))
        L.append(f"| `{md_cell(path, 90)}` | {len(es)} | {md_cell(ids, 400)} |\n")

    L.append("\n## All files\n\n| file | entries | bug ids (oldest first) |\n|---|---:|---|\n")
    for path in sorted(by_file, key=str.lower):
        es = sorted(by_file[path], key=_bug_sort_key)
        ids = " ".join("`" + str(x.get("id", "?")) + "`" for x in es)
        L.append(f"| `{md_cell(path, 110)}` | {len(es)} | {md_cell(ids, 600)} |\n")

    L.append("\n## Tags\n\n| tag | entries | bug ids |\n|---|---:|---|\n")
    for tag in sorted(by_tag, key=str.lower):
        ids = by_tag[tag]
        L.append(f"| `{md_cell(tag, 50)}` | {len(ids)} | "
                 f"{md_cell(' '.join('`' + i + '`' for i in sorted(set(ids))), 400)} |\n")
    return "".join(L)


# --------------------------------------------------------------------------
# 6. Chronology, from git history in every repo
# --------------------------------------------------------------------------

FULL_LOG_SINCE = "2026-01-01"


def gen_chronology() -> str:
    L = [BANNER_MD, "# Chronology (generated from git)\n",
         "Three separate repositories. The mod and the engine are **nested repos with their own "
         "remotes** - a commit in one says nothing about the other, and the deployed binaries are "
         "not traceable to any commit.\n"]

    for repo, desc in GIT_REPOS:
        path = os.path.join(ROOT, repo)
        label = repo if repo != "." else "(workspace root)"
        L.append(f"\n## `{label}` \u2014 {desc}\n\n")
        if not os.path.isdir(os.path.join(path, ".git")):
            L.append("_not a git repository_\n")
            continue

        branch = run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"]).strip() or "?"
        head = run_git(repo, ["log", "-1", "--pretty=%h %ad %s", "--date=short"]).strip()
        remotes = run_git(repo, ["remote", "-v"]).strip().split("\n")
        remotes = sorted({r.split("\t")[0] + " " + r.split("\t")[1].split(" ")[0]
                          for r in remotes if "\t" in r})
        porcelain = git_porcelain(repo)
        modified = sum(1 for l in porcelain if not l.startswith("??"))
        untracked = sum(1 for l in porcelain if l.startswith("??"))
        # Exclude the generator's own output, exactly as git_porcelain() does. Without this
        # the stat counts the lines `build` just wrote into docs/generated, so every build
        # changes the number CHRONOLOGY reports about itself and `check` can NEVER pass:
        # build wrote "291 insertions", check regenerates and computes "298", flags CHRONOLOGY
        # stale, and manifest.json cascades because it stores CHRONOLOGY's sha256. SELF_EXCLUDE
        # was already applied to the porcelain FILE LIST but this second site was missed.
        shortstat = run_git(repo, ["diff", "--shortstat", "--",
                                   ".", f":(exclude){SELF_EXCLUDE}"]).strip()
        allc = run_git(repo, ["log", "--pretty=%ad", "--date=short"]).split("\n")
        allc = [c for c in allc if c.strip()]

        L.append(f"| | |\n|---|---|\n")
        L.append(f"| branch | `{md_cell(branch)}` |\n")
        L.append(f"| HEAD | `{md_cell(head)}` |\n")
        L.append(f"| commits | {len(allc):,} |\n")
        L.append(f"| remotes | {md_cell(', '.join(remotes)) or '(none)'} |\n")
        L.append(f"| **uncommitted** | **{modified} modified, {untracked} untracked** |\n")
        if shortstat:
            L.append(f"| unstaged diff | {md_cell(shortstat)} |\n")

        if untracked or modified:
            L.append(f"\n> Working tree is dirty. Everything in those {modified + untracked} files "
                     "exists only here - a `git checkout` destroys it with no restore point.\n")

        months = Counter(d[:7] for d in allc if len(d) >= 7)
        if months:
            L.append("\n<details><summary>commits per month (all history)</summary>\n\n")
            L.append("| month | commits |\n|---|---:|\n")
            for m in sorted(months, reverse=True):
                L.append(f"| {m} | {months[m]} |\n")
            L.append("\n</details>\n")

        log = run_git(repo, ["log", f"--since={FULL_LOG_SINCE}",
                             "--pretty=%h%x1f%ad%x1f%an%x1f%s", "--date=short"])
        rows = [r for r in log.split("\n") if r.count("\x1f") == 3]
        L.append(f"\n### Commits since {FULL_LOG_SINCE} ({len(rows)})\n\n")
        if rows:
            L.append("| sha | date | author | subject |\n|---|---|---|---|\n")
            for r in rows:
                sha, date, author, subj = r.split("\x1f")
                L.append(f"| `{md_cell(sha)}` | {md_cell(date)} | {md_cell(author, 24)} | "
                         f"{md_cell(subj, 130)} |\n")
        else:
            L.append("_none_\n")
    return "".join(L)


# --------------------------------------------------------------------------
# 7. Generated-set index
# --------------------------------------------------------------------------

def authored_budget() -> list[tuple[str, int, int, bool]]:
    """(file, kb, ceiling_kb, over) for each authored doc with a budget."""
    rows = []
    for name in sorted(AUTHORED_CEILINGS_KB):
        ceiling = AUTHORED_CEILINGS_KB[name]
        try:
            kb = int(round(os.path.getsize(os.path.join(ROOT, "docs", name)) / 1024))
        except OSError:
            kb = 0
        rows.append((name, kb, ceiling, kb > ceiling))
    return rows


def warn_budget() -> None:
    over = [r for r in authored_budget() if r[3]]
    if not over:
        return
    print("docgen: authored docs over budget - MERGE AND PRUNE, do not append:", file=sys.stderr)
    for name, kb, ceiling, _ in over:
        print(f"  {name}: {kb} KB > {ceiling} KB ceiling", file=sys.stderr)


def gen_readme(names: list[str], fp: str) -> str:
    L = [BANNER_MD, "# docs/generated \u2014 derived documentation\n",
         "Everything in this directory is a **pure function of the repository state**. It is "
         "rebuilt from scratch, never patched. If one of these files is wrong, the fix is in the "
         "code, the git history, `.wolf/buglog.json`, or `docs/tools/docgen.py` - never here.\n",
         "\n## The split that keeps this doc set alive\n",
         "| | authored (`docs/*.md`) | generated (`docs/generated/*`) |\n|---|---|---|\n"
         "| written by | a human, or Claude with judgement | `docs/tools/docgen.py` |\n"
         "| can drift | yes - needs review | **no** - regenerated |\n"
         "| holds | judgement, causation, war stories, open questions | inventories, indexes, counts |\n"
         "| examples | `SOURCE_OF_TRUTH.md`, `TRAPS.md`, `DECISIONS.md`, `OPEN.md` | this directory |\n",
         "\nThe rule: **anything extractable from code, git or buglog.json must be generated.** "
         "Hand-maintained inventories rot - that is exactly how `.wolf/anatomy.md` ended at ~2% "
         "coverage while promising completeness.\n",
         "\n## Files\n\n| file | what it is | source of truth |\n|---|---|---|\n"
         "| `FILEMAP.md` | workspace census + full source index | a fresh sweep of every file |\n"
         "| `filemap.tsv` | every in-scope file, one row, greppable | same sweep |\n"
         "| `CVARS_COOP.md` | all `coop_*` cvars: engine default, cfg seed, script sites, ui | `.scr` + `.cfg` + `.urc` + `Cvar_Get` |\n"
         "| `CVARS_ENGINE.md` | every cvar the engine registers, with default and flags | `Cvar_Get` under `openmohaa-hzm/code/` |\n"
         "| `SUBSYSTEMS.md` | `coop_mod/` scripts, boot order, coop-integrated maps | `coop_mod/*.scr`, `maps/*.scr` |\n"
         "| `FIX_LEDGER.md` | every buglog entry, chronological | `.wolf/buglog.json` |\n"
         "| `FIX_INDEX.md` | **file -> ordered bug ids**, and tag index | `.wolf/buglog.json` |\n"
         "| `CHRONOLOGY.md` | per-repo history, HEAD, and uncommitted exposure | `git` in all three repos |\n"
         "| `manifest.json` | sha256 of each generated file + input fingerprint | this generator |\n",
         "\n## How to run it\n\n"
         "```powershell\n"
         "python docs\\tools\\docgen.py build      # regenerate (skips if inputs unchanged)\n"
         "python docs\\tools\\docgen.py build --force\n"
         "python docs\\tools\\docgen.py check      # exit 1 if these files are stale\n"
         "python docs\\tools\\docgen.py status     # fingerprint + staleness, no writes\n"
         "```\n\n"
         "`.wolf/hooks/stop.js` runs `build` at the end of every session. It is a no-op when "
         "nothing changed, so the cost is a fingerprint walk, not a rebuild.\n"]

    L.append("\n## Authored-doc budget\n")
    L.append("The authored files carry judgement, so they cannot be generated - but they can still "
             "rot by accumulation. `.wolf/cerebrum.md` reached 525 KB because its filling rule had "
             "no counterweight, and at that size the rule that said to read it was no longer "
             "physically satisfiable. Over budget means **merge and prune**, not append.\n\n")
    L.append("| authored file | size | ceiling | |\n|---|---:|---:|---|\n")
    for name, kb, ceiling, over in authored_budget():
        state = "**OVER - prune**" if over else "ok"
        L.append(f"| `docs/{name}` | {kb} KB | {ceiling} KB | {state} |\n")

    L.append(f"\nInput fingerprint of this generation: `{fp}`\n")
    return "".join(L)


# --------------------------------------------------------------------------
# Build / check / status
# --------------------------------------------------------------------------

def build_outputs() -> tuple[dict[str, str], str, dict]:
    t0 = time.time()
    files = sweep()
    t_sweep = time.time() - t0

    t = time.time()
    fp = fingerprint(files)
    t_fp = time.time() - t

    t = time.time()
    eng_regs, eng_dyn, eng_scanned = scan_engine_cvars(files)
    script_use, cfg_seed, ui_ref, dyn_prefix = scan_mod_cvars(files)
    t_scan = time.time() - t

    out: dict[str, str] = {}
    t = time.time()
    out["CVARS_ENGINE.md"] = gen_cvars_engine(eng_regs, eng_dyn, eng_scanned)
    out["CVARS_COOP.md"] = gen_cvars_coop(script_use, cfg_seed, ui_ref, dyn_prefix, eng_regs)
    fmap, ftsv = gen_filemap(files)
    out["FILEMAP.md"] = fmap
    out["filemap.tsv"] = ftsv
    out["SUBSYSTEMS.md"] = gen_subsystems(files)
    bugs = load_buglog()
    out["FIX_LEDGER.md"] = gen_fix_ledger(bugs)
    out["FIX_INDEX.md"] = gen_fix_index(bugs)
    out["CHRONOLOGY.md"] = gen_chronology()
    out["README.md"] = gen_readme(sorted(out), fp)
    t_render = time.time() - t

    manifest = {
        "_README": "DO NOT EDIT - generated by docs/tools/docgen.py",
        "tool_version": TOOL_VERSION,
        "inputs_fingerprint": fp,
        "counts": {
            "workspace_files": len(files),
            "engine_cvar_registrations": len(eng_regs),
            "engine_cvar_dynamic_names": eng_dyn,
            "buglog_entries": len(bugs),
        },
        "files": {k: hashlib.sha256(v.encode("utf-8")).hexdigest()
                  for k, v in sorted(out.items())},
    }
    out["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"

    timings = {
        "sweep_s": round(t_sweep, 3),
        "fingerprint_s": round(t_fp, 3),
        "scan_s": round(t_scan, 3),
        "render_s": round(t_render, 3),
        "total_s": round(time.time() - t0, 3),
    }
    return out, fp, timings


def write_outputs(out: dict[str, str]) -> list[str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    changed = []
    for name, content in sorted(out.items()):
        path = os.path.join(OUT_DIR, name)
        data = content.encode("utf-8")
        try:
            with open(path, "rb") as fh:
                if fh.read() == data:
                    continue        # write-if-different keeps mtimes stable
        except OSError:
            pass
        with open(path, "wb") as fh:
            fh.write(data)
        changed.append(name)
    return changed


def read_state() -> dict:
    try:
        with open(STATE_PATH, "rb") as fh:
            return json.loads(fh.read().decode("utf-8", errors="replace"))
    except Exception:
        return {}


def write_state(fp: str, timings: dict, changed: list[str]) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({
                "_README": "docgen cache. Wall-clock state, deliberately NOT part of the "
                           "generated set: a timestamp inside a generated doc would make "
                           "`check` fail every run and the guarantee worthless. Safe to "
                           "delete - the next build just does a full rebuild.",
                "inputs_fingerprint": fp,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timings": timings,
                "files_rewritten": changed,
            }, fh, indent=2, sort_keys=True)
            fh.write("\n")
    except OSError:
        pass


def cheap_fingerprint() -> str:
    return fingerprint(sweep())


def outputs_match_manifest() -> bool:
    """Do the files on disk still hash to what the last generation produced?

    The input fingerprint alone is not enough: a human (or an agent ignoring the
    DO-NOT-EDIT banner) can edit a generated file without touching any input, and
    the fast path would then declare everything fine forever. Ten sha256s over
    ~1.7 MB costs a few milliseconds - cheap enough to always verify.
    """
    try:
        with open(os.path.join(OUT_DIR, "manifest.json"), "rb") as fh:
            manifest = json.loads(fh.read().decode("utf-8"))
        recorded = manifest.get("files") or {}
        if not recorded:
            return False
        for name, want in recorded.items():
            with open(os.path.join(OUT_DIR, name), "rb") as fh:
                if hashlib.sha256(fh.read()).hexdigest() != want:
                    return False
        return True
    except Exception:
        return False


def cmd_build(force: bool) -> int:
    if not force:
        state = read_state()
        prior = state.get("inputs_fingerprint")
        if prior:
            fp_now = cheap_fingerprint()
            if fp_now == prior and outputs_match_manifest():
                print(f"docgen: up-to-date ({fp_now[:12]}) - nothing to do")
                return 0
    out, fp, timings = build_outputs()
    changed = write_outputs(out)
    write_state(fp, timings, changed)
    print(f"docgen: rebuilt {len(out)} files ({len(changed)} changed on disk) "
          f"in {timings['total_s']}s -> {rel(OUT_DIR)}/")
    if changed:
        print("        " + ", ".join(changed))
    warn_budget()
    return 0


def cmd_check() -> int:
    out, fp, timings = build_outputs()
    stale, missing = [], []
    for name, content in sorted(out.items()):
        path = os.path.join(OUT_DIR, name)
        try:
            with open(path, "rb") as fh:
                on_disk = fh.read()
        except OSError:
            missing.append(name)
            continue
        if on_disk != content.encode("utf-8"):
            stale.append(name)
    if not stale and not missing:
        print(f"docgen check: OK - docs/generated matches a fresh generation "
              f"({fp[:12]}, {timings['total_s']}s)")
        warn_budget()
        return 0
    print("docgen check: FAILED - docs/generated is stale", file=sys.stderr)
    for n in missing:
        print(f"  MISSING  {n}", file=sys.stderr)
    for n in stale:
        print(f"  STALE    {n}", file=sys.stderr)
    print("\nFix: python docs/tools/docgen.py build", file=sys.stderr)
    return 1


def cmd_status() -> int:
    state = read_state()
    fp_now = cheap_fingerprint()
    prior = state.get("inputs_fingerprint")
    print(f"docgen {TOOL_VERSION}")
    print(f"  out dir      : {rel(OUT_DIR)}")
    print(f"  fingerprint  : {fp_now}")
    print(f"  last recorded: {prior or '(never generated)'}")
    print(f"  generated at : {state.get('generated_at', '-')}")
    print(f"  last timings : {state.get('timings', {})}")
    print(f"  state        : {'UP TO DATE' if prior == fp_now else 'STALE - run build'}")
    return 0 if prior == fp_now else 1


def main(argv: list[str]) -> int:
    mode = "build"
    args = [a for a in argv[1:] if not a.startswith("-")]
    flags = {a for a in argv[1:] if a.startswith("-")}
    if args:
        mode = args[0].lower()
    if mode in ("build", "gen", "generate"):
        return cmd_build(force="--force" in flags or "-f" in flags)
    if mode == "check":
        return cmd_check()
    if mode == "status":
        return cmd_status()
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(130)
