"""hub_bake.py - the attic bake (menus3d/attic_bake3.py) run on the prepared multiplayer hub, with the hub's own groups.

    blender -b H:/hzm_work/mphub3d/hub_mp.blend -t 4 --python hub_bake.py -- --out H:/hzm_work/mphub3d/bake --onepass bg,chrome [--bg 4096] [--bg-spp 24] [--groups floor,chrome,bg]

Not a fork: attic_bake3.py is read and executed with exactly two parts swapped (asserted), so every fix to the attic bake
reaches the hub.  Swapped: group_of (hub groups) and PLAN (atlas size / spp per group).
Groups:  floor  the procedural plank quad -> tiling CC0 wood x a separate low-res lightmap (as the attic)
         quad   the lettered boards (game-type board, SERVICE RECORD face + plaque): source image x a 256 px lightmap (QUAD_POST)
         chrome chrome / satin chrome parts (gloss stage in the shader)
         skip   glass (the radio dial glass: baked opaque it would hide the dial)
         bg     everything else, one 4096 atlas, ONE joined source pass (--onepass bg: the lesson of slice 1)
One heavy job at a time: GPU Cycles, -t 4."""
import os, sys

SRC = os.path.join(r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d", "attic_bake3.py")
code = open(SRC, encoding="utf-8").read()
a = code.index("def group_of(o):")
b = code.index("\nG = {}")
HUB_GROUP_OF = '''def group_of(o):
    n = o.name
    if n in ("gb_face", "nb_srface", "nb_plaque_face"):
        return "quad"            # lettered boards: the source image itself + a separate lightmap (QUAD_POST below), never an atlas
    if o.get("grp"):
        return o["grp"]
    m = mats_of(o)
    if n == "floor":
        return "floor"
    if any(x in ("haze", "frosted", "glass") for x in m):
        return "skip"
    if any(x in ("chrome", "satin_chrome") for x in m):
        return "chrome"
    return "bg"

'''
code = code[:a] + HUB_GROUP_OF + code[b:]
PLAN_OLD = 'PLAN = {"skip": None, "nook": (2048, 32), "floor": None, "chalk": (1024, 32), "radio": (4096, 32), "projector": (2048, 32), "fan": (1024, 32), "chrome": (2048, 24), "bg": (BGSIZE, BGSPP), "wallmap": (4096, 32)}'
assert code.count(PLAN_OLD) == 1, "attic_bake3 PLAN changed: update hub_bake.py"
code = code.replace(PLAN_OLD, 'PLAN = {"skip": None, "floor": None, "quad": None, "chrome": (1024, 24), "bg": (BGSIZE, BGSPP)}')
assert '"--nook" in argv' in code      # the attic's radio-room splice stays off (no --nook)
if "--groups" not in sys.argv:
    sys.argv += ["--groups", "floor,chrome,bg"]
# [2026-11-02] the lettered boards (game-type board, SERVICE RECORD face + plaque) are NOT atlas-baked: a selected-to-active pass
# of the 2-triangle game-type board came out with black holes (ray misses) and the atlas softened the lettering.  Like the floor,
# each keeps its source image at its own UVs and gets a separate 256 px DIFFUSE lightmap (direct + indirect) -> q_<name>.npz,
# q_<name>_lm.png, quads.json (image path, lm scale).  hub_build_models.py turns them into image x lightmap shaders.
QUAD_POST = """
quads = {}
for o in G.get("quad", []):
    me = o.data
    srcimg = [n.image for n in o.material_slots[0].material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image][0]
    if "atlas" not in me.uv_layers:
        me.uv_layers.active = me.uv_layers[0]
        me.uv_layers.new(name="atlas", do_init=True)
    me.uv_layers.active = me.uv_layers["atlas"]
    me.uv_layers["atlas"].active_render = True
    mat = o.material_slots[0].material
    img = bpy.data.images.new("lm_" + o.name, 256, 256, float_buffer=True)
    nd = mat.node_tree.nodes.new("ShaderNodeTexImage")
    nd.image = img
    mat.node_tree.nodes.active = nd
    cy.samples = 96
    cy.use_denoising = True
    bk.use_selected_to_active = False
    select([o])
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=4, use_clear=True)
    a = np.empty(256 * 256 * 4, np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(256, 256, 4)[:, :, :3]
    sc = 0.92 / max(1e-6, float(np.percentile(a, 99.7)))
    a = np.clip(a * sc, 0, 1)
    enc = np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(np.maximum(a, 1e-8), 1 / 2.4) - 0.055)
    im = bpy.data.images.new("o_lm_" + o.name, 256, 256, float_buffer=False)
    im.pixels.foreach_set(np.concatenate([enc, np.ones((256, 256, 1), np.float32)], 2).ravel())
    im.filepath_raw = os.path.join(OUT, "q_%s_lm.png" % o.name)
    im.file_format = 'PNG'
    im.save()
    nd.image = None
    tris_of(o, os.path.join(OUT, "q_%s.npz" % o.name))
    quads[o.name] = {"image": bpy.path.abspath(srcimg.filepath), "lm_scale": sc}
    log("quad", o.name, quads[o.name])
json.dump(quads, open(os.path.join(OUT, "quads.json"), "w"), indent=1)
"""
exec(compile(code + QUAD_POST, SRC + " (hub groups)", "exec"))
