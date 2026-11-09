# FG42 (Shorty_Digitan, Sketchfab d699ac259bd74f70a51125a7e4320f4b, CC BY 4.0): per object, a collapse decimation to the game
# budget, then every triangle corner (world position, corner normal, UV) with its object and material -> <out>/tris.npz.
# Untrusted data: read only, no scripts run (--factory-startup --disable-autoexec).
#   blender --background --factory-startup --disable-autoexec --python bl_extract.py -- <fbx> <out_dir>
import bpy, sys, os, json
import numpy as np

fbx, out = sys.argv[sys.argv.index('--') + 1:][:2]
os.makedirs(out, exist_ok=True)
RATIO = json.loads(os.environ.get('FG_RATIO', '{}')) or {
    'Body': 0.30, 'Barrel': 0.28, 'Bipod': 0.28, 'Rear_sight': 0.40, 'Magazine': 0.60, 'Ejection_port': 1.0, 'Trigger': 1.0, 'Bolt': 1.0}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.fbx_import(filepath=fbx)
rows, obj, mat = [], [], []
dg = bpy.context.evaluated_depsgraph_get()
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    r = RATIO.get(o.name, 1.0)
    if r < 1.0:
        m = o.modifiers.new('dec', 'DECIMATE'); m.decimate_type = 'COLLAPSE'; m.ratio = r; m.use_collapse_triangulate = True
    tri = o.modifiers.new('tri', 'TRIANGULATE')
dg.update()
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    me.calc_loop_triangles()
    uvl = me.uv_layers.active.data
    MW = o.matrix_world; NM = MW.to_3x3().inverted().transposed()
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    n0 = len(obj)
    for t in me.loop_triangles:
        for k in range(3):
            li = t.loops[k]; vi = t.vertices[k]
            p = MW @ me.vertices[vi].co
            n = (NM @ me.corner_normals[li].vector).normalized()
            uv = uvl[li].uv
            rows.append((p.x, p.y, p.z, n.x, n.y, n.z, uv[0], uv[1]))
        obj.append(o.name); mat.append(mats[t.material_index] if mats else o.name)
    print('OBJ %-16s ratio %.2f tris %d' % (o.name, r if (r := RATIO.get(o.name, 1.0)) else 1, len(obj) - n0))
    oe.to_mesh_clear()
A = np.array(rows, np.float32).reshape(-1, 3, 8)
np.savez(os.path.join(out, 'tris.npz'), corners=A, obj=np.array(obj), mat=np.array(mat))
print('TOTAL tris', len(obj))
