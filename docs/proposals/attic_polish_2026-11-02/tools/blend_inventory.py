"""blender -b attic_room.blend --python blend_inventory.py -- <out.json>  (no render: CPU only, seconds)
every object: name, type, parent, collection, world bounds (BU m), material names, image textures"""
import bpy, json, sys
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]
rows = []
for o in bpy.data.objects:
    r = {"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None,
         "coll": [c.name for c in o.users_collection], "hide_render": o.hide_render}
    if o.type in ("MESH", "CURVE", "FONT"):
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        r["min"] = [min(v[i] for v in bb) for i in range(3)]
        r["max"] = [max(v[i] for v in bb) for i in range(3)]
        r["mats"] = [s.material.name for s in o.material_slots if s.material]
        imgs = []
        for s in o.material_slots:
            m = s.material
            if m and m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == "TEX_IMAGE" and n.image:
                        imgs.append(n.image.filepath or n.image.name)
        r["imgs"] = sorted(set(imgs))
        if o.type == "MESH":
            r["tris"] = sum(len(p.vertices) - 2 for p in o.data.polygons)
    else:
        r["loc"] = list(o.matrix_world.translation)
    rows.append(r)
json.dump(rows, open(out, "w"), indent=0)
print("objects", len(rows))
