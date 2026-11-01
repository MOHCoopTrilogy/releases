#!/usr/bin/env python3
"""check_deck.py - Steam Deck feasibility lint for every HZM release (read-only).

Plan and reasoning: docs/proposals/steamdeck_2026-11-01/README.md.

It is a RATCHET. Each check turns what it finds into stable keys (file + token, never a line number)
and fails only on keys that are not in docs/tools/check_deck_baseline.json. The debt that exists
today is recorded once and tolerated; nothing new gets in. Paying debt off shrinks the baseline:
re-run with --update-baseline after a cleanup and commit the smaller file.

Checks
  case     asset references whose case differs from the real file (Linux loose files and any
           future case-sensitive path). Engine tolerates it today (files.cpp case-folds), so ratchet.
  win32    Windows-only API calls / includes in engine code that are NOT inside an _WIN32 guard.
           An unguarded one is a Linux compile break or a Windows-only behaviour.
  shiptext shipped text (loose cfgs + text inside the mod pk3s) naming drive letters, powershell,
           .vbs/.bat/.exe launchers, osk.exe: things a Deck cannot run.
  glsl     gl2 shaders: own #version lines (the engine injects one), NV-only extensions, doubles.
  paks     release size budget from manifests/latest.json: total and per-file growth.
  preset   the Deck preset cfg (when it exists) only sets cvars the engine or mod registers.

Usage
  python -I docs/tools/check_deck.py                    # all checks, exit 1 on new debt
  python -I docs/tools/check_deck.py --only case,win32
  python -I docs/tools/check_deck.py --update-baseline  # accept the current state
  python -I docs/tools/check_deck.py --engine H:/hzm_work/eng-hotfix13661
"""
import argparse, collections, json, os, re, sys, zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
BASELINE = os.path.join(os.path.dirname(__file__), "check_deck_baseline.json")
MANIFEST = os.path.join(REPO, "manifests", "latest.json")
ENGINE_CANDIDATES = ["H:/hzm_work/eng-hotfix13661", os.path.join(REPO, "openmohaa-hzm")]
DECK_PRESET = os.path.join(MOD, "coop_mod", "cfg", "deck_preset.cfg")   # does not exist yet (stage 2)

# Budgets. Raise them deliberately, in a commit that says why.
PAK_TOTAL_BUDGET_GB = 9.0          # v1.10.49 ships 8.68 GB, all mandatory
PAK_GROWTH_WARN_MB = 200           # one file growing more than this between releases needs a reason
NEW_FILE_WARN_MB = 300             # one new file bigger than this needs a reason (and should be optional)


# ----------------------------------------------------------------------------------------------- case
TEXT_EXT = {".scr", ".tik", ".shader", ".urc", ".cfg", ".txt", ".mus"}
SKIP_DIRS = {"_backups", "_research", "_notes", "__MACOSX", "docs", "_callvote", "_terrain_pack"}
ASSET_EXT = ("tik|wav|mp3|tga|jpg|jpeg|dds|png|bsp|scr|skd|skc|shader|urc|cfg|mus|txt|ftx|spr|st|"
             "ritualfont|hzmlm|pth|hzlc")
ROOTS = ("models|sound|textures|maps|gfx|ui|global|anim|scripts|music|fonts|env|coop_mod|sky|"
         "ubersound|ubermode|cmpatch|htr|gags|navlinks|alienx|hzm_preload|video|fx|sprites")
REF_RE = re.compile(r"(?<![A-Za-z0-9_])((?:%s)[\\/][A-Za-z0-9_\-./\\ ]*?\.(?:%s))(?![A-Za-z0-9_])"
                    % (ROOTS, ASSET_EXT), re.I)
SHADER_IMG_RE = re.compile(r"^\s*(?:map|clampmap|animmap\s+[\d.]+|qer_editorimage|nextbundle\s+map|"
                           r"skyparms)\s+(.+)$", re.I | re.M)
IMG_EXTS = (".tga", ".jpg", ".jpeg", ".dds", ".png")


