"""mk_smoke.py - smoke & fire Phase 1 smoke flipbooks (copied from fx_1025 mk_fx.py; adds billow / soot / dust presets).
Our own renders (Blender GPL, output ours, CC0-compatible). Run:
  blender -b -noaudio -t 4 --python mk_fx.py -- <preset> <outdir> [--res N] [--frames A:B] [--px N] [--bake-only|--render-only]

Presets (all units metres-ish, 1 BU = 1 m; sprites are rendered by an ORTHOGRAPHIC side camera and exported as frames):
  fireball   one-shot blast (grenade / shell): burst of fuel+smoke, radial velocity, buoyant mushroom. 2 layers:
             <out>/fire/f_0001.png  RGB emission on black (additive blend in-engine)
             <out>/smoke/s_0001.png RGBA lit smoke (straight alpha; blend in-engine)
  bigblast   same with 3x the fuel and a slower, taller plume (tank / truck / fuel dump)
  flame      continuous flame on a small source (campfire / barrel / torch), steady-state window exported as a loop
  smokecol   dark smoke column puff (rising smoke, wreck smoke); RGBA

Everything is deterministic (fixed seed) so a re-run reproduces the frames. CPU Cycles only, -t 4 by the caller.
"""
import bpy, sys, os, math, random

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
preset, outdir = argv[0], argv[1]
opt = {}
i = 2
while i < len(argv):
    if argv[i].startswith("--"):
        k = argv[i][2:]
        if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            opt[k] = argv[i + 1]; i += 2
        else:
            opt[k] = True; i += 1
    else:
        i += 1
RES = int(opt.get("res", 128))
PX = int(opt.get("px", 256))
SAMPLES = int(opt.get("samples", 48))
random.seed(1025)

P = {
    "fireball": dict(dom=(3.2, 3.2, 4.4), cen_z=1.6, nframes=64, fuel=4.0, burst=5, vel=7.0, rad=0.35, buoy_a=1.0, buoy_b=2.2,
                     flame_vort=1.2, vort=0.6, burn=0.9, dissolve=60, smoke_amt=1.4, flame_smoke=0.5, steady=False, export=(2, 64)),
    "bigblast": dict(dom=(5.0, 5.0, 7.0), cen_z=2.2, nframes=84, fuel=9.0, burst=8, vel=6.0, rad=0.8, buoy_a=0.9, buoy_b=2.4,
                     flame_vort=1.0, vort=0.5, burn=0.6, dissolve=90, smoke_amt=2.0, flame_smoke=0.8, steady=False, export=(2, 84)),
    "flame": dict(dom=(1.6, 1.6, 3.2), cen_z=0.15, nframes=150, fuel=1.0, burst=0, vel=0.0, rad=0.28, buoy_a=0.6, buoy_b=2.0,
                  flame_vort=1.6, vort=0.9, burn=1.4, dissolve=25, smoke_amt=0.6, flame_smoke=0.2, steady=True, export=(100, 131)),
    "smokecol": dict(dom=(3.0, 3.0, 5.5), cen_z=0.3, nframes=120, fuel=0.0, burst=0, vel=0.0, rad=0.45, buoy_a=1.3, buoy_b=0.0,
                     flame_vort=0.0, vort=0.9, burn=0.0, dissolve=0, smoke_amt=2.2, flame_smoke=0.0, steady=True, export=(60, 91)),
    # [smoke&fire Phase 1] one rolling billow that blooms, swells and thins (a smoke-grenade bank, a column puff, the
    # M18 cloud): rendered NEUTRAL light grey so one set serves white / grey / coloured signal smoke via the tik colour
    "billow": dict(dom=(3.4, 3.4, 3.4), cen_z=0.35, nframes=110, fuel=0.0, burst=6, vel=2.4, rad=0.55, buoy_a=0.35, buoy_b=0.0,
                   flame_vort=0.0, vort=1.4, burn=0.0, dissolve=0, smoke_amt=2.6, flame_smoke=0.0, steady=False, export=(14, 109)),
    # dark soot billow (wreck columns, burning buildings): same motion, dense and dark (scol set by the caller)
    "soot": dict(dom=(3.4, 3.4, 3.8), cen_z=0.35, nframes=110, fuel=0.0, burst=6, vel=2.0, rad=0.55, buoy_a=0.6, buoy_b=0.0,
                 flame_vort=0.0, vort=1.2, burn=0.0, dissolve=0, smoke_amt=3.0, flame_smoke=0.0, steady=False, export=(14, 109)),
    # low dust skirt (blast dust, crate breaks): wide, flat, fast out then settling
    "dust": dict(dom=(4.4, 4.4, 2.0), cen_z=0.2, nframes=90, fuel=0.0, burst=3, vel=4.5, rad=0.45, buoy_a=0.08, buoy_b=0.0,
                 flame_vort=0.0, vort=1.0, burn=0.0, dissolve=0, smoke_amt=2.0, flame_smoke=0.0, steady=False, export=(4, 89)),
}[preset]
SMOKE_ONLY = preset in ("smokecol", "billow", "soot", "dust")
for _k in list(P.keys()):
    if _k in opt and isinstance(P[_k], (int, float)) and not isinstance(P[_k], bool):
        P[_k] = type(P[_k])(float(opt[_k]))
