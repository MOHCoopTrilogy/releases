"""blender -b attic_room_66.blend --python wx_inspect.py -- <out.json> : objects near the gable window / the left roof slope (BU), no render."""
import bpy, json, sys
from mathutils import Vector
out = sys.argv[sys.argv.index("--") + 1]
res = []
for o in bpy.data.objects:
    if o.type not in ('MESH', 'EMPTY', 'LIGHT'):
        continue
    if o.type == 'MESH' and len(o.data.vertices):
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        lo = [min(v[i] for v in vs) for i in range(3)]
        hi = [max(v[i] for v in vs) for i in range(3)]
    else:
        lo = hi = list(o.matrix_world.translation)
    # near the gable window (x -5.5..-3, y 6..7.5) or on the left roof (x < -1, z > 1.8) or rafters
    near_win = lo[0] < -3.7 and hi[0] > -4.9 and hi[1] > 6.6 and lo[1] < 7.2 and lo[2] < 2.4 and hi[2] > 1.3
    roofish = any(k in o.name.lower() for k in ("roof", "rafter", "beam", "ceil", "slope", "wall", "win", "sky", "purlin", "joist"))
    if near_win:
        res.append({"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None, "lo": [round(x, 3) for x in lo],
                    "hi": [round(x, 3) for x in hi], "mats": [s.material.name for s in o.material_slots if s.material] if o.type == 'MESH' else [],
                    "nv": len(o.data.vertices) if o.type == 'MESH' else 0, "grp": o.get("grp")})
json.dump(res, open(out, "w"), indent=0)
print("INSPECT", len(res))
