#!/usr/bin/env python
"""glsl_variant_lint.py - offline per-permutation lint of the gl2 GLSL (vet_phaseS "Option C", G3).

WHY. A GLSL compile error in renderer_opengl2 is not a warning: GLSL_InitGPUShaders calls
ri.Error(ERR_FATAL, "Could not load lightall shader!") (renderergl2/tr_glsl.c), so ONE typo in ONE permutation stops
the game for EVERY gl2 player at start-up - and nothing in the build compiles GLSL. No glslang is installed and no
game client may be launched from an agent session, so this tool is the offline gate.

WHAT IT DOES, per permutation:
  1. rebuilds the EXACT source the driver receives: GLSL_GetShaderHeader's text for #version 120 / 130 / 150 (the
     enum values it prints are parsed out of renderergl2/tr_local.h), then the permutation's #defines exactly as
     GLSL_InitGPUShaders builds them, then the .glsl file. The header template is pinned: every string literal in
     tr_glsl.c's GLSL_GetShaderHeader must be one this tool knows, or it FAILS as "header drift".
  2. runs a C preprocessor (#if/#ifdef/#elif/#else/#endif, defined(), && || ! and comparisons, object macros).
  3. lints the active code: balanced () [] {}; no double quote or backslash anywhere in a .glsl (the stringify step
     wraps every line in "..." - renderergl2/tools/stringify.cpp); every identifier declared BEFORE use (scoped by
     braces, function parameters, for-init); version rules (texture/textureLod/bit operators need 130; texture2D /
     gl_FragColor / gl_FrontFacing are fragment-only once the header's 130+ macros apply; no 'f' float suffix in 120);
     every uniform u_X declared in a .glsl exists in tr_glsl.c uniformsInfo[] with a matching type; uniformsInfo[] has
     exactly as many rows as uniform_t has members (vet F10).
  4. TEXT BUFFER (bug-3179, 2026-09-28): GLSL_InitGPUShader copies header + source into a fixed per-stage buffer
     (char vpCode/fpCode[N], N parsed out of tr_glsl.c - a literal or a #define) and GLSL_LoadGPUShaderText refuses a
     text that does not fit, which is the same ERR_FATAL for every gl2 player. v1103c shipped lightall_fp variants of
     32145-32744 bytes into a 32000 buffer; glslang and every check above passed. FAIL when header + source + NUL > N,
     WARN (printed, not failing) above 95% of N. Neither glslang nor a real-driver compile can see this: it happens
     before any GL call.
  It does NOT type-check expressions or prove the driver accepts the program - that is what glslangValidator adds
  (--emit writes every unique rebuilt source so it can be fed to one).

PERMUTATIONS: lightall = every LIGHTDEF index GLSL_InitGPUShaders builds (its skip rules applied) x a fixed set of
cvar configurations (the user's live one first, then fast-light, all-on and mixed ones, chosen so every define that
lightall reads is exercised with and without USE_LIGHT_VECTOR / USE_FAST_LIGHT / USE_MODELMATRIX); dlight = both;
generic = every GENERICDEF index; texturecolor = the one; pshadow = its one build (USE_PCF + USE_DISCARD - added
2026-09-26 for headlight S4). Vertex AND fragment, #version 120, 130 and 150.

    python docs/tools/glsl_variant_lint.py                 # lint the tree, exit 1 on any finding
    python docs/tools/glsl_variant_lint.py --selftest      # prove it: a broken copy must FAIL and the tree must PASS
    python docs/tools/glsl_variant_lint.py --emit DIR      # also write every unique rebuilt source (for glslang)
    python docs/tools/glsl_variant_lint.py --post          # ALSO every other GLSL_InitGPUShader program (post-FX etc.)
    python docs/tools/glsl_variant_lint.py --post --write-baseline   # record today's known findings (allowlist)

POST-FX COVERAGE (--post, 2026-09-27, docs/proposals/postfx_ports_2026-09-27 plan Q0.1). Every post program is
ri.Error(ERR_FATAL) at start-up too (tr_glsl.c "Could not load <x> shader!"), and none of them was linted. --post
DERIVES the program list from the GLSL_InitGPUShader/GLSL_TryInitGPUShader call sites in tr_glsl.c (never a hand
list): name, vertex file, fragment file, and the extradefines built since the last `extradefines[0] =` reset.
Sites whose defines are built under a condition need an entry in POST_VARIANTS; an unknown conditional site is a
finding, so a new looped program cannot slip through unlinted. GLES-only `#extension` lines (qglesMajorVersion < 3)
are dropped - desktop GL never emits them. Findings already present today are listed in glsl_post_baseline.json and
reported as KNOWN (they do not fail the run); anything else fails. --post is OPT-IN until the MSAA/gfx owner agrees
the table (their lint_msaa_p2b.py layers on --emit); without --post the tool's output is byte-for-byte what it was.
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
GL2 = os.path.join(ROOT, "openmohaa-hzm", "code", "renderergl2")
VERSIONS = (120, 130, 150)

# --------------------------------------------------------------------------------------------- the pinned header
# every string literal GLSL_GetShaderHeader may append (formats included). A literal not listed = header drift.
KNOWN_HEADER_LITERALS = {
    "#version 300 es\n", "#version 150\n", "#version 130\n", "precision mediump float;\n",
    "precision mediump sampler2DShadow;\n", "#define attribute in\n", "#define varying out\n",
    "#define varying in\n", "out vec4 out_Color;\n", "#define gl_FragColor out_Color\n",
    "#define texture2D texture\n", "#define textureCubeLod textureLod\n", "#define shadow2D texture\n",
    "#version 100\n", "#define shadow2D(a,b) shadow2DEXT(a,b)\n", "#version 120\n",
    "#define shadow2D(a,b) shadow2D(a,b).r\n", "#ifndef M_PI\n#define M_PI 3.14159265358979323846\n#endif\n",
    "#ifndef deformGen_t\n", "#define deformGen_t\n", "#define DGEN_WAVE_SIN %i\n", "#define DGEN_WAVE_SQUARE %i\n",
    "#define DGEN_WAVE_TRIANGLE %i\n", "#define DGEN_WAVE_SAWTOOTH %i\n", "#define DGEN_WAVE_INVERSE_SAWTOOTH %i\n",
    "#define DGEN_BULGE %i\n", "#define DGEN_MOVE %i\n", "#endif\n", "#ifndef tcGen_t\n", "#define tcGen_t\n",
    "#define TCGEN_LIGHTMAP %i\n", "#define TCGEN_TEXTURE %i\n", "#define TCGEN_ENVIRONMENT_MAPPED %i\n",
    "#define TCGEN_ENVIRONMENT_MAPPED2 %i\n", "#define TCGEN_FOG %i\n", "#define TCGEN_VECTOR %i\n",
    "#ifndef colorGen_t\n", "#define colorGen_t\n", "#define CGEN_LIGHTING_DIFFUSE %i\n", "#define CGEN_DOT %i\n",
    "#define CGEN_ONE_MINUS_DOT %i\n", "#ifndef alphaGen_t\n", "#define alphaGen_t\n",
    "#define AGEN_LIGHTING_SPECULAR %i\n", "#define AGEN_PORTAL %i\n", "#define AGEN_SCOORD %i\n",
    "#define AGEN_TCOORD %i\n", "#define AGEN_DOT %i\n", "#define AGEN_ONE_MINUS_DOT %i\n",
    "#ifndef r_FBufScale\n#define r_FBufScale vec2(%f, %f)\n#endif\n", "#define USE_PBR\n",
    "#define ROUGHNESS_MIPS float(%d)\n", "#line 0\n",
}


def c_string_literals(text):
    """adjacent C string literals joined, unescaped (\\n only - all this header uses)"""
    out = []
    for m in re.finditer(r'((?:"(?:[^"\\]|\\.)*"\s*)+)', text):
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
        s = "".join(parts).replace("\\n", "\n").replace('\\"', '"')
        out.append(s)
    return out


def header_function_body(tr_glsl):
    m = re.search(r"static void GLSL_GetShaderHeader\(.*?\n\{(.*?)\n\}\n", tr_glsl, re.S)
    if not m:
        raise SystemExit("header drift: GLSL_GetShaderHeader not found in tr_glsl.c")
    return m.group(1)


def check_header_pinned(tr_glsl):
    body = re.sub(r"//[^\n]*", "", header_function_body(tr_glsl))
    found = set()
    for lit in c_string_literals(body):
        # the va() format blocks are one literal each; split them into lines again
        for line in re.findall(r"[^\n]*\n", lit):
            found.add(line)
        if not lit.endswith("\n"):
            found.add(lit)
    known = set()
    for k in KNOWN_HEADER_LITERALS:
        for line in re.findall(r"[^\n]*\n", k):
            known.add(line)
    unknown = sorted(found - known)
    return unknown


def parse_enums(tr_local):
    """name -> value for every enumerator of every typedef enum in tr_local.h"""
    vals = {}
    text = re.sub(r"/\*.*?\*/", "", tr_local, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    for m in re.finditer(r"(?:typedef\s+)?enum\s*\w*\s*\{(.*?)\}\s*\w*\s*;", text, re.S):
        cur = -1
        for item in m.group(1).split(","):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                name, expr = [x.strip() for x in item.split("=", 1)]
                expr2 = re.sub(r"\b([A-Za-z_]\w*)\b", lambda mm: str(vals.get(mm.group(1), 0)), expr)
                try:
                    cur = int(eval(expr2.replace("0x", "0x"), {"__builtins__": {}}))
                except Exception:
                    cur += 1
            else:
                name = item
                cur += 1
            if re.match(r"^[A-Za-z_]\w*$", name):
                vals[name] = cur
    return vals


def build_header(version, stage, extra, enums, pbr=False, cube=False):
    h = []
    if version >= 130:
        h.append("#version %d\n" % version)
        h.append(extra)
        if stage == "vp":
            h.append("#define attribute in\n#define varying out\n")
        else:
            h.append("#define varying in\nout vec4 out_Color;\n#define gl_FragColor out_Color\n"
                     "#define texture2D texture\n#define textureCubeLod textureLod\n#define shadow2D texture\n")
    else:
        h.append("#version 120\n")
        h.append(extra)
        h.append("#define shadow2D(a,b) shadow2D(a,b).r\n")
    h.append("#ifndef M_PI\n#define M_PI 3.14159265358979323846\n#endif\n")
    h.append("#ifndef deformGen_t\n#define deformGen_t\n")
    for n in ("DGEN_WAVE_SIN", "DGEN_WAVE_SQUARE", "DGEN_WAVE_TRIANGLE", "DGEN_WAVE_SAWTOOTH",
              "DGEN_WAVE_INVERSE_SAWTOOTH", "DGEN_BULGE", "DGEN_MOVE"):
        h.append("#define %s %d\n" % (n, enums[n]))
    h.append("#endif\n#ifndef tcGen_t\n#define tcGen_t\n")
    for n in ("TCGEN_LIGHTMAP", "TCGEN_TEXTURE", "TCGEN_ENVIRONMENT_MAPPED", "TCGEN_ENVIRONMENT_MAPPED2", "TCGEN_FOG",
              "TCGEN_VECTOR"):
        h.append("#define %s %d\n" % (n, enums[n]))
    h.append("#endif\n#ifndef colorGen_t\n#define colorGen_t\n")
    for n in ("CGEN_LIGHTING_DIFFUSE", "CGEN_DOT", "CGEN_ONE_MINUS_DOT"):
        h.append("#define %s %d\n" % (n, enums[n]))
    h.append("#endif\n#ifndef alphaGen_t\n#define alphaGen_t\n")
    for n in ("AGEN_LIGHTING_SPECULAR", "AGEN_PORTAL", "AGEN_SCOORD", "AGEN_TCOORD", "AGEN_DOT", "AGEN_ONE_MINUS_DOT"):
        h.append("#define %s %d\n" % (n, enums[n]))
    h.append("#endif\n")
    h.append("#ifndef r_FBufScale\n#define r_FBufScale vec2(%f, %f)\n#endif\n" % (1.0 / 3440, 1.0 / 1440))
    if pbr:
        h.append("#define USE_PBR\n")
    if cube:
        h.append("#define ROUGHNESS_MIPS float(%d)\n" % 6)
    h.append("#line 0\n")
    return "".join(h)


# --------------------------------------------------------------------------------------------- permutations
LIGHTDEF = dict(LIGHTMAP=0x1, LIGHT_VECTOR=0x2, LIGHT_VERTEX=0x3, TYPE_MASK=0x3, ENTITY_VERTEX=0x4, TCGEN=0x8,
                PARALLAX=0x10, SHADOWMAP=0x20, ENTITY_BONE=0x40, COUNT=0x80)
MAX_BONES = 80

# (label, cvars). The first is the user's live gl2 config (G:\mohaa-gl2\home\maintt\configs\omconfig.cfg, 2026-09-26).
CONFIGS = [
    ("user", dict(normal=1, spec=0, parallax=0, pshadows=0, sun=1, dlight=1, cube=0, deluxe=0, gloss=1, delspec=0.3,
                  pbr=0, swizzle=0, gpuanim=1)),
    ("fastlight", dict(normal=0, spec=0, parallax=0, pshadows=0, sun=1, dlight=1, cube=0, deluxe=0, gloss=0,
                       delspec=0.3, pbr=0, swizzle=0, gpuanim=1)),
    ("fast-sun2-dl2", dict(normal=0, spec=0, parallax=0, pshadows=0, sun=2, dlight=2, cube=0, deluxe=1, gloss=2,
                           delspec=0.0, pbr=1, swizzle=1, gpuanim=0)),
    ("all-on", dict(normal=1, spec=1, parallax=2, pshadows=1, sun=2, dlight=2, cube=2, deluxe=1, gloss=3, delspec=0.3,
                    pbr=1, swizzle=1, gpuanim=1)),
    ("mixed-a", dict(normal=1, spec=0, parallax=1, pshadows=0, sun=1, dlight=1, cube=1, deluxe=0, gloss=0,
                     delspec=0.0, pbr=0, swizzle=0, gpuanim=0)),
    ("mixed-b", dict(normal=0, spec=1, parallax=0, pshadows=0, sun=0, dlight=0, cube=0, deluxe=1, gloss=2,
                     delspec=0.3, pbr=0, swizzle=1, gpuanim=1)),
    ("mixed-c", dict(normal=1, spec=1, parallax=0, pshadows=0, sun=1, dlight=2, cube=0, deluxe=0, gloss=1,
                     delspec=0.0, pbr=1, swizzle=0, gpuanim=1)),
    ("mixed-d", dict(normal=1, spec=0, parallax=2, pshadows=0, sun=2, dlight=1, cube=2, deluxe=1, gloss=0,
                     delspec=0.3, pbr=0, swizzle=1, gpuanim=0)),
    ("mixed-e", dict(normal=0, spec=0, parallax=0, pshadows=0, sun=2, dlight=2, cube=1, deluxe=0, gloss=3,
                     delspec=0.0, pbr=1, swizzle=0, gpuanim=1)),
    ("mixed-f", dict(normal=1, spec=1, parallax=1, pshadows=1, sun=0, dlight=1, cube=0, deluxe=1, gloss=2,
                     delspec=0.3, pbr=0, swizzle=0, gpuanim=0)),
]


def lightall_defines(i, c):
    """mirror of the lightall loop in GLSL_InitGPUShaders; None = the loop skips index i"""
    L = LIGHTDEF
    light_type = i & L["TYPE_MASK"]
    fast = not (c["normal"] or c["spec"])
    if (i & L["PARALLAX"]) and not c["parallax"]:
        return None
    if (i & L["SHADOWMAP"]) and (not light_type or not c["sun"]):
        return None
    if (i & L["ENTITY_VERTEX"]) and (i & L["ENTITY_BONE"]):
        return None
    d = []
    if c["dlight"] >= 2:
        d.append("#define USE_SHADOWMAP\n")
    if c["swizzle"]:
        d.append("#define SWIZZLE_NORMALMAP\n")
    if light_type:
        d.append("#define USE_LIGHT\n")
        if fast:
            d.append("#define USE_FAST_LIGHT\n")
        if light_type == L["LIGHTMAP"]:
            d.append("#define USE_LIGHTMAP\n")
            if c["deluxe"] and not fast:
                d.append("#define USE_DELUXEMAP\n")
        elif light_type == L["LIGHT_VECTOR"]:
            d.append("#define USE_LIGHT_VECTOR\n")
        elif light_type == L["LIGHT_VERTEX"]:
            d.append("#define USE_LIGHT_VERTEX\n")
        if c["normal"]:
            d.append("#define USE_NORMALMAP\n")
            if (i & L["PARALLAX"]) and not (i & L["ENTITY_VERTEX"]) and not (i & L["ENTITY_BONE"]) and c["parallax"]:
                d.append("#define USE_PARALLAXMAP\n")
                if c["parallax"] > 1:
                    d.append("#define USE_RELIEFMAP\n")
                if c["pshadows"]:
                    d.append("#define USE_PARALLAXMAP_SHADOWS\n")
                d.append("#define r_parallaxMapOffset %f\n" % 0.0)
        if c["spec"]:
            d.append("#define USE_SPECULARMAP\n")
        if c["cube"]:
            d.append("#define USE_CUBEMAP\n")
            if c["cube"] == 2:
                d.append("#define USE_BOX_CUBEMAP_PARALLAX\n")
        elif c["delspec"] > 0.000001:
            d.append("#define r_deluxeSpecular %f\n" % c["delspec"])
        d.append(("#define GLOSS_IS_GLOSS\n", "#define GLOSS_IS_SMOOTHNESS\n", "#define GLOSS_IS_ROUGHNESS\n",
                  "#define GLOSS_IS_SHININESS\n")[c["gloss"]])
    if i & L["SHADOWMAP"]:
        d.append("#define USE_SHADOWMAP\n")
        if c["sun"] == 1:
            d.append("#define SHADOWMAP_MODULATE\n")
        elif c["sun"] == 2:
            d.append("#define USE_PRIMARY_LIGHT\n")
    if i & L["TCGEN"]:
        d.append("#define USE_TCGEN\n#define USE_TCMOD\n")
    if i & L["ENTITY_VERTEX"]:
        d.append("#define USE_MODELMATRIX\n")
        if c["gpuanim"]:
            d.append("#define USE_VERTEX_ANIMATION\n")
    elif i & L["ENTITY_BONE"]:
        d.append("#define USE_MODELMATRIX\n")
        d.append("#define USE_BONE_ANIMATION\n#define MAX_GLSL_BONES %d\n" % MAX_BONES)
    return "".join(d)


def generic_defines(i, gpuanim):
    # GENERICDEF bits (tr_local.h): DEFORM 1, TCGEN 2, VERTEX_ANIM 4, FOG 8, BONE 0x10, RGBAGEN 0x20 - read from enums
    return None  # filled in main() from the parsed enum (see generic_variants)


# --------------------------------------------------------------------------------------------- preprocessor
class PP:
    def __init__(self):
        self.macros = {}      # name -> replacement text (object-like)
        self.fmacros = {}     # name -> (params, body)

    def eval_if(self, expr, where):
        toks = re.findall(r"defined\s*\(\s*\w+\s*\)|defined\s+\w+|&&|\|\||==|!=|>=|<=|[()!<>]|\d+(?:\.\d+)?|\w+", expr)
        out = []
        for t in toks:
            if t.startswith("defined"):
                name = re.findall(r"\w+", t)[1]
                out.append("1" if (name in self.macros or name in self.fmacros) else "0")
            elif t == "&&":
                out.append(" and ")
            elif t == "||":
                out.append(" or ")
            elif t == "!":
                out.append(" not ")
            elif re.match(r"^\d", t):
                out.append(t)
            elif re.match(r"^\w+$", t):
                v = self.macros.get(t, "0").strip()
                out.append(v if re.match(r"^-?\d+(\.\d+)?$", v) else "0")
            else:
                out.append(t)
        try:
            return bool(eval("".join(out), {"__builtins__": {}}))
        except Exception as e:
            raise LintError("%s: cannot evaluate #if %r (%s)" % (where, expr, e))

    def run(self, lines):
        """lines: [(tag, text)] -> active [(tag, text)] with comments already stripped"""
        stack = []   # (active, taken)
        active = True
        out = []
        for tag, text in lines:
            s = text.strip()
            if s.startswith("#"):
                m = re.match(r"#\s*(\w+)\s*(.*)$", s)
                d, rest = (m.group(1), m.group(2).strip()) if m else ("", "")
                if d in ("ifdef", "ifndef"):
                    cond = (rest in self.macros or rest in self.fmacros)
                    if d == "ifndef":
                        cond = not cond
                    stack.append((active, active and cond))
                    active = active and cond
                elif d == "if":
                    cond = self.eval_if(rest, tag) if active else False
                    stack.append((active, cond))
                    active = active and cond
                elif d == "elif":
                    if not stack:
                        raise LintError("%s: #elif without #if" % tag)
                    parent, taken = stack[-1]
                    cond = (not taken) and parent and self.eval_if(rest, tag)
                    stack[-1] = (parent, taken or cond)
                    active = cond
                elif d == "else":
                    if not stack:
                        raise LintError("%s: #else without #if" % tag)
                    parent, taken = stack[-1]
                    active = parent and not taken
                    stack[-1] = (parent, True)
                elif d == "endif":
                    if not stack:
                        raise LintError("%s: #endif without #if" % tag)
                    parent, _ = stack.pop()
                    active = parent
                elif not active:
                    pass
                elif d == "define":
                    m2 = re.match(r"(\w+)\(([^)]*)\)\s*(.*)$", rest)
                    if m2:
                        self.fmacros[m2.group(1)] = ([p.strip() for p in m2.group(2).split(",")], m2.group(3))
                    else:
                        m3 = re.match(r"(\w+)\s*(.*)$", rest)
                        self.macros[m3.group(1)] = m3.group(2)
                elif d == "undef":
                    self.macros.pop(rest, None)
                    self.fmacros.pop(rest, None)
                elif d in ("version", "extension", "line", "pragma"):
                    pass
                else:
                    raise LintError("%s: unknown directive #%s" % (tag, d))
                continue
            if active:
                out.append((tag, text))
        if stack:
            raise LintError("unterminated #if block (%d open)" % len(stack))
        return out


class LintError(Exception):
    pass


def strip_comments(src):
    """remove // and /* */ comments, keeping newlines"""
    out = []
    i, n = 0, len(src)
    while i < n:
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            if j < 0:
                raise LintError("unterminated /* comment")
            out.append("\n" * src.count("\n", i, j))
            i = j + 2
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


