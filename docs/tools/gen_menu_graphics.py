#!/usr/bin/env python
"""Generate the COOP POST-PROCESSING sheets and the ADVANCED GRAPHICS sheet from ONE table.

WHY THIS EXISTS
[user 2026-09-14] "we have built menus (advanced gfx and post fx) - those actually need an overhaul, they
look ugly. What you did with Coop Settings menu looks way better. Make sure everything in those is wired
correctly." The old ui/coop_postfx*.urc and ui/advanced_graphics.urc were the pre-redesign dark-panel /
courier-16 style, hand-authored, with drift between the DEFAULTS button (coop_fxdefaults.cfg) and the
actually-shipped look (coop_defaults.cfg). This generator rebuilds all of them in the same two-column
manila-folder style as ui/coop_settings.urc (docs/tools/gen_menu_fieldsettings.py) - it imports that
generator's proven widget/gate helpers - and derives the DEFAULTS button, the rust slider tick marks, and
the shipped seeds from ONE source so they cannot disagree.

SOURCE OF TRUTH FOR DEFAULTS. coop_defaults.cfg (the archived `seta` a fresh profile starts from) is the
truth. This generator READS it: every menu control's shipped default is the coop_defaults value if one is
seeded there, else the engine-registered fallback in the table below. It then WRITES:
    coop_mod/cfg/coop_fxdefaults.cfg   - the post-FX DEFAULTS button (mirrors coop_defaults exactly)
    coop_mod/cfg/coop_gfxdefaults.cfg  - the advanced-graphics DEFAULTS button (new)
so pressing DEFAULTS restores precisely the shipping look. It does NOT rewrite coop_defaults.cfg (treated
as truth); `check` reports any menu cvar not seeded there (advisory) and any fxdefaults/coop_defaults
mismatch (fatal).

    python docs/tools/gen_menu_graphics.py check   # regenerate in memory, byte-compare, run every gate
    python docs/tools/gen_menu_graphics.py build    # write the files, then run the gates

RENDERER. The mod ships gl2 (renderer_opengl2 - confirm from the qconsole banner, TRAPS T7). Every linkcvar
is wired to the cvar the gl2 renderer (or cgame) registers, verified by the registration gate below. gl1-only
r_ppSunShafts/Intensity are dropped (dead on gl2); gl2 god-rays are r_drawSunRays. LATCH cvars that a live
vid_restart from an open menu would crash on (bug-1181) are marked "*" and take effect on the next map load;
the post-FX APPLY is a plain close. Advanced-graphics APPLY runs ui_checkrestart (bug-1145 made that path
safe for the gl1-style latched knobs).

GATES (all fatal unless noted): byte drift . text fit (live RitualFont metrics) . canvas bounds . paper
margins . interactive overlaps . a Label declared after a control it covers . unique names . brace/quote
balance . ASCII only . every linkcvar registered in the engine or read by a script (the wire audit) . every
slider range contains its shipped default . DEFAULTS cfg == coop_defaults seed for every seeded menu cvar .
CLOSE/return buttons do not fall through onto the Video Options menu underneath (advisory) . unseeded menu
cvars listed (advisory).
"""
import io
import os
import re
import sys

import gen_menu_fieldsettings as fs
# [2026-09-25] this sheet keeps its own toggle pitch: gen_menu_fieldsettings went 24 -> 22 (Hide Objective Cards) and
# sharing its T_PITCH silently re-spaced every graphics menu by 2px on the next build.
T_PITCH = 24


# ---------------------------------------------------------------- workspace root (worktree-safe)
def _find_root():
    """The mod tree (hzm-mohaa-coop-mod) is untracked and lives only at the workspace root, which is not
    inside a git worktree. Walk up from this file and from CWD to find it, so the generator runs from either."""
    for start in (os.path.dirname(os.path.abspath(__file__)), os.path.abspath(os.getcwd())):
        d = start
        for _ in range(8):
            if os.path.isdir(os.path.join(d, "hzm-mohaa-coop-mod")):
                return d
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd
    return fs.ROOT


ROOT = _find_root()
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
ENG = os.path.join(ROOT, "openmohaa-hzm", "code")
# fs.Font / fs.rd / fs.urc_resources read fs's module globals at call time; point them at the real tree.
fs.ROOT, fs.MOD, fs.ENG = ROOT, MOD, ENG

PFX_URC = [os.path.join(MOD, "ui", "coop_postfx%s.urc" % ("" if i == 1 else i)) for i in range(1, 5)]
ADV_URC = os.path.join(MOD, "ui", "advanced_graphics.urc")
FX_CFG = os.path.join(MOD, "coop_mod", "cfg", "coop_fxdefaults.cfg")
GFX_CFG = os.path.join(MOD, "coop_mod", "cfg", "coop_gfxdefaults.cfg")
DEFAULTS_CFG = os.path.join(MOD, "coop_defaults.cfg")
VIDEO_URC = os.path.join(MOD, "ui", "video options.urc")

S, T = fs.S, fs.T


def P(display_cvar, set_cvars, options, default, aliases=(), test=False):
    """A discrete pulldown spec. options = [(label, value) or (label, value, extra_cmd), ...]: each pick runs
    `seta <cv> <value>` for every set_cvar, then extra_cmd if given. aliases = [(value, label)] are READOUT-only
    linkstrings for values a pick no longer writes (an archived value from an older menu), so the readout
    never goes blank.
    test=True: a TEST row for a feature still behind its AUTO define. Picks write `set`, never `seta`, so the choice
    resets every launch and a saved config can never pin it (TRAPS T7); the row is left out of every DEFAULTS cfg,
    the coop_defaults seed audit and the unseeded advisory (it must never be seeded)."""
    return dict(type="pulldown", display_cvar=display_cvar, set_cvars=set_cvars, options=options, default=default,
                aliases=list(aliases), test=test)


def is_test(spec):
    return bool(spec.get("test"))


def opt_extra(o):
    return o[2] if len(o) > 2 else None


# ---------------------------------------------------------------- THE TABLES
# item = (key, kind, label, cvar, spec). kind in {toggle, slider, pulldown}. A trailing " *" in a label marks
# a LATCH cvar that applies after a restart (post-FX pages only; see the page footnote). The shipped default in
# each spec is a FALLBACK - the real default is read from coop_defaults.cfg when seeded there.

# [lightning plan 2.3 / D6, applied by docs/proposals/graphics_menu_2026-09-27/staged_lightning_row] LIGHTNING:
# a player preference read live every frame by cgame (cg_hzmlightning.c). Reduced flashing = one soft pulse per strike,
# no flicker or bolts; Off = thunder only. The 3-flashes-per-second limiter is always on and is not a setting.
LIGHTNING = P("cg_hzmLightningMode", ["cg_hzmLightningMode"],
              [("Normal", 1), ("Reduced flashing", 2), ("Off (thunder only)", 0)], 1)

