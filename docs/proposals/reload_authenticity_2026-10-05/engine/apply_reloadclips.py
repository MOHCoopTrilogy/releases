"""apply_reloadclips.py - reload authenticity phase B, cgame only (cg_viewmodelanim.c).

    python apply_reloadclips.py <engine root> [--check]

1. PER-WEAPON RELOAD CLIPS. When the server asks for reload / reload_single / reload_end, the client first looks
   for an fps alias  coopr_<weapon key>_<suffix>  (weapon key = the configstring weapon name, lower case, every run
   of non-alphanumerics -> '_': "Mosin-Nagant Sniper" -> "mosin_nagant_sniper"); the exact name first, then the
   "(Finish)"-stripped base, so finish skins follow their gun. No such alias = the prefix clip, exactly as today.
   The aliases are data (models/player/base/anims_shared.txt, included by include_fps.txt), so every later
   phase B gun is a data change, not a cgame change. The ADS hook below still appends "_ads" to whatever was
   chosen (no coopr_*_ads row = the hip clip).
2. "Webley Mk VI" (the renamed colt45_colt1911w.tik, a Webley break-top mesh) -> WPREFIX_WEBLEY.
3. TEST-ONLY cvar coop_vmPrefixTest "<weapon name>=<prefix>" (default empty = off): swaps one gun's whole
   first-person prefix by name, so a batched slot run can compare hand sets without a rebuild.
Anchored edits; refuses on any anchor mismatch. --check = verify anchors / already-applied, write nothing.
"""
import sys, io, os

MARK = "HZM coop [reload audit phase B]"

E1_ANCHOR = '''        Com_sprintf(szAnimName, sizeof(szAnimName), "%s_%s", AnimPrefixList[iAnimPrefixIndex], pszAnimSuffix);
'''
E1_NEW = E1_ANCHOR + '''        // HZM coop [reload audit phase B] per-weapon reload clip (apply_reloadclips.py): coopr_<weapon key>_<suffix>
        // wins when the hands tiki has it - lets one gun of a shared prefix get the reload that fits ITS feed.
        if (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD || cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_SINGLE
            || cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_END) {
            CoopPerWeaponReloadAnim(pTiki, pszAnimSuffix, szAnimName, sizeof(szAnimName));
        }
'''

E2_ANCHOR = '''void CG_ViewModelAnimation(refEntity_t *pModel)
{'''
E2_NEW = '''// HZM coop [reload audit phase B] "Mosin-Nagant Sniper" -> "mosin_nagant_sniper"
static void CoopWeaponKey(const char *name, char *out, int outSize)
{
    int n = 0, gap = 0;

    for (; *name && n < outSize - 1; name++) {
        char c = *name;
        if (c >= 'A' && c <= 'Z') {
            c = c - 'A' + 'a';
        }
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) {
            if (gap && n > 0 && n < outSize - 2) {
                out[n++] = '_';
            }
            out[n++] = c;
            gap      = 0;
        } else {
            gap = 1;
        }
    }
    out[n] = 0;
}

// HZM coop [reload audit phase B] exact weapon name first, then the "(Finish)"-stripped base
static void CoopPerWeaponReloadAnim(dtiki_t *pTiki, const char *suffix, char *anim, int animSize)
{
    const char *wpn;
    char        base[64], key[64], tryName[MAX_QPATH];
    int         pass;

    if (!pTiki || !cg.snap || cg.snap->ps.activeItems[1] < 0) {
        return;
    }
    wpn = CG_ConfigString(CS_WEAPONS + cg.snap->ps.activeItems[1]);
    if (!wpn || !*wpn) {
        return;
    }
    for (pass = 0; pass < 2; pass++) {
        if (pass == 0) {
            CoopWeaponKey(wpn, key, sizeof(key));
        } else {
            if (!CoopStripSkinSuffix(wpn, base, sizeof(base))) {
                return;
            }
            CoopWeaponKey(base, key, sizeof(key));
        }
        Com_sprintf(tryName, sizeof(tryName), "coopr_%s_%s", key, suffix);
        if (cgi.Anim_NumForName(pTiki, tryName) != -1) {
            Q_strncpyz(anim, tryName, animSize);
            return;
        }
    }
}

void CG_ViewModelAnimation(refEntity_t *pModel)
{'''

E3_ANCHOR = '''    if (CoopStripSkinSuffix(szWeaponName, szSkinBase, sizeof(szSkinBase))) {
        szWeaponName = szSkinBase;
    }
'''
E3_NEW = E3_ANCHOR + '''
    // HZM coop [reload audit phase B] TEST-ONLY: coop_vmPrefixTest "<weapon name>=<prefix>" swaps one gun's
    // whole first-person prefix for a slot-run comparison. Default empty = off.
    {
        static cvar_t *pPrefixTest = NULL;
        const char    *eq;
        int            k;

        if (!pPrefixTest) {
            pPrefixTest = cgi.Cvar_Get("coop_vmPrefixTest", "", 0);
        }
        eq = pPrefixTest->string[0] ? strchr(pPrefixTest->string, '=') : NULL;
        if (eq && (int)(eq - pPrefixTest->string) == (int)strlen(szWeaponName)
            && !Q_stricmpn(pPrefixTest->string, szWeaponName, (int)(eq - pPrefixTest->string))) {
            for (k = 1; k < (int)(sizeof(AnimPrefixList) / sizeof(AnimPrefixList[0])); k++) {
                if (AnimPrefixList[k] && !Q_stricmp(AnimPrefixList[k], eq + 1)) {
                    return k;
                }
            }
        }
    }
'''

E4_ANCHOR = '''        if (!Q_stricmp(szWeaponName, "S&W M10 .38")) {
            return WPREFIX_M10;
        }
'''
E4_NEW = E4_ANCHOR + '''        // HZM coop [reload audit phase B] the renamed colt45_colt1911w.tik is a Webley break-top mesh (the pack
        // ships webley_* world anims for it): it takes the Webley's hands, and its torso is RELOAD_WEBLEY.
        if (!Q_stricmp(szWeaponName, "Webley Mk VI")) {
            return WPREFIX_WEBLEY;
        }
'''

EDITS = [(E2_ANCHOR, E2_NEW), (E1_ANCHOR, E1_NEW), (E3_ANCHOR, E3_NEW), (E4_ANCHOR, E4_NEW)]


def main():
    root = sys.argv[1]
    check = "--check" in sys.argv
    p = os.path.join(root, "code", "cgame", "cg_viewmodelanim.c")
    raw = io.open(p, "rb").read()
    crlf = b"\r\n" in raw
    s = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in s:
        print("already applied:", p)
        return 0
    for a, _ in EDITS:
        if s.count(a) != 1:
            print("ANCHOR MISMATCH (%d hits): %r" % (s.count(a), a[:70]))
            return 1
    if check:
        print("check OK:", p)
        return 0
    for a, b in EDITS:
        s = s.replace(a, b, 1)
    if crlf:
        s = s.replace("\n", "\r\n")
    io.open(p, "wb").write(s.encode("utf-8"))
    print("applied:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