# --------------------------------------------------------------------------------------------- the checker
TYPES = set("""void bool int uint float double vec2 vec3 vec4 bvec2 bvec3 bvec4 ivec2 ivec3 ivec4 uvec2 uvec3 uvec4
mat2 mat3 mat4 mat2x2 mat2x3 mat2x4 mat3x2 mat3x3 mat3x4 mat4x2 mat4x3 mat4x4 sampler1D sampler2D sampler3D samplerCube
sampler2DShadow sampler1DShadow samplerCubeShadow sampler2DArray sampler2DRect""".split())
QUALIFIERS = set("""const uniform attribute varying in out inout centroid flat smooth noperspective invariant highp mediump
lowp precision""".split())
KEYWORDS = set("""if else for while do return break continue discard struct true false switch case default""".split())
BUILTIN_FUNCS = set("""radians degrees sin cos tan asin acos atan pow exp log exp2 log2 sqrt inversesqrt abs sign floor ceil
fract mod min max clamp mix step smoothstep length distance dot cross normalize faceforward reflect refract
matrixCompMult lessThan lessThanEqual greaterThan greaterThanEqual equal notEqual any all not texture2D texture2DProj
texture2DLod texture2DProjLod textureCube textureCubeLod shadow2D shadow2DProj texture textureLod textureProj
textureSize texelFetch textureGrad dFdx dFdy fwidth round trunc sinh cosh tanh asinh acosh atanh transpose inverse
outerProduct determinant isnan isinf roundEven modf""".split())
BUILTIN_VARS = {
    "vp": set("gl_Position gl_PointSize gl_VertexID gl_ClipVertex".split()),
    "fp": set("gl_FragColor gl_FragCoord gl_FrontFacing gl_FragDepth gl_FragData gl_PointCoord".split()),
}
V130_FUNCS = {"texture", "textureLod", "textureProj", "textureSize", "texelFetch", "textureGrad", "round", "trunc",
              "sinh", "cosh", "tanh", "asinh", "acosh", "atanh", "isnan", "isinf", "roundEven", "modf"}
