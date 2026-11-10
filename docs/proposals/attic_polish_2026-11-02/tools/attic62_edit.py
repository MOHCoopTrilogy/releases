"""attic62_edit.py - v1.10.62 attic scene edits (Blender, no render: CPU only).

    blender -b H:/hzm_archive/menuattic/export/attic_room.blend -t 2 --python attic62_edit.py -- <stock dir> <art dir> <out.blend>

What it does (the bake then runs attic_bake3.py on the saved file; nothing here renders):
  door     the BRIEFING door (door_brief_*: leaf, casings, mouldings, panels, knob, escutcheon) moves from the right wall (x 3.0,
           y 8.30) to the back wall of the corridor right of the map (doorwall0, y 9.60), where vanilla's main menu has its second
           door and the rifle rack stood.  The rifles and their rack (only there to fill that spot) are removed; the old doorway is
           filled with plaster (x 3.0-3.12, y 7.79-8.81, under the existing lintel); the notice board steps 8 cm right to clear the
           new casing.  The MULTIPLAYER door is untouched, except thin jamb liners inside its opening (behind the casings) that close
           the gap the back room's light leaked through (audit #15).
  props    audit items cut and replaced with stock MOHAA models (export_stock.py OBJ), posed and scaled as the game shows them:
           #2 cabinet + safe + typewriter -> two smallfilecabinet + typewriter; #6 desk trays / loose papers -> documents1a/2a;
           #7 film-case box + #8 reels -> documents1a + the REPORT A BUG toolbox (toolbox_closed); #10 projector -> stock projector
           (named projector_stock so it stays the Film Room's 'projector' group); #14 rifle rack -> gone (door).
  new      the FIELD REPORT dispatch board (gen_fieldreport_art.py) on the post by the long desk, facing the room.
  lamps    #5 / #17 the plastic-green shades -> dark bottle-green enamel, rougher, no blown highlight.
  atlas    every new / replaced prop and the small boards (rota board, notice board) get grp=props: their own 4096 atlas in the
           bake (attic_bake3 PLAN 'props'), so they are crisp instead of sharing the room atlas."""
import math, os, sys
import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
STOCK, ART, OUT = argv[0], argv[1], argv[2]
SC = bpy.context.scene
S = 1.0 / 52.5
log = lambda *a: print("[attic62]", *a, flush=True)  # noqa: E731


def objs(prefixes):
    return [o for o in bpy.data.objects if o.name.startswith(prefixes)]


def remove(prefixes):
    n = 0
    for o in objs(prefixes):
        bpy.data.objects.remove(o, do_unlink=True)
        n += 1
    log("removed", prefixes, n)


def wbounds(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(v[i] for v in bb) for i in range(3)]), Vector([max(v[i] for v in bb) for i in range(3)])


def box(name, lo, hi, mat):
    me = bpy.data.meshes.new(name)
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(v, [], f)
    me.update()
    o = bpy.data.objects.new(name, me)
    SC.collection.objects.link(o)
    o.data.materials.append(bpy.data.materials[mat])
    me.uv_layers.new(name="UVMap")
    return o


# ---- 1. the briefing door -> the corridor's back wall (doorwall0, y 9.60), centred x 1.50
P0, P1 = Vector((3.0, 8.30, 0.0)), Vector((1.50, 9.60, 0.0))
M = Matrix.Translation(P1) @ Matrix.Rotation(math.radians(90), 4, "Z") @ Matrix.Translation(-P0)
# the doorway is built exactly as it was: an opening through the wall's thickness, the leaf set in it, jamb + head liners
# filling it from the leaf to the wall edge (that gap was where the back room's light leaked through), made in the door's old
# frame so they move with it
for nm, lo, hi in (("door_brief_jamb_r", (3.0, 7.79, 0.0), (3.12, 7.88, 2.58)), ("door_brief_jamb_l", (3.0, 8.73, 0.0), (3.12, 8.81, 2.58)),
                   ("door_brief_jamb_h", (3.0, 7.79, 2.49), (3.12, 8.81, 2.58)), ("door_brief_backing", (3.04, 7.88, 0.0), (3.12, 8.73, 2.49))):
    box(nm, lo, hi, "beam" if "jamb" in nm else "plaster")
door = objs(("door_brief_", "HS_briefing_door"))
ds = set(door)


def _has_moved_ancestor(o):
    q = o.parent
    while q is not None:
        if q in ds:
            return True
        q = q.parent
    return False


for o in [o for o in door if not _has_moved_ancestor(o)]:      # move each sub-tree once (children follow their parent)
    o.matrix_world = M @ o.matrix_world
log("door parts moved", len(door))
remove(("rack_", "rifle0_", "rifle1_", "back_brief_", "brief_"))     # the rifles; the briefing back room behind the filled doorway
box("rwall_fill_brief", (3.0, 7.79, 0.0), (3.12, 8.81, 2.58), "plaster")
# the corridor's back wall (doorwall0, x 0.4-3.0, y 9.60-9.72) gets the opening the door now stands in (x 0.99-2.01, as the
# old one: 1.02 wide, lintel from 2.58)
dw = bpy.data.objects.get("doorwall0")
if dw:
    bpy.data.objects.remove(dw, do_unlink=True)
for nm, lo, hi in (("doorwall0_l", (0.4, 9.6, 0.0), (0.99, 9.72, 5.0)), ("doorwall0_r", (2.01, 9.6, 0.0), (3.0, 9.72, 5.0)),
                   ("doorwall0_lintel", (0.99, 9.6, 2.58), (2.01, 9.72, 5.0))):
    box(nm, lo, hi, "plaster")
for o in objs(("noticeboard", "notice_card")):
    o.location.x += 0.08
# the MULTIPLAYER doorway: the same jamb + head liners (leaf edge to wall edge), nothing else on that door changes
for nm, lo, hi in (("jamb_mp_r", (3.0, 5.89, 0.0), (3.12, 5.97, 2.58)), ("jamb_mp_l", (3.0, 6.83, 0.0), (3.12, 6.91, 2.58)),
                   ("jamb_mp_h", (3.0, 5.89, 2.49), (3.12, 6.91, 2.58))):
    box(nm, lo, hi, "beam")

# ---- 2. props cut (replaced below)
remove(("typewriter_", "cab_l1", "cab_l2", "tray_", "paper_215_290", "fbox", "can_reel_", "can0_", "can1_", "fcan", "paper_470_420", "projector_"))   # #7 film-case box + standing cans, #8 the two flat reel cans, the sheet under the toolbox


