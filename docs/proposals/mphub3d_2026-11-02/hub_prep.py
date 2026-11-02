"""hub_prep.py - HUB_A (the multiplayer room) made ready for the live 3D menu.  Blender 5.1:

    blender -b H:/hzm_archive/menuattic/export/hub_A_room.blend --python hub_prep.py -- --out H:/hzm_work/mphub3d/hub_mp.blend --tex H:/hzm_work/mphub3d/tex

What it changes (the source .blend is never written):
  * the SERVICE RECORD board (user 2026-11-02): the cork board's six random papers + pins are replaced by one face
    (srboard.png from gen_srboard.py: rank insignia chart, ribbon rack, typed service record form, campaigns card) and a
    wooden SERVICE RECORD header plaque on the top rail;
  * the left wooden double door (back to the attic) sat half inside the left wall: narrowed 10 % and moved right so the whole
    door stands in the room between the wall and the lockers;
  * the side walls and their trims run back to the floor's edge (y -1.5 m), so the home camera can stand further back and
    see wooden door -> lockers -> red door -> board -> game-type board in one 4:3 frame (wider screens see more wall);
  * the HUB_HOME camera (the engine home pose is computed from the same numbers in make_mphub3d.py);
  * curves / modifiers are made real meshes and the heaviest props (> 1200 tris: phone, lamp rims, helmet) are decimated
    (collapse 0.5): 63k -> about 50k evaluated tris, one joined bake source later."""
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


OUT = arg("--out", "H:/hzm_work/mphub3d/hub_mp.blend")
TEX = arg("--tex", "H:/hzm_work/mphub3d/tex")
SC = bpy.context.scene
ob = SC.objects

# ---- 1. service record board
for o in list(ob):
    if o.name.startswith(("nb_p", "nb_pin")):
        bpy.data.objects.remove(o, do_unlink=True)
cork = ob["nb_cork"]
cw, ch_ = cork.dimensions.x, cork.dimensions.z
cc = cork.matrix_world.translation.copy()
yface = cc.y - cork.dimensions.y / 2 - 0.004


def img_mat(name, path, rough=0.85):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(path, check_existing=True)
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    return m


def quad(name, cx, y, cz, w, h, mat):
    """a plane facing -Y (into the room), u along +X (to the viewer's right), v along +Z: never mirrored"""
    me = bpy.data.meshes.new(name)
    v = [(cx - w / 2, y, cz - h / 2), (cx + w / 2, y, cz - h / 2), (cx + w / 2, y, cz + h / 2), (cx - w / 2, y, cz + h / 2)]
    me.from_pydata(v, [], [(0, 1, 2, 3)])          # normal -Y (into the room): (v1-v0) x (v2-v0) = (w,0,0) x (w,0,h) = (0,-wh,0)
    uv = me.uv_layers.new(name="UVMap")
    for li, lp in enumerate(me.loops):
        x, _, z = v[lp.vertex_index]
        uv.data[li].uv = ((x - (cx - w / 2)) / w, (z - (cz - h / 2)) / h)
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    SC.collection.objects.link(o)
    return o


face = quad("nb_srface", cc.x, yface, cc.z, cw, ch_, img_mat("srboard", os.path.join(TEX, "srboard.png")))
face["grp"] = "srb"
# header plaque on the top rail: a dark wood block + its lettered front
top = ob["nb_top"]
zt = top.matrix_world.translation.z + top.dimensions.z / 2
PW, PH, PD = 0.86, 0.134, 0.022
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cc.x, 5.405 - PD / 2 - 0.001, zt + PH / 2 + 0.006))
blk = bpy.context.active_object
blk.name = "nb_plaque"
blk.scale = (PW, PD, PH)
bpy.ops.object.transform_apply(scale=True)
blk.data.materials.append(bpy.data.materials["frame_wood"] if "frame_wood" in bpy.data.materials else bpy.data.materials[0])
pf = quad("nb_plaque_face", cc.x, 5.405 - PD - 0.0015, zt + PH / 2 + 0.006, PW - 0.01, PH - 0.01, img_mat("srplaque", os.path.join(TEX, "srplaque.png"), 0.6))
pf["grp"] = "srb"
# only the two lettered faces are the srb group (its own 2048 atlas at full texel density); cork, frame and the plaque block bake in bg
bpy.data.objects.remove(cork, do_unlink=True)       # hidden behind the face

# ---- 2. the wooden double door: fully inside the room (it was half in the left wall)
OLDC, NEWC, SX = -2.95, -2.75, 0.90
Wm = Matrix.Translation((NEWC, 0, 0)) @ Matrix.Diagonal((SX, 1, 1, 1)) @ Matrix.Translation((-OLDC, 0, 0))
for o in list(ob):
    if o.name.startswith("wd_"):
        o.matrix_world = Wm @ o.matrix_world

# ---- 3. side walls + trims run back to the floor edge (y -1.5): the home camera stands at y -1.35
YMIN = -1.5
for n in ("wall_left", "wall_right", "dado_l", "dado_r", "rail_l", "rail_r", "skirt_l", "skirt_r"):
    o = ob[n]
    bpy.context.view_layer.update()
    ys = [(o.matrix_world @ Vector(c)).y for c in o.bound_box]
    lo, hi = min(ys), max(ys)
    k = (hi - YMIN) / (hi - lo)
    o.matrix_world = Matrix.Translation((0, hi, 0)) @ Matrix.Diagonal((1, k, 1, 1)) @ Matrix.Translation((0, -hi, 0)) @ o.matrix_world

# ---- 4. home camera (BU): see make_mphub3d.py HOME - keep the two in step
HOME = {"org": (-0.30, -1.35, 1.65), "yaw_right": 7.0, "pitch_down": 4.0, "fovy": 54.0}
cd = bpy.data.cameras.new("HUB_HOME")
cd.sensor_fit = 'VERTICAL'
cd.sensor_height = 24.0
cd.lens = 12.0 / math.tan(math.radians(HOME["fovy"] / 2))
cam = bpy.data.objects.new("HUB_HOME", cd)
SC.collection.objects.link(cam)
cam.location = HOME["org"]
cam.rotation_euler = (math.radians(90 - HOME["pitch_down"]), 0, math.radians(-HOME["yaw_right"]))
SC.camera = cam

# ---- 5. real meshes + decimate the heaviest props
bpy.context.view_layer.update()
geo = [o for o in ob if o.type in ('MESH', 'CURVE', 'SURFACE', 'FONT') and not o.hide_render]
bpy.ops.object.select_all(action='DESELECT')
for o in geo:
    o.select_set(True)
bpy.context.view_layer.objects.active = geo[0]
bpy.ops.object.make_single_user(object=True, obdata=True, material=False, animation=False)
bpy.ops.object.convert(target='MESH')
tot0 = tot1 = 0
for o in [o for o in ob if o.type == 'MESH']:
    o.data.calc_loop_triangles()
    n = len(o.data.loop_triangles)
    tot0 += n
    if n > 1200 and not o.name.startswith(("gb_", "nb_", "floor", "wall", "ceiling")):
        m = o.modifiers.new("dec", 'DECIMATE')
        m.ratio = 0.5
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="dec")
        o.data.calc_loop_triangles()
        print("decimated", o.name, n, "->", len(o.data.loop_triangles))
    tot1 += len(o.data.loop_triangles)
print("HUBPREP tris", tot0, "->", tot1)
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=False)
print("HUBPREP saved", OUT)