V140_FUNCS = {"inverse"}
FRAG_ONLY = {"dFdx", "dFdy", "fwidth", "gl_FragColor", "gl_FragCoord", "gl_FrontFacing", "gl_FragDepth", "discard"}
TOKEN_RE = re.compile(r"\s*(?:(\d+\.\d*(?:[eE][-+]?\d+)?[fF]?|\.\d+(?:[eE][-+]?\d+)?[fF]?|\d+[eE][-+]?\d+[fF]?|"
                      r"0[xX][0-9a-fA-F]+[uU]?|\d+[uU]?)|([A-Za-z_]\w*)|(<<=|>>=|\+\+|--|<<|>>|<=|>=|==|!=|&&|\|\||"
                      r"\^\^|\+=|-=|\*=|/=|%=|&=|\|=|\^=|[-+*/%<>=!~&|^?:;,.(){}\[\]]))")


def tokenize(active, pp):
    toks = []
    for tag, text in active:
        pos = 0
        text = text.rstrip("\r\n")
        while pos < len(text):
            if text[pos:].strip() == "":
                break
            m = TOKEN_RE.match(text, pos)
            if not m or m.end() == pos:
                raise LintError("%s: cannot tokenize at %r" % (tag, text[pos:pos + 20]))
            pos = m.end()
            if m.group(1):
                toks.append(("num", m.group(1), tag))
            elif m.group(2):
                toks.append(("id", m.group(2), tag))
            else:
                toks.append(("op", m.group(3), tag))
    # object-like macro expansion (recursive, guarded)
    out = []

    def expand(tok, depth):
        kind, val, tag = tok
        if kind == "id" and val in pp.macros and depth < 16:
            body = pp.macros[val]
            sub = []
            p = 0
            while p < len(body):
                if body[p:].strip() == "":
                    break
                m = TOKEN_RE.match(body, p)
                if not m or m.end() == p:
                    raise LintError("%s: cannot tokenize macro %s" % (tag, val))
                p = m.end()
                if m.group(1):
                    sub.append(("num", m.group(1), tag))
                elif m.group(2):
                    sub.append(("id", m.group(2), tag))
                else:
                    sub.append(("op", m.group(3), tag))
            for s in sub:
                if s[0] == "id" and s[1] == val:
                    out.append(s)
                else:
                    expand(s, depth + 1)
        else:
            out.append(tok)

    for t in toks:
        expand(t, 0)
    return out


