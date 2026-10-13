"""zip the staged shotgun files (skd, tiks, bead shader / texture, shotgun textures, shotgun clips) into a small pk3 for the offline tools"""
import sys, os, zipfile
A = r'C:\mohaa-coop-dev\docs\proposals\ads_twohand_2026-10-11\heavy\assets'
out = sys.argv[1]
n = 0
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for d, _, fs in os.walk(A):
        for f in fs:
            p = os.path.join(d, f); rel = os.path.relpath(p, A).replace(os.sep, '/')
            if 'shotgun' in rel.lower() or 'bead' in rel.lower():
                z.write(p, rel); n += 1
print(out, n, 'files')
