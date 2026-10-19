#!/usr/bin/env python
"""gfx_live_audit.py - for every setting on the graphics menus: WHEN does a change actually take effect?

READ-ONLY. Writes nothing; prints to stdout. Derived entirely from the code, so the table cannot drift:

  menu rows  docs/tools/gen_menu_graphics.py tables (the 4 Post-FX sheets + Advanced Graphics, which that generator
             owns) + a parse of the two hand-written menus (ui/video options.urc, ui/advancedoptions.urc).
  flags      every Cvar_Get("<name>", <default>, <flags>) per module. Cvar_Get OR-combines flags on an existing cvar
             (qcommon/cvar.c Cvar_Get), so a cvar's live flags are the UNION over every module loaded in that process
             (renderer + renderercommon + sdl + cgame + client + uilib).
  reads      every dereference of the pointer(s) a module binds to the cvar (->integer/value/string/modified/
             modificationCount/latchedString), plus Cvar_Variable*("name") / Cvar_Find("name") by literal name.
             A cvar is almost never read through its own name (see audit_menu_cvars.py for why).
  phase      crude call-graph reachability (C/C++ function bodies, calls by identifier) from declared ROOTS:
               FRAME   RE_BeginFrame / RE_RenderScene / the backend / 2D draws; CG_DrawActiveFrame; CL_Frame
               INIT    R_Init (gl2: every registration = every map load + vid_restart; gl1: DLL load only);
                       CG_Init (every map load + vid_restart)
               REG     RE_BeginRegistration / RE_Shutdown; CG_ServerRestarted / CG_GameStateReceived
               WORLD   RE_LoadWorldMap (the BSP load)
               ASSET   image / shader / model / font creation (R_CreateImage, R_LoadImage, R_FindShader...)
               WINDOW  GLimp_Init / GLimp_SetMode (window + context; a map load keeps the window)
               CMD:x   a console command handler (ri.Cmd_AddCommand("x", fn))
               TABLE   reached only through a function pointer (a file-scope table, or an address taken outside
                       frame code): time unknown, listed but not counted
             FRAME traversal stops at every other phase's roots (a lazy image load under a frame root is ASSET work,
             not a per-frame read); INIT stops at ASSET/WINDOW/WORLD roots. A pointer assigned during a frame
             (tess.currentStageIteratorFunc = RB_StageIteratorGeneric) is followed from frame code only.
             One phase per site: FRAME if a frame root reaches it (gl2 bakes cubemaps through R_RenderView at world
             load, so the draw path is also WORLD-reachable - that does not make it a load-time read), else the
             most restrictive. Not counted: DIAG (a print in GfxInfo_f and friends) and CLAMP (a read inside the
             non-frame function that registers the cvar - a range check, not a use).
  derived    a read on a line `tr.X = ...cvar...` caches the value; the phases where tr.X is consumed are followed
             one level. A cached copy consumed at world load makes the setting MAPLOAD (r_overBrightBits ->
             tr.overbrightBits -> the lightmap colour shift in tr_bsp.c).

CLASS (per renderer process; the mod ships gl2):
  LIVE     read per frame (or re-applied per frame on ->modified) and not CVAR_LATCH - the next frame shows it
  RESTART  needs a renderer re-init: R_Init / GLSL / FBO / image / shader creation, or CVAR_LATCH consumed there.
           Applied by vid_restart, and under gl2 ALSO by any map change (RE_BeginRegistration re-runs R_Init).
  MAPLOAD  read while loading the world (RE_LoadWorldMap). Applied by a map change, or vid_restart (which restarts
           cgame and reloads the world) - never by a live hook that leaves the world in place.
  WINDOW   read only at window/context creation. vid_restart ONLY - a map change keeps the window
           (InitOpenGL skips GLimp_Init once glConfig.vidWidth != 0).
  CMD      applied by a console command (e.g. ter_restart)
  DEAD     no reader in this renderer's process
  (+mix)   suffix: ALSO read per frame - the per-frame read sees the new value while the init-time resource does not
           (non-latched), or sees the OLD value until the latch is consumed (latched).

MENU "*" VERDICT: the Post-FX sheets' APPLY is a plain close (bug-1181), so a row applies at APPLY only if LIVE.
Video Options / Advanced Options / Advanced Graphics APPLY run ui_checkrestart, which issues vid_restart only when a
widget IN THAT MENU is linkcvar'd to a CVAR_LATCH cvar holding a latchedString (uilib/uimenu.cpp Menu::CheckRestart).
So a non-LIVE, non-latched row there waits silently for the next map; a latched row whose reads are all per-frame
forces a needless vid_restart.

Usage:
  python docs/tools/gfx_live_audit.py                 # the audit table (markdown)
  python docs/tools/gfx_live_audit.py --sites         # + every read site, file:line function [phases]
  python docs/tools/gfx_live_audit.py --json          # machine-readable
  python docs/tools/gfx_live_audit.py --check FILE    # exit 1 if FILE's embedded table (between the
                                                      # <!-- gfx_live_audit:begin/end --> markers) is stale
  python docs/tools/gfx_live_audit.py --cvar NAME     # one cvar, every registration and read site
  python docs/tools/gfx_live_audit.py --why FUNC [gl2|gl1|cgame|client]   # a call chain from each phase's roots
  --extra a,b,c  also classify cvars that are on no menu (recorded in the --check marker, so the check reproduces it)
  --engine DIR   audit another engine tree (e.g. openmohaa-hzm-gfx/code); default openmohaa-hzm/code

Honest limits: a cvar pointer copied into another variable or struct member is not followed; derived state is
followed one level only (r_intensity -> local -> s_intensitytable is missed); a value that feeds a GPU object
without a tr.X field (an FBO sized from tr.renderImage) is visible only through the read that sized it;
#if handling drops only `#if 0` and `__EMSCRIPTEN__` / non-Windows branches. Every row carries its sites -
spot-check the ones a decision rests on (--cvar, --why). Runs in ~10 s.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _find_root():
    for start in (HERE, os.path.abspath(os.getcwd())):
        d = start
        for _ in range(8):
            if os.path.isdir(os.path.join(d, "hzm-mohaa-coop-mod")) and os.path.isdir(os.path.join(d, "openmohaa-hzm")):
                return d
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd
    return os.path.dirname(os.path.dirname(HERE))


ROOT = _find_root()
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
ENG = os.path.join(ROOT, "openmohaa-hzm", "code")
if "--engine" in sys.argv:
    ENG = os.path.abspath(sys.argv[sys.argv.index("--engine") + 1])

HAND_MENUS = [("Video Options", "video options.urc"), ("Advanced Options", "advancedoptions.urc")]

# ---------------------------------------------------------------- roots (the only hand-declared input)
FRAME_ROOTS = {
    "renderer": ["RE_BeginFrame", "RE_EndFrame", "RE_RenderScene", "RE_ClearScene", "RB_ExecuteRenderCommands",
                 "RE_AddRefEntityToScene", "RE_AddRefEntityToScene2", "RE_AddPolyToScene", "RE_AddPolyToScene2",
                 "RE_AddLightToScene", "RE_AddLightToScene2", "RE_AddAdditiveLightToScene", "RE_AddRefSpriteToScene",
                 "RE_AddTerrainMarkToScene", "RE_StretchPic", "RE_StretchRaw", "RE_StretchRaw2", "Draw_StretchPic",
                 "Draw_StretchPic2", "Draw_TilePic", "Draw_TilePicOffset", "Draw_TrianglePic", "DrawBox", "AddBox",
                 "Set2DWindow", "RE_Scissor", "DrawLineLoop", "R_DrawString", "Draw_SetColor", "RE_SetColor",
                 "R_MarkFragments", "R_MarkFragmentsForInlineModel", "R_LightForPoint", "R_GetLightingForDecal",
                 "R_GetLightingForSmoke", "R_GatherLightSources", "RE_SwipeBegin", "RE_SwipeEnd", "RE_SetRenderTime",
                 "R_DebugLine", "RE_UploadCinematic", "RE_TakeVideoFrame", "R_LerpTag", "RE_ForceUpdatePose",
                 "R_SavePerformanceCounters"],
    "cgame": ["CG_DrawActiveFrame", "CG_Draw2D", "CG_CleanUpTempModels"],
    "client": ["CL_Frame", "SCR_UpdateScreen", "CL_CheckUserinfo"],
    "uilib": [],
}
INIT_ROOTS = {"renderer": ["R_Init"], "cgame": ["CG_Init"], "client": ["CL_Init", "CL_InitRef"], "uilib": []}
REG_ROOTS = {"renderer": ["RE_BeginRegistration", "RE_EndRegistration", "RE_Shutdown", "GetRefAPI"],
             "cgame": ["CG_Shutdown", "CG_ServerRestarted", "CG_GameStateReceived"], "client": [], "uilib": []}
WORLD_ROOTS = {"renderer": ["RE_LoadWorldMap"], "cgame": [], "client": [], "uilib": []}
ASSET_ROOTS = {"renderer": ["R_CreateImage", "R_CreateImage2", "R_FindImageFile", "R_FindImageFileOld", "R_FindShader",
                            "R_FindShaderEx", "R_FindShaderByName", "RE_RegisterShader", "RE_RegisterShaderNoMip",
                            "RE_RegisterShaderLightMap", "RE_RegisterShaderFromImage", "RE_RefreshShaderNoMip",
                            "RE_RegisterModel", "RE_RegisterSkin", "RE_RegisterFont", "R_LoadFont", "RE_SpawnEffectModel",
                            "RE_RegisterServerModel", "R_LoadImage", "R_LoadRawImage"],
               "cgame": [], "client": [], "uilib": []}
WINDOW_ROOTS = {"renderer": ["GLimp_Init", "GLimp_SetMode", "GLimp_StartDriverAndSetMode"],
                "cgame": [], "client": [], "uilib": []}

# reads that only PRINT a cvar (diagnostics, gfxinfo) say nothing about when it takes effect
DIAG_FUNCS = {"GfxInfo_f", "GfxMemInfo_f", "UI_LoadProbe_Report", "R_PrintLongString", "R_ImageList_f"}
# derived state: a read on a line "tr.X = ...cvar..." caches the value; where tr.X is consumed is followed one level
DERIVED_LHS = re.compile(r"^\s*((?:tr|backEnd|glRefConfig|glConfig)\s*\.\s*\w+)\s*=[^=]")

PHASE_ORDER = ["WINDOW", "WORLD", "ASSET", "INIT", "REG", "CMD", "FRAME", "TABLE", "UNREACHED"]  # restrictive first


def phase_rank(p):
    """Deterministic display order (sets of strings iterate in hash order, which changes per process)."""
    key = "CMD" if p.startswith("CMD:") else p
    return (PHASE_ORDER.index(key) if key in PHASE_ORDER else len(PHASE_ORDER), p)
READ_KINDS = ("integer", "value", "string", "modified", "modificationCount", "latchedString")
KEYWORDS = set("""if for while switch return sizeof defined else do case goto typeof __typeof__ static_assert
                  _Static_assert alignof offsetof va_arg catch new delete throw operator""".split())


# ---------------------------------------------------------------- source preparation
def rd(p):
    try:
        with io.open(p, "rb") as fh:
            return fh.read().decode("utf-8", "replace")
    except Exception:
        return ""


def strip_comments(src):
    """Blank comments (keep newlines and offsets); keep string literals. Returns (nocomment, masked) where masked
    also blanks string/char literal contents (so braces and parens inside strings cannot confuse the scanner)."""
    out, msk = [], []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i)); msk.append(" " * (j - i)); i = j
        elif c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blk = re.sub(r"[^\n]", " ", src[i:j])
            out.append(blk); msk.append(blk); i = j
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(src[i:j]); msk.append(c + " " * max(0, j - i - 2) + (c if j - i >= 2 else "")); i = j
        else:
            out.append(c); msk.append(c); i += 1
    return "".join(out), "".join(msk)


DEAD_IF = re.compile(r"^\s*#\s*(if\s+0\b|ifdef\s+__EMSCRIPTEN__|if\s+defined\s*\(?\s*__EMSCRIPTEN__|ifdef\s+__APPLE__|"
                     r"ifdef\s+__linux__|if\s+defined\s*\(?\s*__linux__|ifndef\s+_WIN32)")
ANY_IF = re.compile(r"^\s*#\s*if")
ELSE_ = re.compile(r"^\s*#\s*(else|elif)\b")
ENDIF = re.compile(r"^\s*#\s*endif\b")


def drop_dead_branches(text):
    """Blank the true branch of #if 0 / __EMSCRIPTEN__ / non-Windows conditionals (keep their #else)."""
    lines = text.split("\n")
    stack = []   # each: 'dead' (in a dead branch), 'live-after-dead', 'other'
    out = []
    for ln in lines:
        dead_now = any(s == "dead" for s in stack)
        if DEAD_IF.match(ln):
            stack.append("dead"); out.append(" " * len(ln)); continue
        if ANY_IF.match(ln):
            stack.append("other"); out.append(" " * len(ln) if dead_now else ln); continue
        if ELSE_.match(ln) and stack:
            if stack[-1] == "dead":
                stack[-1] = "live-after-dead"
            elif stack[-1] == "live-after-dead":
                stack[-1] = "dead"
            out.append(" " * len(ln)); continue
        if ENDIF.match(ln) and stack:
            stack.pop(); out.append(" " * len(ln)); continue
        out.append(" " * len(ln) if dead_now else ln)
    return "\n".join(out)


