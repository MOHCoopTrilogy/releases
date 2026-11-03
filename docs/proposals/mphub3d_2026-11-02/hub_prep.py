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

# ---- 2. the way back to the attic.
# [mpui 2026-11-03] user: "Why would it be a double door? The entrance to it in the main attic isn't a double door. Continuity
# is important" + "Vanilla would have that door on the left wall to the camera". The back-wall double door (wd_*) is removed
# (plain wall stays) and the ATTIC's own MULTIPLAYER door (attic_room.blend door_mp_*: leaf, frosted light, glazing bars,
# mouldings, casings, brass knob + escutcheon - same models, materials and proportions) stands on the LEFT side wall, seen
# from the room side: turned 180 degrees about Z (it faced -X into the attic, here +X into the room), knob and escutcheon
# moved to the other edge (the far side of the same door), a cool backdrop behind the frosted light (the glass is not baked,
# as in the attic, where the back room shows through it), and a MAIN MENU plaque over the casing (gen_srboard.py mmplaque.png).
# --double-door keeps the earlier back-wall double door.
if "--double-door" in argv:
    OLDC, NEWC, SX = -2.95, -2.75, 0.90
    Wm = Matrix.Translation((NEWC, 0, 0)) @ Matrix.Diagonal((SX, 1, 1, 1)) @ Matrix.Translation((-OLDC, 0, 0))
    for o in list(ob):
        if o.name.startswith("wd_"):
            o.matrix_world = Wm @ o.matrix_world