def _norm(p):
    p = p.replace("\\", "/").strip().strip('"').lstrip("/")
    return re.sub(r"/+", "/", p)


def _stem(p):
    b, e = os.path.splitext(p)
    return b if e.lower() in IMG_EXTS else p


def mod_texts(mod, want_index=True):
    """Yield (origin, path, bytes) for every shipped text file; also build the shipped-file index."""
    exact, texts, inpak_dups = set(), [], []
    for pk in sorted(f for f in os.listdir(mod) if f.lower().endswith(".pk3")):
        try:
            z = zipfile.ZipFile(os.path.join(mod, pk))
        except Exception as ex:
            print("  WARN cannot open %s: %s" % (pk, ex))
            continue
        seen = collections.defaultdict(set)
        for info in z.infolist():
            if info.is_dir():
                continue
            p = _norm(info.filename)
            exact.add(p)
            seen[p.lower()].add(p)
            if os.path.splitext(p)[1].lower() in TEXT_EXT and info.file_size < 4_000_000:
                texts.append((pk, p, z.read(info)))
        inpak_dups += [(pk, sorted(v)) for v in seen.values() if len(v) > 1]
    for root, dirs, files in os.walk(mod):
        rel = os.path.relpath(root, mod).replace("\\", "/")
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if f.lower().endswith(".pk3"):
                continue
            p = _norm(f if rel == "." else rel + "/" + f)
            exact.add(p)
            is_text = os.path.splitext(f)[1].lower() in TEXT_EXT
            if (is_text and rel != ".") or f.lower() in ("autoexec.cfg", "coop_defaults.cfg"):
                fp = os.path.join(root, f)
                try:
                    if os.path.getsize(fp) < 4_000_000:
                        texts.append(("<tree>", p, open(fp, "rb").read()))
                except OSError:
                    pass
    return exact, texts, inpak_dups


def check_case(ctx):
    exact, texts, inpak_dups = ctx["mod"]
    low = collections.defaultdict(set)
    for p in exact:
        low[p.lower()].add(p)
    exstem = {_stem(p) for p in exact}
    lowstem = collections.defaultdict(set)
    for s in exstem:
        lowstem[s.lower()].add(s)
    found = {}
    for origin, path, data in texts:
        txt = data.decode("latin-1")
        cands = [m.group(1) for m in REF_RE.finditer(txt)]
        if path.lower().endswith(".shader"):
            for m in SHADER_IMG_RE.finditer(txt):
                cands += [t for t in m.group(1).split() if "/" in t and not t.startswith("$")]
        for c in cands:
            r = _norm(c)
            if not r or " " in r:
                continue
            is_img = os.path.splitext(r)[1].lower() in IMG_EXTS or "." not in os.path.basename(r)
            if r in exact or (is_img and _stem(r) in exstem):
                continue
            hits = low.get(r.lower()) or (lowstem.get(_stem(r).lower()) if is_img else None)
            if hits:
                found.setdefault("ref %s -> %s" % (r, sorted(hits)[0]), "%s:%s" % (origin, path))
    for pk, v in inpak_dups:   # two entries in ONE pak differing only by case: which one loads is luck
        found["inpak-dup %s %s" % (pk, " | ".join(v))] = pk
    return found