def place(name, label, at, yaw=0.0, k=1.0, grp="props", gain=1.0):
    """import the stock OBJ (game units, Z up), scale to metres (x k), stand its bottom-centre on `at` (BU m), yaw in degrees"""
    d = os.path.join(STOCK, name)
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(d, name + ".obj"), forward_axis="Y", up_axis="Z")
    new = [o for o in bpy.data.objects if o not in before]
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in new:
        a, b = wbounds(o)
        lo = Vector([min(lo[i], a[i]) for i in range(3)])
        hi = Vector([max(hi[i], b[i]) for i in range(3)])
    c = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    T = Matrix.Translation(Vector(at)) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Scale(S * k, 4) @ Matrix.Translation(-c)
    for i, o in enumerate(new):
        o.matrix_world = T @ o.matrix_world
        o.name = "%s_%d" % (label, i)
        o["grp"] = grp
        if o.type == "MESH":
            # the 1/52.5 import scale goes into the mesh: attic_bake3 joins a group into its first object's space, and its cage
            # extrusion / ray distance (0.03 / 0.15) are then read in THAT object's units - from a stock prop, 1/52.5 of a metre
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            orient(o)
            if gain != 1.0:
                brighten(o, gain)
    log("placed", name, "as", label, "at", at, "yaw", yaw, "k", k)
    return new


def brighten(o, gain):
    """a dark stock texture x gain before the bake: MOHAA lights models with overbright (lightgrid x 2), so a steel texture authored
    at ~10 % grey reads mid-grey in the game; baked as a plain albedo it went black (the worktable / toolbox, first v1.10.62 bake)"""
    for slot in o.material_slots:
        m = slot.material
        if not m or not m.use_nodes or m.get("p62_gain"):
            continue
        nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf or not bsdf.inputs["Base Color"].links:
            continue
        src = bsdf.inputs["Base Color"].links[0].from_socket
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(src, mix.inputs["A"])
        mix.inputs["B"].default_value = (gain, gain, gain, 1.0)
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
        m["p62_gain"] = gain
        log("gain", m.name, gain)


HOME_CAM_BU = Vector((-0.40, -0.70, 1.95))      # the home camera (game -36.7 21.0 102.4)