PFX_PAGES = [
    ("coop_postfx", "POST-PROCESSING", "IMAGE", "coop_postfx2", None, [
        (0, "POST-PROCESSING", [
            ("Master", "toggle", "Post-Processing", "r_postProcess", T(1)),
        ]),
        (0, "BLOOM", [
            ("Bloom", "toggle", "Bloom", "r_ppBloom", T(1)),
            ("BloomMode", "toggle", "Exposure-Aware", "r_ppBloomMode", T(1)),
            ("BloomThr", "slider", "Threshold", "r_ppBloomThreshold", S("float", 0, 1, 0.02, 0.62, "DARK", "BRIGHT")),
            ("BloomInt", "slider", "Intensity", "r_ppBloomIntensity", S("float", 0, 3, 0.05, 0.55, "SUBTLE", "STRONG")),
            ("BloomKnee", "slider", "Soft Knee", "r_ppBloomKnee", S("float", 0, 0.5, 0.02, 0.1, "HARD", "SOFT")),
        ]),
        (1, "SHARPEN & AA", [
            ("Sharpen", "toggle", "Sharpen", "r_ppSharpen", T(1)),
            ("SharpAmt", "slider", "Sharpen Amt", "r_ppSharpenAmount", S("float", 0, 1, 0.05, 0.78, "LOW", "HIGH")),
            ("FXAA", "toggle", "FXAA (Edge AA)", "r_ppFXAA", T(1)),
        ]),
        (1, "RESOLUTION", [
            ("RScale", "slider", "Render Scale *", "r_renderScale", S("float", 0.5, 2, 0.05, 1.0, "PERF", "SSAA")),
            ("Upscale", "toggle", "FSR Upscale", "r_upscaleFilter", T(1)),
            ("FSRSharp", "slider", "FSR Sharpness", "r_fsrSharpness", S("float", 0, 1, 0.05, 0.25, "SOFT", "CRISP")),
            ("SoftPart", "toggle", "Soft Particles *", "r_softParticles", T(1)),
        ]),
    ]),
    ("coop_postfx2", "POST-PROCESSING", "COLOR", "coop_postfx3", "coop_postfx", [
        (0, "COLOR GRADE", [
            ("Tone", "toggle", "Tonemap (ACES)", "r_ppTonemap", T(1)),
            ("Exp", "slider", "Exposure", "r_ppExposure", S("float", 0.2, 2, 0.02, 0.7, "DARK", "BRIGHT")),
            ("Con", "slider", "Contrast", "r_ppContrast", S("float", 0.5, 1.5, 0.02, 1.0, "FLAT", "PUNCHY")),
            ("Sat", "slider", "Saturation", "r_ppSaturation", S("float", 0, 2, 0.02, 1.08, "GRAY", "VIVID")),
            ("Temp", "slider", "Temperature", "r_ppTemp", S("float", -0.3, 0.3, 0.02, 0, "COOL", "WARM")),
            ("Grade", "slider", "Grade Preset", "r_ppGrade", S("integer", 0, 4, 1, 0, "OFF", "BLEACH")),
            ("MapGrade", "toggle", "Per-Map Grade", "r_ppMapGradeOn", T(1)),
        ]),
        (1, "AMBIENT OCCLUSION", [
            ("SSAO", "toggle", "Ambient Occ. *", "r_ppSSAO", T(1)),
            ("SRad", "slider", "AO Radius", "r_ppSSAORadius", S("float", 2, 48, 1, 21, "TIGHT", "WIDE")),
            ("SInt", "slider", "AO Intensity", "r_ppSSAOIntensity", S("float", 0, 3, 0.05, 0.62, "LOW", "HIGH")),
            ("SBias", "slider", "AO Bias", "r_ppSSAOBias", S("float", 0.1, 4, 0.05, 1.46, "LOW", "HIGH")),
            ("SDA", "toggle", "AO Edge-Aware", "r_ppSSAODepthAware", T(1)),
        ]),
    ]),
    ("coop_postfx3", "POST-PROCESSING", "ATMOSPHERE", "coop_postfx4", "coop_postfx2", [
        (0, "ATMOSPHERE", [
            ("Heat", "toggle", "Heat Haze", "r_ppHeatHaze", T(1)),
            ("HeatAmt", "slider", "Heat Amount", "r_ppHeatAmount", S("float", 0, 2, 0.1, 1.0, "LOW", "HIGH")),
            ("Rain", "toggle", "Rain On Lens", "r_ppRainDrops", T(1)),
            ("RainAmt", "slider", "Rain Amount", "r_ppRainAmount", S("float", 0, 2, 0.1, 0.5, "LIGHT", "HEAVY")),
            ("Uw", "toggle", "Underwater FX", "r_ppUnderwaterFx", T(1)),
            ("Lightning", "pulldown", "Lightning", "cg_hzmLightningMode", LIGHTNING),
            ("MuzR", "slider", "Muzzle Radius", "r_ppMuzzleRadius", S("float", 0.02, 0.6, 0.02, 0.1, "SMALL", "BIG")),
        ]),
        (1, "DEPTH OF FIELD", [
            ("DoF", "toggle", "Depth of Field *", "r_ppDoF", T(1)),
            ("DFoc", "slider", "Focus (0=auto)", "r_ppDoFFocus", S("float", 0, 4000, 25, 0, "NEAR", "FAR")),
            ("DRng", "slider", "Sharp Range", "r_ppDoFRange", S("float", 100, 4000, 50, 2256, "THIN", "DEEP")),
            ("DInt", "slider", "Blur Amount", "r_ppDoFIntensity", S("float", 0, 1, 0.05, 0.55, "LOW", "HIGH")),
        ]),
        # [2026-09-27 Phase 1] Sun Rays row hidden (ao_sunrays_2026-09-27 D3): no coop map shows a visible sun under
        # our fog, and the rays glowed as a square on fogged skies. Rays stay off; r_drawSunRays is PINNED to 0.
        (1, "SUN", [
            ("SunShadow", "toggle", "Sun Shadows *", "r_sunShadows", T(1)),
        ]),
    ]),
    ("coop_postfx4", "POST-PROCESSING", "COMBAT", None, "coop_postfx3", [
        (0, "COMBAT FEEDBACK", [
            ("LowHP", "toggle", "Low-Health FX", "r_ppLowHealth", T(1)),
            ("LowStart", "slider", "Onset", "r_ppLowHealthStart", S("float", 0.05, 1, 0.05, 0.5, "LATE", "EARLY")),
            ("LowBeat", "slider", "Heartbeat", "r_ppLowHealthBeat", S("float", 0, 1, 0.05, 0.49, "STEADY", "THROB")),
            ("LowAmt", "slider", "Strength", "r_ppLowHealthAmount", S("float", 0, 2, 0.05, 0.18, "SUBTLE", "STRONG")),
        ]),
        (0, "SUPPRESSION & HITS", [
            ("Supp", "toggle", "Suppression FX", "r_ppSuppression", T(1)),
            ("SuppAmt", "slider", "Suppress Str", "r_ppSuppressAmount", S("float", 0, 2, 0.05, 0.55, "LOW", "HIGH")),
            ("HitBlood", "toggle", "On-Hit Blood", "r_ppHitBlood", T(1)),
            ("HitAmt", "slider", "Blood Str", "r_ppHitAmount", S("float", 0, 2, 0.1, 1.0, "LOW", "HIGH")),
        ]),
        (1, "CINEMATIC", [
            ("Chrom", "toggle", "Chromatic Ab.", "r_ppChromaticAberration", T(0)),
            ("ChromAmt", "slider", "Chromatic Amt", "r_ppChromaticAberrationAmount", S("float", 0, 2, 0.05, 0.35, "LOW", "HIGH")),
            ("Grain", "toggle", "Film Grain", "r_ppFilmGrain", T(0)),
            ("GrainAmt", "slider", "Grain Amount", "r_ppFilmGrainAmount", S("float", 0, 2, 0.05, 0.35, "LOW", "HIGH")),
        ]),
    ]),
]

# [2026-09-27 graphics menu Phase 1, bug-3119 / D1] ANTI-ALIASING = Off / Smooth edges (the FXAA post pass) until
# the gfx MSAA flip. The old Off/2x/4x/8x pulldown drew the bug-1298 halos above Off, and it also wrote
# r_ext_multisample: window-backbuffer MSAA, which gl2 blits its FBO into and clamps to 4 (tr_init.c:1486). The
# row now writes ONLY r_ppFXAA; both MSAA cvars are pinned 0 once by coop_gfxfix1.cfg (PINNED below). The gfx
# flip brings Auto/2x/4x/8x back on its own new cvar, r_msaa. r_ppFXAA is the same cvar as the Post-FX "FXAA"
# toggle, so the two rows always agree.
AA = P("r_ppFXAA", ["r_ppFXAA"], [("Off", 0), ("Smooth edges", 1)], 1)

# [2026-10-04 gfx flip, shadows plan P6.2] MULTISAMPLE ANTI-ALIASING is back, on its own cvar. gl2 renders the 3D
# scene into multisample textures with shader resolves (renderergl2/tr_msaa.c: min+max depth, tone-exact colour,
# alpha-to-coverage for cutouts, centroid lightmap coords), so the bug-1298 halos of the old path are gone.
# r_msaa is ARCHIVE, default -1 = Auto (8x on >=10 GB VRAM when the buffers fit 5 % of it, 4x on 4-10 GB or unknown,
# 2x below 4 GB, off on Intel iGPU / no ARB_texture_multisample / GLSL < 1.50 / render scale >= 1.5), decided at
# every R_Init and never written back. It is READ AT R_INIT, so a pick shows from the next map load or video restart
# (APPLY does not restart for it: not LATCH). Writes ONLY r_msaa (bug-1152); the old r_ext_multisample /
# r_ext_framebuffer_multisample stay PINNED 0. gl1 ignores r_msaa (accepted: gl1 has no menu MSAA).
MSAA = P("r_msaa", ["r_msaa"], [("Auto", -1), ("Off", 0), ("2x", 2), ("4x", 4), ("8x", 8)], -1)

# [D3] FRAME RATE LIMIT. com_maxfps is paced in WHOLE milliseconds (qcommon/common.c:2330, minMsec = 1000/maxfps),
# so only these values mean what they say: 62 = 16 ms, 142 = 7 ms, 166 = 6 ms, 200 = 5 ms, 250 = 4 ms; 0 = uncapped.
# The old autoexec force of 180 really ran at 200, hence the 200 default (no change in pace for anyone).
# The player's pick is ALSO stored in the alias coop_fpsRestore, which autoexec.cfg runs at every launch: hosting
# caps a session at 125 (coop_mod/start_server.cfg, bug-1673 host pacing) and that 125 lands in the saved config,
# but it can no longer outlive the session. An alias, not a cvar, on purpose: the server filter has no `alias`
# verb and layer 2 drops a server line that names one (qcommon/cmd_filter.c ~485), so unlike a vstr'd cvar a
# hostile server cannot plant a command in it - no SEC2 guard-list (cmd_srvguard.h) entry, no engine change.
FPS_CHOICES = [("62 fps", 62), ("125 fps", 125), ("142 fps", 142), ("166 fps", 166), ("200 fps", 200),
               ("250 fps", 250), ("Unlimited", 0)]
FPS = P("com_maxfps", ["com_maxfps"],
        [(lab, v, "alias coop_fpsRestore seta com_maxfps %d" % v) for lab, v in FPS_CHOICES], 200)

