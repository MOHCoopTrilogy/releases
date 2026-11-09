# list the FBX's objects / materials / triangle counts / bounds (Blender, background). Untrusted data: read only.
import bpy, sys
fbx = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.fbx_import(filepath=fbx)
for o in bpy.data.objects:
    if o.type == 'MESH':
        me = o.data; me.calc_loop_triangles()
        bb = [o.matrix_world @ v.co for v in me.vertices]
        mn = [min(p[i] for p in bb) for i in range(3)]; mx = [max(p[i] for p in bb) for i in range(3)]
        uv = me.uv_layers.active.data if me.uv_layers.active else None
        us = [d.uv for d in uv] if uv else []
        print('OBJ %-28s tris %6d mats %s uv %s..%s bounds %s %s' % (o.name, len(me.loop_triangles), [m.name for m in me.materials if m],
              [round(min(u[0] for u in us), 2), round(min(u[1] for u in us), 2)] if us else None,
              [round(max(u[0] for u in us), 2), round(max(u[1] for u in us), 2)] if us else None,
              [round(v, 3) for v in mn], [round(v, 3) for v in mx]))
    else:
        print('OBJ %-28s %s' % (o.name, o.type))
