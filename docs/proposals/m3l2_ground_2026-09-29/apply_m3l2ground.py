# -*- coding: utf-8 -*-
"""Apply the m3l2 ground proposal (docs/proposals/m3l2_ground_2026-09-29).

    python apply_m3l2ground.py --check              (default) rebuild + byte-compare the staged pak, run every gate,
                                                    and verify every anchor below exists exactly once - writes nothing
    python apply_m3l2ground.py --apply [--base DIR] do it: DIR defaults to C:\\mohaa-coop-dev (rehearse on a copy first)

What --apply writes (and nothing else; build.ps1 is NOT run, nothing is deployed):
  1. <base>\\hzm-mohaa-coop-mod\\zzzzzzzzzz_coop_m3l2ground.pk3   the staged pak (build.ps1 never packs a root .pk3)
  2. <base>\\build.ps1            a deploy block after the overrides-pak block (copies the pak like its siblings)
  3. <base>\\publish_release.ps1  a staging line after the coop_fixes line
Both text edits are binary-safe (the file's own line ending + BOM kept), anchored on text that must occur exactly
once, idempotent (a second --apply changes nothing), and rolled back if any later step fails.
Run build.ps1 yourself afterwards, with the game closed.
"""
import argparse, hashlib, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAK = "zzzzzzzzzz_coop_m3l2ground.pk3"
STAGED = os.path.join(HERE, "staged", PAK)
GEN = os.path.join(HERE, "tools", "gen_m3l2ground_pak.py")

BUILD_ANCHOR = """        Write-Host "  Deployed overrides pak -> $destDir"
    }
"""
BUILD_BLOCK = """    # [2026-09-29, m3l2 ground] m3l2's courtyard / barnyard / road ground (docs/proposals/m3l2_ground_2026-09-29,
    # built by its tools/gen_m3l2ground_pak.py). Ships maps/m3l2.bsp with a patched SHADER lump only (road faces ->
    # textures/hzm_m3l2/road, courtyard faces -> farmyard, late-barn barnyard faces -> farmyard_b) plus those NEW-name textures and
    # scripts/hzm_m3l2_ground.shader. The only other m3l2.bsp is retail main/Pak5.pk3, so any maintt pak wins. The BSP
    # header checksum field is untouched (CM_Checksum returns it as-is), so an unpatched client still joins and just sees
    # the old ground. Listed in publish_release.ps1's staging.
    $m3l2GroundPak = Join-Path $srcDir 'zzzzzzzzzz_coop_m3l2ground.pk3'
    if (Test-Path $m3l2GroundPak) {
        Copy-Item -Path $m3l2GroundPak -Destination (Join-Path $destDir 'zzzzzzzzzz_coop_m3l2ground.pk3') -Force
        Write-Host "  Deployed m3l2 ground pak -> $destDir"
    }
"""
PUB_ANCHOR = """$stage["home/maintt/zzzzzzzzzz_coop_fixes.pk3"]  = "$mod\\zzzzzzzzzz_coop_fixes.pk3"
"""
PUB_BLOCK = """# [2026-09-29, m3l2 ground] m3l2 courtyard/barnyard/road ground + patched m3l2.bsp (docs/proposals/m3l2_ground_2026-09-29)
# - copied by build.ps1 the same way. Ship it to players and servers together (pure-pak alignment; the map checksum field is unchanged).
$stage["home/maintt/zzzzzzzzzz_coop_m3l2ground.pk3"]  = "$mod\\zzzzzzzzzz_coop_m3l2ground.pk3"
"""


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def plan_edit(path, anchor, block):
    """-> (new bytes or None if already applied). Keeps BOM and the file's own EOL."""
    b = open(path, "rb").read()
    eol = b"\r\n" if b"\r\n" in b else b"\n"
    a = anchor.encode("utf-8").replace(b"\n", eol)
    k = block.encode("utf-8").replace(b"\n", eol)
    if k in b:
        return None
    n = b.count(a)
    if n != 1:
        raise SystemExit("anchor found %d times in %s (need exactly 1) - refusing" % (n, path))
    return b.replace(a, a + k)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    ap.add_argument("--base", default=r"C:\mohaa-coop-dev")
    a = ap.parse_args()
    r = subprocess.run([sys.executable, GEN, "check", "--pak", STAGED], cwd=os.path.dirname(GEN))
    if r.returncode != 0:
        raise SystemExit("staged pak failed its check - nothing applied")
    build = os.path.join(a.base, "build.ps1")
    pub = os.path.join(a.base, "publish_release.ps1")
    dst = os.path.join(a.base, "hzm-mohaa-coop-mod", PAK)
    nb, npub = plan_edit(build, BUILD_ANCHOR, BUILD_BLOCK), plan_edit(pub, PUB_ANCHOR, PUB_BLOCK)
    print("build.ps1:", "already applied" if nb is None else "block will be inserted")
    print("publish_release.ps1:", "already applied" if npub is None else "line will be inserted")
    print("pak:", ("present, identical" if os.path.exists(dst) and sha(dst) == sha(STAGED) else
                   "present, DIFFERENT - will be replaced" if os.path.exists(dst) else "will be copied"), "->", dst)
    if not a.apply:
        print("CHECK OK (nothing written)")
        return
    backups = []
    try:
        for path, new in ((build, nb), (pub, npub)):
            if new is None:
                continue
            bak = path + ".pre_m3l2ground"
            shutil.copyfile(path, bak)
            backups.append((path, bak))
            open(path, "wb").write(new)
        if os.path.exists(dst):
            shutil.copyfile(dst, dst + ".pre_m3l2ground")
            backups.append((dst, dst + ".pre_m3l2ground"))
        else:
            backups.append((dst, None))
        shutil.copyfile(STAGED, dst)
        assert sha(dst) == sha(STAGED)
        for path, new in ((build, nb), (pub, npub)):
            if new is not None:
                assert open(path, "rb").read() == new
    except BaseException:
        for path, bak in reversed(backups):
            if bak is None:
                if os.path.exists(path):
                    os.remove(path)
            else:
                shutil.copyfile(bak, path)
        print("ROLLED BACK")
        raise
    for path, bak in backups:
        if bak and os.path.exists(bak):
            os.remove(bak)
    print("APPLIED. Next: close the game, run .\\build.ps1, then check the log sweep.")


if __name__ == "__main__":
    main()