# [D4] MENU LAYOUT = ui_menuCenter (uilib/uiwidget.cpp:669-676, 2653-2667): Stretched fills the screen (your 07-27
# verdict, the default), Centred keeps the 4:3 board in proportion. Re-read when the menus realign, i.e. at the
# next map load or video restart (client/cl_ui.cpp UI_ResolutionChange -> RealignMenus); the subtitle says so.
MENU = P("ui_menuCenter", ["ui_menuCenter"], [("Stretched", 0), ("Centred", 1)], 0)

# [bug-3121 / G7] CURVE DETAIL as the vanilla list's four values (advancedoptions.urc curve detail list, 20/10/4/3).
# r_subdivisions is a max curve error: LOWER is finer, and 2 is the engine floor (renderergl2/tr_init.c:2118), so
# the old slider's "1" silently read as 2. 2 and 1 stay readable for old configs but are no longer offered: the
# retail developers commented those two entries out.
CURVE = P("r_subdivisions", ["r_subdivisions"], [("Lowest", 20), ("Low", 10), ("Medium", 4), ("High", 3)], 4,
          aliases=[(2, "Higher"), (1, "Highest")])

# [bug-3120 / G6] SOLDIER SHADOWS. With coop_shadowDir 1 (the default) every non-zero cg_shadows draws the SAME
# sun-oriented decal (cgame/cg_modelanim.c:776-841), so "Simple" and "Complex" / "OFF..FEET" promised looks the
# code does not draw. Off / On. 2 is the shipped seed; 0 also removes water ripples (cg_specialfx.cpp:1108).
SHADOW = P("cg_shadows", ["cg_shadows"], [("Off", 0), ("On", 2)], 2, aliases=[(1, "On"), (3, "On")])

# [2026-09-28, v1.10.3 default flip; water_wetness plan D7 - user-approved after 42/42 in-engine] WATER REFLECTIONS
# and WET IN RAIN are normal rows now. r_hzmWater (renderergl2/tr_hzm_water.c:327) and r_hzmWet (tr_hzm_wet.c:87) are
# flags 0, default "-1" = AUTO, and AUTO is 1 (renderercommon/hzm_waterwet.h). Seeded -1, NOT 1, in coop_defaults.cfg,
# so a later AUTO change still reaches players whose saved config holds the seed (TRAPS T7); DEFAULTS writes -1 too.
# Live and faded over 1.5 s - no restart, no latch. Omaha is excluded in the engine by map name; nothing here.
# A pulldown, not a CheckBox: a CheckBox (and a bare enabledcvar) reads -1 as ON only by accident of the value.
WATER = P("r_hzmWater", ["r_hzmWater"], [("Off", 0), ("On", 1)], -1, aliases=[(-1, "On (default)")])
WET = P("r_hzmWet", ["r_hzmWet"], [("Off", 0), ("On", 1)], -1, aliases=[(-1, "On (default)")])

# [2026-10-04, docs/proposals/ground_variety_2026-09-29] GROUND VARIETY - a normal row, OFF by default. r_groundVariety
# (renderergl2/tr_hzm_groundvar.c) is flags 0, default "-1" = AUTO = HZM_GROUNDVAR_AUTO, which is 0 (OFF): the
# 2026-10-04 in-engine QA was clean where it was valid (m3l2 barn yard + field, m2l1: no blur, <2 levels colour shift,
# no added shimmer, ~0 % cost) but only 2 of 4 maps captured cleanly and the cost run was on a busy machine, so the
# ship rule kept it opt-in. Seeded -1 like WATER/WET (TRAPS T7), so flipping AUTO in the engine later reaches everyone.
# 1 = world-space brightness variation only, 2 = plus hex tiling where scripts/hzm_groundvariety.txt allows it.
# Live, no restart. gl1: no effect. Omaha is excluded in the engine by map name and asset name; nothing here.
GROUNDVAR = P("r_groundVariety", ["r_groundVariety"], [("Off", 0), ("Subtle", 1), ("Full", 2)], -1,
              aliases=[(-1, "Off (default)")])

ADV_SECTIONS = [
    (0, "TEXTURES & LIGHTING", [
        ("Aniso", "toggle", "Anisotropic Filter", "r_ext_texture_filter_anisotropic", T(1)),
        ("AnisoLvl", "slider", "Aniso Level", "r_ext_max_anisotropy", S("integer", 2, 16, 2, 16, "2x", "16x")),
        # [bug-3117..3119 Phase 1] Overbright Light and Tex Intensity are gone: on gl2 overbright only clips bright
        # lightmaps earlier (the world gain is r_mapOverBrightBits), and r_intensity > 1 brightens TGA/JPG but skips
        # every HD .dds, so the two drift apart. r_overBrightBits is pinned to its seed by coop_gfxfix1.cfg.
        ("Sun", "toggle", "Draw Sun", "r_drawSun", T(1)),
        # r_flares is what draws the HZM lamp, headlight and searchlight glow (tr_hzm_spot_rb.c:107); the retail
        # flare path has nothing left to draw on gl2.
        ("Flare", "toggle", "Lamp Glow", "r_flares", T(1)),
        ("FDL", "toggle", "Fast Dlights (old renderer only)", "r_fastdlights", T(0)),  # bug-3038: gl1-only, no reader on gl2
        ("GroundVar", "pulldown", "Ground Variety", "r_groundVariety", GROUNDVAR),
    ]),
    (0, "DISPLAY", [
        ("Vsync", "toggle", "VSync", "r_swapInterval", T(1)),
        ("Fps", "pulldown", "Frame Rate Limit", "com_maxfps", FPS),
        ("MenuLay", "pulldown", "Menu Layout", "ui_menuCenter", MENU),
    ]),
    (1, "GEOMETRY & EFFECTS", [
        ("MSAA", "pulldown", "Anti-Aliasing", "r_msaa", MSAA),
        ("AA", "pulldown", "Edge Smoothing", "r_ppFXAA", AA),
        ("Curve", "pulldown", "Curve Detail", "r_subdivisions", CURVE),
        ("Shadow", "pulldown", "Soldier Shadows", "cg_shadows", SHADOW),
        # [bug-3117 / G3] "Draw Distance" is gone: it set r_lodscale, which does nothing while autoexec.cfg forces
        # r_uselod 0 (full model detail always, tr_model.cpp:800), and draw distance is the server's fog/farplane.
        ("FxDet", "slider", "Effect Detail", "cg_effectdetail", S("float", 0.2, 1, 0.1, 1.0, "SPARSE", "FULL")),
        ("FxMax", "slider", "Max Effects", "cg_max_tempmodels", S("integer", 256, 4096, 128, 4000, "LOW", "MAX")),
        ("Marks", "slider", "Decal Count", "cg_marks_max", S("integer", 64, 1024, 64, 487, "FEW", "MANY")),
        # [2026-10-04, docs/proposals/footprints_2026-10-04] boot prints in snow, mud and soft dirt (cgame
        # cg_footprints.c, CVAR_ARCHIVE, default 1). Own 200-print pool, independent of the decal slider above. Live.
        ("Footprint", "toggle", "Footprints", "cg_footprints", T(1)),
    ]),
    (1, "WATER & WEATHER", [
        ("Water", "pulldown", "Water Reflections", "r_hzmWater", WATER),
        ("Wet", "pulldown", "Wet in Rain", "r_hzmWet", WET),
    ]),
]

# [bug-3115 / bug-3118, Phase 1] Cvars with NO menu control any more (their only choices were harmful), pinned to
# their coop_defaults.cfg seed. Every DEFAULT cfg re-pins them, and coop_gfxfix1.cfg repairs them ONCE in configs
# that the old engine-default DEFAULT buttons (ui_resetcvars) or the installer snapshot already damaged.
# (cvar, reason, pages) - pages = which generated DEFAULT cfgs also carry it: gfx / video / adv.
PINNED = [
    ("r_ext_compressed_textures", "0 stops every HD .dds pack loading (renderergl2/tr_image.c:2488)", ("video",)),
    ("r_colorbits", "16-bit banding and a forced farclip; 0 and 32 are the same", ("video",)),
    ("r_texturebits", "16-bit textures and no HD sky layers; 0 and 32 are the same", ("video",)),
    ("vss_draw", "0 makes volumetric smoke invisible (cgame/cg_view.c:8852)", ("adv",)),
    ("r_drawstaticdecals", "0 hides the maps' own decals", ("adv",)),
    ("r_ext_multisample", "window MSAA: gl2 blits into it, clamps to 4 (bug-3119)", ("gfx",)),
    ("r_ext_framebuffer_multisample", "old gl2 MSAA path (bug-1298 halos); r_msaa owns anti-aliasing since the gfx flip", ("gfx",)),
    ("r_overBrightBits", "row removed; gl2 world gain is r_mapOverBrightBits", ("gfx",)),
    ("r_drawSunRays", "row hidden: no visible sun under the coop fog, square glow on fogged skies", ("fx",)),
]

