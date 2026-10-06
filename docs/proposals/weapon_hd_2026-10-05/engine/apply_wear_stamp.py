"""Stamp the per-instance weapon wear row into game.dll (fgame/weapon.cpp, Weapon::AttachGun).

    python apply_wear_stamp.py --check [--root <engine checkout>]     verify the anchor, change nothing
    python apply_wear_stamp.py         [--root <engine checkout>]     apply (idempotent, CRLF/LF preserved)

Default root = C:/mohaa-coop-dev/openmohaa-hzm. Anchored on the exact AttachGun prologue; refuses if it moved.
"""
import os, sys
ROOT = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else r"C:/mohaa-coop-dev/openmohaa-hzm"
P = os.path.join(ROOT, "code", "fgame", "weapon.cpp")
ANCHOR = b"""void Weapon::AttachGun(weaponhand_t hand, qboolean holstering)
{
    int tag_num;

    if (!owner) {
        current_attachToTag = "";
        return;
    }
"""
ADD = b"""
    // HZM coop [2026-10-05, weapon HD per-instance wear, user-approved] Pick this weapon's WEAR ROW. The weapon TIKs
    // shipped by zzzzzzzzzz_coop_hd_wpn_5wear.pk3 carry three shader rows on every surface that paints from the gun's
    // main sheet (docs/tools/weapon_hd/gen_wear_tiks.py); the renderer draws row MDL_SURFACE_SKININDEX(surface bits)
    // and clamps an absent row to 0 (tr_model.cpp), so any TIK without the rows - finishes, imports, other mods -
    // simply keeps its one look. Seed = owner identity + gun model: a PLAYER always gets the same wear on the same gun
    // (netname), an AI gets one per entity. First and third person draw this same entity (cg_modelanim.c copies
    // s->surfaces for the view weapon too), so they always agree. Only skin bits 0,1,6 are written; NODRAW and the
    // surface-type bits that the weapon's own animations toggle are left alone. coop_weaponWear 0 = everyone row 0.
    {
        static cvar_t *pWear = gi.Cvar_Get("coop_weaponWear", "1", 0);
        if (pWear->integer && edict->tiki) {
            unsigned int h = 2166136261u;
            const char  *who = NULL;
            char         buf[32];
            if (owner->IsSubclassOfPlayer() && owner->edict->client) {
                who = owner->edict->client->pers.netname;
            } else {
                Com_sprintf(buf, sizeof(buf), "ai%d", owner->entnum);
                who = buf;
            }
            for (const char *c = who; *c; c++) {
                h = (h ^ (unsigned char)*c) * 16777619u;
            }
            for (const char *c = model.c_str(); *c; c++) {
                h = (h ^ (unsigned char)tolower(*c)) * 16777619u;
            }
            const int idx  = (int)(h % 3u);
            const int bits = (idx & 3) | ((idx & 4) << 4);
            const int mask = MDL_SURFACE_SKINOFFSET_BIT0 | MDL_SURFACE_SKINOFFSET_BIT1 | MDL_SURFACE_SKINOFFSET_BIT2;
            int       n    = gi.TIKI_NumSurfaces(edict->tiki);
            if (n > MAX_MODEL_SURFACES) {
                n = MAX_MODEL_SURFACES;
            }
            for (int i = 0; i < n; i++) {
                edict->s.surfaces[i] = (byte)((edict->s.surfaces[i] & ~mask) | bits);
            }
        }
    }
"""
b = open(P, "rb").read()
nl = b"\r\n" if b.count(b"\r\n") > b.count(b"\n") // 2 else b"\n"
a, add = ANCHOR.replace(b"\n", nl), ADD.replace(b"\n", nl)
if a + add in b:
    print("already applied"); sys.exit(0)
assert b.count(a) == 1, "anchor not found exactly once (%d) - weapon.cpp moved, re-derive" % b.count(a)
if "--check" in sys.argv:
    print("check ok:", P); sys.exit(0)
open(P, "wb").write(b.replace(a, a + add))
print("applied:", P)
