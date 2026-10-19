/*
vcl_selftest.c - offline unit test for the volumetric clouds (plan 2.8 V2), no game client.

It compiles openmohaa-hzm-vcl/code/renderergl2/tr_hzm_clouds_pure.h UNCHANGED (every function the renderer uses to
build its noise, coverage and max-mip textures, the scroll wrap and the deny list) and checks it against reference
bytes the P0 twin wrote (make_refs.py):
  - noise: every mip level of the 64^3 Worley fBm, byte-exact, in GL's upload layout
  - coverage: PIL "L" of the HD layer, byte-exact; every quantised box mip, byte-exact
  - max chain: every level >= every level-0 texel it covers, and equal to the true block maximum
  - scroll wrap: at t = 0 .. 1e6 s the offset stays in [0, scale), and NS * SCS / NT * SCT are integers (seamless)
  - deny list: the Omaha maps + _sml, the user's m3l2 / m3l3, every Omaha box / shader name, and the 8 IN maps pass
    build.bat compiles, runs, then proves the test can FAIL on broken copies (mutate.py)
Every check prints nothing when it holds; the last line is the verdict.
    vcl_selftest.exe <refs_dir>
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "tr_hzm_clouds_pure.h"
#include "tr_hzm_clouds_profile.h"

static int g_fail, g_checks;
#define CHECK( cond, ... ) do { g_checks++; if ( !( cond ) ) { g_fail++; printf( "FAIL %s:%d: ", __FILE__, __LINE__ ); \
	printf( __VA_ARGS__ ); printf( "\n" ); } } while ( 0 )

static unsigned char *readall( const char *dir, const char *name, long *size ) {
	char path[1024];
	FILE *f;
	unsigned char *b;
	long n;

	snprintf( path, sizeof( path ), "%s/%s", dir, name );
	f = fopen( path, "rb" );
	if ( !f ) {
		printf( "FAIL: cannot open %s\n", path );
		exit( 2 );
	}
	fseek( f, 0, SEEK_END );
	n = ftell( f );
	fseek( f, 0, SEEK_SET );
	b = (unsigned char *)malloc( n ? n : 1 );
	fread( b, 1, n, f );
	fclose( f );
	*size = n;
	return b;
}

static int diffcount( const unsigned char *a, const unsigned char *b, long n, long *first ) {
	long i;
	int d = 0;

	*first = -1;
	for ( i = 0; i < n; i++ ) {
		if ( a[i] != b[i] ) {
			if ( *first < 0 ) *first = i;
			d++;
		}
	}
	return d;
}

static void test_noise( const char *dir ) {
	const int n0 = HZM_VCL_NOISEN;
	unsigned char *lvl0 = malloc( n0 * n0 * n0 ), *up = malloc( n0 * n0 * n0 );
	double *w = malloc( sizeof( double ) * n0 * n0 * n0 * 3 ), *fp = malloc( sizeof( double ) * 16 * 16 * 16 * 3 );
	float *cur = malloc( sizeof( float ) * n0 * n0 * n0 ), *nxt = malloc( sizeof( float ) * n0 * n0 * n0 );
	int n = n0, level = 0, i;

	R_HZM_VclNoiseBytes( n0, lvl0, w, fp );
	for ( i = 0; i < n0 * n0 * n0; i++ ) {
		cur[i] = (float)( lvl0[i] / 255.0 );
	}
	for ( ;; ) {
		char name[64];
		long size, first;
		unsigned char *ref;
		int d;

		R_HZM_VclNoiseQuantGL( cur, n, up );
		snprintf( name, sizeof( name ), "noise_l%d.bin", level );
		ref = readall( dir, name, &size );
		CHECK( size == (long)n * n * n, "noise level %d size %ld != %d", level, size, n * n * n );
		d = diffcount( up, ref, size, &first );
		CHECK( d == 0, "noise level %d: %d bytes differ from the twin (first at %ld: C %d twin %d)", level, d, first,
			first >= 0 ? up[first] : 0, first >= 0 ? ref[first] : 0 );
		free( ref );
		if ( n == 1 ) break;
		R_HZM_VclNoiseDown( cur, n, nxt );
		memcpy( cur, nxt, sizeof( float ) * ( n / 2 ) * ( n / 2 ) * ( n / 2 ) );
		n /= 2;
		level++;
	}
	CHECK( level == 6, "noise has %d levels below 0, want 6", level );
	free( lvl0 ); free( up ); free( w ); free( fp ); free( cur ); free( nxt );
}

static void test_coverage( const char *dir ) {
	long rsize, gsize, first;
	unsigned char *rgba = readall( dir, "cov_rgba.bin", &rsize );
	unsigned char *pil = readall( dir, "cov_grey.bin", &gsize );
	const int W = HZM_VCL_COVN;
	unsigned char *grey = malloc( W * W ), *up = malloc( W * W ), *mx = malloc( W * W ), *mxn = malloc( W * W );
	float *cur = malloc( sizeof( float ) * W * W ), *nxt = malloc( sizeof( float ) * W * W );
	int i, d, x, y, level;

	CHECK( rsize == (long)W * W * 4 && gsize == (long)W * W, "coverage ref sizes %ld %ld", rsize, gsize );
	for ( i = 0; i < W * W; i++ ) {
		grey[i] = R_HZM_VclGrey( rgba + i * 4 );
		cur[i] = (float)grey[i] / 255.0f;
		mx[i] = grey[i];
	}
	d = diffcount( grey, pil, (long)W * W, &first );
	CHECK( d == 0, "grey: %d texels differ from PIL L (first %ld)", d, first );
	{
		// the HD layer is grey (R = G = B), which no weighting can get wrong: coloured texels vs PIL's own values
		static const unsigned char rgbL[][4] = { { 255, 0, 0, 76 }, { 0, 255, 0, 150 }, { 0, 0, 255, 29 },
			{ 10, 200, 90, 131 }, { 123, 45, 67, 71 }, { 254, 1, 128, 91 } };
		for ( i = 0; i < 6; i++ ) {
			unsigned char px[4] = { rgbL[i][0], rgbL[i][1], rgbL[i][2], 255 };
			CHECK( R_HZM_VclGrey( px ) == rgbL[i][3], "grey(%d,%d,%d) = %d, PIL says %d", px[0], px[1], px[2],
				R_HZM_VclGrey( px ), rgbL[i][3] );
		}
	}

	for ( level = 0, x = W, y = W;; level++ ) {
		char name[64];
		long size;
		unsigned char *ref;

		for ( i = 0; i < x * y; i++ ) {
			up[i] = (unsigned char)R_HZM_VclRintF( cur[i] * 255.0f );
		}
		snprintf( name, sizeof( name ), "cov_l%d.bin", level );
		ref = readall( dir, name, &size );
		CHECK( size == (long)x * y, "cov level %d size", level );
		d = diffcount( up, ref, size, &first );
		CHECK( d == 0, "coverage level %d: %d bytes differ from build_mips (first %ld: C %d twin %d)", level, d, first,
			first >= 0 ? up[first] : 0, first >= 0 ? ref[first] : 0 );
		free( ref );
		if ( x == 1 && y == 1 ) break;
		R_HZM_VclCovDown( cur, x, y, nxt );
		memcpy( cur, nxt, sizeof( float ) * ( x / 2 ) * ( y / 2 ) );
		x /= 2; y /= 2;
	}
	CHECK( level == 11, "coverage has %d levels below 0, want 11", level );

	// the max chain: equal to the true block maximum of level 0, level by level (so conservative by construction)
	for ( level = 0, x = W;; level++ ) {
		int bs = W / x, a, b, bad = 0;
		for ( b = 0; b < x && !bad; b++ ) {
			for ( a = 0; a < x && !bad; a++ ) {
				int u, v, m = 0;
				for ( v = 0; v < bs; v++ ) {
					for ( u = 0; u < bs; u++ ) {
						int g = grey[( b * bs + v ) * W + a * bs + u];
						if ( g > m ) m = g;
					}
				}
				if ( mx[b * x + a] != m ) bad = 1 + b * x + a;
			}
		}
		CHECK( !bad, "max chain level %d texel %d is not the block maximum", level, bad - 1 );
		if ( x == 1 ) break;
		R_HZM_VclMaxDown( mx, x, x, mxn );
		memcpy( mx, mxn, ( x / 2 ) * ( x / 2 ) );
		x /= 2;
	}
	free( rgba ); free( pil ); free( grey ); free( up ); free( mx ); free( mxn ); free( cur ); free( nxt );
}

static void test_scroll( void ) {
	double t;
	double nss = 2.0 * HZM_VCL_SCS, nts = 3.0 * HZM_VCL_SCT;	// the profile's VCL_NS = 2, VCL_NT = 3

	for ( t = 0.0; t <= 1.0e6; t += 997.13 ) {
		double s = R_HZM_VclScroll( t, HZM_VCL_SPS, HZM_VCL_SCS ), u = R_HZM_VclScroll( t, HZM_VCL_SPT, HZM_VCL_SCT );
		CHECK( s >= 0.0 && s < HZM_VCL_SCS && u >= 0.0 && u < HZM_VCL_SCT, "scroll out of range at t=%f: %f %f", t, s, u );
	}
	// across a wrap the offset jumps by exactly the scale: seamless only if the noise tiling is an integer multiple
	CHECK( nss == floor( nss ) && nts == floor( nts ), "NS*SCS %f / NT*SCT %f not integers - the wrap would seam", nss, nts );
	CHECK( fabs( R_HZM_VclScroll( 199.999, HZM_VCL_SPS, HZM_VCL_SCS ) - HZM_VCL_SCS ) < 1e-3
		&& R_HZM_VclScroll( 200.001, HZM_VCL_SPS, HZM_VCL_SCS ) < 1e-3, "s wraps at 200 s (1 / 0.005)" );
	CHECK( R_HZM_VclScroll( 1.0e6 + 0.5, HZM_VCL_SPS, HZM_VCL_SCS ) == R_HZM_VclScroll( 1.0e6 + 0.5, HZM_VCL_SPS, HZM_VCL_SCS ),
		"deterministic" );
}

static void test_deny( void ) {
	static const char *const deny[] = { "m3l1a", "M3L1B", "e3l1", "e3l1_sml", "e3l2", "e3l2_sml", "m3l2", "m3l3", 0 };
	static const char *const in[] = { "co_lobby2", "co_lobby3", "mohdm7", "m1l1", "m1l2a", "m1l2b", "m6l3a", "m6l3b", 0 };
	int i;

	for ( i = 0; deny[i]; i++ ) {
		CHECK( R_HZM_VclDeny( deny[i], "textures/sky/africanight", "env/mohnight1" ) != 0, "map %s not denied", deny[i] );
	}
	CHECK( !strcmp( R_HZM_VclDeny( "m3l2", 0, 0 ), "deny:user-m3l2" ), "m3l2 reason" );
	CHECK( !strcmp( R_HZM_VclDeny( "m3l3", 0, 0 ), "deny:user-m3l3" ), "m3l3 reason" );
	CHECK( !strcmp( R_HZM_VclDeny( "e3l2", 0, 0 ), "deny:omaha" ), "e3l2 reason" );
	CHECK( R_HZM_VclDeny( "obj_team3", "textures/sky/dday2", "env/dday2" ) != 0, "dday2 box not denied" );
	CHECK( R_HZM_VclDeny( "mp_montebattaglia_tow", "textures/sky/x", "env/ep2sky/E3L1SKY" ) != 0, "e3l1sky not denied" );
	CHECK( R_HZM_VclDeny( "zz", "textures/sky/e3l2sky", "" ) != 0, "e3l2sky shader not denied" );
	CHECK( R_HZM_VclDeny( "zz", "textures/sky/omaha_x", 0 ) != 0, "omaha name not denied" );
	CHECK( R_HZM_VclDeny( "zz", 0, "env/inteldim" ) != 0, "inteldim not denied" );
	for ( i = 0; in[i]; i++ ) {
		CHECK( R_HZM_VclDeny( in[i], "textures/sky/africanight", "env/mohnight1" ) == 0, "IN map %s denied", in[i] );
	}
	CHECK( R_HZM_VclDeny( "m3l1", "textures/sky/africanight", "env/mohnight1" ) == 0, "prefix match must not deny m3l1" );
}

/* v1.1 (2026-10-05): the procedural coverage field and the family table (tr_hzm_clouds_pure.h).
   - deterministic (two runs byte-identical);
   - rank-normalised: every byte value holds 1/256 of the texels within +-3 % (so 1 - CLO is the covered share);
   - TILEABLE: the step across the wrap (last column -> first, last row -> first) is no bigger than an interior step
     (mean |difference| within 1.35x of the mean over all interior neighbour pairs);
   - not flat: interior neighbour steps are small (smooth field) but the field spans 0..255;
   - every reviewed family box is outside the deny list (Omaha / dday2 never get a profile), and none repeats. */
