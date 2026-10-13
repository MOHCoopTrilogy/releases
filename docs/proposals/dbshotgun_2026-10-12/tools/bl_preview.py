# Blender (background, factory startup, autoexec off): neutral-lit previews of a .blend
#   blender --background --factory-startup --disable-autoexec --python tools/bl_preview.py -- <file.blend> <out_prefix> [texdir]
# texdir given  -> every material is replaced by diffuse*AO from <texdir>/doubleBarrelD.png / AO.png (the low file)
# texdir absent -> the file's own materials are rendered as they are (the high file)
import bpy, sys, math, os
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
path, outp = args[0], args[1]
texdir = args[2] if len(args) > 2 else None
bpy.ops.wm.open_mainfile(filepath=path, load_ui=False, use_scripts=False)
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT', 'EMPTY'):
        bpy.data.objects.remove(o)

if texdir:
    d = bpy.data.images.load(os.path.join(texdir, 'doubleBarrelD.png'))
    a = bpy.data.images.load(os.path.join(texdir, 'doubleBarrelAO.png'))
    a.colorspace_settings.name = 'Non-Color'
    r = bpy.data.images.load(os.path.join(texdir, 'doubleBarrelR.png'))
    r.colorspace_settings.name = 'Non-Color'
    m = bpy.data.materials.new('preview')
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes['Principled BSDF']
    td = nt.nodes.new('ShaderNodeTexImage'); td.image = d
    ta = nt.nodes.new('ShaderNodeTexImage'); ta.image = a
    tr = nt.nodes.new('ShaderNodeTexImage'); tr.image = r
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = 1.0
    nt.links.new(td.outputs['Color'], mx.inputs[6])
    nt.links.new(ta.outputs['Color'], mx.inputs[7])
    nt.links.new(mx.outputs[2], bs.inputs['Base Color'])
    nt.links.new(tr.outputs['Color'], bs.inputs['Roughness'])
    for o in bpy.data.objects:
        if o.type == 'MESH':
            for s in o.material_slots:
                s.material = m

mn = Vector((1e9,) * 3); mx_ = Vector((-1e9,) * 3)
for o in bpy.data.objects:
    if o.type == 'MESH':
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i]); mx_[i] = max(mx_[i], w[i])
ctr = (mn + mx_) / 2
size = (mx_ - mn).length

sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 48
sc.cycles.use_denoising = True
sc.render.threads_mode = 'FIXED'
sc.render.threads = 4
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.image_settings.file_format = 'JPEG'
sc.render.image_settings.quality = 90
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); sc.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.55, 0.57, 0.6, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 0.9

def lamp(name, loc, energy):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.size = size
    ob = bpy.data.objects.new(name, l); sc.collection.objects.link(ob)
    ob.location = ctr + Vector(loc) * size
    ob.rotation_euler = (ctr - ob.location).to_track_quat('-Z', 'Y').to_euler()
lamp('key', (0.6, -0.9, 0.9), 900 * size * size / 20)
lamp('fill', (-0.8, 0.7, 0.4), 350 * size * size / 20)

cam = bpy.data.cameras.new('c'); cam.lens = 70
co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
views = {
    'threequarter': (0.75, -0.95, 0.45),
    'side': (0.0, -1.0, 0.0),
    'side_other': (0.0, 1.0, 0.0),
    'top': (0.0, -0.001, 1.0),
    'rear': (-1.0, 0.0, 0.12),
    'muzzle': (1.0, -0.25, 0.2),
}
for name, d in views.items():
    v = Vector(d).normalized()
    dist = size * (1.55 if name not in ('rear', 'muzzle') else 1.2)
    co.location = ctr + v * dist
    co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = outp + '_' + name + '.jpg'
    bpy.ops.render.render(write_still=True)
    print('WROTE', sc.render.filepath)
