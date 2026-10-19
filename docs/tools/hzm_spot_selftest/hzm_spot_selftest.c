/*
hzm_spot_selftest.c - offline unit test for Phase S (vet_phaseS.md G4: "byte identity / Omaha forced 1" without a
game client).

It links openmohaa-hzm/code/renderergl2/tr_hzm_spot.c UNCHANGED - that file holds every pure function the renderer's
spot/flare path decides with, and reads nothing but its arguments - and compiles it against the real tr_local.h and
renderercommon/hzm_light_restore.h, so the bit layout, dlight_t and the carrier helpers under test are the shipped ones.
The one thing mirrored here is tr_scene.c R_AddDynamicLightTyped's slot fill (cap -> intensity test -> fill ->
R_HZM_SpotBeginLight), ten lines that sit around the call under test; the mirror is marked.

    docs/tools/hzm_spot_selftest/build.bat      (needs the MSVC toolchain; prints PASS / FAIL, exit code 0 / 1)

Every check prints nothing when it holds; a failure prints the case and counts. The last line is the verdict.
*/

#include "tr_local.h"

#include <stdio.h>
#include <string.h>
#include <math.h>

// q_shared.c is not linked (it pulls the engine's error/print imports); HZM_LightRestoreMapProtected needs only this
int Q_stricmpn( const char *s1, const char *s2, size_t n ) {
	size_t i;

	for ( i = 0; i < n; i++ ) {
		int c1 = (unsigned char)s1[i], c2 = (unsigned char)s2[i];

		if ( c1 >= 'A' && c1 <= 'Z' ) {
			c1 += 'a' - 'A';
		}
		if ( c2 >= 'A' && c2 <= 'Z' ) {
			c2 += 'a' - 'A';
		}
		if ( c1 != c2 ) {
			return c1 < c2 ? -1 : 1;
		}
		if ( !c1 ) {
			return 0;
		}
	}
	return 0;
}

static int g_fail, g_checks;

#define CHECK( cond, ... ) do { g_checks++; if ( !( cond ) ) { g_fail++; printf( "FAIL %s:%d: ", __FILE__, __LINE__ ); \
	printf( __VA_ARGS__ ); printf( "\n" ); } } while ( 0 )

static unsigned int g_rng = 20260926u;
static float frand( void ) {	// 0..1, deterministic
	g_rng = g_rng * 1664525u + 1013904223u;
	return ( g_rng >> 8 ) * ( 1.0f / 16777216.0f );
}
static float srand1( void ) {
	return frand() * 2.0f - 1.0f;
}

// ------------------------------------------------------------------ the mirrored tr_scene.c slot fill
typedef struct {
	dlight_t		dl[MAX_DLIGHTS];
	int				first, num;
	hzmFlare_t		flares[HZM_FLARE_MAX];
	int				numFlares;
	hzmSpotStats_t	st;
	int				capDropped;
} scene_t;

// MIRROR of renderergl2/tr_scene.c R_AddDynamicLightTyped after its tr.registered test (the intake, the cap, the
// intensity test, the fill, R_HZM_SpotBeginLight). The intake itself is the real R_HZM_SpotIntakeCore.
static void AddLight( scene_t *s, const vec3_t org, float intensity, float r, float g, float b, int type,
                      qboolean spotsOn, qboolean flaresOn ) {
	hzmAdd_t	verdict = HZM_ADD_LIGHT;
	dlight_t	*dl;

	if ( type & ( HZM_DLIGHT_SPOT | HZM_DLIGHT_CARRIER ) ) {	// R_HZM_SpotIntake's one-bit fast path
		if ( R_HZM_SpotIntakeCore( s->dl, s->first, s->num, s->flares, &s->numFlares, HZM_FLARE_MAX, org, intensity,
		                           r, g, b, type, spotsOn, flaresOn, &s->st, &verdict ) ) {
			return;
		}
	}
	if ( s->num >= MAX_DLIGHTS ) {
		s->capDropped++;
		return;
	}
	if ( intensity <= 0 ) {
		return;
	}
	dl = &s->dl[s->num++];
	memset( dl, 0xCD, sizeof( *dl ) );	// a reused slot holds LAST frame's garbage - it must all be overwritten
	VectorCopy( org, dl->origin );
	dl->radius = intensity;
	dl->color[0] = r;
	dl->color[1] = g;
	dl->color[2] = b;
	dl->additive = ( type & additive ) ? qtrue : qfalse;
	dl->type = (dlighttype_t)type;
	R_HZM_SpotBeginLight( dl, type, verdict == HZM_ADD_SPOT ? qtrue : qfalse );
}

