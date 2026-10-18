# Extract the pistol parts of the downloaded no12u Mauser C96 (CC BY 4.0) in REST pose, per triangle corner, with the
# connected shells of every bone part, as an .npz + shells.json. Untrusted data: read only, no archive content executed.
#   blender --background --factory-startup --disable-autoexec --python bl_extract.py -- <fbx> <out_dir>
import bpy, sys, json, os
import numpy as np
import bmesh

fbx, out = sys.argv[sys.argv.index('--') + 1:][:2]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.fbx_import(filepath=fbx)
ob = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()
me = ob.data
MW = ob.matrix_world
gn = [g.name for g in ob.vertex_groups]
dom = []
for v in me.vertices:
    best = max(v.groups, key=lambda g: g.weight) if v.groups else None
    dom.append(gn[best.group] if best else 'none')

bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
# shells (connected vertex components)
comp = [-1] * len(bm.verts); nc = 0
for v in bm.verts:
    if comp[v.index] >= 0:
        continue
    st = [v]; comp[v.index] = nc
    while st:
        a = st.pop()
        for e in a.link_edges:
            b = e.other_vert(a)
            if comp[b.index] < 0:
                comp[b.index] = nc; st.append(b)
    nc += 1
me.calc_loop_triangles()
uvl = me.uv_layers.active.data
try:
    me.calc_normals_split()
except Exception:
    pass
rows = []   # per corner: x y z nx ny nz u v
tri_part, tri_shell = [], []
NM = MW.to_3x3().inverted().transposed()
for t in me.loop_triangles:
    for k in range(3):
        li = t.loops[k]; vi = t.vertices[k]
        p = MW @ me.vertices[vi].co
        n = (NM @ me.corner_normals[li].vector).normalized() if hasattr(me, 'corner_normals') else (NM @ me.vertices[vi].normal).normalized()
        uv = uvl[li].uv
        rows.append((p.x, p.y, p.z, n.x, n.y, n.z, uv[0], uv[1]))
    tri_part.append(dom[t.vertices[0]]); tri_shell.append(comp[t.vertices[0]])
A = np.array(rows, np.float32).reshape(-1, 3, 8)
np.savez(os.path.join(out, 'tris.npz'), corners=A, part=np.array(tri_part), shell=np.array(tri_shell, np.int32))
sh = {}
for i, (p, s) in enumerate(zip(tri_part, tri_shell)):
    d = sh.setdefault(str(s), {'part': p, 'tris': 0, 'mn': [1e9] * 3, 'mx': [-1e9] * 3})
    d['tris'] += 1
    for k in range(3):
        for a in range(3):
            d['mn'][a] = min(d['mn'][a], float(A[i, k, a])); d['mx'][a] = max(d['mx'][a], float(A[i, k, a]))
json.dump(sh, open(os.path.join(out, 'shells.json'), 'w'), indent=0)
# bone heads (rest) for pivots
bones = {b.name: [list(arm.matrix_world @ b.head_local), list(arm.matrix_world @ b.tail_local), b.parent.name if b.parent else None] for b in arm.data.bones}
json.dump(bones, open(os.path.join(out, 'bones.json'), 'w'), indent=1)
print('corners', A.shape, 'shells', nc, 'material', [m.name for m in me.materials])