# Vanilla menus whose DEFAULT button now execs a generated cfg instead of ui_resetcvars (bug-3115 / G1).
# ui_resetcvars -> Cvar_Reset restores the ENGINE registration default (uilib/uimenu.cpp:359-371), not the mod's:
# r_ext_compressed_textures 0 (HD packs gone), r_picmip 1, cg_marks_add 0, vss_draw 0, cg_effectdetail 0.2.
VANILLA_DEFAULTS = [
    # (urc, generated cfg, header title, PINNED page key)
    (VIDEO_URC, os.path.join(MOD, "coop_mod", "cfg", "coop_videodefaults.cfg"), "VIDEO OPTIONS", "video"),
    (os.path.join(MOD, "ui", "advancedoptions.urc"), os.path.join(MOD, "coop_mod", "cfg", "coop_advdefaults.cfg"),
     "ADVANCED OPTIONS", "adv"),
]
# Never reset by a DEFAULT button: the player's screen and view. The resolution seeds (coop_defaults.cfg r_mode -1
# 1920x1080) are only the pre-detect fallback - resetting them would shrink a 3440x1440 player (vet 3).
# ui_console is unseeded and its engine default 0 disables the console key: a DEFAULT press must not lock a player
# out of the console, so it is the player's, like the view.
DEFAULT_EXCLUDE = ("r_mode", "r_customwidth", "r_customheight", "r_fullscreen", "r_desktopfullscreen", "r_noborder",
                   "ui_displaymode", "fov", "ui_console")
# Not linked by any widget, but part of the page's shipped state (the terrain "Max" row sets all three ter_*).
DEFAULT_EXTRAS = {"adv": [("ter_maxtris", "24576")]}

FIX_CFG = os.path.join(MOD, "coop_mod", "cfg", "coop_gfxfix1.cfg")
FIX_ALIAS = "coop_gfxFix1"      # a NEW repair gets a NEW name (coop_gfxFix2 ...): the saved config keeps this one disarmed
FPS_ALIAS = "coop_fpsRestore"


# ---------------------------------------------------------------- layout (forked from fs.lay_sheet, + pulldown)
def lay_graphics(sections, colx, top, colw):
    rows, heads, bottoms = [], [], {}
    for col, title, items in sections:
        y = bottoms.get(col, top - 8) + 8
        heads.append((col, title, y))
        ry = y + 24
        for i, it in enumerate(items):
            rows.append((col, ry, i) + tuple(it))
            tall = it[1] == "slider"
            bottoms[col] = ry + (32 if tall else fs.ROW_H)
            ry += fs.S_PITCH if tall else T_PITCH
    g = dict(stripes=[], headers=[], labels=[], plates=[], lamps=[], notches=[], captions=[],
             displays=[], sliders=[], checkboxes=[], pulldowns=[])
    for col, y, i, key, kind, text, cvar, spec in rows:
        if i % 2 == 1:
            g["stripes"].append(fs.label("stripe" + key, (colx[col], y - 2, colw, fs.S_PITCH if kind == "slider" else T_PITCH), bg=fs.STRIPE))
    for col, title, y in heads:
        tag = re.sub(r"[^A-Za-z]", "", title.title())
        g["headers"].append(fs.text_label("hdr" + tag, (colx[col], y, colw, 18), title, "facfont-20", fs.RUST, "left"))
        g["headers"].append(fs.label("rule" + tag, (colx[col], y + 19, colw, 1), bg=fs.RULE))
    for col, y, i, key, kind, text, cvar, spec in rows:
        x = colx[col]
        if kind == "toggle":
            px = x + colw - fs.PLATE_W
            g["labels"].append(fs.text_label("lbl" + key, (x + 8, y, colw - fs.PLATE_W - 14, fs.ROW_H), text, "facfont-20", fs.INK, "left"))
            g["plates"].append(fs.text_label("on" + key, (px, y + 1, fs.PLATE_W, fs.PLATE_H), "ON", "facfont-20", fs.AMBER, "center",
                                             dontlocalize=True, bg=fs.PLATE, border="3D_BORDER", enabledcvar=cvar))
            g["plates"].append(fs.text_label("off" + key, (px, y + 1, fs.PLATE_W, fs.PLATE_H), "OFF", "facfont-20", fs.OFFTEXT, "center",
                                             dontlocalize=True, bg=fs.OFFPLATE, border="INDENT_BORDER", enabledcvar="!" + cvar))
            g["lamps"].append(fs.label("lampOn" + key, (px + 4, y + 6, 4, 8), bg=fs.LAMP_ON, enabledcvar=cvar))
            g["lamps"].append(fs.label("lampOff" + key, (px + 4, y + 6, 4, 8), bg=fs.LAMP_OFF, enabledcvar="!" + cvar))
            g["checkboxes"].append(fs.W("cb" + key, "CheckBox", (x, y, colw, fs.ROW_H), fg=fs.WHITE, bg=fs.CLEAR, border="NONE", linkcvar=cvar))
        elif kind == "pulldown":
            # [Phase 1] the value well starts where a slider's TRACK starts (SLIDER_X + ARROW_W), so pulldown and
            # slider rows line up by eye and the caption gets PD_X - 12 = 113 of width ("Frame Rate Limit" is 104).
            g["labels"].append(fs.text_label("lbl" + key, (x + 8, y, PD_X - 12, fs.ROW_H), text, "facfont-20", fs.INK, "left"))
            dx = x + PD_X
            dw = colw - PD_X
            disp = fs.W("val" + key, "Label", (dx, y, dw, 18))
            body = ['\tname "val%s"' % key, "\trect %d %d %d %d" % disp["rect"],
                    "\tfgcolor " + fs.c4(fs.INK), "\tbgcolor " + fs.c4(fs.BEIGE), '\tborderstyle "INDENT_BORDER"',
                    '\tlinkcvar "%s"' % spec["display_cvar"]]
            # [2026-09-27, bug-3155] NO `shader` here. It used to name textures/menu/blank2, an OPAQUE black plate
            # (scripts/mohmenu.shader: clampMap, no blend) that UIWidget::Draw tints by the FOREGROUND colour
            # (uilib/uiwidget.cpp:2136-2140) - ink x black = black - drawn over the beige fill, so the ink value text
            # sat on a black bar. The plain colour fill is the recipe the ON/OFF plates already use.
            for o in spec["options"]:
                body.append('\tlinkstring %s "%s"' % (fs.num(o[1]), o[0]))
            for val, lab in spec.get("aliases", []):
                body.append('\tlinkstring %s "%s"' % (fs.num(val), lab))
            body += ['\tfont "verdana-12"', "\ttextalign center"]
            disp["raw_body"] = body
            g["displays"].append(disp)
            pd = fs.W("pd" + key, "PulldownMenuContainer", (dx - 2, y - 2, dw + 4, 20))
            pbody = ['\ttitle "list"', '\tname "pd%s"' % key, "\trect %d %d %d %d" % pd["rect"],
                     "\tfgcolor " + fs.c4(fs.WHITE), "\tbgcolor " + fs.c4(fs.CLEAR), '\tborderstyle "NONE"',
                     '\tmenushader "MENU" "textures/mohmenu/trans_click"',
                     '\tselmenushader "MENU" "textures/mohmenu/trans_click"']
            for o in spec["options"]:
                lab, val = o[0], o[1]
                verb = "set" if is_test(spec) else "seta"
                cmds = ["%s %s %s" % (verb, cv, fs.num(val)) for cv in spec["set_cvars"]]
                if opt_extra(o):
                    cmds.append(opt_extra(o))
                pbody.append('\taddpopup "MENU" "%s" command "%s"' % (lab, " ; ".join(cmds)))
            pd["raw_body"] = pbody
            g["pulldowns"].append(pd)
        else:
            g["labels"].append(fs.text_label("lbl" + key, (x + 8, y, fs.SLIDER_X - 12, fs.ROW_H), text, "facfont-20", fs.INK, "left"))
            pos = (spec["default"] - spec["lo"]) / float(spec["hi"] - spec["lo"])
            cx = x + fs.SLIDER_X + fs.ARROW_W + fs.THUMB_W / 2.0 + (fs.SLIDER_W - 2 * fs.ARROW_W - fs.THUMB_W) * pos
            g["notches"].append(fs.label("notch" + key, (round(cx - 1), y - 1, 2, 21), bg=fs.RUST))
            g["captions"].append(fs.text_label("capL" + key, (x + fs.SLIDER_X, y + 20, 70, 12), spec["capL"], "verdana-12", fs.MUTED, "left", dontlocalize=True))
            g["captions"].append(fs.text_label("capR" + key, (x + fs.SLIDER_X + fs.SLIDER_W - 70, y + 20, 70, 12), spec["capR"], "verdana-12", fs.MUTED, "right", dontlocalize=True))
            g["sliders"].append(fs.W("sl" + key, "Slider", (x + fs.SLIDER_X, y + 2, fs.SLIDER_W, fs.SLIDER_H), fg=fs.WHITE, bg=fs.CLEAR, border="NONE",
                                    linkcvar=cvar, slidertype=spec["type"], setrange=(spec["lo"], spec["hi"]), stepsize=spec["step"]))
    return rows, g