def orient(o):
    """MOHAA draws these models with `cull none`, so their single-sided parts (the worktable's top is one quad) can face either way;
    Cycles bakes a face from its normal side, so a top facing down bakes the dark underside - the table went black in the first
    v1.10.62 bake.  Closed parts: outward normals.  Flat open parts (a top, a sheet of paper): turned to face the home camera."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    # the OBJ export writes every triangle with its own corners: weld first, or every triangle is its own "flat island" and the
    # back half of a closed box gets turned to the camera (the folders baked red / black checkers in the second bake)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # two-sided parts are modelled as the same triangle twice, facing both ways: keep one (the bake picks either at random per
    # triangle - the toolbox end, the folders came out as black / colour checkers)
    seenf, dup = set(), []
    for f in bm.faces:
        k = frozenset(v.index for v in f.verts)
        if k in seenf:
            dup.append(f)
        else:
            seenf.add(k)
    if dup:
        bmesh.ops.delete(bm, geom=dup, context="FACES_ONLY")
        log("orient", o.name, "dropped", len(dup), "back-to-back duplicate faces")
    bm.faces.ensure_lookup_table()
    seen, flips = set(), 0
    mw = o.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        isl, stack = [], [f0]
        seen.add(f0.index)
        while stack:
            f = stack.pop()
            isl.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        bmesh.ops.recalc_face_normals(bm, faces=isl)
        ns = [(nm @ f.normal).normalized() for f in isl if f.calc_area() > 0]
        if not ns or len(isl) > 64:
            continue
        flat = all(abs(n.dot(ns[0])) > 0.87 for n in ns)
        if not flat:
            # the stock meshes are not manifold (recalc leaves single triangles of a quad inside-out - the toolbox end and the
            # folders baked as black / colour checkers): every face of a solid part faces away from that part's own centre
            ic = sum((f.calc_center_median() for f in isl), Vector()) / len(isl)
            for f in isl:
                if f.normal.dot(f.calc_center_median() - ic) < -1e-6:
                    f.normal_flip()
                    flips += 1
            continue
        ctr = mw @ (sum((f.calc_center_median() for f in isl), Vector()) / len(isl))
        if ns[0].dot(HOME_CAM_BU - ctr) < 0 and (ns[0].z < 0.5 or ctr.z < HOME_CAM_BU.z):
            for f in isl:
                f.normal_flip()
            flips += 1
    bm.to_mesh(o.data)
    bm.free()
    # the OBJ's vertex normals are not the model's (non-unit, sideways on the worktable's top): Cycles' selected-to-active bake
    # casts along the interpolated normal, so those rays missed and the worktable baked pure black.  Drop them; smooth up to 40 deg.
    bpy.context.view_layer.objects.active = o
    if o.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    o.data.shade_smooth()
    o.data.set_sharp_from_angle(angle=math.radians(40))
    o.data.update()
    if flips:
        log("orient", o.name, "flipped", flips, "flat parts towards the camera")


# filing cabinets (front +X in the model -> -Y, facing the room), the typewriter on the right-hand one
place("smallfilecabinet", "p62_cabinet_a", (-4.75, 6.49, 0.0), -90)
place("smallfilecabinet", "p62_cabinet_b", (-5.41, 6.49, 0.0), -90)
place("typewriter", "p62_typewriter", (-4.75, 6.50, 0.957), -90)
# the long desk: folders where the trays / loose sheets were, and where the film case stood
place("documents1a", "p62_docs_a", (-0.31, 4.96, 0.785), 20)      # (documents2a: its red and blue folders are coincident boxes - they baked as red / black checkers)
place("documents1a", "p62_docs_c", (0.24, 2.86, 0.785), 5)
# REPORT A BUG: the steel field toolbox where the film reels lay (handle towards the camera)
# (user 2026-11-03: "closer to the camera" - the empty near end of the long desk, short of the papers, angled 15 deg off square)
place("toolbox_closed", "p62_toolbox", (0.45, 1.60, 0.785), 255, 0.72, gain=2.0)   # 255: the plain end towards the camera (the other end bakes as black / white bars)
# the Film Room's projector: the stock 16 mm projector, the old one's footprint and height (lens -X as before)
place("projector", "projector_stock", (0.995, 2.00, 1.00), 0, 0.56, grp="projector")

# #1 the General's work table: the stock table drawn 1.9x by the menu (actor_anims.TABLE_PROPS) becomes a true-scale stock
# worktable baked into the room (top 0.92 m: Weathers' hands still rest on it), with the two clipboards lying on it; the
# oversized card table behind it goes.  BU yaw = game yaw + 90 (game +x is BU +y).
# (the stock `worktable` was tried first: its texture is near-black steel (mean 26 / 255) and it baked as a black slab in the
# foreground even at x2.5 - so the stock `simplerectable`, the table the scene drew before, now true size and baked matte)
place("simplerectable", "p62_worktable", (-2.0133, 1.5, 0.0), 90)
# under his hands: a stock folder stack (the stock clipboards were tried: their paper and board are two coincident layers and the
# board baked black over the paper - two black paddles under Weathers' hands)
# v1.10.66 (user: "Give the general a blueprint instead of what he looks at now on menu"): the folder stack goes; a cyanotype sheet
# (gen_blueprint_art.py) lies flat under his hands - see section 11 below.

# ---- 3. the FIELD REPORT dispatch board, 0.41 x 0.55 m, 2 cm plywood, pinned flat on the right-hand plaster wall (rwall0, x 3.00)
# between the post and the MULTIPLAYER door at head height (user 2026-11-03: "something on this WALL" - it first went on post_630)
img = bpy.data.images.load(os.path.join(ART, "fieldreport_board.png"))
mat = bpy.data.materials.new("fieldreport_board")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
tex.image = img
mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.75
bx = box("p62_fieldreport", (2.978, 4.145, 1.17), (2.998, 4.555, 1.717), "plaster")     # 0.41 x 0.547 m (the art is 3:4): y 4.15 .. 4.56 clears the post (3.41) and the door casing (5.85)
bx.data.materials[0] = mat
bx["grp"] = "props"
uv = bx.data.uv_layers[0].data
# face 5 = (3, 0, 4, 7) = the -X face (towards the room): the viewer faces +X, so u runs along -y (vertex 3 is y1), v along +z
for li, (u, v) in zip(bx.data.polygons[5].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
    uv[li].uv = (u, v)

# ---- 4. lamp shades: dark bottle-green enamel, not plastic
# (first bake: base 0.035 / 0.085 / 0.045 still read lime under the 1100 W desk key, and shade_lime kept a lime EMISSION 0.35
# that lit the pendant and wall-lamp shades from inside - so darker still, matte, no emission; the ledger's paint_green stays)
for mn in ("shade_green", "shade_lime"):
    m = bpy.data.materials.get(mn)
    if not m or not m.use_nodes:
        continue
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            bc = n.inputs["Base Color"]
            if not bc.is_linked:
                bc.default_value = (0.010, 0.026, 0.014, 1.0)
            n.inputs["Roughness"].default_value = 0.62
            if "Coat Weight" in n.inputs:
                n.inputs["Coat Weight"].default_value = 0.08
            if "Emission Strength" in n.inputs:
                n.inputs["Emission Strength"].default_value = 0.0
            log("lamp material", mn, "linked" if bc.is_linked else "set")

# ---- 4b. the v1.10.61 texel fixes made at the source, so the new bake needs no retouch for them:
#   D-A3 the telephones' candy-coloured bakelite (green / grey / red) -> the black bakelite the set already has (only on phones:
#   the notice-board pins keep their red); D-A4 the key light's lamp (a lighting-rig prop hanging in mid-air: arm, shade, bulb,
#   flex) goes, its light stays
blk = bpy.data.materials.get("bak_black")
for o in bpy.data.objects:
    if o.name.startswith(("phone", "wallphone")) and o.type == "MESH":
        for s in o.material_slots:
            if s.material and s.material.name in ("bak_green", "bak_grey", "bak_red"):
                s.material = blk
for o in [o for o in bpy.data.objects if o.name.startswith("keylamp_") and o.type in ("MESH", "CURVE")]:
    bpy.data.objects.remove(o, do_unlink=True)
log("phones -> bak_black, keylamp rig prop removed")

# ---- 5. crisp atlas for the small boards
for o in objs(("maplist_board", "noticeboard", "notice_card_face", "phoneshelf_back")):
    o["grp"] = "props"

# ---- 6. v1.10.62 (user): "make the fans animate in the main menu (accurately)".  The wall fan's four blades + spinner become their
# own group "rotor" (its own atlas, then gen_fan_rotor.py: a model turning about the motor shaft).  They are made invisible to
# every ray, so nothing in the room - wall, cage, motor - bakes a frozen blade shadow; the cage, motor, badge, canopy stay "fan".
import json  # noqa: E402
rot = [o for o in bpy.data.objects if o.type == "MESH" and (o.name.startswith("fan_blade") or o.name == "fan_spinner")]
assert len(rot) == 5, [o.name for o in rot]
for o in rot:
    o["grp"] = "rotor"
    for f in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_shadow", "visible_volume_scatter"):
        if hasattr(o, f):
            setattr(o, f, False)


def wcentre(o):
    a, b = wbounds(o)
    return [(a[i] + b[i]) / 2 for i in range(3)]


# the motor shaft: the normal of the guard's front ring (the cage's rings are true circles about the shaft; the stock blades and
# spinner sit 17 deg off it - spun as modelled they would wobble), pointing out of the guard (motor -> spinner)
import numpy as _np  # noqa: E402
_r = bpy.data.objects["fan_ring0"]
_V = _np.array([tuple(_r.matrix_world @ v.co) for v in _r.data.vertices])
_ax = _np.linalg.svd(_V - _V.mean(0))[2][2]
_hub, _mot = _np.array(wcentre(bpy.data.objects["fan_spinner"])), _np.array(wcentre(bpy.data.objects["fan_motor2"]))
if _np.dot(_ax, _hub - _mot) < 0:
    _ax = -_ax
json.dump({"hub": wcentre(bpy.data.objects["fan_spinner"]), "motor": wcentre(bpy.data.objects["fan_motor2"]), "shaft": [float(x) for x in _ax]},
          open(os.path.join(os.path.dirname(OUT), "rotor_axis.json"), "w"), indent=1)
log("rotor", [o.name for o in rot])

# ---- 7. v1.10.62 (user): "if the door looks one way inside the main menu, it should look exactly the same from the other side".
# The MULTIPLAYER door's other side is the MP room's exit (mphub3d hub_prep.py copies door_mp_* from the archive attic blend and
# shows a DIM FROSTED pane + glazing bars on the leaf face).  Here the same pane sat inside the leaf slab (x 3.014-3.026 in a
# 3.00-3.04 leaf) and never showed, so the attic side read as a plain upper leaf.  Same treatment as the room side: the pane moved
# to the leaf's room face (-X here: the hub's +0.022 mirrored), scaled 1.10 x 1.22 to fill the light, the bars 0.026 in front,
# and the hub's frosted_dim material (same ramp numbers, baked with the room).
fm = bpy.data.materials.new("frosted_dim")
fm.use_nodes = True
_nt = fm.node_tree
_fb = [n for n in _nt.nodes if n.type == "BSDF_PRINCIPLED"][0]
_fb.inputs["Roughness"].default_value = 0.95
_tc = _nt.nodes.new("ShaderNodeTexCoord")
_sep = _nt.nodes.new("ShaderNodeSeparateXYZ")
_ramp = _nt.nodes.new("ShaderNodeValToRGB")
_nt.links.new(_tc.outputs["Generated"], _sep.inputs[0])
_nt.links.new(_sep.outputs["Z"], _ramp.inputs["Fac"])
_ramp.color_ramp.elements[0].color = (0.085, 0.082, 0.075, 1.0)    # = hub_prep.py frosted_dim
_ramp.color_ramp.elements[1].color = (0.15, 0.145, 0.13, 1.0)
_nt.links.new(_ramp.outputs["Color"], _fb.inputs["Base Color"])
bpy.context.view_layer.update()
for o in list(bpy.data.objects):
    if o.name.startswith("door_mp_glass"):
        WMg = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = WMg
        o.data.materials.clear()
        o.data.materials.append(fm)
        o["grp"] = "bg"
        c = wcentre(o)
        c = Vector(c)
        o.matrix_world = Matrix.Translation((-0.022, 0, 0)) @ Matrix.Translation(c) @ Matrix.Diagonal((1.0, 1.10, 1.22, 1.0)) @ Matrix.Translation(-c) @ o.matrix_world
        log("mp door pane", o.name, "-> frosted_dim on the room face")
    elif o.name.startswith("door_mp_gbar"):
        WMg = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = Matrix.Translation((-0.026, 0, 0)) @ WMg


# ======================================================================================================================================
# v1.10.63 (user 2026-11-04)
# ======================================================================================================================================
def img_mat(name, path, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    t = m.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path)
    m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def col_mat(name, rgb, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = tuple(rgb) + (1.0,)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def mbox(name, lo, hi, mat, grp="props"):
    """a box with world-planar UVs (faces map their own 2 axes, metres x 2): fine for wood grain / flat colour"""
    o = box(name, lo, hi, "plaster")
    o.data.materials[0] = mat
    o["grp"] = grp
    uv = o.data.uv_layers[0].data
    for p in o.data.polygons:
        n = p.normal
        ax = (1, 2) if abs(n.x) > 0.5 else ((0, 2) if abs(n.y) > 0.5 else (0, 1))
        for li in p.loop_indices:
            v = o.data.vertices[o.data.loops[li].vertex_index].co
            uv[li].uv = (v[ax[0]] * 2.0, v[ax[1]] * 2.0)
    return o


def face_image(o, mat, axis_sign):
    """put an image on the one face of box `o` whose normal is axis_sign ('-x', '-y' ...), u to the viewer's right, v up"""
    o.data.materials.append(mat)
    idx = len(o.data.materials) - 1
    ax = "xyz".index(axis_sign[1])
    sg = -1 if axis_sign[0] == "-" else 1
    uv = o.data.uv_layers[0].data
    for p in o.data.polygons:
        if p.normal[ax] * sg > 0.5:
            p.material_index = idx
            vs = [o.data.vertices[o.data.loops[li].vertex_index].co for li in p.loop_indices]
            # viewer faces -normal: for a -y face the viewer looks +y, right = +x; -x face: looks +x, right = -y; +x face: right = +y
            ra = {("y", -1): (0, 1), ("y", 1): (0, -1), ("x", -1): (1, -1), ("x", 1): (1, 1)}[(axis_sign[1], sg)]
            rs = [v[ra[0]] * ra[1] for v in vs]
            zs = [v[2] for v in vs]
            for li, v in zip(p.loop_indices, vs):
                uv[li].uv = ((v[ra[0]] * ra[1] - min(rs)) / (max(rs) - min(rs)), (v[2] - min(zs)) / (max(zs) - min(zs)))


