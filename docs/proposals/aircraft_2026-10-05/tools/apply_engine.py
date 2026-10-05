"""apply_engine.py [--check] [--root DIR] - the aircraft engine bits (docs/proposals/aircraft_2026-10-05).

fgame:  ScriptSlave event `coop_aircraft <radius> [hp]` marks an entity as an aircraft. Bit LOOPSOUND_FLAG_HZM_AIRCRAFT
        in entityState.loopSoundFlags tells the cgame (Doppler + fog see-through). radius > 0 = German plane that
        allied fire can shoot down: HP accounting in ScriptSlave::DamageFunc (small arms x coop_acSmallArms,
        MG/turret/explosive x 1, German attackers ignored), a ray-vs-sphere bullet test in BulletAttack (works above
        the sky brush and on a scaled-down plane), and a proximity fuse for allied projectiles. The last attacker
        is published to script as <plane>.coop_acAttacker, HP as .health.
cgame:  cg_hzm_aircraft.c - Doppler pitch on the plane's loop sound, fog see-through (draw-distance compression
        with matching scale, so the plane keeps its apparent size), cg_hzmAcDebug per-frame lerp log.
Anchored, exactly-once edits. --check verifies every anchor without writing.
"""
import os, sys

ROOT = r"C:\mohaa-coop-dev\openmohaa-hzm"
HERE = os.path.dirname(os.path.abspath(__file__))

EDITS = []


def edit(path, old, new):
    EDITS.append((path, old, new))


# ---------------------------------------------------------------- shared flag
edit("code/qcommon/q_shared.h",
     "\tfloat\tloopSoundPitch;\n\tint\t\tloopSoundFlags;\n",
     "\tfloat\tloopSoundPitch;\n\tint\t\tloopSoundFlags;\t// bit 1 = LOOPSOUND_FLAG_NO_PAN, bit 2 = LOOPSOUND_FLAG_HZM_AIRCRAFT\n")
edit("code/qcommon/q_shared.h",
     "#define RF_ALWAYSDRAW\t\t\t(1<<26)",
     "// HZM coop [aircraft 2026-10-05] entityState.loopSoundFlags bit: this entity is a coop aircraft (cgame Doppler +\n"
     "// fog see-through). Never passed on to the sound system (cg_modelanim.c masks it).\n"
     "#define LOOPSOUND_FLAG_HZM_AIRCRAFT 2\n"
     "#define RF_ALWAYSDRAW\t\t\t(1<<26)")

# ---------------------------------------------------------------- fgame: keep the bit across loopsound
edit("code/fgame/entity.cpp",
     "            // Local sound will always be heard\n            edict->s.loopSoundFlags = aliaschannel == CHAN_LOCAL;\n",
     "            // Local sound will always be heard\n"
     "            // HZM coop [aircraft 2026-10-05] keep LOOPSOUND_FLAG_HZM_AIRCRAFT; only bit 1 is the alias channel\n"
     "            edict->s.loopSoundFlags = (edict->s.loopSoundFlags & LOOPSOUND_FLAG_HZM_AIRCRAFT)\n"
     "                                    | ((aliaschannel == CHAN_LOCAL) ? 1 : 0);\n")

# ---------------------------------------------------------------- fgame: ScriptSlave aircraft
edit("code/fgame/scriptslave.h",
     "    void DamageFunc(Event *ev);\n    void SetDamage(Event *ev);\n",
     "    void DamageFunc(Event *ev);\n"
     "    // HZM coop [aircraft 2026-10-05] coop call-in aircraft (coop_mod/aircraft.scr)\n"
     "    float m_fHzmAirRadius = 0;  // > 0: shootable, damage sphere radius\n"
     "    float m_fHzmAirHp     = 0;\n"
     "    void  EventHzmAircraft(Event *ev);\n"
     "    void  EventHzmAirThink(Event *ev);\n"
     "    void  HzmAircraftDamage(Event *ev);\n"
     "    void SetDamage(Event *ev);\n")

edit("code/fgame/scriptslave.cpp",
     "Event EV_ScriptSlave_ModifyFlyPath\n(",
     open(os.path.join(HERE, "eng_scriptslave_events.inc")).read() + "Event EV_ScriptSlave_ModifyFlyPath\n(")
edit("code/fgame/scriptslave.cpp",
     "    {&EV_ScriptSlave_NormalAngles,           &ScriptSlave::EventNormalAngles    },\n    {NULL,                                   NULL                               }\n",
     "    {&EV_ScriptSlave_NormalAngles,           &ScriptSlave::EventNormalAngles    },\n"
     "    {&EV_ScriptSlave_HzmAircraft,            &ScriptSlave::EventHzmAircraft     },\n"
     "    {&EV_ScriptSlave_HzmAirThink,            &ScriptSlave::EventHzmAirThink     },\n"
     "    {NULL,                                   NULL                               }\n")
edit("code/fgame/scriptslave.cpp",
     "void ScriptSlave::DamageFunc(Event *ev)\n{\n    Unregister(STRING_DAMAGE);\n}\n",
     "void ScriptSlave::DamageFunc(Event *ev)\n{\n"
     "    if (m_fHzmAirRadius > 0 && m_fHzmAirHp > 0) {\n        HzmAircraftDamage(ev); // HZM coop [aircraft 2026-10-05]\n    }\n"
     "    Unregister(STRING_DAMAGE);\n}\n\n" + open(os.path.join(HERE, "eng_scriptslave_funcs.inc")).read())