def ordered(chrome, g, footer, buttons):
    out = list(chrome)
    for k in ("stripes", "headers", "labels", "plates", "lamps", "notches", "captions", "displays"):
        out += g[k]
    out += footer + g["sliders"] + g["checkboxes"] + g["pulldowns"] + buttons
    return out


# ---------------------------------------------------------------- chrome + sheets
COLX = {0: 52, 1: 332}
COLW = fs.COLW
PD_X = fs.SLIDER_X + fs.ARROW_W - 1   # 124: pulldown value well = slider track start
TOP = 86
FOOT_Y = 414          # the footer rule; every row widget must end above it
PAPER_BOX = (32, 38, 608, 446)
ROW_PREFIXES = ("stripe", "hdr", "rule", "lbl", "on", "off", "lamp", "cb", "sl", "notch", "capL", "capR", "val", "pd")


def base_chrome(foldertab, title, badge, subtitle):
    return [
        fs.label("folder", (20, 26, 600, 432), bg=fs.FOLDER, border="3D_BORDER"),
        fs.text_label("foldertab", (40, 6, 150, 24), foldertab, "facfont-20", fs.TABINK, "center", bg=fs.TAB, border="3D_BORDER"),
        fs.label("paper", (32, 38, 576, 408), bg=fs.PAPER, border="3D_BORDER"),
        fs.label("titlePlate", (44, 46, 552, 24), bg=fs.PLATE, border="3D_BORDER"),
        fs.text_label("titleText", (56, 49, 300, 18), title, "facfont-20", fs.BEIGE, "left"),
        fs.text_label("pageBadge", (356, 51, 240, 14), badge, "verdana-12", fs.AMBER, "right", dontlocalize=True),
        fs.text_label("subtitle", (52, 71, 544, 12), subtitle, "verdana-12", fs.MUTED, "left", dontlocalize=True),
    ]


def foot_buttons(specs):
    """specs = [(name, text, sound, cmd, x, w)] -> plate Buttons on the footer strip."""
    return [fs.plate_button(n, (x, 418, w, 20), t, s, c) for (n, t, s, c, x, w) in specs]


PFX_APPLY = "sound/menu/apply.wav"
PFX_BACK = "sound/menu/back.wav"


# ---------------------------------------------------------------- APPLY NOW (live-settings plan 3.6; STAGED, off)
# [2026-09-27] Rows whose change still needs a video restart (the renderer's ROM count r_hzmPendingRestart, gl2
# live-settings build only) get an APPLY NOW plate in the footer gap (x 404, left of APPLY). It closes the menu and
# runs vid_restart - the Advanced APPLY's order. The cvar does not exist on today's renderer or gl1, so every gate
# below reads 0 there and nothing shows. Captions replace the subtitle while something waits, chosen by sv_running
# (decision U8); a listen host gets a one-click confirm because its restart pauses every player. STAYS False until
# HZM_LIVEAPPLY_AUTO is flipped in the main tree after the user's test: the plate is a visible behaviour change, and
# the Post-FX ' *' set changes with it (gfx_live_audit.py --check-stars is the arbiter, wired into check below).
LIVE_APPLY_PLATE = False
PEND = "r_hzmPendingRestart"
APPLYNOW_RECT = (404, 418, 96, 20)
APPLYNOW_CAPTIONS = [
    ("subPendLocal", "%s>0 sv_running==0" % PEND,
     "Some changes need a short reload of the picture: about 10 seconds, only on your screen."),
    ("subPendHost", "%s>0 sv_running>0 ui_gfxConfirm==0" % PEND,
     "Some changes need a short reload: about 10 seconds, and while you host everyone's game pauses."),
    ("subPendSure", "%s>0 sv_running>0 ui_gfxConfirm==1" % PEND,
     "Sure? Every player's game pauses for about 10 seconds. Click YES to go ahead."),
]


def live_chrome(chrome):
    """Gate the normal subtitle off while something waits, and add the three captions on the same line."""
    if not LIVE_APPLY_PLATE:
        return chrome
    out = []
    for w in chrome:
        if w["name"] == "subtitle":
            w = dict(w, enabledcvar="%s==0" % PEND)
            out.append(w)
            for name, gate, text in APPLYNOW_CAPTIONS:
                out.append(fs.text_label(name, w["rect"], text, "verdana-12", fs.HOSTRED if "Host" in name or "Sure" in name
                                         else fs.RUST, "left", dontlocalize=True, enabledcvar=gate))
        else:
            out.append(w)
    return out


def applynow_buttons(close_cmd):
    """Three plates, one rect, mutually exclusive gates (gate_applynow proves it)."""
    if not LIVE_APPLY_PLATE:
        return []
    go = "set ui_gfxConfirm 0 ; %s ; vid_restart" % close_cmd
    specs = [
        ("applyNowLocal", "APPLY NOW", "%s>0 sv_running==0" % PEND, go),
        ("applyNowHost", "APPLY NOW", "%s>0 sv_running>0 ui_gfxConfirm==0" % PEND, "set ui_gfxConfirm 1"),
        ("applyNowSure", "YES", "%s>0 sv_running>0 ui_gfxConfirm==1" % PEND, go),
    ]
    out = []
    for name, text, gate, cmd in specs:
        b = fs.plate_button(name, APPLYNOW_RECT, text, PFX_APPLY, cmd)
        b["enabledcvar"] = gate
        b["gate_group"] = "applynow"
        out.append(b)
    return out


def confirm_reset(cmd):
    """Every other footer button clears a half-done host confirm."""
    return ("set ui_gfxConfirm 0 ; " + cmd) if LIVE_APPLY_PLATE else cmd


def gate_applynow(sheets, problems):
    """Plates of one gate_group share one rect, and every pair has a contradictory condition."""
    def conds(g):
        out = {}
        for t in g.split():
            m = re.match(r"^(!?)([A-Za-z_0-9]+)(==|>|<|>=|<=|!=)?(-?\d+)?$", t)
            if m:
                out[m.group(2)] = (m.group(3) or ("==" if m.group(1) else ">"), int(m.group(4) or 0))
        return out

    def disjoint(a, b):
        for k in set(a) & set(b):
            (oa, va), (ob, vb) = a[k], b[k]
            ops = {"==": lambda x, y: x == y, "!=": lambda x, y: x != y, ">": lambda x, y: x > y,
                   "<": lambda x, y: x < y, ">=": lambda x, y: x >= y, "<=": lambda x, y: x <= y}
            sa = set(v for v in range(-2, 9) if ops[oa](v, va))
            sb = set(v for v in range(-2, 9) if ops[ob](v, vb))
            if not (sa & sb):
                return True
        return False

    for name, (widgets, _paper) in sheets.items():
        grp = [w for w in widgets if w.get("gate_group")]
        for i, a in enumerate(grp):
            for b in grp[i + 1:]:
                if a["rect"] != b["rect"]:
                    problems.append("%s: %s / %s share a gate_group but not a rect" % (name, a["name"], b["name"]))
                if not disjoint(conds(a["enabledcvar"]), conds(b["enabledcvar"])):
                    problems.append("%s: %s / %s can show at the same time (%r vs %r)"
                                    % (name, a["name"], b["name"], a["enabledcvar"], b["enabledcvar"]))


def sheet_pfx(page, idx, total):
    name, title, tag, nxt, prv, sections = page
    subtitle = "Applies live.  * = takes effect after a vid_restart or the next map load.  CANCEL reverts."
    chrome = live_chrome(base_chrome("POST-FX", title, "%s   %d / %d" % (tag, idx, total), subtitle))
    rows, g = lay_graphics(sections, COLX, TOP, COLW)
    footer = [fs.label("footRule", (44, FOOT_Y, 552, 1), bg=fs.RULE)]
    # popmenu depth back to Video Options: this page pushed (idx-1) sheets on top of it.
    apply_cmd = " ; ".join(["popmenu 0"] * idx)
    specs = [("defaultsBtn", "DEFAULTS", PFX_APPLY, "exec coop_mod/cfg/coop_fxdefaults.cfg", 44, 92)]
    if prv:
        specs.append(("backBtn", "< BACK", PFX_BACK, "popmenu 0", 150, 78))
    else:
        specs.append(("cancelBtn", "CANCEL", PFX_BACK, "exec configs/coop_fxsession.cfg ; popmenu 0", 150, 78))
    if nxt:
        specs.append(("moreBtn", "MORE >", PFX_APPLY, "pushmenu " + nxt, 236, 78))
    else:
        specs.append(("cancelBtn", "CANCEL", PFX_BACK, "exec configs/coop_fxsession.cfg ; " + apply_cmd, 236, 78))
    specs.append(("applyBtn", "APPLY", PFX_APPLY, apply_cmd, 508, 88))
    specs = [(n, t, snd, confirm_reset(c), x, w) for (n, t, snd, c, x, w) in specs]
    buttons = foot_buttons(specs) + applynow_buttons(apply_cmd)
    return rows, ordered(chrome, g, footer, buttons), PAPER_BOX