else:
    ATTIC = arg("--attic", "H:/hzm_archive/menuattic/export/attic_room.blend")
    DOOR_Y = float(arg("--door-y", "4.05"))            # BU centre of the door along the left wall (clear of the back-left corner)
    for o in list(ob):
        if o.name.startswith("wd_"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    wl = ob["wall_left"]
    XW = max((wl.matrix_world @ Vector(c)).x for c in wl.bound_box)       # the left wall's room-side face
    with bpy.data.libraries.load(ATTIC, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith("door_mp_")]
        dst.materials = [n for n in src.materials if n == "backroom_cool"]
    AX, AY = 3.0, 6.40                                  # attic: the door's wall plane x and its centre y
    Rz = Matrix.Rotation(math.pi, 4, "Z")
    # the attic leaf sits 0-4 cm BEHIND its casing plane, in an opening of the attic wall; the hub's left wall is solid, so the
    # whole door stands PROUD of it by DOOR_OUT (leaf in front of the wall face and the dado rail, casings around it)
    DOOR_OUT = 0.07
    Dm = Matrix.Translation((XW + DOOR_OUT, DOOR_Y, 0)) @ Rz @ Matrix.Translation((-AX, -AY, 0))
    for o in dst.objects:
        SC.collection.objects.link(o)
    # the leaf, glazing, mouldings, knob and escutcheon are children of an EMPTY hinge pivot: freeze every part's evaluated world
    # matrix, drop the parenting, then move the parts (a fresh link has stale world matrices until the view layer updates)
    bpy.context.view_layer.update()
    WM = {o.name: o.matrix_world.copy() for o in dst.objects}
    for o in dst.objects:
        o.parent = None
    for o in list(dst.objects):
        if o.type == "EMPTY":
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        o.matrix_world = Dm @ WM[o.name]
        if o.name.startswith(("door_mp_knob", "door_mp_escutch")):
            # attic: knob 0.35 m to the viewer's left; the room side of the same door has it on the viewer's right (+Y here)
            o.matrix_world = Matrix.Translation((0, 0.70, 0)) @ o.matrix_world
        o.name = "wd_" + o.name
    bpy.context.view_layer.update()
    print("HUBPREP exit door: %d attic door parts on the left wall x=%.3f y=%.2f" % (len(dst.objects), XW, DOOR_Y))
    # the backdrop behind the frosted light (attic glass y 6.07..6.73, z 1.07..2.02): a quad facing +X just inside the wall
    bdm = dst.materials[0] if dst.materials else bpy.data.materials.new("backroom_cool")
    def quad_x(name, x, cy, cz, w, h, mat):
        """a plane facing +X (into the room from the left wall), u along +Y (the viewer's right when looking -X): never mirrored"""
        me = bpy.data.meshes.new(name)
        v = [(x, cy - w / 2, cz - h / 2), (x, cy + w / 2, cz - h / 2), (x, cy + w / 2, cz + h / 2), (x, cy - w / 2, cz + h / 2)]
        me.from_pydata(v, [], [(0, 1, 2, 3)])        # (v1-v0) x (v2-v0) = (0,w,0) x (0,w,h) = (wh,0,0): normal +X
        uv = me.uv_layers.new(name="UVMap")
        for li, lp in enumerate(me.loops):
            _, y, z = v[lp.vertex_index]
            uv.data[li].uv = ((y - (cy - w / 2)) / w, (z - (cz - h / 2)) / h)
        me.materials.append(mat)
        me.update()
        assert me.polygons[0].normal.x > 0.99, name
        o = bpy.data.objects.new(name, me)
        SC.collection.objects.link(o)
        return o
    # the frosted light: in the attic it is not baked (glass) and the lit back room shows through it; against the hub's solid wall
    # that read as a black hole, so here the pane is a DIM frosted surface baked with the room (grp bg): no emission (a lit pane
    # was the brightest thing in the room, coordinator QA 2026-11-03), a grey-buff close to the wall tone, darker than the lit wall,
    # with a soft vertical gradient (lighter at the top, as if the corridor beyond were lit)
    fm = bpy.data.materials.new("frosted_dim")
    fm.use_nodes = True
    nt = fm.node_tree
    fb = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    fb.inputs["Roughness"].default_value = 0.95
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = (0.085, 0.082, 0.075, 1.0)   # bottom of the pane (measured: lit at 0.17-0.30 it matched the wall, QA 2026-11-03)
    ramp.color_ramp.elements[1].color = (0.15, 0.145, 0.13, 1.0)     # top
    nt.links.new(ramp.outputs["Color"], fb.inputs["Base Color"])
    for o in ob:
        if o.name.startswith("wd_door_mp_glass"):
            o.data.materials.clear()
            o.data.materials.append(fm)
            o["grp"] = "bg"
            # the pane sits inside the leaf slab (attic x 3.01..3.03 in a 3.00..3.04 leaf): baked there it gets no light and
            # reads black; bring it to the leaf's room-side face (+X here) so it bakes as lit frosted glass
            c = o.matrix_world.translation.copy()
            bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
            c = sum(bb, Vector()) / 8
            # and fill the leaf's light opening (the attic pane is a little smaller than its cut-out, which showed as a black rim)
            o.matrix_world = Matrix.Translation((0.022, 0, 0)) @ Matrix.Translation(c) @ Matrix.Diagonal((1.0, 1.10, 1.22, 1.0)) @ Matrix.Translation(-c) @ o.matrix_world
    for o in ob:
        if o.name.startswith("wd_door_mp_gbar"):
            o.matrix_world = Matrix.Translation((0.026, 0, 0)) @ o.matrix_world      # the glazing bars in front of the pane, as seen in the attic
    # the MAIN MENU plaque over the casing top (z 2.60): a wood block + its lettered face (a "quad" group, like the SR plaque)
    QW, QH, QD = 0.96, 0.15, 0.022      # [QA 2026-11-03] a little larger than the SR plaque (0.86 x 0.134): it hangs further from the camera
    zq = 2.60 + 0.03 + QH / 2
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(XW + QD / 2 + 0.001, DOOR_Y, zq))   # on the wall itself
    qb = bpy.context.active_object
    qb.name = "wd_plaque"
    qb.scale = (QD, QW, QH)
    bpy.ops.object.transform_apply(scale=True)
    qb.data.materials.append(bpy.data.materials["frame_wood"] if "frame_wood" in bpy.data.materials else bpy.data.materials[0])
    quad_x("wd_plaque_face", XW + QD + 0.0015, DOOR_Y, zq, QW - 0.01, QH - 0.01, img_mat("mmplaque", os.path.join(TEX, "mmplaque.png"), 0.6))

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
HOME = {"org": (-0.30, -1.35, 1.65), "yaw_right": 3.0, "pitch_down": 4.0, "fovy": 58.0}   # [mpui 2026-11-03] was 7 / 54: the left-wall exit door in the 4:3 frame
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
