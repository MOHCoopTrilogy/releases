"""attic67_edit.py - v1.10.67 the attic's windows (Blender, no render).

    blender -b H:/hzm_work/attic62/attic_room_66.blend -t 2 --python attic67_edit.py -- <out.blend>

User (via the coordinator, 2026-11-09): (3) "make the gable window BIGGER ... so more of the outside shows past the rafter from the
home view" and (1) "a period roof SKYLIGHT in the big sloped ceiling on the left of the home view".

  gable    the 0.62 x 0.62 m four-pane window (window_l: win_frame*, win_mull_*, win_sky) becomes a 1.50 x 0.90 m six-pane casement
           (3 x 2 panes) at x -4.75 .. -3.25, z 1.15 .. 2.05 BU - as big as the gable allows under the left roof slope (the roof is at
           z 2.13 over its left edge) and clear of the wall map (x -3.02). The back wall is cut where the glass is (a boolean), so
           the bake sees the real opening; the 'moon' area light that stood in the old pane grows with it.
  skylight a period cast-iron roof light in the left slope (roof-1) between the rafters beam1 (y 3.0) and the purlin beam2 (y 4.6):
           0.95 m along the slope x 1.15 m, two panes; frame boxes like the right-hand skylight's, a glass plane (moon_sky2: a bake
           skip material) and a matching boolean cut in roof-1. It sits in the upper left of the main menu's view.
Writes window67.json (the gable pane and the skylight's glass, in BU) for gen_window_view.py.
"""
import json, math, os, sys
import bpy, bmesh
from mathutils import Matrix, Vector

OUT = sys.argv[sys.argv.index("--") + 1]
SC = bpy.context.scene
log = lambda *a: print("[attic67]", *a, flush=True)  # noqa: E731


def box(name, lo, hi, mat, parent=None):
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


def frame_hole(obj, outer, inner):
    """replace a single planar quad with the same quad minus a rectangle: 8 vertices, 4 'picture frame' faces (the bake re-unwraps)"""
    o_n = obj.data.polygons[0].normal.copy() if obj.data.polygons else None
    me = obj.data
    # both rings in one cyclic order (the quad's vertex order is not guaranteed to run round it: crossed faces left holes)
    cen = sum(outer, Vector()) / 4
    n = (outer[1] - outer[0]).cross(outer[2] - outer[0])
    if n.length < 1e-9:
        n = (outer[2] - outer[0]).cross(outer[3] - outer[0])
    n.normalize()
    ax = (outer[0] - cen).normalized()
    ay = n.cross(ax)
    order = sorted(range(4), key=lambda i: math.atan2((outer[i] - cen).dot(ay), (outer[i] - cen).dot(ax)))
    outer = [outer[i] for i in order]
    inner = [inner[i] for i in order]
    bm = bmesh.new()
    vo = [bm.verts.new(p) for p in outer]
    vi = [bm.verts.new(p) for p in inner]
    for k in range(4):
        bm.faces.new((vo[k], vo[(k + 1) % 4], vi[(k + 1) % 4], vi[k]))
    bm.normal_update()
    if o_n is not None:
        for f in bm.faces:
            if f.normal.dot(obj.matrix_world.to_3x3().inverted() @ (obj.matrix_world.to_3x3() @ o_n)) < 0:
                f.normal_flip()
    bm.to_mesh(me)
    bm.free()
    me.update()
    log("hole in", obj.name, len(me.polygons), "faces")


def world_quad(obj):
    return [obj.matrix_world @ v.co for v in obj.data.vertices]


# ---------------------------------------------------------------- the gable window
for o in list(bpy.data.objects):
    if o.name.startswith(("win_frame", "win_mull", "win_sky")):
        bpy.data.objects.remove(o, do_unlink=True)
X0, X1, Z0, Z1 = -4.75, -3.25, 1.15, 2.05
WY = 6.82
F = 0.06                                   # frame width
box("win_frame", (X0 - F, 6.74, Z1), (X1 + F, 6.86, Z1 + F), "beam")
box("win_frame.001", (X0 - F, 6.74, Z0 - F), (X1 + F, 6.86, Z0), "beam")
box("win_frame.002", (X0 - F, 6.74, Z0), (X0, 6.86, Z1), "beam")
box("win_frame.003", (X1, 6.74, Z0), (X1 + F, 6.86, Z1), "beam")
box("win_sill", (X0 - F - 0.04, 6.66, Z0 - F - 0.03), (X1 + F + 0.04, 6.86, Z0 - F), "beam")          # a sill to rest the eye on
for k in (1, 2):
    xm = X0 + (X1 - X0) * k / 3
    box("win_mull_v%d" % k, (xm - 0.016, 6.75, Z0), (xm + 0.016, 6.83, Z1), "beam")
box("win_mull_h", (X0, 6.75, (Z0 + Z1) / 2 - 0.016), (X1, 6.83, (Z0 + Z1) / 2 + 0.016), "beam")
me = bpy.data.meshes.new("win_sky")
me.from_pydata([(X0, WY, Z0), (X1, WY, Z0), (X1, WY, Z1), (X0, WY, Z1)], [], [(0, 1, 2, 3)])
g = bpy.data.objects.new("win_sky", me)
SC.collection.objects.link(g)
g.data.materials.append(bpy.data.materials["moon_sky"])
bw = bpy.data.objects["backwall"]
assert len(bw.data.vertices) == 4, "backwall is expected to be one quad"
mwi = bw.matrix_world.inverted()
# outer corners in the quad's own order (local), inner = the pane, wound the same way round
oc = [v.co.copy() for v in bw.data.vertices]
wc = [bw.matrix_world @ c for c in oc]
cen = sum(wc, Vector()) / 4
inner_w = []
for c in wc:
    inner_w.append(Vector((X0 if c.x < cen.x else X1, WY, Z0 if c.z < cen.z else Z1)))