# ---------------------------------------------------------------------------------------------- win32
WIN_TOKENS = [r"#\s*include\s*<windows\.h", r"#\s*include\s*[<\"](?:shellapi|shlobj|winreg|dbghelp|"
              r"winhttp|wininet|dxgi|psapi|tlhelp32|commdlg|mmsystem|winsock2?)\.h",
              r"\bMessageBox[AW]?\s*\(", r"\bCreateProcess[AW]?\s*\(", r"\bShellExecute(?:Ex)?[AW]?\s*\(",
              r"\bWinExec\s*\(", r"\bReg(?:Open|Create|Set|Query|Get)\w*\s*\(", r"\bGetModuleFileName[AW]?\s*\(",
              r"\bGetModuleHandle[AW]?\s*\(", r"\bLoadLibrary(?:Ex)?[AW]?\s*\(", r"\bGetProcAddress\s*\(",
              r"\bWaitForSingleObject\s*\(", r"\bSleep\s*\(", r"\bOutputDebugString[AW]?\s*\(",
              r"\b_mkdir\s*\(", r"\b_access\s*\(", r"\b_popen\s*\(", r"\b__try\b", r"\b__except\b",
              r"\b__declspec\s*\(", r"\b__forceinline\b", r"\b_alloca\s*\(", r"\bsprintf_s\s*\(", r"\bstrcpy_s\s*\(",
              r"\bfopen_s\s*\(", r"\b_stricmp\s*\(", r"\b_strnicmp\s*\(", r"\b_snprintf\s*\(",
              r"(?i:\"[^\"]*\bpowershell)", r"(?i:\"[^\"]*\bosk\.exe)", r"(?i:\"[^\"]*\.vbs\")",
              r"\"[A-Za-z]:\\\\", r"(?i:\"[^\"\s]*\.dll\")"]
WIN_RE = re.compile("|".join("(?:%s)" % t for t in WIN_TOKENS))
WIN_MACROS = re.compile(r"\b(?:_WIN32|_WIN64|WIN32|_MSC_VER|__WIN32__|_WINDOWS)\b")
SRC_EXT = (".c", ".cpp", ".cc", ".h", ".hpp")
# Files that are Windows-only by construction (the build never compiles them on Linux).
WIN_FILE_RE = re.compile(r"(?i)(?:^|[/_])(?:win32|win|windows|wgl|dxgi|msvc)[_./]|sys_win|win_|_win\.")
SKIP_ENGINE_DIRS = {"thirdparty", "libs", "third_party", "external", "SDL2", "AL", "curl", "zlib", "jpeg-8c",
                    "libogg", "libvorbis", "opus", "libmad", ".cmake", "build", ".git", "tools",
                    "gamespy"}   # vendored GameSpy SDK: Windows sample apps; upstream's Linux build compiles what it needs
VENDORED_FILES = {"code/qcommon/json.hpp"}


def _cond_kind(line):
    """+1 = Windows-only block, -1 = non-Windows block, 0 = unrelated."""
    s = line.strip()[1:].strip()
    if s.startswith("ifdef"):
        return 1 if WIN_MACROS.search(s) else 0
    if s.startswith("ifndef"):
        return -1 if WIN_MACROS.search(s) else 0
    if s.startswith("if") or s.startswith("elif"):
        if not WIN_MACROS.search(s):
            return 0
        if re.search(r"!\s*defined\s*\(?\s*_?WIN", s) or "&&" in s and "!" in s:
            return -1 if "||" not in s else 0
        return 1 if "&&" not in s or re.search(r"defined\s*\(?\s*_?WIN", s) else 0
    return 0


def check_win32(ctx):
    eng = ctx["engine"]
    found = {}
    if not eng:
        print("  SKIP no engine tree found (pass --engine)")
        return None
    code = os.path.join(eng, "code")
    for root, dirs, files in os.walk(code):
        dirs[:] = [d for d in dirs if d not in SKIP_ENGINE_DIRS and not d.startswith(".")]
        for f in files:
            if not f.endswith(SRC_EXT):
                continue
            rel = os.path.relpath(os.path.join(root, f), eng).replace("\\", "/")
            if WIN_FILE_RE.search(rel) or rel in VENDORED_FILES:
                continue
            try:
                lines = open(os.path.join(root, f), encoding="latin-1").read().splitlines()
            except OSError:
                continue
            stack = []   # kind per open #if
            in_block_comment = False
            for ln in lines:
                st = ln.lstrip()
                if st.startswith("#"):
                    d = st[1:].strip()
                    if d.startswith("if"):
                        stack.append(_cond_kind(st))
                    elif d.startswith("elif"):
                        if stack:
                            stack[-1] = _cond_kind(st)
                    elif d.startswith("else"):
                        if stack:
                            stack[-1] = -stack[-1]
                    elif d.startswith("endif"):
                        if stack:
                            stack.pop()
                if in_block_comment:
                    if "*/" in ln:
                        in_block_comment = False
                    continue
                code_part = ln.split("//", 1)[0]
                if "/*" in code_part and "*/" not in code_part:
                    in_block_comment = True
                    code_part = code_part.split("/*", 1)[0]
                if 1 in stack:
                    continue
                m = WIN_RE.search(code_part)
                if m:
                    tok = re.sub(r"\s+", "", m.group(0))[:40]
                    found.setdefault("%s %s" % (rel, tok), rel)
    return found


