r"""cgame patch (ads-heavy-next worktree, cgame only): a VIEW-ANIM TRACE for the harness. With `coop_vmTrace 1` every
view-model row the cgame starts is printed as

    ^~^~^ VMANIM t=<cg.time> id=<view-anim id> row=<hands row> ads=<0|1> draw=<cg_drawviewmodel> wpn=<weapon name>

The ADSFRAME probe prints nothing while a scope picture is up (FG 42, run hh9), so it could not say whether a reload
played at all. Default 0: nothing is printed, no behaviour change.

    python apply_vmtrace.py <worktree>     (idempotent)
"""
import sys, os
W = sys.argv[1]
p = os.path.join(W, 'code/cgame/cg_viewmodelanim.c')
s = open(p, encoding='utf-8', newline='').read()
if 'coop_vmTrace' in s:
    print('already patched'); sys.exit(0)
nl = '\r\n' if '\r\n' in s else '\n'
a = ("        if (!bWeaponChanged) {\n"
     "            fCrossblendTime =\n"
     "                CoopVMCrossblend(").replace('\n', nl)
b = ("        {   // HZM coop [heavy lane 2026-10-13] harness trace of the row that starts now (apply_vmtrace.py)\n"
     "            static cvar_t *pTrace = NULL;\n"
     "            if (!pTrace) {\n"
     "                pTrace = cgi.Cvar_Get(\"coop_vmTrace\", \"0\", 0);\n"
     "            }\n"
     "            if (pTrace->integer) {\n"
     "                const char *wpnName = (cg.snap && cg.snap->ps.activeItems[1] >= 0)\n"
     "                                          ? CG_ConfigString(CS_WEAPONS + cg.snap->ps.activeItems[1])\n"
     "                                          : \"\";\n"
     "                cgi.Printf(\"^~^~^ VMANIM t=%d id=%d row=%s ads=%d draw=%d wpn=%s\\n\", cg.time, cgi.anim->g_iLastVMAnim, szAnimName,\n"
     "                           s_coopAdsClip ? 1 : 0, cg_drawviewmodel ? cg_drawviewmodel->integer : -1, wpnName ? wpnName : \"\");\n"
     "            }\n"
     "        }\n").replace('\n', nl)
assert s.count(a) == 2, s.count(a)          # the FIRST site is where a new row has just been chosen (the second re-blends a swap)
s = s.replace(a, b + a, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('code/cgame/cg_viewmodelanim.c patched')