frame_hole(bw, oc, [mwi @ p for p in inner_w])
# the gable wall stood on above the roof (to z 5.5): through the new skylight it was all you saw. Cut it off along the left roof's
# plane (z = 1.6 + (x + 5.9) * K, K = 3.02 / 6.5), 2 cm above it so the joint stays closed.
_K = (4.62 - 1.6) / 6.5
_a = math.atan(_K)
_bm = bmesh.new()
_bm.from_mesh(bw.data)
_n = Vector((-math.sin(_a), 0.0, math.cos(_a)))
bmesh.ops.bisect_plane(_bm, geom=_bm.verts[:] + _bm.edges[:] + _bm.faces[:], plane_co=bw.matrix_world.inverted() @ Vector((-5.9, WY, 1.6 + 0.02 / math.cos(_a))),
                       plane_no=(bw.matrix_world.inverted().to_3x3() @ _n).normalized(), clear_outer=True)
_bm.to_mesh(bw.data)
_bm.free()
bw.data.update()
log("backwall cut to the roof line", len(bw.data.polygons), "faces")
moon = bpy.data.objects.get("moon")
if moon and moon.type == 'LIGHT':
    moon.location = ((X0 + X1) / 2, 6.6, (Z0 + Z1) / 2)
    if moon.data.type == 'AREA':
        moon.data.shape = 'RECTANGLE'
        moon.data.size, moon.data.size_y = X1 - X0, Z1 - Z0
        moon.data.energy *= (X1 - X0) * (Z1 - Z0) / (0.62 * 0.62) * 0.7
    log("moon light", moon.data.type, moon.data.energy)

# ---------------------------------------------------------------- the skylight in the left slope
roof = bpy.data.objects["roof-1"]
# roof-1 runs from (x -5.9, z 1.6) up to (x 0.6, z 4.62): z(x) = 1.6 + (x + 5.9) * k
K = (4.62 - 1.6) / 6.5
ang = math.atan(K)
SX0, SX1 = -3.35, -2.45                    # along x (0.99 m along the slope)
SY0, SY1 = 3.30, 4.42                      # between the rafter beam1 (y 3.09) and the purlin beam2 (y 4.52)


def rz(x):
    return 1.6 + (x + 5.9) * K


cx, cz = (SX0 + SX1) / 2, rz((SX0 + SX1) / 2)
assert len(roof.data.vertices) == 4, "roof-1 is expected to be one quad"
rmi = roof.matrix_world.inverted()
roc = [v.co.copy() for v in roof.data.vertices]
rwc = [roof.matrix_world @ c for c in roc]
rcen = sum(rwc, Vector()) / 4
inner_r = []
for c in rwc:
    xx = SX0 if c.x < rcen.x else SX1
    yy = SY0 if c.y < rcen.y else SY1
    inner_r.append(Vector((xx, yy, rz(xx))))
frame_hole(roof, roc, [rmi @ p for p in inner_r])
log("roof-1 faces", len(roof.data.polygons))


def tilted_box(name, a0, a1, y0, y1, t0, t1, mat):
    """a box in the slope's frame: a along the slope's x, y across, t along the normal (0 = the roof plate), metres"""
    o = box(name, (a0, y0, t0), (a1, y1, t1), mat)
    o.matrix_world = Matrix.Translation((cx, 0, cz)) @ Matrix.Rotation(-ang, 4, 'Y')
    return o


L = (SX1 - SX0) / math.cos(ang)            # length along the slope
A0, A1 = -L / 2, L / 2
FR = 0.07
tilted_box("skyl_fr0", A0 - FR, A1 + FR, SY0 - FR, SY0, -0.10, 0.06, "beam")
tilted_box("skyl_fr1", A0 - FR, A1 + FR, SY1, SY1 + FR, -0.10, 0.06, "beam")
tilted_box("skyl_fr2", A0 - FR, A0, SY0, SY1, -0.10, 0.06, "beam")
tilted_box("skyl_fr3", A1, A1 + FR, SY0, SY1, -0.10, 0.06, "beam")
tilted_box("skyl_bar", A0, A1, (SY0 + SY1) / 2 - 0.018, (SY0 + SY1) / 2 + 0.018, -0.04, 0.03, "beam")
gm = bpy.data.meshes.new("skyl_glass")
gm.from_pydata([(A0, SY0, 0.0), (A1, SY0, 0.0), (A1, SY1, 0.0), (A0, SY1, 0.0)], [], [(0, 1, 2, 3)])
gl = bpy.data.objects.new("skyl_glass", gm)
SC.collection.objects.link(gl)
gl.data.materials.append(bpy.data.materials["moon_sky2"])
gl.matrix_world = Matrix.Translation((cx, 0, cz)) @ Matrix.Rotation(-ang, 4, 'Y')
gw = [list(gl.matrix_world @ v.co) for v in gm.vertices]
log("skylight glass", [[round(c, 3) for c in p] for p in gw])

bpy.ops.wm.save_as_mainfile(filepath=OUT)
json.dump({"gable": {"x0": X0, "x1": X1, "z0": Z0, "z1": Z1, "y": WY},
           "skylight": {"corners": gw, "x0": SX0, "x1": SX1, "y0": SY0, "y1": SY1, "k": K}},
          open(os.path.join(os.path.dirname(OUT), "window67.json"), "w"), indent=1)
log("saved", OUT)
