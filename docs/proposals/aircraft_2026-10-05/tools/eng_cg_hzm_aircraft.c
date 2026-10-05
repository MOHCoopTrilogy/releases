/*
===========================================================================
HZM coop - coop call-in aircraft, client side (docs/proposals/aircraft_2026-10-05).

The server flags its aircraft with LOOPSOUND_FLAG_HZM_AIRCRAFT (ScriptSlave `coop_aircraft`, coop_mod/aircraft.scr).
For those entities only:

 1. DOPPLER. The engine's loop sounds carry no velocity (vec3_origin at every call site) and the AL speed of sound is
    never set, so a passing plane never changes pitch. The pitch multiplier is computed here, per client, from the
    entity's snapshot velocity and the listener's. The planes are drawn scaled down (s) and fly at s x real speed,
    so the source speed is divided by s: the shift matches the real aircraft the player believes he is seeing.

 2. FOG SEE-THROUGH (and, with no fog, a speck fade toward the +-8000 coordinate edge). Past ~55% of the fog distance the plane is drawn CLOSER along the view ray with its scale cut by
    the same ratio. Its apparent size is unchanged (perspective), only the fog depth it sits in is compressed, so it
    fades late instead of vanishing (the user asked for "a little" see-through on the foggiest maps). Nothing else in
    the scene, and no fog setting, changes. Off with cg_hzmAcFog 0.

 3. cg_hzmAcDebug 1 prints the drawn pose of every aircraft every frame (^~^~^ ACLERP) for the smoothness gate.
    Without the flag (a live, unpatched server) it matches the plane models by name, so a before/after run can be
    measured with the same client.
===========================================================================
*/

#include "cg_local.h"
#include "tiki.h"

static cvar_t *s_acDoppler;
static cvar_t *s_acSound;
static cvar_t *s_acFog;
static cvar_t *s_acFogStart;
static cvar_t *s_acFogSlope;
static cvar_t *s_acFogMax;
static cvar_t *s_acDebug;

static void CG_HZM_AircraftCvars(void)
{
    if (s_acDoppler) {
        return;
    }
    s_acDoppler  = cgi.Cvar_Get("cg_hzmDoppler", "1", CVAR_ARCHIVE);
    s_acSound    = cgi.Cvar_Get("cg_hzmDopplerC", "18000", 0);  // speed of sound, units/s (343 m/s at 16 u/ft)
    s_acFog      = cgi.Cvar_Get("cg_hzmAcFog", "1", CVAR_ARCHIVE);
    s_acFogStart = cgi.Cvar_Get("cg_hzmAcFogStart", "0.55", 0);  // fraction of the fog distance left untouched
    s_acFogSlope = cgi.Cvar_Get("cg_hzmAcFogSlope", "0.3", 0);   // compression beyond it
    s_acFogMax   = cgi.Cvar_Get("cg_hzmAcFogMax", "0.92", 0);    // never drawn deeper than this
    s_acDebug    = cgi.Cvar_Get("cg_hzmAcDebug", "0", 0);
}

static qboolean CG_HZM_IsAircraft(const centity_t *cent)
{
    return (cent->currentState.loopSoundFlags & LOOPSOUND_FLAG_HZM_AIRCRAFT) ? qtrue : qfalse;
}

static void CG_HZM_EntVelocity(const centity_t *cent, vec3_t vel)
{
    float dt;

    VectorClear(vel);
    if (!cent->interpolate || !cg.nextSnap || !cg.snap) {
        return;
    }
    dt = (cg.nextSnap->serverTime - cg.snap->serverTime) * 0.001f;
    if (dt <= 0.001f) {
        return;
    }
    VectorSubtract(cent->nextState.origin, cent->currentState.origin, vel);
    VectorScale(vel, 1.0f / dt, vel);
}

