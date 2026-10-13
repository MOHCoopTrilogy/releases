r"""cgame patch (cgame only): the AIMED PER-SHOT CYCLE takes a PER-WEAPON row, guarded by the mesh, + a last-round row.

User 2026-10-13 (deployed build): "noticed the shotgun doesnt have the pumping action when in ads". While the aim is
held the server keeps the view-model animation at `charge` (the aim pose) through every shot - the hands row
`<prefix>_fire` (for the pump gun: the retail clip WITH the pump stroke) is never played, so the gun's own `fire` row
ran its forend back and forward under a hand that did not move. The cgame already has a client-only id for this
(COOP_VM_ANIM_CYCLE, pistol lane 2026-10-12: `<prefix>_cycle_ads`, started when the clip ammo drops while the aim
pose is up). That row is keyed by the hands PREFIX - `shotgun` is also the double-barrel shotgun's. This patch:

  1. looks for `coopr_<weapon key>_cycle_ads` FIRST (weapon key = the weapon's name, the reload audit's rule: exact
     name, then the "(Finish)"-stripped base - the base only when the held gun is the SAME MESH as the base gun,
     CG_AdsSightSameMesh, so "Shotgun (Double Barrel)" does not take the pump gun's row);
  2. plays `coopr_<weapon key>_cyclelast_ads` when the shot that started it was the LAST round, if fps_anims has
     that row (the prefix row is still "rounds left only", as before);
  3. resolves the playing row through the per-weapon lookup (base rows `coopr_<key>_cycle` / `_cyclelast` must exist:
     they are what an aim let go in mid-cycle hands over to).
No row = nothing changes: every gun without a `coopr_<key>_cycle*` row behaves exactly as before.

TWO SOURCE SHAPES are handled: ads-heavy-next (the prefix-only trigger, as the deployed integ-ads bb5dc05f has it) and
integ-ads from 2627cb94 on (the pistol lane's Welrod change: the trigger already asks the per-weapon lookup for
`coopr_<key>_cycle` - there this patch adds the same-mesh guard and the last-round row; the Welrod's exact-name rows
resolve as before).

    python apply_cyclewpn.py <worktree>      (idempotent)
"""
import sys, os
W = sys.argv[1]
MARK = 'CoopPerWeaponCycleRow'
p = os.path.join(W, 'code/cgame/cg_viewmodelanim.c')
s = open(p, encoding='utf-8', newline='').read()
if MARK in s:
    print('already patched'); sys.exit(0)
LF = chr(10)
nl = chr(13) + LF if (chr(13) + LF) in s else LF


def rep(a, b):
    global s
    a = a.replace(LF, nl); b = b.replace(LF, nl)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('''void CG_ViewModelAnimation(refEntity_t *pModel)
{''', '''// HZM coop [heavy lane 2026-10-13, shotgun pump] the aimed per-shot cycle of ONE gun: `coopr_<weapon key>_<suffix>_ads`
// (suffix "cycle" / "cyclelast"). Found by the exact weapon name, or by its "(Finish)"-stripped base when the held gun
// is the same mesh as that base gun (a different gun whose name merely ends in "(...)" does not borrow the row).
static qboolean s_coopCycleWpn  = qfalse; // the running cycle came from a per-weapon row
static qboolean s_coopCycleLast = qfalse; // ... and it followed the last round

static int CoopPerWeaponCycleRow(dtiki_t *pTiki, const char *suffix)
{
    char        anim[MAX_QPATH], ads[MAX_QPATH], base[64], key[64], exact[MAX_QPATH];
    const char *wpn;
    int         iAds;

    if (!pTiki || !cg.snap || cg.snap->ps.activeItems[1] < 0) {
        return -1;
    }
    anim[0] = 0;
    CoopPerWeaponReloadAnim(pTiki, suffix, anim, sizeof(anim));
    if (!anim[0]) {
        return -1;
    }
    Com_sprintf(ads, sizeof(ads), "%s_ads", anim);
    iAds = cgi.Anim_NumForName(pTiki, ads);
    if (iAds == -1) {
        return -1;
    }
    wpn = CG_ConfigString(CS_WEAPONS + cg.snap->ps.activeItems[1]);
    CoopWeaponKey(wpn, key, sizeof(key));
    Com_sprintf(exact, sizeof(exact), "coopr_%s_%s", key, suffix);
    if (cgi.Anim_NumForName(pTiki, exact) == -1 && CoopStripSkinSuffix(wpn, base, sizeof(base))
        && !CG_AdsSightSameMesh(wpn, base)) {
        return -1;
    }
    return iAds;
}

void CG_ViewModelAnimation(refEntity_t *pModel)
{''')