# ---------------------------------------------------------------- fgame: bullets
edit("code/fgame/weaputils.cpp",
     "    lastSurfaceFlags = 0;\n    iNumHit          = 0;\n\n    // HZM coop [user 2026-08-25] PLAYER SUPPRESSION",
     "    lastSurfaceFlags = 0;\n    iNumHit          = 0;\n\n"
     "    // HZM coop [aircraft 2026-10-05] shootable coop aircraft: a ray-vs-sphere test that does not stop at the sky\n"
     "    // brush and does not depend on the scaled-down model's tiny link box (scriptslave.cpp).\n"
     "    G_HZM_AircraftBulletHits(start, dir, range, damage, count, dflags, meansofdeath, owner, weap);\n\n"
     "    // HZM coop [user 2026-08-25] PLAYER SUPPRESSION")
edit("code/fgame/weaputils.h",
     "float BulletAttack\n",
     "// HZM coop [aircraft 2026-10-05] scriptslave.cpp\n"
     "void G_HZM_AircraftBulletHits(const Vector& start, const Vector& dir, float range, float damage, int count,\n"
     "                              int dflags, int meansofdeath, Entity *owner, Weapon *weap);\n"
     "float BulletAttack\n")

# ---------------------------------------------------------------- cgame
edit("code/cgame/cg_modelanim.c",
     "void CG_ModelAnim(centity_t *cent, qboolean bDoShaderTime)\n{",
     "// HZM coop [aircraft 2026-10-05] cg_hzm_aircraft.c\n"
     "float CG_HZM_AircraftPitch(const centity_t *cent, float fPitch);\n"
     "void  CG_HZM_AircraftView(const centity_t *cent, refEntity_t *model);\n\n"
     "void CG_ModelAnim(centity_t *cent, qboolean bDoShaderTime)\n{")
edit("code/cgame/cg_modelanim.c",
     "    if (s1->loopSound && (s1->parent == ENTITYNUM_NONE) && !CG_LoopSoundIsForeignLocal(s1)) {\n"
     "        cgi.S_AddLoopingSound(\n"
     "            cent->lerpOrigin,\n"
     "            vec3_origin,\n"
     "            cgs.sound_precache[s1->loopSound],\n"
     "            s1->loopSoundVolume,\n"
     "            s1->loopSoundMinDist,\n"
     "            s1->loopSoundMaxDist,\n"
     "            s1->loopSoundPitch,\n"
     "            s1->loopSoundFlags\n",
     "    if (s1->loopSound && (s1->parent == ENTITYNUM_NONE) && !CG_LoopSoundIsForeignLocal(s1)) {\n"
     "        cgi.S_AddLoopingSound(\n"
     "            cent->lerpOrigin,\n"
     "            vec3_origin,\n"
     "            cgs.sound_precache[s1->loopSound],\n"
     "            s1->loopSoundVolume,\n"
     "            s1->loopSoundMinDist,\n"
     "            s1->loopSoundMaxDist,\n"
     "            CG_HZM_AircraftPitch(cent, s1->loopSoundPitch), // HZM coop [aircraft] Doppler\n"
     "            s1->loopSoundFlags & ~LOOPSOUND_FLAG_HZM_AIRCRAFT\n")
edit("code/cgame/cg_modelanim.c",
     "        cgi.R_AddRefEntityToScene(&model, s1->parent);\n\n        // HZM coop [bug-2569] THE BODY COPIES GO IN AFTER THE RIG",
     "        CG_HZM_AircraftView(cent, &model); // HZM coop [aircraft 2026-10-05] fog see-through, debug log\n"
     "        cgi.R_AddRefEntityToScene(&model, s1->parent);\n\n        // HZM coop [bug-2569] THE BODY COPIES GO IN AFTER THE RIG")

NEWFILES = {"code/cgame/cg_hzm_aircraft.c": "eng_cg_hzm_aircraft.c"}


def main():
    check = "--check" in sys.argv
    root = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else ROOT
    ok = True
    texts = {}
    for path, old, new in EDITS:
        p = os.path.join(root, path)
        if p not in texts:
            texts[p] = open(p, encoding="latin-1", newline="").read()
        t = texts[p]
        crlf = "\r\n" in t
        o, n = (old.replace("\n", "\r\n"), new.replace("\n", "\r\n")) if crlf else (old, new)
        if t.count(n) == 1:      # the new text often contains the anchor, so test it first (idempotent re-run)
            print("already applied:", path, repr(old[:50]))
            continue
        c = t.count(o)
        if c != 1:
            print("ANCHOR x%d: %s %r" % (c, path, old[:70]))
            ok = False
            continue
        texts[p] = t.replace(o, n)
    for dst, src in NEWFILES.items():
        p = os.path.join(root, dst)
        body = open(os.path.join(HERE, src), encoding="latin-1").read()
        if os.path.exists(p) and open(p, encoding="latin-1").read() != body:
            print("new file differs (will overwrite):", dst)
        texts[p] = body
    if not ok:
        print("CHECK FAILED")
        return 1
    if check:
        print("check ok (%d edits, %d new files)" % (len(EDITS), len(NEWFILES)))
        return 0
    for p, t in texts.items():
        with open(p, "w", encoding="latin-1", newline="") as f:
            f.write(t)
    print("applied to", root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