# ---- 8. the RECORDS desk, as vanilla's records screen has it: the medal box (closed) and the LOAD / SAVE trays
# (gen_records_art.py makes the art from the vanilla screens).  The two loose sheets where the box goes are cleared.
remove(("paper_268_348", "paper_290_340"))
wood = img_mat("medalbox_wood", os.path.join(ART, "medalbox_wood.png"), 0.45)
front = img_mat("medalbox_front", os.path.join(ART, "medalbox_front.png"), 0.45)
velvet = col_mat("medalbox_velvet", (0.30, 0.03, 0.04), 0.9)
MB = {"x": (-0.33, 0.07), "y": (3.162, 3.50), "z0": 0.785, "zl": 0.86, "z1": 0.895}      # box: body z0..zl, lid zl..z1, hinge at y1, zl
body = mbox("p62_medalbox_body", (MB["x"][0], MB["y"][0], MB["z0"]), (MB["x"][1], MB["y"][1], MB["zl"]), wood)
face_image(body, front, "-y")
# the open box shows a velvet well: the body's top face (only seen when the lid is up)
body.data.materials.append(velvet)
for p in body.data.polygons:
    if p.normal.z > 0.5:
        p.material_index = len(body.data.materials) - 1
lid = mbox("p62_medalbox_lid", (MB["x"][0], MB["y"][0], MB["zl"]), (MB["x"][1], MB["y"][1], MB["z1"]), wood, grp="medallid")
json.dump(MB, open(os.path.join(os.path.dirname(OUT), "medalbox.json"), "w"), indent=1)
tray_m = col_mat("tray_green", (0.07, 0.13, 0.08), 0.5, 0.3)
paper_m = col_mat("tray_paper", (0.78, 0.74, 0.62), 0.9)
TX, TY = (0.12, 0.40), (3.18, 3.46)          # beside the box on its right, same depth: the long desk runs 13 deg off +y, its felt's
# left edge is x -0.29 at y 2.84 and -0.40 at y 3.33 (the box sat 5 cm over it at x -0.45; in front of it the trays hid the box)
for k, (word, z0) in enumerate((("save", 0.785), ("load", 0.875))):
    t = 0.006
    mbox("p62_tray%d_base" % k, (TX[0], TY[0], z0), (TX[1], TY[1], z0 + t), tray_m)
    mbox("p62_tray%d_back" % k, (TX[0], TY[1] - t, z0), (TX[1], TY[1], z0 + 0.065), tray_m)
    mbox("p62_tray%d_l" % k, (TX[0], TY[0], z0), (TX[0] + t, TY[1], z0 + 0.065), tray_m)
    mbox("p62_tray%d_r" % k, (TX[1] - t, TY[0], z0), (TX[1], TY[1], z0 + 0.065), tray_m)
    fw = mbox("p62_tray%d_front" % k, (TX[0], TY[0], z0), (TX[1], TY[0] + t, z0 + 0.035), tray_m)
    mbox("p62_tray%d_paper" % k, (TX[0] + 0.02, TY[0] + 0.02, z0 + t), (TX[1] - 0.02, TY[1] - 0.02, z0 + t + 0.012), paper_m)
    pl = mbox("p62_tray%d_plate" % k, ((TX[0] + TX[1]) / 2 - 0.06, TY[0] - 0.004, z0 + 0.008), ((TX[0] + TX[1]) / 2 + 0.06, TY[0], z0 + 0.032), tray_m)
    face_image(pl, img_mat("tray_%s" % word, os.path.join(ART, "tray_%s.png" % word), 0.4, 0.4), "-y")