static void AddSpot( scene_t *s, int tag, const vec3_t apex, const vec3_t axis, float range, float innerDeg,
                     float outerDeg, int owner, qboolean on ) {
	vec3_t c = { 0.6f, 0.46f, 0.3f };

	AddLight( s, apex, range, c[0], c[1], c[2], additive | hzm_dlight_noshadow | HZM_DLIGHT_SPOT | HZM_DLIGHT_FOGGED
	          | HZM_DlightTagBits( tag ), on, on );
	AddLight( s, axis, -1.0f, (float)cos( DEG2RAD( innerDeg ) ), (float)cos( DEG2RAD( outerDeg ) ), (float)owner,
	          HZM_DLIGHT_CARRIER | HZM_DLIGHT_KIND_SPOT | HZM_DlightTagBits( tag ), on, on );
}

static void Finish( scene_t *s, int *dropped ) {
	s->num = R_HZM_SpotCompact( s->dl, s->first, s->num, dropped );
}

// GLSL mirror: lightall_fp/vp + dlight_fp HzmSpotCone(), on the uniform the renderer uploads
static float GlslCone( const vec4_t u, const vec3_t toSurfUnit ) {
	float k = (float)sqrt( u[0] * u[0] + u[1] * u[1] + u[2] * u[2] ), cosOuter, t;

	if ( k <= 0.0f ) {
		return 1.0f;
	}
	cosOuter = u[3];
	if ( cosOuter > 2.0f ) {
		cosOuter -= 4.0f;
	}
	t = ( ( toSurfUnit[0] * u[0] + toSurfUnit[1] * u[1] + toSurfUnit[2] * u[2] ) / k - cosOuter ) * k;
	t = t < 0.0f ? 0.0f : ( t > 1.0f ? 1.0f : t );
	return t * t * ( 3.0f - 2.0f * t );
}

static void RandUnit( vec3_t v ) {
	float l;

	do {
		v[0] = srand1();
		v[1] = srand1();
		v[2] = srand1();
		l = (float)sqrt( DotProduct( v, v ) );
	} while ( l < 0.05f || l > 1.0f );
	VectorScale( v, 1.0f / l, v );
}