def sheet_adv():
    # [Phase 1] plain words (user 09-27): no "latched", no "vid_restart". Menu Layout is not latched, so APPLY cannot
    # restart for it; it shows when the menus realign at the next map (see MENU).
    subtitle = "APPLY briefly reloads the picture for some rows. Anti-Aliasing and Menu Layout show from the next map."
    chrome = live_chrome(base_chrome("VIDEO", "ADVANCED GRAPHICS", "PER-PLAYER", subtitle))
    rows, g = lay_graphics(ADV_SECTIONS, COLX, TOP, COLW)
    footer = [fs.label("footRule", (44, FOOT_Y, 552, 1), bg=fs.RULE)]
    specs = [
        ("defaultsBtn", "DEFAULTS", PFX_APPLY, "exec coop_mod/cfg/coop_gfxdefaults.cfg", 44, 92),
        ("backBtn", "BACK", PFX_BACK, "popmenu 0", 236, 78),
        ("applyBtn", "APPLY", PFX_APPLY, "ui_checkrestart ; popmenu 0", 508, 88),
    ]
    specs = [(n, t, snd, confirm_reset(c), x, w) for (n, t, snd, c, x, w) in specs]
    buttons = foot_buttons(specs) + applynow_buttons("popmenu 0")
    return rows, ordered(chrome, g, footer, buttons), PAPER_BOX


# ---------------------------------------------------------------- emit
def emit_widget(w):
    if "raw_body" in w:
        return ["resource", w["kind"], "{"] + w["raw_body"] + ["}"]
    return fs.emit_widget(w)


HEADER = """\
// GENERATED by docs/tools/gen_menu_graphics.py - DO NOT HAND-EDIT. Change the table there, run `build`, and
// `check` must pass (fit, overlap, fall-through, byte drift, and every linkcvar registered in the engine).
// Same manila-sheet recipe as ui/coop_settings.urc: ON/OFF plate + lamp gated `enabledcvar`, a transparent
// whole-row CheckBox declared last as the click target; sliders are the retail textures/menu/slider recipe;
// the rust tick under each slider marks its shipped default (read from coop_defaults.cfg). Canvas stays
// 640x480 (a widget outside it draws nothing, bug-1365); each resource field on its own line (single-line
// blocks are silently dropped); colour fills, never raw-image shaders, for panels; ASCII only, no BOM/CR.
// The mod ships gl2: every linkcvar is a gl2 (or cgame) registration. LATCH rows marked * apply on the next
// map load - the post-FX APPLY does NOT vid_restart (bug-1181 crashes gl2 from an open menu)."""


def emit_menu(name, intro, widgets):
    out = intro.splitlines() + HEADER.splitlines() + [
        'menu "%s" 640 480 NONE 1' % name, "borderstyle NONE", "bgcolor 0 0 0 0", "align centerx centery",
        "virtualres 1", "fullscreen 0", "", "direction from_top 0", ""]
    for w in widgets:
        out += emit_widget(w)
    out.append("end.")
    return "\n".join(out) + "\n"


PFX_INTRO = """\
// HZM coop - POST-PROCESSING EFFECTS: the gl2 GLSL post-FX chain, one printed settings sheet per group,
// paged with MORE >/< BACK. Opened from Video Options (POST-FX EFFECTS), which writeconfig's coop_fxsession
// first so CANCEL can revert. All controls bind their renderer cvar live. [user 2026-09-14] restyled to
// match ui/coop_settings.urc."""

ADV_INTRO = """\
// HZM coop - ADVANCED GRAPHICS: stock gl2 quality cvars the vanilla video menu does not expose (anisotropic
// filtering, edge smoothing, curve detail, effect/decal budgets) plus the display rows (vsync, frame rate limit,
// menu layout). Opened from Video Options (ADVANCED GFX). Latched knobs apply on APPLY (ui_checkrestart
// auto-issues vid_restart; bug-1145). [user 2026-09-14] restyled to match ui/coop_settings.urc.
// [2026-09-27 graphics menu Phase 1, bug-3117/3119/3120/3121] Draw Distance, Overbright, Tex Intensity gone;
// Anti-Aliasing = Off / Smooth edges until the gfx MSAA flip; Frame Rate Limit and Menu Layout added."""


# ---------------------------------------------------------------- defaults resolution (coop_defaults = truth)
def all_menu_cvars():
    """(cvar, spec, page-or-'adv') for every distinct menu control, MSAA expanded to its two set_cvars."""
    return [(cvar, spec, kind) for cvar, spec, kind, _text in all_menu_rows()]


def all_menu_rows():
    """all_menu_cvars() plus each row's on-screen caption (the gl2 wire gate reads the GL1_ONLY_TAG in it)."""
    seen = []
    for _n, _t, _tag, _nx, _pv, sections in PFX_PAGES:
        for _c, _title, items in sections:
            for key, kind, text, cvar, spec in items:
                seen.append((cvar, spec, kind, text))
    for _c, _title, items in ADV_SECTIONS:
        for key, kind, text, cvar, spec in items:
            seen.append((cvar, spec, kind, text))
    return seen


def defaults_seeds():
    """cvar -> value string, from coop_defaults.cfg (the archived source of truth)."""
    seeds = {}
    for m in fs.SETA_RE.finditer(fs.rd(DEFAULTS_CFG)):
        seeds[m.group(1)] = m.group(2)
    return seeds


def resolve_default(cvar, spec, seeds):
    """Shipped default = coop_defaults seed if present, else the table fallback."""
    if cvar in seeds:
        return seeds[cvar]
    return fs.num(spec["default"])


def apply_defaults(seeds):
    """Set each slider spec['default'] to its shipped value so the rust tick lands on it."""
    for _n, _t, _tag, _nx, _pv, sections in PFX_PAGES:
        for _c, _title, items in sections:
            for key, kind, text, cvar, spec in items:
                if kind == "slider":
                    spec["default"] = float(resolve_default(cvar, spec, seeds))
    for _c, _title, items in ADV_SECTIONS:
        for key, kind, text, cvar, spec in items:
            if kind == "slider":
                spec["default"] = float(resolve_default(cvar, spec, seeds))


def pfx_cvars_ordered():
    out = []
    for _n, _t, _tag, _nx, _pv, sections in PFX_PAGES:
        for _c, _title, items in sections:
            for key, kind, text, cvar, spec in items:
                out.append((cvar, spec, kind))
    return out


def adv_cvars_ordered():
    out = []
    for _c, _title, items in ADV_SECTIONS:
        for key, kind, text, cvar, spec in items:
            if kind == "pulldown" and is_test(spec):
                continue            # never in a DEFAULTS cfg: a test row must not be seeded or re-set
            if kind == "pulldown":
                for cv in spec["set_cvars"]:
                    out.append((cv, spec, "pulldown"))
            else:
                out.append((cvar, spec, kind))
    return out


def pulldown_extra_for(spec, val):
    """The extra command of the option a DEFAULTS press lands on (e.g. the frame-rate alias), or None."""
    for o in spec["options"]:
        if opt_extra(o) and abs(float(o[1]) - float(val)) < 1e-9:
            return opt_extra(o)
    return None


def pinned_lines(page, seeds):
    return ["seta %s %s    // pinned: %s" % (cv, seeds[cv], why) for cv, why, pages in PINNED if page in pages]


def emit_defaults(header_lines, cvars, seeds, pinned_page=None):
    L = list(header_lines)
    done_extra = set()
    for cvar, spec, kind in cvars:
        if kind == "pulldown":
            val = seeds.get(cvar, fs.num(spec["default"]))
        else:
            val = resolve_default(cvar, spec, seeds)
        L.append("seta %s %s" % (cvar, val))
        if kind == "pulldown" and id(spec) not in done_extra:
            done_extra.add(id(spec))
            ex = pulldown_extra_for(spec, val)
            if ex:
                L.append(ex)
    if pinned_page:
        L += [""] + pinned_lines(pinned_page, seeds)
    L += ["", 'print "Graphics settings restored to defaults.\\n"']
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- vanilla DEFAULT cfgs + the one-time repair
def urc_linkcvars(path):
    """Every `linkcvar` in a hand-made urc, in file order, comments stripped (the vanilla menus)."""
    out = []
    for ln in fs.rd(path).replace("\r\n", "\n").split("\n"):
        m = re.match(r'\s*linkcvar\s+"([^"]+)"', fs.strip_comment(ln))
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def registered_defaults():
    """cvar -> set of engine registration defaults (Cvar_Get(name, default, ...)) across the scanned modules."""
    reg = re.compile(r'Cvar_Get2?\s*\(\s*"([^"]+)"\s*,\s*"([^"]*)"')
    out = {}
    for sub in REG_SUBS:
        for d, _dirs, files in os.walk(os.path.join(ENG, sub)):
            if "thirdparty" in d or "SDL2" in d:
                continue
            for f in files:
                if f.endswith((".c", ".cpp", ".h")):
                    for name, dv in reg.findall(fs.rd(os.path.join(d, f))):
                        out.setdefault(name, set()).add(dv)
    return out


def vanilla_default_value(cv, seeds, engdef, problems, urc):
    """coop_defaults seed, else the ONE engine registration default; anything else is a gate failure."""
    if cv in seeds:
        return seeds[cv]
    dv = engdef.get(cv, set())
    if len(dv) == 1:
        return next(iter(dv))
    problems.append("vanilla DEFAULT: %s (linked in %s) has no coop_defaults seed and %s engine default(s) %s - "
                    "seed it or add it to DEFAULT_EXCLUDE" % (cv, os.path.basename(urc), len(dv), sorted(dv)))
    return None