def check(toks, stage, version, uniforms_info, findings, fname):
    """scoped declared-before-use + version rules; appends findings"""
    def err(tag, msg):
        findings.append("%s %s v%d %s: %s" % (fname, stage, version, tag, msg))

    # balance
    pairs = {")": "(", "]": "[", "}": "{"}
    st = []
    for kind, v, tag in toks:
        if kind == "op" and v in "([{":
            st.append((v, tag))
        elif kind == "op" and v in ")]}":
            if not st or st[-1][0] != pairs[v]:
                err(tag, "unbalanced %s" % v)
                return
            st.pop()
    if st:
        err(st[-1][1], "unclosed %s" % st[-1][0])
        return

    # statement shape: a block ends after a statement, and two operands never touch (a lost ';' or operator)
    for k in range(1, len(toks)):
        pk, pv, _ = toks[k - 1]
        ck, cv, ctag = toks[k]
        if ck == "op" and cv == "}" and not (pk == "op" and pv in (";", "}", "{")):
            err(ctag, "'}' after %r - a statement is missing its ';'" % pv)
        if ck in ("id", "num") and (pk == "num" or (pk == "op" and pv == "]")):
            err(ctag, "%r directly after %r - a missing ';' or operator" % (cv, pv))
        if ck in ("id", "num") and pk == "id" and not (pv in TYPES or pv in QUALIFIERS or pv in KEYWORDS
                                                       or pv == "struct"):
            # a struct type name followed by a variable name is legitimate
            if not any(t[0] == "id" and t[1] == "struct" and toks[j + 1][1] == pv
                       for j, t in enumerate(toks[:k - 1]) if j + 1 < len(toks)):
                err(ctag, "%r directly after %r - a missing ';' or operator" % (cv, pv))

    globals_ = set()
    structs = set()
    scopes = []          # list of sets (function / block scopes)
    uniforms_here = {}   # name -> glsl type
    iface = {}           # this stage's varyings: vp outputs / fp inputs, name -> glsl type
    used = set()         # identifiers read anywhere in this stage
    n = len(toks)
    i = 0

    def known(name):
        if name in globals_ or name in structs:
            return True
        for s in scopes:
            if name in s:
                return True
        return False

    def is_type(v):
        return v in TYPES or v in structs

    def declare(name, tag):
        if scopes:
            scopes[-1].add(name)
        else:
            globals_.add(name)

    paren_depth = 0
    pending_params = None   # names to put into the scope the next '{' opens (function params / for-init)
    while i < n:
        kind, v, tag = toks[i]
        prev = toks[i - 1] if i else ("op", ";", tag)
        if kind == "num":
            if version < 130 and v[-1:] in "fF" and ("." in v or "e" in v.lower()):
                err(tag, "float suffix %r needs #version 130" % v)
            if version < 130 and v[-1:] in "uU":
                err(tag, "unsigned literal %r needs #version 130" % v)
            i += 1
            continue
        if kind == "op":
            if v in ("%", "&", "|", "^", "<<", ">>", "~", "%=", "&=", "|=", "^=", "<<=", ">>=") and version < 130:
                err(tag, "operator %r needs #version 130" % v)
            if v == "{":
                scopes.append(set(pending_params or ()))
                pending_params = None
            elif v == "}":
                if scopes:
                    scopes.pop()
            elif v == "(":
                paren_depth += 1
            elif v == ")":
                paren_depth -= 1
            i += 1
            continue
        # identifier
        if prev[0] == "op" and prev[1] == ".":
            i += 1   # member / swizzle
            continue
        if v == "struct":
            if i + 1 < n and toks[i + 1][0] == "id":
                structs.add(toks[i + 1][1])
                i += 2
                continue
        if v in QUALIFIERS or v in KEYWORDS:
            if v == "discard" and stage != "fp":
                err(tag, "discard in a vertex shader")
            if v == "precision":
                # precision mediump float;  -> skip to ;
                while i < n and not (toks[i][0] == "op" and toks[i][1] == ";"):
                    i += 1
                continue
            i += 1
            continue
        if is_type(v):
            # a declaration or a constructor call
            j = i + 1
            if j < n and toks[j][0] == "op" and toks[j][1] == "(":
                i += 1  # constructor
                continue
            if j < n and toks[j][0] == "op" and toks[j][1] == "[":
                # array type: float[5] name
                depth = 0
                while j < n:
                    if toks[j][1] == "[":
                        depth += 1
                    elif toks[j][1] == "]":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    j += 1
            if j < n and toks[j][0] == "id":
                name = toks[j][1]
                k = j + 1
                # function definition / prototype?
                if k < n and toks[k][0] == "op" and toks[k][1] == "(" and not scopes and paren_depth == 0:
                    globals_.add(name)
                    # parameters
                    params = []
                    depth = 0
                    k2 = k
                    while k2 < n:
                        t = toks[k2]
                        if t[1] == "(":
                            depth += 1
                        elif t[1] == ")":
                            depth -= 1
                            if depth == 0:
                                break
                        elif depth == 1 and t[0] == "id" and (t[1] not in QUALIFIERS) and not is_type(t[1]):
                            # a parameter name follows its type
                            pk = toks[k2 - 1]
                            if pk[0] == "id" and (is_type(pk[1])) or (pk[0] == "op" and pk[1] == "]"):
                                params.append(t[1])
                            else:
                                err(t[2], "unexpected parameter token %r" % t[1])
                        k2 += 1
                    # array-size expressions inside params are checked below as uses
                    after = toks[k2 + 1] if k2 + 1 < n else ("op", ";", tag)
                    if after[1] == "{":
                        pending_params = params
                    i = k2 + 1
                    continue
                # variable declaration(s): name [= expr | [N]] (, name ...)* ;
                declare(name, tag)
                if not scopes:
                    q = i - 1
                    while q >= 0 and toks[q][0] == "id" and toks[q][1] in QUALIFIERS:
                        if toks[q][1] == "uniform":
                            uniforms_here[name] = v
                        # the stage interface (after the header's macros: 130+ varying -> out / in)
                        if (stage == "vp" and toks[q][1] in ("out", "varying")) or \
                                (stage == "fp" and toks[q][1] in ("in", "varying")):
                            iface[name] = v
                        q -= 1
                # scan to ';' (or ')' for a for-init), declaring further comma names at depth 0
                k = j + 1
                depth = 0
                while k < n:
                    t = toks[k]
                    if t[0] == "op" and t[1] in "([{":
                        depth += 1
                    elif t[0] == "op" and t[1] in ")]}":
                        if depth == 0:
                            break
                        depth -= 1
                    elif t[0] == "op" and t[1] == ";" and depth == 0:
                        break
                    elif t[0] == "op" and t[1] == "," and depth == 0:
                        if k + 1 < n and toks[k + 1][0] == "id":
                            declare(toks[k + 1][1], t[2])
                    elif t[0] == "id" and not (toks[k - 1][0] == "op" and toks[k - 1][1] == ".") \
                            and not (toks[k - 1][0] == "op" and toks[k - 1][1] == "," and depth == 0):
                        vv = t[1]
                        if not (known(vv) or vv in TYPES or vv in BUILTIN_FUNCS or vv in KEYWORDS
                                or vv in QUALIFIERS or vv in BUILTIN_VARS[stage] or vv in pp_fmacros_holder[0]):
                            err(t[2], "undeclared identifier %r (in the initialiser of %r)" % (vv, name))
                        use_rules(vv, t[2])
                        used.add(vv)
                    k += 1
                i = k
                continue
            i += 1
            continue
        # a plain use
        if not (known(v) or v in BUILTIN_FUNCS or v in BUILTIN_VARS[stage] or v in pp_fmacros_holder[0]):
            if v in BUILTIN_VARS["fp"] or v in BUILTIN_VARS["vp"]:
                err(tag, "%r is not available in a %s" % (v, "vertex shader" if stage == "vp" else "fragment shader"))
            else:
                err(tag, "undeclared identifier %r" % v)
        use_rules(v, tag)
        used.add(v)
        i += 1

    # uniform table cross-check
    for name, typ in uniforms_here.items():
        if not name.startswith("u_"):
            continue
        if name not in uniforms_info:
            err("-", "uniform %s is not in tr_glsl.c uniformsInfo[] - it would never be resolved (silently 0)" % name)
            continue
        want = uniforms_info[name]
        ok = {"GLSL_INT": {"int", "sampler2D", "samplerCube", "sampler2DShadow", "sampler3D", "sampler1D"},
              "GLSL_FLOAT": {"float"}, "GLSL_FLOAT5": {"float"}, "GLSL_VEC2": {"vec2"}, "GLSL_VEC3": {"vec3"},
              "GLSL_VEC4": {"vec4"}, "GLSL_MAT16": {"mat4"}, "GLSL_MAT16_BONEMATRIX": {"mat4"}}.get(want)
        if ok is not None and typ not in ok:
            err("-", "uniform %s is %s in the shader but %s in uniformsInfo[]" % (name, typ, want))

    # a fragment input that is declared but never read is legal (lightall_fp declares var_ColorAmbient for every
    # lit permutation and reads it only with USE_LIGHT_VECTOR); only a READ one must be written by the vertex shader
    if stage == "fp":
        return dict((k, t) for k, t in iface.items() if k in used)
    return iface


