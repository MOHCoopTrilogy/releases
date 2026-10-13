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
# where the harness runs' frames are kept. NOT on G: any more - that drive filled up on 2026-10-13 (bug-3777);
# the engine still writes its screenshots into the copy's home on G: during a run, the runner moves them here
RUNS = os.environ.get('DBS_RUNS', "C:/Users/curry/AppData/Local/Temp/claude/C--mohaa-coop-dev/7ee3b4ee-deea-4563-b7bc-c7746a82f4e9/scratchpad/dbs/runs")
