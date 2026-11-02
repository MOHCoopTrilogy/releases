"""ng_bake.py - re-bake ONLY the attic's wall map group with the new theatre map (gen_theatremap.py), through the attic bake itself.

    blender -b H:/hzm_archive/menuattic/export/attic_room.blend -t 4 --python ng_bake.py -- --map H:/hzm_work/ng/tex/wallmap_med.png --out H:/hzm_work/ng/bake_wm --occ H:/hzm_work/ng/occ.json

The wallmap material's image is pointed at the new map (the archive's wallmap.png is never touched), then menus3d/attic_bake3.py
runs unchanged (no --nook: see below) on only the wallmap group (one 4096 atlas, ~1 min on the GPU).  Everything else in the shipped attic stays as it is."""
import os, sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
MAP = argv[argv.index("--map") + 1]
n = 0
for img in bpy.data.images:
    if os.path.basename(img.filepath.replace("\\", "/")).lower() == "wallmap.png":
        img.filepath = MAP
        img.reload()
        n += 1
assert n == 1, "wallmap.png images found: %d" % n
# the map is baked with NOTHING between it and the full-map camera: the radio shelf (attic --nook splice), the old radio stack, the
# records-desk clutter, chairs and the hanging sign (occ.json) would otherwise leave their baked shadows on the map, which the
# full-map view shows without the objects (first engine run: dark blurred blocks over Sicily).  The attic home view shows the
# same evenly lit map behind its shelf.
import json, re
OCC = json.load(open(argv[argv.index("--occ") + 1])) if "--occ" in argv else {}
gone = 0
for o in list(bpy.data.objects):
    if o.name.startswith(("keylamp2", "radiotable", "radio_", "ammo_box", "cord_r", "outlet_box")) or re.match(r"pin\d+$", o.name) or (o.name in OCC and not o.name.startswith("beam")):
        bpy.data.objects.remove(o, do_unlink=True)
        gone += 1
print("NG cleared", gone, "objects in front of the map")
if "--groups" not in sys.argv:
    sys.argv += ["--groups", "wallmap"]
SRC = os.path.join(r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d", "attic_bake3.py")
exec(compile(open(SRC, encoding="utf-8").read(), SRC, "exec"))