for cx in (TX[0] + 0.004, TX[1] - 0.004):                 # the upper tray stands on four posts
    for cy in (TY[0] + 0.004, TY[1] - 0.004):
        mbox("p62_traypost_%.2f_%.2f" % (cx, cy), (cx - 0.004, cy - 0.004, 0.791), (cx + 0.004, cy + 0.004, 0.875), tray_m)
log("records desk: medal box + LOAD / SAVE trays")

# ---- 9. the RIFLE RACK on the right-hand wall right of the post (rwall0 x 3.00, y 2.05 .. 3.05; seen at 21:9 - at 16:9 that wall
# is outside the frame): a wall-mounted wooden rack - back board, butt shelf with a lip, slot spacers at the top rail - holding
# the game's own world models: BAR, M1 Garand, Springfield, Thompson, MP40, StG44, Kar98k, muzzles up, sights to the wall.
# the rack's wood: the desks' wood under a dark walnut stain (desk_wood as is baked a bright orange-yellow board behind dark guns,
# first v1.10.63 still)
rk = bpy.data.materials["desk_wood"].copy()
rk.name = "rack_wood"
_bs = next(n for n in rk.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
STAIN = (0.46, 0.33, 0.24, 1.0)
if _bs.inputs["Base Color"].links:
    _src = _bs.inputs["Base Color"].links[0].from_socket
    _mx = rk.node_tree.nodes.new("ShaderNodeMix")
    _mx.data_type, _mx.blend_type = "RGBA", "MULTIPLY"
    _mx.inputs["Factor"].default_value = 1.0
    rk.node_tree.links.new(_src, _mx.inputs["A"])
    _mx.inputs["B"].default_value = STAIN
    rk.node_tree.links.new(_mx.outputs["Result"], _bs.inputs["Base Color"])
else:
    _c = _bs.inputs["Base Color"].default_value
    _bs.inputs["Base Color"].default_value = tuple(_c[i] * STAIN[i] for i in range(3)) + (1.0,)
# v1.10.63 (user, on the first stills): "move it further to the right so it is symmetrical" - centred on the bare plaster between
# the post (y 3.19) and the wall's end (rwall0 y 0.50) AS THE PEEK VIEW SEES IT (equal screen gaps at 16:9, PEEK_POSE yaw -35;
# the world midpoint 1.845 left a gap of 0.06 screen widths at the post and 0.14 at the wall's end): centre y 1.54.
# (A v1.10.64 move into the home view - y 4.65 .. 5.40 between the FIELD REPORT board and the roof brace - was cancelled by the
# user, "im good with the rack where its at"; it is on mod branch attic-64, b8b33da0, unmerged.)
RX, RY0, RY1 = 3.0, 1.03, 2.05
# the right-hand plaster wall (rwall0 + its skirting) ended at y 0.50, open onto the dark eaves beyond: never seen from home, but the
# peek and the rack close-up look along it - run both on to y -1.00 (the roof's own end)
for _n in ("rwall0", "skirting_rw"):
    _o = bpy.data.objects[_n]
    _mi = _o.matrix_world.inverted()
    for _v in _o.data.vertices:
        _w = _o.matrix_world @ _v.co
        if abs(_w.y - 0.50) < 0.02:
            _w.y = -1.00
            _v.co = _mi @ _w
log("rwall0 + skirting run on to y -1.00")
mbox("p63_rack_board", (RX - 0.02, RY0, 0.90), (RX - 0.001, RY1, 2.20), rk)      # tall enough for the BAR / Kar98k (1.2 m)
mbox("p63_rack_shelf", (RX - 0.19, RY0, 0.90), (RX - 0.02, RY1, 0.935), rk)
mbox("p63_rack_lip", (RX - 0.20, RY0, 0.935), (RX - 0.185, RY1, 0.965), rk)
mbox("p63_rack_rail", (RX - 0.035, RY0, 1.50), (RX - 0.02, RY1, 1.56), rk)
mbox("p63_rack_cap", (RX - 0.06, RY0 - 0.01, 2.20), (RX - 0.001, RY1 + 0.01, 2.23), rk)
GUNS = ["bar", "m1_garand", "springfield", "thompsonsmg", "mp40", "mp44", "kar98"]
pitch = (RY1 - RY0) / len(GUNS)
for k in range(len(GUNS) + 1):                          # spacers between the slots (and at the ends), on the top rail
    yy = RY0 + k * pitch
    mbox("p63_rack_spacer%d" % k, (RX - 0.13, yy - 0.012, 1.50), (RX - 0.035, yy + 0.012, 1.56), rk)
# model axes (MOHAA weapons): +X muzzle, +Z sights / top, +Y the gun's left.  Rack: muzzle -> +Z (up), top -> +X (the wall),
# the gun's left -> -Y.  Columns of R are the images of the model's X, Y, Z.
R = Matrix(((0.0, 0.0, 1.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0))).to_4x4()
for k, g in enumerate(GUNS):
    d = os.path.join(STOCK, g)
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(d, g + ".obj"), forward_axis="Y", up_axis="Z")
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        o.matrix_world = R @ Matrix.Scale(S, 4) @ o.matrix_world
        o.name = "p63_gun_%s_%d" % (g, new.index(o))
        o["grp"] = "props"
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in new:
        a, b = wbounds(o)
        lo = Vector([min(lo[i], a[i]) for i in range(3)])
        hi = Vector([max(hi[i], b[i]) for i in range(3)])
    yc = RY0 + (k + 0.5) * pitch
    T = Matrix.Translation((RX - 0.024 - hi.x, yc - (lo.y + hi.y) / 2, 0.936 - lo.z))
    for o in new:
        o.matrix_world = T @ o.matrix_world
        if o.type == "MESH":
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            orient(o)
    for o in new:                                           # v1.10.64 (user: "brighter guns on the rack"): the stock gun textures are
        if o.type == "MESH":                                # authored dark for the game's overbright model lighting (lightgrid x 2);
            brighten(o, float(os.environ.get("RACK_GUN_GAIN", "2.4")))   # baked as plain albedo they read as silhouettes
    log("rack gun", g, "slot", k, "height %.2f m" % (hi.z - lo.z))
