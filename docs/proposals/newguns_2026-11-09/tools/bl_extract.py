# Untrusted FBX -> every triangle corner (world position, corner normal, UV), its loose-part id, object and material -> <out>/tris.npz
# (the fg42hd recipe, plus loose-part separation: the Bren source is ONE object, and the magazine / cocking handle / bipod have to be
# told apart). Parts above MIN_TRIS are collapse-decimated to RATIO; small parts are kept whole. Read only, no scripts run.
#   blender -b --factory-startup --disable-autoexec --python bl_extract.py -- <fbx> <out_dir> [rotY_deg] [hide_obj,..]
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Matrix

a = sys.argv[sys.argv.index('--') + 1:]
fbx, out = a[0], a[1]
rot = float(a[2]) if len(a) > 2 and a[2] else 0.0
hide = set(a[3].split(',')) if len(a) > 3 and a[3] else set()
RATIO = float(os.environ.get('NG_RATIO', '0.3'))
MIN_TRIS = int(os.environ.get('NG_MIN_TRIS', '400'))
FLOOR = int(os.environ.get('NG_FLOOR', '0'))       # keep at least ~FLOOR triangles of every decimated part (the MP 28's small parts collapsed to nothing at 2 %)
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.fbx_import(filepath=fbx)
for o in list(bpy.data.objects):
    if o.type != 'MESH' or o.name in hide:
        bpy.data.objects.remove(o)
if os.environ.get('NG_ROTX'):   # the Bren's object is pitched (rot x 77.9 deg, not the FBX's 90): set it level
    for o in bpy.data.objects:
        o.rotation_euler[0] = math.radians(float(os.environ['NG_ROTX']))
    bpy.context.view_layer.update()
R = Matrix.Rotation(math.radians(rot), 4, 'Y')
for o in bpy.data.objects:
    o.matrix_world = R @ o.matrix_world
bpy.context.view_layer.update()
# separate every object into its loose parts
for o in list(bpy.data.objects):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
objs = [o for o in bpy.data.objects if o.type == 'MESH']
import json
PR = {int(k): v for k, v in json.loads(os.environ.get('NG_PART_RATIO', '{}')).items()}   # per loose part (index in objs)
for pi, o in enumerate(objs):
    o.data.calc_loop_triangles()
    n = len(o.data.loop_triangles); print("PART", pi, o.name, n)
    r = PR.get(pi, (max(RATIO, min(1.0, FLOOR / max(n, 1))) if FLOOR else RATIO) if n > MIN_TRIS else 1.0)
    if r < 1.0:
        m = o.modifiers.new('dec', 'DECIMATE'); m.decimate_type = 'COLLAPSE'; m.ratio = r; m.use_collapse_triangulate = True
    o.modifiers.new('tri', 'TRIANGULATE')
dg = bpy.context.evaluated_depsgraph_get(); dg.update()
rows, part, obj, mat = [], [], [], []
for pi, o in enumerate(objs):
    oe = o.evaluated_get(dg); me = oe.to_mesh(); me.calc_loop_triangles()
    uvl = me.uv_layers.active.data
    MW = o.matrix_world; NM = MW.to_3x3().inverted().transposed()
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    for t in me.loop_triangles:
        for k in range(3):
            li = t.loops[k]; vi = t.vertices[k]
            p = MW @ me.vertices[vi].co
            n = (NM @ me.corner_normals[li].vector).normalized()
            uv = uvl[li].uv
            rows.append((p.x, p.y, p.z, n.x, n.y, n.z, uv[0], uv[1]))
        part.append(pi); obj.append(o.name.split('.')[0]); mat.append(mats[t.material_index] if mats else '')
    oe.to_mesh_clear()
A = np.array(rows, np.float32).reshape(-1, 3, 8)
np.savez(os.path.join(out, 'tris.npz'), corners=A, part=np.array(part), obj=np.array(obj), mat=np.array(mat))
print('PARTS', len(objs), 'TOTAL tris', len(part))
