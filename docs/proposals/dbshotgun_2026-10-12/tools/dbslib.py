"""Shared paths + the mod's existing tool libraries (read-only reuse) for the double-barrel shotgun proposal.

    import dbslib as L      ->  L.vfs, L.skdlib, L.gungeo  (ironsights_2026-09-28/tools: live-install pk3 reader, SKD/SKC
                                reader, tik/gun loader),  L.AP (ads_bolt add_part: bone_block)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
ASSETS = os.path.join(PROP, 'assets')
MEDIA = os.path.join(PROP, 'media')
BUILD = os.path.join(PROP, 'build')
SRC = os.path.join(PROP, 'source', 'Shotgun')
DOCS = os.path.dirname(os.path.dirname(PROP))
IS = os.path.join(DOCS, 'proposals', 'ironsights_2026-09-28', 'tools')
if IS not in sys.path:
    sys.path.insert(1, IS)
import vfs, skdlib, gungeo  # noqa: E402