# ------------------------------------------------------------------------------------------- shiptext
SHIP_RE = re.compile(r"(?i)(?<![A-Za-z])[A-HJ-Z]:[\\/][^\s\"']*|\bpowershell(?:\.exe)?\b|\bcmd\.exe\b|"
                     r"\bosk\.exe\b|[\w./\\-]+\.(?:vbs|bat|ps1)\b|\bstart\s+\"\"|%APPDATA%|%USERPROFILE%")


def check_shiptext(ctx):
    _, texts, _ = ctx["mod"]
    found = {}
    for origin, path, data in texts:
        txt = data.decode("latin-1")
        for ln in txt.splitlines():
            s = ln.strip()
            if s.startswith("//") or s.startswith("#"):
                continue     # comments do not run
            code_part = s.split("//", 1)[0]
            for m in SHIP_RE.finditer(code_part):
                found.setdefault("%s %s" % (path, m.group(0)[:60]), origin)
    return found


# ----------------------------------------------------------------------------------------------- glsl
def check_glsl(ctx):
    eng = ctx["engine"]
    if not eng:
        print("  SKIP no engine tree found")
        return None
    gdir = os.path.join(eng, "code", "renderergl2", "glsl")
    if not os.path.isdir(gdir):
        print("  SKIP no %s" % gdir)
        return None
    found = {}
    rules = [(re.compile(r"^\s*#\s*version\b", re.M), "own-#version (engine injects one; a second one is a Mesa error)"),
             (re.compile(r"#\s*extension\s+GL_NVX?_\w+"), "NV-only extension"),
             (re.compile(r"\b(?:double|dvec[234]|dmat[234])\b"), "double precision (GL 4.0+)")]
    for f in sorted(os.listdir(gdir)):
        if not f.endswith(".glsl"):
            continue
        txt = open(os.path.join(gdir, f), encoding="latin-1").read()
        txt_nc = re.sub(r"//[^\n]*|/\*.*?\*/", "", txt, flags=re.S)
        for rx, why in rules:
            if why and rx.search(txt_nc):
                found["%s %s" % (f, why)] = f
    return found


# ----------------------------------------------------------------------------------------------- paks
def _load_manifest(path):
    return json.load(open(path, encoding="utf-8-sig"))


def check_paks(ctx):
    if not os.path.isfile(MANIFEST):
        print("  SKIP no manifests/latest.json")
        return None
    man = _load_manifest(MANIFEST)
    files = man["files"]
    total = sum(x.get("size", 0) for x in files)
    found = {}
    print("  manifest %s: %d files, %.2f GB (budget %.1f GB)" % (man.get("version"), len(files), total / 1e9,
                                                                PAK_TOTAL_BUDGET_GB))
    if total / 1e9 > PAK_TOTAL_BUDGET_GB:
        found["total over budget %.1f GB" % PAK_TOTAL_BUDGET_GB] = "%.2f GB" % (total / 1e9)
    # Growth vs the previous manifest in the repo (by version sort).
    prev = None
    vers = []
    for f in os.listdir(os.path.dirname(MANIFEST)):
        m = re.match(r"manifest-(\d+)\.(\d+)\.(\d+)\.json$", f)
        if m:
            vers.append((tuple(int(x) for x in m.groups()), f))
    cur_v = tuple(int(x) for x in re.findall(r"\d+", str(man.get("version", "0.0.0")))[:3])
    older = [f for v, f in sorted(vers) if v < cur_v]
    if older:
        prev = _load_manifest(os.path.join(os.path.dirname(MANIFEST), older[-1]))
    if prev:
        psize = {x["path"]: x.get("size", 0) for x in prev["files"]}
        for x in files:
            p, s = x["path"], x.get("size", 0)
            if p not in psize and s > NEW_FILE_WARN_MB * 1e6:
                found["new big file %s" % p] = "%d MB" % (s / 1e6)
            elif p in psize and s - psize[p] > PAK_GROWTH_WARN_MB * 1e6:
                found["grew %s" % p] = "+%d MB" % ((s - psize[p]) / 1e6)
        print("  compared with %s" % older[-1])
    linux = [x["path"] for x in files if x["path"].endswith(".so") or "linux" in x["path"].lower()]
    print("  Linux binaries in manifest: %s" % (", ".join(linux) if linux else "none (stage 1 not shipped)"))
    if ctx["require_linux"] and not linux:
        found["no Linux binaries in manifest"] = "--require-linux"
    return found