pp_fmacros_holder = [set()]
_use_ctx = {}


def use_rules(v, tag):
    stage, version, findings, fname = _use_ctx["stage"], _use_ctx["version"], _use_ctx["findings"], _use_ctx["fname"]
    if version < 130 and v in V130_FUNCS:
        findings.append("%s %s v%d %s: %s() needs #version 130" % (fname, stage, version, tag, v))
    if version < 140 and v in V140_FUNCS:
        findings.append("%s %s v%d %s: %s() needs #version 140" % (fname, stage, version, tag, v))
    if stage == "vp" and v in FRAG_ONLY:
        findings.append("%s %s v%d %s: %s is fragment-only" % (fname, stage, version, tag, v))
    if version >= 150 and stage == "vp" and v in ("texture2D", "textureCube", "textureCubeLod", "texture2DLod",
                                                 "shadow2D"):
        findings.append("%s %s v%d %s: %s() was removed from #version 150 core (the header only redefines it for "
                        "fragment shaders)" % (fname, stage, version, tag, v))


def lint_source(fname, stage, version, header, glsl, uniforms_info, findings, emit=None):
    iface = None
    if '"' in glsl or "\\" in glsl:
        ln = next(n for n, l in enumerate(glsl.split("\n"), 1) if '"' in l or "\\" in l)
        findings.append("%s line %d: a double quote or backslash - stringify.cpp wraps every line in \"...\"" % (fname, ln))
        return None
    full = header + glsl
    try:
        stripped = strip_comments(full)
        hlines = header.count("\n")
        lines = []
        for n_, l in enumerate(stripped.split("\n"), 1):
            tag = ("hdr:%d" % n_) if n_ <= hlines else ("%s:%d" % (fname, n_ - hlines))
            lines.append((tag, l))
        pp = PP()
        active = pp.run(lines)
        pp_fmacros_holder[0] = set(pp.fmacros)
        toks = tokenize(active, pp)
        _use_ctx.update(stage=stage, version=version, findings=findings, fname=fname)
        iface = check(toks, stage, version, uniforms_info, findings, fname)
    except LintError as e:
        findings.append("%s %s v%d: %s" % (fname, stage, version, e))
    if emit is not None:
        key = hashlib.sha1(full.encode()).hexdigest()[:16]
        emit.setdefault(key, (fname, stage, version, full))
    return iface


def parse_uniforms_info(tr_glsl, tr_local):
    m = re.search(r"static uniformInfo_t uniformsInfo\[\]\s*=\s*\{(.*?)\n\};", tr_glsl, re.S)
    body = re.sub(r"//[^\n]*", "", m.group(1))
    rows = re.findall(r'\{\s*"(\w+)"\s*,\s*(\w+)\s*\}', body)
    tl = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", tr_local), flags=re.S)
    end = tl.index("} uniform_t;")
    body2 = tl[tl.rindex("{", 0, end) + 1:end]
    members = [x.split("=")[0].strip() for x in body2.split(",") if x.strip()]
    members = [x for x in members if x != "UNIFORM_COUNT"]
    return rows, members


def generic_variants(enums):
    g = {k: enums[k] for k in enums if k.startswith("GENERICDEF_")}
    out = []
    for i in range(g["GENERICDEF_COUNT"]):
        if (i & g["GENERICDEF_USE_VERTEX_ANIMATION"]) and (i & g["GENERICDEF_USE_BONE_ANIMATION"]):
            continue
        d = []
        if i & g["GENERICDEF_USE_DEFORM_VERTEXES"]:
            d.append("#define USE_DEFORM_VERTEXES\n")
        if i & g["GENERICDEF_USE_TCGEN_AND_TCMOD"]:
            d.append("#define USE_TCGEN\n#define USE_TCMOD\n")
        if i & g["GENERICDEF_USE_VERTEX_ANIMATION"]:
            d.append("#define USE_VERTEX_ANIMATION\n")
        elif i & g["GENERICDEF_USE_BONE_ANIMATION"]:
            d.append("#define USE_BONE_ANIMATION\n#define MAX_GLSL_BONES %d\n" % MAX_BONES)
        if i & g["GENERICDEF_USE_FOG"]:
            d.append("#define USE_FOG\n")
        if i & g["GENERICDEF_USE_RGBAGEN"]:
            d.append("#define USE_RGBAGEN\n")
        out.append(("generic#%d" % i, "".join(d)))
    return out


# programs the base lint already covers with full permutation tables
POST_SKIP = {"lightall", "dlight", "generic", "texturecolor", "pshadow"}

