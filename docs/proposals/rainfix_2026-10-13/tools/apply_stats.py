"""apply_stats.py - MEASUREMENT ONLY instrumentation on top of the rain fix (never committed to the engine branch).
    python apply_stats.py            patch the rainfix worktree
Reverse with:  git -C C:/mohaa-coop-dev/openmohaa-hzm-rainfix apply -R <stats.diff>
Adds coop_rainStats 1: once a second two console lines,
  ^~^~^ RAINSTAT ...  spawn / skip counters, live streaks, pool refusals, microseconds a frame in the rain spawner and
                      in the beam pass, mean start / end height over the ground, mean "gap" (how high over the ground
                      the top of a streak still is when the streak is removed)
  ^~^~^ RAINCOV ...   streak units drawn per frame in 32-unit height bands over the player's feet (-64 .. 448)
"""
import io, sys
ROOT = "C:/mohaa-coop-dev/openmohaa-hzm-rainfix/code/cgame/"


def patch(name, pairs):
    p = ROOT + name
    s = io.open(p, "r", encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in s else "\n"
    if "HZMRAINSTATS" in s:
        print(name, "already patched")
        return
    for old, new in pairs:
        old = old.replace("\n", nl)
        new = new.replace("\n", nl)
        if s.count(old) != 1:
            sys.exit("%s: anchor found %d times: %r" % (name, s.count(old), old[:70]))
        s = s.replace(old, new)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print(name, "patched")


NATURE_HEAD = r'''// HZMRAINSTATS (measurement build only)
#include <chrono>
struct hzmRainStat_t {
    int       frames, want, made, kDist, kSky, kStub, kLife, kFlat, kEnd, kNear, nSamp;
    double    hs, he, gap, cosz, life;
    long long usRain;
    double    cov[16];
    int       covFrames;
};
hzmRainStat_t g_hzmRS;
int           g_hzmBeamsAlive   = 0;
int           g_hzmBeamPoolFail = 0;
long long     g_hzmBeamsUs      = 0;
int           g_hzmBeamFrames   = 0;
static int    s_hzmRSLast       = 0;

long long CG_HZMRainNowUs(void)
{
    return std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now().time_since_epoch())
        .count();
}

qboolean CG_HZMRainStatsOn(void)
{
    static cvar_t *p = NULL;
    if (!p) { p = cgi.Cvar_Get("coop_rainStats", "0", 0); }
    return p->integer ? qtrue : qfalse;
}

// a drawn streak from vA (tail) to vB (head): add its height span to the 32-unit bands over the player's feet
void CG_HZMRainCov(const float *vA, const float *vB)
{
    float z0, z1, lo, hi;
    int   k;

    if (!CG_HZMRainStatsOn()) {
        return;
    }
    z0 = vA[2] - cg.predicted_player_state.origin[2];
    z1 = vB[2] - cg.predicted_player_state.origin[2];
    if (z0 > z1) { float t = z0; z0 = z1; z1 = t; }
    for (k = 0; k < 16; k++) {
        lo = -64.0f + 32.0f * k;
        hi = lo + 32.0f;
        if (z1 <= lo || z0 >= hi) { continue; }
        g_hzmRS.cov[k] += (double)((z1 < hi ? z1 : hi) - (z0 > lo ? z0 : lo));
    }
}

static void CG_HZMRainSample(const vec3_t vStart, const vec3_t vEnd, int iLife, int iFlags)
{
    vec3_t  vZero = {0.0f, 0.0f, 0.0f};
    vec3_t  a, b, d;
    trace_t tr;
    float   gz, len;

    if (!CG_HZMRainStatsOn() || (g_hzmRS.made & 7)) {
        return;
    }
    VectorSubtract(vEnd, vStart, d);
    len = VectorNormalize(d);
    VectorCopy(vEnd, a);
    a[2] += 4.0f;
    VectorCopy(a, b);
    b[2] -= 4096.0f;
    cgi.CM_BoxTrace(&tr, a, b, vZero, vZero, 0, MASK_SOLID, qfalse);
    if (tr.fraction >= 1.0f || tr.startsolid) {
        return; // no ground under it
    }
    gz = tr.endpos[2];
    g_hzmRS.nSamp++;
    g_hzmRS.hs   += vStart[2] - gz;
    g_hzmRS.he   += vEnd[2] - gz;
    g_hzmRS.gap  += (vEnd[2] - gz) + ((iFlags & BEAM_HZM_TAILRUN) ? 0.0f : (float)(int)cg.rain.length * -d[2]);
    g_hzmRS.cosz += -d[2];
    g_hzmRS.life += iLife;
    (void)len;
}

static void CG_HZMRainStatFrame(long long usT0)
{
    char line[512];
    int  k, n;

    if (!CG_HZMRainStatsOn()) {
        return;
    }
    g_hzmRS.frames++;
    g_hzmRS.usRain += CG_HZMRainNowUs() - usT0;
    if (cg.time - s_hzmRSLast < 1000 && cg.time >= s_hzmRSLast) {
        return;
    }
    n = g_hzmRS.nSamp ? g_hzmRS.nSamp : 1;
    cgi.Printf(
        "^~^~^ RAINSTAT ms=%d frames=%d want=%d made=%d kDist=%d kSky=%d kStub=%d kLife=%d kFlat=%d kEnd=%d kNear=%d "
        "alive=%d poolfail=%d rain_us=%.1f beams_us=%.1f hs=%.1f he=%.1f gap=%.1f cosz=%.3f life=%.0f den=%.2f "
        "len=%.0f spd=%.0f vary=%d slant=%d dist=%.0f wind=%.0f,%.0f\n",
        cg.time - s_hzmRSLast, g_hzmRS.frames, g_hzmRS.want, g_hzmRS.made, g_hzmRS.kDist, g_hzmRS.kSky, g_hzmRS.kStub,
        g_hzmRS.kLife, g_hzmRS.kFlat, g_hzmRS.kEnd, g_hzmRS.kNear, g_hzmBeamsAlive, g_hzmBeamPoolFail,
        (double)g_hzmRS.usRain / (g_hzmRS.frames ? g_hzmRS.frames : 1),
        (double)g_hzmBeamsUs / (g_hzmBeamFrames ? g_hzmBeamFrames : 1), g_hzmRS.hs / n, g_hzmRS.he / n,
        g_hzmRS.gap / n, g_hzmRS.cosz / n, g_hzmRS.life / n, cg.rain.density, cg.rain.length, cg.rain.speed,
        cg.rain.speed_vary, cg.rain.slant, cg.rain.min_dist, vss_wind_x->value, vss_wind_y->value
    );
    line[0] = 0;
    for (k = 0; k < 16; k++) {
        Q_strcat(line, sizeof(line), va(" %d", (int)(g_hzmRS.cov[k] / (g_hzmBeamFrames ? g_hzmBeamFrames : 1))));
    }
    cgi.Printf("^~^~^ RAINCOV%s\n", line);
    memset(&g_hzmRS, 0, sizeof(g_hzmRS));
    g_hzmBeamPoolFail = 0;
    g_hzmBeamsUs      = 0;
    g_hzmBeamFrames   = 0;
    s_hzmRSLast       = cg.time;
}

void CG_Rain(centity_t *cent)
{
    int         iLife;
    int         iBeamFlags;
'''

NATURE = [
    ("void CG_Rain(centity_t *cent)\n{\n    int         iLife;\n    int         iBeamFlags;\n", NATURE_HEAD),
    # global path: counters
    ("""        iNumSpawn = CG_HZMRainSpawnCount(iNumSpawn, &sCarryGlobal); // HZM coop [bug-3558] by elapsed time
    }
""", """        iNumSpawn = CG_HZMRainSpawnCount(iNumSpawn, &sCarryGlobal); // HZM coop [bug-3558] by elapsed time
    }
    long long usStat0 = CG_HZMRainNowUs();
    g_hzmRS.want += iNumSpawn;
"""),
    ("""        if (VectorLengthSquared(vLength) > Square(cg.rain.min_dist)) {
            continue;
        }
        if (bEntRoof) {""", """        if (VectorLengthSquared(vLength) > Square(cg.rain.min_dist)) {
            g_hzmRS.kDist++;
            continue;
        }
        if (bEntRoof) {"""),
    ("""                if (!(skyTr.surfaceFlags & SURF_SKY)) {
                    continue; // no sky in this column -> no drop""", """                if (!(skyTr.surfaceFlags & SURF_SKY)) {
                    g_hzmRS.kSky++;
                    continue; // no sky in this column -> no drop"""),
    ("""                if (wallTr.fraction < 0.1f) {
                    continue; // streak would be a stub - skip the drop entirely""", """                if (wallTr.fraction < 0.1f) {
                    g_hzmRS.kStub++;
                    continue; // streak would be a stub - skip the drop entirely"""),
    ("""                if (iLife < 50) {
                    continue;
                }
            } else if (!CG_HZMRainFloor(vStart, vEnd, &iLife)) {
                continue;""", """                if (iLife < 50) {
                    g_hzmRS.kLife++;
                    continue;
                }
            } else if (!CG_HZMRainFloor(vStart, vEnd, &iLife)) {
                g_hzmRS.kFlat++;
                continue;"""),
    ("""                    continue; // lands under cover""", """                    g_hzmRS.kEnd++;
                    continue; // lands under cover"""),
    ("""        if (CG_HZMRainTooNear(vStart, vEnd)) {
            continue; // HZM coop [2026-10-12] near cull
        }
        iBeamFlags = CG_HZMRainTailRun(vStart, vEnd, &iLife); // HZM coop [bug-3881] the streak runs into the surface
""", """        if (CG_HZMRainTooNear(vStart, vEnd)) {
            g_hzmRS.kNear++;
            continue; // HZM coop [2026-10-12] near cull
        }
        iBeamFlags = CG_HZMRainTailRun(vStart, vEnd, &iLife); // HZM coop [bug-3881] the streak runs into the surface
        CG_HZMRainSample(vStart, vEnd, iLife, iBeamFlags);
        g_hzmRS.made++;
"""),
    ("""            vEnd, 0, 0, 0, 1, 0, shadername, fcolor, 0, 0.0, cg.rain.length, 1.0, 0, "raineffect"
        );
    }
}""", """            vEnd, 0, 0, 0, 1, 0, shadername, fcolor, 0, 0.0, cg.rain.length, 1.0, 0, "raineffect"
        );
    }
    CG_HZMRainStatFrame(usStat0);
}"""),
]

BEAM = [
    ("void CG_AddBeams(void)\n{\n", """// HZMRAINSTATS (measurement build only)
extern int       g_hzmBeamsAlive, g_hzmBeamPoolFail, g_hzmBeamFrames;
extern long long g_hzmBeamsUs;
extern long long CG_HZMRainNowUs(void);
extern void      CG_HZMRainCov(const float *vA, const float *vB);
struct hzmBeamTimer_t {
    long long t0;
    int       n;
    hzmBeamTimer_t() : t0(CG_HZMRainNowUs()), n(0) {}
    ~hzmBeamTimer_t()
    {
        g_hzmBeamsUs += CG_HZMRainNowUs() - t0;
        g_hzmBeamFrames++;
        g_hzmBeamsAlive = n;
    }
};

void CG_AddBeams(void)
{
    hzmBeamTimer_t hzmTimer;
"""),
    ("""        // Fade the beam based on it's life
        fade = (float)(b->endtime - cg.time) / (float)b->life;
""", """        // Fade the beam based on it's life
        fade = (float)(b->endtime - cg.time) / (float)b->life;
        hzmTimer.n++;
"""),
    ("""                cgi.R_AddPolyToScene(b->beamshader, 4, points, b->renderfx);
            } else if (b->flags & BEAM_INVERTED_FAST) {""", """                cgi.R_AddPolyToScene(b->beamshader, 4, points, b->renderfx);
                CG_HZMRainCov(vCurrStart, vCurrEnd);
            } else if (b->flags & BEAM_INVERTED_FAST) {"""),
    ("""                VectorNormalizeFast(vDir);
                VectorMA(vCurrEnd, -b->toggledelay, vDir, vCurrStart);

                CG_BuildRendererBeam_Fast(""", """                VectorNormalizeFast(vDir);
                VectorMA(vCurrEnd, -b->toggledelay, vDir, vCurrStart);
                CG_HZMRainCov(vCurrStart, vCurrEnd);

                CG_BuildRendererBeam_Fast("""),
    ("""        VectorCopy(start, b->start);
        VectorCopy(end, b->end);
        return;
    }
    return;
}""", """        VectorCopy(start, b->start);
        VectorCopy(end, b->end);
        return;
    }
    {
        extern int g_hzmBeamPoolFail;
        g_hzmBeamPoolFail++;
    }
    return;
}"""),
]

patch("cg_nature.cpp", NATURE)
patch("cg_beam.cpp", BEAM)
