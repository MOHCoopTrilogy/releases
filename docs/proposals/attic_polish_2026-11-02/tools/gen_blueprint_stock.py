"""gen_blueprint_stock.py <art dir> - the General's blueprints from the GAME'S OWN plan art (v1.10.66; user: "There are blueprints in
the game too" - stock first). Both are cut from Allied Assault's U-boat mission plan pickups (main/Pak2.pk3):

  blueprint_uboat.png  textures/models/items/naxosplans3.tga, the top 512 x 320: "U-Boot Bauart VII C - Einrichtungsplan", the
                       Type VIIC general arrangement (side view, cutaway, deck plan) - the large sheet under his hands
  blueprint_naxos.png  textures/models/items/naxosplans2.tga, the lower-left 330 x 227: the Naxos radar detector drawings - a second
                       sheet half under the first

The stock art is 512 px for a whole pickup atlas, so each cut is enlarged x4 (Lanczos) with a light unsharp mask: the line art stays
clean (no invented detail - an AI upscale of the stock K5 schematics in the HD pack was checked and rejected: its lettering is
gibberish). The paper's own stains and folds are kept; the cut is inset 2 px so no neighbouring atlas tile shows at the edge.
(gen_blueprint_art.py, a procedurally drawn cyanotype, was the first take - superseded by the stock art.)"""
import io, os, sys, zipfile
from PIL import Image, ImageFilter

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
z = zipfile.ZipFile(r"G:\GOG\Medal of Honor - Allied Assault War Chest\main\Pak2.pk3")
for src, box, name in (("textures/models/items/naxosplans3.tga", (2, 2, 510, 318), "blueprint_uboat.png"),
                       ("textures/models/items/naxosplans2.tga", (4, 288, 328, 508), "blueprint_naxos.png")):
    im = Image.open(io.BytesIO(z.read(src))).convert("RGB").crop(box)
    big = im.resize((im.width * 4, im.height * 4), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.0, percent=60, threshold=2))
    big.save(os.path.join(out, name))
    print(name, src, box, "->", big.size)