# the display lamp (user: "put a light over it that actually showcases it better"): a picture lamp in the attic's own kit - brass
# wall plate and twin arms, a green-enamel trough shade with a white-enamel inside - over the rack, and its baked spot aimed down
# the guns: a soft warm pool on the board fading out on the plaster
RYC = (RY0 + RY1) / 2
LZ = 2.50                                                     # shade top
brass, green, white = (bpy.data.materials[n] for n in ("brass", "shade_green", "enamel_white"))
mbox("p63_rlamp_plate", (RX - 0.012, RYC - 0.05, LZ - 0.02), (RX - 0.001, RYC + 0.05, LZ + 0.07), brass)
for dy in (-0.16, 0.16):
    mbox("p63_rlamp_arm%+d" % int(dy * 100), (RX - 0.42, RYC + dy - 0.008, LZ + 0.012), (RX - 0.012, RYC + dy + 0.008, LZ + 0.026), brass)
    mbox("p63_rlamp_stay%+d" % int(dy * 100), (RX - 0.42, RYC + dy - 0.006, LZ + 0.026), (RX - 0.408, RYC + dy + 0.006, LZ + 0.05), brass)
SW = 0.30                                                    # half length of the trough
mbox("p63_rlamp_top", (RX - 0.48, RYC - SW, LZ), (RX - 0.32, RYC + SW, LZ + 0.012), green)
mbox("p63_rlamp_inner", (RX - 0.475, RYC - SW + 0.004, LZ - 0.004), (RX - 0.325, RYC + SW - 0.004, LZ), white)
mbox("p63_rlamp_front", (RX - 0.492, RYC - SW, LZ - 0.075), (RX - 0.48, RYC + SW, LZ + 0.012), green)
mbox("p63_rlamp_back", (RX - 0.332, RYC - SW, LZ - 0.035), (RX - 0.32, RYC + SW, LZ + 0.012), green)
for sy in (-1, 1):
    mbox("p63_rlamp_end%+d" % sy, (RX - 0.492, RYC + sy * SW - 0.006, LZ - 0.075), (RX - 0.32, RYC + sy * SW + 0.006, LZ + 0.012), green)
mbox("p63_rlamp_bulb", (RX - 0.43, RYC - SW + 0.05, LZ - 0.035), (RX - 0.39, RYC + SW - 0.05, LZ - 0.01), bpy.data.materials["bulb"])
_ld = bpy.data.lights.new("rack_lamp_light", "SPOT")
_ld.energy = float(os.environ.get("RACK_LAMP_W", "100"))
_ld.color = (1.0, 0.82, 0.60)
_ld.spot_size = math.radians(95.0)
_ld.spot_blend = 0.9
_ld.shadow_soft_size = 0.10
_lo = bpy.data.objects.new("rack_lamp_light", _ld)
bpy.context.scene.collection.objects.link(_lo)
_lo.location = (RX - 0.41, RYC, LZ - 0.05)
_aim = Vector((RX - 0.12, RYC, 1.25)) - _lo.location
_lo.rotation_euler = _aim.to_track_quat("-Z", "Y").to_euler()
log("rack lamp", RYC, _ld.energy)

# ---- 11. the General's BLUEPRINTS (v1.10.66; user: "Give the general a blueprint instead of what he looks at now on menu", then
# "There are blueprints in the game too"): the GAME'S OWN U-boat mission plans (gen_blueprint_stock.py, cut from Pak2's naxosplans
# pickups) flat on the work table (top z 0.932, x -2.70 .. -1.33, y 1.005 .. 1.995) under Weathers' hands, reading from the camera
# side: the Type VIIC general arrangement on top (0.88 x 0.55 m), the Naxos radar sheet half under it, turned; a brass weight and an
# ink pot hold the top sheet's corners. Their own bake group "blueprint"
# (2048 atlas: in the 4096 props atlas a sheet would get ~300 texels across). (gen_blueprint_art.py's drawn cyanotype was the first take.)
import bmesh  # noqa: E402


def sheet(name, img, c, w, dpt, yaw_deg, curls=()):
    """a paper sheet w x dpt (m), centre c (its underside), turned yaw_deg, corners (u, v, radius, lift) curling up; UVs from the flat grid"""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=56, y_subdivisions=40, size=1.0)
    o = bpy.context.active_object
    o.name = name
    o["grp"] = "blueprint"
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    bm = bmesh.new()
    bm.from_mesh(me)
    uvlay = bm.loops.layers.uv.active
    for f in bm.faces:
        for lp in f.loops:
            lp[uvlay].uv = (lp.vert.co.x + 0.5, lp.vert.co.y + 0.5)
    for v in bm.verts:
        u0, v0 = v.co.x, v.co.y
        x, y, z = u0 * w, v0 * dpt, 0.0
        for cu, cv, r, lift in curls:
            dd = math.hypot((u0 - cu) * w, (v0 - cv) * dpt)
            if dd < r:
                t = (1 - dd / r) ** 2
                z += lift * t
                x -= math.copysign(1, cu) * lift * t * 0.35          # a curl pulls the paper in a little as it rises
                y -= math.copysign(1, cv) * lift * t * 0.35
        v.co = Vector((x, y, z))
    bm.to_mesh(me)
    bm.free()
    o.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
    o.location = c
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me.shade_smooth()
    me.materials.clear()
    me.materials.append(img_mat(name, os.path.join(ART, img), 0.85))
    return o


BP_C, BP_W, BP_D, BP_YAW = Vector((-2.02, 1.55, 0.9355)), 0.88, 0.55, -4.0
sheet("p66_bp_naxos", "blueprint_naxos.png", Vector((-2.30, 1.72, 0.9335)), 0.50, 0.34, 14.0)
# (curled corners were tried: the selected-to-active bake took the lifted faces as stair-stepped grey blocks - so the sheet lies flat,
# held by the weight, the ink pot and his hands)
sheet("p66_bp_uboat", "blueprint_uboat.png", BP_C, BP_W, BP_D, BP_YAW)
# the weights: a brass paperweight (near-right corner) and a squat ink pot with a black cap (far-left corner)
_rot = Matrix.Rotation(math.radians(BP_YAW), 4, "Z")


def _corner(cu, cv, inset=0.045):
    return BP_C + _rot @ Vector((cu * BP_W - math.copysign(inset, cu), cv * BP_D - math.copysign(inset, cv), 0.0))


pw = _corner(0.5, -0.5)
ip = _corner(-0.5, 0.5)
_mb = bpy.data.materials["brass"].copy()                     # a diffuse bake takes a metal as black: the weight's brass as satin
_mb.name = "brass_satin"
_mbs = _mb.node_tree.nodes.get("Principled BSDF")
_mbs.inputs["Metallic"].default_value, _mbs.inputs["Roughness"].default_value = 0.0, 0.40
_mbs.inputs["Base Color"].default_value = (0.40, 0.26, 0.09, 1.0)        # an old, darkened brass (the metal colour reads pale cream as a diffuse)
# v1.10.66 (coordinator: "the green ink pot and the brass weight read as plain untextured boxes"): real shapes - a brass dome
# paperweight on a turned foot, and a round ink bottle (dark green glass, a paper label, a black screw cap)


