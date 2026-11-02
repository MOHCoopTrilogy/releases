"""Reduce the downloaded CC0 wood / metal scans to the one-channel DETAIL masters build_sheets.py reads.

    python -I docs/tools/weapon_hd/prep_cc0_detail.py docs/proposals/weapon_skins_cc0_2026-11-01/downloads

The downloads (CC0, listed in MASTERS below with URL and author) are 2K PBR material sets. They never ship and
no generator reads them directly. This script keeps ONE channel of each (the photo's luma for wood, the height
or roughness map for metal), crops away any structure that is not surface detail (the plate seams of
blue_metal_plate), turns wood so its grain runs along x, and writes a grayscale JPEG (q95) master plus
SOURCES.json to docs/tools/assets/weapon_detail_src/. cc0_detail.py band-passes the masters at build time, so
only their fine structure (pores, fibres, pits, scuffs, scratches) ever reaches a weapon sheet; their colour and
their large-scale tone never do.

Downloads are untrusted data: this only decodes JPEG images with PIL and never executes or extracts anything.
Run with -I; numpy/PIL/scipy live in the user site, which -I drops, so it is appended explicitly below (the
script's own dir and the cwd stay off sys.path).
"""
import json
import os
import site
import sys

sys.path.append(site.getusersitepackages())
import numpy as np                                    # noqa: E402
from PIL import Image                                 # noqa: E402
from scipy import ndimage                             # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "assets", "weapon_detail_src")
PH = "https://polyhaven.com/license"
ACG = "https://docs.ambientcg.com/license/"

# master -> source file, channel, crop (u0, v0, u1, v1 of the source), role, provenance
MASTERS = {
    "wood_walnut_a.jpg": dict(src="walnut_veneer_diff_2k.jpg", role="wood pores / fibre (walnut, straight grain)",
                              url="https://polyhaven.com/a/walnut_veneer", author="Jenelle van Heerden (Poly Haven)",
                              dl="https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/walnut_veneer/walnut_veneer_diff_2k.jpg",
                              licence="CC0 1.0", licence_url=PH, method="photo scan"),
    "wood_walnut_b.jpg": dict(src="american_walnut_veneer_diff_2k.jpg", role="wood pores / fibre (walnut)",
                              url="https://polyhaven.com/a/american_walnut_veneer", author="Jenelle van Heerden (Poly Haven)",
                              dl="https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/american_walnut_veneer/american_walnut_veneer_diff_2k.jpg",
                              licence="CC0 1.0", licence_url=PH, method="photo scan"),
    "wood_walnut_c.jpg": dict(src="Wood026_2K-JPG_Color.jpg", role="wood pores / fibre (walnut-tone hardwood)",
                              url="https://ambientcg.com/a/Wood026", author="Lennart Demes (ambientCG)",
                              dl="https://ambientcg.com/get?file=Wood026_2K-JPG.zip",
                              licence="CC0 1.0", licence_url=ACG, method="photo-based PBR material"),
    "wood_oak.jpg":      dict(src="red_oak_veneer_diff_2k.jpg", role="open-pore oak / beech-like stocks (finishes.json wood_scan: oak)",
                              url="https://polyhaven.com/a/red_oak_veneer", author="Jenelle van Heerden (Poly Haven)",
                              dl="https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/red_oak_veneer/red_oak_veneer_diff_2k.jpg",
                              licence="CC0 1.0", licence_url=PH, method="photo scan"),
    "steel_scratch.jpg": dict(src="blue_metal_plate_rough_2k.jpg", crop=(0.33, 0.07, 0.75, 0.78),
                              role="sparse real scratches and scuffs (contact zones)",
                              url="https://polyhaven.com/a/blue_metal_plate", author="Rob Tuytel (Poly Haven)",
                              dl="https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/blue_metal_plate/blue_metal_plate_rough_2k.jpg",
                              licence="CC0 1.0", licence_url=PH, method="photo scan (roughness map)"),
    "steel_pits.jpg":    dict(src="Metal046B_2K-JPG_Displacement.jpg", role="pitting / worn-bluing mottle",
                              url="https://ambientcg.com/a/Metal046B", author="Lennart Demes (ambientCG)",
                              dl="https://ambientcg.com/get?file=Metal046B_2K-JPG.zip",
                              licence="CC0 1.0", licence_url=ACG, method="ambientCG creationMethod PBRProcedural"),
    "steel_scuff.jpg":   dict(src="Metal027_2K-JPG_Displacement.jpg", role="matte phosphate stipple + fine scuffs (parkerized / painted)",
                              url="https://ambientcg.com/a/Metal027", author="Lennart Demes (ambientCG)",
                              dl="https://ambientcg.com/get?file=Metal027_2K-JPG.zip",
                              licence="CC0 1.0", licence_url=ACG, method="ambientCG creationMethod PBRProcedural"),
    "steel_brushed.jpg": dict(src="Metal009_2K-JPG_Displacement.jpg", role="machining / polish lines along the part (blued)",
                              url="https://ambientcg.com/a/Metal009", author="Lennart Demes (ambientCG)",
                              dl="https://ambientcg.com/get?file=Metal009_2K-JPG.zip",
                              licence="CC0 1.0", licence_url=ACG, method="ambientCG creationMethod PBRProcedural"),
}
REJECTED = {
    "metal_plate_02_diff_2k.jpg / _rough_2k.jpg": "https://polyhaven.com/a/metal_plate_02 (CC0, Rob Tuytel) - a grid of riveted "
                                                  "plates: the seams survive any band-pass, so it would stamp straight lines on guns",
    "red_oak / american_walnut / walnut rough maps": "downloaded for comparison; the diffuse luma carries the same pores more cleanly",
    "blue_metal_plate_diff_2k.jpg": "colour of the painted plate; only its roughness map is used",
}


def grain_angle(a):
    """dominant grain direction (deg, 0 = along x) from the structure tensor of the whole image"""
    gx, gy = ndimage.sobel(a, 1), ndimage.sobel(a, 0)
    jxx, jyy, jxy = (gx * gx).mean(), (gy * gy).mean(), (gx * gy).mean()
    return float(np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2)) % 180.0


def main():
    src_dir = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    rec = {}
    for name, m in MASTERS.items():
        im = Image.open(os.path.join(src_dir, m["src"]))
        im.load()
        if "crop" in m:
            W, H = im.size
            u0, v0, u1, v1 = m["crop"]
            im = im.crop((int(u0 * W), int(v0 * H), int(u1 * W), int(v1 * H)))
        a = np.asarray(im.convert("L"), np.float32)
        info = dict(m, size=list(a.shape[::-1]))
        if name.startswith("wood"):
            ang = grain_angle(ndimage.gaussian_filter(a, 2.0))
            if 45 < ang < 135:                      # grain runs along y: turn it (exact 90, no resample)
                a = np.rot90(a).copy()
                info["rot90"] = True
            info["grain_deg_before"] = round(ang, 1)
            info["grain_deg_after"] = round(grain_angle(ndimage.gaussian_filter(a, 2.0)), 1)
        Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name), quality=95)
        rec[name] = info
        print(name, info["size"], info.get("grain_deg_before", ""), info.get("grain_deg_after", ""))
    rec["_rejected"] = REJECTED
    json.dump(rec, open(os.path.join(OUT, "SOURCES.json"), "w", encoding="utf-8"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