# conditional define builders in tr_glsl.c, mirrored. key = the program name string at the call site.
_SHADOW_SIZES = "#define r_shadowMapSize %f\n#define r_shadowCascadeZFar %f\n"
POST_VARIANTS = {
    # FOGDEF loop: deform x (none | vertex anim | bone anim); vertex+bone never together
    "fogpass": [(lbl, d) for dl, dd in (("", ""), ("deform", "#define USE_DEFORM_VERTEXES\n"))
                for lbl, d in ((dl + "+static", dd), (dl + "+vanim", dd + "#define USE_VERTEX_ANIMATION\n"),
                               (dl + "+bone", dd + "#define USE_BONE_ANIMATION\n#define MAX_GLSL_BONES %d\n" % MAX_BONES))],
    "shadowfill": [("static", ""), ("vanim", "#define USE_VERTEX_ANIMATION\n"),
                   ("bone", "#define USE_BONE_ANIMATION\n#define MAX_GLSL_BONES %d\n" % MAX_BONES)],
    "calclevels4x": [("first", "#define FIRST_PASS\n"), ("rest", "")],
    # r_shadowFilter 0/1/2 x cascade on/off; sizes: the engine defaults and the user's live omconfig values
    "shadowmask": [("f%d_c%d_%d" % (f, c, sz), ("#define USE_SHADOW_FILTER\n" if f >= 1 else "")
                    + ("#define USE_SHADOW_FILTER2\n" if f >= 2 else "")
                    + ("#define USE_SHADOW_CASCADE\n" if c else "")
                    + _SHADOW_SIZES % (sz, cz))
                   for f in (0, 1, 2) for c in (0, 1) for sz, cz in ((1024, 1024.0), (4096, 512.0))],
    "depthBlur": [("%s%s" % ("V" if i & 1 else "H", "" if i & 2 else "+depth"),
                   ("#define USE_VERTICAL_BLUR\n" if i & 1 else "#define USE_HORIZONTAL_BLUR\n")
                   + ("" if i & 2 else "#define USE_DEPTH\n")) for i in range(4)],
    # HZM water pass (tr_hzm_water.c, water_wetness_2026-09-27): [0] plain, [1] the fogShader deform split
    "hzmwater": [("static", ""), ("deform", "#define USE_DEFORM_VERTEXES\n")],
}


def _strip_if0(text):
    out, depth0, stack = [], 0, []
    for line in text.split("\n"):
        t = line.strip()
        if re.match(r"#\s*if\s+0\b", t):
            stack.append(True)
            depth0 += 1
            continue
        if re.match(r"#\s*if", t):
            stack.append(False)
        elif re.match(r"#\s*endif", t) and stack:
            if stack.pop():
                depth0 -= 1
                continue
        out.append("" if depth0 else line)
    return "\n".join(out)


def post_sites(tr_glsl):
    """[(program name, vp file stem, fp file stem, defines or None if conditional, conditional flag)]"""
    t = _strip_if0(re.sub(r"//[^\n]*", "", tr_glsl))
    body = t[t.index("void GLSL_InitGPUShaders"):]
    out = []
    for m in re.finditer(r'GLSL_(?:Try)?InitGPUShader\s*\(\s*&tr\.\w+(?:\[\w+\])?\s*,\s*"(\w+)"\s*,[^;]*?'
                         r'fallbackShader_(\w+?)_vp\s*,\s*fallbackShader_(\w+?)_fp\s*\)', body, re.S):
        name, vp, fp = m.group(1), m.group(2), m.group(3)
        reset = body.rfind("extradefines[0]", 0, m.start())
        win = body[reset:m.start()] if reset >= 0 else ""
        # drop GLES-only blocks: if (qglesMajorVersion ...) { ... }
        win2 = re.sub(r"if\s*\(\s*qglesMajorVersion[^)]*\)[^)]*\)?\s*\{[^}]*\}", "", win)
        conditional = False
        lits = []
        for q in re.finditer(r"Q_strcat\s*\(\s*extradefines\s*,[^;]*;", win2):
            # the statement is guarded when an if/else sits between the previous statement end and it
            prev = max(win2.rfind(";", 0, q.start()), win2.rfind("}", 0, q.start()), win2.rfind("{", 0, q.start()))
            if re.search(r"\bif\s*\(|\belse\b", win2[prev + 1:q.start()]):
                conditional = True
            lit = re.match(r'Q_strcat\s*\(\s*extradefines\s*,[^,]+,\s*"((?:[^"\\]|\\.)*)"\s*\)', q.group(0))
            if lit:
                lits.append(lit.group(1))
            else:
                conditional = True          # a computed (va) define must be mirrored by hand in POST_VARIANTS
        if re.search(r"\bfor\s*\(", win2):
            conditional = True              # built in a loop: the loop index selects the defines
        defines = "".join(l.encode().decode("unicode_escape") for l in lits)
        out.append((name, vp, fp, None if conditional else defines, conditional))
    return out


def text_buffer_size(tr_glsl):
    """(size, how) of GLSL_InitGPUShader's per-stage shader text buffers, or (None, why). Both stages must agree."""
    body = re.search(r"static\s+int\s+GLSL_InitGPUShader\s*\([^)]*\)\s*\{(.*?)\n\}", tr_glsl, re.S)
    if not body:
        return None, "GLSL_InitGPUShader not found in tr_glsl.c"
    sizes = {}
    for stage in ("vp", "fp"):
        m = re.search(r"\bchar\s+%sCode\s*\[\s*(\w+)\s*\]" % stage, body.group(1))
        if not m:
            return None, "char %sCode[...] not found in GLSL_InitGPUShader" % stage
        tok = m.group(1)
        if not tok.isdigit():
            d = re.search(r"^\s*#\s*define\s+%s\s+(\d+)\s*$" % re.escape(tok), tr_glsl, re.M)
            if not d:
                return None, "%sCode[%s]: no '#define %s <decimal>' in tr_glsl.c" % (stage, tok, tok)
            tok = d.group(1)
        sizes[stage] = int(tok)
    if sizes["vp"] != sizes["fp"]:
        return None, "vpCode[%d] and fpCode[%d] differ - the gate assumes one size" % (sizes["vp"], sizes["fp"])
    return sizes["fp"], "ok"


BUF_WARN = 0.95


