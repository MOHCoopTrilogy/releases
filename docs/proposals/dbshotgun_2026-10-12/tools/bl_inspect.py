# Blender (background, factory startup, autoexec off): list what is in a .blend
#   blender --background --factory-startup --disable-autoexec --python tools/bl_inspect.py -- <file.blend>
import bpy, sys
from mathutils import Vector

path = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.open_mainfile(filepath=path, load_ui=False, use_scripts=False)
print('FILE', path)
print('UNIT', bpy.context.scene.unit_settings.system, bpy.context.scene.unit_settings.scale_length)
print('TEXTS', [t.name for t in bpy.data.texts])
print('IMAGES', [(i.name, i.filepath, tuple(i.size), i.packed_file is not None) for i in bpy.data.images])
dg = bpy.context.evaluated_depsgraph_get()
tot = 0
for o in bpy.data.objects:
    if o.type != 'MESH':
        print('OBJ', o.name, o.type, 'parent', o.parent.name if o.parent else None)
        continue
    m = o.data
    m.calc_loop_triangles()
    eo = o.evaluated_get(dg)
    em = eo.to_mesh()
    em.calc_loop_triangles()
    ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = [min(w[i] for w in ws) for i in range(3)]
    mx = [max(w[i] for w in ws) for i in range(3)]
    print('MESH', repr(o.name), 'verts', len(m.vertices), 'tris', len(m.loop_triangles),
          'evaltris', len(em.loop_triangles), 'mods', [(md.type, md.show_viewport) for md in o.modifiers],
          'mats', [s.material.name if s.material else None for s in o.material_slots],
          'uv', [u.name for u in m.uv_layers], 'parent', o.parent.name if o.parent else None,
          'hide', o.hide_viewport, o.hide_render,
          'loc', [round(v, 4) for v in o.matrix_world.translation],
          'scale', [round(v, 4) for v in o.scale],
          'bbmin', [round(v, 4) for v in mn], 'bbmax', [round(v, 4) for v in mx])
    # loose parts
    import bmesh
    bm = bmesh.new(); bm.from_mesh(m)
    seen = set(); parts = []
    for v in bm.verts:
        if v.index in seen: continue
        st = [v]; seen.add(v.index); idx = [v]
        while st:
            a = st.pop()
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); st.append(b); idx.append(b)
        cs = [o.matrix_world @ q.co for q in idx]
        pmn = [round(min(c[i] for c in cs), 3) for i in range(3)]
        pmx = [round(max(c[i] for c in cs), 3) for i in range(3)]
        mats = sorted({f.material_index for q in idx for f in q.link_faces})
        parts.append((len(idx), pmn, pmx, mats))
    bm.free()
    print('  LOOSE PARTS', len(parts))
    for p in sorted(parts, key=lambda p: -p[0]):
        print('   ', p)
    tot += len(em.loop_triangles)
    eo.to_mesh_clear()
print('TOTAL EVAL TRIS', tot)
for mt in bpy.data.materials:
    print('MAT', mt.name, 'nodes', [(n.type, getattr(getattr(n, 'image', None), 'name', None)) for n in (mt.node_tree.nodes if mt.node_tree else [])])