static void test_proc( void ) {
	enum { N = 512 };
	static unsigned char a[N * N], b[N * N];
	static float val[N * N];
	static unsigned int hist[65536];
	int count[256], i, j, k;
	double inner = 0.0, wrapX = 0.0, wrapY = 0.0;
	long ni = 0;

	R_HZM_VclProcCoverage( N, a, val, hist );
	R_HZM_VclProcCoverage( N, b, val, hist );
	CHECK( !memcmp( a, b, sizeof( a ) ), "procedural coverage is not deterministic" );
	memset( count, 0, sizeof( count ) );
	for ( i = 0; i < N * N; i++ ) {
		count[a[i]]++;
	}
	for ( k = 1; k < 255; k++ ) {		// the two end bins hold half a bin each (mid-rank rounding)
		CHECK( count[k] > (int)( N * N / 256 * 0.97 ) && count[k] < (int)( N * N / 256 * 1.03 ),
			"rank histogram bin %d holds %d (want %d +-3%%)", k, count[k], N * N / 256 );
	}
	for ( j = 0; j < N; j++ ) {
		for ( i = 0; i < N - 1; i++ ) {
			inner += abs( (int)a[j * N + i + 1] - (int)a[j * N + i] );
			ni++;
		}
		wrapX += abs( (int)a[j * N] - (int)a[j * N + N - 1] );
	}
	for ( i = 0; i < N; i++ ) {
		wrapY += abs( (int)a[i] - (int)a[( N - 1 ) * N + i] );
	}
	inner /= (double)ni;
	wrapX /= N;
	wrapY /= N;
	CHECK( wrapX <= inner * 1.35 && wrapY <= inner * 1.35, "not tileable: wrap steps %.2f / %.2f vs interior %.2f",
		wrapX, wrapY, inner );
	CHECK( inner < 12.0, "field too noisy for a coverage map: interior step %.2f", inner );
	for ( i = 0; hzmCloudFamilies[i].box; i++ ) {
		CHECK( R_HZM_VclDeny( "zz", 0, hzmCloudFamilies[i].box ) == 0, "family box %s is on the deny list",
			hzmCloudFamilies[i].box );
		CHECK( R_HZM_VclFamily( hzmCloudFamilies[i].box ) == &hzmCloudFamilies[i], "family %s repeats",
			hzmCloudFamilies[i].box );
		CHECK( hzmCloudFamilies[i].cover > 0.0f && hzmCloudFamilies[i].cover < 1.0f && hzmCloudFamilies[i].tile > 64.0f,
			"family %s out of range", hzmCloudFamilies[i].box );
	}
	CHECK( R_HZM_VclFamily( "env/dday2" ) == 0 && R_HZM_VclFamily( "env/ep2sky/e3l1sky" ) == 0
		&& R_HZM_VclFamily( "env/mohnight1" ) == 0 && R_HZM_VclFamily( "ENV/MOHDAY1" ) != 0, "family lookup" );
}

int main( int argc, char **argv ) {
	if ( argc < 2 ) {
		printf( "usage: vcl_selftest <refs_dir>\n" );
		return 2;
	}
	test_noise( argv[1] );
	test_coverage( argv[1] );
	test_scroll();
	test_deny();
	test_proc();
	printf( "%s: %d checks, %d failed\n", g_fail ? "FAIL" : "PASS", g_checks, g_fail );
	return g_fail ? 1 : 0;
}