def run(glsl_dir, gl2_dir, emit_dir=None, quiet=False, post=False):
    tr_glsl = open(os.path.join(gl2_dir, "tr_glsl.c"), encoding="latin-1").read()
    tr_local = open(os.path.join(gl2_dir, "tr_local.h"), encoding="latin-1").read()
    findings = []

    drift = check_header_pinned(tr_glsl)
    for d in drift:
        findings.append("header drift: GLSL_GetShaderHeader appends %r, which this tool does not model - update "
                        "KNOWN_HEADER_LITERALS and build_header()" % d)
    bufsize, why = text_buffer_size(tr_glsl)
    if bufsize is None:
        findings.append("text buffer: %s (the size gate cannot run - bug-3179)" % why)
    bufmax = {}             # stem -> (largest header + source + NUL, label, version)
    enums = parse_enums(tr_local)
    for k, want in (("LIGHTMAP", "LIGHTDEF_USE_LIGHTMAP"), ("LIGHT_VECTOR", "LIGHTDEF_USE_LIGHT_VECTOR"),
                    ("LIGHT_VERTEX", "LIGHTDEF_USE_LIGHT_VERTEX"), ("TYPE_MASK", "LIGHTDEF_LIGHTTYPE_MASK"),
                    ("ENTITY_VERTEX", "LIGHTDEF_ENTITY_VERTEX_ANIMATION"), ("TCGEN", "LIGHTDEF_USE_TCGEN_AND_TCMOD"),
                    ("PARALLAX", "LIGHTDEF_USE_PARALLAXMAP"), ("SHADOWMAP", "LIGHTDEF_USE_SHADOWMAP"),
                    ("ENTITY_BONE", "LIGHTDEF_ENTITY_BONE_ANIMATION"), ("COUNT", "LIGHTDEF_COUNT")):
        if enums.get(want) != LIGHTDEF[k]:
            findings.append("LIGHTDEF drift: %s is %s in tr_local.h, this tool models %d" % (want, enums.get(want),
                                                                                           LIGHTDEF[k]))
    rows, members = parse_uniforms_info(tr_glsl, tr_local)
    if len(rows) != len(members):
        findings.append("uniformsInfo[] has %d rows but uniform_t has %d members (vet F10: order is by index)"
                        % (len(rows), len(members)))
    uniforms_info = dict(rows)
    for (row, mem) in zip(rows, members):
        # u_ModelViewProjectionMatrix <-> UNIFORM_MODELVIEWPROJECTIONMATRIX: compare case-folded letters
        if re.sub(r"[^a-z0-9]", "", row[0][2:].lower()) != re.sub(r"[^a-z0-9]", "", mem[len("UNIFORM_"):].lower()):
            findings.append("uniformsInfo[] row %r sits at the index of %s - the table is out of order" % (row[0], mem))
            break

    src = {}

    def load(name):
        if name not in src:
            raw = open(os.path.join(glsl_dir, name + ".glsl"), "rb").read()
            src[name] = raw.decode("latin-1").replace("\r\n", "\n")
        return src[name]
    for name in ("lightall_vp", "lightall_fp", "dlight_vp", "dlight_fp", "generic_vp", "generic_fp",
                 "texturecolor_vp", "texturecolor_fp", "pshadow_vp", "pshadow_fp"):
        load(name)

    emit = {} if emit_dir else None
    count = 0
    seen = set()
    jobs = []
    for label, c in CONFIGS:
        for i in range(LIGHTDEF["COUNT"]):
            d = lightall_defines(i, c)
            if d is None:
                continue
            jobs.append(("lightall", "lightall[%s]#%d" % (label, i), d, bool(c["pbr"]), bool(c["cube"])))
    for i in range(2):
        jobs.append(("dlight", "dlight#%d" % i, "#define USE_DEFORM_VERTEXES\n" if i else "", False, False))
    for label, d in generic_variants(enums):
        jobs.append(("generic", label, d, False, False))
    jobs.append(("texturecolor", "texturecolor", "", False, False))
    # the pshadow receive program: built once, with exactly these defines (tr_glsl.c GLSL_InitGPUShaders)
    jobs.append(("pshadow", "pshadow", "#define USE_PCF\n#define USE_DISCARD\n", False, False))
    stems = {}
    if post:
        sites = post_sites(tr_glsl)
        seen_names = set()
        for name, vp, fp, defines, cond in sites:
            if name in POST_SKIP:
                continue
            seen_names.add(name)
            stems[name] = (vp + "_vp", fp + "_fp")
            for stem in stems[name]:
                if not os.path.exists(os.path.join(glsl_dir, stem + ".glsl")):
                    findings.append("post: %s uses %s.glsl, which does not exist in %s" % (name, stem, glsl_dir))
            if cond:
                if name not in POST_VARIANTS:
                    findings.append("post: %s builds its defines under a condition and has no POST_VARIANTS entry - "
                                    "mirror the tr_glsl.c loop in glsl_variant_lint.py" % name)
                    continue
                for lbl, d in POST_VARIANTS[name]:
                    jobs.append((name, "%s[%s]" % (name, lbl), d, False, False))
            else:
                jobs.append((name, name, defines, False, False))
        for name in POST_VARIANTS:
            if name not in seen_names:
                findings.append("post: POST_VARIANTS has %s but tr_glsl.c no longer builds it" % name)
    pairs = []

    for prog, label, defines, pbr, cube in jobs:
        for v in VERSIONS:
            key = (prog, v, defines, pbr, cube)
            if key in seen:
                continue
            seen.add(key)
            ifaces = {}
            names = {}
            for stage in ("vp", "fp"):
                stem = stems[prog][0 if stage == "vp" else 1] if prog in stems else "%s_%s" % (prog, stage)
                header = build_header(v, stage, defines, enums, pbr=pbr, cube=cube)
                before = len(findings)
                need = len((header + load(stem)).encode("latin-1")) + 1      # + the NUL the copy writes
                if need > bufmax.get(stem, (0,))[0]:
                    bufmax[stem] = (need, label, v)
                names[stage] = (stem, hashlib.sha1((header + load(stem)).encode()).hexdigest()[:16])
                ifaces[stage] = lint_source("%s.glsl" % stem, stage, v, header,
                                            load(stem), uniforms_info, findings, emit)
                if len(findings) > before:
                    findings.insert(before, "-- in %s (%s, #version %d):" % (label, stage, v))
                count += 1
            if post:
                pairs.append(dict(label=label, version=v,
                                  vert="%s_v%d_%s.vert" % (names["vp"][0], v, names["vp"][1]),
                                  frag="%s_v%d_%s.frag" % (names["fp"][0], v, names["fp"][1])))
            # the link: every varying the fragment shader declares must be a vertex output of the same type
            if ifaces.get("vp") is not None and ifaces.get("fp") is not None:
                for name, typ in sorted(ifaces["fp"].items()):
                    if name not in ifaces["vp"]:
                        findings.append("%s (#version %d): varying %s is read by %s_fp but never written by %s_vp - a "
                                        "link error" % (label, v, name, prog, prog))
                    elif ifaces["vp"][name] != typ:
                        findings.append("%s (#version %d): varying %s is %s in %s_vp but %s in %s_fp - a link error"
                                        % (label, v, name, ifaces["vp"][name], prog, typ, prog))

    if bufsize:
        for stem, (need, label, v) in sorted(bufmax.items()):
            if need > bufsize:
                findings.append("text buffer: %s.glsl needs %d bytes (header + source + NUL, worst %s #version %d) but "
                                "GLSL_InitGPUShader's buffer is %d - GLSL_LoadGPUShaderText refuses it and every gl2 "
                                "client dies at start-up (bug-3179)" % (stem, need, label, v, bufsize))
        if not quiet:
            worst = max(bufmax.items(), key=lambda kv: kv[1][0]) if bufmax else None
            if worst:
                print("text buffer: largest %s.glsl %d / %d bytes (%.0f%%)" % (worst[0], worst[1][0], bufsize,
                                                                             100.0 * worst[1][0] / bufsize))
            for stem, (need, label, v) in sorted(bufmax.items()):
                if bufsize >= need > BUF_WARN * bufsize:
                    print("WARN text buffer: %s.glsl at %d of %d bytes (%.1f%%) - raise HZM_GLSL_TEXT_MAX in tr_glsl.c "
                          "before it overflows" % (stem, need, bufsize, 100.0 * need / bufsize))
    if emit_dir:
        os.makedirs(emit_dir, exist_ok=True)
        for key, (fname, stage, v, full) in sorted(emit.items()):
            ext = "vert" if stage == "vp" else "frag"
            with open(os.path.join(emit_dir, "%s_v%d_%s.%s" % (fname[:-5], v, key, ext)), "w", newline="\n") as f:
                f.write(full)
        if post:
            import json
            with open(os.path.join(emit_dir, "pairs.json"), "w", newline="\n") as f:
                json.dump(pairs, f, indent=1)
    if not quiet:
        print("glsl_variant_lint: %d unique rebuilt sources (%d lightall/dlight/generic/texturecolor/pshadow%s jobs x "
              "vp/fp x #version %s), uniformsInfo %d rows / uniform_t %d members"
              % (count, len(jobs), "/post" if post else "", "/".join(map(str, VERSIONS)), len(rows), len(members)))
        if emit_dir:
            print("emitted %d unique sources to %s" % (len(emit), emit_dir))
    return findings, count