bake_only = "bake-only" in opt
render_only = "render-only" in opt
if "frames" in opt:
    a, b = opt["frames"].split(":"); P["export"] = (int(a), int(b))

os.makedirs(outdir, exist_ok=True)
cache = os.path.join(outdir, "cache")
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, P["nframes"]
sc.render.fps = 30
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = PX
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.color_depth = "16"
sc.view_settings.view_transform = "Standard"
sc.cycles.volume_bounces = 1
sc.cycles.volume_step_rate = 1.0

dx, dy, dz = P["dom"]
if "domx" in opt:
    dx = dy = float(opt["domx"]); dz = float(opt.get("domz", dz))
P["cen_z"] = float(opt.get("cenz", P["cen_z"]))
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, dz / 2))
dom = bpy.context.object
dom.name = "Domain"; dom.scale = (dx, dy, dz)
m = dom.modifiers.new("Fluid", "FLUID"); m.fluid_type = "DOMAIN"
d = m.domain_settings
d.domain_type = "GAS"
d.resolution_max = RES
d.cache_type = "ALL"
d.cache_directory = cache
d.use_noise = "noise" in opt   # 5.1: a noise bake renders NOTHING from the cache (verified 2026-10-26) - use base resolution instead
d.noise_scale = 2
d.noise_strength = 1.0
d.noise_pos_scale = 1.4
d.noise_time_anim = 0.5
d.alpha = P["buoy_a"]; d.beta = P["buoy_b"]
d.vorticity = P["vort"]
d.use_dissolve_smoke = P["dissolve"] > 0
d.dissolve_speed = max(1, P["dissolve"])
d.burning_rate = P["burn"]
d.flame_smoke = P["flame_smoke"]
d.flame_vorticity = P["flame_vort"]
d.flame_ignition = float(opt.get("ign", 1.0))
d.flame_max_temp = 3.0
d.flame_smoke_color = (0.04, 0.04, 0.04)
d.use_adaptive_timesteps = True
d.cfl_condition = 3.0
sc.frame_current = 1

# flow source (sphere); the burst stops after P['burst'] frames, steady presets keep it on
bpy.ops.mesh.primitive_uv_sphere_add(radius=P["rad"], location=(0, 0, P["cen_z"]), segments=24, ring_count=12)
fl = bpy.context.object
fl.name = "Flow"
fm = fl.modifiers.new("Fluid", "FLUID"); fm.fluid_type = "FLOW"
f = fm.flow_settings
f.flow_type = "BOTH" if not SMOKE_ONLY else "SMOKE"
f.flow_behavior = "GEOMETRY" if P["burst"] else "INFLOW"
f.flow_source = "MESH"
f.surface_distance = float(opt.get("sd", 1.0))
f.volume_density = 1.0
fl.hide_render = True
f.smoke_color = (0.12, 0.11, 0.1)
f.density = P["smoke_amt"]
f.temperature = 1.0 if not SMOKE_ONLY else 0.0
f.fuel_amount = P["fuel"] if not SMOKE_ONLY else 0.0
f.subframes = 2
if P["vel"] > 0:
    f.use_initial_velocity = True
    f.velocity_normal = P["vel"]
    f.velocity_random = 1.5
