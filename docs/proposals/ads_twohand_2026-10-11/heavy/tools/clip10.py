"""scratch (HARNESS ONLY, never staged): a test overlay whose weapon tik has a small clip, so an emptied-gun reload can be
captured without firing a 120-round belt (the view walks up 50 deg).   python clip10.py <in.pk3> <out.pk3> <tik in pak> <n>"""
import sys, re, zipfile
src, dst, tik, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
b = zipfile.ZipFile(src)
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
    hit = 0
    for i in b.infolist():
        d = b.read(i.filename)
        if i.filename.lower() == tik.lower():
            t = d.decode('latin-1')
            t, k = re.subn(r'(\n\s*clipsize\s+)\d+', lambda m: m.group(1) + str(n), t)
            assert k == 1, k
            d = t.encode('latin-1'); hit += 1
        z.writestr(i.filename, d)
    assert hit == 1, hit
print('wrote', dst, 'clipsize', n)