def _cyl(name, c, r, z0, h, mat, seg=32, grp="desk"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=seg, radius=r, depth=h, location=(c.x, c.y, z0 + h / 2))
    o = bpy.context.active_object
    o.name = name
    o["grp"] = grp
    o.data.materials.clear()
    o.data.materials.append(mat)
    o.data.shade_smooth()
    return o


_cyl("p66_bp_weight_foot", pw, 0.034, BP_C.z, 0.008, _mb)
bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=0.030, location=(pw.x, pw.y, BP_C.z + 0.008))
_dome = bpy.context.active_object
_dome.name = "p66_bp_weight_dome"
_dome["grp"] = "desk"
_dome.scale = (1.0, 1.0, 0.85)
_bm = bmesh.new()
_bm.from_mesh(_dome.data)
bmesh.ops.delete(_bm, geom=[v for v in _bm.verts if v.co.z < -1e-4], context="VERTS")         # the upper half only
_bm.to_mesh(_dome.data)
_bm.free()
_dome.data.materials.clear()
_dome.data.materials.append(_mb)
_dome.data.shade_smooth()
_cyl("p66_bp_weight_knob", pw, 0.007, BP_C.z + 0.008 + 0.024, 0.012, _mb, 16)
_glass = bpy.data.materials["bak_green"].copy()
_glass.name = "ink_glass"
_gb = _glass.node_tree.nodes.get("Principled BSDF")
_gb.inputs["Base Color"].default_value = (0.020, 0.075, 0.045, 1.0)
_gb.inputs["Roughness"].default_value = 0.18
_cyl("p66_bp_inkpot", ip, 0.024, BP_C.z, 0.040, _glass, 40)
_cyl("p66_bp_inkneck", ip, 0.012, BP_C.z + 0.040, 0.006, _glass, 24)
_cyl("p66_bp_inkcap", ip, 0.0135, BP_C.z + 0.046, 0.016, bpy.data.materials["bak_black"], 24)
_lab = _cyl("p66_bp_inklabel", ip, 0.0243, BP_C.z + 0.010, 0.020, img_mat("ink_label", os.path.join(ART, "ink_label.png"), 0.8), 40)
_lab.data.uv_layers.active.name = "UVMap"
for _poly in _lab.data.polygons:                              # the label image wraps once round the side; caps blank paper
    for _li in _poly.loop_indices:
        _v = _lab.data.vertices[_lab.data.loops[_li].vertex_index].co
        _ang = (math.atan2(_v.y, _v.x) / (2 * math.pi)) % 1.0
        _lab.data.uv_layers.active.data[_li].uv = (_ang if abs(_poly.normal.z) < 0.5 else 0.02, (_v.z + 0.010) / 0.020 if abs(_poly.normal.z) < 0.5 else 0.02)
log("blueprint", tuple(round(c, 3) for c in BP_C), "weights", tuple(round(c, 3) for c in pw), tuple(round(c, 3) for c in ip))

# ---- 10. the Film Room projector's reels turn on hover: the two reels (each two 12-sided faces + a hub) leave the baked projector
# for their own group "reels" (ray-invisible here, so the room and the projector bake with no frozen reel; baked alone after, as
# the fan rotor is) - gen_projector_fx.py builds them as models turning about their axles
import bmesh  # noqa: E402
po = bpy.data.objects["projector_stock_0"]
bm = bmesh.new()
bm.from_mesh(po.data)
bm.faces.ensure_lookup_table()
seen, isl_all = set(), []
for f0 in bm.faces:
    if f0.index in seen:
        continue
    isl, st = [], [f0]
    seen.add(f0.index)
    while st:
        f = st.pop()
        isl.append(f)
        for e in f.edges:
            for gf in e.link_faces:
                if gf.index not in seen:
                    seen.add(gf.index)
                    st.append(gf)
    isl_all.append(isl)
mw = po.matrix_world
reel_faces = []
discs = []
for isl in isl_all:
    V = [mw @ v.co for f in isl for v in f.verts]
    lo = Vector([min(v[i] for v in V) for i in range(3)])
    hi = Vector([max(v[i] for v in V) for i in range(3)])
    ext = hi - lo
    if ext.y < 0.01 and ext.x > 0.10 and ext.z > 0.10:          # a flat reel face (in the x-z plane, the axle along y)
        discs.append(((lo + hi) / 2, max(ext.x, ext.z) / 2, isl))
for c, r, isl in discs:
    reel_faces += isl
for isl in isl_all:                                               # the hubs: small islands on a reel's axle
    V = [mw @ v.co for f in isl for v in f.verts]
    cc = sum(V, Vector()) / len(V)
    if any(abs(cc.x - c.x) < 0.012 and abs(cc.z - c.z) < 0.012 and (max(v.x for v in V) - min(v.x for v in V)) < 0.03 for c, r, _ in discs) and isl not in [d[2] for d in discs]:
        reel_faces += isl
log("projector reels: %d disc faces, %d faces in all" % (len(discs), len(reel_faces)))
assert len(discs) >= 2, "reel discs not found"
ret = bmesh.ops.split(bm, geom=list(set(reel_faces)))
bm.to_mesh(po.data)
bm.free()
bpy.ops.object.select_all(action="DESELECT")
po.select_set(True)
bpy.context.view_layer.objects.active = po
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.object.mode_set(mode="OBJECT")
_rf = set()
for p in po.data.polygons:                                       # re-find the reel faces after the split (by position):
    vs = [mw @ po.data.vertices[i].co for i in p.vertices]       # EVERY corner inside a reel's disc - the arms that hold the reels
    for c, r, _ in discs:                                        # cross the discs but reach the body; they stay with the body
        if all(abs(v.y - c.y) < 0.03 and Vector((v.x - c.x, v.z - c.z)).length < r + 0.003 for v in vs):
            _rf.add(p.index)
for p in po.data.polygons:
    p.select = p.index in _rf
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="SELECTED")
bpy.ops.object.mode_set(mode="OBJECT")
reels = [o for o in bpy.context.selected_objects if o is not po]
for o in reels:
    o.name = "proj_reels"
    o["grp"] = "reels"
    for f in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_shadow", "visible_volume_scatter"):
        if hasattr(o, f):
            setattr(o, f, False)
json.dump({"reels": [{"c": [float(x) for x in c], "r": float(r)} for c, r, _ in discs], "axis_bu": [0.0, 1.0, 0.0]},
          open(os.path.join(os.path.dirname(OUT), "projector_reels.json"), "w"), indent=1)
log("projector reels split:", [o.name for o in reels], "centres", [tuple(round(x, 3) for x in c) for c, r, _ in discs])

