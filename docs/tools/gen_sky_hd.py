# -*- coding: utf-8 -*-
"""gen_sky_hd.py - seam-safe 2048x2048 HD sky boxes for the gl2 `r_skyHD` hook (env/hzmhd/...).

    python docs/tools/gen_sky_hd.py build [box ...]    generate -> write TGA -> gate the DECODED file -> pak
    python docs/tools/gen_sky_hd.py check [--rederive] re-validate the SHIPPED pak (read-only; exit 1 on any fail)
    python docs/tools/gen_sky_hd.py sheet [box ...]    contact sheets, old vs new, 3440x1440 at the user's FOV
    python docs/tools/gen_sky_hd.py selftest [box]     validator controls: must-pass / must-fail (exit 1 if a
                                                       control does not behave, i.e. a gate is blind or biased)
    python docs/tools/gen_sky_hd.py pins               print the sha256 of every pinned file (maintenance)
    --stage DIR / --pak PATH / --manifest PATH         build/check somewhere other than _hd_sky / the mod folder /
                                                       docs/tools (a staged candidate; the ESRGAN cache stays put)

Design and evidence: scratchpad research_sky.md + vet_sky.md (2026-09-25). In one paragraph:
the engine draws the outer box from <box>_{rt,bk,lf,ft,up,dn} (renderergl2 tr_shader.c ParseSkyParms),
CLAMP_TO_EDGE, through tr_sky.c's st_to_vec/sky_texorder tables - reproduced EXACTLY below. Every
face is processed on a canvas padded with its true neighbours re-projected through those tables, so
the upscaler sees a geometrically continuous sky and never invents a seam. Low and mid frequencies
come from the source by construction (Lanczos base + back-projection), Real-ESRGAN contributes only a
masked, capped high band where the source has structure, seams are repaired harmonically (no interior
extrema, no corner overshoot), stars live on their own layer and are re-rendered in direction space,
and the float result is quantized to 8 bit through a blue-noise threshold map. Output is 24-bit TGA (what was validated is what
ships - no encode step), power of two, all six faces, under NEW names env/hzmhd/<box>_<suf>.tga, so no
pak-order or .dds/.jpg/.tga name contest can ever hide or override it (TRAPS T6: mint a new name).

HARD CONSTRAINT (user): never touch Omaha work. The dday2 / e3l1sky / e3l2sky skies are PERMANENTLY
excluded (user decision 2026-09-25: "leave the Omaha skybox as it is") - they are in EXCLUDE AND in
OMAHA_GUARD, so the tool refuses them even if EXCLUDE is edited. OMAHA_GUARD also refuses to read from,
or write to, any Omaha asset or pak under any circumstances.

SEAM PASS (2026-09-26, docs/proposals/seams_2026-09-25 vet F19-F22): an up/side FEATHER on the star-free source
(C1 bridge of the along-edge-coherent profile; cloud-only, alignment-checked, never side/side) becomes the reference
every gate compares against; new gates seam_local (32-texel windows vs an interior reference where the feather
acts, no worse than the Lanczos-magnified original where no pass may act), grain_jump and the feather bounds; and
a seam-only mode (native resolution, no ESRGAN, stars untouched) for the AA_HD night boxes - see "seam pass".

Every source is an explicit sha256-pinned pak member (never "whatever currently loads": the live
resolver returns hd_skybox's FOREIGN sky for e1l3/e3l1 and the m3l1a DXT1 for dday2). A gate is never
loosened to let a sky through - a sky that fails is dropped and stays on its original.
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.fft import dstn

Image.MAX_IMAGE_PIXELS = None
LSB = 1.0 / 255.0

# ------------------------------------------------------------------------------------------ paths
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"      # read-only
DEV = r"C:\mohaa-coop-dev"
STAGE = os.path.join(DEV, "_hd_sky")                             # git-ignored (root allowlist)
OUT_DIR = os.path.join(STAGE, "out")                             # staged env/hzmhd/*.tga
CACHE_DIR = os.path.join(STAGE, "cache", "esrgan")               # ESRGAN outputs, keyed by input hash
REPORT_DIR = os.path.join(STAGE, "report")
SHEET_DIR = os.path.join(STAGE, "sheets")
PAK_NAME = "zzzzzzzzzz_coop_hd_skies.pk3"                        # built out-of-band, copied by build.ps1
PAK_PATH = os.path.join(DEV, "hzm-mohaa-coop-mod", PAK_NAME)     # (.pk3 is excluded from the mod sweep)
MANIFEST = os.path.join(DEV, "docs", "tools", "sky_hd_manifest.json")
HD_PREFIX = "env/hzmhd/"

# ------------------------------------------------------------------------------------------ ESRGAN pin
ESR_EXE = os.path.join(DEV, "_tools", "realesrgan", "realesrgan-ncnn-vulkan.exe")   # git-ignored _tools
ESR_PINS = {
    ESR_EXE: "07e49f7cbb4ede01ae4dd4c399d3a7e5846e3d2085c3128eff881e55cb7b1a0c",
    os.path.join(DEV, "_tools", "realesrgan", "models", "realesrgan-x4plus.bin"):
        "713ee713b0353afaa27976f0563a64a5043bd70b9bd8936c2e26e25ebcdbcddf",
    os.path.join(DEV, "_tools", "realesrgan", "models", "realesrgan-x4plus.param"):
        "35330ececcea33b6c397a72548e788d5d53becee4734c50b7fada36e89f10a86",
}
# -t is PINNED (the -t 0 auto tile size follows free VRAM, so output was not reproducible); -g pinned.
ESR_ARGS = ["-s", "4", "-n", "realesrgan-x4plus", "-t", "256", "-g", "0"]

# ------------------------------------------------------------------------------------------ constants
OUT_N = 2048            # 3440 px at ~112.7 deg hfov = ~1.12 px/texel at face centre: 4096 buys nothing
FLAT_MAX = 64           # faces at or below this are flat colour cards (dn 8x8): copied verbatim
SUF = ["rt", "bk", "lf", "ft", "up", "dn"]
REPAIR_FACES = ("rt", "bk", "lf", "ft", "up")   # dn is outside the seam system: it sits below the horizon,
                                                # and pulling side bottoms toward it shifts the horizon colour

# The three Omaha-list skies. PERMANENTLY excluded - user decision 2026-09-25: "leave the Omaha skybox as it
# is". Not a default to revisit. (dday2 = m3l1a/m3l1b/m3l2/m3l3, e3l1sky = e3l1 only, e3l2sky = e3l2 only -
# all on the never-touch list.) OMAHA_GUARD below refuses the same names, so deleting a line here changes
# nothing: the exclusion is enforced twice on purpose.
EXCLUDE = ["env/dday2", "env/ep2sky/e3l1sky", "env/ep2sky/e3l2sky"]

# Omaha work this tool must never read from or write to, whatever EXCLUDE says: the m3l1a HD pak and its
# census, the baked sky sheen and its generator, and the ocean/shore asset families.
OMAHA_GUARD = re.compile(
    r"(m3l1a|omaha|ocean|seabed|wetsand|shoreline|(^|[/_\\.-])surf|(^|[/_\\.-])wake|sky_?sheen|skysheen|"
    r"hd_skybox|dday2|e3l1sky|e3l2sky|inteldim)", re.I)
# inteldim = inteldimclouds, the scrolling layer of maptour omaha_beach: Omaha, never touched.
# hd_skybox is refused as a SOURCE too: it paints a different sky (corr -0.86..+0.86 vs retail).


def guard(name, what):
    if OMAHA_GUARD.search(name.replace("\\", "/")):
        raise SystemExit("REFUSED by OMAHA_GUARD (%s): %s - Omaha work is never touched by this tool" % (what, name))


# ------------------------------------------------------------------------------------------ sources
P_RETAIL_AA = "main/Pak2.pk3"
P_RETAIL_BT = "mainta/pak1.pk3"
P_AAHD = "maintt/zzzzz-AA_HD_Project_Pak1.pk3"


def _faces(pak, box, ext, shas, paks=None):
    return {s: ((paks or {}).get(s, pak), "%s_%s.%s" % (box, s, ext), shas[i]) for i, s in enumerate(SUF)}


# Each face: (pak relative to GOG, member, sha256). `src` is what the pipeline upscales, `today` is what
# gl2 draws on the live install today (the "old" side of the contact sheet), `retail` (256-source boxes
# only) is the original the AA HD Project JPG was made from - a second fidelity reference.
BOXES = {
    # mohnight1 / lighthousesky: the retail-256 ESRGAN upscale failed the star gates (bug-2937), so these two are
    # SEAM-ONLY boxes (vet_seams F22, item 5): today's AA_HD 2048 faces at their native resolution, no ESRGAN, no
    # deband - only the up/side feather and the harmonic repair, both computed on the star-free background and
    # added to the untouched faces (stars keep their exact texels). `retail512` is the original they came from,
    # pinned for reference only (not a gate input: a seam pass is judged against the faces it starts from).
    # (`retail512` here, `retail_ref` on the day boxes: the same role, different retail sizes.)
    "env/mohnight1": dict(
        maps="m1l1 m1l2a m1l2b m6l3b co_lobby2 co_lobby3 (no fog)", stars=True, mode="seam",
        retail512=_faces(P_RETAIL_AA, "env/mohnight1", "jpg", [
            "2e242a4c184d88bf2b340016ae131bdb0005a56bd78d4714baf0f3eba0946987",
            "92b7ef96b6979d24801aed286d2bdaf64d4657971def4405f94373ad382edc16",
            "23b427c13f090c3dfd19f5d01bd87ce7f944fb4d1db7681082e0e84781dca758",
            "150056e394a93aab66d74a52475d57b97554a950967663468b4644fbf8cd470e",
            "0d78757ddbcf8f1f8fa39ef6ff0c00b135962f087d378cbc20367ebb56bd0e55",
            "b86e43373bb9c99626ba69ded9ed0b74a2cf6855480fa27f160db37cf5a9976a"]),
        src=_faces(P_AAHD, "env/mohnight1", "jpg", [
            "799bdd8f0e759d59ee6e2d15ed79cd1ac23a79734cfd9367f9fe2f8b8c7c6d4b",
            "d4e34a28d4078b0207d6fc72330b0e5df5dd8d1359b8a30ff5800094412c5f43",
            "97819b9c1b12c6c7c679300c268b6d35612d1fc9839b2a2fb26c6a3913b939a3",
            "328707aca915027dc6ca6b1adab18ed0d4ca29c7ae80e380fcce7fce685805ab",
            "e5d2f89cdd2eff11061a3ea7a0dbdd3d8618606a0fd043b5bb54e4a35961f9f1",
            "30bc6830abb5ba9fcaaabddbcbad380b48c9867e0ddfd8a305ffe8cfe4ce1a61"])),
    "env/lighthousesky": dict(
        maps="m1l3c co_lobby4 (no fog)", stars=True, mode="seam",
        retail512=_faces(P_RETAIL_AA, "env/lighthousesky", "jpg", [
            "b2a55fcbab7d1711e3b0ab012bed399fd23f564fc2bef5652de2e20aa906ce8c",
            "68f9e7b8b9cfc88bc21f7297be99670aac59ade9d9f7a76d28a91ebbcac5d607",
            "6520ffc2004d78d2610c50b62d83976d2b039ac74b2617410b0dfdfd3f58440d",
            "8c733889b553e3dc684f391525483d3dadccc399f960c7e1aeb15556034e699c",
            "36cf3c558d22203c63763779bfa37a37cfb88c70e8e8eeb3a0d57b1c1e8be7e2",
            "b7935e4a31ba300044115a75d47e6d1eec0e0c76d2859ebece431ae06c612c20"]),
        src=_faces(P_AAHD, "env/lighthousesky", "jpg", [
            "335baacb624ea3a3526eb00302c7f6f4e033e4cf0f245e0d0161c5a6a91bbc96",
            "c6f57054b060bae8d92cf5e71a8f435e9a68ff97c8c87191d3dae6012dc471ad",
            "e544b39c70d4be127dd0dc44bdf25296c6de4a8810c3cc317ac9102d14c175ef",
            "f66f4c299a6306989dca14901d8db9cc28c09b50539e8ead40e4a44bdc9a5870",
            "822361bf4eb0662f444e72ba930055a3a8812d24c865cb2fd729d3a148461fc7",
            "7f79637fd84de9cf81ad65d1f2473da7c94500aa799652f36d6bfe93b73051ad"])),
    # mohday1 / mohday2 / nordawn: the ESRGAN upscale failed its gates (bug-2937) -> SEAM-ONLY boxes too (user,
    # 2026-09-26), at the AA_HD faces' native 1024. Same gate set as the night boxes: `retail_ref` (256) is the
    # original, pinned for reference only - retail_block counts the seam repair at the face borders against
    # retail's own seams (8-13 of 11-21 over-limit blocks per face sit on the border; skyhd2 report).
    # Player-stack census (skyhd2 sky_census.json): no Omaha map draws them.
    "env/nordawn": dict(
        maps="m2l1 co_lobby6 (far fog 14500)", stars=False, mode="seam",
        src=_faces(P_AAHD, "env/nordawn", "jpg", [
            "e1d7c0d0ed04ec4f897235d9ebea3cf5cc77d95c8b9970589161c53c7f5a4a88",
            "ad5ee0ab1f42f6a6d697754b89f030a4ba5680ea4928dca9d201e924a0154be3",
            "9227b43561d46ea35f4b68eb5d3bd80093349563f21d6b4caa9270b5b80a3113",
            "435c6962a3cc53ee9b6f55bf25140705e97b85628f6f88c203e41b584c847fc4",
            "0d5f2f33a4c3a7c8375b2f2f9e3b703bd58f9acaee46207b68a3b03e563a9258",
            "f314d97c6b74d140037dbd7b8c821ef4b0b6490b0b4960388abc18ff99439577"]),
        retail_ref=_faces(P_RETAIL_AA, "env/nordawn", "jpg", [
            "d6a828141e5fb5325ab7bd4f0231a26ebb4e1c27f80da0f0cee7ca6fc51071b5",
            "009ee6767e1d1d9afd0adea94dd6d6984bf0419248dde7322ce2c16d9624fa97",
            "283a971809c283061c7a262d68c07ab5373f8c89f84d74aa63da705baabe54d7",
            "15fa3a5b1780e4dcf9de606e78750ca819ae541c3ae725698fe6b672c18af744",
            "cf06262f5313b38eb6f29b62e3fe6c7f57ec073bb5ac96f50acc5103019ecfdf",
            "b0b7bdc49bc51350011a47fc128b4f9b04856e384456684a4b7c26f032aac680"])),
    "env/mohday1": dict(
        maps="m4l0 (far fog 13000)", stars=False, mode="seam",
        src=_faces(P_AAHD, "env/mohday1", "jpg", [
            "65e0f62963792cb9bf0745033360686f5e3b5af9f10aa2e71c493bc1cdd53529",
            "92e744f37f14485672328b093583be7554e59db93e469d4250d3ad3f1a58b568",
            "2b006023ba654b94c4be826713676ec9c34418a97f5da926f645840a8f656b99",
            "5ae1b5ed0edcdfc897436a66e6a2e30aebb67ae15af0fe8962aae0bb7f3831bb",
            "5b541711cd1ac70390d48b930cd95478962ce0b9b931140f3b332652d35f3b3b",
            "c3affb4222e5431f2fc07465804479a18a0343e787571d6ac91abfb04f8ccfb6"], {"dn": P_RETAIL_AA}),
        retail_ref=_faces(P_RETAIL_AA, "env/mohday1", "jpg", [
            "2a612c2b4bb155889dfd0ddfb042cc1811a79204df5d0487b7bf20b158773e90",
            "afe7e8110c85233aa853e59b9dc712e1740019974940d25c48e43d4995097b80",
            "7bffe77a4df0a43d57064a766310f11bbddb4ee9990030339fc422842995da07",
            "9247aef379bdb9bdd066d80dd9521c642704b0a55a74a0e29d2a12dcda955b2b",
            "6b0f914927c1c24c8934ad4774bf172ccac3582ce2f7632f7c92f3b3c23f071e",
            "c3affb4222e5431f2fc07465804479a18a0343e787571d6ac91abfb04f8ccfb6"])),
    "env/mohday2": dict(
        maps="m5l3 training co_lobby1 (far fog 15000)", stars=False, mode="seam",
        src=_faces(P_AAHD, "env/mohday2", "jpg", [
            "c538869b43b0edb055adb27c0ee44f0a642d057075843021bd81ebf804b8c595",
            "f6d226694dc97d969762af9050c3d5b835bb9c24cb68a43cb9c898a7ac2a563b",
            "d87ab18aca09c985bc883735dd0f0f212fb065459986675499604c6bf02bf1a2",
            "c1a45938e16309d6a7856d295858ef5869ecd3968cfd22a926d43196dfc1cb3a",
            "15eae31adcc5d06a4585955a5c43e3db3a9983fecc651cdc08f8eb99c06ee29e",
            "c3affb4222e5431f2fc07465804479a18a0343e787571d6ac91abfb04f8ccfb6"], {"dn": P_RETAIL_AA}),
        retail_ref=_faces(P_RETAIL_AA, "env/mohday2", "jpg", [
            "e47c7a191d953773b26e782d337f84861196c5c6ad82a731f5027246c938a8db",
            "b9d5ffe08ef88ae1f19b4ca818c9237fee154f1eba20c984f23949496bef2608",
            "f648ce12729e738cc9d1327c70753c81e94f8244a5350692f02a2d642a3d59fd",
            "c8bdbf21003a56bc0a2e207f822722b93643ac73184d481d9b39f2079b85e0be",
            "38e3b24605060d74e15f199e0efd83f73d1056efeafdc29d70303ef171cacb89",
            "c3affb4222e5431f2fc07465804479a18a0343e787571d6ac91abfb04f8ccfb6"])),
    "env/m5l2": dict(
        maps="t3l1 t3l2 (3D skybox, never fogged); m5l1a/b m5l2a/b (fog)", stars=False,
        src=_faces(P_AAHD, "env/m5l2", "jpg", [
            "85516d9564737febbb526e7496c6cd4ba590ab23e212d5f3ce297d59c00818e1",
            "ad9f453d6c12a6f5fda550d2fe3cca9ea726949457e0741af586f12d6f33be02",
            "a8de9984970834e38d4677b9d8f603cfb9bf92816d235bdf0a19c9f65116bf40",
            "329fec3f6bd7fc745e6ed36cd726a218edf6a97f4f77f42a686aac58e711c386",
            "e8038c2226590dd359d27543c52fd307e8452ba779d7ff2121ddbdd4a647a6e8",
            "aa72f06a1932e03f0321a3c777b2df99b1e2bec8fa7c98745ecc4aa949ab54b9"], {"dn": P_RETAIL_AA}),
        retail=_faces(P_RETAIL_AA, "env/m5l2", "jpg", [
            "d9cd08033e10f0ec3aa68159b476acad195ac192212925b960368ceca6412907",
            "405f47f1c180e553d771393cdcd8383c29e078db22e31f815158bb6d5b26eaaa",
            "629efa8ceae7285a64b86934ffa22837d719f1b9d3b7f2669de5d81107b4e1f9",
            "4a59d5346d7dc208d380ca4d23b849dc1b2fc6db4f47a9ace39a83d6f6070c55",
            "961eb5752e41755241832451c15c2487b24ca9469dcb314cf6e05ecda7cec648",
            "aa72f06a1932e03f0321a3c777b2df99b1e2bec8fa7c98745ecc4aa949ab54b9"])),
    "env/t3l1": dict(
        maps="t3l1 (3D skybox)", stars=False,
        src=_faces(P_RETAIL_BT, "env/t3l1", "tga", [
            "b88e970c8f6aecd87ba77fc8f6e656622095cc6457eee4107625a25137dd5fd7",
            "bb5403cafb52f749b9d2808f1906ca865f157ca118144392646f573431e63a77",
            "65e483d678bfb9f7fb71c9dc4c952f442e1e258fc45f4d98d6320c0135cb3a66",
            "95f44ad672ecdc1fe3eba42cc397a34b277e212febc815488453bc27dab3640c",
            "e6d90eb018227e7ecf2447b7c20258bf9004ddca98043b64eb1c07fed1a2284c",
            "6789ad2f6159a737df523d641f1f9ac09536aa319d0c09f126c9887cbfc819be"])),
    "env/t3l2": dict(
        maps="t3l2 (3D skybox, painted skyline)", stars=False,
        src=_faces(P_RETAIL_BT, "env/t3l2", "tga", [
            "7d841c1d06315fd1f34373d94d3c3f0de0aa5aad5d5934799c089612773bda3b",
            "5ed9fe7257c166a776a7745516d5dd7837c478d83759c672d229cff2bb303c9c",
            "e1a7920ed9877dfff55ff9086bc7bf3a7d2ee4583c43879bd720f40587db01fb",
            "ccc18d435e519777e27b4e1859cd33e7ec928459133a92d4783c9cf4ac5a4b67",
            "5c4782852fbfa19672d05c20bef7d40e9062b26edfeda6c4211b21bae631f91d",
            "f964335f842437b0e8d3ad2946f41584f32051776e70cae07afb71ce122c7ea7"])),
    "env/t1l1": dict(
        maps="t1l1 (3D skybox)", stars=False,
        src=_faces(P_RETAIL_BT, "env/t1l1", "tga", [
            "f9b22ca8cba782ac4c3417eb908fcc6e77729b657c000b810900fb63ab61632d",
            "7b572d5bfad98f47dbe514aac334b99db6c27be2fcb34f948691edd091cda879",
            "0357b69cc09d64728d097e5cb6679122c874005795822f1e6300ae7179503b0c",
            "3f477b78e0a148795c309c24c9bda8208a2b0a254af9d51481c84e97ea3150c3",
            "19cf2a80646f9024fd743c78772af064236e7c070bd55d617ba2773a725d33e9",
            "dc2e8701159f47f7154c79bfb6f5ba5de98e80d3aac70f8e129b3249748d57e1"])),
    "env/t1l1a": dict(
        maps="t1l1 (second box)", stars=False,
        src=_faces(P_RETAIL_BT, "env/t1l1a", "tga", [
            "bacbf8605e566d18ffce32857defb9b0572b268eb5aef4bb53eed4173cd10523",
            "59c3af90aa9522511693a212a34d8f2c20f5ce4c1b10f8d662c9a0710b97d337",
            "e99657b0c2a6d6d5515c6d11b0df7f71ed9d9d7180e1ea32c1ba7051ef71c225",
            "5fdfd1133458808d055984ffa3c56a9b22c2c53670de07501a868878bf3a5748",
            "df40a567a9b4e20a21455db28d4fc4120dee91d11f7bf4aac323727ba16924d2",
            "2c45e1955b644a4dfa6e1c8506837b4940d8c023069cb5aeda203afc0c1b718d"])),
}
for _b in BOXES.values():
    _b.setdefault("today", _b["src"])

# ------------------------------------------------------------------------------------------ gates
# Thresholds are in DISPLAY LSB: every absolute threshold is divided by the face's display gain g
# (r_autoExposure lifts a dark sky by up to 2 stops, so a 2-LSB texture error on a night sky is ~8 display
# LSB). Values are the research thresholds (research_sky.md 3.3) or STRICTER. Never loosen one to pass a sky.
GATES = dict(
    seam_cross_allow=0.75,      # edge cross step may exceed the source's (identically smoothed) by this
    seam_ratio_max=3.0,         # ... and cross/in-face step may not exceed max(this, source's own ratio)
    seam_drift_allow=1.0,       # windowed mean difference along the edge
    mean_shift_max=0.75,        # global per-channel mean shift after BOX-down
    block_shift_max=1.5,        # worst 1/32-face block, NON-harmonic residual (research: 2.0; tightened so a
                                #   synthetic 2-LSB blotch fails - see selftest)
    repair_err_max=0.75,        # boundary displacement vs the displacement a perfect seam repair needs
    mottle_ratio_max=1.6,       # band-pass RMS in smooth regions vs the Lanczos-of-source reference
    bands_floor=5.0,            # banding edges per Mtexel may not exceed max(reference, floor)
    corner_allow=1.5,           # corner band-pass excursion beyond 2x reference (star-free)
    star_keep_min=0.9, star_flux_tol=0.15, star_flux_ok_min=0.9, star_halo_max=1.0, star_halo_bad_max=0.1,
    horizon_max=0.75,           # mean colour of the horizon band and the bottom 5% rows of side faces
    disc_exc_max=2.0,           # excursion beyond the local source range around bright discs (sun/glow)
    detail_keep_min=0.8,        # fine-band energy kept where the source has structure (deband damage)
    retail_shift_allow=0.5, retail_block_allow=1.0,   # 256-source boxes: no further from retail than AA_HD
    # ---- seam pass 2026-09-26 (vet_seams F19-F22). NEW gates, not relaxations of the ones above.
    # seam_local (item 1): every 32-texel window of every cube edge (dn excluded - outside the seam system, item 3
    # skipped). The step is the intercept difference of two 8-texel line fits, one each side, extrapolated to the
    # edge (a smooth gradient across the edge scores 0), worst channel. Two domains, decided by the pinned source:
    #  REPAIR domain - windows where the feather acts (mean feather mask >= repair_domain_min): the seam must be
    #    gone - step <= local_ratio x the same measurement across interior lines parallel to the edge at that
    #    window (the texture's own local step there) + local_allow;
    #  ART domain - everywhere no pass may act (side/side edges - never feathered; content the feather refuses:
    #    the t1l1 treeline, the t3l2 skyline, the t3l1 horizon; the corner tapers): no worse than the ORIGINAL
    #    magnified the way the pipeline magnifies it (Lanczos - a bilinear reference would bill the upscale's
    #    legitimate sharpness of a painted cut as a new seam) + art_allow. art_allow is seam_drift_allow (1.0 on
    #    128-texel windows) carried to 32-texel windows at the same noise level (x sqrt(128/32)); at 0.5 the gate
    #    failed 0.24-vs-0.22 LSB windows - dither-level differences nobody can see.
    local_ratio=2.0, local_allow=1.0, repair_domain_min=0.5, art_allow=2.0,
    # grain_jump (item 4): fine-band RMS in the 32-texel strip each side of an edge, each face on its own texel
    # grid; |ln(A/B)| <= max(grain_jump_max, the source's own jump + grain_jump_allow).
    grain_jump_max=0.3, grain_jump_allow=0.1,
    # feather (item 2): the correction the up/side feather applies to the source (texture LSB, and display LSB).
    feather_max=4.0, feather_display_max=16.0,
)
# The up/side feather (item 2). Geometry in RETAIL texels (q = face size / 512 converts): band depth D, rows
# [D0, D) carry each face's trend, SIG_C = along-edge coherence scale. Mask thresholds in display LSB.
# ALIGN_E: the shift test only runs where the outer rows carry structure >= 3 display LSB (retail-texel band); below
# that the two faces' art is texture at ~0.2-0.3 zero-shift correlation and a "best shift" is noise (at 1.0 it
# refused 3-12% of the t-series up edges, all low-contrast cloud, leaving a stub of t1l1's dark edge line).
FEATHER = dict(D=8, D0=3, SIG_C=3.0, FIT_MAX=1.0, GRAD_MAX=3.0, ALIGN_E=3.0, ALIGN_GAIN=0.5, ALIGN_WIN=24, ALIGN_SHIFT=3)


# ============================================================================== cube geometry (tr_sky.c)
# suf[6] = {rt,bk,lf,ft,up,dn}; sky_texorder = {0,2,1,3,4,5}; st_to_vec as below; MakeSkyVec b=(s,t,1),
# xyz[j] = sign(k)*b[|k|-1]; u=(s+1)/2, v=1-(t+1)/2; texcoords span [0,1] with CLAMP_TO_EDGE.
ST_TO_VEC = [(3, -1, 2), (-3, 1, 2), (1, 3, 2), (-1, -3, 2), (-2, -1, 3), (2, -1, -3)]
SKY_TEXORDER = [0, 2, 1, 3, 4, 5]
FACE_AXIS = {SUF[SKY_TEXORDER[a]]: a for a in range(6)}


def face_dir(face, u, v):
    k = ST_TO_VEC[FACE_AXIS[face]]
    s = 2.0 * np.asarray(u, np.float64) - 1.0
    t = 1.0 - 2.0 * np.asarray(v, np.float64)
    b = [s, t, np.ones_like(s)]
    return np.stack([b[abs(q) - 1] * (1.0 if q > 0 else -1.0) for q in k], -1)


def dir_face(d):
    ax = np.abs(d)
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    axis = np.where((ax[..., 0] >= ax[..., 1]) & (ax[..., 0] >= ax[..., 2]), np.where(x >= 0, 0, 1),
                    np.where(ax[..., 1] >= ax[..., 2], np.where(y >= 0, 2, 3), np.where(z >= 0, 4, 5)))
    u = np.zeros(d.shape[:-1])
    v = np.zeros(d.shape[:-1])
    for a in range(6):
        m = axis == a
        if not m.any():
            continue
        dd = d[m]
        k = ST_TO_VEC[a]
        b = [None, None, None]
        for j in range(3):
            b[abs(k[j]) - 1] = dd[:, j] * (1.0 if k[j] > 0 else -1.0)
        u[m] = (b[0] / b[2] + 1) * 0.5
        v[m] = 1.0 - (b[1] / b[2] + 1) * 0.5
    return np.array(SKY_TEXORDER)[axis], u, v


def sample_bilinear(img, u, v):
    """GL_LINEAR + GL_CLAMP_TO_EDGE."""
    H, W = img.shape[:2]
    x = np.clip(u * W - 0.5, 0, W - 1)
    y = np.clip(v * H - 0.5, 0, H - 1)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    x1 = np.minimum(x0 + 1, W - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy) +
            img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)


def sample_cube(faces, d):
    fi, u, v = dir_face(d)
    out = np.zeros(d.shape[:-1] + (3,), np.float64)
    for i, s in enumerate(SUF):
        m = fi == i
        if m.any():
            out[m] = sample_bilinear(faces[s], u[m], v[m])
    return out


def padded_face(faces, face, N, pad, partners=None):
    """The face plane extended by `pad` texels, filled by re-projecting the TRUE neighbours (gnomonic
    continuation). Across an edge to a face outside `partners` (a flat card, or dn, which sit outside the
    seam system) the canvas continues the face itself by clamping - exactly what CLAMP_TO_EDGE draws -
    so a flat dn colour never bleeds into the bottom rows of a side face."""
    idx = (np.arange(-pad, N + pad) + 0.5) / N
    uu, vv = np.meshgrid(idx, idx)
    d = face_dir(face, uu, vv)
    out = sample_cube(faces, d)
    if partners is not None:
        fi, _, _ = dir_face(d)
        own = np.array([SUF[i] in partners or SUF[i] == face for i in range(6)])[fi]
        if not own.all():
            out[~own] = sample_bilinear(faces[face], np.clip(uu[~own], 0, 1), np.clip(vv[~own], 0, 1))
    return out


def hfov_for(cg_fov=80.0, W=3440, H=1440):
    """cgame CG_CalcFov Hor+: fov_x = 2*atan(tan(fov/2) * (W/H * 3/4))."""
    return float(np.degrees(2 * np.arctan(np.tan(np.radians(cg_fov / 2)) * (W / H * 0.75))))


def perspective(faces, yaw_deg, pitch_deg, W=3440, H=1440, hfov_deg=None):
    """Q3 view angles: pitch positive = look DOWN, yaw positive = turn left."""
    hfov_deg = hfov_deg or hfov_for(80.0, W, H)
    yaw, pit = np.radians(yaw_deg), np.radians(pitch_deg)
    fwd = np.array([np.cos(pit) * np.cos(yaw), np.cos(pit) * np.sin(yaw), -np.sin(pit)])
    left = np.array([-np.sin(yaw), np.cos(yaw), 0.0])
    up = np.cross(fwd, left)
    tx = np.tan(np.radians(hfov_deg) / 2)
    ty = tx * H / W
    xs = ((np.arange(W) + 0.5) / W * 2 - 1) * tx
    ys = (1 - (np.arange(H) + 0.5) / H * 2) * ty
    X, Y = np.meshgrid(xs, ys)
    d = fwd[None, None, :] - X[..., None] * left[None, None, :] + Y[..., None] * up[None, None, :]
    return sample_cube(faces, d)


def perimeter(N):
    top = [(0, x) for x in range(N)]
    right = [(y, N - 1) for y in range(1, N)]
    bottom = [(N - 1, x) for x in range(N - 2, -1, -1)]
    left = [(y, 0) for y in range(N - 2, 0, -1)]
    return np.array(top + right + bottom + left)


def partner_mean(faces, F, pts, allowed):
    """Mean of each boundary texel and its cross-edge partner(s) found BY DIRECTION (3-face mean at
    corners). Partners outside `allowed` (flat cards, dn) do not vote."""
    N = faces[F].shape[0]
    y, x = pts[:, 0], pts[:, 1]
    u, v = (x + 0.5) / N, (y + 0.5) / N
    eps = 0.75 / N
    acc = faces[F][y, x].astype(np.float64).copy()
    cnt = np.ones(len(pts))
    for du, dv, m in ((-eps, 0, x == 0), (eps, 0, x == N - 1), (0, -eps, y == 0), (0, eps, y == N - 1)):
        idx = np.nonzero(m)[0]
        if not len(idx):
            continue
        fi, uu, vv = dir_face(face_dir(F, u[idx] + du, v[idx] + dv))
        for j, s in enumerate(SUF):
            mm = fi == j
            if not mm.any() or s not in allowed:
                continue
            sel = idx[mm]
            acc[sel] += sample_bilinear(faces[s], uu[mm], vv[mm])
            cnt[sel] += 1
    return acc / cnt[:, None]


def dirichlet(ring):
    """Harmonic fill of an (M,M,C) array whose outer ring holds the boundary values (exact DST-I)."""
    M = ring.shape[0]
    n = M - 2
    k = np.arange(1, n + 1)
    c = np.cos(np.pi * k / (n + 1))
    lam = (4 - 2 * c)[:, None] - 2 * c[None, :]
    out = ring.astype(np.float64).copy()
    for ch in range(ring.shape[2]):
        g = ring[..., ch]
        b = np.zeros((n, n))
        b[0, :] += g[0, 1:-1]
        b[-1, :] += g[-1, 1:-1]
        b[:, 0] += g[1:-1, 0]
        b[:, -1] += g[1:-1, -1]
        out[1:-1, 1:-1, ch] = dstn(dstn(b, type=1, norm="ortho") / lam, type=1, norm="ortho")
    return out


def repair_allowed(faces):
    return {s for s in REPAIR_FACES if faces[s].shape[0] > FLAT_MAX}


def boundary_need(faces, F, allowed, sigma_frac=1 / 128.0):
    """What a perfect seam repair must move each boundary texel of F by (smoothed along the perimeter)."""
    N = faces[F].shape[0]
    pts = perimeter(N)
    if F not in allowed:
        return pts, np.zeros((len(pts), 3))
    g = partner_mean(faces, F, pts, allowed) - faces[F][pts[:, 0], pts[:, 1]]
    if sigma_frac == 0:
        return pts, g
    return pts, ndimage.gaussian_filter1d(g, max(1.0, N * sigma_frac), axis=0, mode="wrap")


def _trend_faces(faces, rows=(1, 7)):
    """Each face with its outermost row on every side replaced by its own trend there (a line through rows 1..6,
    extrapolated to row 0): what the edge would be if the border row carried no anomaly."""
    out = {}
    for F in SUF:
        a = np.array(faces[F], np.float64, copy=True)
        if a.shape[0] > FLAT_MAX:
            d = np.arange(*rows, dtype=np.float64)
            for sd in "LRTB":
                st = _strip(faces[F], sd, rows[1]).astype(np.float64)
                y = st[:, rows[0]:rows[1]]
                b = ((y - y.mean(1, keepdims=True)) * (d - d.mean())[None, :, None]).sum(1) / ((d - d.mean()) ** 2).sum()
                c = np.zeros((st.shape[0], 1, 3))
                c[:, 0] = (y.mean(1) - b * d.mean()) - st[:, 0]
                _add_strip(a, sd, c)
        out[F] = a
    return out


def agreed_need(faces, F, allowed, trend=None):
    """Seam-only boxes (native resolution): the texel-exact need, scaled by how much of it the two faces' own
    TRENDS confirm (alpha in [0, 1], per channel, at the gate's N/128 smoothing). The move therefore never exceeds
    the raw meeting (repair_err: once-smoothed move within [0, once-smoothed need]) and never follows a one-row
    anomaly the trends do not share: meeting at the raw texels there bent both faces' trends into a new local step
    (nordawn / mohday1 / mohnight1 rt|ft, the art domain of seam_local)."""
    N = faces[F].shape[0]
    pts, raw = boundary_need(faces, F, allowed, 0)
    if F not in allowed:
        return pts, raw
    trend = trend if trend is not None else _trend_faces(faces)
    _, rob = boundary_need(trend, F, allowed, 0)
    sg = max(1.0, N / 128.0)
    ns = ndimage.gaussian_filter1d(raw, sg, axis=0, mode="wrap")
    rs_ = ndimage.gaussian_filter1d(rob, sg, axis=0, mode="wrap")
    alpha = np.where(np.abs(ns) < 0.02 * LSB, 1.0, np.clip(rs_ / np.where(np.abs(ns) < 1e-12, 1e-12, ns), 0.0, 1.0))
    # alpha varies along the edge, so the SMOOTHED move is not alpha x the smoothed need: where the need flips sign
    # within ~sg texels and alpha differs on the two sides, one lobe survives the smoothing and overshoots (nordawn
    # rt|bk by the dn corner: 1.8 LSB). Check the move exactly as repair_err does and shrink alpha around every
    # overshoot until none is left (alpha -> 0 is always inside, so this terminates).
    lo, hi = np.minimum(ns, 0), np.maximum(ns, 0)
    tol = 0.05 * LSB
    for _ in range(40):
        sm = ndimage.gaussian_filter1d(raw * alpha, sg, axis=0, mode="wrap")
        over = (sm > hi + tol) | (sm < lo - tol)
        if not over.any():
            break
        near = ndimage.gaussian_filter1d(over.astype(np.float64), sg, axis=0, mode="wrap") > 0.02
        alpha = np.where(near, alpha * 0.7, alpha)
    return pts, raw * alpha


def harmonic_repair(faces, sigma_frac=1 / 128.0, agreed=False):
    """sigma_frac 0 = texel-exact need (seam-only boxes, native resolution): the validator smooths the output's
    boundary move once and compares it with the once-smoothed need - a need smoothed here too is smoothed twice
    and spills past the partner wherever it varies along the edge (repair_err 0.4-0.6 on the night boxes).
    agreed=True: the texel-exact need scaled by the trends' agreement (agreed_need)."""
    allowed = repair_allowed(faces)
    out, corr = dict(faces), {}
    trend = _trend_faces(faces) if agreed else None
    for F in allowed:
        N = faces[F].shape[0]
        pts, g = agreed_need(faces, F, allowed, trend) if agreed else boundary_need(faces, F, allowed, sigma_frac)
        ring = np.zeros((N, N, 3))
        ring[pts[:, 0], pts[:, 1]] = g
        corr[F] = dirichlet(ring)
        out[F] = faces[F] + corr[F]
    return out, corr


# ============================================================================== seam pass (2026-09-26)
# Research: docs/proposals/seams_2026-09-25/report_seams.md s3 + vet_seams.md F19-F22. Order: item 4 (grain) ->
# item 2 (feather) -> item 1 (local gate) -> item 5 (seam-only boxes). Findings that shaped it (scratchpad skyhd):
#  * item 4: measured on each face's OWN texel grid the shipped boxes have NO up-face grain drop (up/side strips
#    0.95-1.05 x); the research's "grain jump" came from resampling the far side off texel centres (bilinear
#    shaves grain). A TPDF dither would equalise noise modulation but raises all grain to ~0.46 and fails the
#    corner/disc gates - rejected. Item 4 is therefore a GATE (grain_jump) that locks the equality in.
#  * the retail t1l1 (and others) SHARE the outermost texel row between a side face and up, and that shared row
#    often sits below both interiors: a thin dark line along the up edge. Both rows are equal, so the harmonic
#    need there is ~0 and repair_err pins it - no existing stage could touch it. The feather therefore acts on
#    the SOURCE (star-free background, source resolution), and every gate compares against the feathered source;
#    the feather itself is gated (band-confined, bounded) and recomputed from the pinned source by the validator.
def _strip(face, side, depth):
    """(N, depth, C) view of a face's outer rows: [t, d], d = 0 the outermost row. T/B: t = column, L/R: t = row."""
    if side == "T":
        return face[:depth, :].transpose(1, 0, 2)
    if side == "B":
        return face[::-1][:depth, :].transpose(1, 0, 2)
    if side == "L":
        return face[:, :depth]
    return face[:, ::-1][:, :depth]


def _add_strip(face, side, c):
    depth = c.shape[1]
    if side == "T":
        face[:depth, :] += c.transpose(1, 0, 2)
    elif side == "B":
        face[::-1][:depth, :] += c.transpose(1, 0, 2)
    elif side == "L":
        face[:, :depth] += c
    else:
        face[:, ::-1][:, :depth] += c


def _neighbour(F, side):
    c = (np.arange(8) + 0.5) / 8
    uo, vo = {"L": (np.full(8, -0.01), c), "R": (np.full(8, 1.01), c), "T": (c, np.full(8, -0.01)),
              "B": (c, np.full(8, 1.01))}[side]
    fi, _, _ = dir_face(face_dir(F, uo, vo))
    return SUF[int(np.bincount(fi).argmax())]


def _side_towards(B, A):
    return [sd for sd in "LRTB" if _neighbour(B, sd) == A][0]


def edge_tmap(A, sideA, B, sideB, N):
    """Along-edge index of B's strip for every along-edge index of A's strip (a permutation: same or reversed)."""
    c = (np.arange(N) + 0.5) / N
    u, v = {"T": (c, np.zeros(N)), "B": (c, np.ones(N)), "L": (np.zeros(N), c), "R": (np.ones(N), c)}[sideA]
    d = face_dir(A, u, v)
    k = ST_TO_VEC[FACE_AXIS[B]]
    b = [None] * 3
    for j in range(3):
        b[abs(k[j]) - 1] = d[:, j] * (1.0 if k[j] > 0 else -1.0)
    ub, vb = (b[0] / b[2] + 1) * 0.5, 1 - (b[1] / b[2] + 1) * 0.5
    tb = np.round((ub if sideB in "TB" else vb) * N - 0.5).astype(int)
    assert sorted(tb.tolist()) == list(range(N)), (A, sideA, B, sideB)
    return tb


def up_side_edges():
    return [(A, _side_towards(A, "up"), "up", _side_towards("up", A)) for A in ("rt", "bk", "lf", "ft")]


def _linfit(L, d0, depth):
    d = np.arange(d0, depth, dtype=np.float64)
    y = L[:, d0:depth]
    dm = d.mean()
    b = ((y - y.mean(1, keepdims=True)) * (d - dm)[None, :, None]).sum(1) / ((d - dm) ** 2).sum()
    return y.mean(1) - b * dm, b


def _hermite(p0, m0, p1, m1, s):
    return ((2 * s ** 3 - 3 * s ** 2 + 1) * p0 + (s ** 3 - 2 * s ** 2 + s) * m0 +
            (-2 * s ** 3 + 3 * s ** 2) * p1 + (s ** 3 - s ** 2) * m1)


def feather_edge(fa, fb, gain, q, prm=FEATHER):
    """One up/side edge. fa/fb: (N, D, 3) outer rows of the side face and of up, both in A's along-edge order.
    Only the along-edge-COHERENT profile L (smoothed along the edge, SIG_C) is touched: each face's trend is a line
    fitted to L over rows [D0, D); across [-D, D] L is replaced by one C1 Hermite curve - A's trend (value+slope)
    -> the two trends' mean at the edge (slope = mean slope) -> B's trend - full weight to D/2, smoothstep out by D.
    Finer structure (clouds, grain) stays each face's own: nothing is cross-blended, so nothing can ghost.
    Mask (per along-edge texel, smoothed, tapered to 0 over D at the corners so no side/side edge moves):
      cloud-only - L is a line beyond the outer rows (fit residual <= FIT_MAX) and no sharp structure crosses the
                   edge (along-edge gradient <= GRAD_MAX per retail texel);
      aligned    - no along-edge shift (<= ALIGN_SHIFT retail texels) matches the two sides' outer-row structure
                   (retail-texel band) clearly better than zero shift (t3l2 skyline / t1l1 treeline class)."""
    N = fa.shape[0]
    D, d0, sig = int(prm["D"] * q), int(prm["D0"] * q), prm["SIG_C"] * q
    LA = ndimage.gaussian_filter1d(fa, sig, axis=0, mode="nearest")
    LB = ndimage.gaussian_filter1d(fb, sig, axis=0, mode="nearest")
    aA, bA = _linfit(LA, d0, D)
    aB, bB = _linfit(LB, d0, D)
    dd = np.arange(d0, D)
    resA = LA[:, d0:D] - (aA[:, None] + bA[:, None] * dd[None, :, None])
    resB = LB[:, d0:D] - (aB[:, None] + bB[:, None] * dd[None, :, None])
    fit = np.maximum(np.sqrt((resA ** 2).mean((1, 2))), np.sqrt((resB ** 2).mean((1, 2)))) / LSB * gain
    grad = np.maximum(np.abs(np.gradient(LA, axis=0)).max((1, 2)), np.abs(np.gradient(LB, axis=0)).max((1, 2))) * q / LSB * gain

    def bp(x):
        return ndimage.gaussian_filter1d(x, 1.0 * q, axis=0) - ndimage.gaussian_filter1d(x, 4.0 * q, axis=0)
    pa = luma(bp(fa[:, 1:d0 + 1]).mean(1)) / LSB * gain
    pb = luma(bp(fb[:, 1:d0 + 1]).mean(1)) / LSB * gain
    mis = np.zeros(N, bool)
    W, R = int(prm["ALIGN_WIN"] * q), int(prm["ALIGN_SHIFT"] * q)
    for i in range(0, N, W // 2):
        sl = slice(max(0, i - W // 2), min(N, i + W // 2))
        a_, b_ = pa[sl], pb[sl]
        if np.sqrt(0.5 * ((a_ ** 2).mean() + (b_ ** 2).mean())) < prm["ALIGN_E"]:
            continue
        ssd = {}
        for sh in range(-R, R + 1):
            x, y = (a_[sh:], b_[:len(b_) - sh]) if sh >= 0 else (a_[:sh], b_[-sh:])
            ssd[sh] = float(((x - y) ** 2).mean())
        best = min(ssd, key=ssd.get)
        if best != 0 and ssd[0] > (1 + prm["ALIGN_GAIN"]) * ssd[best] + 0.25:
            mis[sl] = True
    ok = (fit <= prm["FIT_MAX"]) & (grad <= prm["GRAD_MAX"]) & ~mis
    m = np.where(ok, ndimage.gaussian_filter1d(ok.astype(np.float64), 2.0 * q), 0.0)
    tp = np.clip(np.minimum(np.arange(N) + 0.5, N - 0.5 - np.arange(N)) / D - 0.5, 0, 1)
    m = m * tp * tp * (3 - 2 * tp)
    X = float(D)
    mr = 0.5 * ((aA - 0.5 * bA) + (aB - 0.5 * bB))          # both trends extrapolated to the edge (row -0.5)
    s0 = 0.5 * (-bA + bB)
    d = np.arange(D) + 0.5
    PA = _hermite((aA + bA * (X - 0.5))[:, None], (-bA * X)[:, None], mr[:, None], (s0 * X)[:, None], (1 - d / X)[None, :, None])
    PB = _hermite(mr[:, None], (s0 * X)[:, None], (aB + bB * (X - 0.5))[:, None], (bB * X)[:, None], (d / X)[None, :, None])
    tt = np.clip((d - X / 2) / (X / 2), 0, 1)
    w = (1 - tt * tt * (3 - 2 * tt))[None, :, None]
    # The feather repairs modest seams only: an along-edge texel whose correction would exceed the feather gate
    # (GATES feather_max, texture and display LSB) is refused and left to the harmonic repair, and the mask is
    # re-smoothed until none does. Refusing only lowers the smoothed mask elsewhere, so this terminates; a box
    # that never reaches the bound (all five 2026-09-26 boxes) is unchanged byte for byte.
    lim = min(GATES["feather_max"], GATES["feather_display_max"] / gain) * LSB
    capped = 0
    while True:
        cA = m[:, None, None] * w * (PA - LA)
        cB = m[:, None, None] * w * (PB - LB)
        over = np.maximum(np.abs(cA).max((1, 2)), np.abs(cB).max((1, 2))) > lim
        if not over.any():
            break
        capped += int(over.sum())
        ok &= ~over
        m = np.where(ok, ndimage.gaussian_filter1d(ok.astype(np.float64), 2.0 * q), 0.0) * tp * tp * (3 - 2 * tp)
    diag = dict(capped=capped, cover=round(float(m.mean()), 3), fit_refused=round(float((fit > prm["FIT_MAX"]).mean()), 3),
                grad_refused=round(float((grad > prm["GRAD_MAX"]).mean()), 3), misaligned=round(float(mis.mean()), 3))
    return cA, cB, diag, m


def box_gains(src_full):
    """Display gain per repair face, from the FULL pinned source - the one definition the feather uses in both the
    pipeline and the validator (the feather mask depends on it, so both sides must agree exactly)."""
    return {s: display_gain(src_full[s]) for s in SUF if src_full[s].shape[0] > FLAT_MAX}


def seam_feather(faces, gains, prm=FEATHER):
    """Item 2 on star-free SOURCE faces at their own resolution. Returns (feathered faces, F, per-edge diag,
    per-edge mask in A's along-edge order at the source resolution). Only up/side edges; faces outside the seam
    system (flat cards, dn) are never touched."""
    allowed = repair_allowed(faces)
    F = {s: np.zeros(faces[s].shape, np.float64) for s in SUF}
    diag, masks = {}, {}
    if "up" in allowed:
        N = faces["up"].shape[0]
        q = N / 512.0
        D = int(prm["D"] * q)
        for A, sA, B, sB in up_side_edges():
            if A not in allowed or faces[A].shape[0] != N:
                continue
            tb = edge_tmap(A, sA, B, sB, N)
            fa = _strip(faces[A], sA, D).astype(np.float64)
            fb = _strip(faces[B], sB, D).astype(np.float64)[tb]
            cA, cB, dg, m = feather_edge(fa, fb, max(gains.get(A, 1.0), gains.get(B, 1.0)), q, prm)
            _add_strip(F[A], sA, cA)
            _add_strip(F[B], sB, cB[np.argsort(tb)])
            dg["max_lsb"] = round(float(max(np.abs(cA).max(), np.abs(cB).max()) / LSB), 3)
            diag["%s.%s|%s" % (A, sA, B)] = dg
            masks["%s.%s|%s" % (A, sA, B)] = m
    return {s: faces[s] + F[s] for s in SUF}, F, diag, masks


def feather_band(faces, prm=FEATHER):
    """Boolean mask per face of the texels the feather may touch (the up/side bands)."""
    out = {s: np.zeros(faces[s].shape[:2], bool) for s in SUF}
    if "up" not in repair_allowed(faces):
        return out
    N = faces["up"].shape[0]
    D = int(prm["D"] * N / 512.0)
    for A, sA, B, sB in up_side_edges():
        for F_, sd in ((A, sA), (B, sB)):
            m = np.zeros(out[F_].shape + (1,))
            _add_strip(m, sd, np.ones((N, D, 1)))
            out[F_] |= m[..., 0] > 0
    return out


# ---- item 1: local seam statistics, per 32-texel window along every edge, at the output scale
LOCAL_W, LOCAL_STRIDE, LOCAL_K, LOCAL_REF_OFFS = 32, 16, 8, (40, 80)


def _uv_line(side, N, x):
    c = (np.arange(N) + 0.5) / N
    if side == "L":
        return np.full(N, -x / N), c
    if side == "R":
        return np.full(N, 1 + x / N), c
    if side == "T":
        return c, np.full(N, -x / N)
    return c, np.full(N, 1 + x / N)


def _fit_step(a, b, K):
    """a, b: (N, K, C) samples at x = -(j+.5) and +(j+.5). Signed intercept difference at x = 0, and the bend."""
    xs = np.arange(K) + 0.5
    xm = xs.mean()
    den = ((xs - xm) ** 2).sum()
    sa = ((a - a.mean(1, keepdims=True)) * (-(xs - xm))[None, :, None]).sum(1) / den
    sb = ((b - b.mean(1, keepdims=True)) * (xs - xm)[None, :, None]).sum(1) / den
    return (a.mean(1) + sa * xm) - (b.mean(1) - sb * xm), (sa - sb) * K


def _windows(v):
    N = v.shape[0]
    return np.stack([v[i:i + LOCAL_W].mean(0) for i in range(0, N - LOCAL_W + 1, LOCAL_STRIDE)])


def _local_edges(faces, flat):
    N = max(faces[s].shape[0] for s in SUF if s not in flat)
    out, done = [], set()
    for A in SUF:
        if A in flat or A == "dn":
            continue
        for side in "LRTB":
            B = _neighbour(A, side)
            key = tuple(sorted((A, B)))
            if key in done or B in flat or B == "dn":
                continue
            done.add(key)
            out.append((A, side, B, _side_towards(B, A)))
    return N, out


def local_seam_stats(faces, flat, N_eval, K=LOCAL_K):
    """Per edge: per-window |step| (worst channel), interior reference and bend, texture LSB, at the output scale
    N_eval. A smaller face is sampled bilinearly - what GL magnifies it to - so source and output are measured
    the same way. The reference is the same measurement across interior lines parallel to the edge, 40 and 80
    texels inside each face, at the same window."""
    _, edges = _local_edges(faces, flat)
    N = N_eval
    res = {}
    for A, sA, B, sB in edges:
        a = np.stack([sample_bilinear(faces[A], *_uv_line(sA, N, -(j + 0.5))) for j in range(K)], 1) / LSB
        b = np.stack([sample_cube(faces, face_dir(A, *_uv_line(sA, N, j + 0.5))) for j in range(K)], 1) / LSB
        st, kk = _fit_step(a, b, K)
        tb = edge_tmap(A, sA, B, sB, N)
        refs = []
        for F_, sF, reidx in ((A, sA, None), (B, sB, tb)):
            for off in LOCAL_REF_OFFS:
                ra = np.stack([sample_bilinear(faces[F_], *_uv_line(sF, N, -(j + 0.5) - off)) for j in range(K)], 1) / LSB
                rb = np.stack([sample_bilinear(faces[F_], *_uv_line(sF, N, (j + 0.5) - off)) for j in range(K)], 1) / LSB
                r, _ = _fit_step(ra, rb, K)
                refs.append(np.abs(_windows(r if reidx is None else r[reidx])).max(1))
        res["%s.%s|%s" % (A, sA, B)] = dict(A=A, B=B, step=np.abs(_windows(st)).max(1),
                                            kink=np.abs(_windows(kk)).max(1), ref=np.max(refs, 0))
    return res


def repair_domain(fmask, n_src, N_eval):
    """Per up/side edge: the mean feather mask over each local window (windows in output texels, mask at the
    source resolution in the same along-edge order)."""
    out = {}
    for name, m in fmask.items():
        mo = np.repeat(m, N_eval // n_src) if N_eval != n_src else m
        out[name] = np.array([mo[i:i + LOCAL_W].mean() for i in range(0, N_eval - LOCAL_W + 1, LOCAL_STRIDE)])
    return out


def grain_own(face, side, depth=32, sigma=1.0):
    """Fine-band RMS (LSB) of a face's own texels in the strip along one side - no resampling (the research's
    cross-edge resampling shaved the far side's grain and read as a grain jump that is not there)."""
    L = luma(face) / LSB
    f = L - ndimage.gaussian_filter(L, sigma, mode="nearest")
    f = {"L": f[:, 1:depth], "R": f[:, -depth:-1], "T": f[1:depth, :], "B": f[-depth:-1, :]}[side]
    return float(np.sqrt((f ** 2).mean()))


def grain_jumps(faces, flat):
    """Per edge (dn excluded): (grain A, grain B, |ln A/B|), strips 1/64 of the face deep (32 texels at 2048)."""
    out = {}
    _, edges = _local_edges(faces, flat)
    for A, sA, B, sB in edges:
        ga = grain_own(faces[A], sA, max(4, faces[A].shape[0] // 64))
        gb = grain_own(faces[B], sB, max(4, faces[B].shape[0] // 64))
        out["%s.%s|%s" % (A, sA, B)] = (ga, gb, float(abs(np.log(max(ga, 0.05) / max(gb, 0.05)))))
    return out


# ============================================================================== small helpers
def luma(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def rs(a, n, filt=Image.Resampling.LANCZOS):
    """Float resize (PIL 'F' per channel - no 8-bit rounding)."""
    if a.ndim == 2:
        return np.asarray(Image.fromarray(a.astype(np.float32)).resize((n, n), filt)).astype(np.float32)
    return np.stack([rs(a[..., c], n, filt) for c in range(a.shape[2])], -1)


def box_down(a, n):
    N = a.shape[0]
    if N == n:
        return a.astype(np.float64)
    f = N // n
    assert f * n == N, (N, n)
    return a.reshape(n, f, n, f, -1).mean((1, 3))


def local_std(a, k=5):
    L = luma(a).astype(np.float64)
    return np.sqrt(np.maximum(ndimage.uniform_filter(L * L, k) - ndimage.uniform_filter(L, k) ** 2, 0))


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def to8(a):
    return np.clip(np.round(np.asarray(a, np.float64) * 255), 0, 255).astype(np.uint8)


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def display_gain(src_face):
    """Display amplification of a dark face under r_autoExposure (<= 2 stops, tr_init.c:1518-1519)."""
    return float(np.clip((64.0 / 255.0) / max(float(luma(src_face).mean()), 1e-4), 1.0, 4.0))


# ============================================================================== IO: pinned paks, TGA
_zips = {}


def read_member(pak, member, want_sha=None):
    guard(pak, "source pak")
    guard(member, "source member")
    path = os.path.join(GOG, pak.replace("/", os.sep))
    if path not in _zips:
        _zips[path] = zipfile.ZipFile(path)
    z = _zips[path]
    names = {n.lower(): n for n in z.namelist()}
    b = z.read(names[member.lower()])
    if want_sha and sha256(b) != want_sha:
        raise SystemExit("SOURCE PIN MISMATCH: %s!%s is %s, pinned %s - refusing (a source changed; re-vet it "
                         "and update BOXES)" % (pak, member, sha256(b), want_sha))
    return b


def decode_image(b):
    if b[:2] != b"\xff\xd8" and len(b) > 18 and b[2] in (2, 10):
        return read_tga(b).astype(np.float64) / 255.0
    im = Image.open(io.BytesIO(b))
    im.load()
    return np.asarray(im.convert("RGB")).astype(np.float64) / 255.0


def load_set(spec):
    return {s: decode_image(read_member(*spec[s])) for s in SUF}


def write_tga(a8):
    """Uncompressed type-2, 24-bit, bottom-left origin - byte-for-byte the layout of the retail skies."""
    H, W = a8.shape[:2]
    hdr = bytes([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, W & 255, W >> 8, H & 255, H >> 8, 24, 0])
    return hdr + np.ascontiguousarray(a8[::-1, :, ::-1]).tobytes()


def read_tga(b):
    """renderercommon/tr_image_tga.c semantics: type 2 (uncompressed) 24/32 bit; attributes bit 5 = top-left.
    Returns top-down RGB uint8 (row 0 = v 0)."""
    idlen, cmtype, itype = b[0], b[1], b[2]
    W, H = b[12] | (b[13] << 8), b[14] | (b[15] << 8)
    bpp, attr = b[16], b[17]
    if cmtype != 0 or itype != 2 or bpp not in (24, 32):
        raise ValueError("unsupported TGA (type %d cmap %d bpp %d)" % (itype, cmtype, bpp))
    nb = bpp // 8
    data = np.frombuffer(b[18 + idlen:18 + idlen + W * H * nb], np.uint8).reshape(H, W, nb)
    rgb = data[:, :, [2, 1, 0]]
    return rgb if (attr & 0x20) else rgb[::-1]


def hd_member(box, suf):
    rel = box[4:] if box.startswith("env/") else box
    return HD_PREFIX + rel + "_" + suf + ".tga"


# ============================================================================== ESRGAN (pinned + cached)
_esr_checked = False


def esr_verify():
    global _esr_checked
    if _esr_checked:
        return
    for p, want in ESR_PINS.items():
        if not os.path.exists(p):
            raise SystemExit("ESRGAN missing: %s" % p)
        got = sha256(open(p, "rb").read())
        if got != want:
            raise SystemExit("ESRGAN PIN MISMATCH: %s is %s, pinned %s" % (p, got, want))
    _esr_checked = True


def esr_key(a8):
    h = hashlib.sha256()
    h.update(json.dumps([sorted(ESR_PINS.values()), ESR_ARGS, list(a8.shape)]).encode())
    h.update(np.ascontiguousarray(a8).tobytes())
    return h.hexdigest()


def esrgan(a8, allow_run=True):
    """4x Real-ESRGAN of a uint8 RGB array. Cached by (pins, args, pixels); the cache index records each
    output's sha256 so `check --rederive` can prove the cached file is the one the pak was built from."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = esr_key(a8)
    op = os.path.join(CACHE_DIR, key + ".png")
    if not os.path.exists(op):
        if not allow_run:
            raise SystemExit("ESRGAN cache miss (%s) and running is not allowed here" % key[:16])
        esr_verify()
        with tempfile.TemporaryDirectory(dir=STAGE) as td:
            ip = os.path.join(td, "in.png")
            tp = os.path.join(td, "out.png")
            Image.fromarray(a8).save(ip)
            t = time.time()
            r = subprocess.run([ESR_EXE, "-i", ip, "-o", tp] + ESR_ARGS + ["-m", os.path.join(os.path.dirname(ESR_EXE), "models")],
                               capture_output=True, timeout=3600)
            if not os.path.exists(tp):
                raise SystemExit("ESRGAN failed: %s" % r.stderr[-600:])
            shutil.move(tp, op)
            print("      esrgan %dx%d -> %.1fs" % (a8.shape[1], a8.shape[0], time.time() - t), flush=True)
    b = open(op, "rb").read()
    idx_p = os.path.join(CACHE_DIR, "index.json")
    idx = json.load(open(idx_p)) if os.path.exists(idx_p) else {}
    if idx.get(key) not in (None, sha256(b)):
        raise SystemExit("ESRGAN cache entry %s changed on disk" % key[:16])
    if key not in idx:
        idx[key] = sha256(b)
        json.dump(idx, open(idx_p, "w"), indent=0, sort_keys=True)
    arr = np.asarray(Image.open(io.BytesIO(b)).convert("RGB"))
    assert arr.shape[0] == a8.shape[0] * 4, (arr.shape, a8.shape)
    return arr.astype(np.float32) / 255.0, key, sha256(b)


# ============================================================================== stars
STAR_THR = 10 / 255.0


def star_extract(faces):
    """Point sources pulled OUT before any filtering (ESRGAN erases/brightens them, the detail layer rings
    around them, a seam repair meeting one at a corner paints a wedge). Returns (star-free faces, stars).
    A star on an edge is found on both faces: deduplicated ACROSS faces only (two close stars on one
    face are two stars - the pilot merged them and lost the fainter one)."""
    bg_faces, stars = {}, []
    for F in SUF:
        a = faces[F]
        N = a.shape[0]
        if N <= FLAT_MAX:
            bg_faces[F] = a
            continue
        bg = np.stack([ndimage.median_filter(a[..., c], 5, mode="nearest") for c in range(3)], -1)
        r = a - bg
        Lr = luma(r)
        pk = (Lr > STAR_THR) & (Lr == ndimage.maximum_filter(Lr, 3))
        mask = ndimage.binary_dilation(pk, iterations=2)
        out = a.copy()
        out[mask] = bg[mask]
        bg_faces[F] = out
        for y, x in np.argwhere(pk):
            y0, y1, x0, x1 = max(0, y - 2), min(N, y + 3), max(0, x - 2), min(N, x + 3)
            w = np.clip(r[y0:y1, x0:x1], 0, None)
            lw = luma(w)
            tot = lw.sum()
            if tot <= 0:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1]
            cy, cx = (yy * lw).sum() / tot, (xx * lw).sum() / tot
            d = face_dir(F, np.array([(cx + 0.5) / N]), np.array([(cy + 0.5) / N]))[0]
            # flux = the UNCLIPPED aperture sum: clipping at 0 counted the JPEG ringing's positive lobes and
            # re-rendered every star ~10% too bright (measured median +6..+16% on mohnight1/lighthouse)
            flux = np.clip(r[y0:y1, x0:x1].sum((0, 1)), 0, None)
            stars.append((d / np.linalg.norm(d), flux, N, F))
    keep = []
    for st in sorted(stars, key=lambda z: -float(luma(z[1][None, :])[0])):
        tol = 1.5 * 2.0 / st[2]
        if all(k[3] == st[3] or np.linalg.norm(st[0] - k[0]) > tol for k in keep):
            keep.append(st)
    return bg_faces, keep


def star_on_face(F, N, d):
    """Pixel position of direction d on face F's plane (may be outside [0,N)); None if behind."""
    k = ST_TO_VEC[FACE_AXIS[F]]
    b = [None] * 3
    for j in range(3):
        b[abs(k[j]) - 1] = d[j] * (1.0 if k[j] > 0 else -1.0)
    if b[2] <= 1e-6:
        return None
    uu, vv = (b[0] / b[2] + 1) * 0.5, 1 - (b[1] / b[2] + 1) * 0.5
    return uu * N - 0.5, vv * N - 0.5


def star_render(faces, stars, sigma_src=0.35):
    """Splat every star as a normalised Gaussian (sigma in SOURCE texels) onto every face whose plane it
    projects into, 3-sigma margin past the edge - a star on an edge is split seamlessly."""
    out = {F: a.copy() for F, a in faces.items()}
    for F, a in out.items():
        N = a.shape[0]
        if N <= FLAT_MAX:
            continue
        for d, flux, Nsrc, _ in stars:
            p = star_on_face(F, N, d)
            if p is None:
                continue
            px, py = p
            scale = N / float(Nsrc)
            sig = max(0.5, sigma_src * scale)
            R = int(np.ceil(3 * sig))
            if px < -R or px > N - 1 + R or py < -R or py > N - 1 + R:
                continue
            x0, x1 = int(max(0, np.floor(px - R))), int(min(N - 1, np.ceil(px + R)))
            y0, y1 = int(max(0, np.floor(py - R))), int(min(N - 1, np.ceil(py + R)))
            if x1 < x0 or y1 < y0:
                continue
            yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            g = np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / (2 * sig * sig)) / (2 * np.pi * sig * sig)
            a[y0:y1 + 1, x0:x1 + 1] += g[..., None] * flux[None, None, :] * scale * scale
    return out


def star_mask(F, N, stars, radius_px, pad=0):
    m = np.zeros((N + 2 * pad, N + 2 * pad), bool)
    for d, _, _, _ in stars:
        p = star_on_face(F, N, d)
        if p is None:
            continue
        px, py = p[0] + pad, p[1] + pad
        if px < -radius_px or py < -radius_px or px > N + 2 * pad + radius_px or py > N + 2 * pad + radius_px:
            continue
        x0, x1 = int(max(0, np.floor(px - radius_px))), int(min(N + 2 * pad - 1, np.ceil(px + radius_px)))
        y0, y1 = int(max(0, np.floor(py - radius_px))), int(min(N + 2 * pad - 1, np.ceil(py + radius_px)))
        if x1 < x0 or y1 < y0:
            continue
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        m[y0:y1 + 1, x0:x1 + 1] |= (xx - px) ** 2 + (yy - py) ** 2 <= radius_px ** 2
    return m


def disc_mask(a, min_area=6, thr=16 / 255.0):
    """Bright discs (sun, moon, glow cores): compact regions well above the local median. Stars (<= 4
    texels) are not discs - they have their own layer."""
    L = luma(a)
    cand = (L - ndimage.median_filter(L, 15, mode="nearest")) > thr
    lab, n = ndimage.label(cand)
    if n == 0:
        return np.zeros(L.shape, bool)
    area = ndimage.sum(np.ones_like(L), lab, index=np.arange(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = area >= min_area
    return keep[lab]


# ============================================================================== the pipeline
def deband(a, thr, radius=4):
    """Range-limited disc mean: averages each texel with the disc neighbours within thr in EVERY channel.
    Removes 8-bit plateaus / JPEG block steps in smooth sky; edges and stars (contrast > thr) untouched.
    (A luma-only range test - the pilot's - mixes texels of equal luma but different chroma and moved blue
    by 1.5 LSB on t3l2; the per-channel test cannot.)"""
    acc = np.zeros_like(a)
    wsum = np.zeros(a.shape[:2])
    H, W = a.shape[:2]
    # ODD reflection (2*edge - mirror) continues a linear gradient exactly, so the disc mean at the border is
    # unbiased. Edge replication biased border texels ~0.5-1 LSB (t3l2); debanding the neighbour-padded canvas
    # instead mixed texels ACROSS authored seams (moved red 1.1 LSB on mohday1 where no repair was needed).
    P = np.pad(a, ((radius, radius), (radius, radius), (0, 0)), mode="reflect", reflect_type="odd")
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius:
                continue
            n = P[radius + dy:radius + dy + H, radius + dx:radius + dx + W]
            w = (np.abs(n - a).max(-1) <= thr).astype(np.float64)
            acc += n * w[..., None]
            wsum += w
    return acc / wsum[..., None]


_BLUE = None
BLUE_N = 128


def blue_noise(n=BLUE_N, sigma=1.5, seed=20260925):
    """Void-and-cluster (Ulichney 1993) threshold map, n x n, values (rank+0.5)/n^2 in (0,1). Tiles
    seamlessly (all energy sums wrap). Deterministic; cached in STAGE."""
    global _BLUE
    if _BLUE is not None:
        return _BLUE
    cp = os.path.join(STAGE, "cache", "bluenoise_%d_%g_%d.npy" % (n, sigma, seed))
    if os.path.exists(cp):
        _BLUE = np.load(cp)
        return _BLUE
    yy, xx = np.mgrid[0:n, 0:n]
    dy, dx = np.minimum(yy, n - yy), np.minimum(xx, n - xx)
    K = np.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma))

    def energy(pat):
        return np.real(np.fft.ifft2(np.fft.fft2(pat) * np.fft.fft2(K)))

    def shifted(p):
        return np.roll(np.roll(K, p[0], 0), p[1], 1)

    rng = np.random.default_rng(seed)
    pat = np.zeros((n, n))
    pat.flat[rng.choice(n * n, n * n // 10, replace=False)] = 1
    E = energy(pat)
    while True:                                          # initial binary pattern: no clusters, no voids
        c = np.unravel_index(np.argmax(np.where(pat == 1, E, -np.inf)), pat.shape)
        pat[c] = 0
        E -= shifted(c)
        v = np.unravel_index(np.argmin(np.where(pat == 0, E, np.inf)), pat.shape)
        if v == c:
            pat[c] = 1
            E += shifted(c)
            break
        pat[v] = 1
        E += shifted(v)
    rank = np.zeros((n, n), np.int64)
    ones = int(pat.sum())
    p1, E1 = pat.copy(), E.copy()
    for r in range(ones - 1, -1, -1):                    # phase 1: strip the tightest clusters
        c = np.unravel_index(np.argmax(np.where(p1 == 1, E1, -np.inf)), p1.shape)
        p1[c] = 0
        E1 -= shifted(c)
        rank[c] = r
    p2, E2 = pat.copy(), E.copy()
    for r in range(ones, n * n):                         # phases 2+3: fill the largest voids
        v = np.unravel_index(np.argmin(np.where(p2 == 0, E2, np.inf)), p2.shape)
        p2[v] = 1
        E2 += shifted(v)
        rank[v] = r
    _BLUE = (rank + 0.5) / float(n * n)
    os.makedirs(os.path.dirname(cp), exist_ok=True)
    np.save(cp, _BLUE)
    return _BLUE


def bluenoise_dither8(a, seed):
    """Ordered dither with a blue-noise threshold map: local means are exact and the quantization error sits
    at the highest spatial frequencies. White TPDF (the pilot's) put +-1 LSB of broadband grain on every
    texel - +-4 display LSB on a night sky under r_autoExposure's 2 stops, which failed the corner, disc
    and mottle gates on t1l1/t1l1a/t3l1 from grain alone. Same map for all three channels (no chroma
    grain), offset per face by a seeded shift."""
    T = blue_noise()
    n = T.shape[0]
    H, W = a.shape[:2]
    oy, ox = seed % n, (seed // n) % n
    Tt = np.tile(np.roll(np.roll(T, oy, 0), ox, 1), (H // n + 1, W // n + 1))[:H, :W]
    return np.clip(np.floor(a * 255 + Tt[..., None]), 0, 255).astype(np.uint8)


def face_seed(box, suf):
    return int(sha256(("gen_sky_hd:" + box + ":" + suf).encode())[:8], 16)


# ---- seam-only boxes (item 5), second pass 2026-09-26: what actually broke mohnight1 / lighthousesky
# The "30+ LSB corner mismatches" were two different things (scratchpad skyhd2\analysis):
#  * STARS. At AA_HD 2048 a star is a 4-8 texel upscaled blob; star_extract (retail scale: 5x5 median, 3x3 peak,
#    2-texel grow) leaves it in the "star-free" background. Stars that the AA HD per-face upscale CUT at an edge
#    or DUPLICATED at an offset across it then read as 36-107 LSB seams, and the harmonic repair / feather
#    smeared them. star_extract_hd below is the AA_HD-scale layer; the stars still keep their exact texels.
#  * The original renderer's HOT CORNER TEXEL: bk's two top corners are +100..+231 LSB in retail (one texel),
#    grown into a 6-27 texel wedge by the AA HD upscale (+ blobs attached to the rt / ft corners). Present in
#    retail, so re-deriving the corner from retail cannot remove it: corner_rebuild solves it out harmonically.
CORNER = dict(R=40, PAD=24, HOT=16.0, GLOW=4.0, ATTACH=3, MED=15)      # R, PAD at 2048: see corner_geom


def corner_geom(N, prm=CORNER):
    """R and PAD for a face of N texels (the table is for 2048; a 1024 face gets the same ANGULAR disc)."""
    return max(16, int(round(prm["R"] * N / 2048.0))), max(12, int(round(prm["PAD"] * N / 2048.0)))
# MAX_AREA_BRIGHT / PEAK_BRIGHT: measured on both night boxes (skyhd2 blob_areas.py) the blob areas run on to ~160;
# above that the tail is either a bright star with its glow (peak 57-200 LSB over the local median, area 177-323)
# or faint cloud texture (peak 14-30, area up to 483); no moon-sized blob exists. 48 sits in the gap.
STARHD = dict(MED=15, THR_LO=6.0, THR_PEAK=14.0, MAX_AREA=160, MAX_AREA_BRIGHT=480, PEAK_BRIGHT=48.0, GROW=3, PAD=24)


def up_corners():
    """The 4 cube corners where two side faces meet up (dn is outside the seam system)."""
    return [np.array([sx, sy, 1.0]) / np.sqrt(3.0) for sx in (1, -1) for sy in (1, -1)]


def _corner_texel(F, d, N):
    k = ST_TO_VEC[FACE_AXIS[F]]
    b = [None] * 3
    for j in range(3):
        b[abs(k[j]) - 1] = d[j] * (1.0 if k[j] > 0 else -1.0)
    u, v = (b[0] / b[2] + 1) * 0.5, 1 - (b[1] / b[2] + 1) * 0.5
    return int(np.clip(np.floor(v * N), 0, N - 1)), int(np.clip(np.floor(u * N), 0, N - 1))


def _corner_window(faces, F, y, x, W, N):
    """F's own texel grid extended past its edges, rows y-W..y+W, cols x-W..x+W; the neighbours re-projected
    through the cube (padded_face's canvas, locally). Returns (canvas (2W+1, 2W+1, 3), inside-F mask)."""
    yy, xx = np.mgrid[y - W:y + W + 1, x - W:x + W + 1]
    d = face_dir(F, (xx + 0.5) / N, (yy + 0.5) / N)
    inside = (yy >= 0) & (yy < N) & (xx >= 0) & (xx < N)
    return sample_cube(faces, d), inside, yy, xx


def _laplace_fill(canvas, unknown):
    """Harmonic (Laplace) fill of `unknown` texels from their known 4-neighbours (Dirichlet; a missing neighbour
    past the canvas border is left out, i.e. Neumann there). Exact sparse solve, vectorised build."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    out = canvas.copy()
    n = int(unknown.sum())
    if not n:
        return out
    H, W = unknown.shape
    idx = -np.ones((H, W), np.int64)
    idx[unknown] = np.arange(n)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)
    rhs = np.zeros((n, canvas.shape[2]))
    ys, xs = np.nonzero(unknown)
    me = idx[ys, xs]
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        yy, xx = ys + dy, xs + dx
        inb = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
        diag[me[inb]] += 1
        yy, xx, m_ = yy[inb], xx[inb], me[inb]
        unk = unknown[yy, xx]
        rows.append(m_[unk])
        cols.append(idx[yy[unk], xx[unk]])
        vals.append(-np.ones(int(unk.sum())))
        np.add.at(rhs, m_[~unk], canvas[yy[~unk], xx[~unk]])
    rows.append(np.arange(n))
    cols.append(np.arange(n))
    vals.append(diag)
    A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()
    for c in range(canvas.shape[2]):
        out[unknown, c] = spsolve(A, rhs[:, c])
    return out


def corner_rebuild(faces, prm=CORNER):
    """Remove bright blobs ATTACHED to an up-corner texel (the original renderer's hot corner texel and what the
    AA HD upscale grew from it) by a harmonic solve across the three meeting faces: the blob is masked on every
    face first, then each face's masked texels are filled on a local canvas that continues into its two
    neighbours through the cube, every known texel of all three faces serving as boundary. Nothing else moves.
    Returns (faces, changed-mask per face, diag)."""
    allowed = repair_allowed(faces)
    out = {s: np.array(faces[s], np.float64, copy=True) for s in SUF}
    masks = {s: np.zeros(faces[s].shape[:2], bool) for s in SUF}
    diag = {}
    hot = prm["HOT"] * LSB
    todo = []
    for d in up_corners():
        fs = [s for s in allowed if np.dot(face_dir(s, np.array([0.5]), np.array([0.5]))[0], d) > 0.5]
        if len(fs) != 3:
            continue
        for F in fs:
            N = faces[F].shape[0]
            R, pad = corner_geom(N, prm)
            W = R + pad
            y, x = _corner_texel(F, d, N)
            cv, inside, yy, xx = _corner_window(faces, F, y, x, W, N)
            L = luma(cv)
            ex = luma(cv) - ndimage.median_filter(L, prm["MED"], mode="nearest")
            disc = inside & (np.hypot(yy - y, xx - x) <= R)
            lab, n = ndimage.label((ex > hot) & disc)
            if not n:
                continue
            near = np.unique(lab[(np.hypot(yy - y, xx - x) <= prm["ATTACH"]) & (lab > 0)])
            core = np.isin(lab, near[near > 0])
            if not core.any():
                continue
            # hysteresis: the upscale blurred the hot texel into a glow below HOT - take every texel connected
            # to the core that is still > GLOW above the local median
            glab, _ = ndimage.label((ex > prm["GLOW"] * LSB) & disc)
            gid = np.unique(glab[core & (glab > 0)])
            m = core | np.isin(glab, gid[gid > 0])
            m = ndimage.binary_dilation(m, iterations=2) & inside & (np.hypot(yy - y, xx - x) <= R)
            masks[F][yy[m], xx[m]] = True
            todo.append((d, F, y, x))
    if not todo:
        return out, masks, diag
    nan = {s: (np.where(masks[s][..., None], np.nan, faces[s]) if masks[s].any() else faces[s]) for s in SUF}
    for d, F, y, x in todo:
        N = faces[F].shape[0]
        R, pad = corner_geom(N, prm)
        W = R + pad
        cv, inside, yy, xx = _corner_window(nan, F, y, x, W, N)
        unk = np.isnan(cv).any(-1)
        filled = _laplace_fill(np.nan_to_num(cv), unk)
        mine = unk & inside & masks[F][np.clip(yy, 0, N - 1), np.clip(xx, 0, N - 1)]
        out[F][yy[mine], xx[mine]] = filled[mine]
        ring = ndimage.binary_dilation(unk, iterations=1) & ~unk
        key = "%s@%s" % (F, "".join("+" if c > 0 else "-" for c in d))
        diag[key] = dict(texels=int(mine.sum()),
                         removed_max_lsb=round(float((luma(faces[F][yy[mine], xx[mine]]) - luma(filled[mine])).max() / LSB), 1),
                         ring_lo=round(float(luma(cv[ring]).min() / LSB), 2), ring_hi=round(float(luma(cv[ring]).max() / LSB), 2),
                         fill_lo=round(float(luma(filled[mine]).min() / LSB), 2), fill_hi=round(float(luma(filled[mine]).max() / LSB), 2))
    return out, masks, diag


def star_extract_hd(faces, prm=STARHD):
    """AA_HD-scale star layer: compact bright blobs ((luma - 15-texel median) > THR_LO, peak > THR_PEAK, area <=
    MAX_AREA - the moon and cloud rims are bigger), grown by GROW. Found on each face's canvas padded with its
    TRUE neighbours (PAD texels, padded_face): a star the AA HD upscale cut at an edge is seen whole and masked on
    both faces, and the median background next to an edge is not a replica of the edge row. (A per-face median
    left half of every cut star in the "background" and the texel-exact repair pulled the neighbour up to it:
    lighthousesky bright_disc 9-14 LSB.) Returns (background, star mask per face): inside the mask the
    background is the harmonic fill from the unmasked canvas, outside it is the face verbatim."""
    bg, masks = {}, {}
    allowed = repair_allowed(faces)
    P = prm["PAD"]
    for F in SUF:
        a = faces[F]
        N = a.shape[0]
        if N <= FLAT_MAX:
            bg[F], masks[F] = a, np.zeros(a.shape[:2], bool)
            continue
        cv = padded_face(faces, F, N, P, partners=allowed if F in allowed else set())
        B = np.stack([ndimage.median_filter(cv[..., c], prm["MED"], mode="nearest") for c in range(3)], -1)
        r = luma(cv - B)
        lab, n = ndimage.label(r > prm["THR_LO"] * LSB)
        m = np.zeros(r.shape, bool)
        if n:
            ids = np.arange(1, n + 1)
            keep = np.zeros(n + 1, bool)
            area = ndimage.sum(np.ones_like(r), lab, ids)
            peak = ndimage.maximum(r, lab, ids)
            keep[1:] = (peak > prm["THR_PEAK"] * LSB) & ((area <= prm["MAX_AREA"]) |
                                                         ((area <= prm["MAX_AREA_BRIGHT"]) & (peak >= prm["PEAK_BRIGHT"] * LSB)))
            m = ndimage.binary_dilation(keep[lab], iterations=prm["GROW"])
        # the background under a star is the HARMONIC fill of its surroundings on the true-neighbour canvas: smooth,
        # so a star cut at an edge leaves no texel-scale structure for the seam repair to follow (a median fill did:
        # lighthousesky bright_disc 2.7-4.6 at the up|lf edge star)
        fill = _laplace_fill(cv, m)
        m, fill = m[P:P + N, P:P + N], fill[P:P + N, P:P + N]
        bg[F] = np.where(m[..., None], fill, a)
        masks[F] = m
    return bg, masks


def process_seam_box(box, log=print):
    """Item 5 (vet_seams F22): a SEAM-ONLY pass at the faces' native resolution - no ESRGAN, no deband, no
    resampling. The feather (item 2) and the harmonic repair are computed on the star-free background and ADDED
    to the untouched faces, so every star keeps its exact texels (a smooth sub-LSB..few-LSB offset at most), and
    wherever both corrections are 0 the output is the source byte for byte (a blue-noise threshold never lifts an
    integer). Returns (faces_u8, info).
    First pass (2026-09-26 a) FAILED with the retail-scale star_extract: the AA_HD stars stayed in the
    background and the original renderer's hot corner texels were read as seams (see "seam-only boxes" above).
    Second pass: corner_rebuild (the effective source) -> star_extract_hd -> feather -> harmonic repair."""
    cfg = BOXES[box]
    full0 = load_set(cfg["src"])
    big = [s for s in SUF if full0[s].shape[0] > FLAT_MAX]
    sizes = {full0[s].shape[0] for s in big}
    assert len(sizes) == 1, (box, sizes)
    N = sizes.pop()
    assert N & (N - 1) == 0 and N >= 512, (box, N)     # native resolution, power of two (r_roundImagesDown)
    gains = box_gains(full0)
    full, _, cdiag = corner_rebuild(full0)
    # point sources (stars; nordawn's sun glitter) are never seams: every correction is computed on the layer
    # without them and added to the untouched faces
    bg, smask = star_extract_hd(full)
    stars = [1] * int(sum(ndimage.label(smask[s])[1] for s in big))
    log("    corners rebuilt: %s; point sources held out: %d (untouched)" % (sorted(cdiag), len(stars)))
    bgF, F, fdiag, _ = seam_feather(bg, gains)
    rep_, corr = harmonic_repair(bgF, sigma_frac=0, agreed=True)
    out8 = {}
    for s in SUF:
        if s in big:
            c = corr[s] if s in corr else 0
            fin = full[s] + F[s] + c
            if np.isnan(fin).any():
                raise SystemExit("NaN in %s %s" % (box, s))
            q = bluenoise_dither8(fin, face_seed(box, s)).astype(np.int16)
            # bright discs (moon, glow cores - the validator's region): round INWARD into the local 3x3 range of
            # the effective source (moved by the repair), as the upscale path does - a threshold dither may
            # otherwise lift a texel sitting on its local maximum by 1 LSB (bright_disc at gain 3: 0.66). Star
            # texels are left alone (they are not the background the range was taken from).
            reg = ndimage.binary_dilation(disc_mask(bgF[s]), iterations=4)
            if reg.any():
                lo_q = np.ceil((ndimage.minimum_filter(bgF[s], size=(3, 3, 1)) + c) * 255 - 1e-6)
                hi_q = np.floor((ndimage.maximum_filter(bgF[s], size=(3, 3, 1)) + c) * 255 + 1e-6)
                ok = reg[..., None] & (lo_q <= hi_q)
                ok &= ~smask[s][..., None]
                q = np.where(ok, np.clip(q, lo_q, hi_q), q).astype(np.int16)
            out8[s] = np.clip(q, 0, 255).astype(np.uint8)
        else:
            out8[s] = to8(full[s])
    info = dict(mode="seam", N_src=N, scale=1, gains=gains, stars=len(stars), feather=fdiag, corners=cdiag,
                feather_max_lsb={s: round(float(np.abs(F[s]).max() / LSB), 2) for s in big},
                repair_max_lsb={s: round(float(np.abs(corr[s]).max() / LSB), 2) for s in corr})
    return out8, info


def process_box(box, allow_esrgan=True, log=print):
    """Returns (faces_u8 dict, info dict). Deterministic given the pinned sources and the ESRGAN cache."""
    cfg = BOXES[box]
    if cfg.get("mode") == "seam":
        return process_seam_box(box, log=log)
    src = load_set(cfg["src"])
    big = [s for s in SUF if src[s].shape[0] > FLAT_MAX]
    sizes = {src[s].shape[0] for s in big}
    assert len(sizes) == 1, (box, sizes)
    N = sizes.pop()
    k = OUT_N // N
    assert k * N == OUT_N and k in (2, 4), (box, N)
    P = N // 8
    gains = {s: display_gain(src[s]) for s in big}
    info = dict(N_src=N, scale=k, pad=P, gains=gains, esrgan={})

    if cfg.get("stars"):
        bg, stars = star_extract(src)
        log("    stars extracted: %d" % len(stars))
    else:
        bg, stars = src, []
    info["stars"] = len(stars)
    allowed = repair_allowed(src)
    # item 2: the up/side feather, on the star-free SOURCE (see "seam pass"). From here on the feathered source
    # bgF is THE source: deband, boundary pin, back-projection target, detail masks and the anti-ringing range all
    # use it, and validate() recomputes it from the pinned source. Only the ESRGAN INPUT stays the unfeathered
    # canvas: the feather lives below ESRGAN's band (the detail is masked/capped by the feathered local std), and
    # the pinned cache keeps serving `check --rederive` without a GPU.
    bgF, _, fdiag, _ = seam_feather(bg, box_gains(src))
    info["feather"] = fdiag
    # deband each face on its own (never across a seam); the threshold shrinks with display gain, because
    # faint night structure is up to 4x more visible
    db = {s: (deband(bgF[s], 2.5 * LSB / gains[s]) if s in big else bgF[s]) for s in SUF}
    # ... and pin its BOUNDARY low frequencies back to the source (harmonic fill of the smoothed perimeter
    # difference): the deband may remove noise, but the edges belong to the seam system alone. Without this it
    # flattened a thin upscaler edge line on mohday1 and moved rt's top edge 0.9 LSB where no repair was needed.
    for s in big:
        pts = perimeter(N)
        dif = ndimage.gaussian_filter1d(bgF[s][pts[:, 0], pts[:, 1]] - db[s][pts[:, 0], pts[:, 1]],
                                        max(1.0, N / 128.0), axis=0, mode="wrap")
        ring = np.zeros((N, N, 3))
        ring[pts[:, 0], pts[:, 1]] = dif
        db[s] = db[s] + dirichlet(ring)

    hyb, clamp = {}, {}
    for s in SUF:
        if s not in big:
            hyb[s] = src[s]
            continue
        C = N + 2 * P
        M = C * k
        # true neighbours only across edges inside the seam system; clamp elsewhere (see padded_face)
        partners = allowed if s in allowed else set()
        canvas = padded_face(bg, s, N, P, partners=partners)          # ESRGAN input only (cache key)
        fcanvas = padded_face(bgF, s, N, P, partners=partners)        # the source every mask/range reads
        dcanvas = padded_face(db, s, N, P, partners=partners)
        esr4, key, osha = esrgan(to8(canvas), allow_run=allow_esrgan)
        del canvas
        info["esrgan"][s] = dict(key=key, out_sha256=osha)
        esr = box_down(esr4, M).astype(np.float32) if k != 4 else esr4
        del esr4
        # base: anti-ringing Lanczos of the debanded canvas, clamped to the local 3x3 source range
        B = rs(dcanvas, M)
        lo = rs(ndimage.minimum_filter(dcanvas, size=(3, 3, 1)), M, Image.Resampling.BILINEAR)
        hi = rs(ndimage.maximum_filter(dcanvas, size=(3, 3, 1)), M, Image.Resampling.BILINEAR)
        B = np.clip(B, lo, hi)
        # detail: only what the source grid cannot carry, only where the source has structure, capped,
        # and never near a star or a bright disc (halos / ringing)
        D = esr - rs(box_down(esr, C), M)
        sd = local_std(fcanvas)
        Msk = smoothstep(1.5 * LSB, 6.0 * LSB, sd)
        # bright discs get a wide berth (the validator's disc region is 4 source texels; 6 here), stars 3+2,
        # and so does every isolated point peak the validator's star detector would find (sun glitter on
        # nordawn's sea, specks): detail and back-projection rang around them (20 LSB, star_flux 0.89)
        pkm = np.zeros(fcanvas.shape[:2], bool)
        pk = star_detect(fcanvas)
        pkm[pk[:, 0], pk[:, 1]] = True
        dexcl = ndimage.binary_dilation(disc_mask(fcanvas), iterations=6) | ndimage.binary_dilation(pkm, iterations=3)
        excl = dexcl.copy()
        if stars:
            excl |= ndimage.binary_dilation(star_mask(s, N, stars, 3.0, pad=P), iterations=2)
        Msk = Msk * (~excl)
        Mk = rs(Msk, M, Image.Resampling.BILINEAR)[..., None]
        cap = rs(sd, M, Image.Resampling.BILINEAR)[..., None] * 2.0 + 0.5 * LSB
        H = B + np.clip(D, -cap, cap) * Mk
        del B, D, esr, Mk, cap, lo, hi
        # Back-projection onto the debanded source (the low band IS the source's, exactly), alternated with
        # the anti-ringing clamp around discs/peaks (hold the result inside the local range of the star-free
        # SOURCE canvas) - projection onto two convex sets. Both constraints can hold at once (a flat block
        # equal to its source texel satisfies both), so this converges. A clamp applied once AFTER the
        # back-projection broke its exactness at 1-texel features: it shifted m5l2's bright bottom-edge line
        # by half a texel (+2 / -1.3 LSB rows, block 2.4, repair 3.2) and left 12-19 LSB halos on t3l2.
        # The range is the face's OWN 3x3 range (edge-clamped, exactly what the bright_disc gate checks): the
        # neighbour-padded canvas let the outermost texel ring borrow a neighbour's brighter texels (m5l2: all
        # residual excursions sat at distance 0-1 from the edge). The clamp acts on the face only.
        own = padded_face(bgF, s, N, P, partners=set())
        lo = rs(ndimage.minimum_filter(own, size=(3, 3, 1)), M, Image.Resampling.BILINEAR)
        hi = rs(ndimage.maximum_filter(own, size=(3, 3, 1)), M, Image.Resampling.BILINEAR)
        del own
        dN = np.asarray(Image.fromarray(dexcl.astype(np.uint8) * 255).resize((M, M), Image.Resampling.NEAREST)) > 127
        inside = np.zeros((M, M), bool)
        inside[P * k:(P + N) * k, P * k:(P + N) * k] = True
        dN &= inside
        for it in range(10):
            r = dcanvas - box_down(H, C)
            # smooth (Lanczos) corrections first; then EXACT projections (the residual added uniformly over
            # its k x k block), so both steps are true projections and the alternation converges - the
            # Lanczos step alone stalled at m5l2's line (repair_err 0.92). Late residuals are ~0.1 LSB.
            H = H + (rs(r, M) if it < 4 else np.repeat(np.repeat(r, k, 0), k, 1).astype(np.float32))
            if dN.any():
                H = np.where(dN[..., None], np.clip(H, lo, hi), H)
        cy = slice(P * k, (P + N) * k)
        hyb[s] = np.asarray(H[cy, cy], np.float64)
        clamp[s] = (dN[cy, cy].copy(), np.asarray(lo[cy, cy]), np.asarray(hi[cy, cy]))
        del H, lo, hi, dN
        log("    %s done" % s)
    pre = {s: hyb[s] for s in SUF}
    rep, corr = harmonic_repair(pre)
    fin = star_render(rep, stars) if stars else rep
    slayer = star_render({s: np.zeros_like(fin[s]) for s in SUF}, stars) if stars else {}
    out8 = {}
    for s in SUF:
        if s in big:
            if np.isnan(fin[s]).any():
                raise SystemExit("NaN in %s %s" % (box, s))
            q = bluenoise_dither8(fin[s], face_seed(box, s)).astype(np.int16)
            # On dark faces (display gain >= 2) the disc/peak clamp must survive quantization: round the allowed
            # range INWARD (moved by the seam repair field and the star layer, added after the range was taken).
            # Not below gain 2: there the < 1 LSB blue-noise excursion is already inside the disc gate, and
            # rounding a bound inward biases texels that sit ON it by up to +1 LSB (m5l2's edge line: 0.78).
            dN, lo, hi = clamp[s]
            if dN.any() and gains[s] >= 2.0:
                c = (corr[s] if s in corr else 0) + (slayer[s] if s in slayer else 0)
                lo_q = np.ceil((lo + c) * 255 - 1e-6)
                hi_q = np.floor((hi + c) * 255 + 1e-6)
                ok = dN[..., None] & (lo_q <= hi_q)
                q = np.where(ok, np.clip(q, lo_q, hi_q), q).astype(np.int16)
            out8[s] = np.clip(q, 0, 255).astype(np.uint8)
        else:
            out8[s] = to8(src[s])      # flat card: the decoded source, verbatim
    info["repair_max_lsb"] = {s: round(float(np.abs(corr[s]).max() / LSB), 2) for s in corr}
    return out8, info


# ============================================================================== validator
def _edge_arrays(faces, N_eval, flat):
    """Per cube edge: A's edge/inner texels and B's matched edge/inner values at the SAME directions, all
    sampled bilinearly (clamped) at N_eval texel centres. For a face at N_eval this is the texel itself;
    for a smaller face it is the magnified image GL actually draws - so candidate and source are measured
    the same way at the same scale."""
    res, done = [], set()
    c = (np.arange(N_eval) + 0.5) / N_eval
    e0, e1 = 0.5 / N_eval, 1.5 / N_eval
    for A in SUF:
        if A in flat:
            continue
        for side in "LRTB":
            if side == "L":
                ua, va, ui, vi, uo, vo, uo2, vo2 = e0, c, e1, c, -e0, c, -e1, c
            elif side == "R":
                ua, va, ui, vi, uo, vo, uo2, vo2 = 1 - e0, c, 1 - e1, c, 1 + e0, c, 1 + e1, c
            elif side == "T":
                ua, va, ui, vi, uo, vo, uo2, vo2 = c, e0, c, e1, c, -e0, c, -e1
            else:
                ua, va, ui, vi, uo, vo, uo2, vo2 = c, 1 - e0, c, 1 - e1, c, 1 + e0, c, 1 + e1
            bc = lambda z: np.broadcast_to(z, (N_eval,)).astype(np.float64)
            fi, ub, vb = dir_face(face_dir(A, bc(uo), bc(vo)))
            B = SUF[int(np.bincount(fi).argmax())]
            key = tuple(sorted((A, B)))
            if key in done or B in flat:
                continue
            done.add(key)
            fi2, ub2, vb2 = dir_face(face_dir(A, bc(uo2), bc(vo2)))
            a_e = sample_bilinear(faces[A], bc(ua), bc(va))
            a_i = sample_bilinear(faces[A], bc(ui), bc(vi))
            b_e = sample_bilinear(faces[B], ub, vb)
            b_i = sample_bilinear(faces[B], ub2, vb2)
            res.append(("%s.%s|%s" % (A, side, B), A, B, a_e, b_e, a_i, b_i))
    return res


def seam_stats(faces, N_eval, flat, smooth=2.0):
    out = {}
    for name, A, B, ae, be, ai, bi in _edge_arrays(faces, N_eval, flat):
        ae, be, ai, bi = [ndimage.gaussian_filter1d(z, smooth, axis=0) for z in (ae, be, ai, bi)]
        d = np.abs(ae - be).mean(-1) / LSB
        g = 0.5 * (np.abs(ae - ai).mean(-1) + np.abs(be - bi).mean(-1)) / LSB
        w = max(4, N_eval // 16)
        diff = (ae - be) / LSB
        lf = max(float(np.abs(diff[i:i + w].mean(0)).max()) for i in range(0, N_eval - w + 1, w))
        out[name] = dict(A=A, B=B, cross=float(d.mean()), grad=float(g.mean()),
                         ratio=float(d.mean() / max(g.mean(), 0.25)), lowfreq=lf)
    return out


def bandpass(L, s1=1.0, s2=4.0):
    return ndimage.gaussian_filter(L, s1) - ndimage.gaussian_filter(L, s2)


def band_count(a8, mask, min_run):
    """False contours: 1-4 LSB steps with >= min_run identical texels on BOTH sides, in smooth regions,
    ALL channels, rows AND columns. Returns worst channel, per Mtexel. (The pilot counted 1-2 LSB steps on
    green only, every 256th row: a 6-bit posterize - 4-LSB steps - scored zero. See selftest.)"""
    worst = 0.0
    H, W = a8.shape[:2]
    for c in range(3):
        cnt = 0
        for A, Mm in ((a8[..., c].astype(np.int16), mask), (a8[..., c].T.astype(np.int16), mask.T)):
            R, Cn = A.shape
            ch = np.zeros((R, Cn), bool)
            ch[:, 0] = True
            ch[:, 1:] = A[:, 1:] != A[:, :-1]
            ar = np.broadcast_to(np.arange(Cn), (R, Cn))
            start = np.maximum.accumulate(np.where(ch, ar, 0), axis=1)
            endm = np.zeros((R, Cn), bool)
            endm[:, -1] = True
            endm[:, :-1] = ch[:, 1:]
            end = np.minimum.accumulate(np.where(endm, ar, Cn - 1)[:, ::-1], axis=1)[:, ::-1]
            runlen = end - start + 1
            step = np.zeros((R, Cn), np.int16)
            step[:, 1:] = np.abs(A[:, 1:] - A[:, :-1])
            left = np.zeros((R, Cn), np.int64)
            left[:, 1:] = runlen[:, :-1]
            ok = ch & (ar > 0) & (step >= 1) & (step <= 4) & (left >= min_run) & (runlen >= min_run) & Mm
            cnt += int(ok.sum())
        worst = max(worst, cnt / float(H * W) * 1e6)
    return worst


def star_detect(src_face, thr=24 / 255.0):
    L = luma(src_face)
    med = ndimage.median_filter(L, 7, mode="nearest")
    return np.argwhere((L == ndimage.maximum_filter(L, 3)) & (L - med > thr))


def validate(box, out, src, today=None, retail=None):
    """Every gate, on DECODED 8-bit output vs the pinned source. `out`/`src`: suf -> float [0,1].
    Star boxes are judged per LAYER, the way they are built: the star layer is a deterministic function of
    the pinned source (star_extract), so it is rebuilt here exactly and subtracted from the output; the
    background gates (tone, seams, corners, discs, banding, mottle, detail) then compare the star-free
    output with the star-free source, and the star gates compare the FULL output with the FULL source.
    A seam-only box (mode "seam") keeps the source's stars untouched, so its star layer is the source's own
    (full - star-free background), subtracted from both.
    Seam pass (2026-09-26): the background reference is the FEATHERED star-free source, rebuilt here from the
    pinned source exactly as the pipeline builds it (item 2); the feather itself is gated (band-confined,
    bounded); seam_local (item 1) and grain_jump (item 4) are judged on the output against the ORIGINAL art."""
    cfg = BOXES.get(box, {})
    gain_src = src                                   # the pinned faces: the one input the feather's gains come from
    cdiag, cmask = {}, None
    if cfg.get("mode") == "seam":
        # the effective seam-only source: hot corner texels solved out (gated below), stars at the AA_HD scale
        src, cmask, cdiag = corner_rebuild(src)
    full_out, full_src = out, src
    if cfg.get("mode") == "seam":
        src_bg, _ = star_extract_hd(src)             # every seam-only box: point sources held out, as built
        layer = {s: src[s] - src_bg[s] for s in SUF}
        out = {s: out[s] - layer[s] for s in SUF}
        src = src_bg
    elif cfg.get("stars"):
        src_bg, stars = star_extract(src)
        layer = star_render({s: np.zeros_like(out[s]) for s in SUF}, stars)
        out = {s: out[s] - layer[s] for s in SUF}
        src = src_bg
    flat = {s for s in SUF if src[s].shape[0] <= FLAT_MAX}
    rep = {"faces": {}, "edges": {}, "local": {}, "fails": []}
    gains = {s: (display_gain(src[s]) if s not in flat else 1.0) for s in SUF}
    src_orig = src
    src, Ff, fdiag, fmask = seam_feather(src_orig, box_gains(gain_src))
    rep["feather"] = fdiag
    # corner_rebuild (seam-only boxes): changes only texels attached to an up corner, within CORNER["R"], and the
    # harmonic fill stays inside the range of the known texels around it (maximum principle)
    rep["corners"] = cdiag
    if cmask is not None:
        for s_ in SUF:
            if not cmask[s_].any():
                continue
            N_ = cmask[s_].shape[0]
            ok = np.zeros((N_, N_), bool)
            for d in up_corners():
                if np.dot(face_dir(s_, np.array([0.5]), np.array([0.5]))[0], d) <= 0.5:
                    continue
                y, x = _corner_texel(s_, d, N_)
                yy, xx = np.ogrid[0:N_, 0:N_]
                ok |= np.hypot(yy - y, xx - x) <= corner_geom(N_)[0]
            if (cmask[s_] & ~ok).any():
                rep["fails"].append("%s:corner_outside" % s_)
        for key, dg in cdiag.items():
            if dg["fill_lo"] < dg["ring_lo"] - 0.5 or dg["fill_hi"] > dg["ring_hi"] + 0.5:
                rep["fails"].append("%s:corner_fill" % key)
    allowed = repair_allowed(src)
    N_out = max(out[s].shape[0] for s in SUF)
    Hfield = {}
    # ---- per face
    for s in SUF:
        o, a = out[s], src[s]
        N, n = o.shape[0], a.shape[0]
        g = gains[s]
        m = {"N": N, "gain": round(g, 2)}
        fails = []
        if s in flat:
            if N != n or np.abs(o - a).max() > 0.5 * LSB:
                fails.append("flat_not_verbatim")
            m["FAIL"] = fails
            rep["faces"][s] = m
            continue
        if N & (N - 1) or N < n:
            fails.append("size")
        d = box_down(o, n)
        R = (d - a) / LSB                                   # texture LSB
        shift = R.mean((0, 1))
        m["mean_shift"] = [round(float(x), 3) for x in shift]
        if np.abs(shift).max() > GATES["mean_shift_max"] / g:
            fails.append("mean_shift")
        # tone: split R into its harmonic part (fixed by the boundary = the seam repair) and the rest
        pts = perimeter(n)
        ring_v = ndimage.gaussian_filter1d(R[pts[:, 0], pts[:, 1]], max(1.0, n / 128.0), axis=0, mode="wrap")
        ring = np.zeros_like(R)
        ring[pts[:, 0], pts[:, 1]] = ring_v
        Hh = dirichlet(ring)
        Hfield[s] = Hh
        I = R - Hh
        bs = max(4, n // 32)
        blk = float(np.abs(box_down(I, n // bs)).max())
        m["block_shift"] = round(blk, 3)
        if blk > GATES["block_shift_max"] / g:
            fails.append("block_shift")
        # The harmonic part may only move each boundary texel TOWARD its cross-edge partner, by at most the
        # full amount a perfect repair needs - never away, never past. (The padded canvas already blends the
        # edge partially, so the measured move is normally a same-sign fraction of `need`.) A tone shift
        # therefore cannot hide in H: H is fixed by the boundary, and the boundary is bounded here.
        _, need = boundary_need(src, s, allowed)
        need = need / LSB
        rerr = float(np.abs(ring_v - np.clip(ring_v, np.minimum(need, 0), np.maximum(need, 0))).max())
        m["repair_err"] = round(rerr, 3)
        if rerr > GATES["repair_err_max"] / g:
            fails.append("repair_err")
        # hallucination / mottle (ratio: gain invariant)
        L_src = luma(a) / LSB
        sd = np.sqrt(np.maximum(ndimage.uniform_filter(L_src ** 2, 5) - ndimage.uniform_filter(L_src, 5) ** 2, 0))
        smooth_n = sd < 1.5
        smooth_N = np.asarray(Image.fromarray(smooth_n.astype(np.uint8) * 255).resize((N, N), Image.Resampling.NEAREST)) > 127
        lz = rs(a, N).astype(np.float64)
        bo = bandpass(luma(o) / LSB)
        br = bandpass(luma(lz) / LSB)
        mo = float(np.sqrt((bo[smooth_N] ** 2).mean())) if smooth_N.any() else 0.0
        mr = float(np.sqrt((br[smooth_N] ** 2).mean())) if smooth_N.any() else 0.0
        m["mottle"], m["mottle_ref"] = round(mo, 3), round(mr, 3)
        if mo > GATES["mottle_ratio_max"] * max(mr, 0.05):
            fails.append("mottle")
        # banding (decoded bytes vs the plain Lanczos upscale of the source)
        o8 = to8(o)
        run = max(4, N // 128)
        be, bref = band_count(o8, smooth_N, run), band_count(to8(lz), smooth_N, run)
        m["bands"], m["bands_ref"] = round(be, 1), round(bref, 1)
        if be > max(bref, GATES["bands_floor"]):
            fails.append("banding")
        # corners (star-free: star neighbourhoods masked out of both)
        spk = star_detect(a, 10 / 255.0)
        smask_n = np.zeros((n, n), bool)
        smask_n[spk[:, 0], spk[:, 1]] = True
        smask_n = ndimage.binary_dilation(smask_n, iterations=3)
        smask_N = np.asarray(Image.fromarray(smask_n.astype(np.uint8) * 255).resize((N, N), Image.Resampling.NEAREST)) > 127
        bo_a, br_a = np.abs(bo), np.abs(br)
        bo_a[smask_N] = 0
        br_a[smask_N] = 0
        w = max(8, N // 32)
        worst = 0.0
        for (y0, x0) in ((0, 0), (0, N - w), (N - w, 0), (N - w, N - w)):
            worst = max(worst, float(bo_a[y0:y0 + w, x0:x0 + w].max() - 2.0 * br_a[y0:y0 + w, x0:x0 + w].max()))
        m["corner"] = round(worst, 2)
        if worst > GATES["corner_allow"] / g:
            fails.append("corner")
        del bo, br, bo_a, br_a, lz
        # stars: kept, flux, halo (on the source grid, FULL images - star layer included)
        a_full = full_src[s]
        pk = star_detect(a_full)
        m["stars_src"] = int(len(pk))
        if len(pk):
            Ls, Ld = luma(a_full) / LSB, luma(box_down(full_out[s], n)) / LSB
            meds, medd = ndimage.median_filter(Ls, 7, mode="nearest"), ndimage.median_filter(Ld, 7, mode="nearest")
            rs_, rd_ = Ls - meds, Ld - medd
            mxd = ndimage.maximum_filter(rd_, 3)
            kept, fok, halo_bad, ratios = 0, 0, 0, []
            for y, x in pk:
                kept += mxd[y, x] > 0.5 * rs_[y, x]
                y0, y1, x0, x1 = max(0, y - 2), min(n, y + 3), max(0, x - 2), min(n, x + 3)
                fs_, fd_ = rs_[y0:y1, x0:x1].sum(), rd_[y0:y1, x0:x1].sum()
                rt = fd_ / fs_ if fs_ > 0 else 1.0
                ratios.append(rt)
                fok += abs(rt - 1) <= GATES["star_flux_tol"]
                Y0, Y1, X0, X1 = max(0, y - 4), min(n, y + 5), max(0, x - 4), min(n, x + 5)
                ringm = np.ones((Y1 - Y0, X1 - X0), bool)
                ringm[max(0, y - 2) - Y0:min(n, y + 3) - Y0, max(0, x - 2) - X0:min(n, x + 3) - X0] = False
                hd = (Ld[Y0:Y1, X0:X1][ringm] - Ls[Y0:Y1, X0:X1][ringm]).mean()
                halo_bad += hd < -GATES["star_halo_max"] / g
            m["star_keep"] = round(kept / len(pk), 3)
            m["star_flux_ok"] = round(fok / len(pk), 3)
            m["star_flux_median"] = round(float(np.median(ratios)), 3)
            m["star_halo_bad"] = round(halo_bad / len(pk), 3)
            if len(pk) >= 5:
                if kept / len(pk) < GATES["star_keep_min"]:
                    fails.append("stars_lost")
                if fok / len(pk) < GATES["star_flux_ok_min"]:
                    fails.append("star_flux")
                if halo_bad / len(pk) > GATES["star_halo_bad_max"]:
                    fails.append("star_halo")
        # horizon (side faces): the true horizon band and the bottom 5% rows
        if s in ("rt", "bk", "lf", "ft"):
            hb = R[int(0.40 * n):int(0.55 * n)].mean((0, 1))
            bb = R[int(0.95 * n):].mean((0, 1))
            m["horizon"] = [round(float(x), 3) for x in hb]
            m["bottom"] = [round(float(x), 3) for x in bb]
            if max(np.abs(hb).max(), np.abs(bb).max()) > GATES["horizon_max"] / g:
                fails.append("horizon")
        # bright discs: excursion beyond the local source range (repair field removed)
        dm = disc_mask(a)
        if dm.any():
            reg = ndimage.binary_dilation(dm, iterations=4)
            regN = np.asarray(Image.fromarray(reg.astype(np.uint8) * 255).resize((N, N), Image.Resampling.NEAREST)) > 127
            Hup = rs(Hh * LSB, N, Image.Resampling.BILINEAR)
            lo = rs(ndimage.minimum_filter(a, size=(3, 3, 1)), N, Image.Resampling.BILINEAR) + Hup
            hi = rs(ndimage.maximum_filter(a, size=(3, 3, 1)), N, Image.Resampling.BILINEAR) + Hup
            exc = np.maximum(o - hi, lo - o).max(-1)[regN]
            m["disc_exc"] = round(float(exc.max() / LSB), 2)
            if exc.max() / LSB > GATES["disc_exc_max"] / g:
                fails.append("bright_disc")
        # detail kept where the source has structure (deband damage) - fine band on the source grid
        struct = sd >= 3.0
        struct = ndimage.binary_erosion(struct, iterations=1)
        if struct.sum() > 0.01 * n * n:
            fs_ = bandpass(luma(a) / LSB, 0.0001, 1.5)
            fd_ = bandpass(luma(d) / LSB, 0.0001, 1.5)
            keep = float(np.sqrt((fd_[struct] ** 2).mean() / max((fs_[struct] ** 2).mean(), 1e-9)))
            m["detail_keep"] = round(keep, 3)
            if keep < GATES["detail_keep_min"]:
                fails.append("detail_keep")
        # the feather (item 2): only inside the up/side bands, and bounded
        if s in Ff:
            fa = np.abs(Ff[s]) / LSB
            band = feather_band(src_orig)[s]
            m["feather_max"] = round(float(fa.max()), 3)
            if (~band).any() and float(fa[~band].max()) > 0:
                fails.append("feather_outside_band")
            if fa.max() > GATES["feather_max"] or fa.max() * g > GATES["feather_display_max"]:
                fails.append("feather_max")
        m["FAIL"] = fails
        rep["faces"][s] = m
    # ---- edges: candidate and source measured identically at the output scale
    so = seam_stats(out, N_out, flat)
    ss = seam_stats(src, N_out, flat)
    for name, e in so.items():
        s_ = ss[name]
        g = max(gains[e["A"]], gains[e["B"]])
        fails = []
        if e["cross"] > s_["cross"] + GATES["seam_cross_allow"] / g:
            fails.append("seam_cross")
        # (stricter than the research gate, which only fired on cross AND ratio together; 10% relative
        # headroom over the source's own ratio so an edge the pipeline leaves untouched - dn - is not failed
        # on measurement noise)
        if e["ratio"] > max(GATES["seam_ratio_max"], s_["ratio"] * 1.1):
            fails.append("seam_ratio")
        if e["lowfreq"] > s_["lowfreq"] + GATES["seam_drift_allow"] / g:
            fails.append("seam_drift")
        rep["edges"][name] = dict(cross=round(e["cross"], 3), src_cross=round(s_["cross"], 3), ratio=round(e["ratio"], 2),
                                  src_ratio=round(s_["ratio"], 2), lowfreq=round(e["lowfreq"], 2),
                                  src_lowfreq=round(s_["lowfreq"], 2), FAIL=fails)
    # ---- item 1: seam_local, every 32-texel window of every edge (dn excluded), output vs the ORIGINAL art
    lo_out = local_seam_stats(out, flat, N_out)
    lz_src = {s: (rs(src_orig[s], N_out).astype(np.float64) if s not in flat and src_orig[s].shape[0] != N_out
                  else src_orig[s]) for s in SUF}
    lo_src = local_seam_stats(lz_src, flat, N_out)
    del lz_src
    n_src = max(src_orig[s].shape[0] for s in SUF if s not in flat)
    dom = repair_domain(fmask, n_src, N_out)
    gj_out, gj_src = grain_jumps(out, flat), grain_jumps(src_orig, flat)
    for name, e in lo_out.items():
        g = max(gains[e["A"]], gains[e["B"]])
        nw = len(e["step"])
        in_rep = dom[name] >= GATES["repair_domain_min"] if name in dom else np.zeros(nw, bool)
        bound = np.where(in_rep, GATES["local_ratio"] * e["ref"] + GATES["local_allow"] / g,
                         lo_src[name]["step"] + GATES["art_allow"] / g)
        bad = e["step"] > bound
        w = int(np.argmax(e["step"] - bound))
        ga, gb, gj = gj_out[name]
        gjs = gj_src[name][2]
        fails = (["seam_local"] if bad.any() else []) + \
            (["grain_jump"] if gj > max(GATES["grain_jump_max"], gjs + GATES["grain_jump_allow"]) else [])
        rep["local"][name] = dict(
            step_max=round(float(e["step"].max()), 3), step_p50=round(float(np.median(e["step"])), 3),
            ref_p50=round(float(np.median(e["ref"])), 3), src_step_max=round(float(lo_src[name]["step"].max()), 3),
            src_step_p50=round(float(np.median(lo_src[name]["step"])), 3),
            kink_max=round(float(e["kink"].max()), 3), kink_p50=round(float(np.median(e["kink"])), 3),
            src_kink_p50=round(float(np.median(lo_src[name]["kink"])), 3),
            windows=int(nw), repair_windows=int(in_rep.sum()), bad=int(bad.sum()),
            worst=dict(at=w * LOCAL_STRIDE, step=round(float(e["step"][w]), 3), bound=round(float(bound[w]), 3),
                       src=round(float(lo_src[name]["step"][w]), 3), repair=bool(in_rep[w])),
            grain=[round(ga, 3), round(gb, 3)], grain_jump=round(gj, 3), src_grain_jump=round(gjs, 3), FAIL=fails,
            bad_at=[dict(at=int(i) * LOCAL_STRIDE, step=round(float(e["step"][i]), 3), bound=round(float(bound[i]), 3),
                         src=round(float(lo_src[name]["step"][i]), 3), repair=bool(in_rep[i]))
                    for i in np.nonzero(bad)[0][:16]])
    # ---- 256-source boxes: no further from the retail original than the AA HD source already is
    if retail is not None:
        rr = {}
        for s in SUF:
            if s in flat or retail[s].shape[0] <= FLAT_MAX:
                continue
            nr = retail[s].shape[0]
            g = gains[s]
            do = box_down(out[s], nr) - retail[s]
            da = box_down(src[s], nr) - retail[s]
            so_, sa_ = np.abs(do.mean((0, 1))).max() / LSB, np.abs(da.mean((0, 1))).max() / LSB
            bs = max(4, nr // 32)
            bo_, ba_ = np.abs(box_down(do, nr // bs)).max() / LSB, np.abs(box_down(da, nr // bs)).max() / LSB
            f = []
            if so_ > sa_ + GATES["retail_shift_allow"] / g:
                f.append("retail_shift")
            if bo_ > ba_ + GATES["retail_block_allow"] / g:
                f.append("retail_block")
            rr[s] = dict(shift=round(float(so_), 3), aahd_shift=round(float(sa_), 3), block=round(float(bo_), 3),
                         aahd_block=round(float(ba_), 3), FAIL=f)
            if f:
                rep["faces"].setdefault(s, {}).setdefault("FAIL", []).extend(f)
        rep["retail"] = rr
    for s, m in rep["faces"].items():
        for f in m.get("FAIL", []):
            rep["fails"].append("%s:%s" % (s, f))
    for name, e in rep["edges"].items():
        for f in e["FAIL"]:
            rep["fails"].append("%s:%s" % (name, f))
    for name, e in rep["local"].items():
        for f in e["FAIL"]:
            rep["fails"].append("%s:%s" % (name, f))
    rep["verdict"] = "PASS" if not rep["fails"] else "FAIL"
    return rep


# ============================================================================== scrolling sky LAYERS
# Sky-shader STAGE images (the moving cloud dome drawn over the box, tr_sky.c FillCloudBox). Research:
# scratchpad research_clouds.md + vet_clouds.md (2026-09-25). africanight's `talonclouds` loads the DXT1
# talonclouds.dds of zzzzzzz_dds_hdmem.pk3 today (never edited here): 4x4 blocks, 13x20 px at the zenith,
# tinted, because bug-1295's NO_COMPRESSION covers skyParms faces only. The twin is built from the ONLY
# seamless copy - retail 256, pure grey - on a TORUS (a tiling texture processed with edges tiles with
# seams: the AA HD 1024 upscale did exactly that, 4.3x wrap seam). Allowlist only.
LAYERS = {
    "textures/sky/talonclouds": dict(
        maps="africanight: m1l1 m1l2a m1l2b m6l3b co_lobby2 co_lobby3 (m6l3a fogged out); MP bobobjaa01/02 "
             "laststand mohdm7; maptour kranenight",
        src=(P_RETAIL_AA, "textures/sky/talonclouds.jpg",
             "7dad943125315aab79d4f2b21dfdfc839a07be8fbfeb24d1136f49407d5b976a"),
        today=("maintt/zzzzzzz_dds_hdmem.pk3", "textures/sky/talonclouds.dds",
               "7cd31e875f01e1f70bf14c232ff745551f95ade4b3b3056191b68a0c2b0338e3"),
        aahd=("maintt/zzzzz-AA_HD_Project_Pak4.pk3", "textures/sky/talonclouds.jpg",
              "5c5489c9b8eefc652868acccf233fdf6223e6995bc8800d549496e0f1601ca5a"),
        gain=4.0,                     # additive over a NIGHT box: r_autoExposure's full 2 stops
        tcmod_scale=(3.0, 2.0), box="env/mohnight1"),
}
LAYER_OUT_N = 2048
LAYER_PREFIX = "env/hzmhd/clouds/"
LAYER_GATES = dict(
    # every value in DISPLAY LSB at the layer's gain (4), measured on the float image BEFORE dithering
    # unless marked "decoded" (vet_clouds B2: dithered ratios read ~1.0 whatever the image)
    roll_max=0.01,                # texture LSB: out(roll(src)) == roll(out(src)) - tiling proven, any phase
    mean_shift_max=0.75,          # global, after BOX-down to the source grid
    block_shift_max=2.0,          # 1/32-tile blocks after BOX-down
    corr_min=0.999,               # after BOX-down (a vertically flipped twin scores 0.13)
    grid_excess_max=0.5,          # mean step ON the 64 (retail JPEG) / 8 / 4 grid lines minus elsewhere
    wrap_excess_max=0.5,          # the wrap line minus the other 64-grid lines
    fine_keep_min=0.9,            # fine-band energy kept, on the source grid
    void_detail_max=0.5,          # detail RMS where the source is empty sky
    mottle_ratio_max=1.6,         # band-pass RMS in smooth regions vs the torus-Lanczos reference
    grain_max=0.25,               # decoded: band-pass RMS of the quantization error (white TPDF: ~0.5)
    bands_floor=5.0,              # decoded: false contours per Mtexel <= max(reference, floor)
)


def layer_member(name):
    guard(name, "layer")
    if not name.startswith("textures/"):
        raise SystemExit("layer outside textures/: %s" % name)
    return LAYER_PREFIX + name[len("textures/"):] + ".tga"


def load_grey(spec, assert_grey=True):
    a = decode_image(read_member(*spec))
    if assert_grey and not (np.array_equal(a[..., 0], a[..., 1]) and np.array_equal(a[..., 1], a[..., 2])):
        raise SystemExit("layer source is not pure grey: %s" % (spec[1],))
    return luma(a) if not assert_grey else a[..., 0].copy()


def deband_wrap(a, thr, radius=4):
    """deband() on a torus (2D grey)."""
    acc = np.zeros_like(a)
    wsum = np.zeros_like(a)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius:
                continue
            n = np.roll(np.roll(a, dy, 0), dx, 1)
            w = (np.abs(n - a) <= thr).astype(np.float64)
            acc += n * w
            wsum += w
    return acc / wsum


def periodic_fbm(n, cells=(16, 8, 4), seed=19441106, shift=(0, 0)):
    """Deterministic gradient-noise fBm on an n-periodic lattice (every cell size divides n), unit std.
    Its octaves sit above the 256 source's Nyquist (cells of 2, 1 and 0.5 source texels)."""
    out = np.zeros((n, n))
    amp = 1.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) + 0.5
    for ci, c in enumerate(cells):
        m = n // c
        assert m * c == n
        ang = np.random.default_rng(seed + 7919 * ci).random((m, m)) * 2 * np.pi
        gx, gy = np.cos(ang), np.sin(ang)
        X, Y = xx / c, yy / c
        x0, y0 = np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64)
        fx, fy = X - x0, Y - y0
        x0 %= m
        y0 %= m
        x1, y1 = (x0 + 1) % m, (y0 + 1) % m

        def dot(iy, ix, ox, oy):
            return gx[iy, ix] * ox + gy[iy, ix] * oy
        n00, n10 = dot(y0, x0, fx, fy), dot(y0, x1, fx - 1, fy)
        n01, n11 = dot(y1, x0, fx, fy - 1), dot(y1, x1, fx - 1, fy - 1)
        u = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
        v = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
        out += amp * ((n00 * (1 - u) + n10 * u) * (1 - v) + (n01 * (1 - u) + n11 * u) * v)
        amp *= 0.5
    out = np.roll(out, shift, (0, 1))
    return (out - out.mean()) / out.std()


DETAIL_ALPHA = 0.5     # detail amplitude as a fraction of the local source std, x 4d(1-d) (0 in voids/cores)


def process_layer(name, src=None, noise_shift=(0, 0), detail=True, deband_on=True, pad_mode="wrap"):
    """Float 2048 x 2048 grey, one exact period. Deterministic (no GPU step). pad_mode='edge' exists only for
    the selftest's must-fail control."""
    cfg = LAYERS[name]
    if src is None:
        src = load_grey(cfg["src"])
    N = src.shape[0]
    k = LAYER_OUT_N // N
    assert k * N == LAYER_OUT_N
    P = N // 4
    g = cfg["gain"]
    db = deband_wrap(src, 2.5 * LSB / g) if deband_on else src      # the sky rule: 2.5 LSB / display gain
    can = np.pad(src, P, mode=pad_mode)
    dcan = np.pad(db, P, mode=pad_mode)
    C, M = N + 2 * P, (N + 2 * P) * k
    B = rs(dcan, M)
    lo = rs(ndimage.minimum_filter(dcan, 3), M, Image.Resampling.BILINEAR)
    hi = rs(ndimage.maximum_filter(dcan, 3), M, Image.Resampling.BILINEAR)
    B = np.clip(B, lo, hi)
    L = can.astype(np.float64)
    sd = np.sqrt(np.maximum(ndimage.uniform_filter(L * L, 5) - ndimage.uniform_filter(L, 5) ** 2, 0))
    cap = rs(sd, M, Image.Resampling.BILINEAR) * 2.0 + 0.5 * LSB
    if detail:
        dref = max(float(np.percentile(src, 99)), 8 * LSB)
        d = np.clip(can / dref, 0, 1)
        A = DETAIL_ALPHA * rs(sd, M, Image.Resampling.BILINEAR) * rs(4 * d * (1 - d), M, Image.Resampling.BILINEAR)
        Fn = np.pad(periodic_fbm(LAYER_OUT_N, shift=noise_shift), P * k, mode="wrap")
        H = B + np.clip(Fn * A, -cap, cap)
        del Fn, A
    else:
        H = B.astype(np.float64)
    lo2, hi2 = np.maximum(lo - cap, 0.0), np.minimum(hi + cap, 1.0)
    # POCS on the padded canvas, crop LAST: BOX-down == the debanded source, inside the widened local range
    for it in range(10):
        r = dcan - box_down(H[..., None], C)[..., 0]
        H = H + (rs(r, M) if it < 4 else np.repeat(np.repeat(r, k, 0), k, 1))
        H = np.clip(H, lo2, hi2)
    c0 = P * k
    return np.asarray(H[c0:c0 + LAYER_OUT_N, c0:c0 + LAYER_OUT_N], np.float64)


def _steps(x, axis):
    return np.abs(x - np.roll(x, 1, axis)).mean(1 - axis)     # s[c] = mean |x[c] - x[c-1]| (wrapping)


def grid_excess(x, period):
    """Mean step on the grid lines (every `period` texels) minus the mean step elsewhere, worst axis, LSB."""
    worst = -9.0
    for ax in (0, 1):
        s = _steps(x, ax) / LSB
        idx = np.arange(len(s))
        worst = max(worst, float(s[idx % period == 0].mean() - s[idx % period != 0].mean()))
    return worst


def wrap_excess(x, period=64):
    worst = -9.0
    for ax in (0, 1):
        s = _steps(x, ax) / LSB
        idx = np.arange(len(s))
        worst = max(worst, float(s[0] - s[(idx % period == 0) & (idx > 0)].mean()))
    return worst


def torus_lanczos(src, n_out):
    P = src.shape[0] // 4
    k = n_out // src.shape[0]
    return np.asarray(rs(np.pad(src, P, mode="wrap"), (src.shape[0] + 2 * P) * k)[P * k:P * k + n_out, P * k:P * k + n_out], np.float64)


def layer_gates_float(name, out, src, roll=None):
    """Pre-dither gates. `roll` = (max abs error in LSB) from the roll-equivariance run, or None to skip."""
    g = LAYERS[name]["gain"]
    G = LAYER_GATES
    n = src.shape[0]
    m, f = {}, []
    if roll is not None:
        m["roll_err"] = round(roll, 5)
        if roll > G["roll_max"]:
            f.append("roll")
    m["range"] = [round(float(out.min() / LSB), 2), round(float(out.max() / LSB), 2)]
    if out.min() < -0.5 * LSB or out.max() > 1 + 0.5 * LSB or np.isnan(out).any():
        f.append("range")
    d = box_down(out[..., None], n)[..., 0]
    R = (d - src) / LSB
    m["mean_shift"] = round(float(R.mean()) * g, 3)
    if abs(R.mean()) * g > G["mean_shift_max"]:
        f.append("mean_shift")
    bs = max(4, n // 32)
    m["block_shift"] = round(float(np.abs(box_down(R[..., None], n // bs)).max()) * g, 3)
    if m["block_shift"] > G["block_shift_max"]:
        f.append("block_shift")
    m["corr"] = round(float(np.corrcoef(d.ravel(), src.ravel())[0, 1]), 5)
    if m["corr"] < G["corr_min"]:
        f.append("corr")
    k = out.shape[0] // n
    for per in sorted({4, 8, 8 * k}):
        e = grid_excess(out, per) * g
        m["grid%d" % per] = round(e, 3)
        if e > G["grid_excess_max"]:
            f.append("grid%d" % per)
    m["wrap"] = round(wrap_excess(out, 8 * k) * g, 3)
    if m["wrap"] > G["wrap_excess_max"]:
        f.append("wrap")
    fs = src - ndimage.gaussian_filter(src, 1.5, mode="wrap")
    fd = d - ndimage.gaussian_filter(d, 1.5, mode="wrap")
    m["fine_keep"] = round(float(np.sqrt((fd ** 2).sum() / max((fs ** 2).sum(), 1e-12))), 3)
    if m["fine_keep"] < G["fine_keep_min"]:
        f.append("fine_keep")
    void = ndimage.maximum_filter(src, 5, mode="wrap") <= 2 * LSB
    voidN = np.repeat(np.repeat(void, k, 0), k, 1)
    if voidN.any():
        hp = (out - ndimage.gaussian_filter(out, 4.0, mode="wrap")) / LSB
        m["void_detail"] = round(float(np.sqrt((hp[voidN] ** 2).mean())) * g, 3)
        if m["void_detail"] > G["void_detail_max"]:
            f.append("void_detail")
    Ls = src / LSB
    sd = np.sqrt(np.maximum(ndimage.uniform_filter(Ls ** 2, 5, mode="wrap") - ndimage.uniform_filter(Ls, 5, mode="wrap") ** 2, 0))
    smooth = np.repeat(np.repeat(sd < 1.5, k, 0), k, 1)
    ref = torus_lanczos(src, out.shape[0])
    bp = lambda x: ndimage.gaussian_filter(x / LSB, 1.0, mode="wrap") - ndimage.gaussian_filter(x / LSB, 4.0, mode="wrap")
    mo, mr = float(np.sqrt((bp(out)[smooth] ** 2).mean())), float(np.sqrt((bp(ref)[smooth] ** 2).mean()))
    m["mottle"], m["mottle_ref"] = round(mo, 3), round(mr, 3)
    if mo > G["mottle_ratio_max"] * max(mr, 0.05):
        f.append("mottle")
    m["FAIL"] = f
    return m


def layer_gates_decoded(name, dec8, flt, src):
    """Gates on the bytes that ship (dec8: HxWx3 uint8) against the float they were quantized from."""
    g = LAYERS[name]["gain"]
    G = LAYER_GATES
    m, f = {}, []
    N = dec8.shape[0]
    if dec8.shape[0] != dec8.shape[1] or N & (N - 1):
        f.append("size")
    if not (np.array_equal(dec8[..., 0], dec8[..., 1]) and np.array_equal(dec8[..., 1], dec8[..., 2])):
        f.append("not_grey")
    x = dec8[..., 1].astype(np.float64) / 255.0
    e = (x - flt) / LSB
    bp = ndimage.gaussian_filter(e, 1.0, mode="wrap") - ndimage.gaussian_filter(e, 4.0, mode="wrap")
    m["grain"] = round(float(np.sqrt((bp ** 2).mean())) * g, 3)
    if m["grain"] > G["grain_max"]:
        f.append("grain")
    m["quant_mean"] = round(float(e.mean()), 3)
    k = N // src.shape[0]
    for per in sorted({4, 8, 8 * k}):
        ge = grid_excess(x, per) * g
        m["dec_grid%d" % per] = round(ge, 3)
        if ge > G["grid_excess_max"]:
            f.append("dec_grid%d" % per)
    Ls = src / LSB
    sd = np.sqrt(np.maximum(ndimage.uniform_filter(Ls ** 2, 5, mode="wrap") - ndimage.uniform_filter(Ls, 5, mode="wrap") ** 2, 0))
    smooth = np.repeat(np.repeat(sd < 1.5, k, 0), k, 1)
    run = max(4, N // 128)
    be = band_count(dec8, smooth, run)
    bref = band_count(np.repeat(to8(torus_lanczos(src, N))[..., None], 3, -1), smooth, run)
    m["bands"], m["bands_ref"] = round(be, 1), round(bref, 1)
    if be > max(bref, G["bands_floor"]):
        f.append("banding")
    m["FAIL"] = f
    return m


def build_layer(name, with_roll=True):
    """-> (tga bytes, report). The roll run re-derives the whole layer from a source rolled by an off-grid
    phase and demands the rolled output: that proves the tile has no preferred origin, i.e. no seam."""
    cfg = LAYERS[name]
    src = load_grey(cfg["src"])
    out = process_layer(name, src)
    roll = None
    if with_roll:
        a, b = 37, 91                                   # off every grid (not multiples of 8 or 64/8)
        k = LAYER_OUT_N // src.shape[0]
        out_r = process_layer(name, np.roll(src, (a, b), (0, 1)), noise_shift=(a * k, b * k))
        roll = float(np.abs(out_r - np.roll(out, (a * k, b * k), (0, 1))).max() / LSB)
        del out_r
    q = bluenoise_dither8(np.repeat(out[..., None], 3, -1), face_seed(name, "layer"))
    tga = write_tga(q)
    dec = read_tga(tga)
    assert np.array_equal(dec, q)
    rep = {"float": layer_gates_float(name, out, src, roll), "decoded": layer_gates_decoded(name, dec, out, src)}
    rep["fails"] = ["float:" + x for x in rep["float"]["FAIL"]] + ["decoded:" + x for x in rep["decoded"]["FAIL"]]
    rep["verdict"] = "PASS" if not rep["fails"] else "FAIL"
    return tga, rep, out


def layer_selftest():
    """Controls for the layer gates: each must behave or the gates prove nothing."""
    name = "textures/sky/talonclouds"
    cfg = LAYERS[name]
    src = load_grey(cfg["src"])
    N = LAYER_OUT_N
    res = []

    def up_periodic_bilinear(a, n):
        k = n // a.shape[0]
        c = (np.arange(n) + 0.5) / k - 0.5
        i0 = np.floor(c).astype(np.int64)
        fr = c - i0
        i0m, i1m = i0 % a.shape[0], (i0 + 1) % a.shape[0]
        rows = a[i0m] * (1 - fr)[:, None] + a[i1m] * fr[:, None]
        return rows[:, i0m] * (1 - fr)[None, :] + rows[:, i1m] * fr[None, :]

    def ctl(label, fl, expect, dec_from=None, roll=None, exact=False):
        mf = layer_gates_float(name, fl, src, roll)
        fails = ["float:" + x for x in mf["FAIL"]]
        if dec_from is not None:
            md = layer_gates_decoded(name, dec_from, fl, src)
            fails += ["decoded:" + x for x in md["FAIL"]]
        if exact:           # must fail on exactly these gates and nothing else
            ok = sorted(x.split(":", 1)[1] for x in fails) == sorted(expect)
        else:
            ok = (not fails) if not expect else any(any(x.endswith(e) for e in expect) for x in fails)
        res.append((label, ok, fails[:10]))
        print("%-52s %s   %s" % (label, "ok" if ok else "CONTROL BROKEN", " ".join(fails[:10])), flush=True)

    plain = torus_lanczos(src, N)
    # Lanczos alone, then BOX-down, softens the finest source band by ~10.6% (fine_keep 0.894): it must fail
    # THAT gate and no other - which is also the proof that every other gate passes a harmless image.
    ctl("plain torus Lanczos -> fine_keep ONLY", plain, ["fine_keep"], exact=True,
        dec_from=bluenoise_dither8(np.repeat(plain[..., None], 3, -1), 5))
    bp_plain = process_layer(name, src, detail=False, deband_on=False)
    ctl("back-projected torus Lanczos (blue-noise) -> must PASS", bp_plain, [],
        dec_from=bluenoise_dither8(np.repeat(bp_plain[..., None], 3, -1), 5))
    rng = np.random.default_rng(7)
    tp = to8(np.repeat(plain[..., None], 3, -1) + ((rng.random((N, N)) - rng.random((N, N))) * LSB)[..., None])
    ctl("plain torus Lanczos, WHITE TPDF dither -> grain", plain, ["grain"], dec_from=tp)
    hd = luma(decode_image(read_member(*cfg["today"])))
    ctl("today: hdmem DXT1 1024 (as GL magnifies) -> FAIL", up_periodic_bilinear(hd, N), ["grid8", "grid4", "mean_shift", "block_shift", "corr", "fine_keep"])
    aa = luma(decode_image(read_member(*cfg["aahd"])))
    ctl("AA HD 1024 JPG (non-torus upscale) -> wrap", up_periodic_bilinear(aa, N), ["wrap"])
    edge = process_layer(name, src, pad_mode="edge")
    k = N // src.shape[0]
    edge_r = process_layer(name, np.roll(src, (37, 91), (0, 1)), noise_shift=(37 * k, 91 * k), pad_mode="edge")
    eroll = float(np.abs(edge_r - np.roll(edge, (37 * k, 91 * k), (0, 1))).max() / LSB)
    ctl("edge-padded (non-torus) pipeline -> roll", edge, ["roll", "wrap", "grid64"], roll=eroll)
    del edge, edge_r
    ours = process_layer(name, src)
    yy, xx = np.mgrid[0:N, 0:N]
    blot = ours + (((yy - N * 0.4) ** 2 + (xx - N * 0.6) ** 2) <= (N / 16.0) ** 2) * 2 * LSB
    ctl("our layer + a 2-LSB blotch -> block_shift", blot, ["block_shift", "mean_shift"])
    ctl("our layer flipped vertically -> corr", ours[::-1].copy(), ["corr"])
    ctl("our layer blurred 1 source texel -> fine_keep", ndimage.gaussian_filter(ours, 8.0, mode="wrap"), ["fine_keep"])
    return res


# ============================================================================== pak
def write_pak(members):
    """Deterministic: sorted entries, fixed timestamps, fixed attributes (bug-237)."""
    for name in members:
        if not name.startswith(HD_PREFIX):
            raise SystemExit("refusing to pak a member outside %s: %s" % (HD_PREFIX, name))
        guard(name, "pak member")
    tmp = PAK_PATH + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in sorted(members):
            zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zi.create_system = 0
            z.writestr(zi, members[name])
    os.replace(tmp, PAK_PATH)


# ============================================================================== commands
def included_boxes(req):
    boxes = [b for b in req if not b.startswith("textures/")] if req else list(BOXES)
    for b in boxes:
        guard(b, "box")
        if b not in BOXES:
            raise SystemExit("unknown box %s" % b)
        if b in EXCLUDE:
            raise SystemExit("%s is PERMANENTLY excluded (Omaha list, user decision 2026-09-25)" % b)
    return boxes


def cmd_build(args):
    for d in (OUT_DIR, REPORT_DIR, CACHE_DIR):
        os.makedirs(d, exist_ok=True)
    boxes = included_boxes(args.boxes)
    layers = [x for x in args.boxes if x.startswith("textures/")] if args.boxes else list(LAYERS)
    for x in layers:
        guard(x, "layer")
        if x not in LAYERS:
            raise SystemExit("unknown layer %s (allowlist only)" % x)
    man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    man.setdefault("boxes", {})
    man.setdefault("layers", {})
    for name in layers:
        t0 = time.time()
        print("== layer %s" % name, flush=True)
        tga, rep_, _ = build_layer(name)
        mem = layer_member(name)
        p = os.path.join(OUT_DIR, mem.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(tga)
        json.dump(rep_, open(os.path.join(REPORT_DIR, name.replace("/", "_") + ".json"), "w"), indent=1)
        print("   %s  (%.0fs)  %s" % (rep_["verdict"], time.time() - t0, " ".join(rep_["fails"])), flush=True)
        print("   float %s" % {k: v for k, v in rep_["float"].items() if k != "FAIL"}, flush=True)
        print("   decoded %s" % {k: v for k, v in rep_["decoded"].items() if k != "FAIL"}, flush=True)
        man["layers"][name] = dict(verdict=rep_["verdict"], fails=rep_["fails"], member=mem, sha256=sha256(tga),
                                   src=list(LAYERS[name]["src"]), float=rep_["float"], decoded=rep_["decoded"])
    for box in boxes:
        t0 = time.time()
        print("== %s" % box, flush=True)
        out8, info = process_box(box)
        # write, then validate the DECODED file (the bytes that ship)
        members = {}
        for s in SUF:
            b = write_tga(out8[s])
            name = hd_member(box, s)
            p = os.path.join(OUT_DIR, name.replace("/", os.sep))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(b)
            members[name] = sha256(b)
        dec = {s: read_tga(open(os.path.join(OUT_DIR, hd_member(box, s).replace("/", os.sep)), "rb").read()).astype(np.float64) / 255.0
               for s in SUF}
        for s in SUF:
            assert np.array_equal(to8(dec[s]), out8[s])
        src = load_set(BOXES[box]["src"])
        retail = load_set(BOXES[box]["retail"]) if "retail" in BOXES[box] else None
        rep = validate(box, dec, src, retail=retail)
        rep["info"] = info
        json.dump(rep, open(os.path.join(REPORT_DIR, box.replace("/", "_") + ".json"), "w"), indent=1)
        print("   %s  (%.0fs)  %s" % (rep["verdict"], time.time() - t0, " ".join(rep["fails"][:24])), flush=True)
        man["boxes"][box] = dict(verdict=rep["verdict"], fails=rep["fails"], members=members,
                                 src={s: list(BOXES[box]["src"][s]) for s in SUF}, info=info)
    man["esrgan"] = dict(pins={os.path.relpath(k, DEV).replace("\\", "/"): v for k, v in ESR_PINS.items()}, args=ESR_ARGS)
    man["exclude"] = EXCLUDE
    man["gates"] = GATES
    man["out_n"] = OUT_N
    ship = {}
    for box, e in sorted(man["boxes"].items()):
        if e["verdict"] != "PASS" or box in EXCLUDE:
            continue
        for name in e["members"]:
            ship[name] = open(os.path.join(OUT_DIR, name.replace("/", os.sep)), "rb").read()
            if sha256(ship[name]) != e["members"][name]:
                raise SystemExit("staged file changed since it was validated: %s" % name)
    for name, e in sorted(man["layers"].items()):
        if e["verdict"] != "PASS" or name not in LAYERS:
            continue
        ship[e["member"]] = open(os.path.join(OUT_DIR, e["member"].replace("/", os.sep)), "rb").read()
        if sha256(ship[e["member"]]) != e["sha256"]:
            raise SystemExit("staged file changed since it was validated: %s" % e["member"])
    man["shipped"] = sorted(b for b, e in man["boxes"].items() if e["verdict"] == "PASS" and b not in EXCLUDE)
    man["shipped_layers"] = sorted(n for n, e in man["layers"].items() if e["verdict"] == "PASS" and n in LAYERS)
    man["dropped"] = {b: e["fails"] for b, e in sorted(man["boxes"].items()) if e["verdict"] != "PASS"}
    man["dropped_layers"] = {n: e["fails"] for n, e in sorted(man["layers"].items()) if e["verdict"] != "PASS"}
    man["layer_gates"] = LAYER_GATES
    if ship and not args.no_pak:
        write_pak(ship)
        man["pak"] = dict(name=PAK_NAME, sha256=sha256(open(PAK_PATH, "rb").read()), members=len(ship),
                          bytes=os.path.getsize(PAK_PATH))
        print("pak: %s  %d members  %.1f MB" % (PAK_PATH, len(ship), os.path.getsize(PAK_PATH) / 1e6))
    elif not ship:
        print("NOTHING PASSED - no pak written")
    with open(MANIFEST, "w", newline="\n") as f:
        json.dump(man, f, indent=1, sort_keys=True)
        f.write("\n")
    print("shipped:", man["shipped"], man["shipped_layers"])
    print("dropped:", {b: len(v) for b, v in man["dropped"].items()}, man["dropped_layers"])


def cmd_check(args):
    """Read-only. Exit 1 unless the shipped pak is exactly what the manifest says, every source pin still
    holds, and every gate still passes on the DECODED pak members."""
    bad = []
    if not os.path.exists(MANIFEST):
        print("no manifest")
        return 1
    man = json.load(open(MANIFEST))
    if not os.path.exists(PAK_PATH):
        print("no pak at %s" % PAK_PATH)
        return 1
    if sha256(open(PAK_PATH, "rb").read()) != man.get("pak", {}).get("sha256"):
        bad.append("pak sha256 differs from the manifest")
    z = zipfile.ZipFile(PAK_PATH)
    names = sorted(z.namelist())
    expect = sorted([n for b in man["shipped"] for n in man["boxes"][b]["members"]] +
                    [man["layers"][x]["member"] for x in man.get("shipped_layers", [])])
    if names != expect:
        bad.append("pak member list != manifest (extra %s, missing %s)" % (sorted(set(names) - set(expect))[:5],
                                                                           sorted(set(expect) - set(names))[:5]))
    for n in names:
        try:
            guard(n, "pak member")
        except SystemExit as e:
            bad.append(str(e))
        if not n.startswith(HD_PREFIX):
            bad.append("member outside %s: %s" % (HD_PREFIX, n))
    for b in man["shipped"]:
        if b in EXCLUDE:
            bad.append("excluded box shipped: %s" % b)
        if b not in BOXES:
            bad.append("shipped box no longer in BOXES: %s" % b)
            continue
        print("== %s" % b, flush=True)
        dec = {}
        for s in SUF:
            name = hd_member(b, s)
            raw = z.read(name)
            if sha256(raw) != man["boxes"][b]["members"][name]:
                bad.append("%s sha256 differs" % name)
            t = read_tga(raw)
            if t.shape[0] != t.shape[1] or t.shape[0] & (t.shape[0] - 1):
                bad.append("%s not a power-of-two square: %s" % (name, t.shape))
            dec[s] = t.astype(np.float64) / 255.0
        src = load_set(BOXES[b]["src"])            # re-verifies every source pin
        retail = load_set(BOXES[b]["retail"]) if "retail" in BOXES[b] else None
        rep = validate(b, dec, src, retail=retail)
        print("   %s %s" % (rep["verdict"], " ".join(rep["fails"][:12])), flush=True)
        if rep["verdict"] != "PASS":
            bad.append("%s fails gates: %s" % (b, rep["fails"][:8]))
        if args.rederive:
            out8, _ = process_box(b, allow_esrgan=False, log=lambda *a: None)
            for s in SUF:
                if write_tga(out8[s]) != z.read(hd_member(b, s)):
                    bad.append("%s %s: re-derived bytes differ from the pak" % (b, s))
    # layers are fully deterministic (no GPU step): ALWAYS re-derived, byte-compared, and re-gated - the
    # pre-dither gates need the float image, which only a re-derivation can give back
    for x in man.get("shipped_layers", []):
        print("== layer %s" % x, flush=True)
        if x not in LAYERS:
            bad.append("shipped layer no longer in LAYERS: %s" % x)
            continue
        mem = man["layers"][x]["member"]
        raw = z.read(mem)
        if sha256(raw) != man["layers"][x]["sha256"]:
            bad.append("%s sha256 differs" % mem)
        tga, rep, _ = build_layer(x)                 # re-verifies the source pin
        if tga != raw:
            bad.append("%s: re-derived bytes differ from the pak" % mem)
        print("   %s %s" % (rep["verdict"], " ".join(rep["fails"])), flush=True)
        if rep["verdict"] != "PASS":
            bad.append("%s fails gates: %s" % (x, rep["fails"]))
    for b in bad:
        print("CHECK FAIL:", b)
    print("check: %s" % ("OK" if not bad else "FAILED (%d)" % len(bad)))
    return 1 if bad else 0


def _label(img, text):
    im = Image.fromarray(img)
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 8 + 7 * len(text), 18], fill=(0, 0, 0))
    dr.text((4, 3), text, fill=(255, 255, 0))
    return np.asarray(im)


SHEET_VIEWS = [("zenith (straight up)", 0.0, -89.9), ("3-face corner rt|bk|up, 35 deg up", 45.0, -35.26),
               ("horizon corner rt|bk", 45.0, 0.0)]


def dome_texcoords(yaw_deg, pitch_deg, W, H, hfov_deg, scale=(3.0, 2.0), radius=4096.0, height=512.0):
    """tr_sky.c R_InitSkyTexCoords for a view ray: sphere of radius R+h centred R below the eye,
    s = acos(v.x), t = acos(v.y), then tcMod scale. Returns (s, t) in texture units, and the view dirs."""
    yaw, pit = np.radians(yaw_deg), np.radians(pitch_deg)
    fwd = np.array([np.cos(pit) * np.cos(yaw), np.cos(pit) * np.sin(yaw), -np.sin(pit)])
    left = np.array([-np.sin(yaw), np.cos(yaw), 0.0])
    up = np.cross(fwd, left)
    tx = np.tan(np.radians(hfov_deg) / 2)
    ty = tx * H / W
    X, Y = np.meshgrid(((np.arange(W) + 0.5) / W * 2 - 1) * tx, (1 - (np.arange(H) + 0.5) / H * 2) * ty)
    d = fwd[None, None, :] - X[..., None] * left[None, None, :] + Y[..., None] * up[None, None, :]
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    dz = d[..., 2]
    p = -radius * dz + np.sqrt((radius * dz) ** 2 + 2 * radius * height + height * height)
    v = p[..., None] * d
    v[..., 2] += radius
    v /= np.linalg.norm(v, axis=-1, keepdims=True)
    return np.arccos(np.clip(v[..., 0], -1, 1)) * scale[0], np.arccos(np.clip(v[..., 1], -1, 1)) * scale[1], d


def sample_repeat_trilinear(img, s, t):
    """GL_REPEAT + GL_LINEAR_MIPMAP_LINEAR (isotropic - the engine's 16x aniso is sharper toward the horizon,
    equally for both images). Mip-aware so the sheet does not alias near the horizon (vet_clouds C8)."""
    pyr = [img.astype(np.float64)]
    while pyr[-1].shape[0] > 1:
        a = pyr[-1]
        pyr.append(0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]))
    Hh, Ww = img.shape[:2]
    fp = np.maximum.reduce([np.abs(np.gradient(s, axis=1)) * Ww, np.abs(np.gradient(t, axis=1)) * Hh,
                            np.abs(np.gradient(s, axis=0)) * Ww, np.abs(np.gradient(t, axis=0)) * Hh])
    lam = np.clip(np.log2(np.maximum(fp, 1e-6)), 0, len(pyr) - 1)

    def bil(a, s_, t_):
        h, w = a.shape[:2]
        x, y = s_ * w - 0.5, t_ * h - 0.5
        x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
        fx, fy = (x - x0)[..., None], (y - y0)[..., None]
        x0 %= w
        y0 %= h
        x1, y1 = (x0 + 1) % w, (y0 + 1) % h
        return a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x1] * fx * (1 - fy) + a[y1, x0] * (1 - fx) * fy + a[y1, x1] * fx * fy

    out = np.zeros(s.shape + (img.shape[2],))
    l0 = np.floor(lam).astype(np.int64)
    fr = (lam - l0)[..., None]
    for L in np.unique(l0):
        m = l0 == L
        a = bil(pyr[L], s[m], t[m])
        b = bil(pyr[min(L + 1, len(pyr) - 1)], s[m], t[m])
        out[m] = a * (1 - fr[m]) + b * fr[m]
    return out


def layer_sheet(name, W=3440, H=1440):
    cfg = LAYERS[name]
    hf = hfov_for(80.0, W, H)
    box_today = load_set(BOXES[cfg["box"]]["today"]) if cfg["box"] in BOXES else None
    old = decode_image(read_member(*cfg["today"]))
    new = read_tga(open(os.path.join(OUT_DIR, layer_member(name).replace("/", os.sep)), "rb").read()).astype(np.float64) / 255.0
    fdir = os.path.join(SHEET_DIR, name.replace("/", "_"))
    os.makedirs(fdir, exist_ok=True)
    cw, ch = 1400, 860
    views = [("zenith (straight up)", 0.0, -89.9), ("45 deg up", 0.0, -45.0), ("15 deg up (toward the horizon)", 0.0, -15.0)]
    renders = {}
    for vname, yaw, pit in views:
        s, t, _ = dome_texcoords(yaw, pit, W, H, hf, cfg["tcmod_scale"])
        base = perspective(box_today, yaw, pit, W, H, hf) if box_today else np.zeros((H, W, 3))
        renders[vname] = (base + sample_repeat_trilinear(old, s, t), base + sample_repeat_trilinear(new, s, t))
    paths = []
    for gain in (1.0, 4.0):
        rows = []
        for vname, _, _ in views:
            tiles = []
            for tag, img in zip(("OLD: hdmem DXT1 1024 (what gl2 draws today)", "NEW: env/hzmhd/clouds 2048 grey"), renders[vname]):
                full = np.clip(img * gain * 255 + 0.5, 0, 255).astype(np.uint8)
                if gain == 1.0:
                    Image.fromarray(full).save(os.path.join(fdir, "full_%s_%s.png" % (
                        re.sub(r"[^a-z0-9]+", "_", vname.lower())[:20], tag.split(":")[0].lower())))
                c = full[H // 2 - ch // 2:H // 2 + ch // 2, W // 2 - cw // 2:W // 2 + cw // 2]
                tiles.append(_label(c, "%s | %s | over the %s box | 1:1 of 3440x1440 @ %.1f deg%s" % (
                    tag, vname, cfg["box"], hf, (" | gain x%.0f" % gain) if gain != 1 else "")))
            rows.append(np.concatenate(tiles, 1))
        p = os.path.join(SHEET_DIR, "%s%s.png" % (name.replace("/", "_"), "" if gain == 1 else "_gain%d" % gain))
        Image.fromarray(np.concatenate(rows, 0)).save(p)
        paths.append(p)
        print(p)
    return paths


def cmd_sheet(args):
    os.makedirs(SHEET_DIR, exist_ok=True)
    man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {"boxes": {}}
    if args.boxes and all(b.startswith("textures/") for b in args.boxes):
        for x in args.boxes:
            layer_sheet(x)
        return 0
    boxes = args.boxes or sorted(man["boxes"])
    W, H = 3440, 1440
    hf = hfov_for(80.0, W, H)
    cw, ch = 1400, 860
    index = []
    for box in boxes:
        e = man["boxes"].get(box)
        if not e:
            print("no build for", box)
            continue
        old = load_set(BOXES[box]["today"])
        new = {s: read_tga(open(os.path.join(OUT_DIR, hd_member(box, s).replace("/", os.sep)), "rb").read()).astype(np.float64) / 255.0
               for s in SUF}
        g = max(display_gain(load_set(BOXES[box]["src"])[s]) for s in SUF if old[s].shape[0] > FLAT_MAX)
        gains = [1.0] + ([4.0] if g > 1.5 else [])
        fdir = os.path.join(SHEET_DIR, box.replace("/", "_"))
        os.makedirs(fdir, exist_ok=True)
        for gain in gains:
            rows = []
            for vname, yaw, pit in SHEET_VIEWS:
                tiles = []
                for tag, faces in (("OLD (what gl2 draws today)", old), ("NEW (env/hzmhd)", new)):
                    img = perspective(faces, yaw, pit, W, H, hf)
                    full = np.clip(img * gain * 255 + 0.5, 0, 255).astype(np.uint8)
                    if gain == 1.0:
                        Image.fromarray(full).save(os.path.join(fdir, "full_%s_%s.png" % (
                            re.sub(r"[^a-z0-9]+", "_", vname.lower())[:24], tag.split()[0].lower())))
                    c = full[H // 2 - ch // 2:H // 2 + ch // 2, W // 2 - cw // 2:W // 2 + cw // 2]
                    tiles.append(_label(c, "%s | %s | 1:1 centre crop of 3440x1440 @ %.1f deg%s" % (
                        tag, vname, hf, (" | gain x%.0f" % gain) if gain != 1 else "")))
                rows.append(np.concatenate(tiles, 1))
            sheet = np.concatenate(rows, 0)
            p = os.path.join(SHEET_DIR, "%s%s.png" % (box.replace("/", "_"), "" if gain == 1 else "_gain%d" % gain))
            Image.fromarray(sheet).save(p)
            index.append((box, e["verdict"], p))
            print(p)
    with open(os.path.join(SHEET_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write("<!doctype html><meta charset=utf-8><title>Sky HD sheets</title><body style='background:#111;color:#ddd;font-family:sans-serif'>")
        for box, v, p in index:
            f.write("<h3>%s - %s</h3><a href='%s'><img src='%s' style='max-width:100%%'></a>\n" % (
                box, v, os.path.basename(p), os.path.basename(p)))


def cmd_selftest(args):
    """Controls. A gate that cannot fail proves nothing; one that fails the source against itself is biased.
    `selftest textures/sky/talonclouds` runs the LAYER controls instead."""
    if args.boxes and args.boxes[0].startswith("textures/"):
        res = layer_selftest()
        os.makedirs(REPORT_DIR, exist_ok=True)
        json.dump(res, open(os.path.join(REPORT_DIR, "selftest_layers.json"), "w"), indent=1)
        broken = [r for r in res if not r[1]]
        print("layer selftest: %s" % ("all controls behave" if not broken else "%d CONTROL(S) BROKEN" % len(broken)))
        return 1 if broken else 0
    box = (args.boxes or ["env/t3l2"])[0]
    man = json.load(open(MANIFEST))
    src = load_set(BOXES[box]["src"])
    retail = load_set(BOXES[box]["retail"]) if "retail" in BOXES[box] else None
    new = {s: read_tga(open(os.path.join(OUT_DIR, hd_member(box, s).replace("/", os.sep)), "rb").read()).astype(np.float64) / 255.0
           for s in SUF}
    big = [s for s in SUF if src[s].shape[0] > FLAT_MAX]
    N = new[big[0]].shape[0]
    results = []

    def run(name, cand, expect, ref=src, rt=retail):
        r = validate(box, cand, ref, retail=rt)
        hit = [f for f in r["fails"] if any(f.endswith(":" + x) for x in expect)] if expect else []
        ok = (r["verdict"] == "PASS") if not expect else bool(hit)
        results.append((name, ok, r["fails"][:10]))
        print("%-44s %s   %s" % (name, "ok" if ok else "CONTROL BROKEN", " ".join(r["fails"][:10])), flush=True)

    # 1. the (effective) source against itself: every gate must pass (no gate is biased toward FAIL). Since the seam
    #    pass the reference is the FEATHERED source, so the candidate is too (for a plain box: the feathered faces)
    eff = src
    if not BOXES[box].get("stars"):
        eff = seam_feather(src, box_gains(src))[0]
    run("effective source vs itself -> must PASS", eff, [], rt=retail)
    # 2. the bug-2533 method: independent per-face ESRGAN (no padding) -> must FAIL
    ind = {}
    for s in SUF:
        if s in big:
            e4, _, _ = esrgan(to8(src[s]))
            ind[s] = box_down(e4, N) if e4.shape[0] != N else e4.astype(np.float64)
            ind[s] = to8(ind[s]).astype(np.float64) / 255
        else:
            ind[s] = src[s]
    run("independent per-face ESRGAN -> must FAIL", ind, ["seam_cross", "seam_ratio", "seam_drift", "block_shift",
                                                            "mean_shift", "mottle", "repair_err", "detail_keep"])
    f0 = big[0]
    # 3. a 2-LSB blotch (disc radius N/16) in a passing output -> block_shift must fire
    c = {s: new[s].copy() for s in SUF}
    yy, xx = np.mgrid[0:N, 0:N]
    disc = (((yy - N * 0.4) ** 2 + (xx - N * 0.6) ** 2) <= (N / 16.0) ** 2)
    c[f0] = np.clip(c[f0] + disc[..., None] * 2 * LSB, 0, 1)
    c[f0] = to8(c[f0]) / 255.0
    run("2-LSB blotch -> block_shift", c, ["block_shift"])
    # 4. a +1.5 LSB offset on one whole face -> a seam/shift gate must fire
    c = {s: new[s].copy() for s in SUF}
    c[f0] = to8(c[f0] + 1.5 * LSB) / 255.0
    run("+1.5 LSB face offset -> seam/shift", c, ["seam_cross", "seam_drift", "mean_shift", "repair_err"])
    # 5. smooth (kills the dither) then posterize to 6 bits: 4-LSB false contours -> banding must fire.
    #    (Posterizing the DITHERED output only makes noise - no plateaus - which is not the defect.)
    c = {s: new[s].copy() for s in SUF}
    for s in big:
        c[s] = to8(np.floor(ndimage.gaussian_filter(new[s], (3, 3, 0)) * 63 + 0.5) / 63) / 255.0
    run("smoothed + 6-bit posterize -> banding", c, ["banding"])
    # 6. blur a face by 1 source texel -> detail_keep must fire (if the face has structure)
    c = {s: new[s].copy() for s in SUF}
    sig = N / float(src[f0].shape[0])
    for s in big:
        c[s] = to8(ndimage.gaussian_filter(new[s], (sig, sig, 0))) / 255.0
    run("1-src-texel blur -> detail_keep", c, ["detail_keep", "stars_lost", "star_flux"])
    # 7. stars deleted -> the star gate must fire (on a star box: the retail source with its stars removed)
    sb = "env/mohnight1"
    s_src = load_set(BOXES[sb]["src"])
    bg, st = star_extract(s_src)
    r = validate(sb, bg, s_src)
    ok = any(f.endswith(("stars_lost", "star_flux")) for f in r["fails"])
    results.append(("stars deleted (mohnight1) -> stars", ok, r["fails"][:10]))
    print("%-44s %s   %s" % ("stars deleted (mohnight1) -> stars", "ok" if ok else "CONTROL BROKEN", " ".join(r["fails"][:10])))
    # 8. a dark ring around each star -> star_halo must fire
    c = {s: s_src[s].copy() for s in SUF}
    for s in SUF:
        if s_src[s].shape[0] <= FLAT_MAX:
            continue
        n = s_src[s].shape[0]
        ring = np.zeros((n, n), bool)
        for y, x in star_detect(s_src[s]):
            Y0, Y1, X0, X1 = max(0, y - 4), min(n, y + 5), max(0, x - 4), min(n, x + 5)
            ring[Y0:Y1, X0:X1] = True
            ring[max(0, y - 2):min(n, y + 3), max(0, x - 2):min(n, x + 3)] = False
        c[s] = np.clip(c[s] - ring[..., None] * 3 * LSB, 0, 1)
    r = validate(sb, c, s_src)
    ok = any(f.endswith("star_halo") for f in r["fails"])
    results.append(("dark star halos -> star_halo", ok, r["fails"][:10]))
    print("%-44s %s   %s" % ("dark star halos -> star_halo", "ok" if ok else "CONTROL BROKEN", " ".join(r["fails"][:10])))
    # 9. item 1: a 3-display-LSB step planted on an up/side edge of the passing output, 12 rows deep x 128 along,
    #    inside the feather's repair domain -> seam_local must fire
    c = {s: new[s].copy() for s in SUF}
    A, sA, _, _ = up_side_edges()[0]
    g = max(display_gain(src[A]), display_gain(src["up"]))
    st = np.zeros((N, 12, 3))
    st[N // 2 - 64:N // 2 + 64] = 3.0 / g * LSB
    _add_strip(c[A], sA, st)
    c[A] = to8(c[A]) / 255.0
    run("3-display-LSB up/side step -> seam_local", c, ["seam_local"])
    # 10. item 4: white grain (1 LSB rms) on the whole up face -> grain_jump must fire on its edges
    c = {s: new[s].copy() for s in SUF}
    c["up"] = to8(c["up"] + np.random.default_rng(20260926).normal(0, 1.0, c["up"].shape[:2])[..., None] * LSB) / 255.0
    run("grainy up face -> grain_jump", c, ["grain_jump"])
    json.dump(results, open(os.path.join(REPORT_DIR, "selftest_%s.json" % box.replace("/", "_")), "w"), indent=1)
    broken = [r for r in results if not r[1]]
    print("selftest: %s" % ("all controls behave" if not broken else "%d CONTROL(S) BROKEN" % len(broken)))
    return 1 if broken else 0


def cmd_pins(args):
    for p, want in ESR_PINS.items():
        print(p, sha256(open(p, "rb").read()) if os.path.exists(p) else "MISSING", "pinned", want)
    for box, cfg in BOXES.items():
        for key in ("src", "today", "retail", "retail512", "retail_ref"):
            for s, (pak, mem, want) in cfg.get(key, {}).items():
                got = sha256(read_member(pak, mem))
                print("%-20s %-6s %-3s %s %s" % (box, key, s, "ok " if got == want else "BAD", mem))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "check", "sheet", "selftest", "pins"])
    ap.add_argument("boxes", nargs="*")
    ap.add_argument("--rederive", action="store_true", help="check: also re-derive every face from the ESRGAN cache")
    ap.add_argument("--no-pak", action="store_true", help="build: stage and gate only")
    ap.add_argument("--pak", help="pak path to write (build) / verify (check); default: the mod folder's")
    ap.add_argument("--manifest", help="manifest path; default docs/tools/sky_hd_manifest.json")
    ap.add_argument("--stage", help="directory for staged TGAs, reports and sheets; default _hd_sky "
                                    "(the ESRGAN cache always stays in _hd_sky/cache)")
    a = ap.parse_args()
    global PAK_PATH, MANIFEST, OUT_DIR, REPORT_DIR, SHEET_DIR
    if a.pak:
        PAK_PATH = os.path.abspath(a.pak)
    if a.manifest:
        MANIFEST = os.path.abspath(a.manifest)
    if a.stage:
        OUT_DIR, REPORT_DIR, SHEET_DIR = [os.path.join(os.path.abspath(a.stage), d) for d in ("out", "report", "sheets")]
    for b in a.boxes:
        guard(b, "box")
    rc = {"build": cmd_build, "check": cmd_check, "sheet": cmd_sheet, "selftest": cmd_selftest, "pins": cmd_pins}[a.cmd](a)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