if False:
    for fr, v in ((1, 1.0), (P["burst"], 1.0), (P["burst"] + 1, 0.0)):
        f.fuel_amount = P["fuel"] * v; f.keyframe_insert("fuel_amount", frame=fr)
        f.density = P["smoke_amt"] * v; f.keyframe_insert("density", frame=fr)
    for fc in fl.animation_data.action.fcurves if hasattr(fl.animation_data.action, "fcurves") else []:
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"

# ---------------- materials
def vol_material(emit_only):
    mat = bpy.data.materials.new("Vol_" + ("fire" if emit_only else "smoke"))
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    nt.links.new(pv.outputs["Volume"], out.inputs["Volume"])
    _sc = float(opt.get("scol", 0.42))
    pv.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0) if emit_only else (_sc, _sc * 0.95, _sc * 0.9, 1.0)
    pv.inputs["Density"].default_value = 1.0 if not emit_only else 0.6
    pv.inputs["Absorption Color"].default_value = (0.0, 0.0, 0.0, 1.0) if emit_only else (0.1, 0.1, 0.1, 1.0)
    pv.inputs["Anisotropy"].default_value = 0.3
    pv.inputs["Emission Strength"].default_value = 0.0
    pv.inputs["Density Attribute"].default_value = "density"
    pv.inputs["Temperature Attribute"].default_value = "temperature"
    pv.inputs["Temperature"].default_value = float(opt.get("temp", 1000.0))
    if emit_only:
        pv.inputs["Density"].default_value = float(opt.get("fdens", 2.0))
        pv.inputs["Blackbody Intensity"].default_value = float(opt.get("bb", 1.0))
        pv.inputs["Blackbody Tint"].default_value = (1.0, 0.85, 0.65, 1.0)
    else:
        pv.inputs["Density"].default_value = float(opt.get("sdens", 5.0))
        pv.inputs["Blackbody Intensity"].default_value = 0.0
    # --- procedural turbulence on top of the (noise-free, smooth) Mantaflow grid: 4D fBm in WORLD space (isotropic),
    # the W axis advanced per frame so the cells boil. Multiplies density (and, on the fire pass, the blackbody emission).
    # Blender 5.1: a baked Mantaflow NOISE upres renders nothing from the cache, so the detail has to come from here.
    nsc = float(opt.get("nscale", 2.4)); ngain = float(opt.get("ngain", 1.0))
    if ngain > 0:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (nsc, nsc, nsc)
        # drift the noise upward with the buoyant gas: location z follows the frame (set per frame in render loop)
        nt.links.new(geo.outputs["Position"], mp.inputs["Vector"])
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"
        nz.inputs["Detail"].default_value = float(opt.get("ndetail", 9.0)); nz.inputs["Roughness"].default_value = 0.62
        nz.inputs["Distortion"].default_value = float(opt.get("ndist", 0.8)); nz.inputs["Scale"].default_value = 1.0
        nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
        wv = nt.nodes.new("ShaderNodeValue"); wv.name = "WVAL"
        nt.links.new(wv.outputs[0], nz.inputs["W"])
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.clamp = True
        mr.inputs["From Min"].default_value = 0.34; mr.inputs["From Max"].default_value = 0.72
        mr.inputs["To Min"].default_value = 1.0 - 0.75 * ngain; mr.inputs["To Max"].default_value = 1.0 + 1.1 * ngain
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "MULTIPLY"
        mu.inputs[1].default_value = pv.inputs["Density"].default_value
        nt.links.new(mr.outputs["Result"], mu.inputs[0])
        nt.links.new(mu.outputs[0], pv.inputs["Density"])
        if emit_only:
            mb = nt.nodes.new("ShaderNodeMath"); mb.operation = "MULTIPLY"
            mb.inputs[1].default_value = pv.inputs["Blackbody Intensity"].default_value
            nt.links.new(mr.outputs["Result"], mb.inputs[0])
            nt.links.new(mb.outputs[0], pv.inputs["Blackbody Intensity"])
    return mat