def emit_vanilla_defaults(urc, title, page, seeds, engdef, problems):
    L = ["// HZM coop - %s DEFAULT button. ui/%s execs this instead of ui_resetcvars." % (title, os.path.basename(urc)),
         "// GENERATED by docs/tools/gen_menu_graphics.py - DO NOT HAND-EDIT. [2026-09-27 bug-3115] ui_resetcvars reset every",
         "// linked cvar to the ENGINE default (HD textures off, half-size textures, no bullet holes, invisible smoke).",
         "// This restores the SHIPPED look instead: each linked cvar's coop_defaults.cfg seed (engine default only where",
         "// the mod seeds nothing). Resolution, display mode and field of view are left alone (DEFAULT_EXCLUDE)."]
    pinned = set(cv for cv, _w, _p in PINNED)
    for cv in urc_linkcvars(urc):
        if cv in DEFAULT_EXCLUDE or cv in pinned:
            continue
        v = vanilla_default_value(cv, seeds, engdef, problems, urc)
        if v is not None:
            L.append("seta %s %s" % (cv, v))
    for cv, v in DEFAULT_EXTRAS.get(page, []):
        L.append("set %s %s" % (cv, v))
    L += [""] + pinned_lines(page, seeds)
    L += ["", 'print "%s restored to the shipped defaults.\\n"' % title.title()]
    return "\n".join(L) + "\n"


def emit_fix(seeds):
    L = ["// HZM coop - ONE-TIME GRAPHICS REPAIR #1. GENERATED by docs/tools/gen_menu_graphics.py - DO NOT HAND-EDIT.",
         "// [2026-09-27 bug-3115/3116/3118/3119] Run once per profile by the alias %s: coop_defaults.cfg defines it" % FIX_ALIAS,
         "// armed (exec this file), the SAVED config - which loads after coop_defaults.cfg and stores aliases - holds",
         "// it disarmed after the first run, and autoexec.cfg invokes it. The r_resAutoDetected recipe (fire once, keep",
         "// a flag, never fight a later pick) done with an alias, because a server cannot write or run an alias",
         "// (qcommon/cmd_filter.c), whereas a vstr'd cvar needs a SEC2 guard-list entry and a new exe.",
         "// It only touches cvars that NO menu offers any more, so it can never undo a player's choice. A later repair",
         "// is a NEW file and a NEW alias name (coop_gfxFix2): this one stays disarmed in every saved config."]
    for cv, why, _pages in PINNED:
        L.append("seta %s %s    // %s" % (cv, seeds[cv], why))
    L += ["alias %s \"\"" % FIX_ALIAS,
          'echo "^3[gfx] one-time graphics repair: HD textures, 3D smoke and map decals on; window MSAA and sun rays off"']
    return "\n".join(L) + "\n"


FX_HEADER = [
    "// HZM coop - POST-FX SHIPPING DEFAULTS. The DEFAULTS button in ui/coop_postfx*.urc execs this.",
    "// GENERATED by docs/tools/gen_menu_graphics.py - DO NOT HAND-EDIT. Every value mirrors the archived seta",
    "// in coop_defaults.cfg (the shipping look); the generator keeps the two in lockstep, so pressing DEFAULTS",
    "// restores exactly what a fresh profile gets. Change the look in coop_defaults.cfg, then run build.",
]
GFX_HEADER = [
    "// HZM coop - ADVANCED GRAPHICS SHIPPING DEFAULTS. The DEFAULTS button in ui/advanced_graphics.urc execs this.",
    "// GENERATED by docs/tools/gen_menu_graphics.py - DO NOT HAND-EDIT. Mirrors the archived seta in",
    "// coop_defaults.cfg. Latched cvars (aniso/subdivisions/vsync) take effect on the menu's APPLY",
    "// (ui_checkrestart). The PINNED cvars at the end have no row any more; see gen_menu_graphics.py PINNED.",
]


# ---------------------------------------------------------------- engine registration (the wire audit)
# [Phase 1] client + uilib too: ui_menuCenter is read only by uilib (uiwidget.cpp UI_MenuCenterEnabled).
REG_SUBS = ("renderergl1", "renderergl2", "cgame", "fgame", "qcommon", "client", "uilib")
# [bug-3038] The mod ships and tests on gl2 (TRAPS T7). A cvar that ONLY renderergl1 registers has no reader in
# the running renderer: its row is a dead switch. The wire gate rejects it unless the caption carries this tag.
GL1_ONLY_SUBS = ("renderergl1",)
GL1_ONLY_TAG = "(old renderer only)"


def registered_cvars_by_sub():
    per = {}
    # Cvar_Get registers; Cvar_GetString("x", "default") (uilib's uii. wrapper) is a READ with a fallback - either
    # one means a reader exists, which is what the wire gate asks.
    reg = re.compile(r'Cvar_Get(?:2|String)?\s*\(\s*"([^"]+)"')
    for sub in REG_SUBS:
        names = set()
        base = os.path.join(ENG, sub)
        for d, _dirs, files in os.walk(base):
            if "thirdparty" in d or "SDL2" in d:
                continue
            for f in files:
                if f.endswith((".c", ".cpp", ".h")):
                    names.update(reg.findall(fs.rd(os.path.join(d, f))))
        per[sub] = names
    return per


def registered_cvars():
    names = set()
    for s in registered_cvars_by_sub().values():
        names |= s
    return names


def script_read_cvars():
    hits = set()
    getc = re.compile(r'getcvar\s*\(?\s*"?([A-Za-z_][\w]*)')
    for d, _dirs, files in os.walk(os.path.join(MOD, "coop_mod")):
        for f in files:
            if f.endswith(".scr"):
                hits.update(getc.findall(fs.rd(os.path.join(d, f))))
    return hits


# ---------------------------------------------------------------- render + gates
def render_all():
    seeds = defaults_seeds()
    apply_defaults(seeds)
    sheets, papers = {}, {}
    total = len(PFX_PAGES)
    for i, page in enumerate(PFX_PAGES, 1):
        name = page[0]
        rows, widgets, paper = sheet_pfx(page, i, total)
        sheets[name] = (widgets, paper)
    rows, adv_widgets, adv_paper = sheet_adv()
    sheets["advanced_graphics"] = (adv_widgets, adv_paper)
    files = {}
    for i, page in enumerate(PFX_PAGES):
        files[PFX_URC[i]] = emit_menu(page[0], PFX_INTRO, sheets[page[0]][0])
    files[ADV_URC] = emit_menu("advanced_graphics", ADV_INTRO, sheets["advanced_graphics"][0])
    files[FX_CFG] = emit_defaults(FX_HEADER, pfx_cvars_ordered(), seeds, pinned_page="fx")
    files[GFX_CFG] = emit_defaults(GFX_HEADER, adv_cvars_ordered(), seeds, pinned_page="gfx")
    # [Phase 1] the two vanilla DEFAULT buttons and the one-time repair (bug-3115). Their resolution problems are
    # collected here and reported by main() with the other gates.
    engdef = registered_defaults()
    RENDER_PROBLEMS[:] = []
    for urc, cfg, title, page in VANILLA_DEFAULTS:
        files[cfg] = emit_vanilla_defaults(urc, title, page, seeds, engdef, RENDER_PROBLEMS)
    files[FIX_CFG] = emit_fix(seeds)
    return files, sheets, seeds


RENDER_PROBLEMS = []


def gate_ranges(problems):
    for cvar, spec, kind in all_menu_cvars():
        if kind == "slider":
            d = spec["default"]
            if d < spec["lo"] - 1e-9 or d > spec["hi"] + 1e-9:
                problems.append("range: %s default %g outside [%g, %g]" % (cvar, d, spec["lo"], spec["hi"]))


def gate_footer(sheets, problems):
    """No row widget may reach the footer rule - a slider caption dropping onto DEFAULTS reads as a defect
    even though the overlap gate (interactive-only) does not flag it."""
    for name, (widgets, _paper) in sheets.items():
        for w in widgets:
            if any(w["name"].startswith(p) for p in ROW_PREFIXES):
                if w["rect"][1] + w["rect"][3] > FOOT_Y:
                    problems.append("%s: row widget %s ends at y=%d, past the footer rule %d"
                                    % (name, w["name"], w["rect"][1] + w["rect"][3], FOOT_Y))


def gate_wire(problems, notes):
    per = registered_cvars_by_sub()
    reg, live = set(), set()
    for sub, names in per.items():
        reg |= names
        if sub not in GL1_ONLY_SUBS:
            live |= names
    scr = script_read_cvars()
    for cvar, spec, kind, text in all_menu_rows():
        cvs = spec["set_cvars"] if kind == "pulldown" else [cvar]
        for cv in cvs:
            if cv not in reg and cv not in scr:
                problems.append("DEAD WIRE: %s is not registered in the engine or read by a script" % cv)
            elif cv not in live and cv not in scr:
                # [bug-3038] registered only by renderergl1: nothing reads it on gl2, the renderer we ship
                if GL1_ONLY_TAG in text:
                    notes.append("%s is gl1-only; its row is captioned %r" % (cv, text))
                else:
                    problems.append("DEAD ON gl2: %s is registered only by renderergl1 (row %r) - caption it "
                                    "'%s' or drop the row" % (cv, text, GL1_ONLY_TAG))