# ---- 12. the DESK atlas (v1.10.66; user: "all of the papers and telephones and other objects on the main menu tables read as super
# low quality"). The procedural desk props - the bakelite phones, the green lamps, the field telephone case, the red box, the mug,
# stamp, ink pad, pencils, ashtray, ledger, paper stack, the wall phone - had no group and baked into the room's own 4096 atlas, a
# few texels each. They get their own 4096 atlas (group "desk"); the stock replacements on the desks (folders, trays, toolbox,
# medal box, blueprint weights) go with them, so props keeps the big pieces (rack, cabinets, tables, typewriter).
DESK_PREFIX = ("phone", "wallphone", "lamp_main", "lamp_riser", "lamp_far", "stamp", "pencil", "mug", "trough", "stack", "redbox",
               "pin", "pinhead", "patch", "paper_", "ledger", "inkpad", "cord", "cig", "ashtray", "phoneshelf", "p62_docs", "p62_tray",
               "p62_traypost", "p62_toolbox", "p62_medalbox_body", "p66_bp_")
_nd = 0
for o in bpy.context.scene.objects:
    if o.type in ("MESH", "CURVE") and o.name.startswith(DESK_PREFIX) and o.get("grp") in (None, "props", "desk"):
        if o.name.startswith("p66_bp_uboat") or o.name.startswith("p66_bp_naxos"):
            continue
        o["grp"] = "desk"
        _nd += 1
log("desk atlas:", _nd, "objects")
# coordinator QA of the first desk bake: the book / box / lamp base / mug still read soft. (a) TWO desk atlases: "desk" keeps the
# telephones, the field telephone, the red box and the wall phone; "desk2" the small things on the felt (papers, folders, book,
# medal box, trays, toolbox, lamp, mug, stamp, ink pad, pencils, ashtray, blueprint weights) - each twice the texels.
DESK2_PREFIX = ("p62_docs", "p62_tray", "p62_traypost", "p62_toolbox", "p62_medalbox_body", "p62_box_corner", "p66_bp_", "ledger", "mug",
                "lamp_main", "stamp", "inkpad", "pencil", "ashtray", "cig", "stack", "paper_")
_n2 = 0
for o in bpy.context.scene.objects:
    if o.get("grp") == "desk" and o.name.startswith(DESK2_PREFIX):
        o["grp"] = "desk2"
        _n2 += 1
# (b) a diffuse bake takes a METAL as black (the lamp base baked as a dark blob with a dark bleed halo): every metal on the desks
# gets a satin copy (metallic 0) in its own colour, brass darkened to an old brass
_sat = {}
for o in bpy.context.scene.objects:
    if o.get("grp") not in ("desk", "desk2") or o.type not in ("MESH", "CURVE"):
        continue
    for sl in o.material_slots:
        m = sl.material
        if not m or not m.use_nodes:
            continue
        bs = m.node_tree.nodes.get("Principled BSDF")
        if not bs or bs.inputs["Metallic"].default_value < 0.5:
            continue
        if m.name not in _sat:
            c = m.copy()
            c.name = m.name + "_satin66"
            cb = c.node_tree.nodes.get("Principled BSDF")
            col = list(cb.inputs["Base Color"].default_value)
            if m.name.startswith("brass"):
                col = [0.40, 0.26, 0.09, 1.0]
            for _l in list(cb.inputs["Base Color"].links) + list(cb.inputs["Metallic"].links):     # a driven colour / metal would win
                c.node_tree.links.remove(_l)
            cb.inputs["Metallic"].default_value = 0.0
            cb.inputs["Roughness"].default_value = 0.42
            cb.inputs["Base Color"].default_value = col
            _sat[m.name] = c
        sl.material = _sat[m.name]
# (c) the ledger: green buckram with worn, lighter corners (gen_desk_papers.py ledger_cloth.png), planar UVs
_lg = bpy.data.objects.get("ledger")
if _lg is not None:
    _lm = img_mat("ledger_cloth", os.path.join(ART, "ledger_cloth.png"), 0.85)
    _lg.data.materials.clear()
    _lg.data.materials.append(_lm)
    _lo, _hi = wbounds(_lg)
    _uv = _lg.data.uv_layers[0].data if _lg.data.uv_layers else _lg.data.uv_layers.new(name="UVMap").data
    for _p in _lg.data.polygons:
        _nrm = _p.normal
        for _li in _p.loop_indices:
            _v = _lg.matrix_world @ _lg.data.vertices[_lg.data.loops[_li].vertex_index].co
            if abs(_nrm.z) > 0.5:          # the cover: the whole image
                _uv[_li].uv = ((_v.x - _lo.x) / max(1e-6, _hi.x - _lo.x), (_v.y - _lo.y) / max(1e-6, _hi.y - _lo.y))
            else:                          # the edges: the page-edge strip at the image's bottom
                _uv[_li].uv = (0.02 + 0.96 * ((_v.x - _lo.x + _v.y - _lo.y) / max(1e-6, (_hi.x - _lo.x) + (_hi.y - _lo.y))), 0.03)
# (d) the medal box (the red box on the felt): brass corner plates on its four upright corners
_mbx = bpy.data.objects.get("p62_medalbox_body")
if _mbx is not None:
    _blo, _bhi = wbounds(_mbx)
    _bm = _sat.get("brass") or bpy.data.materials["brass_satin"]
    for _cx in (_blo.x, _bhi.x):
        for _cy in (_blo.y, _bhi.y):
            _x0, _x1 = (_cx - 0.003, _cx + 0.022) if _cx == _blo.x else (_cx - 0.022, _cx + 0.003)
            _y0, _y1 = (_cy - 0.003, _cy + 0.022) if _cy == _blo.y else (_cy - 0.022, _cy + 0.003)
            _c = mbox("p62_box_corner_%d_%d" % (int(_cx == _blo.x), int(_cy == _blo.y)), (_x0, _y0, _blo.z), (_x1, _y1, _bhi.z - 0.002), _bm)
            _c["grp"] = "desk2"
log("desk2 atlas:", _n2, "objects; satin copies:", sorted(_sat))
# (e) the rotary dials' centres and radii (dial plate / card), for retouch.py's dial painting (the baked dials are white splats)
_dl = {}
for o in bpy.context.scene.objects:
    if o.type == "MESH" and o.name.endswith("_card") and (o.name.startswith("phone") or o.name.startswith("wallphone")):
        _pl = bpy.data.objects.get(o.name[:-5] + "_dialplate")
        _vs = [o.matrix_world @ v.co for v in o.data.vertices]
        _c = sum(_vs, Vector()) / len(_vs)
        _r = max((v - _c).length for v in _vs)
        _rp = max(((_pl.matrix_world @ v.co) - _c).length for v in _pl.data.vertices) if _pl else _r * 1.15
        _dl[o.name[:-5]] = {"c": list(_c), "r_card": _r, "r_plate": _rp}
json.dump(_dl, open(os.path.join(os.path.dirname(OUT), "dials.json"), "w"), indent=1)
log("dials:", sorted(_dl))

bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
log("saved", OUT)
