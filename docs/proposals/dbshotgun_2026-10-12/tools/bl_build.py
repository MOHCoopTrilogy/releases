# Blender (background, factory startup, autoexec off): source .blend files -> game-ready part meshes + ONE diffuse sheet
#   blender --background --factory-startup --disable-autoexec --python tools/bl_build.py -- <srcdir> <builddir> [--tex 2048]
#
# First-person mesh = the HIGH file (modifiers applied as the author set them for the viewport), flat/straight runs
#   dissolved (planar decimate, no silhouette change), triangulated, joined into 5 rigid parts:
#       barrels (barrels + lumps + forend wood)   body (receiver, fences, stock, guard, pins, safety)
#       lever (top lever)   trig_f / trig_r (the two triggers)
#   The high file has NO baked textures (procedural materials), so: new UV atlas over all parts (smart project, one
#   sheet), colour = the author's own baked diffuse (doubleBarrelD.png, made for the LOW file) projected from the low
#   mesh onto the high one (Cycles emit bake, selected-to-active), times an ambient-occlusion bake of each part ALONE
#   (so the faces that the opened action shows are not black).
# World mesh = the LOW file as it is, with the author's UVs; its sheet = diffuse x AO from the zip.
# Frame written out: hinge pin on the origin, +x muzzle, +y LEFT, +z up, Blender units (the game frame is made later).
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = args[0], args[1]
TEX = int(args[args.index('--tex') + 1]) if '--tex' in args else 2048
os.makedirs(OUT, exist_ok=True)

PARTS = {
    'Cylinder': 'barrels', 'Cylinder.003': 'barrels',
    'Cylinder.001': 'body', 'Cylinder.002': 'body', 'Cylinder.004': 'body', 'Cylinder.005': 'body',
    'Circle': 'body', 'Circle.001': 'body', 'Circle.002': 'body', 'Cylinder.006': 'body',
    'Plane': 'lever', 'Cylinder.007': 'trig',
}
PLANAR_DEG = 1.0

bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, 'doubleBarrelHight.blend'), load_ui=False, use_scripts=False)
sc = bpy.context.scene
vl = bpy.context.view_layer


def only(o, extra=()):
    bpy.ops.object.select_all(action='DESELECT')
    for e in extra:
        e.select_set(True)
    o.select_set(True)
    vl.objects.active = o


for o in list(bpy.data.objects):
    if o.type != 'MESH':
        bpy.data.objects.remove(o)

SHIFT = Vector(bpy.data.objects['Cylinder'].location)      # low file = high file minus this (its barrels sit at 0)
SHIFT.y = 0.0                                               # keep the high file's mirror plane on y = 0
print('SHIFT', tuple(SHIFT))

objs = [o for o in bpy.data.objects if o.type == 'MESH']
for o in objs:
    o.hide_set(False); o.hide_render = False
    only(o)
    wood = [('wood' in (s.material.name.lower() if s.material else '')) for s in o.material_slots]
    bpy.ops.object.convert(target='MESH')                   # applies the viewport modifier stack
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    m = o.data
    m.transform(__import__('mathutils').Matrix.Translation(-SHIFT))
    a = m.attributes.new('wood', 'INT', 'FACE')
    a.data.foreach_set('value', [int(wood[p.material_index]) if wood else 0 for p in m.polygons])
    n0 = sum(len(p.vertices) - 2 for p in m.polygons)
    md = o.modifiers.new('pl', 'DECIMATE'); md.decimate_type = 'DISSOLVE'; md.angle_limit = math.radians(PLANAR_DEG)
    md.delimit = {'MATERIAL'}
    bpy.ops.object.modifier_apply(modifier=md.name)
    bm = bmesh.new(); bm.from_mesh(m)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(m); bm.free()
    print('PART', o.name, PARTS[o.name], 'tris', n0, '->', len(m.polygons))

