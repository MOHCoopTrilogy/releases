"""mutate.py - deliberately BROKEN copies of tr_hzm_clouds_pure.h for build.bat's proof step (a test that cannot fail
proves nothing - TRAPS T14). Each breaks one thing vcl_selftest.c claims to check.
    python mutate.py <tr_hzm_clouds_pure.h> <out_dir>   -> writes <out_dir>/m<n>/tr_hzm_clouds_pure.h, prints the dirs
"""
import os
import sys

MUTATIONS = [
    ("hash", "h *= 0x7feb352du;", "h *= 0x7feb352cu;"),
    ("half-even", "return ( fmodf( f, 2.0f ) == 0.0f ) ? f : f + 1.0f;", "return f + 1.0f;"),
    ("noise-weights", "double f = 0.625 * w[i] + 0.25 * w[n3 + i] + 0.125 * w[2 * n3 + i];",
     "double f = 0.625 * w[i] + 0.26 * w[n3 + i] + 0.125 * w[2 * n3 + i];"),
    ("noise-mip-order", "nxt[( i * h + j ) * h + k] = 0.125f * s;", "nxt[( i * h + j ) * h + k] = s / 8.0f + 1e-7f;"),
    ("worley-wrap", "return r < 0 ? r + m : r;", "return r < 0 ? -r : r;"),
    ("grey-weights", "rgba[0] * 19595 + rgba[1] * 38470 + rgba[2] * 7471", "rgba[0] * 7471 + rgba[1] * 38470 + rgba[2] * 19595"),
    ("grey-round", "* 7471 + 0x8000 ) >> 16", "* 7471 ) >> 16"),
    ("cov-box", "nxt[b * x2 + a] = 0.25f * s;", "nxt[b * x2 + a] = 0.25f * s + 0.0001f;"),
    ("max-chain", "if ( mx[( 2 * b + 1 ) * x + 2 * a + 1] > m ) m = mx[( 2 * b + 1 ) * x + 2 * a + 1];", ""),
    ("deny-sml", '"e3l2", "e3l2_sml", 0 };', '"e3l2", 0 };'),
    ("deny-name", '"dday2", "e3l1sky", "e3l2sky", "omaha", "inteldim", 0 };', '"dday2", "e3l1sky", "omaha", "inteldim", 0 };'),
    ("scroll", "a = a - floor( a );", "a = a - floor( a ) + 1e-3;"),
    # v1.1 the procedural profile
    ("proc-rank", "out[i] = (unsigned char)R_HZM_VclRintD( ( r > 1.0 ? 1.0 : r ) * 255.0 );", "out[i] = (unsigned char)( val[i] / 257.0f );"),
    ("proc-wrap", "(unsigned int)R_HZM_VclMod( cx, c ), (unsigned int)R_HZM_VclMod( cy, c ), 1u, seed );",
     "(unsigned int)cx, (unsigned int)cy, 1u, seed );"),
    ("proc-family-omaha", '{ "env/m5l2",          "stratus", ', '{ "env/dday2",         "stratus", '),
]


def main():
    src, out = sys.argv[1], sys.argv[2]
    raw = open(src, "rb").read().decode("latin-1")
    for i, (name, a, b) in enumerate(MUTATIONS):
        assert raw.count(a) == 1, (name, raw.count(a))
        d = os.path.join(out, "m%d_%s" % (i, name))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "tr_hzm_clouds_pure.h"), "wb").write(raw.replace(a, b).encode("latin-1"))
        print(d)


if __name__ == "__main__":
    main()
