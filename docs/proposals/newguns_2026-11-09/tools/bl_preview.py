# Preview render of an untrusted FBX + its PBR texture folder (Blender, background, read only).
# blender -b --factory-startup --disable-autoexec --python bl_preview.py -- <fbx> <texdir> <outprefix> [hide_obj,..]
import bpy, sys, os, math, glob
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
fbx, texdir, outp = a[0], a[1], a[2]
hide = set(a[3].split(',')) if len(a) > 3 and a[3] else set()

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.fbx_import(filepath=fbx)
for o in list(bpy.data.objects):
    if o.type != 'MESH' or o.name in hide:
        bpy.data.objects.remove(o)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
if len(a) > 4:  # level a tilted source: degrees about world Y
    import mathutils
    R = mathutils.Matrix.Rotation(math.radians(float(a[4])), 4, 'Y')
    for o in meshes: o.matrix_world = R @ o.matrix_world
    bpy.context.view_layer.update()

texs = [f for f in glob.glob(os.path.join(texdir, '*')) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tga'))]
def key(s): return s.lower().replace(' ', '_').replace('-', '_')
CH = {'basecolor': ['basecolor', 'base_color', 'albedo', 'diffuse'], 'normal': ['normal'],
      'rough': ['roughness'], 'metal': ['metallic', 'metalness'], 'ao': ['_ao']}
def find(mname, ch, single):
    for f in texs:
        b = key(os.path.basename(f))
        if any(c in b for c in CH[ch]) and (single or b.startswith(key(mname))):
            if ch == 'normal' and 'internal' in b: continue
            return f
    return None

mats = {m for o in meshes for m in o.data.materials if m}
single = len(mats) == 1
for m in mats:
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs[0], out.inputs[0])
    def img(ch, color):
        f = find(m.name, ch, single)
        if not f: return None
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(f)
        if not color: n.image.colorspace_settings.name = 'Non-Color'
        return n
    bc = img('basecolor', True); ao = img('ao', False)
    if bc and ao:
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1.0
        nt.links.new(bc.outputs[0], mix.inputs[6]); nt.links.new(ao.outputs[0], mix.inputs[7])
        nt.links.new(mix.outputs[2], bs.inputs['Base Color'])
    elif bc: nt.links.new(bc.outputs[0], bs.inputs['Base Color'])
    r = img('rough', False)
    if r: nt.links.new(r.outputs[0], bs.inputs['Roughness'])
    mt = img('metal', False)
    if mt: nt.links.new(mt.outputs[0], bs.inputs['Metallic'])
    n = img('normal', False)
    if n:
        nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(n.outputs[0], nm.inputs['Color'])
        nt.links.new(nm.outputs[0], bs.inputs['Normal'])
    print('MAT', m.name, [os.path.basename(x) if x else None for x in
          (find(m.name, c, single) for c in CH)])

pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
ctr = (mn + mx) / 2; ext = mx - mn
L = max(ext); ax_long = list(ext).index(L)
ax_up = 2  # Blender imports Z-up; a side magazine can make Y the widest short axis
ax_thin = 3 - ax_long - ax_up
print('BOUNDS', [round(v, 3) for v in ext], 'long', ax_long, 'thin', ax_thin, 'up', ax_up)

sc = bpy.context.scene
try: sc.render.engine = 'BLENDER_EEVEE'
except Exception: sc.render.engine = 'BLENDER_EEVEE_NEXT'
try: sc.eevee.taa_render_samples = 32
except Exception: pass
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.32, 0.33, 0.35, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.9

def vec(i, s=1.0):
    v = Vector((0, 0, 0)); v[i] = s; return v
up = vec(ax_up)
for i, (d, e) in enumerate([((vec(ax_thin) + up * 0.6 + vec(ax_long) * 0.4), 3.0), ((-vec(ax_thin) + up * 0.8), 2.0)]):
    ld = bpy.data.lights.new('l%d' % i, 'SUN'); ld.energy = e
    lo = bpy.data.objects.new('l%d' % i, ld); sc.collection.objects.link(lo)
    lo.rotation_euler = (d.normalized()).to_track_quat('Z', 'Y' if ax_up != 1 else 'Z').to_euler()

cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'
cam = bpy.data.objects.new('c', cd); sc.collection.objects.link(cam); sc.camera = cam
views = {'side': -vec(ax_thin), 'side2': vec(ax_thin), 'q34': (-vec(ax_thin) + up * 0.5 + vec(ax_long) * 0.6)}
for nm, d in views.items():
    d = d.normalized()
    cam.location = ctr + d * L * 3
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cd.ortho_scale = L * 1.08
    cd.clip_end = L * 10
    sc.render.filepath = outp + '_' + nm + '.png'
    bpy.ops.render.render(write_still=True)
    print('WROTE', sc.render.filepath)