mat_fire = vol_material(True)
mat_smoke = vol_material(False)

# camera: ortho, side view along +Y, domain fits frame
bpy.ops.object.camera_add(location=(0, -10, dz / 2), rotation=(math.pi / 2, 0, 0))
cam = bpy.context.object
cam.data.type = "ORTHO"
cam.data.ortho_scale = max(dx, dz) * (1.0 if preset in ("flame",) or SMOKE_ONLY else 0.95)
sc.camera = cam
if preset in ("flame",):
    cam.location.z = dz / 2

# lights for the smoke layer: warm fill from the fireball plus cool sky
bpy.ops.object.light_add(type="POINT", location=(0, -1.5, P["cen_z"]))
lt = bpy.context.object
lt.data.energy = 0
lt.data.color = (1.0, 0.62, 0.3)
lt.data.shadow_soft_size = 0.8
w = bpy.data.worlds.new("W"); sc.world = w
w.use_nodes = True
bgn = w.node_tree.nodes["Background"]
bgn.inputs["Color"].default_value = (0.55, 0.62, 0.72, 1.0)
bgn.inputs["Strength"].default_value = 0.7

def set_pass(layer):
    for ob in list(dom.data.materials):
        pass
    dom.data.materials.clear()
    dom.data.materials.append(mat_fire if layer == "fire" else mat_smoke)
    lt.data.energy = 0 if layer == "fire" else 0   # set per frame below
    bgn.inputs["Strength"].default_value = 0.0 if layer == "fire" else 0.7

if not render_only:
    bpy.ops.fluid.bake_all() if False else None
    bpy.context.view_layer.objects.active = dom
    bpy.ops.fluid.bake_data()
    if d.use_noise:
        bpy.ops.fluid.bake_noise()
    print("BAKE DONE", preset)
if bake_only:
    sys.exit(0)

a, b = P["export"]
looks = [("", {})]
if "looks" in opt:   # "A:bb=0.5,ngain=1.8;B:bb=0.8" - several looks from ONE bake (the bake is the expensive part)
    looks = []
    for part in str(opt["looks"]).split(";"):
        nm, kv = part.split(":", 1)
        looks.append((nm, dict(x.split("=") for x in kv.split(",") if x)))
for lname, kv in looks:
    opt.update(kv)
    sc.view_settings.view_transform = opt.get('vt', 'Standard')
    mat_fire = vol_material(True); mat_smoke = vol_material(False)
    for layer in [l for l in (("fire", "smoke") if not SMOKE_ONLY else ("smoke",)) if l in str(opt.get("layers", "fire,smoke")).split(",")]:
        set_pass(layer)
        ld = os.path.join(outdir, lname, layer) if lname else os.path.join(outdir, layer)
        os.makedirs(ld, exist_ok=True)
        for k, fr in enumerate(range(a, b + 1, int(opt.get('step', 1)))):
            sc.frame_set(fr)
            for _m in (mat_fire, mat_smoke):
                _w = _m.node_tree.nodes.get('WVAL')
                if _w: _w.outputs[0].default_value = fr * float(opt.get('wspeed', 0.07))
            if layer == "smoke" and preset in ("fireball", "bigblast"):
                t = (fr - a) / max(1, b - a)
                lt.data.energy = 4000.0 * math.exp(-5.0 * t) * (P["rad"] + 0.6)
            sc.render.filepath = os.path.join(ld, "%s_%04d.png" % (layer[0], k + 1))
            bpy.ops.render.render(write_still=True)
            print("RENDERED", lname, layer, fr)
print("ALL DONE", preset)