def gate_defaults(files, seeds, problems, notes):
    fx = {m.group(1): m.group(2) for m in fs.SETA_RE.finditer(files[FX_CFG])}
    gfx = {m.group(1): m.group(2) for m in fs.SETA_RE.finditer(files[GFX_CFG])}
    for cvar, spec, kind in all_menu_cvars():
        if kind == "pulldown" and is_test(spec):
            for cv in spec["set_cvars"]:
                if cv in seeds:
                    problems.append("defaults: TEST row cvar %s is seeded in coop_defaults.cfg - test rows are never seeded" % cv)
                if cv in fx or cv in gfx:
                    problems.append("defaults: TEST row cvar %s is in a DEFAULTS cfg" % cv)
            continue
        cvs = spec["set_cvars"] if kind == "pulldown" else [cvar]
        for cv in cvs:
            btn = fx.get(cv, gfx.get(cv))
            if btn is None:
                problems.append("defaults: %s is on a sheet but no DEFAULTS cfg sets it" % cv)
                continue
            if cv in seeds and abs(float(btn) - float(seeds[cv])) > 1e-9:
                problems.append("defaults: DEFAULTS sets %s %s but coop_defaults seeds %s" % (cv, btn, seeds[cv]))
            if cv not in seeds:
                notes.append("%s is not seeded in coop_defaults.cfg (using engine fallback %s)" % (cv, btn))


def gate_fallthrough(sheets, problems, notes):
    vid = [r for r in fs.urc_resources(VIDEO_URC) if r[0] in fs.INTERACTIVE and r[2]]
    # The page-1 CANCEL/APPLY (and advanced BACK/APPLY) pop straight back to Video Options; a double-click's
    # second press lands there.
    for name in ("coop_postfx", "advanced_graphics"):
        widgets = sheets[name][0]
        for w in widgets:
            if w["kind"] != "Button":
                continue
            for kind, nm, rect, cmd in vid:
                if fs.ov(w["rect"], rect):
                    notes.append("%s %s overlaps Video Options %s %s (double-click fall-through)" % (name, w["name"], nm, rect))


AUTOEXEC_CFG = os.path.join(MOD, "autoexec.cfg")
START_CFG = os.path.join(MOD, "coop_mod", "start_server.cfg")


def cfg_statements(path):
    """Top-level statements of a cfg, comments stripped, split on ; outside quotes (Cbuf-like, enough here)."""
    out = []
    for ln in fs.rd(path).replace("\r\n", "\n").split("\n"):
        ln = fs.strip_comment(ln)
        cur, q = "", False
        for ch in ln:
            if ch == '"':
                q = not q
            if ch == ";" and not q:
                out.append(cur.strip())
                cur = ""
            else:
                cur += ch
        if cur.strip():
            out.append(cur.strip())
    return [s for s in out if s]


def gate_phase1(files, seeds, problems):
    """[2026-09-27 graphics menu Phase 1] the contracts the hand-edited files must keep with this table."""
    problems.extend(RENDER_PROBLEMS)
    # pins: every PINNED cvar is seeded, so DEFAULTS, the repair and a fresh profile agree
    for cv, _why, _pages in PINNED:
        if cv not in seeds:
            problems.append("PINNED %s has no coop_defaults.cfg seed" % cv)
    # vanilla DEFAULT buttons exec the generated cfg; nothing calls ui_resetcvars on those pages
    for urc, cfg, _title, _page in VANILLA_DEFAULTS:
        text = fs.rd(urc)
        rel = "coop_mod/cfg/" + os.path.basename(cfg)
        if 'stuffcommand "exec %s"' % rel not in text:
            problems.append("%s: its DEFAULT button must be stuffcommand \"exec %s\"" % (os.path.basename(urc), rel))
        if "ui_resetcvars" in "\n".join(fs.strip_comment(l) for l in text.split("\n")):
            problems.append("%s still runs ui_resetcvars (engine defaults, bug-3115)" % os.path.basename(urc))
        for cv in urc_linkcvars(urc):
            if cv in dict((p[0], 1) for p in PINNED):
                problems.append("%s still links PINNED %s - it has no row any more" % (os.path.basename(urc), cv))
    # the two aliases: defined (armed / default) in coop_defaults.cfg, invoked in autoexec.cfg
    dft = cfg_statements(DEFAULTS_CFG)
    auto = cfg_statements(AUTOEXEC_CFG)
    want_fix = 'alias %s "exec coop_mod/cfg/%s"' % (FIX_ALIAS, os.path.basename(FIX_CFG))
    if want_fix not in dft:
        problems.append("coop_defaults.cfg must arm the repair: %s" % want_fix)
    fps_default = pulldown_extra_for(FPS, seeds.get("com_maxfps", FPS["default"]))
    want_fps = 'alias %s "%s"' % (FPS_ALIAS, fps_default.split(" ", 2)[2]) if fps_default else None
    if not want_fps or want_fps not in dft:
        problems.append("coop_defaults.cfg must define the frame-rate default: %s" % want_fps)
    for name in (FIX_ALIAS, FPS_ALIAS):
        if name not in auto:
            problems.append("autoexec.cfg must invoke the alias %s on its own line" % name)
    if any(re.match(r"seta?\s+com_maxfps\b", st) for st in auto):
        problems.append("autoexec.cfg sets com_maxfps - that re-forces a value over the Frame Rate Limit row (T7)")
    if any(FPS_ALIAS in st for st in cfg_statements(START_CFG)):
        problems.append("start_server.cfg touches %s - hosting must never overwrite the player's pick" % FPS_ALIAS)


def gate_live_audit(problems):
    """[2026-09-27, live-settings plan 3.6] The Post-FX ' *' set is DERIVED: gfx_live_audit.py --check-stars fails if a
    starred row's cvar is live under the shipped HZM_LIVEAPPLY_AUTO, or a hooked row that still waits has no star;
    --check-auto fails if the renderer and cgame AUTO copies disagree. A subprocess, not an import: that script imports
    this generator, so the reverse import would be circular (live-settings vet 15)."""
    import subprocess
    audit = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gfx_live_audit.py")
    if not os.path.exists(audit):
        problems.append("gfx_live_audit.py missing - the Post-FX star set cannot be checked")
        return
    for flag in ("--check-stars", "--check-auto"):
        r = subprocess.run([sys.executable, audit, flag], capture_output=True, text=True)
        if r.returncode != 0:
            problems.append("gfx_live_audit.py %s failed: %s" % (flag, (r.stdout + r.stderr).strip()[-400:]))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode not in ("build", "check"):
        print(__doc__)
        return 2
    files, sheets, seeds = render_all()

    if mode == "build":
        for p, text in sorted(files.items()):
            data = text.encode("ascii")
            io.open(p, "wb").write(data)
            print("wrote %s (%d bytes, LF)" % (os.path.relpath(p, ROOT), len(data)))

    problems, notes, drift = [], [], []
    for p, text in sorted(files.items()):
        rel = os.path.relpath(p, ROOT)
        if not os.path.exists(p):
            drift.append(rel + " (missing)")
        elif fs.rd(p) != text:
            drift.append(rel)
    for rel in drift:
        problems.append("DRIFT: %s differs from the table - run build" % rel)

    fonts = {"facfont-20": fs.Font("facfont-20"), "verdana-12": fs.Font("verdana-12")}
    for name, (widgets, paper) in sheets.items():
        # one representative per gate_group: the stacked APPLY NOW plates are exclusive (gate_applynow proves it)
        seen_grp, gated = set(), []
        for w in widgets:
            gname = w.get("gate_group")
            if gname and gname in seen_grp:
                continue
            seen_grp.add(gname)
            gated.append(w)
        fs.gate_sheet(name, gated, paper, fonts, problems)
    gate_applynow(sheets, problems)
    for p in list(PFX_URC) + [ADV_URC, FX_CFG, GFX_CFG, FIX_CFG] + [v[1] for v in VANILLA_DEFAULTS]:
        gate_text_key = os.path.relpath(p, ROOT)
        fs.gate_text(gate_text_key, files[p], problems)
    gate_phase1(files, seeds, problems)
    gate_live_audit(problems)
    gate_ranges(problems)
    gate_footer(sheets, problems)
    gate_wire(problems, notes)
    gate_defaults(files, seeds, problems, notes)
    gate_fallthrough(sheets, problems, notes)

    for name, (widgets, paper) in sorted(sheets.items()):
        inter = [w for w in widgets if w["kind"] in fs.INTERACTIVE]
        print("%-20s: %3d widgets, %2d interactive" % (name, len(widgets), len(inter)))
    print("byte-identical: %d of %d files" % (len(files) - len(drift), len(files)))
    for n in notes:
        print("  advisory: " + n)
    if problems:
        print("PROBLEMS (%d):" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("  -> OK: no drift, fit/overlap/wire/range/defaults gates all pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
