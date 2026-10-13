"""cgame (ads-next): the S&W M10's loose chamber heads on ANOTHER PLAYER'S gun (pistol lane, 2026-10-13).

Before: only the local player's held gun counted its coop_round<N> surfaces; every other M10 drew all six heads at all
times - also through that player's whole one-by-one reload. Another client is not told a player's clip count, but it
does see the gun's own rows (`reload` = the cylinder opens, `reload_single` once per round, `reload_end`). So the gun
of another player follows the same rule as the local one with the count taken from the rows it plays:
    outside a reload     all heads (as the local gun: a fired case looks like a live round from behind)
    `reload`             all heads until the cases are dumped (0.70 s into the row), then none
    `reload_single`      as many as loops have ended (latched like the local gun: the new head shows when the loop
                         restarts, once its chamber has turned away from the feed position)
    `reload_end`         the loops that were played
A reload with rounds left reads low by those rounds while it lasts (the count is not on the wire); a full reload of an
emptied gun is exact.
    coop_vmRoundOthers   1 = the above (default), 0 = another player's gun draws all six as before, 2 = also print it
    coop_vmRoundSurfaces 2 = TEST: the local gun is driven by the same estimate (what another player sees of it; with
                             the third-person camera this is the check without a second client)
Inert for a gun without a coop_round1 surface.

    python patch_cg_roundothers.py [worktree]        idempotent
"""
import sys, os, io
WT = sys.argv[1] if len(sys.argv) > 1 else r"C:\mohaa-coop-dev\openmohaa-hzm-ads"
P = os.path.join(WT, 'code', 'cgame', 'cg_modelanim.c')
s = io.open(P, encoding='latin-1', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
if 'coop_vmRoundOthers' in s:
    print('already patched'); sys.exit(0)

ANCHOR = "    CG_InterpolateAnimParms(s1, sNext, &model);" + nl + "    // HZM coop [aimed reload 2026-10-12] THE GUN'S OWN ANIMATION IN AN AIMED RELOAD"
assert s.count(ANCHOR) == 1, s.count(ANCHOR)
NEW = r'''    CG_InterpolateAnimParms(s1, sNext, &model);
    // HZM coop [revolver chambers 2026-10-13] ANOTHER PLAYER'S GUN. Only the local player's held gun counted its
    // coop_round<N> heads (below); every other one drew all six at all times, also through that player's whole
    // one-by-one reload. Another client is not told the clip count, but it sees the rows the gun plays, so the count
    // is taken from them: outside a reload all heads (as the local gun); in `reload` all until the cases are dumped
    // (0.70 s), then none; in `reload_single` one more each time the loop restarts (latched like the local gun);
    // in `reload_end` the loops that were played. A reload with rounds left reads low by those rounds while it
    // lasts. coop_vmRoundOthers 0 = all six as before, 2 = print; coop_vmRoundSurfaces 2 = TEST, the local gun is
    // driven by this estimate too (what another player sees of it). Inert without a coop_round1 surface.
    if (model.tiki && cg.snap && s1->parent != ENTITYNUM_NONE) {
        static cvar_t *pRnd = NULL, *pOth = NULL;
        if (!pRnd) {
            pRnd = cgi.Cvar_Get("coop_vmRoundSurfaces", "1", 0);
            pOth = cgi.Cvar_Get("coop_vmRoundOthers", "1", 0);
        }
        if (pRnd->integer && pOth->integer && (s1->parent != cg.snap->ps.clientNum || pRnd->integer == 2)
            && cgi.Surface_NameToNum(model.tiki, "coop_round1") >= 0) {
            static struct {
                int   ent, seen, est, shown, printed;
                float loopT;
            } s_o[4];
            static const char *const s_oAnim[3] = {"reload", "reload_single", "reload_end"};
            int      iA[3], n, q, slot = -1, oldest = 0, show;
            float    tOpen = -1.0f, tLoop = -1.0f;
            qboolean bEnd = qfalse;
            for (q = 0; q < 3; q++) {
                iA[q] = cgi.Anim_NumForName(model.tiki, s_oAnim[q]);
            }
            for (n = 0; n < MAX_FRAMEINFOS; n++) {
                if (!model.frameInfo[n].weight || model.frameInfo[n].index < 0) {
                    continue;
                }
                if (model.frameInfo[n].index == iA[0]) {
                    tOpen = model.frameInfo[n].time;
                } else if (model.frameInfo[n].index == iA[1]) {
                    tLoop = model.frameInfo[n].time;
                } else if (model.frameInfo[n].index == iA[2]) {
                    bEnd = qtrue;
                }
            }
            for (n = 0; n < 4; n++) {
                if (s_o[n].ent == s1->number + 1) {
                    slot = n;
                }
                if (s_o[n].seen < s_o[oldest].seen) {
                    oldest = n;
                }
            }
            if (slot < 0 || cg.time - s_o[slot].seen > 500 || cg.time < s_o[slot].seen) {
                if (slot < 0) {
                    slot = oldest;
                }
                s_o[slot].ent     = s1->number + 1;
                s_o[slot].est     = 0;
                s_o[slot].shown   = 0;
                s_o[slot].loopT   = -1.0f;
                s_o[slot].printed = -2;
            }
            s_o[slot].seen = cg.time;
            if (tLoop >= 0.0f) {
                if (s_o[slot].loopT < 0.0f) {
                    s_o[slot].shown = s_o[slot].est; // the loop starts
                } else if (tLoop < s_o[slot].loopT - 0.1f) {
                    s_o[slot].est++; // it restarts: the round seated in the pass that just ended counts now
                    s_o[slot].shown = s_o[slot].est;
                }
                s_o[slot].loopT = tLoop;
                show            = s_o[slot].shown;
            } else if (bEnd) {
                if (s_o[slot].loopT >= 0.0f) {
                    s_o[slot].est++; // the last pass's round
                    s_o[slot].loopT = -1.0f;
                }
                show = s_o[slot].est;
            } else if (tOpen >= 0.0f) {
                s_o[slot].est   = 0;
                s_o[slot].loopT = -1.0f;
                show            = tOpen < 0.70f ? 99 : 0;
            } else {
                s_o[slot].est   = 0;
                s_o[slot].loopT = -1.0f;
                show            = 99;
            }
            if (pOth->integer == 2 && show != s_o[slot].printed) {
                cgi.Printf("^~^~^ ROUNDOTHER ent %d parent %d show %d (open %.2f loop %.2f end %d) t %d\n", s1->number, s1->parent,
                           show, tOpen, tLoop, (int)bEnd, cg.time);
                s_o[slot].printed = show;
            }
            s_coopRoundShow = show;
            s_coopRoundEnt  = s1->number;
        }
    }
    // HZM coop [aimed reload 2026-10-12] THE GUN'S OWN ANIMATION IN AN AIMED RELOAD'''.replace('\n', nl)
s = s.replace(ANCHOR, NEW, 1)

OLD2 = 'sn1 = pRounds->integer ? cgi.Surface_NameToNum(model.tiki, "coop_round1") : -1;'
assert s.count(OLD2) == 1
s = s.replace(OLD2, '// 2 = TEST: the local gun is driven by the other-player estimate above (pistol lane 2026-10-13)' + nl
              + '            sn1 = (pRounds->integer && pRounds->integer != 2) ? cgi.Surface_NameToNum(model.tiki, "coop_round1") : -1;', 1)
io.open(P, 'w', encoding='latin-1', newline='').write(s)
print('patched', P)
