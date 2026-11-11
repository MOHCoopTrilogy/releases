"""strip_pak_entry.py - bug-10899: rewrite a pk3 without one entry (models/player/base/anims_shared.txt by default),
every other entry copied byte-for-byte with its original compression and timestamp.

    python strip_pak_entry.py <in.pk3> <out.pk3> [entry]
"""
import shutil
import sys
import zipfile

src, dst = sys.argv[1], sys.argv[2]
entry = (sys.argv[3] if len(sys.argv) > 3 else "models/player/base/anims_shared.txt").lower()
n = dropped = 0
with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst + ".tmp", "w") as zo:
    for info in zi.infolist():
        if info.filename.lower() == entry:
            dropped += 1
            continue
        with zi.open(info) as f, zo.open(info, "w") as g:
            shutil.copyfileobj(f, g, 1 << 20)
        n += 1
with zipfile.ZipFile(dst + ".tmp") as z:
    assert z.testzip() is None
import os
os.replace(dst + ".tmp", dst)
print("%s -> %s: %d entries kept, %d dropped (%s)" % (src, dst, n, dropped, entry))