HEAD = '''        if (iItem == s_cycItem && s_cycClip > 0 && iClip > 0 && iClip < s_cycClip && pCycle->integer
            && cgi.anim->g_iLastVMAnim == VM_ANIM_CHARGE && CG_AimingDownSights()) {
            char szCyc[MAX_QPATH];
            int  iCyc;
'''
OLD_A = HEAD + '''            Com_sprintf(szCyc, sizeof(szCyc), "%s_cycle_ads", AnimPrefixList[iAnimPrefixIndex]);
            iCyc = cgi.Anim_NumForName(pTiki, szCyc);
            if (iCyc != -1) {'''
OLD_B = HEAD + '''            // [pistol lane 2026-10-12] one gun of a shared prefix can have its own cycle (Welrod: a bolt-action
            // pistol on the Colt rows): coopr_<weapon key>_cycle wins, as for the reload rows
            Com_sprintf(szCyc, sizeof(szCyc), "%s_cycle", AnimPrefixList[iAnimPrefixIndex]);
            CoopPerWeaponReloadAnim(pTiki, "cycle", szCyc, sizeof(szCyc));
            Q_strcat(szCyc, sizeof(szCyc), "_ads");
            iCyc = cgi.Anim_NumForName(pTiki, szCyc);
            if (iCyc != -1) {'''
SHAPE_B = OLD_B.replace(LF, nl) in s
print('source shape:', 'integ-ads (per-weapon trigger present)' if SHAPE_B else 'ads-heavy-next (prefix trigger)')
rep(OLD_B if SHAPE_B else OLD_A, '''        if (iItem == s_cycItem && s_cycClip > 0 && iClip >= 0 && iClip < s_cycClip && pCycle->integer
            && cgi.anim->g_iLastVMAnim == VM_ANIM_CHARGE && CG_AimingDownSights()) {
            char szCyc[MAX_QPATH];
            int  iCyc;
            // [heavy lane, shotgun pump] the gun's own row first (and its last-round row); the prefix row as before
            iCyc            = CoopPerWeaponCycleRow(pTiki, iClip > 0 ? "cycle" : "cyclelast");
            s_coopCycleWpn  = (iCyc != -1) ? qtrue : qfalse;
            s_coopCycleLast = (iCyc != -1 && iClip == 0) ? qtrue : qfalse;
            if (iCyc == -1 && iClip > 0) {
                Com_sprintf(szCyc, sizeof(szCyc), "%s_cycle_ads", AnimPrefixList[iAnimPrefixIndex]);
                iCyc = cgi.Anim_NumForName(pTiki, szCyc);
            }
            if (iCyc != -1) {''')
rep('''        case COOP_VM_ANIM_CYCLE:
            pszAnimSuffix = "cycle";
            break;''', '''        case COOP_VM_ANIM_CYCLE:
            pszAnimSuffix = s_coopCycleLast ? "cyclelast" : "cycle";
            break;''')
if SHAPE_B:
    # integ-ads resolves EVERY cycle through the per-weapon lookup: keep that for the gun's own rows only - a gun
    # that was refused its base name's row above (another mesh) must not get it here either
    rep('''            || cgi.anim->g_iLastVMAnim == COOP_VM_ANIM_CYCLE) {
            CoopPerWeaponReloadAnim(''', '''            || (cgi.anim->g_iLastVMAnim == COOP_VM_ANIM_CYCLE && s_coopCycleWpn)) {
            CoopPerWeaponReloadAnim(''')
else:
    rep('''            || cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_END || cgi.anim->g_iLastVMAnim == VM_ANIM_CHARGE) {
            CoopPerWeaponReloadAnim(''', '''            || cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_END || cgi.anim->g_iLastVMAnim == VM_ANIM_CHARGE
            || (cgi.anim->g_iLastVMAnim == COOP_VM_ANIM_CYCLE && s_coopCycleWpn)) {
            CoopPerWeaponReloadAnim(''')
open(p, 'w', encoding='utf-8', newline='').write(s)
print('code/cgame/cg_viewmodelanim.c patched')
