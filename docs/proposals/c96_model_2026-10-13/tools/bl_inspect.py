# Blender inspection of the downloaded Sketchfab C96 (untrusted data: read only).
# Run:  blender --background --factory-startup --disable-autoexec --python bl_inspect.py -- <fbx> <out.json>
import bpy, bmesh, sys, json, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
fbx, out = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
imp = "wm.fbx_import" if hasattr(bpy.ops.wm, "fbx_import") else "import_scene.fbx"
if imp == "wm.fbx_import":
    bpy.ops.wm.fbx_import(filepath=fbx)
else:
    bpy.ops.import_scene.fbx(filepath=fbx)

res = {"importer": imp, "blender": bpy.app.version_string,
       "unit_scale": bpy.context.scene.unit_settings.scale_length,
       "frame_range": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
       "fps": bpy.context.scene.render.fps, "objects": [], "armatures": [],
       "actions": [], "materials": [], "images": []}


def islands_stats(bm):
    """signed volume per connected island: negative = inside-out shell"""
    bm.faces.ensure_lookup_table()
    seen = set()
    n_isl = neg = 0
    openisl = 0
    for f in bm.faces:
        if f.index in seen:
            continue
        stack = [f]
        seen.add(f.index)
        vol = 0.0
        nfaces = 0
        isopen = False
        while stack:
            g = stack.pop()
            nfaces += 1
            vs = [v.co for v in g.verts]
            for i in range(1, len(vs) - 1):
                vol += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
            for e in g.edges:
                if len(e.link_faces) == 1:
                    isopen = True
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        n_isl += 1
        if isopen:
            openisl += 1
        elif vol < 0:
            neg += 1
    return n_isl, openisl, neg


tot = 0
for o in bpy.data.objects:
    d = {"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None,
         "parent_bone": o.parent_bone or None,
         "loc": [round(x, 5) for x in o.matrix_world.translation],
         "rot_deg": [round(math.degrees(x), 2) for x in o.matrix_world.to_euler()],
         "scale": [round(x, 5) for x in o.matrix_world.to_scale()],
         "animated": bool(o.animation_data and o.animation_data.action),
         "action": o.animation_data.action.name if o.animation_data and o.animation_data.action else None}
    if o.type == "MESH":
        me = o.data
        me.calc_loop_triangles()
        tris = len(me.loop_triangles)
        tot += tris
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.transform(o.matrix_world)
        bnd = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        wire = sum(1 for e in bm.edges if len(e.link_faces) == 0)
        loose = sum(1 for v in bm.verts if not v.link_edges)
        zero = sum(1 for f in bm.faces if f.calc_area() < 1e-12)
        n_isl, openisl, neg = islands_stats(bm)
        co = [v.co.copy() for v in bm.verts]
        bm.free()
        mn = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
        mx = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
        uvr = None
        if me.uv_layers:
            us = [l.uv for l in me.uv_layers[0].data]
            uvr = [round(min(u.x for u in us), 3), round(min(u.y for u in us), 3),
                   round(max(u.x for u in us), 3), round(max(u.y for u in us), 3)]
        d.update({"verts": len(me.vertices), "polys": len(me.polygons), "tris": tris,
                  "ngons": sum(1 for p in me.polygons if p.loop_total > 4),
                  "bbox_min": [round(x, 5) for x in mn], "bbox_max": [round(x, 5) for x in mx],
                  "size": [round(x, 5) for x in (mx - mn)],
                  "materials": [m.name if m else None for m in me.materials],
                  "uv_layers": [l.name for l in me.uv_layers], "uv_range": uvr,
                  "vgroups": [g.name for g in o.vertex_groups],
                  "modifiers": [(m.type, getattr(getattr(m, "object", None), "name", None)) for m in o.modifiers],
                  "shape_keys": [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
                  "boundary_edges": bnd, "nonmanifold_edges": nonman, "wire_edges": wire,
                  "loose_verts": loose, "zero_area_faces": zero,
                  "islands": n_isl, "open_islands": openisl, "inverted_closed_islands": neg,
                  "custom_normals": bool(getattr(me, "has_custom_normals", False))})
    elif o.type == "ARMATURE":
        res["armatures"].append({"name": o.name, "bones": [
            {"name": b.name, "parent": b.parent.name if b.parent else None,
             "head": [round(x, 5) for x in (o.matrix_world @ b.head_local)],
             "len": round(b.length, 5)} for b in o.data.bones]})
    res["objects"].append(d)
res["total_tris"] = tot


def fcurves_of(act):
    fc = []
    if hasattr(act, "layers") and len(act.layers):
        for lay in act.layers:
            for st in lay.strips:
                for cb in getattr(st, "channelbags", []):
                    for f in cb.fcurves:
                        fc.append((cb.slot.name_display if cb.slot else "?", f))
    elif hasattr(act, "fcurves"):
        for f in act.fcurves:
            fc.append(("", f))
    return fc


for act in bpy.data.actions:
    a = {"name": act.name, "frame_range": [act.frame_range[0], act.frame_range[1]], "channels": {}}
    for slot, f in fcurves_of(act):
        vals = [k.co[1] for k in f.keyframe_points]
        if not vals:
            continue
        key = slot + " | " + f.data_path
        e = a["channels"].setdefault(key, {})
        e[str(f.array_index)] = {"keys": len(vals), "min": round(min(vals), 5), "max": round(max(vals), 5),
                                 "first_f": f.keyframe_points[0].co[0], "last_f": f.keyframe_points[-1].co[0],
                                 "moves": abs(max(vals) - min(vals)) > 1e-5}
    res["actions"].append(a)

for m in bpy.data.materials:
    md = {"name": m.name, "users": m.users, "nodes": []}
    if m.node_tree:
        for n in m.node_tree.nodes:
            nd = {"type": n.bl_idname}
            if n.bl_idname == "ShaderNodeTexImage":
                nd["image"] = n.image.name if n.image else None
                nd["path"] = n.image.filepath if n.image else None
                nd["to"] = [l.to_socket.name for o_ in n.outputs for l in o_.links]
            md["nodes"].append(nd)
    res["materials"].append(md)
for im in bpy.data.images:
    res["images"].append({"name": im.name, "path": im.filepath, "size": list(im.size), "source": im.source})

with open(out, "w") as fh:
    json.dump(res, fh, indent=1)
print("INSPECT_OK", tot, len(res["objects"]))