# the two triggers are one object: split by loose parts, name by x (front trigger = further forward)
t = bpy.data.objects['Cylinder.007']
before = set(bpy.data.objects)
only(t)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5)
bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
trigs = [t] + [o for o in bpy.data.objects if o not in before]
print('TRIGGER PIECES', [(o.name, len(o.data.polygons)) for o in trigs])
groups = {'barrels': [], 'body': [], 'lever': [], 'trig_f': [], 'trig_r': []}
# mirror modifier already welded each trigger into one piece -> 2 loose parts expected; more = halves, group by x
xs = [sum((v.co.x for v in o.data.vertices)) / len(o.data.vertices) for o in trigs]
mid = (max(xs) + min(xs)) / 2
for o, x in zip(trigs, xs):
    groups['trig_f' if x > mid else 'trig_r'].append(o)
for o in bpy.data.objects:
    if o.type == 'MESH' and o not in trigs:
        groups[PARTS[o.name]].append(o)

parts = {}
for name, lst in groups.items():
    only(lst[0], lst)
    if len(lst) > 1:
        bpy.ops.object.join()
    o = vl.objects.active
    o.name = 'P_' + name
    m = o.data
    for p in m.polygons:
        p.use_smooth = True
    m.set_sharp_from_angle(angle=math.radians(40))
    parts[name] = o
    print('GROUP', name, 'verts', len(m.vertices), 'tris', len(m.polygons))

# ---- one UV atlas over all parts
allp = list(parts.values())
for o in allp:
    for uv in list(o.data.uv_layers):
        o.data.uv_layers.remove(uv)
    o.data.uv_layers.new(name='atlas')
only(allp[0], allp)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0025, area_weight=0.0, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')

# ---- bake targets
img_d = bpy.data.images.new('bake_d', TEX, TEX, alpha=True)
img_d.generated_color = (1, 0, 1, 0)
img_ao = bpy.data.images.new('bake_ao', TEX, TEX, alpha=True)
img_ao.generated_color = (1, 1, 1, 0)
mat = bpy.data.materials.new('dbs_bake'); mat.use_nodes = True
nt = mat.node_tree
tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img_d
nt.nodes.active = tn
for o in allp:
    o.data.materials.clear(); o.data.materials.append(mat)