class SrcFile(object):
    def __init__(self, path, rel):
        self.path, self.rel = path, rel
        raw = rd(path)
        nc, mk = strip_comments(raw)
        self.nc = drop_dead_branches(nc)
        self.mk = drop_dead_branches(mk)
        self.line_starts = [0]
        for m in re.finditer("\n", self.mk):
            self.line_starts.append(m.end())
        self.funcs = self._functions()

    def line_of(self, off):
        lo, hi = 0, len(self.line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.line_starts[mid] <= off:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    def _functions(self):
        """[(name, body_start, body_end)] for every top-level brace block whose header looks like a function."""
        mk = self.mk
        funcs = []
        depth = 0
        transparent = []           # depths of extern "C" / namespace blocks
        boundary = 0
        i, n = 0, len(mk)
        opens = []
        while i < n:
            c = mk[i]
            if c == "#" and (i == 0 or mk[i - 1] == "\n" or mk[max(0, i - 200):i].split("\n")[-1].strip() == ""):
                j = i
                while True:
                    k = mk.find("\n", j)
                    if k < 0:
                        k = n
                        break
                    if mk[k - 1] == "\\":
                        j = k + 1
                        continue
                    break
                if depth - len(transparent) == 0:
                    boundary = k
                i = k
                continue
            if c == "{":
                eff = depth - len(transparent)
                if eff == 0:
                    header = mk[boundary:i]
                    hs = header.strip()
                    if re.search(r'\bextern\s*"\s*C\s*"\s*$', header) or re.search(r"\bnamespace\b[\w\s:]*$", hs):
                        depth += 1
                        transparent.append(depth)
                        boundary = i + 1
                        i += 1
                        continue
                    name = self._func_name(hs)
                    opens.append((name, i))
                depth += 1
            elif c == "}":
                if transparent and transparent[-1] == depth:
                    transparent.pop()
                    depth -= 1
                    boundary = i + 1
                    i += 1
                    continue
                depth -= 1
                if depth - len(transparent) == 0:
                    if opens:
                        name, st = opens.pop()
                        if name:
                            funcs.append((name, st, i))
                    boundary = i + 1
                if depth < 0:
                    depth = 0
            elif c == ";" and depth - len(transparent) == 0:
                boundary = i + 1
            i += 1
        return funcs

    @staticmethod
    def _func_name(hs):
        if not hs or "(" not in hs:
            return None
        if re.match(r"^(typedef|struct|enum|union|class)\b", hs):
            return None
        if hs.rstrip().endswith("="):
            return None       # an initialiser: static void (*table[])(void) = { ... }
        pre = hs[:hs.index("(")]
        if "=" in pre:
            return None
        m = re.search(r"([A-Za-z_~][\w:~]*)\s*$", pre)
        if not m:
            return None
        name = m.group(1)
        if name in KEYWORDS or name in ("void", "int", "char", "float", "double", "unsigned", "signed", "long",
                                        "short", "const", "static", "inline", "extern", "qboolean"):
            return None
        return name

    def func_at(self, off):
        best = None
        for name, st, en in self.funcs:
            if st <= off <= en:
                best = name
        return best


# ---------------------------------------------------------------- modules and processes
def src_files(dirs, exclude=()):
    out = []
    for d in dirs:
        base = os.path.join(ENG, d)
        if os.path.isfile(base):
            out.append(base)
            continue
        for b, _ds, fs_ in os.walk(base):
            if "thirdparty" in b or "SDL2" in b:
                continue
            for f in sorted(fs_):
                if f.endswith((".c", ".cpp")) and f not in exclude:
                    out.append(os.path.join(b, f))
    return out


MODULES = {
    # renderergl2/CMakeLists.txt removes tr_model.c from the glob
    "gl2": ("renderer", ["renderergl2", "renderercommon", "sdl/sdl_glimp.c", "sdl/sdl_gamma.c"], ("tr_model.c",)),
    "gl1": ("renderer", ["renderergl1", "renderercommon", "sdl/sdl_glimp.c", "sdl/sdl_gamma.c"], ()),
    "cgame": ("cgame", ["cgame"], ()),
    "client": ("client", ["client"], ()),
    "uilib": ("uilib", ["uilib"], ()),
}
PROCESS = {"gl2": ["gl2", "cgame", "client", "uilib"], "gl1": ["gl1", "cgame", "client", "uilib"]}


class Module(object):
    def __init__(self, key):
        self.key = key
        self.kind, dirs, excl = MODULES[key]
        self.files = [SrcFile(p, os.path.relpath(p, os.path.dirname(ENG)).replace("\\", "/"))
                      for p in src_files(dirs, excl)]
        self.defs = {}      # short name -> [(file, st, en)]
        for f in self.files:
            for name, st, en in f.funcs:
                short = name.split("::")[-1]
                self.defs.setdefault(short, []).append((f, st, en))
        self.calls = {}     # direct calls: name followed by '('
        self.addr = {}      # address-taken: a function name used as a value inside a body
        # (tess.currentStageIteratorFunc = RB_StageIteratorGeneric; CG_InitCGMessageAPI storing a parser). Such a
        # function runs LATER, at a time the reference does not tell us: followed only from FRAME code (a pointer
        # set during a frame is called during the frame); from anywhere else it is a TABLE root (unknown time).
        # Cmd_AddCommand("x", fn) is neither (fn becomes a CMD root).
        ident_re = re.compile(r"(?<!\w)(\.|->)?\s*([A-Za-z_]\w*)\s*(\()?")
        for short, bodies in self.defs.items():
            callees, refs = set(), set()
            for f, st, en in bodies:
                body = f.mk[st:en]
                body = re.sub(r"Cmd_AddCommand\s*\([^;]*;", " ", body)
                for m in ident_re.finditer(body):
                    nm = m.group(2)
                    if nm not in self.defs or nm in KEYWORDS or nm == short:
                        continue
                    if m.group(3):
                        callees.add(nm)
                    elif not m.group(1):
                        refs.add(nm)
            self.calls[short] = callees
            self.addr[short] = refs - callees
        # file-scope function-pointer tables (rb_surfaceTable, CLASS_DECLARATION response tables, image loaders)
        tabled = set()
        for f in self.files:
            spans = sorted((st, en) for _n, st, en in f.funcs if _n.split("::")[-1] not in ("CLASS_DECLARATION",))
            pos, outside = 0, []
            for st, en in spans:
                outside.append(f.mk[pos:st])
                pos = en + 1
            outside.append(f.mk[pos:])
            txt = " ".join(outside)
            for _n, st, en in f.funcs:
                if _n.split("::")[-1] == "CLASS_DECLARATION":
                    txt += " " + f.mk[st:en]
            for m in re.finditer(r"&?\s*(?:[A-Za-z_]\w*::)?([A-Za-z_]\w*)\s*(\()?", txt):
                if m.group(2) is None and m.group(1) in self.defs:
                    tabled.add(m.group(1))
        self.file_tabled = tabled
        self.defs.setdefault("<tables>", [])
        self.cmds = {}
        for f in self.files:
            for m in re.finditer(r'Cmd_AddCommand\s*\(\s*"([^"]+)"\s*,\s*&?\s*([A-Za-z_]\w*)', f.nc):
                self.cmds[m.group(2)] = m.group(1)
        self.phase = self._phases()

    def _bfs(self, roots, barriers, parent=None, follow_addr=False):
        seen = set()
        todo = [r for r in roots if r in self.defs]
        if parent is not None:
            for r in todo:
                parent.setdefault(r, None)
        while todo:
            fn = todo.pop()
            if fn in seen:
                continue
            seen.add(fn)
            nxt = set(self.calls.get(fn, ()))
            if follow_addr:
                nxt |= self.addr.get(fn, set())
            for c in sorted(nxt):
                if c not in seen and c not in barriers:
                    if parent is not None and c not in parent:
                        parent[c] = fn
                    todo.append(c)
        return seen

    def why(self, target):
        """For --why: one call chain from each phase's roots to target."""
        out = []
        for tag, roots, barriers, fa in self._phase_specs():
            parent = {}
            if target in self._bfs(roots, barriers, parent, fa):
                chain, cur = [], target
                while cur is not None and len(chain) < 40:
                    chain.append(cur)
                    cur = parent.get(cur)
                out.append("%-8s %s" % (tag, " <- ".join(chain)))
        return out

    def _phase_specs(self):
        k = self.kind
        roots = {"FRAME": FRAME_ROOTS[k], "INIT": INIT_ROOTS[k], "WORLD": WORLD_ROOTS[k], "ASSET": ASSET_ROOTS[k],
                 "WINDOW": WINDOW_ROOTS[k], "REG": REG_ROOTS[k]}
        allroots = set()
        for v in roots.values():
            allroots.update(v)
        cmdroots = set(self.cmds)
        frame_barriers = (allroots | cmdroots) - set(roots["FRAME"])
        if not hasattr(self, "_frame_set"):
            self._frame_set = self._bfs(roots["FRAME"], frame_barriers, follow_addr=True)
        later = set(self.file_tabled)
        for fn, refs in self.addr.items():
            if fn not in self._frame_set:
                later |= refs
        self.calls["<tables>"] = later
        specs = [
            ("FRAME", roots["FRAME"], frame_barriers, True),
            ("INIT", roots["INIT"], set(roots["ASSET"]) | set(roots["WINDOW"]) | set(roots["WORLD"]), False),
            ("WORLD", roots["WORLD"], set(roots["ASSET"]) | set(roots["INIT"]), False),
            ("ASSET", roots["ASSET"], set(roots["INIT"]) | set(roots["WINDOW"]), False),
            ("WINDOW", roots["WINDOW"], set(), False),
            ("REG", roots["REG"], allroots - set(roots["REG"]), False),
            ("TABLE", ["<tables>"], allroots | cmdroots, False),
        ]
        for fn, cmd in sorted(self.cmds.items()):
            specs.append(("CMD:" + cmd, [fn], allroots, False))
        return specs

    def _phases(self):
        phase = {}
        for tag, roots, barriers, fa in self._phase_specs():
            for fn in self._bfs(roots, barriers, follow_addr=fa):
                phase.setdefault(fn, set()).add(tag)
        return phase

    def phases_of(self, fn):
        if not fn:
            return {"FILE"}
        return self.phase.get(fn.split("::")[-1], {"UNREACHED"})


# ---------------------------------------------------------------- cvar bindings and reads
def split_args(s, start):
    """s[start] is just after '('. Return (args list, end index of the closing ')')."""
    depth, i, args, cur = 1, start, [], start
    while i < len(s):
        c = s[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                args.append(s[cur:i].strip())
                return args, i
        elif c == "," and depth == 1:
            args.append(s[cur:i].strip())
            cur = i + 1
        i += 1
    return args, i


FLAG_TOKENS = ("ARCHIVE", "LATCH", "CHEAT", "ROM", "TEMP", "INIT", "USERINFO", "TERRAIN_LATCH", "SOUND_LATCH",
               "SERVERINFO", "SYSTEMINFO", "SAVEGAME", "NORESTART")


def parse_flags(txt):
    flags = set()
    for m in re.finditer(r"CVAR_([A-Z_]+)", txt):
        if m.group(1) in FLAG_TOKENS:
            flags.add(m.group(1))
    return flags


class CvarIndex(object):
    def __init__(self, mod):
        self.mod = mod
        self.regs = {}      # lname -> [dict]
        self.binds = {}     # var -> set(lname) (global) ; (file.rel, func, var) -> set(lname) (local)
        self.local = {}
        self.fstatic = {}
        reg_re = re.compile(r"\b(Cvar_Get2?|Cvar_Find)\s*\(")
        for f in mod.files:
            for m in reg_re.finditer(f.nc):
                args, end = split_args(f.nc, m.end())
                if not args or not re.match(r'^"[^"]+"$', args[0]):
                    continue
                name = args[0][1:-1]
                lname = name.lower()
                fn = f.func_at(m.start())
                pre = f.nc[max(0, m.start() - 160):m.start()]
                am = re.search(r"([A-Za-z_]\w*)\s*=\s*(?:\(\s*cvar_t\s*\*\s*\)\s*)?(?:[A-Za-z_]\w*\s*(?:\.|->)\s*)?$", pre)
                var = am.group(1) if am else None
                if m.group(1) != "Cvar_Find":
                    flags = parse_flags(args[2]) if len(args) > 2 else set()
                    self.regs.setdefault(lname, []).append(dict(
                        name=name, file=f.rel, line=f.line_of(m.start()), func=fn, default=args[1] if len(args) > 1 else "",
                        flags=flags, phases=sorted(mod.phases_of(fn)), var=var))
                if var:
                    decl = r"\bcvar_t\b[^;{}()]*\*\s*" + re.escape(var) + r"\b"
                    if fn and re.search(decl, self._body(f, fn)):
                        self.local.setdefault((f.rel, fn.split("::")[-1], var), set()).add(lname)
                    elif re.search(r"\bstatic\b[^;{}()]*" + decl, self._outside(f)):
                        self.fstatic.setdefault((f.rel, var), set()).add(lname)
                    else:
                        self.binds.setdefault(var, set()).add(lname)
        # every pointer dereference, resolved innermost scope first: function-local, file-static, module-global
        self.reads = {}
        allvars = set(self.binds) | {k[1] for k in self.fstatic} | {k[2] for k in self.local}
        deref = None
        if allvars:
            alts = "|".join(sorted((re.escape(v) for v in allvars), key=len, reverse=True))
            deref = re.compile(r"\b(" + alts + r")\s*->\s*(" + "|".join(READ_KINDS) + r")\b")
        for f in mod.files:
            if deref is not None:
                for m in deref.finditer(f.mk):
                    var = m.group(1)
                    fn = f.func_at(m.start())
                    short = fn.split("::")[-1] if fn else None
                    names = self.local.get((f.rel, short, var)) or self.fstatic.get((f.rel, var))
                    if names is None:
                        if fn and re.search(r"\bcvar_t\b[^;{}()]*\*\s*" + re.escape(var) + r"\b", self._body(f, fn)):
                            continue      # a local of the same name bound to something else
                        names = self.binds.get(var)
                    if names:
                        self._add_read(f, m, names, m.group(2))
            for m in re.finditer(r"\bCvar_(VariableIntegerValue|VariableValue|VariableString|VariableStringBuffer)"
                                 r"\s*\(\s*\"([^\"]+)\"", f.nc):
                self._add_read(f, m, {m.group(2).lower()}, "by-name")

    def _outside(self, f):
        if not hasattr(f, "_outside_txt"):
            pos, parts = 0, []
            for _n, st, en in sorted(f.funcs, key=lambda t: t[1]):
                if st >= pos:
                    parts.append(f.mk[pos:st])
                    pos = en + 1
            parts.append(f.mk[pos:])
            f._outside_txt = "\n".join(parts)
        return f._outside_txt

    def _body(self, f, fn):
        for bf, st, en in self.mod.defs.get(fn.split("::")[-1], ()):
            if bf is f:
                return f.mk[st:en]
        return ""

    def _add_read(self, f, m, names, kind):
        fn = f.func_at(m.start())
        ln = f.line_of(m.start())
        line_txt = f.nc[f.line_starts[ln - 1]:f.nc.find("\n", f.line_starts[ln - 1])].strip()
        if re.search(r"\bCvar_Get2?\s*\(", line_txt) and kind != "by-name":
            return   # e.g. "if (!x) x = ri.Cvar_Get(...)" - the registration, not a use
        phases = sorted(self.mod.phases_of(fn))
        short = fn.split("::")[-1] if fn else None
        if short in DIAG_FUNCS:
            phases = ["DIAG"]
        derived = None
        dm = DERIVED_LHS.match(line_txt)
        if dm:
            derived = re.sub(r"\s+", "", dm.group(1))
        else:
            # one hop through a local: "j = i * r_intensity->value;" then "s_intensitytable[i] = j;" in the same
            # function caches the value in a file-scope table (static NAME[...])
            lm = re.match(r"^\s*([A-Za-z_]\w*)\s*=[^=]", line_txt)
            if lm and fn:
                body = self._body(f, fn)
                tm = re.search(r"\b([A-Za-z_]\w*)\s*\[[^\]]*\]\s*=[^=;]*\b" + re.escape(lm.group(1)) + r"\b", body)
                if tm and re.search(r"\bstatic\b[^;{}()]*\b" + re.escape(tm.group(1)) + r"\s*\[", self._outside(f)):
                    derived = "static." + tm.group(1)
        for nm in names:
            self.reads.setdefault(nm, []).append(dict(file=f.rel, line=ln, func=fn, kind=kind, phases=phases,
                                                      derived=derived))

    def derived_consumers(self, field):
        """Phases of every read of a cached field (tr.sunShadows), excluding its assignments."""
        memo = self.__dict__.setdefault("_derived_memo", {})
        if field in memo:
            return memo[field]
        memo[field] = out = self._derived_consumers(field)
        return out

    def _derived_consumers(self, field):
        obj, fld = field.split(".", 1)
        if obj == "static":
            pat = re.compile(r"\b" + re.escape(fld) + r"\s*\[[^\]]*\](?!\s*=[^=])")
        else:
            pat = re.compile(r"\b" + obj + r"\s*\.\s*" + re.escape(fld) + r"\b(?!\s*=[^=])")
        out = []
        for f in self.mod.files:
            for m in pat.finditer(f.mk):
                fn = f.func_at(m.start())
                if not fn:
                    continue      # the declaration itself
                out.append(dict(file=f.rel, line=f.line_of(m.start()), func=fn,
                                eff=effective_phase(self.mod.phases_of(fn))))
        return out


# ---------------------------------------------------------------- menus
def generated_rows():
    import gen_menu_graphics as g
    rows = []
    for page in g.PFX_PAGES:
        name = page[0]
        for _col, section, items in page[5]:
            for key, kind, label, cvar, spec in items:
                cvars = spec["set_cvars"] if kind == "pulldown" else [cvar]
                rows.append(dict(menu=name, section=section, label=label.rstrip(" *").strip(),
                                 star=label.rstrip().endswith("*"), cvars=cvars, apply="close",
                                 linked={cvar}))
    for _col, section, items in g.ADV_SECTIONS:
        for key, kind, label, cvar, spec in items:
            cvars = spec["set_cvars"] if kind == "pulldown" else [cvar]
            rows.append(dict(menu="advanced_graphics", section=section, label=label.rstrip(" *").strip(),
                             star=label.rstrip().endswith("*"), cvars=cvars, apply="checkrestart", linked={cvar}))
    return rows


def menu_apply_mode(text):
    return "checkrestart" if "ui_checkrestart" in text else "close"


SET_RE = re.compile(r"\bseta?\s+([A-Za-z_]\w*)\s")


def hand_rows(title, fname):
    path = os.path.join(MOD, "ui", fname)
    text = rd(path)
    apply = menu_apply_mode(text)
    blocks = re.split(r"\n\s*resource\s*\n", text)
    linked, rows, label_for = set(), [], {}
    for b in blocks:
        typ = b.strip().split("\n", 1)[0].strip()
        lc = re.search(r'linkcvar\s+"([^"]+)"', b)
        tt = re.search(r'\btitle\s+"([^"]*)"', b)
        nm = re.search(r'\bname\s+"([^"]*)"', b)
        if lc:
            linked.add(lc.group(1).lower())
            t = (tt.group(1) if tt else "") or (nm.group(1) if nm else "")
            if t and t.lower() not in ("default", "list", "hidden", "mode", "plate", "x"):
                label_for.setdefault(lc.group(1).lower(), t)
    for b in blocks:
        typ = b.strip().split("\n", 1)[0].strip()
        nm = re.search(r'\bname\s+"([^"]*)"', b)
        tt = re.search(r'\btitle\s+"([^"]*)"', b)
        lc = re.search(r'linkcvar\s+"([^"]+)"', b)
        sets = []
        for m in re.finditer(r'(?:addpopup\s+"[^"]*"\s+"[^"]*"\s+command|stuffcommand)\s+"([^"]*)"', b):
            for s in SET_RE.finditer(m.group(1) + " "):
                if s.group(1).lower() not in [x.lower() for x in sets]:
                    sets.append(s.group(1))
        cv = []
        if lc and typ in ("Slider", "CheckBox", "Field", "UIField", "UICheckBox", "UISlider"):
            cv.append(lc.group(1))
        cv += [s for s in sets if s.lower() not in [c.lower() for c in cv]]
        cv = [c for c in cv if not c.lower().startswith("ui_") and c.lower() not in ("g_subtitle",)]
        if not cv:
            continue
        lab = (tt.group(1) if tt and tt.group(1) not in ("list", "List", "Default") else "") or \
            label_for.get(cv[0].lower()) or (nm.group(1) if nm else typ)
        opts = re.findall(r'addpopup\s+"[^"]*"\s+"([^"]*)"', b)
        if opts:
            lab += " {" + " / ".join(opts[:3]) + (" / ..." if len(opts) > 3 else "") + "}"
        rows.append(dict(menu=title, section="", label=lab, star=False, cvars=cv, apply=apply,
                         linked={c for c in cv if c.lower() in linked}))
    return rows


# ---------------------------------------------------------------- classification
def effective_phase(phases):
    """One phase per read site. A function reachable from a frame root IS a per-frame read, whatever else also
    reaches it (gl2's RE_LoadWorldMap bakes cubemaps through R_RenderView, so the whole draw path is also
    WORLD-reachable; that does not make R_RecursiveWorldNode a load-time read). Otherwise the most restrictive."""
    ps = set(phases)
    if "DIAG" in ps:
        return "DIAG"
    if "FRAME" in ps:
        return "FRAME"
    for p in ("WINDOW", "WORLD", "ASSET", "INIT"):
        if p in ps:
            return p
    if "REG" in ps:
        return "REG"
    cmd = sorted(p for p in ps if p.startswith("CMD:"))
    if cmd:
        return cmd[0]
    if "TABLE" in ps:
        return "TABLE"
    return "UNREACHED"


def classify(lname, proc, idx):
    regs, reads = [], []
    for mkey in PROCESS[proc]:
        regs += [dict(r, module=mkey) for r in idx[mkey].regs.get(lname, [])]
        reads += [dict(r, module=mkey) for r in idx[mkey].reads.get(lname, [])]
    flags = set()
    for r in regs:
        flags |= r["flags"]
    userinfo = "USERINFO" in flags
    if not reads and not userinfo:
        return dict(cls="DEAD", flags=flags, regs=regs, reads=reads, phases=set(), note="no reader")
    phases = set()
    frame_mod = False
    regfns = {(r["file"], r["func"]) for r in regs if "FRAME" not in r["phases"]}
    cmd_also = set()
    for r in reads:
        eff = effective_phase(r["phases"])
        if (r["file"], r["func"]) in regfns and eff != "FRAME":
            eff = "CLAMP"      # read in the function that registers it (range clamp / validation), not a use
        r["eff"] = eff
        cmd_also |= {p[4:] for p in r["phases"] if p.startswith("CMD:") and eff in ("WORLD", "ASSET", "INIT")}
        if eff in ("DIAG", "CLAMP"):
            continue
        phases.add(eff)
        if eff == "FRAME" and r["kind"] in ("modified", "modificationCount"):
            frame_mod = True
    base = {p for p in phases if p in ("WINDOW", "WORLD", "ASSET", "INIT", "REG", "FRAME", "TABLE", "UNREACHED")
            or p.startswith("CMD:")}
    note = []
    latched = "LATCH" in flags
    consumers = sorted({"%s(%s)" % (r["func"], r.get("eff") or effective_phase(r["phases"])) for r in regs})
    latch_frame = latched and any("FRAME" in r["phases"] for r in regs)
    if userinfo and not reads:
        return dict(cls="LIVE", flags=flags, regs=regs, reads=reads, phases={"USERINFO"},
                    note="userinfo: the server re-reads it on change")
    restrictive = [p for p in ("WINDOW", "WORLD", "ASSET", "INIT", "REG") if p in base]
    cmd = sorted(p for p in base if p.startswith("CMD:"))
    has_frame = "FRAME" in base
    if "TABLE" in base:
        note.append("some reads only via a function pointer (TABLE: time unknown, not counted)")
    if "UNREACHED" in base:
        note.append("some reads in functions no root reaches")
    if cmd_also:
        note.append("the load-time read is also run by: " + ", ".join(sorted(cmd_also)))
    der = []
    for r in reads:
        if r.get("derived") and r["eff"] not in ("DIAG", "CLAMP"):
            mod = idx[r["module"]]
            cons = mod.derived_consumers(r["derived"])
            cp = sorted({c["eff"] for c in cons})
            der.append("%s (set %s, read %s)" % (r["derived"], r["eff"], "/".join(cp) or "nowhere"))
    if der:
        note.append("caches into " + "; ".join(sorted(set(der))))
    if restrictive:
        top = restrictive[0]
        cls = {"WINDOW": "WINDOW", "WORLD": "MAPLOAD", "ASSET": "RESTART", "INIT": "RESTART", "REG": "RESTART"}[top]
        if has_frame and frame_mod and not latched and top != "WORLD":
            cls = "LIVE"
            note.append("init-time read, re-applied per frame on ->modified")
        elif has_frame:
            cls += "+mix"
    elif has_frame:
        cls = "LIVE"
    elif cmd:
        cls = "CMD"
        note.append(",".join(c[4:] for c in cmd))
    else:
        cls = "UNKNOWN"
        note.append("every read is in a function no declared root reaches - check by hand")
    if latched and cls == "LIVE":
        if latch_frame:
            note.append("latch consumed by a per-frame Cvar_Get")
        else:
            cls = "RESTART"
            note.append("every read is per-frame, but CVAR_LATCH holds the value until the next Cvar_Get "
                        "(R_Register / CG_Init): LATCH is the only thing making it wait")
    # a cached copy (tr.X = cvar) consumed while loading the world makes the setting wait for the world
    for r in reads:
        if r.get("derived") and r["eff"] not in ("DIAG", "CLAMP"):
            ceff = {c["eff"] for c in idx[r["module"]].derived_consumers(r["derived"])}
            if "WORLD" in ceff and cls.split("+")[0] in ("LIVE", "RESTART"):
                cls = "MAPLOAD" + ("+mix" if "FRAME" in ceff else "")
                note = [n for n in note if "LATCH is the only thing" not in n]
                note.append("MAPLOAD through the cached copy")
                break
            if ceff & {"ASSET", "INIT"} and cls.split("+")[0] in ("LIVE", "RESTART"):
                cls = "RESTART" + ("+mix" if "FRAME" in ceff else "")
                note = [n for n in note if "LATCH is the only thing" not in n]
                note.append("RESTART through the cached copy (consumed at %s)" % "/".join(sorted(ceff & {"ASSET", "INIT"})))
    return dict(cls=cls, flags=flags, regs=regs, reads=reads, phases=base, note="; ".join(note))


def marker_verdict(row, cv, c2, flags2, flags_of):
    """Is the menu's '*' marker (or its absence) right, given what the menu's APPLY does?"""
    cls = c2.split("+")[0]
    if row["apply"] == "none":
        return "-"
    if cls == "DEAD":
        return "DEAD row (nothing reads it on gl2)"
    live = cls == "LIVE"
    if row["apply"] == "close":
        if live and row["star"]:
            return "WRONG: '*' but live"
        if not live and not row["star"]:
            return "WRONG: missing '*'"
        return "ok"
    # Menu::CheckRestart looks at each widget's OWN linkcvar: this cvar restarts the video only if it is linked here
    linked = {x.lower() for x in row["linked"]}
    latched_linked = ("LATCH" in flags2) and cv.lower() in linked
    if live:
        if latched_linked:
            return "ok, but APPLY forces a needless vid_restart"
        return "ok"
    if latched_linked:
        return "ok (APPLY vid_restarts)"
    others = [c for c in row["cvars"] if c.lower() != cv.lower() and c.lower() in linked
              and "LATCH" in flags_of(c)]
    if others and "TERRAIN_LATCH" not in flags2:
        return ("waits unless %s changes in the same pick (it is linked and latched; this cvar is not linked)"
                % "/".join(others))
    if "TERRAIN_LATCH" in flags2:
        return "waits: TERRAIN_LATCH never latches (cvar.c), so CheckRestart's ter_restart never fires"
    return "WRONG: waits silently for the next map (not latched, so APPLY does not restart)"


def short_sites(reads, maxn=3):
    """Compact 'file:line fn [phase]': the first site of each effective phase, restrictive first."""
    by = {}
    for r in reads:
        by.setdefault(r.get("eff") or effective_phase(r["phases"]), []).append(r)
    rank = {p: i for i, p in enumerate(["WINDOW", "WORLD", "ASSET", "INIT", "REG"])}
    picked = []
    for key in sorted(by, key=lambda k: (rank.get(k, 6 if k.startswith("CMD") else 7 if k == "FRAME" else 9), k)):
        r = by[key][0]
        picked.append("%s:%d %s [%s]" % (r["file"].split("/", 1)[-1], r["line"], r["func"] or "-", key))
    more = len(reads) - len(picked[:maxn])
    return "; ".join(picked[:maxn]) + (" (+%d)" % more if more > 0 else "")


def fl(flags):
    order = ["ARCHIVE", "LATCH", "CHEAT", "TERRAIN_LATCH", "ROM", "TEMP", "USERINFO", "INIT"]
    s = ",".join(x.replace("TERRAIN_LATCH", "TER_LATCH") for x in order if x in flags)
    return s or "0"


def build(extra=()):
    idx = {k: CvarIndex(Module(k)) for k in MODULES}
    rows = generated_rows()
    for title, fname in HAND_MENUS:
        rows += hand_rows(title, fname)
    uitext = {}
    for fn_ in sorted(os.listdir(os.path.join(MOD, "ui"))):
        if fn_.endswith(".urc"):
            uitext[fn_] = rd(os.path.join(MOD, "ui", fn_)).lower()
    for cv in extra:
        pat = re.compile(r'(linkcvar\s+"' + re.escape(cv.lower()) + r'"|\bseta?\s+' + re.escape(cv.lower()) + r'\b)')
        where = [fn_[:-4] for fn_, t in uitext.items() if pat.search(t)]
        rows.append(dict(menu="(no menu)" if not where else "(other: %s)" % ", ".join(where), section="", label="-",
                         star=False, cvars=[cv], apply="none", linked=set()))
    out = []
    for row in rows:
        for cv in row["cvars"]:
            ln = cv.lower()
            r2 = classify(ln, "gl2", idx)
            r1 = classify(ln, "gl1", idx)
            out.append(dict(menu=row["menu"], section=row["section"], label=row["label"], star=row["star"],
                            apply=row["apply"], cvar=cv, gl2=r2, gl1=r1,
                            verdict=marker_verdict(row, cv, r2["cls"], r2["flags"],
                                                   lambda c: classify(c.lower(), "gl2", idx)["flags"])))
    return out, idx


def md_table(out):
    L = ["| # | menu | row | cvar | gl2 flags | gl1 flags | gl2 class | gl1 class | gl2 read phases | `*` | verdict | "
         "gl2 key read sites |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, o in enumerate(out, 1):
        g2, g1 = o["gl2"], o["gl1"]
        L.append("| %d | %s | %s | `%s` | %s | %s | **%s**%s | %s | %s | %s | %s | %s |" % (
            i, o["menu"], o["label"], o["cvar"], fl(g2["flags"]), fl(g1["flags"]), g2["cls"],
            (" (" + g2["note"] + ")") if g2["note"] else "", g1["cls"],
            "/".join(sorted(g2["phases"], key=phase_rank)) or "-",
            "*" if o["star"] else "", o["verdict"], short_sites(g2["reads"]) or "-"))
    counts = {}
    seen = set()
    nrows = 0
    for o in out:
        if o["menu"].startswith("(no menu)") or o["menu"].startswith("(other:"):
            continue
        nrows += 1
        if o["cvar"].lower() in seen:
            continue
        seen.add(o["cvar"].lower())
        counts[o["gl2"]["cls"]] = counts.get(o["gl2"]["cls"], 0) + 1
    L.append("")
    L.append("gl2 class counts over %d distinct menu cvars (%d menu rows): %s" % (
        len(seen), nrows, ", ".join("%s %d" % (k, counts[k]) for k in sorted(counts))))
    return "\n".join(L)


# ------------------------------------------------------------------ live graphics settings (r_hzmLiveApply)
def live_auto():
    """(renderer AUTO, cgame AUTO) - the two HZM_LIVEAPPLY_AUTO copies; None where the engine has no such define"""
    out = []
    for rel in (os.path.join("renderergl2", "tr_local.h"), os.path.join("cgame", "cg_view.c")):
        m = re.search(r"#define\s+HZM_LIVEAPPLY_AUTO\s+(\d+)", rd(os.path.join(ENG, rel)) or "")
        out.append(int(m.group(1)) if m else None)
    return tuple(out)


def live_hooks():
    """[(cvar, bit)] parsed from R_HZM_LiveHooks[] in renderergl2/tr_hzm_live.c (one entry per line)"""
    txt = rd(os.path.join(ENG, "renderergl2", "tr_hzm_live.c")) or ""
    m = re.search(r"R_HZM_LiveHooks\[\]\s*=\s*\{(.*?)\n\};", txt, re.S)
    return [(c.lower(), int(b)) for c, b in re.findall(r'\{\s*"([^"]+)"\s*,\s*(\d+)\s*\}', m.group(1))] if m else []


def live_set(bits=None):
    """cvars that apply without a restart under `bits` (default: the shipped renderer AUTO)"""
    if bits is None:
        bits = live_auto()[0] or 0
    return sorted(c for c, b in live_hooks() if b & bits)


def check_live():
    """--check-auto: the renderer and cgame AUTO defines agree. --check-stars: the post-FX ' *' rows are exactly the
    starrable rows that are NOT live under the shipped AUTO (a live row keeps no star; a waiting row keeps its star)."""
    rc = 0
    ra, ca = live_auto()
    if "--check-auto" in sys.argv:
        if ra is None and ca is None:
            print("ok: no HZM_LIVEAPPLY_AUTO in this engine tree (live settings not merged)")
        elif ra != ca:
            print("FAIL: HZM_LIVEAPPLY_AUTO renderer %s != cgame %s - they must flip together" % (ra, ca))
            rc = 1
        else:
            print("ok: HZM_LIVEAPPLY_AUTO %s in renderer and cgame" % ra)
    if "--check-stars" in sys.argv:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import gen_menu_graphics as G
        live = set(live_set())
        bad = []
        for page in G.PFX_PAGES:
            for _col, _title, rows in page[5]:
                for row in rows:
                    starred = row[2].rstrip().endswith("*")
                    cv = row[3].lower()
                    if starred and cv in live:
                        bad.append("%s is live under AUTO %s but its row still says '*'" % (row[3], ra))
                    if not starred and cv in [c for c, _ in live_hooks()] and cv not in live:
                        bad.append("%s waits for a restart under AUTO %s but its row has no '*'" % (row[3], ra))
        for b in bad:
            print("FAIL:", b)
        if not bad:
            print("ok: post-FX stars match the live set under AUTO %s: %s" % (ra, ", ".join(sorted(live)) or "none"))
        rc = rc or (1 if bad else 0)
    return rc


def main():
    if "--check-auto" in sys.argv or "--check-stars" in sys.argv:
        return check_live()
    if "--live" in sys.argv:
        print("\n".join(live_set(int(sys.argv[sys.argv.index("--live") + 1]))))
        return 0
    if "--why" in sys.argv:
        fn = sys.argv[sys.argv.index("--why") + 1]
        mod = sys.argv[sys.argv.index("--why") + 2] if len(sys.argv) > sys.argv.index("--why") + 2 else "gl2"
        m = Module(mod)
        print("\n".join(m.why(fn)) or "%s: reached from no root in %s" % (fn, mod))
        return 0
    extra = []
    if "--extra" in sys.argv:
        extra = [c for c in sys.argv[sys.argv.index("--extra") + 1].split(",") if c]
    if "--check" in sys.argv:
        doc = rd(sys.argv[sys.argv.index("--check") + 1])
        m = re.search(r"<!-- gfx_live_audit:begin(.*?)-->", doc)
        if m and "--extra" in m.group(1):
            extra = [c for c in m.group(1).split("--extra", 1)[1].strip().split(",") if c]
    out, idx = build(extra)
    if "--cvar" in sys.argv:
        nm = sys.argv[sys.argv.index("--cvar") + 1].lower()
        for proc in ("gl2", "gl1"):
            c = classify(nm, proc, idx)
            print("== %s  %s  class=%s  flags=%s  %s" % (proc, nm, c["cls"], fl(c["flags"]), c["note"]))
            for r in c["regs"]:
                print("   REG  %s:%d %s [%s] default=%s flags=%s var=%s" % (r["file"], r["line"], r["func"],
                                                                         "/".join(r["phases"]), r["default"],
                                                                         fl(r["flags"]), r["var"]))
            for r in c["reads"]:
                print("   READ %s:%d %s ->%s [%s]" % (r["file"], r["line"], r["func"], r["kind"], "/".join(r["phases"])))
        return 0
    if "--json" in sys.argv:
        def clean(c):
            return dict(cls=c["cls"], flags=sorted(c["flags"]), note=c["note"], phases=sorted(c["phases"]),
                        regs=[dict(r, flags=sorted(r["flags"])) for r in c["regs"]], reads=c["reads"])
        print(json.dumps([dict(o, gl2=clean(o["gl2"]), gl1=clean(o["gl1"])) for o in out], indent=1, default=list))
        return 0
    table = md_table(out)
    if "--check" in sys.argv:
        p = sys.argv[sys.argv.index("--check") + 1]
        doc = rd(p)
        m = re.search(r"<!-- gfx_live_audit:begin[^>]*-->\n(.*?)\n<!-- gfx_live_audit:end -->", doc, re.S)
        if not m:
            print("no gfx_live_audit markers in %s" % p)
            return 1
        if m.group(1).strip() != table.strip():
            print("STALE: %s no longer matches the code - regenerate the block with this script" % p)
            return 1
        print("ok: %s matches the code" % p)
        return 0
    print(table)
    if "--sites" in sys.argv:
        print("\n## Every read site (gl2 process)\n")
        seen = set()
        for o in out:
            if o["cvar"].lower() in seen:
                continue
            seen.add(o["cvar"].lower())
            print("### `%s` - %s" % (o["cvar"], o["gl2"]["cls"]))
            for r in o["gl2"]["regs"]:
                print("- REG `%s:%d` %s [%s] flags=%s" % (r["file"], r["line"], r["func"], "/".join(r["phases"]),
                                                          fl(r["flags"])))
            for r in o["gl2"]["reads"]:
                print("- `%s:%d` %s ->%s [%s]" % (r["file"], r["line"], r["func"], r["kind"], "/".join(r["phases"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
