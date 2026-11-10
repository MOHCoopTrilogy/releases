"""ne_shp.py - a minimal ESRI .shp reader (Polygon / PolyLine, types 3/5/13/15), enough for the Natural Earth 1:50m layers.
Returns a list of shapes, each a list of parts, each a list of (lon, lat).  No dependencies (pyshp is not installed here and the data
should not pull a package in).  Run untrusted-data tools with python -I."""
import struct


def read(path, bbox=None):
    """bbox = (lon0, lat0, lon1, lat1): keep only shapes whose own bbox meets it."""
    data = open(path, "rb").read()
    assert struct.unpack(">i", data[0:4])[0] == 9994, "not a shapefile"
    off = 100
    out = []
    while off + 8 <= len(data):
        _num, clen = struct.unpack(">ii", data[off:off + 8])
        rec = data[off + 8: off + 8 + clen * 2]
        off += 8 + clen * 2
        st = struct.unpack("<i", rec[:4])[0]
        if st == 0:
            continue
        assert st in (3, 5, 13, 15), st
        x0, y0, x1, y1 = struct.unpack("<4d", rec[4:36])
        if bbox and (x1 < bbox[0] or x0 > bbox[2] or y1 < bbox[1] or y0 > bbox[3]):
            continue
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = list(struct.unpack("<%di" % nparts, rec[44:44 + 4 * nparts])) + [npts]
        p0 = 44 + 4 * nparts
        pts = struct.unpack("<%dd" % (2 * npts), rec[p0:p0 + 16 * npts])
        shape = []
        for i in range(nparts):
            a, b = parts[i], parts[i + 1]
            shape.append([(pts[2 * k], pts[2 * k + 1]) for k in range(a, b)])
        out.append(shape)
    return out


def read_dbf(path):
    """dBASE III records as a list of dicts (strings stripped); enough for Natural Earth attribute tables."""
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[4:8])[0]
    hlen, rlen = struct.unpack("<HH", data[8:12])
    fields, off = [], 32
    while data[off] != 0x0D:
        name = data[off:off + 11].split(b"\0")[0].decode("latin-1")
        fields.append((name, data[off + 16]))
        off += 32
    out = []
    for i in range(n):
        r = data[hlen + i * rlen: hlen + (i + 1) * rlen]
        pos, row = 1, {}
        for name, ln in fields:
            row[name] = r[pos:pos + ln].replace(bytes(1), b"").decode("utf-8", "replace").strip()
            pos += ln
        out.append(row)
    return out


def read_with_attrs(path, bbox=None):
    """[(parts, attrs)] - the .shp shapes paired with their .dbf rows (bbox filter applied after pairing)."""
    shapes = read(path)
    rows = read_dbf(path[:-4] + ".dbf")
    out = []
    for sh, row in zip(shapes, rows):
        if bbox:
            xs = [p[0] for part in sh for p in part]
            ys = [p[1] for part in sh for p in part]
            if not xs or max(xs) < bbox[0] or min(xs) > bbox[2] or max(ys) < bbox[1] or min(ys) > bbox[3]:
                continue
        out.append((sh, row))
    return out