# ---- the low file's meshes, in the same frame, emitting the author's baked diffuse
with bpy.data.libraries.load(os.path.join(SRC, 'doubleBarrelLow.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
lows = []
dimg = bpy.data.images.load(os.path.join(SRC, 'doubleBarrelD.png'))
em = bpy.data.materials.new('low_emit'); em.use_nodes = True
ent = em.node_tree
for n in list(ent.nodes):
    ent.nodes.remove(n)
eo = ent.nodes.new('ShaderNodeOutputMaterial'); ee = ent.nodes.new('ShaderNodeEmission'); et = ent.nodes.new('ShaderNodeTexImage')
et.image = dimg
ent.links.new(et.outputs['Color'], ee.inputs['Color']); ent.links.new(ee.outputs[0], eo.inputs['Surface'])
low_y = None
for o in dst.objects:
    if o is None or o.type != 'MESH':
        continue
    sc.collection.objects.link(o)
    lows.append(o)
lowshift = Vector((0.0, -bpy.data.objects['Cylinder'].location.y if 'Cylinder' in bpy.data.objects else 0.0, 0.0))
# y centre of the low barrels = the offset the author moved the low file sideways by
lb = [o for o in lows if o.name.startswith('Cylinder') and len(o.data.vertices) > 500][0]
ys = [(lb.matrix_world @ v.co).y for v in lb.data.vertices]
LOWY = (max(ys) + min(ys)) / 2
print('LOW Y CENTRE', LOWY)
for o in lows:
    o.location.y -= LOWY
    o.data.materials.clear(); o.data.materials.append(em)
vl.update()

sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.cycles.samples = 4
bk = sc.render.bake
bk.use_selected_to_active = True
bk.cage_extrusion = 0.03
bk.max_ray_distance = 0.09
bk.margin = 0                 # dbs_tex.py grows the islands itself (the bake margin left magenta fringes in the 2nd sheet)
bk.use_clear = False
for name, o in parts.items():
    only(o, lows)
    bpy.ops.object.bake(type='EMIT')
    print('BAKED D', name)

# the author's "glossy" sheet the same way: his diffuse is BLACK on the steel (metal workflow), the steel's colour and
# its scratches live in the glossy sheet - a diffuse-only renderer needs both
img_g = bpy.data.images.new('bake_g', TEX, TEX, alpha=True)
img_g.generated_color = (1, 0, 1, 0)
tn.image = img_g
et.image = bpy.data.images.load(os.path.join(SRC, 'doubleBarrelG.png'))
for name, o in parts.items():
    only(o, lows)
    bpy.ops.object.bake(type='EMIT')
    print('BAKED G', name)
g = np.empty(TEX * TEX * 4, np.float32); img_g.pixels.foreach_get(g)
np.save(os.path.join(OUT, 'bake_g.npy'), g.reshape(TEX, TEX, 4)[::-1])

# ---- ambient occlusion, each part alone
tn.image = img_ao
bk.use_selected_to_active = False
sc.cycles.samples = 48
for o in lows:
    o.hide_render = True
for name, o in parts.items():
    for q in allp:
        q.hide_render = (q is not o)
    only(o)
    bpy.ops.object.bake(type='AO')
    print('BAKED AO', name)
for q in allp:
    q.hide_render = False

d = np.empty(TEX * TEX * 4, np.float32); img_d.pixels.foreach_get(d); d = d.reshape(TEX, TEX, 4)
ao = np.empty(TEX * TEX * 4, np.float32); img_ao.pixels.foreach_get(ao); ao = ao.reshape(TEX, TEX, 4)
np.save(os.path.join(OUT, 'bake_d.npy'), d[::-1])           # top row first, linear float RGBA
np.save(os.path.join(OUT, 'bake_ao.npy'), ao[::-1])
miss = (d[..., 3] > 0.5) & (d[..., 0] > 0.9) & (d[..., 1] < 0.1) & (d[..., 2] > 0.9)
print('ATLAS covered %.1f %%, magenta (bake missed) %.2f %% of covered' % (100 * (d[..., 3] > 0.5).mean(), 100 * miss.sum() / max(1, (d[..., 3] > 0.5).sum())))


def dump(o, uvname):
    m = o.data
    m.calc_loop_triangles()
    uv = m.uv_layers[uvname].data
    cn = m.corner_normals
    wood = m.attributes.get('wood')
    tris = []
    for t in m.loop_triangles:
        tri = []
        for li in t.loops:
            v = m.vertices[m.loops[li].vertex_index].co
            w = o.matrix_world @ v
            n = (o.matrix_world.to_3x3() @ Vector(cn[li].vector)).normalized()
            tri.append([round(w.x, 5), round(w.y, 5), round(w.z, 5), round(n.x, 4), round(n.y, 4), round(n.z, 4),
                        round(uv[li].uv.x, 5), round(1.0 - uv[li].uv.y, 5)])
        tris.append(tri)
    return tris


out = {'frame': 'hinge pin at origin, +x muzzle, +y left, +z up, Blender units', 'parts': {}}
for name, o in parts.items():
    out['parts'][name] = dump(o, 'atlas')
    print('DUMP', name, len(out['parts'][name]))
json.dump(out, open(os.path.join(OUT, 'high_parts.json'), 'w'))

lo = {'frame': out['frame'], 'parts': {}}
for o in lows:
    m = o.data
    for p in m.polygons:
        p.use_smooth = True
    m.set_sharp_from_angle(angle=math.radians(40))
    lo['parts'][o.name] = dump(o, 'UVMap')
    print('DUMP LOW', o.name, len(lo['parts'][o.name]))
json.dump(lo, open(os.path.join(OUT, 'low_parts.json'), 'w'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'dbs_work.blend'), compress=True)
print('DONE')
