#!/usr/bin/env python3
"""Build the shipped bring-your-own-disc converter: hzmconv.zip (updater payload, unpacked beside the exe by
installer/byo_convert.ps1 on first use).

  python docs/tools/frontline/build_hzmconv.py [--out DIR]

1. PyInstaller one-folder build of hzmconv.py (hzmconv.spec): OUR converter code + Python, numpy, Pillow.
2. tools/ beside it, from the pinned local builds (INTEGRATION.md section 10):
     tools/ffmpeg/     our minimal LGPL-2.1 ffmpeg 8.1 (+ COPYING.LGPLv2.1, CONFIGURE_LINE.txt, SOURCE.txt, build.sh)
     tools/vgmstream/  the MPEG-enabled vgmstream-cli shared with European Assault (+ COPYING) and libmpg123-0.dll
                       (LGPL-2.1, a separate DLL a user can swap; + COPYING.mpg123, SOURCE.txt)
   The shared MPEG build was cleared for Frontline on 2026-11-09: the converted 1_1 pak is byte-identical with the
   plain build (sha256 eb590027...18a9 both).
3. LICENSES/: Python (PSF), numpy (BSD + its bundled notices), Pillow (MIT-CMU/HPND); NOTICE.txt lists everything.
4. A deterministic zip (sorted entries, fixed timestamps), so an unchanged build hashes the same and the updater's
   per-file sha256 reuse does not re-download it.

Refuses to package anything that is not ours or a listed runtime: no disc data can be in the tree (byo_guard.py scan).
"""
import argparse
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
FFMPEG = r"H:\hzm_work\frontline_tools\ffmpeg_src"            # build.sh, CONFIGURE_LINE.txt, build/ffmpeg.exe
FFMPEG_SRC_TXT = r"H:\hzm_work\frontline_tools\hzmconv_build\dist\hzmconv\tools\ffmpeg\SOURCE.txt"
VGM = r"H:\hzm_work\ea_tools_dl\vgmstream_mpeg"                 # MPEG-enabled vgmstream (EA agent's build)
MPG123 = r"H:\hzm_work\ea_tools_dl\mpg123\mpg123-1.32.12"
ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=r"H:\hzm_work\frontline_tools\hzmconv_release")
    o = ap.parse_args()
    work, dist = os.path.join(o.out, "work"), os.path.join(o.out, "dist")
    for d in (work, dist):
        shutil.rmtree(d, ignore_errors=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
                    "--workpath", work, "--distpath", dist, "hzmconv.spec"], cwd=HERE, check=True)
    root = os.path.join(dist, "hzmconv")
    tools = os.path.join(root, "tools")

    # ffmpeg (LGPL-2.1, static, no external libraries)
    ff = os.path.join(tools, "ffmpeg")
    cp(os.path.join(FFMPEG, "build", "ffmpeg.exe"), os.path.join(ff, "ffmpeg.exe"))
    for n in ("CONFIGURE_LINE.txt", "build.sh"):
        cp(os.path.join(FFMPEG, n), os.path.join(ff, n))
    cp(os.path.join(FFMPEG, "ffmpeg-8.1", "COPYING.LGPLv2.1"), os.path.join(ff, "COPYING.LGPLv2.1"))
    cp(FFMPEG_SRC_TXT, os.path.join(ff, "SOURCE.txt"))
    cfg = open(os.path.join(ff, "CONFIGURE_LINE.txt"), encoding="latin-1").read()
    assert "--enable-gpl" not in cfg and "--enable-nonfree" not in cfg, "ffmpeg must stay LGPL-only"

    # vgmstream (ISC-style) + libmpg123 (LGPL-2.1, dynamic)
    vg = os.path.join(tools, "vgmstream")
    cp(os.path.join(VGM, "build", "cli", "Release", "vgmstream-cli.exe"), os.path.join(vg, "vgmstream-cli.exe"))
    cp(os.path.join(VGM, "build", "cli", "Release", "libmpg123-0.dll"), os.path.join(vg, "libmpg123-0.dll"))
    cp(os.path.join(VGM, "COPYING"), os.path.join(vg, "COPYING"))
    cp(os.path.join(MPG123, "COPYING"), os.path.join(vg, "COPYING.mpg123"))
    with open(os.path.join(vg, "SOURCE.txt"), "w", newline="\r\n") as f:
        f.write("vgmstream-cli: https://github.com/vgmstream/vgmstream (ISC-style licence, COPYING), built with MPEG support.\n"
                "libmpg123-0.dll: mpg123 1.32.12, LGPL-2.1 (COPYING.mpg123), built with MSVC x64, unmodified source:\n"
                "  https://www.mpg123.de/download/mpg123-1.32.12.tar.bz2 (GPG signature verified against Thomas Orgis' key)\n"
                "  It is a separate DLL: you may replace it with your own build of the same library.\n")

    # licences of the bundled Python runtime and packages
    lic = os.path.join(root, "LICENSES")
    py_lic = os.path.join(os.path.dirname(sys.executable), "LICENSE.txt")
    cp(py_lic, os.path.join(lic, "Python-PSF-LICENSE.txt"))
    import numpy
    import PIL
    for mod, name in ((numpy, "numpy"), (PIL, "Pillow")):
        site = os.path.dirname(os.path.dirname(mod.__file__))
        di = sorted(glob.glob(os.path.join(site, ("pillow" if name == "Pillow" else name) + "-*.dist-info")))
        # every licence/notice file the wheel carries (numpy bundles OpenBLAS / gfortran-runtime notices under licenses/)
        found = sorted(p for d in di for p in glob.glob(os.path.join(d, "**", "*"), recursive=True)
                       if os.path.isfile(p) and ("licen" in p.lower() or "copying" in p.lower() or "notice" in p.lower()))
        assert found, "no licence file for " + name
        for p in found:
            rel = os.path.relpath(p, di[0]).replace("\\", "/").replace("/", "_")
            cp(p, os.path.join(lic, name, rel))
    with open(os.path.join(root, "NOTICE.txt"), "w", newline="\r\n") as f:
        f.write("hzmconv - the MOH Coop Trilogy bring-your-own-disc converter.\n\n"
                "It converts missions from YOUR OWN Medal of Honor: Frontline / European Assault disc image, on your PC.\n"
                "It contains no data from those games. Our code; bundled third-party runtimes and their licences:\n"
                "  Python %s (PSF licence)            LICENSES/Python-PSF-LICENSE.txt\n"
                "  numpy %s (BSD-3, bundled notices)  LICENSES/numpy/\n"
                "  Pillow %s (MIT-CMU / HPND)         LICENSES/Pillow/\n"
                "  ffmpeg 8.1 (LGPL-2.1 or later)      tools/ffmpeg/ (COPYING.LGPLv2.1, SOURCE.txt, CONFIGURE_LINE.txt, build.sh)\n"
                "  vgmstream (ISC-style)               tools/vgmstream/COPYING\n"
                "  mpg123 1.32.12 (LGPL-2.1)           tools/vgmstream/COPYING.mpg123, SOURCE.txt\n"
                "No GPL component is included. (numpy's OpenBLAS DLL carries GCC runtime code, which the GCC Runtime\n"
                "Library Exception permits in any program; see LICENSES/numpy/licenses_LICENSE.txt.)\n" % (sys.version.split()[0], numpy.__version__, PIL.__version__))

    # [v1.10.69] European Assault: its own copies of the shared modules, as source, in _internal/ea (hzmconv.py
    # _ea_modules_first puts them ahead of the frozen Frontline set for an EA run). Only what hzmconv_ea imports.
    ea_src = os.path.join(os.path.dirname(HERE), "ea")
    need, todo = set(), ["hzmconv_ea"]
    import re
    while todo:
        m = todo.pop()
        f = os.path.join(ea_src, m + ".py")
        if m in need or not os.path.isfile(f):
            continue
        need.add(m)
        todo += re.findall(r"^\s*(?:import|from)\s+(\w+)", open(f, encoding="utf-8", errors="replace").read(), re.M)
    assert "hzmconv_ea" in need and "flconvert" in need, need
    ea_dst = os.path.join(root, "_internal", "ea")
    for m in sorted(need):
        cp(os.path.join(ea_src, m + ".py"), os.path.join(ea_dst, m + ".py"))
    for j in glob.glob(os.path.join(ea_src, "*.json")):
        cp(j, os.path.join(ea_dst, os.path.basename(j)))
    print("ea modules:", " ".join(sorted(need)))

    # nothing from a disc may be in here (it never should be: the tree is our code + the runtimes above)
    guard = os.path.join(os.path.dirname(HERE), "byo_guard.py")
    subprocess.run([sys.executable, guard, root], check=True)

    zp = os.path.join(o.out, "hzmconv.zip")
    names = []
    for d, _, fs in os.walk(root):
        for n in fs:
            p = os.path.join(d, n)
            names.append((os.path.relpath(p, root).replace("\\", "/"), p))
    names.sort()
    with zipfile.ZipFile(zp + ".tmp", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, p in names:
            zi = zipfile.ZipInfo(arc, ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(p, "rb") as f:
                z.writestr(zi, f.read())
    os.replace(zp + ".tmp", zp)
    print("hzmconv.zip  %d files  %.1f MB  sha256 %s" % (len(names), os.path.getsize(zp) / 2 ** 20, sha(zp)))
    print("  ffmpeg.exe       %s" % sha(os.path.join(ff, "ffmpeg.exe")))
    print("  vgmstream-cli    %s" % sha(os.path.join(vg, "vgmstream-cli.exe")))
    print("  libmpg123-0.dll  %s" % sha(os.path.join(vg, "libmpg123-0.dll")))


if __name__ == "__main__":
    main()
