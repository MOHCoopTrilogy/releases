/*
HZM coop [2026-09-27] offline unit test for renderergl2/tr_hzm_lodfog.c (the PURE half of r_hzmLodFog).
docs/proposals/fog_lod_pop_2026-09-27/plan.md section 5.1. Built by build.bat next to this file (MSVC, a console
program - no window, no game). Prints PASS and exits 0, or prints every FAIL and exits 1.

Properties (the whole reason the feature exists is the first one):
  P1 HIDDEN   - for every fov / aspect / instance radius / fog distance / direction, once the ORIGIN reaches the
                gate, no point of the instance sphere that is inside the frustum is at planar depth < farEff.
                (Camera pitch is irrelevant: the fog and the frustum are both in camera space. Governed culls use the
                true 3-D distance, so the retail doubled-dz quirk does not apply.)
  P2 OFF      - floor 0 or cap 0 returns AUTHORED with the retail band, distScale 1, no gate, retail culls.
  P3 CONTINUOUS - near' is continuous in the fog distance through the governed -> hand-back -> authored zones.
  P4 AUTHORED BEYOND - past the hand-back zone the band is exactly the shader's.
  P5 NEVER NEARER - near' is never nearer than the authored near.
  P6 NAMES   - the Omaha list decision by loaded BSP name (path, case, _sml, .bsp).
  P7 ORDER   - through one cache the decision follows every map load, in both orders (review fix
               2026-09-28: the first version keyed the cache on the tr.world pointer, which never changes).
*/
#include "tr_local.h"
#include <stdio.h>

static int g_fail = 0;
#define CHECK( cond, ... ) do { if ( !( cond ) ) { g_fail++; printf( "FAIL: " __VA_ARGS__ ); printf( "\n" ); } } while ( 0 )

/* fovY from a horizontal fov and aspect, MOHAA hor+ style: fovY = 2 atan(tan(fovX/2) / aspect) */
static float FovY( float fovX, float aspect ) {
	return (float)( 2.0 * atan( tan( fovX * M_PI / 360.0 ) / aspect ) * 180.0 / M_PI );
}