def selftest(gl2_dir):
    """the tool must FAIL on deliberately broken copies and PASS on the tree"""
    glsl_dir = os.path.join(gl2_dir, "glsl")
    findings, n = run(glsl_dir, gl2_dir, quiet=True)
    if findings:
        print("SELFTEST: the pristine tree does not pass:\n  " + "\n  ".join(findings[:40]))
        return False
    print("SELFTEST pristine: PASS (%d sources)" % n)
    mutations = [
        ("lightall_fp.glsl", "float NL, NH, NE, EH, attenuation;", "float NL, NH, NE, EH;",
         "undeclared identifier 'attenuation'"),
        ("lightall_vp.glsl", "uniform float  u_LightRadius;", "uniform float  u_LightRadiu;",
         "undeclared identifier 'u_LightRadius'"),
        ("dlight_fp.glsl", "gl_FragColor.a = alpha;", "gl_FragColor.a = alpha", "missing its ';'"),
        ("dlight_vp.glsl", "var_Color = u_Color * dlightmod;", "var_Color = u_Color * dlightmod * texture2D(u_Color);",
         "removed from #version 150"),
    ]
    # Phase S [2026-09-26]: the spot-cone code must be caught too (a typo in a uniform NAME compiles and is silently 0)
    if "u_HzmLightSpot" in open(os.path.join(glsl_dir, "lightall_fp.glsl"), "rb").read().decode("latin-1"):
        mutations += [
            ("lightall_fp.glsl", "uniform vec4      u_HzmLightSpot;", "uniform vec4      u_HzmLightSpott;",
             "u_HzmLightSpott is not in tr_glsl.c uniformsInfo"),
            ("lightall_vp.glsl", "#if defined(USE_LIGHT_VECTOR) && defined(USE_FAST_LIGHT)",
             "#if defined(USE_LIGHT_VECTOR) && !defined(USE_FAST_LIGHT)", "undeclared identifier 'HzmSpotCone'"),
            ("dlight_fp.glsl", "varying vec3      var_HzmSpotDir;", "varying vec3      var_HzmSpotDirection;",
             "undeclared identifier 'var_HzmSpotDir'"),
            ("dlight_vp.glsl", "varying vec3   var_HzmSpotDir;", "varying vec4   var_HzmSpotDir;",
             "varying var_HzmSpotDir is vec4 in dlight_vp but vec3 in dlight_fp"),
        ]
    # S4 [2026-09-26]: the spot-shadow mask in pshadow_fp must be caught too
    if "u_HzmPshadowSpot" in open(os.path.join(glsl_dir, "pshadow_fp.glsl"), "rb").read().decode("latin-1"):
        mutations += [
            ("pshadow_fp.glsl", "uniform vec4      u_HzmPshadowSpot;", "uniform vec4      u_HzmPshadowSpott;",
             "u_HzmPshadowSpott is not in tr_glsl.c uniformsInfo"),
            ("pshadow_fp.glsl", "float spotMask = HzmSpotShadowMask(var_Position);",
             "float spotMask = HzmSpotShadowMask(var_Positio);", "undeclared identifier 'var_Positio'"),
        ]
    mutations += [
        ("lightall_fp.glsl", "vec4 diffuse = texture2D(u_DiffuseMap, texCoords);",
         "vec4 diffuse = texture2D(u_DiffuseMap, texCoords) * \"x\";", "double quote"),
    ]
    ok = True
    # bug-3179: the text-buffer gate must fire on a tr_glsl.c whose buffer is smaller than the largest lightall_fp
    tmpg = tempfile.mkdtemp(prefix="glsllint_buf_")
    try:
        for f in ("tr_glsl.c", "tr_local.h"):
            shutil.copy(os.path.join(gl2_dir, f), tmpg)
        tg = open(os.path.join(tmpg, "tr_glsl.c"), "rb").read().decode("latin-1")
        size, _ = text_buffer_size(tg)
        tg2 = re.sub(r"(\bchar\s+(?:vp|fp)Code\s*\[)\s*\w+\s*(\])", r"\g<1>20000\2", tg)
        open(os.path.join(tmpg, "tr_glsl.c"), "wb").write(tg2.encode("latin-1"))
        f3, _ = run(glsl_dir, tmpg, quiet=True)
        hit = [x for x in f3 if x.startswith("text buffer:")]
        if size is None or not hit:
            print("SELFTEST text buffer: a 20000-byte buffer was NOT caught (parsed size %s)" % size)
            ok = False
        else:
            print("SELFTEST text buffer (20000 bytes): FAIL as it must - %s" % hit[0][:120])
    finally:
        shutil.rmtree(tmpg, ignore_errors=True)
    for fname, find, repl, expect in mutations:
        tmp = tempfile.mkdtemp(prefix="glsllint_")
        try:
            for f in os.listdir(glsl_dir):
                if f.endswith(".glsl"):
                    shutil.copy(os.path.join(glsl_dir, f), tmp)
            p = os.path.join(tmp, fname)
            t = open(p, "rb").read().decode("latin-1")
            assert t.count(find) == 1, "selftest anchor %r" % find
            open(p, "wb").write(t.replace(find, repl).encode("latin-1"))
            f2, _ = run(tmp, gl2_dir, quiet=True)
            hit = [x for x in f2 if expect in x]
            if not f2 or not hit:
                print("SELFTEST broken copy (%s: %r): NOT caught (%d findings)" % (fname, repl, len(f2)))
                ok = False
            else:
                print("SELFTEST broken copy (%s): FAIL as it must - %d findings, e.g. %s" % (fname, len(f2), hit[0]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return ok


BASELINE = os.path.join(HERE, "glsl_post_baseline.json")


def _norm(f):
    """a finding without line numbers, so an unrelated edit above a known finding does not un-allowlist it"""
    return re.sub(r":\d+", ":N", re.sub(r"line \d+", "line N", f))


def post_selftest(gl2_dir):
    """--post must catch a typo planted in a post-FX shader, and an unknown conditional site"""
    glsl_dir = os.path.join(gl2_dir, "glsl")
    base, _ = run(glsl_dir, gl2_dir, quiet=True, post=True)
    base_n = set(_norm(x) for x in base)
    ok = True
    for fname, find, repl, expect in (
            ("dof_fp.glsl", "float coc = clamp(", "float coc = clamq(", "clamq"),
            ("sharpen_fp.glsl", "amp = sqrt(amp);", "amp = sqrt(ampx);", "undeclared identifier 'ampx'"),
            ("bloom_blur_fp.glsl", "uniform vec2      u_InvTexRes;", "uniform vec2      u_InvTexRez;",
             "u_InvTexRez")):
        tmp = tempfile.mkdtemp(prefix="glsllint_post_")
        try:
            for f in os.listdir(glsl_dir):
                if f.endswith(".glsl"):
                    shutil.copy(os.path.join(glsl_dir, f), tmp)
            pth = os.path.join(tmp, fname)
            t = open(pth, "rb").read().decode("latin-1")
            if t.count(find) != 1:
                print("POST SELFTEST anchor missing in %s: %r (update the selftest)" % (fname, find))
                ok = False
                continue
            open(pth, "wb").write(t.replace(find, repl).encode("latin-1"))
            f2, _ = run(tmp, gl2_dir, quiet=True, post=True)
            new = [x for x in f2 if _norm(x) not in base_n and expect in x]
            if not new:
                print("POST SELFTEST (%s): NOT caught" % fname)
                ok = False
            else:
                print("POST SELFTEST (%s): caught - %s" % (fname, new[0]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    saved = dict(POST_VARIANTS)
    try:
        POST_VARIANTS.pop("depthBlur")
        f3, _ = run(glsl_dir, gl2_dir, quiet=True, post=True)
        if any("depthBlur builds its defines under a condition" in x for x in f3):
            print("POST SELFTEST (unknown conditional site): caught")
        else:
            print("POST SELFTEST (unknown conditional site): NOT caught")
            ok = False
    finally:
        POST_VARIANTS.clear()
        POST_VARIANTS.update(saved)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glsl-dir", default=os.path.join(GL2, "glsl"))
    ap.add_argument("--gl2-dir", default=GL2)
    ap.add_argument("--emit", default=None, help="write every unique rebuilt source here (for glslangValidator)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--post", action="store_true", help="also lint every other GLSL_InitGPUShader program (post-FX)")
    ap.add_argument("--write-baseline", action="store_true", help="with --post: record today's findings as KNOWN")
    a = ap.parse_args()
    if a.selftest:
        ok = selftest(a.gl2_dir)
        if a.post:
            ok = post_selftest(a.gl2_dir) and ok
        sys.exit(0 if ok else 1)
    findings, n = run(a.glsl_dir, a.gl2_dir, emit_dir=a.emit, post=a.post)
    if a.post:
        import json
        if a.write_baseline:
            with open(BASELINE, "w", newline="\n") as f:
                json.dump(sorted(set(_norm(x) for x in findings)), f, indent=1)
            print("wrote %d known findings to %s" % (len(set(_norm(x) for x in findings)), BASELINE))
            sys.exit(0)
        known = set(json.load(open(BASELINE))) if os.path.exists(BASELINE) else set()
        kn = [x for x in findings if _norm(x) in known]
        findings = [x for x in findings if _norm(x) not in known]
        if kn:
            print("KNOWN (allowlisted in %s, not failing): %d" % (os.path.basename(BASELINE), len(kn)))
    if findings:
        print("FINDINGS (%d):" % len(findings))
        for f in findings[:200]:
            print("  " + f)
        sys.exit(1)
    print("PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