int main( void ) {
	int i, e, l, c;

	printf( "hzm_spot_selftest: Phase S pure functions (tr_hzm_spot.c) + carrier layout (hzm_light_restore.h)\n" );
	printf( "  GENTITYNUM_BITS %d, tag bits %d, MAX_DLIGHTS %d, HZM_FLARE_MAX %d, protocol %d\n", GENTITYNUM_BITS,
	        HZM_DLIGHT_TAG_BITS, MAX_DLIGHTS, HZM_FLARE_MAX, HZM_SPOT_PROTOCOL );

	// 1. the three Phase S AUTO defines flip TOGETHER (vet R20: a partial flip is a mismatched pair by another name).
	//    They shipped at 0 and went to 1 together when Test S passed (2026-09-26); the old "all 0" form of this check
	//    went stale at that flip. S3a's cgame-only HZM_BEAMSTOP_AUTO must be a plain 0/1.
	CHECK( HZM_SPOT_AUTO == HZM_FLARES_AUTO && HZM_FLARES_AUTO == HZM_HEADLIGHTS_AUTO,
	       "the Phase S AUTO defines disagree (partial flip)" );
	CHECK( HZM_BEAMSTOP_AUTO == 0 || HZM_BEAMSTOP_AUTO == 1, "HZM_BEAMSTOP_AUTO is not 0/1" );

	// 2. flare ids round-trip for EVERY entity x lamp x class (vet F2), and never touch another field
	for ( e = 0; e < MAX_GENTITIES; e++ ) {
		for ( l = 0; l < 4; l++ ) {
			for ( c = 0; c < 2; c++ ) {
				int			id = HZM_FlareIdPack( e, l );
				int			type = HZM_DlightFlareBits( id, c );
				hzmFlare_t	f;
				vec3_t		org = { 1, 2, 3 };

				if ( !( type > 0 ) || !( type & HZM_DLIGHT_CARRIER ) || ( type & HZM_DLIGHT_KIND_MASK ) != HZM_DLIGHT_KIND_FLARE
				     || ( type & ( HZM_DLIGHT_SPOT | HZM_DLIGHT_FOGGED | HZM_DLIGHT_RESERVED_MASK | HZM_DLIGHT_RETAIL_BITS
				                   | hzm_dlight_noshadow | hzm_dlight_edgefade ) )
				     || HZM_DlightTagOf( type ) != id || ( id >> 2 ) != e || ( id & 3 ) != l
				     || HZM_DlightFlareClassOf( type ) != c ) {
					CHECK( 0, "flare id round trip e=%d l=%d c=%d type=0x%x", e, l, c, type );
					e = MAX_GENTITIES;
					break;
				}
				if ( R_HZM_SpotClassify( -0.5f, type, qtrue, qtrue ) != HZM_ADD_FLARE
				     || !R_HZM_FlareFromCarrier( org, -0.5f, 0.0f, 0.0f, 2.0f, type, &f ) || f.id != id
				     || f.flareClass != c || f.brightness != 0.5f || f.facing[2] != 1.0f ) {
					CHECK( 0, "flare carrier decode e=%d l=%d c=%d", e, l, c );
					e = MAX_GENTITIES;
					break;
				}
			}
		}
	}
	g_checks++;

	// 3. spot tags round-trip over the whole field and never reach the class / reserved bits
	for ( i = 1; i <= HZM_DLIGHT_TAG_MAX; i++ ) {
		int t = HZM_DlightTagBits( i ) | HZM_DLIGHT_SPOT;

		if ( HZM_DlightTagOf( t ) != i || ( t & ( HZM_DLIGHT_CLASS_MASK | HZM_DLIGHT_RESERVED_MASK ) ) ) {
			CHECK( 0, "spot tag %d", i );
			break;
		}
	}
	g_checks++;

	// 4. the TIKI mask (cgame cg_commands.cpp DynamicLight) can never produce a Phase S bit from ANY author integer
	for ( i = 0; i < 1 << 20; i++ ) {
		int raw = (int)( ( (unsigned)i * 2654435761u ) ^ ( (unsigned)i << 11 ) );

		if ( ( raw & HZM_DLIGHT_RETAIL_BITS ) & ~HZM_DLIGHT_RETAIL_BITS ) {
			CHECK( 0, "TIKI mask leak %d", raw );
			break;
		}
		if ( R_HZM_SpotClassify( 100.0f, raw & HZM_DLIGHT_RETAIL_BITS, qtrue, qtrue ) != HZM_ADD_LIGHT ) {
			CHECK( 0, "a masked TIKI type classified as Phase S: %d", raw & HZM_DLIGHT_RETAIL_BITS );
			break;
		}
	}
	g_checks++;

	// 5. carriers take no slot; a spot + its carrier = ONE ready slot; a flare = no slot
	{
		scene_t s;
		vec3_t	apex = { 0, 0, 64 }, axis = { 1, 0, 0 }, org = { 0, 0, 0 };
		int		dropped = 0;

		memset( &s, 0, sizeof( s ) );
		AddLight( &s, org, 160, 1, 0.82f, 0.45f, additive, qtrue, qtrue );			// a muzzle flash
		AddSpot( &s, 1, apex, axis, 1100, 12, 28, 77, qtrue );
		AddLight( &s, apex, -0.8f, 1, 0, 0, HZM_DlightFlareBits( HZM_FlareIdPack( 77, 0 ), 0 ), qtrue, qtrue );
		CHECK( s.num == 2, "slots after flash + spot + flare: %d (want 2)", s.num );
		CHECK( s.numFlares == 1, "flares %d", s.numFlares );
		CHECK( s.dl[0].hzmSpot == HZM_SPOT_NONE && s.dl[0].hzmTag == 0 && s.dl[0].hzmConeK == 0.0f
		       && s.dl[0].hzmOwner == -1, "the muzzle flash carries spot state (slot not zeroed)" );
		CHECK( s.dl[1].hzmSpot == HZM_SPOT_READY && s.dl[1].hzmOwner == 77, "the spot is not ready/owned" );
		CHECK( fabs( s.dl[1].hzmCosOuter - cos( DEG2RAD( 28.0 ) ) ) < 1e-6
		       && fabs( 1.0 / s.dl[1].hzmConeK - ( cos( DEG2RAD( 12.0 ) ) - cos( DEG2RAD( 28.0 ) ) ) ) < 1e-5,
		       "cone parameters" );
		Finish( &s, &dropped );
		CHECK( s.num == 2 && dropped == 0, "compaction removed a ready light" );
		CHECK( s.st.orphan == 0 && s.st.discarded == 0 && s.st.spotOff == 0, "unexpected drops" );
	}

	// 6. a carrier after a DROPPED light is discarded and never turns another light (a muzzle flash) into a cone
	{
		scene_t s;
		vec3_t	apex = { 0, 0, 64 }, axis = { 1, 0, 0 }, org = { 0, 0, 0 };

		memset( &s, 0, sizeof( s ) );
		for ( i = 0; i < MAX_DLIGHTS; i++ ) {
			AddLight( &s, org, 160, 1, 0.82f, 0.45f, additive, qtrue, qtrue );
		}
		AddSpot( &s, 1, apex, axis, 1100, 12, 28, 5, qtrue );
		CHECK( s.num == MAX_DLIGHTS && s.capDropped == 1, "the cap did not drop the spot light" );
		CHECK( s.st.orphan == 1, "the orphan carrier was not counted (%d)", s.st.orphan );
		for ( i = 0; i < MAX_DLIGHTS; i++ ) {
			if ( s.dl[i].hzmSpot != HZM_SPOT_NONE ) {
				CHECK( 0, "slot %d became a spot", i );
				break;
			}
		}
	}

	// 7. mismatched tags: the carrier is discarded, the light stays pending and spot-or-nothing removes it
	{
		scene_t s;
		vec3_t	apex = { 0, 0, 64 }, axis = { 1, 0, 0 }, org = { 0, 0, 0 };
		int		dropped = 0;

		memset( &s, 0, sizeof( s ) );
		AddLight( &s, apex, 1100, 0.6f, 0.46f, 0.3f, additive | HZM_DLIGHT_SPOT | HZM_DlightTagBits( 3 ), qtrue, qtrue );
		AddLight( &s, org, 160, 1, 1, 1, additive, qtrue, qtrue );
		AddLight( &s, axis, -1, 0.97f, 0.88f, 5, HZM_DLIGHT_CARRIER | HZM_DLIGHT_KIND_SPOT | HZM_DlightTagBits( 4 ), qtrue,
		          qtrue );
		CHECK( s.st.orphan == 1 && s.dl[0].hzmSpot == HZM_SPOT_PENDING, "mismatched tag attached" );
		Finish( &s, &dropped );
		CHECK( s.num == 1 && dropped == 1 && s.dl[0].radius == 160 && s.dl[0].hzmSpot == HZM_SPOT_NONE,
		       "spot-or-nothing: num %d dropped %d", s.num, dropped );
	}

	// 8. a spot with NO carrier (never sent) is removed; order of the rest is kept
	{
		scene_t s;
		vec3_t	apex = { 0, 0, 64 }, org = { 0, 0, 0 };
		int		dropped = 0;

		memset( &s, 0, sizeof( s ) );
		AddLight( &s, org, 100, 1, 1, 1, 0, qtrue, qtrue );
		AddLight( &s, apex, 1100, 0.6f, 0.46f, 0.3f, additive | HZM_DLIGHT_SPOT | HZM_DlightTagBits( 1 ), qtrue, qtrue );
		AddLight( &s, org, 200, 1, 1, 1, 0, qtrue, qtrue );
		Finish( &s, &dropped );
		CHECK( s.num == 2 && dropped == 1 && s.dl[0].radius == 100 && s.dl[1].radius == 200, "compaction order" );
	}

	// 9. OMAHA: the protected worlds; there, spots are DROPPED (never an omni light) and every carrier discarded
	{
		scene_t s;
		vec3_t	apex = { 0, 0, 64 }, axis = { 1, 0, 0 };
		qboolean on;

		CHECK( HZM_LightRestoreMapProtected( "maps/m3l1a.bsp" ) && HZM_LightRestoreMapProtected( "m3l1b" )
		       && HZM_LightRestoreMapProtected( "MAPS\\M3L1A.BSP" ), "Omaha not protected" );
		CHECK( !HZM_LightRestoreMapProtected( "maps/e3l1.bsp" ) && !HZM_LightRestoreMapProtected( "maps/m3l1" )
		       && !HZM_LightRestoreMapProtected( "maps/m3l1ab.bsp" ) && !HZM_LightRestoreMapProtected( "" ),
		       "a non-Omaha map protected" );
		on = HZM_LightRestoreMapProtected( "maps/m3l1a.bsp" ) ? qfalse : qtrue;	// what R_HZM_SpotsOn resolves there
		memset( &s, 0, sizeof( s ) );
		AddSpot( &s, 1, apex, axis, 1100, 12, 28, 5, on );
		AddLight( &s, apex, -0.8f, 1, 0, 0, HZM_DlightFlareBits( 9, 0 ), on, on );
		CHECK( s.num == 0 && s.numFlares == 0, "Omaha: a spot or flare got through (num %d flares %d)", s.num,
		       s.numFlares );
		CHECK( s.st.spotOff == 1 && s.st.discarded == 2, "Omaha counters spotOff %d discarded %d", s.st.spotOff,
		       s.st.discarded );
	}

	// 10. the non-spot factor is EXACTLY 1.0f, and every non-ready light uploads an all-zero uniform
	{
		dlight_t	d;
		vec4_t		u;
		vec3_t		p;

		for ( i = 0; i < 100000; i++ ) {
			memset( &d, 0, sizeof( d ) );
			R_HZM_SpotClearLight( &d );
			d.origin[0] = srand1() * 4000;
			d.origin[1] = srand1() * 4000;
			d.origin[2] = srand1() * 4000;
			d.radius = frand() * 2000;
			if ( i & 1 ) {
				d.hzmSpot = HZM_SPOT_PENDING;		// a pending light is not a cone either
			}
			p[0] = srand1() * 4000;
			p[1] = srand1() * 4000;
			p[2] = srand1() * 4000;
			if ( R_HZM_DlightFactorAt( &d, p, frand() * 100 ) != 1.0f ) {
				CHECK( 0, "non-spot factor != 1.0f" );
				break;
			}
			R_HZM_SpotUniformVec( &d, d.hzmAxis, ( i & 2 ) ? qtrue : qfalse, u );
			if ( u[0] != 0.0f || u[1] != 0.0f || u[2] != 0.0f || u[3] != 0.0f ) {
				CHECK( 0, "non-spot uniform not all zero" );
				break;
			}
		}
		g_checks++;
		R_HZM_SpotUniformVec( NULL, p, qtrue, u );
		CHECK( u[0] == 0.0f && u[1] == 0.0f && u[2] == 0.0f && u[3] == 0.0f, "NULL light uniform" );
	}

	// 11. the cone: 0 everywhere behind the lamp, 1 inside the inner angle, the GLSL mirror == the CPU law, and the
	//     debug offset changes the tint only
	{
		scene_t	s;
		vec3_t	apex = { 100, -50, 64 }, axis, dir;
		vec4_t	u, ud;

		RandUnit( axis );
		memset( &s, 0, sizeof( s ) );
		AddSpot( &s, 1, apex, axis, 1100, 12, 28, -1, qtrue );
		R_HZM_SpotUniformVec( &s.dl[0], s.dl[0].hzmAxis, qfalse, u );
		R_HZM_SpotUniformVec( &s.dl[0], s.dl[0].hzmAxis, qtrue, ud );
		CHECK( ud[3] == u[3] + HZM_SPOT_DEBUG_OFFSET && ud[0] == u[0], "debug offset" );
		for ( i = 0; i < 200000; i++ ) {
			float	cpu, gpu, gpuDbg, cd;

			RandUnit( dir );
			cd = DotProduct( dir, s.dl[0].hzmAxis );
			cpu = R_HZM_SpotConeDir( s.dl[0].hzmAxis, s.dl[0].hzmCosOuter, s.dl[0].hzmConeK, dir );
			gpu = GlslCone( u, dir );
			gpuDbg = GlslCone( ud, dir );
			if ( cd <= 0.0f && ( cpu != 0.0f || gpu != 0.0f ) ) {
				CHECK( 0, "light behind the lamp: dot %.4f cpu %.4f gpu %.4f", cd, cpu, gpu );
				break;
			}
			if ( cd >= (float)cos( DEG2RAD( 11.9 ) ) && cpu < 0.9999f ) {
				CHECK( 0, "inside the inner angle but cone %.5f", cpu );
				break;
			}
			if ( fabs( cpu - gpu ) > 2e-5f || fabs( gpu - gpuDbg ) > 2e-5f ) {
				CHECK( 0, "GLSL mirror disagrees: cpu %.6f gpu %.6f dbg %.6f", cpu, gpu, gpuDbg );
				break;
			}
		}
		g_checks++;
	}

	// 12. the attenuation IS lightall's CalcLightAttenuation(1, R^2/d^2)
	for ( i = 0; i < 100000; i++ ) {
		float R = 10.0f + frand() * 3000.0f, d = 1.0f + frand() * 4000.0f;
		float glsl = ( 0.5f * ( R * R / ( d * d ) ) - 1.5f ) * 1.0f + 1.0f;
		float cpu = R_HZM_SpotAttenuation( d * d, R );

		glsl = glsl < 0.0f ? 0.0f : ( glsl > 1.0f ? 1.0f : glsl );
		if ( fabs( glsl - cpu ) > 1e-5f ) {
			CHECK( 0, "attenuation R %.1f d %.1f cpu %.6f glsl %.6f", R, d, cpu, glsl );
			break;
		}
	}
	g_checks++;

	// 13. the cull is CONSERVATIVE: a sphere any of whose sampled points the cone lights must never be culled, and
	//     the sphere-dilated cone agrees (> 0) wherever a sampled point is lit
	{
		dlight_t	d;
		vec3_t		axis, zero3 = { 0, 0, 0 };
		int			culledLit = 0, dilatedMiss = 0, trials = 0;

		for ( i = 0; i < 20000; i++ ) {
			vec3_t	center, p, to;
			float	rad = 1.0f + frand() * 200.0f, outer = 5.0f + frand() * 80.0f, inner = outer * frand();
			int		k;
			qboolean touches, anyLit = qfalse;

			scene_t s;
			memset( &s, 0, sizeof( s ) );
			RandUnit( axis );
			AddSpot( &s, 1, zero3, axis, 2000, inner, outer, -1, qtrue );
			d = s.dl[0];
			center[0] = srand1() * 800;
			center[1] = srand1() * 800;
			center[2] = srand1() * 800;
			touches = R_HZM_SpotSphereTouches( d.origin, d.hzmAxis, d.hzmCosOuter, center, rad );
			for ( k = 0; k < 64; k++ ) {
				vec3_t off;

				RandUnit( off );
				VectorMA( center, rad * frand(), off, p );
				VectorSubtract( p, d.origin, to );
				if ( R_HZM_SpotConeDir( d.hzmAxis, d.hzmCosOuter, d.hzmConeK, to ) > 0.0f ) {
					anyLit = qtrue;
					break;
				}
			}
			if ( anyLit ) {
				trials++;
				if ( !touches ) {
					culledLit++;
				}
				if ( !( R_HZM_SpotConeSphere( d.origin, d.hzmAxis, d.hzmCosOuter, d.hzmConeK, center, rad ) > 0.0f ) ) {
					dilatedMiss++;
				}
			}
		}
		CHECK( culledLit == 0, "the cull dropped %d lit spheres of %d", culledLit, trials );
		CHECK( dilatedMiss == 0, "the dilated cone missed %d lit spheres of %d", dilatedMiss, trials );
		CHECK( trials > 1000, "too few lit samples (%d) to mean anything", trials );
	}

	// 14. malformed carriers: zero axis, NaN cone, positive intensity, reserved bits, unknown kind
	{
		scene_t s;
		vec3_t	apex = { 0, 0, 64 }, zero = { 0, 0, 0 }, axis = { 1, 0, 0 };
		float	nanv = (float)sqrt( -1.0 );
		int		dropped = 0;

		memset( &s, 0, sizeof( s ) );
		AddLight( &s, apex, 1100, 1, 1, 1, additive | HZM_DLIGHT_SPOT | HZM_DlightTagBits( 1 ), qtrue, qtrue );
		AddLight( &s, zero, -1, 0.97f, 0.88f, 5, HZM_DLIGHT_CARRIER | HZM_DLIGHT_KIND_SPOT | HZM_DlightTagBits( 1 ), qtrue,
		          qtrue );
		AddLight( &s, apex, 1100, 1, 1, 1, additive | HZM_DLIGHT_SPOT | HZM_DlightTagBits( 2 ), qtrue, qtrue );
		AddLight( &s, axis, -1, nanv, 0.88f, 5, HZM_DLIGHT_CARRIER | HZM_DLIGHT_KIND_SPOT | HZM_DlightTagBits( 2 ), qtrue,
		          qtrue );
		Finish( &s, &dropped );
		CHECK( s.num == 0 && dropped == 2, "malformed carriers left a light (num %d dropped %d)", s.num, dropped );
		memset( &s, 0, sizeof( s ) );
		// a carrier bit with a POSITIVE intensity is not ours: an ordinary light, no spot state
		AddLight( &s, apex, 300, 1, 1, 1, HZM_DLIGHT_CARRIER | HZM_DLIGHT_KIND_SPOT | HZM_DlightTagBits( 1 ), qtrue, qtrue );
		CHECK( s.num == 1 && s.dl[0].hzmSpot == HZM_SPOT_NONE, "positive-intensity carrier bit" );
		// a spot bit with tag 0 is not a spot
		AddLight( &s, apex, 300, 1, 1, 1, HZM_DLIGHT_SPOT, qtrue, qtrue );
		CHECK( s.num == 2 && s.dl[1].hzmSpot == HZM_SPOT_NONE, "tagless spot bit" );
		CHECK( R_HZM_SpotClassify( -1, HZM_DLIGHT_CARRIER | ( 2 << HZM_DLIGHT_KIND_SHIFT ) | HZM_DlightTagBits( 1 ), qtrue,
		                           qtrue ) == HZM_ADD_DISCARD, "unknown kind" );
		CHECK( R_HZM_SpotClassify( -1, HZM_DLIGHT_CARRIER | HZM_DLIGHT_KIND_FLARE | ( 1 << 27 ), qtrue, qtrue )
		       == HZM_ADD_DISCARD, "reserved bits" );
		CHECK( R_HZM_SpotClassify( -1, HZM_DLIGHT_CARRIER | HZM_DLIGHT_KIND_SPOT, qtrue, qtrue ) == HZM_ADD_DISCARD,
		       "tagless spot carrier" );
	}

	// 15. flare list: capped, never a slot
	{
		scene_t s;
		vec3_t	lamp = { 0, 0, 64 };

		memset( &s, 0, sizeof( s ) );
		for ( i = 0; i < HZM_FLARE_MAX + 10; i++ ) {
			AddLight( &s, lamp, -1, 1, 0, 0, HZM_DlightFlareBits( i, 0 ), qtrue, qtrue );
		}
		CHECK( s.numFlares == HZM_FLARE_MAX && s.st.flareFull == 10 && s.num == 0, "flare cap" );
		memset( &s, 0, sizeof( s ) );
		AddLight( &s, lamp, -1, 1, 0, 0, HZM_DlightFlareBits( 1, 0 ), qtrue, qfalse );	// flares off
		CHECK( s.numFlares == 0 && s.st.discarded == 1 && s.num == 0, "flare while off" );
	}

	// 16. flare shape: 0 behind the lamp, grows toward the eye's facing, near fade to 0 at the lamp
	{
		hzmFlare_t	f;
		vec3_t		eye;
		float		half, inten, dist;

		memset( &f, 0, sizeof( f ) );
		VectorSet( f.facing, 1, 0, 0 );
		f.brightness = 1.0f;
		VectorSet( eye, -500, 0, 0 );
		R_HZM_FlareShape( &f, eye, 1440, 0.05f, 0.25f, 150, 4, &half, &inten, &dist );
		CHECK( inten == 0.0f, "flare seen from behind: %.4f", inten );
		VectorSet( eye, 500, 0, 0 );
		R_HZM_FlareShape( &f, eye, 1440, 0.05f, 0.25f, 150, 4, &half, &inten, &dist );
		CHECK( fabs( inten - 0.25f ) < 1e-5f && fabs( half - 0.5f * 0.05f * 1440 ) < 1e-3f, "facing flare %.4f %.2f",
		       inten, half );
		VectorSet( eye, 1, 0, 0 );
		R_HZM_FlareShape( &f, eye, 1440, 0.05f, 0.25f, 150, 4, &half, &inten, &dist );
		CHECK( inten < 1e-3f, "near fade %.5f", inten );
	}

	printf( "%s: %d checks, %d failed\n", g_fail ? "FAIL" : "PASS", g_checks, g_fail );
	return g_fail ? 1 : 0;
}
