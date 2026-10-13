# Look-test renders of the downloaded Sketchfab C96 (untrusted data: read only, nothing from the archive is executed).
# Run:  blender --background --factory-startup --disable-autoexec --python bl_render.py -- --fbx F --tex DIR --out DIR
#           [--stats parts.json] [--views a,b,..] [--hide G1,G2] [--bolt 0.13] [--old old_c96.json]
# Views: delivered, left, right, top, aim, aim_cocked, front34, boltback, boltback_top, old_left
import bpy, sys, json, math, os, argparse
from mathutils import Vector, Matrix, Quaternion

ap = argparse.ArgumentParser()
ap.add_argument('--fbx'); ap.add_argument('--tex'); ap.add_argument('--out')
ap.add_argument('--stats', default=None); ap.add_argument('--views', default='')
ap.add_argument('--hide', default='Stock,StockCup,Clip,FreshBullet,EjectBullet')
ap.add_argument('--gun', default='Root,Slide,Hammer,Trigger,Ring')
ap.add_argument('--bolt', type=float, default=0.13)       # bolt travel, share of the pistol's length
ap.add_argument('--samples', type=int, default=64)
ap.add_argument('--old', default=None)
ap.add_argument('--aim', default='')                      # "rear_y,rear_z,front_y,front_z" override
ap.add_argument('--aimdist', type=float, default=1.2)     # eye distance behind the rear sight, in pistol lengths
ap.add_argument('--aimlens', type=float, default=110.0)
ap.add_argument('--suffix', default='')
ap.add_argument('--w', type=int, default=1600); ap.add_argument('--h', type=int, default=900)
A = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.fbx_import(filepath=A.fbx)
sc = bpy.context.scene
ob = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
me = ob.data

# ---------------------------------------------------------------- animation facts, then drop the animation
anim = {}
for f in range(1, 78):
    sc.frame_set(f)
    row = {}
    for pb in arm.pose.bones:
        q = pb.rotation_quaternion if pb.rotation_mode == 'QUATERNION' else pb.rotation_euler.to_quaternion()
        row[pb.name] = (round(math.degrees(q.angle), 2), [round(x, 4) for x in pb.location], [round(x, 3) for x in pb.scale])
    anim[f] = row
ham = max(range(1, 78), key=lambda f: anim[f]['Hammer'][0])
sc.frame_set(ham)
HAMQ = arm.pose.bones['Hammer'].rotation_quaternion.copy()
arm.animation_data_clear()


def reset_pose():
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)


reset_pose()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- parts by dominant vertex group
gn = [g.name for g in ob.vertex_groups]
dom = []
for v in me.vertices:
    best = max(v.groups, key=lambda g: g.weight) if v.groups else None
    dom.append(gn[best.group] if best else None)
blend = sum(1 for v in me.vertices if sum(1 for g in v.groups if g.weight > 0.02) > 1)
me.calc_loop_triangles()
parts = {}
for t in me.loop_triangles:
    g = dom[t.vertices[0]]
    parts.setdefault(g, {'tris': 0, 'v': set()})
    parts[g]['tris'] += 1
    parts[g]['v'].update(t.vertices)
MW = ob.matrix_world
co = [MW @ v.co for v in me.vertices]
pstat = {}
for g, d in parts.items():
    pts = [co[i] for i in d['v']]
    mn = [min(p[k] for p in pts) for k in range(3)]; mx = [max(p[k] for p in pts) for k in range(3)]
    pstat[str(g)] = {'tris': d['tris'], 'min': [round(x, 4) for x in mn], 'max': [round(x, 4) for x in mx]}
GUN = set(A.gun.split(','))
gpts = [co[i] for i in range(len(co)) if dom[i] in GUN]
gmn = Vector([min(p[k] for p in gpts) for k in range(3)]); gmx = Vector([max(p[k] for p in gpts) for k in range(3)])
L = gmx.y - gmn.y
ctr = (gmn + gmx) / 2
prof = []
NB = 48
for b in range(NB):
    y0 = gmn.y + L * b / NB; y1 = y0 + L / NB
    zs = [p.z for i, p in enumerate(co) if dom[i] in GUN and y0 <= p.y < y1 + 1e-9 and abs(p.x) < 0.25 * (gmx.x - gmn.x)]
    zh = [p.z for i, p in enumerate(co) if dom[i] == 'Hammer' and y0 <= p.y < y1 + 1e-9]
    prof.append([round((y0 + y1) / 2, 3), round(max(zs), 4) if zs else None, round(max(zh), 4) if zh else None])
if A.stats:
    keyf = {f: {b: anim[f][b] for b in ('Hammer', 'Trigger', 'EjectBullet', 'Slide')} for f in (1, 11, 15, 19, 23, 27, 37, 50, 77)}
    json.dump({'parts': pstat, 'verts_weighted_to_2plus_bones': blend, 'gun_min': list(gmn), 'gun_max': list(gmx),
               'gun_len': L, 'hammer_max_frame': ham, 'hammer_max_deg': anim[ham]['Hammer'][0], 'anim_keyframes': keyf,
               'top_profile_y_zmaxCentre_zmaxHammer': prof}, open(A.stats, 'w'), indent=1)
    print('STATS_OK')
