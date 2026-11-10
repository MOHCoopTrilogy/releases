"""Safe unzip of an untrusted model download: python -I unz.py <zip> <outdir>"""
import sys, zipfile, os
z = zipfile.ZipFile(sys.argv[1])
out = os.path.abspath(sys.argv[2])
for i in z.infolist():
    dst = os.path.abspath(os.path.join(out, i.filename))
    assert dst.startswith(out + os.sep) or dst == out, i.filename
    print(i.file_size, i.filename)
z.extractall(out)