int main( void ) {
	const float fars[]   = { 500.0f, 1000.0f, 1500.0f, 1800.0f, 2300.0f, 3000.0f, 5000.0f };
	const float fovsX[]  = { 40.0f, 80.0f, 90.0f, 113.3f, 130.0f };
	const float aspects[] = { 4.0f / 3.0f, 16.0f / 9.0f, 3440.0f / 1440.0f };
	const float radii[]  = { 0.0f, 65.0f, 364.0f, 1069.0f };
	const float nears[]  = { 0.0f, 256.0f, 900.0f, 2000.0f, 5000.0f };
	int a, b, c, d, e;
	hzmLodBand_t band;

	/* P2 */
	CHECK( R_HZM_LodFogBand( 0.0f, 3500.0f, 100.0f, 256.0f, 256.0f, 0.52f, &band ) == HZM_LODBAND_AUTHORED
	       && band.nearDist == 256.0f && band.range == 256.0f && band.distScale == 1.0f && band.gateDist == 0.0f
	       && !band.trueDistance, "P2 floor 0 not authored" );
	CHECK( R_HZM_LodFogBand( 1000.0f, 0.0f, 100.0f, 256.0f, 256.0f, 0.52f, &band ) == HZM_LODBAND_AUTHORED,
	       "P2 cap 0 not authored" );
	CHECK( R_HZM_LodFogFloor( 0.0f, 1.0f, 80.0f, 60.0f ) == 0.0f, "P2 far 0 gives a floor" );
	CHECK( R_HZM_LodFogFloor( 1000.0f, 1.0f, 0.0f, 60.0f ) == 0.0f, "P2 fov 0 gives a floor" );

	for ( a = 0; a < (int)ARRAY_LEN( fars ); a++ )
	for ( b = 0; b < (int)ARRAY_LEN( fovsX ); b++ )
	for ( c = 0; c < (int)ARRAY_LEN( aspects ); c++ )
	for ( d = 0; d < (int)ARRAY_LEN( radii ); d++ )
	for ( e = 0; e < (int)ARRAY_LEN( nears ); e++ ) {
		const float fx = fovsX[b], fy = FovY( fovsX[b], aspects[c] );
		const float fl = R_HZM_LodFogFloor( fars[a], 1.0f, fx, fy );
		const int   r  = R_HZM_LodFogBand( fl, 1.0e9f, radii[d], nears[e], 300.0f, 0.52f, &band );
		const float tx = (float)tan( fx * M_PI / 360.0 ), ty = (float)tan( fy * M_PI / 360.0 );
		int k;

		CHECK( r == HZM_LODBAND_GOVERNED, "P1 uncapped not governed" );
		CHECK( band.nearDist >= nears[e], "P5 near moved nearer" );
		/* P1: put the ORIGIN at the gate distance in 81 directions across (and just outside) the frustum, sample
		   the instance sphere, and check every sample the camera can see (inside the frustum) is at planar depth
		   >= far, i.e. 100% fog. Camera space: x right, y up, z forward. */
		for ( k = 0; k < 81; k++ ) {
			const double u = ( ( k % 9 ) / 4.0 - 1.0 ) * 1.1, v = ( ( k / 9 ) / 4.0 - 1.0 ) * 1.1;
			double dx = u * tx, dy = v * ty, dz = 1.0, n = sqrt( dx * dx + dy * dy + dz * dz );
			const double ox = dx / n * band.gateDist, oy = dy / n * band.gateDist, oz = dz / n * band.gateDist;
			int j;

			for ( j = 0; j < 200; j++ ) {	/* Fibonacci sphere, full radius (the worst case) */
				const double t = ( j + 0.5 ) / 200.0, phi = acos( 1.0 - 2.0 * t ), th = j * 2.39996322972865332;
				const double px = ox + radii[d] * sin( phi ) * cos( th );
				const double py = oy + radii[d] * sin( phi ) * sin( th );
				const double pz = oz + radii[d] * cos( phi );

				if ( pz <= 0.0 || fabs( px ) > pz * tx || fabs( py ) > pz * ty ) {
					continue;	/* not visible */
				}
				CHECK( pz >= fars[a] * 0.9999, "P1 visible below 100%% fog: far %.0f fovX %.1f aspect %.3f r %.0f z %.1f",
				       fars[a], fx, aspects[c], radii[d], pz );
			}
		}
	}

	/* P3 + P4: sweep the fog distance through all three zones for one model and check near' continuity */
	{
		const float cap = 3500.0f, fx = 113.3f, fy = FovY( 113.3f, 3440.0f / 1440.0f );
		float prev = -1.0f, f;
		int sawGov = 0, sawHand = 0, sawAuth = 0;

		for ( f = 200.0f; f <= 4000.0f; f += 1.0f ) {
			const int r = R_HZM_LodFogBand( R_HZM_LodFogFloor( f, 1.0f, fx, fy ), cap, 1069.0f, 256.0f, 256.0f, 1.0f, &band );
			sawGov  |= r == HZM_LODBAND_GOVERNED;
			sawHand |= r == HZM_LODBAND_HANDBACK;
			sawAuth |= r == HZM_LODBAND_AUTHORED;
			if ( r == HZM_LODBAND_AUTHORED ) {
				CHECK( band.nearDist == 256.0f && band.distScale == 1.0f && !band.trueDistance, "P4 authored band altered at far %.0f", f );
			}
			if ( prev >= 0.0f ) {
				/* continuity: a 1-unit fog step moves near' by at most edge (governed) or 4 x edge (the hand-back
				   slope, |near - cap| x edge / (0.25 cap) <= 4 edge); a real jump is hundreds of units */
				const float edge = R_HZM_LodFogFloor( 1.0f, 1.0f, fx, fy );
				CHECK( fabs( band.nearDist - prev ) <= 4.0f * edge + 1.0f, "P3 jump at far %.0f: %.2f -> %.2f", f, prev, band.nearDist );
			}
			prev = band.nearDist;
		}
		CHECK( sawGov && sawHand && sawAuth, "P3 sweep did not cross all three zones" );
	}

	/* P6 NAMES - the Omaha list, by the loaded BSP name, whatever the path / case / _sml / .bsp */
	{
		const char *yes[] = { "m3l1a", "maps/m3l1a.bsp", "M3L1B", "maps\\e3l1_sml", "e3l2", "maps/obj/obj_team3.bsp" };
		const char *no[]  = { "", "e2l2", "maps/e2l1.bsp", "m3l1", "m3l1ab", "obj_team1", "e3l3" };
		int k;
		for ( k = 0; k < (int)ARRAY_LEN( yes ); k++ ) {
			CHECK( R_HZM_LodFogMapNameExcluded( yes[k] ), "P6 %s should be excluded", yes[k] );
		}
		for ( k = 0; k < (int)ARRAY_LEN( no ); k++ ) {
			CHECK( !R_HZM_LodFogMapNameExcluded( no[k] ), "P6 %s should NOT be excluded", no[k] );
		}
	}

	/* P7 ORDER - the regression the renderer-keep review found: the decision must follow EACH loaded map, in both
	   orders, through one cache (the renderer's static), not stick to the first map of the DLL's life */
	{
		const char *seq[] = { "maps/m3l1a.bsp", "maps/e2l2.bsp", "maps/m3l1a.bsp", "maps/e2l1.bsp", "maps/e2l1.bsp",
		                      "maps/obj/obj_team3.bsp", "maps/m6l1a.bsp" };
		const int   want[] = { 1, 0, 1, 0, 0, 1, 0 };
		const int   chg[]  = { 1, 1, 1, 1, 0, 1, 1 };
		hzmLodFogMapCache_t cache;
		qboolean changed;
		int k;
		memset( &cache, 0, sizeof( cache ) );
		for ( k = 0; k < (int)ARRAY_LEN( seq ); k++ ) {
			const qboolean ex = R_HZM_LodFogExcludedCached( seq[k], &cache, &changed );
			CHECK( ( ex ? 1 : 0 ) == want[k], "P7 step %d %s excluded %d want %d", k, seq[k], (int)ex, want[k] );
			CHECK( ( changed ? 1 : 0 ) == chg[k], "P7 step %d %s changed %d want %d", k, seq[k], (int)changed, chg[k] );
		}
	}

	if ( g_fail ) {
		printf( "%d FAIL\n", g_fail );
		return 1;
	}
	printf( "PASS\n" );
	return 0;
}
