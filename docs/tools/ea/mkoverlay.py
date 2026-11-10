#!/usr/bin/env python3
"""Test-only overlay pk3 of the pilot's mod scripts (from the `frontline` mod worktree) for a PRIVATE test
home. Never deployed, never released. usage: mkoverlay.py <mod_worktree> <out.pk3> <rel> [<rel> ...]"""
import os
import sys
import zipfile

src, out, rels = sys.argv[1], sys.argv[2], sys.argv[3:]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in sorted(rels):
        zi = zipfile.ZipInfo(rel, (2026, 11, 8, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        with open(os.path.join(src, *rel.split("/")), "rb") as f:
            z.writestr(zi, f.read())
print("overlay", out, len(rels), "files")
