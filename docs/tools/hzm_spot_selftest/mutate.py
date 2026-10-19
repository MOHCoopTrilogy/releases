"""mutate.py - write deliberately BROKEN copies of tr_hzm_spot.c for build.bat's proof step.

A self-test that cannot fail proves nothing (TRAPS T14 "a pass that cannot fail"). Each mutation below breaks one
invariant hzm_spot_selftest.c claims to check; build.bat compiles each copy and requires the test to FAIL.

    python mutate.py <tr_hzm_spot.c> <out_dir>      -> writes <out_dir>/mut_<n>.c, prints their names
"""
import os
import sys

MUTATIONS = [
    # the tag match is what stops a carrier turning a muzzle flash into a cone (vet F15)
    ("tag-match", "if ( dl->hzmSpot != HZM_SPOT_PENDING || dl->hzmTag != tag ) {",
     "if ( dl->hzmSpot == HZM_SPOT_READY ) {"),
    # every add must zero the spot fields (the slots are reused per frame)
    ("zero-on-add", "void R_HZM_SpotBeginLight( dlight_t *dl, int type, qboolean isSpot ) {\n\tR_HZM_SpotClearLight( dl );",
     "void R_HZM_SpotBeginLight( dlight_t *dl, int type, qboolean isSpot ) {"),
    # spot-or-nothing: a pending light must be removed
    ("compact", "if ( dlights[i].hzmSpot == HZM_SPOT_PENDING ) {", "if ( 0 ) {"),
    # the non-spot factor must be exactly 1.0f
    ("factor-1", "\tif ( dl->hzmSpot != HZM_SPOT_READY ) {\n\t\treturn 1.0f;\n\t}\n\tVectorSubtract( point, dl->origin, v );",
     "\tif ( dl->hzmSpot != HZM_SPOT_READY ) {\n\t\treturn 0.999f;\n\t}\n\tVectorSubtract( point, dl->origin, v );"),
    # the cull must stay conservative (drop the asin(r/d) widening)
    ("cull", "return ( c >= cosOuter * cosA - sinO * sinA ) ? qtrue : qfalse;", "return ( c >= cosOuter ) ? qtrue : qfalse;"),
]


def main():
    src, out = sys.argv[1], sys.argv[2]
    raw = open(src, "rb").read()
    crlf = raw.count(b"\r\n") > raw.count(b"\n") - raw.count(b"\r\n")
    text = raw.decode("latin-1").replace("\r\n", "\n")
    os.makedirs(out, exist_ok=True)
    for n, (name, find, repl) in enumerate(MUTATIONS):
        if text.count(find) != 1:
            raise SystemExit("mutate.py: anchor for %s found %d times - update the mutation" % (name, text.count(find)))
        t = text.replace(find, repl)
        if crlf:
            t = t.replace("\n", "\r\n")
        p = os.path.join(out, "mut_%d_%s.c" % (n, name))
        open(p, "wb").write(t.encode("latin-1"))
        print(p)


if __name__ == "__main__":
    main()
