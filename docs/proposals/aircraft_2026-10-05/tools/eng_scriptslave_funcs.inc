// HZM coop [aircraft 2026-10-05] ------------------------------------------------------------------------------------
// Shootable German call-in aircraft. Design: docs/proposals/aircraft_2026-10-05/PLAN.md section 12.
// The planes are scaled down and often fly above the sky brush, so neither the bullet trace (stops at the sky
// face) nor the model's link box can be relied on. Registered shootable planes are tested as spheres instead.

#define HZM_MAX_AIRCRAFT 16
static SafePtr<ScriptSlave> s_hzmAircraft[HZM_MAX_AIRCRAFT];

static float HzmAirCvar(const char *name, const char *def)
{
    cvar_t *cv = gi.Cvar_Get(name, def, 0);
    return cv->value;
}

void ScriptSlave::EventHzmAircraft(Event *ev)
{
    int i, freeSlot = -1;

    edict->s.loopSoundFlags |= LOOPSOUND_FLAG_HZM_AIRCRAFT;
    m_fHzmAirRadius = ev->GetFloat(1);
    m_fHzmAirHp     = (ev->NumArgs() > 1) ? ev->GetFloat(2) : 600.0f;
    if (m_fHzmAirRadius <= 0) {
        m_fHzmAirRadius = 0;
        return;
    }

    takedamage = DAMAGE_YES;
    health     = m_fHzmAirHp;
    max_health = m_fHzmAirHp;
    for (i = 0; i < HZM_MAX_AIRCRAFT; i++) {
        if (s_hzmAircraft[i] == this) {
            freeSlot = -2;
            break;
        }
        if (!s_hzmAircraft[i] && freeSlot == -1) {
            freeSlot = i;
        }
    }
    if (freeSlot >= 0) {
        s_hzmAircraft[freeSlot] = this;
    }
    CancelEventsOfType(EV_ScriptSlave_HzmAirThink);
    PostEvent(EV_ScriptSlave_HzmAirThink, level.frametime);
}

// Who may hurt the plane, and how much. German (or world/script) attackers do nothing: the plane is theirs, and a
// script radiusdamage (the bomb run's own blasts) is attributed to world.
static float HzmAirDamageScale(Entity *attacker, Entity *inflictor, int mod)
{
    if (!attacker || attacker == world) {
        return 0;
    }
    if (attacker->IsSubclassOfSentient() && static_cast<Sentient *>(attacker)->m_Team == TEAM_GERMAN) {
        return 0;
    }
    switch (mod) {
    case MOD_BULLET:
    case MOD_FAST_BULLET:
    case MOD_AAGUN:
        if (mod == MOD_AAGUN) {
            return 1.0f;
        }
        if (inflictor && (inflictor->IsSubclassOfTurretGun() || inflictor->IsSubclassOfVehicleTurretGun())) {
            return HzmAirCvar("coop_acMgMult", "1");
        }
        if (inflictor && inflictor->IsSubclassOfWeapon()
            && (static_cast<Weapon *>(inflictor)->GetWeaponClass() & (WEAPON_CLASS_MG | WEAPON_CLASS_HEAVY))) {
            return HzmAirCvar("coop_acMgMult", "1");
        }
        return HzmAirCvar("coop_acSmallArms", "0.25");
    case MOD_EXPLOSION:
    case MOD_GRENADE:
    case MOD_ROCKET:
    case MOD_VEHICLE:
        return (mod == MOD_VEHICLE) ? 0.0f : 1.0f;
    default:
        return 0;
    }
}

void ScriptSlave::HzmAircraftDamage(Event *ev)
{
    Entity *attacker  = ev->GetEntity(1);
    float   damage    = ev->GetFloat(2);
    Entity *inflictor = ev->GetEntity(3);
    int     mod       = ev->GetInteger(9);
    float   scale     = HzmAirDamageScale(attacker, inflictor, mod);

    if (scale <= 0 || damage <= 0) {
        return;
    }
    m_fHzmAirHp -= damage * scale;
    if (m_fHzmAirHp < 0) {
        m_fHzmAirHp = 0;
    }
    health = m_fHzmAirHp;
    Vars()->SetVariable("coop_acAttacker", attacker);
    Vars()->SetVariable("coop_acHitTime", level.time);
    if (HzmAirCvar("coop_acDebug", "0") > 0) {
        gi.Printf("^~^~^ AIRHIT ent=%d atk=%s mod=%d dmg=%.0f x%.2f hp=%.0f\n", entnum,
                  attacker ? attacker->getClassname() : "none", mod, damage, scale, m_fHzmAirHp);
    }
}

