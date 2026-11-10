"""blender -b attic_room_67.blend --python wx_room_preview.py -- <out.png> [w h] : the main menu's home camera, Workbench, with the
bake-skip planes hidden and a bright green world, so every opening to the outside shows (QA for the window / skylight sizes)."""
import bpy, math, sys
a = sys.argv[sys.argv.index("--") + 1:]
out = a[0]
W, H = (int(a[1]), int(a[2])) if len(a) >= 3 else (1720, 720)
SC = bpy.context.scene
for o in SC.objects:
    if o.type == 'MESH' and any(s.material and s.material.name in ("haze", "moon_sky", "moon_sky2", "frosted", "glass") for s in o.material_slots):
        o.hide_render = True
SC.render.engine = 'BLENDER_WORKBENCH'
SC.display.shading.light = 'STUDIO'
SC.display.shading.color_type = 'MATERIAL'
SC.display.shading.show_shadows = False
w = bpy.data.worlds.new("g")
SC.world = w
w.color = (0.1, 1.0, 0.2)
SC.display.shading.background_type = 'WORLD' if hasattr(SC.display.shading, "background_type") else 'THEME'
cd = bpy.data.cameras.new("home")
cd.sensor_fit = 'VERTICAL'
cd.angle_y = math.radians(55.11)
cd.clip_start = 0.02
co = bpy.data.objects.new("home", cd)
SC.collection.objects.link(co)
co.location = (-21.0 / 52.5, -36.7 / 52.5, 102.4 / 52.5)
co.rotation_euler = (math.radians(90 - 7.01), 0, 0)
SC.camera = co
SC.render.resolution_x, SC.render.resolution_y = W, H
SC.render.film_transparent = False
SC.render.filepath = out
bpy.ops.render.render(write_still=True)
print("PREVIEW", out)
