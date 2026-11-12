# PyInstaller spec for hzmconv (one-folder). Build:  pyinstaller --noconfirm --distpath <out> hzmconv.spec
# Bundles OUR converter code + the Python runtime, numpy and Pillow (BSD/HPND). vgmstream-cli (ISC-style),
# realesrgan-ncnn-vulkan (MIT, BSD-3 weights) and an LGPL-only ffmpeg go beside it in tools/ with their licences.
# No Frontline or European Assault bytes, ever.
import os
HERE = os.path.abspath(".")
mods = ["flconvert", "flcore", "flbsp", "flpack", "flseam", "flgeom", "flvis", "flaudio", "shpx", "xdvdfs", "viv",
        "flmovies", "flupscale", "flhd"]
# [v1.10.69] stdlib the European Assault modules (docs/tools/ea, shipped as source in _internal/ea) use beyond Frontline's
mods += ["bisect", "statistics", "wave", "fnmatch", "tempfile", "subprocess", "shutil", "importlib", "importlib.machinery",
         "glob", "argparse", "zlib", "collections", "socket", "hashlib", "json"]
a = Analysis(["hzmconv.py"], pathex=[HERE], hiddenimports=mods,
             datas=[("fl_levels.json", "."), ("fl_texmap.json", "."), ("fl_modelmap.json", "."), ("hd", "hd")],
             excludes=["tkinter", "matplotlib", "scipy", "pandas", "IPython"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="hzmconv", console=True, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="hzmconv")