# --------------------------------------------------------------------------------------------- preset
def check_preset(ctx):
    if not os.path.isfile(DECK_PRESET):
        print("  SKIP %s does not exist yet" % os.path.relpath(DECK_PRESET, REPO))
        return None
    known = set()
    for g in ("CVARS_ENGINE.md", "CVARS_COOP.md"):
        p = os.path.join(REPO, "docs", "generated", g)
        if os.path.isfile(p):
            known |= set(re.findall(r"^\| `([^`]+)` \|", open(p, encoding="utf-8").read(), re.M))
    found = {}
    for ln in open(DECK_PRESET, encoding="latin-1"):
        m = re.match(r"\s*(?:seta|set|setu|sets)\s+(\S+)", ln)
        if m and m.group(1) not in known:
            found["unknown cvar %s" % m.group(1)] = "deck_preset.cfg"
    return found


CHECKS = collections.OrderedDict([("case", check_case), ("win32", check_win32), ("shiptext", check_shiptext),
                                  ("glsl", check_glsl), ("paks", check_paks), ("preset", check_preset)])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", help="comma list of checks: " + ",".join(CHECKS))
    ap.add_argument("--engine", help="engine tree (default: release tree on H:, else openmohaa-hzm)")
    ap.add_argument("--update-baseline", action="store_true", help="accept the current state as the baseline")
    ap.add_argument("--require-linux", action="store_true", help="fail when the manifest has no Linux binaries")
    ap.add_argument("--max", type=int, default=25, help="new findings printed per check")
    a = ap.parse_args()

    want = a.only.split(",") if a.only else list(CHECKS)
    eng = a.engine or next((e for e in ENGINE_CANDIDATES if os.path.isdir(os.path.join(e, "code"))), None)
    ctx = {"engine": eng, "require_linux": a.require_linux}
    if any(c in want for c in ("case", "shiptext")):
        ctx["mod"] = mod_texts(MOD)
    print("check_deck: engine=%s" % eng)

    base = json.load(open(BASELINE, encoding="utf-8")) if os.path.isfile(BASELINE) else {}
    new_base = dict(base)
    bad = 0
    for name in want:
        print("[%s]" % name)
        found = CHECKS[name](ctx)
        if found is None:
            continue
        known = set(base.get(name, []))
        new = sorted(k for k in found if k not in known)
        gone = sorted(k for k in known if k not in found)
        print("  %d findings, %d in baseline, %d NEW, %d paid off" % (len(found), len(known & set(found)),
                                                                    len(new), len(gone)))
        for k in new[:a.max]:
            print("  NEW  %s   (%s)" % (k, found[k]))
        if len(new) > a.max:
            print("  ... %d more" % (len(new) - a.max))
        # Paks findings are per-release (growth, budget): never baseline them, they must be answered each time.
        if name != "paks":
            new_base[name] = sorted(found)
        if new:
            bad += 1
    if a.update_baseline:
        json.dump(new_base, open(BASELINE, "w", encoding="utf-8", newline="\n"), indent=1, sort_keys=True)
        print("baseline written: %s" % os.path.relpath(BASELINE, REPO))
        return 0
    print("RESULT: %s" % ("FAIL - %d check(s) have new Deck debt" % bad if bad else "ok"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