// Per-frame proximity fuse: an allied projectile (flak, rifle grenade, rocket) whose path this frame passes within
// 1.2x the damage radius explodes at once, at its closest approach, so its own radius damage reaches the plane at
// nearly full strength. Bullets are handled in BulletAttack.
void ScriptSlave::EventHzmAirThink(Event *ev)
{
    Entity *e = NULL;
    float   r, fuse;

    if (m_fHzmAirRadius <= 0 || m_fHzmAirHp <= 0) {
        return;
    }
    fuse = m_fHzmAirRadius * 1.2f;
    r    = fuse + 4000.0f * level.frametime; // reach: fast shells move ~100u a frame
    while ((e = findradius(e, origin, r)) != NULL) {
        Projectile *pr;
        Entity     *own;
        Vector      p0, d, to;
        float       len, t, miss;

        if (!e->IsSubclassOfProjectile() || e->deadflag != DEAD_NO) {
            continue;
        }
        pr  = static_cast<Projectile *>(e);
        own = G_GetEntity(pr->owner);
        if (!own || (own->IsSubclassOfSentient() && static_cast<Sentient *>(own)->m_Team == TEAM_GERMAN)) {
            continue;
        }
        // closest approach of this frame's motion segment
        p0  = pr->origin;
        d   = pr->velocity * level.frametime;
        len = d.length();
        to  = origin - p0;
        t   = (len > 0.001f) ? (to * d) / (len * len) : 0.0f;
        if (t < 0) {
            t = 0;
        } else if (t > 1) {
            t = 1;
        }
        miss = (origin - (p0 + d * t)).length();
        if (miss > fuse) {
            continue;
        }
        if (t > 0) {
            pr->setOrigin(p0 + d * t);
        }
        pr->deadflag = DEAD_DEAD; // never fused twice
        pr->PostEvent(EV_Projectile_Explode, 0);
    }
    PostEvent(EV_ScriptSlave_HzmAirThink, level.frametime);
}

void G_HZM_AircraftBulletHits(
    const Vector& start, const Vector& dir, float range, float damage, int count, int dflags, int meansofdeath,
    Entity *owner, Weapon *weap
)
{
    int    i;
    Vector d = dir;

    if (!owner || owner == world) {
        return;
    }
    if (owner->IsSubclassOfSentient() && static_cast<Sentient *>(owner)->m_Team == TEAM_GERMAN) {
        return;
    }
    if (d.normalize() < 0.001f) {
        return;
    }
    for (i = 0; i < HZM_MAX_AIRCRAFT; i++) {
        ScriptSlave *a = s_hzmAircraft[i];
        Vector       to, closest;
        float        t, miss;
        trace_t      tr;

        if (!a) {
            continue;
        }
        if (a->m_fHzmAirRadius <= 0 || a->m_fHzmAirHp <= 0) {
            continue;
        }
        to = a->origin - start;
        t  = to * d;
        closest = start + d * t;
        miss    = (a->origin - closest).length();
        if (HzmAirCvar("coop_acDebug", "0") >= 2 && miss < a->m_fHzmAirRadius * 6) {
            gi.Printf("^~^~^ AIRSHOT ent=%d t=%.0f range=%.0f miss=%.0f r=%.0f owner=%s\n", a->entnum, t, range, miss,
                      a->m_fHzmAirRadius, owner->getClassname());
        }
        if (t <= 0 || t > range) {
            continue;
        }
        if (miss > a->m_fHzmAirRadius) {
            continue;
        }
        // blocked by real geometry on the way? A sky face does not block: the plane may be above it.
        tr = G_Trace(start, vec_zero, vec_zero, closest, owner, MASK_SOLID, false, "HzmAircraftShot", true);
        if (tr.fraction < 1.0f && !(tr.surfaceFlags & SURF_SKY) && !tr.startsolid) {
            continue;
        }
        a->Damage(weap ? (Entity *)weap : owner, owner, damage * (count > 0 ? count : 1), closest, d, d * -1, 0,
                  dflags, meansofdeath);
    }
}
// ------------------------------------------------------------------------------------------------------------------

