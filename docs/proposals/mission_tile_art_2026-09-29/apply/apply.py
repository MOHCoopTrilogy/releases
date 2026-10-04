"""apply.py - install the mission-tile art into the live trees. STAGED ONLY: nothing here has been run for real.

    python apply/apply.py --check     # verify everything, change nothing (exit 1 on any failure)
    python apply/apply.py             # apply (only after --check passes and the user says so; the game must be closed
                                      # before build.ps1, as always)

What it does, in order:
  1. mod wiring  apply/mod/ui/** -> hzm-mohaa-coop-mod/ui/** (byte copies; each generated file kept its live file's line
                 endings). REFUSES if any live file changed since tools/gen_wiring.py read it (apply/base.json md5s):
                 re-run gen_wiring.py then.
  2. art         set/game/*.jpg (67 x {c,s} cards + 67 x {c,s} prints) -> docs/tools/assets/tileart/
  3. pak tool    apply/gen_tileart_pak.py -> docs/tools/gen_tileart_pak.py, then `gen_tileart_pak.py build`
                 (-> hzm-mohaa-coop-mod/zzzzzzzzzz_coop_tileart.pk3)
  4. build.ps1   + the `gen_tileart_pak.py check` gate after the loadart gate, + the deploy copy after the loadart copy
     publish_release.ps1  + the stage line after the loadart stage line
     (both files are UTF-8 BOM + CRLF; inserted text uses CRLF; each anchor must occur exactly once)
Nothing is deployed: build.ps1 does that, when the user runs it.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
ROOT = r"C:\mohaa-coop-dev"
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
ASSETS = os.path.join(ROOT, "docs", "tools", "assets", "tileart")
GAME = os.path.join(PROP, "set", "game")

BUILD_GATE_ANCHOR = ('if ($LASTEXITCODE -ne 0) { Write-Host "BUILD BLOCKED by gen_loadart_pak check - regenerate with: python '
                     'docs/tools/gen_loadart_pak.py build" -ForegroundColor Red; exit 1 }\r\n')
BUILD_GATE = ('# [mission tile art, bug-3274] The coop mission-select tile art ships in its own out-of-band pak (gen_tileart_pak.py,\r\n'
              '# sources docs/tools/assets/tileart); `check` = byte-identical to a rebuild and every image the coop_start cfgs name.\r\n'
              'python "C:\\mohaa-coop-dev\\docs\\tools\\gen_tileart_pak.py" check\r\n'
              'if ($LASTEXITCODE -ne 0) { Write-Host "BUILD BLOCKED by gen_tileart_pak check - regenerate with: python '
              'docs/tools/gen_tileart_pak.py build" -ForegroundColor Red; exit 1 }\r\n')
BUILD_DEPLOY_ANCHOR = ('        Write-Host "  Deployed loading-art pak -> $destDir"\r\n    }\r\n')
BUILD_DEPLOY = ('    # [mission tile art, bug-3274] Coop mission-select tile art (textures/mohmenu/hzmtile/, 512 jpg). Out of the mod\r\n'
                '    # tree for the same reason as the loading art (bug-3251). Listed in publish_release.ps1 in the same change.\r\n'
                "    $tileartPak = Join-Path $srcDir 'zzzzzzzzzz_coop_tileart.pk3'\r\n"
                '    if (Test-Path $tileartPak) {\r\n'
                "        Copy-Item -Path $tileartPak -Destination (Join-Path $destDir 'zzzzzzzzzz_coop_tileart.pk3') -Force\r\n"
                '        Write-Host "  Deployed tile-art pak -> $destDir"\r\n'
                '    }\r\n')
PUB_ANCHOR = '$stage["home/maintt/zzzzzzzzzz_coop_loadart.pk3"]  = "$mod\\zzzzzzzzzz_coop_loadart.pk3"\r\n'
PUB = ('# [mission tile art, bug-3274] Coop mission-select tile art (docs/tools/gen_tileart_pak.py) - copied by build.ps1 the\r\n'
       '# same way; out of the assets_tex pk3 so it is not re-downloaded.\r\n'
       '$stage["home/maintt/zzzzzzzzzz_coop_tileart.pk3"]  = "$mod\\zzzzzzzzzz_coop_tileart.pk3"\r\n')


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def plan_patch(path, anchor, insert, fails):
    b = open(path, "rb").read()
    t = b.decode("utf-8-sig")
    bom = b[:3] == b"\xef\xbb\xbf"
    if insert in t:
        fails.append("%s: already applied" % os.path.basename(path))
        return None
    n = t.count(anchor)
    if n != 1:
        fails.append("%s: anchor found %d times (want 1): %r" % (os.path.basename(path), n, anchor[:60]))
        return None
    t2 = t.replace(anchor, anchor + insert)
    out = (b"\xef\xbb\xbf" if bom else b"") + t2.encode("utf-8")
    assert out.count(b"\r\n") == len(out.split(b"\n")) - 1, "line endings would mix"
    return out


def check():
    fails = []
    base = json.load(open(os.path.join(HERE, "base.json")))
    for rel, h in base.items():
        live = os.path.join(MOD, rel.replace("/", os.sep))
        if not os.path.exists(live):
            fails.append("live file missing: " + rel)
        elif md5(live) != h:
            fails.append("live %s changed since gen_wiring.py read it - re-run tools/gen_wiring.py" % rel)
        if not os.path.exists(os.path.join(HERE, "mod", rel.replace("/", os.sep))):
            fails.append("generated file missing: " + rel)
    # art: every card the generated cfgs name + its print, all present
    import re
    want = set()
    for rel in base:
        if rel.startswith("ui/coop_start/"):
            want |= set(re.findall(r"textures/mohmenu/hzmtile/([a-z0-9_]+)", open(os.path.join(HERE, "mod", rel), encoding="latin-1").read()))
    have = {f[:-4] for f in os.listdir(GAME)} if os.path.isdir(GAME) else set()
    miss = sorted(n for n in want if n not in have or "print_" + n not in have)
    if miss:
        fails.append("%d of %d tile textures (card or print) not built yet, e.g. %s" % (len(miss), len(want), miss[:6]))
    patches = {
        "build.ps1 gate": (os.path.join(ROOT, "build.ps1"), BUILD_GATE_ANCHOR, BUILD_GATE),
        "publish stage": (os.path.join(ROOT, "publish_release.ps1"), PUB_ANCHOR, PUB),
    }
    out = {}
    for k, (p, a, ins) in patches.items():
        out[p] = plan_patch(p, a, ins, fails)
    if out.get(os.path.join(ROOT, "build.ps1")) is not None:
        t = out[os.path.join(ROOT, "build.ps1")].decode("utf-8-sig")
        if t.count(BUILD_DEPLOY_ANCHOR) != 1:
            fails.append("build.ps1: deploy anchor found %d times" % t.count(BUILD_DEPLOY_ANCHOR))
        else:
            t = t.replace(BUILD_DEPLOY_ANCHOR, BUILD_DEPLOY_ANCHOR + BUILD_DEPLOY)
            out[os.path.join(ROOT, "build.ps1")] = b"\xef\xbb\xbf" + t.encode("utf-8")
    return fails, out


def main():
    fails, patched = check()
    for f in fails:
        print("FAIL", f)
    if "--check" in sys.argv:
        print("check", "OK - apply would copy %d wiring files, the art, the pak tool, and patch build.ps1 + publish_release.ps1"
              % len(json.load(open(os.path.join(HERE, "base.json")))) if not fails else "FAILED")
        return 1 if fails else 0
    if fails:
        return 1
    base = json.load(open(os.path.join(HERE, "base.json")))
    for rel in base:
        shutil.copyfile(os.path.join(HERE, "mod", rel.replace("/", os.sep)), os.path.join(MOD, rel.replace("/", os.sep)))
    os.makedirs(ASSETS, exist_ok=True)
    for f in os.listdir(GAME):
        shutil.copyfile(os.path.join(GAME, f), os.path.join(ASSETS, f))
    shutil.copyfile(os.path.join(HERE, "gen_tileart_pak.py"), os.path.join(ROOT, "docs", "tools", "gen_tileart_pak.py"))
    for p, b in patched.items():
        open(p, "wb").write(b)
    rc = subprocess.call([sys.executable, os.path.join(ROOT, "docs", "tools", "gen_tileart_pak.py"), "build"])
    print("applied; pak build exit", rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
