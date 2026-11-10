"""rotor_visible.py - run BEFORE attic_bake3.py in the same Blender call when baking group "rotor" alone:
    blender -b attic_room_62.blend --python rotor_visible.py --python attic_bake3.py -- --out <dir> --groups rotor
attic62_edit.py makes the fan blades invisible to every ray so the room bakes no frozen blade shadow; the rotor's own
selected-to-active bake needs them visible (its rays land on the scene geometry; with them hidden the atlas came out black)."""
import bpy

for o in bpy.data.objects:
    if o.get("grp") in ("rotor", "reels"):      # v1.10.63: the projector reels the same way
        for f in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_shadow", "visible_volume_scatter"):
            if hasattr(o, f):
                setattr(o, f, True)
        print("[rotor_visible]", o.name)
        # the blades are brass at Metallic 1: attic_bake3 bakes DIFFUSE + EMIT only, so a metal bakes black (the rotor atlas came
        # out all zero).  For this bake only: the same brass colour as a satin (non-metal) finish, so the lit tone is kept
        for sl in o.material_slots:
            m = sl.material
            if m and m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == "BSDF_PRINCIPLED" and n.inputs["Metallic"].default_value > 0.5:
                        n.inputs["Metallic"].default_value = 0.0
                        bc = n.inputs["Base Color"]
                        if not bc.is_linked:
                            c = bc.default_value
                            print("[rotor_visible] %s: metallic -> 0, base %s" % (m.name, tuple(round(x, 3) for x in c[:3])))
