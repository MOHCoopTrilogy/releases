"""finishes2 (v1.10.68): the shared reader of docs/tools/finishes2.tsv and of the finishes2 BUILD (the out-of-band pak).

The build is made by docs/proposals/finishes2_2026-11-09/tools/fs2_build.py + fs2_finish2.py into a staging dir; it ships as its
own pak, zzzzzzzzzz_coop_finishes_hd.pk3, which sits next to the other out-of-band paks in the mod base checkout root (build.ps1
deploys it, publish_release.ps1 releases it). Every generator that needs the finish table or the per-gun rows reads them here.

    BUILD = $HZM_FS2_BUILD, else H:\\hzm_work\\newguns\\fs2_build (the shipped v1.10.68 build), else H:\\hzm_work\\finishes2_build
    PAK   = $HZM_FS2_PAK, else <base mod>/zzzzzzzzzz_coop_finishes_hd.pk3 when it exists, else <BUILD>/zzzzzzzzzz_coop_finishes_hd.pk3
"""
import io
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TSV = os.path.join(HERE, "finishes2.tsv")
PAK_NAME = "zzzzzzzzzz_coop_finishes_hd.pk3"
# [v1.10.68 integration] the shipped pak is the newguns build (936 rows: + MP 28 / Panzerfaust, no Bren); finishes2_build is the
# older 910-row staging, and a no-env `gen_skins check` against it reported DRIFT (a `fs2 write` would have dropped the new guns' rows)
_BUILD_CANDIDATES = [os.path.join("H:" + os.sep, "hzm_work", "newguns", "fs2_build"), os.path.join("H:" + os.sep, "hzm_work", "finishes2_build")]
BUILD = os.environ.get("HZM_FS2_BUILD") or next((d for d in _BUILD_CANDIDATES if os.path.isfile(os.path.join(d, "rows.tsv"))), _BUILD_CANDIDATES[-1])
FID_MIN, FID_MAX = 40, 59          # the finishes2 fid band (README: finish slots 40+; 8-19 are model variants)


def table():
    """[{fid, key, name, rung, slow, kind, credit, history}] in fid order"""
    rows = []
    for line in io.open(TSV, encoding="utf-8"):
        line = line.rstrip("\r\n")
        if not line or line.startswith("#") or line.startswith("fid\t"):
            continue
        f = line.split("\t")
        assert len(f) == 8, "finishes2.tsv: 8 columns expected: %r" % line[:60]
        r = dict(fid=int(f[0]), key=f[1], name=f[2], rung=int(f[3]), slow=int(f[4]), kind=f[5], credit=f[6], history=f[7])
        assert FID_MIN <= r["fid"] <= FID_MAX, r
        assert len(r["name"]) <= 14 and r["name"] == r["name"].upper(), r["name"]
        assert r["rung"] <= 750 and r["slow"] <= 750, "challenge targets are capped at 750"
        for bad in ('"', ";", "{", "}", "\u2014"):
            assert bad not in r["history"] + r["credit"], "finishes2.tsv: %r in fid %d text" % (bad, r["fid"])
        rows.append(r)
    rows.sort(key=lambda r: r["fid"])
    assert len({r["fid"] for r in rows}) == len(rows) and len({r["key"] for r in rows}) == len(rows)
    return rows


def by_fid():
    return {r["fid"]: r for r in table()}


def fids():
    return [r["fid"] for r in table()]


def pak_path(base_mod=None):
    p = os.environ.get("HZM_FS2_PAK")
    if p:
        return p
    if base_mod:
        b = os.path.join(base_mod, PAK_NAME)
        if os.path.exists(b):
            return b
    return os.path.join(BUILD, PAK_NAME)


def build_rows(build=None):
    """[(give, fid, key, variant tik, rank)] from the build's rows.tsv (one row per gun x finish)"""
    p = os.path.join(build or BUILD, "rows.tsv")
    out = []
    for i, line in enumerate(io.open(p, encoding="utf-8")):
        line = line.rstrip("\r\n")
        if i == 0 or not line:
            continue
        g, f, k, v, r = line.split("\t")
        out.append((g, int(f), k, v, int(r)))
    return out


def pak_index(path):
    """{lower name: name} of the pak, and a reader"""
    z = zipfile.ZipFile(path)
    return z, {n.lower(): n for n in z.namelist()}