float CG_HZM_AircraftPitch(const centity_t *cent, float fPitch)
{
    vec3_t vSrc, vDir;
    float  c, s, vs, vl, f;

    CG_HZM_AircraftCvars();
    if (!CG_HZM_IsAircraft(cent) || !s_acDoppler->integer) {
        return fPitch;
    }
    CG_HZM_EntVelocity(cent, vSrc);
    VectorSubtract(cg.refdef.vieworg, cent->lerpOrigin, vDir); // source -> listener
    if (VectorNormalize(vDir) < 1.0f) {
        return fPitch;
    }
    s  = cent->currentState.scale > 0.01f ? cent->currentState.scale : 1.0f;
    c  = s_acSound->value > 1000.0f ? s_acSound->value : 18000.0f;
    vs = DotProduct(vSrc, vDir) / s;                                    // apparent closing speed of the source
    vl = DotProduct(cg.predicted_player_state.velocity, vDir);          // listener moving away along the line
    if (vs > 0.9f * c) {
        vs = 0.9f * c;
    } else if (vs < -0.9f * c) {
        vs = -0.9f * c;
    }
    f = (c - vl) / (c - vs);
    if (f < 0.5f) {
        f = 0.5f;
    } else if (f > 2.0f) {
        f = 2.0f;
    }
    return fPitch * f;
}

void CG_HZM_AircraftView(const centity_t *cent, refEntity_t *model)
{
    qboolean bAir;
    float    F, d, d0, d2, dmax, ratio;
    vec3_t   delta;

    CG_HZM_AircraftCvars();
    bAir = CG_HZM_IsAircraft(cent);

    // no fog: shrink toward a speck from 6000u out (gone at ~9500u), so the plane never pops in or out in plain
    // view at the +-8000 coordinate edge. Done here so the networked scale stays the true one (Doppler reads it).
    if (bAir && cg.refdef.farplane_distance <= 1.0f) {
        VectorSubtract(model->origin, cg.refdef.vieworg, delta);
        d = VectorLength(delta);
        if (d > 6000.0f) {
            ratio = (9500.0f - d) / 3500.0f;
            if (ratio < 0.03f) {
                ratio = 0.03f;
            }
            model->scale *= ratio;
        }
    }

    if (bAir && s_acFog->integer && cg.refdef.farplane_distance > 1.0f) {
        F = cg.refdef.farplane_distance;
        VectorSubtract(model->origin, cg.refdef.vieworg, delta);
        d    = VectorLength(delta);
        d0   = s_acFogStart->value * F;
        dmax = s_acFogMax->value * F;
        if (d > d0 && d > 1.0f) {
            d2 = d0 + (d - d0) * s_acFogSlope->value;
            if (d2 > dmax) {
                d2 = dmax;
            }
            ratio = d2 / d;
            VectorMA(cg.refdef.vieworg, ratio, delta, model->origin);
            model->scale *= ratio;
            if (model->renderfx & RF_LIGHTING_ORIGIN) {
                VectorSubtract(model->lightingOrigin, cg.refdef.vieworg, delta);
                VectorMA(cg.refdef.vieworg, ratio, delta, model->lightingOrigin);
            }
        }
    }

    if (s_acDebug->integer) {
        qboolean bMatch = bAir;
        if (!bMatch && model->tiki && model->tiki->name) {
            const char *n = model->tiki->name;
            bMatch = (strstr(n, "fly") || strstr(n, "stuka")) ? qtrue : qfalse;
        }
        if (bMatch) {
            cgi.Printf(
                "^~^~^ ACLERP t=%d ft=%d e=%d o=%.2f %.2f %.2f a=%.2f %.2f %.2f s=%.3f fl=%d\n",
                cg.time,
                cg.frametime,
                cent->currentState.number,
                cent->lerpOrigin[0],
                cent->lerpOrigin[1],
                cent->lerpOrigin[2],
                cent->lerpAngles[0],
                cent->lerpAngles[1],
                cent->lerpAngles[2],
                model->scale,
                bAir ? 1 : 0
            );
        }
    }
}