views = [v for v in A.views.split(',') if v]
if not views:
    sys.exit(0)

# ---------------------------------------------------------------- material from the archive's own PBR maps
def img(name, noncolor):
    im = bpy.data.images.load(os.path.join(A.tex, name), check_existing=True)
    if noncolor:
        im.colorspace_settings.name = 'Non-Color'
    return im


mat = bpy.data.materials.new('c96_pbr'); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
outn = nt.nodes.new('ShaderNodeOutputMaterial'); bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
nt.links.new(bsdf.outputs[0], outn.inputs[0])
for nm, sock, nc in (('Mauser_L_Baker_BaseColor.1001.png', 'Base Color', False), ('Mauser_L_Baker_Roughness.1001.png', 'Roughness', True),
                     ('Mauser_L_Baker_Metallic.1001.png', 'Metallic', True)):
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(nm, nc)
    nt.links.new(t.outputs['Color'], bsdf.inputs[sock])
t = nt.nodes.new('ShaderNodeTexImage'); t.image = img('Mauser_L_Baker_Normal.1001.png', True)
nm_ = nt.nodes.new('ShaderNodeNormalMap')
nt.links.new(t.outputs['Color'], nm_.inputs['Color']); nt.links.new(nm_.outputs['Normal'], bsdf.inputs['Normal'])
me.materials.clear(); me.materials.append(mat)

# ---------------------------------------------------------------- the mod's current C96 (plain diffuse, as the game draws it)
oldobs = []
if A.old and 'old_left' in views:
    od = json.load(open(A.old))
    allp = [Vector(p) for s in od['surfs'] for p in s['P']]
    omn = Vector([min(p[k] for p in allp) for k in range(3)]); omx = Vector([max(p[k] for p in allp) for k in range(3)])
    k = L / (omx.x - omn.x)
    octr = (omn + omx) / 2
    # old +X muzzle -> +Y; the old mesh's model space is root-flipped (grip up), so turn it 180 deg about the muzzle axis first
    R = Matrix.Rotation(math.radians(90), 4, 'Z') @ Matrix.Rotation(math.radians(180), 4, 'X')
    for s in od['surfs']:
        m = bpy.data.meshes.new('old_' + s['name'])
        vs = [(R @ ((Vector(p) - octr) * k)) + ctr for p in s['P']]
        m.from_pydata(vs, [], [(a, c, b) for a, b, c in s['tri']])
        uvl = m.uv_layers.new(name='UVMap')
        for lp in m.loops:
            u, v = s['UV'][lp.vertex_index]
            uvl.data[lp.index].uv = (u, 1.0 - v)
        for p in m.polygons:
            p.use_smooth = True
        mt = bpy.data.materials.new('old_' + s['name']); mt.use_nodes = True
        b2 = mt.node_tree.nodes.get('Principled BSDF')
        b2.inputs['Roughness'].default_value = 0.75; b2.inputs['Metallic'].default_value = 0.0
        if s.get('tex') and os.path.exists(s['tex']):
            ti = mt.node_tree.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(s['tex'], check_existing=True)
            mt.node_tree.links.new(ti.outputs['Color'], b2.inputs['Base Color'])
        m.materials.append(mt)
        o2 = bpy.data.objects.new('old_' + s['name'], m); sc.collection.objects.link(o2); oldobs.append(o2)

# ---------------------------------------------------------------- world, camera, sun
w = bpy.data.worlds.new('studio'); sc.world = w; w.use_nodes = True
wn = w.node_tree; wn.nodes.clear()
wo = wn.nodes.new('ShaderNodeOutputWorld'); mix = wn.nodes.new('ShaderNodeMixShader')
bg1 = wn.nodes.new('ShaderNodeBackground'); bg2 = wn.nodes.new('ShaderNodeBackground'); lp = wn.nodes.new('ShaderNodeLightPath')
tc = wn.nodes.new('ShaderNodeTexCoord'); sx = wn.nodes.new('ShaderNodeSeparateXYZ'); mr = wn.nodes.new('ShaderNodeMapRange')
wn.links.new(tc.outputs['Generated'], sx.inputs[0]); wn.links.new(sx.outputs['Z'], mr.inputs['Value'])
mr.inputs['From Min'].default_value = -1.0; mr.inputs['From Max'].default_value = 1.0
mr.inputs['To Min'].default_value = 0.25; mr.inputs['To Max'].default_value = 1.5
wn.links.new(mr.outputs[0], bg1.inputs['Strength']); bg1.inputs['Color'].default_value = (1, 1, 1, 1)
bg2.inputs['Color'].default_value = (0.42, 0.43, 0.45, 1); bg2.inputs['Strength'].default_value = 1.0
wn.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0]); wn.links.new(bg1.outputs[0], mix.inputs[1]); wn.links.new(bg2.outputs[0], mix.inputs[2])
wn.links.new(mix.outputs[0], wo.inputs['Surface'])

cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
sd = bpy.data.lights.new('sun', 'SUN'); sun = bpy.data.objects.new('sun', sd); sc.collection.objects.link(sun)
sd.energy = 2.5; sd.angle = 0.5
cd.clip_start = 0.01; cd.clip_end = 500


def look(o, pos, tgt, up=Vector((0, 0, 1))):
    f = (tgt - pos).normalized(); r = f.cross(up).normalized(); u = r.cross(f)
    M = Matrix((r, u, -f)).transposed().to_4x4(); M.translation = pos
    o.matrix_world = M
    return f, r, u


def shoot(name, pos, tgt, ortho=None, lens=50.0, up=Vector((0, 0, 1))):
    f, r, u = look(cam, pos, tgt, up)
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.type = 'PERSP'; cd.lens = lens
    d = (f * 0.55 - u * 0.75 + r * 0.35).normalized()
    look(sun, tgt - d * 20, tgt, up if abs(d.dot(up)) < 0.95 else Vector((0, 1, 0)))
    sc.render.filepath = os.path.join(A.out, name + A.suffix + '.jpg')
    bpy.ops.render.render(write_still=True)
    print('RENDERED', name)


for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        sc.render.engine = eng; break
    except TypeError:
        pass
try:
    sc.eevee.taa_render_samples = A.samples
    sc.eevee.use_raytracing = True
except Exception as e:
    print('eevee opt', e)
sc.render.resolution_x = A.w; sc.render.resolution_y = A.h; sc.render.resolution_percentage = 100
try:
    sc.render.image_settings.media_type = 'IMAGE'
except Exception:
    pass
sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 92
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'

HIDE = [h for h in A.hide.split(',') if h]


def pose(hide=True, cocked=False, bolt=False):
    reset_pose()
    if hide:
        for h in HIDE:
            arm.pose.bones[h].scale = (0, 0, 0)
    if cocked:
        arm.pose.bones['Hammer'].rotation_quaternion = HAMQ
    bpy.context.view_layer.update()
    if bolt:
        pb = arm.pose.bones['Slide']
        pb.matrix = Matrix.Translation((0, -A.bolt * L, 0)) @ pb.matrix
    bpy.context.view_layer.update()


asp = A.w / A.h
H = gmx.z - gmn.z
side = max(L * 1.12, H * 1.15 * asp)
fmn = Vector([min(p[k] for p in co) for k in range(3)]); fmx = Vector([max(p[k] for p in co) for k in range(3)])
fctr = (fmn + fmx) / 2
if A.aim:
    ry, rz, fy, fz = [float(x) for x in A.aim.split(',')]
else:
    fy, fz = max(((p[0], p[1]) for p in prof if p[1] is not None and p[0] > gmx.y - 0.12 * L), key=lambda t: t[1])
    ry, rz = max(((p[0], p[1]) for p in prof if p[1] is not None and gmn.y + 0.15 * L < p[0] < gmn.y + 0.6 * L), key=lambda t: t[1])
    rz -= 0.008 * L
front = Vector((0, fy, fz)); rear = Vector((0, ry, rz))
eye = rear + (rear - front).normalized() * (A.aimdist * L)
print('AIM front', front[:], 'rear', rear[:], 'eye', eye[:])

for o2 in oldobs:
    o2.hide_render = True
for v in views:
    if v == 'delivered':
        pose(hide=False)
        shoot(v, fctr + Vector((-0.75, 0.55, 0.38)).normalized() * 40, fctr, ortho=(fmx - fmn).length * 0.95)
    elif v == 'left':
        pose(); shoot(v, ctr + Vector((-40, 0, 0)), ctr, ortho=side)
    elif v == 'right':
        pose(); shoot(v, ctr + Vector((40, 0, 0)), ctr, ortho=side)
    elif v == 'top':
        pose(); shoot(v, ctr + Vector((0, 0, 40)), ctr, ortho=side, up=Vector((-1, 0, 0)))
    elif v == 'aim':
        pose(); shoot(v, eye, front, lens=A.aimlens)
    elif v == 'aim_cocked':
        pose(cocked=True); shoot(v, eye, front, lens=A.aimlens)
    elif v == 'front34':
        pose(); shoot(v, ctr + Vector((-0.62, 0.72, 0.30)).normalized() * 40, ctr, ortho=side * 0.9)
    elif v == 'boltback':
        pose(cocked=True, bolt=True); shoot(v, ctr + Vector((-40, 0, 0)), ctr, ortho=side)
    elif v == 'boltback_top':
        pose(cocked=True, bolt=True)
        tg = Vector((0, gmn.y + 0.42 * L, gmx.z - 0.12 * H))
        shoot(v, tg + Vector((-0.45, -0.55, 0.70)).normalized() * 40, tg, ortho=side * 0.55)
    elif v == 'old_left' and oldobs:
        ob.hide_render = True
        for o2 in oldobs:
            o2.hide_render = False
        shoot(v, ctr + Vector((-40, 0, 0)), ctr, ortho=side)
        ob.hide_render = False
        for o2 in oldobs:
            o2.hide_render = True
print('DONE')
