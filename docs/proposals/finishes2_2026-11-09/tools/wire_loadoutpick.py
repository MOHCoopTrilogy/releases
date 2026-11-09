"""finishes2 wiring (v1.10.68): coop_mod/loadoutpick.scr + coop_mod/challenges.scr edits, binary-safe and count-asserted.

    python wire_loadoutpick.py <mod tree> [--apply]

loadoutpick.scr
  loadout_finish         fids 40-59 are FINISHES: the finish branch (loadout_finOpen gate, coop_loS<n>F, finp re-preview), never the
                         model-variant cycle (8-19); the range check admits them
  loadout_finResolve     the model-variant gates apply to 8-39 only; 40+ go through loadout_finOpen like 1-7
  loadout_slotLocksExport  the second chip row: per slot, one verdict per finishes2 fid (coop_loMast<n>_<F> = lkc<F>_<0|1>.cfg) and the
                         locked ones' progress (coop_loFq<n>_<F>), in the same diff-guarded push as the first row
challenges.scr
  chal_finSeed           O(challenges) instead of O(challenges x challenges-per-stat): finishes2 adds 13 rungs per gun, ~900 seeds
"""
import os
import sys

MOD = sys.argv[1]
APPLY = "--apply" in sys.argv


def edit(rel, pairs):
    p = os.path.join(MOD, *rel.split("/"))
    b = open(p, "rb").read()
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n")
    assert crlf == lf, "%s: mixed line endings (%d CRLF / %d LF)" % (rel, crlf, lf)
    t = b.decode("latin-1").replace("\r\n", "\n")
    for old, new in pairs:
        n = t.count(old)
        if n == 0 and t.count(new) == 1:
            print("  %s: already applied: %s" % (rel, old.strip().splitlines()[0][:70]))
            continue
        assert n == 1, "%s: anchor found %d times: %r" % (rel, n, old[:90])
        t = t.replace(old, new)
    out = t.replace("\n", "\r\n").encode("latin-1")
    assert out.count(b"\r\n") == out.count(b"\n")
    print("%s: %+d bytes" % (rel, len(out) - len(b)))
    if APPLY:
        open(p, "wb").write(out)


LP = []
LP.append(("""	if(local.fid < 0 || local.fid > 19){ end }	//[2026-08-19] MV wave 3: springfield hosts 10 variants (fids 8-17)
""", """	if(local.fid < 0 || local.fid > 59){ end }	//[2026-08-19] MV wave 3: springfield hosts 10 variants (fids 8-17)
	if(local.fid > 19 && local.fid < 40){ end }	//[v1.10.68 finishes2] 20-39 unused; 40-59 = the second finish set
"""))
LP.append(("""	//---------------- finishes (1-7): unchanged gates -------------------------------------------
	if(local.fid <= 7){
""", """	//---------------- finishes (1-7, and finishes2 40+): unchanged gates ---------------------------
	//[v1.10.68 finishes2] fids 40+ are FINISHES (paint, camo, layered), not model variants: same gate (loadout_finOpen = this gun's
	//own rung on its kill ladder, finchal_gen.scr), same archive, same finp re-preview page
	if(local.fid <= 7 || local.fid >= 40){
"""))
LP.append(("""	if(local.fid >= 8){
		if(!(waitthread loadout_mvUnlocked local.player local.give local.fid)){ end local.give }
""", """	if(local.fid >= 8 && local.fid < 40){	//[v1.10.68 finishes2] 40+ are finishes: loadout_finOpen below
		if(!(waitthread loadout_mvUnlocked local.player local.give local.fid)){ end local.give }
"""))
# the second chip row's verdicts, computed with the first row's
LP.append(("""		if(local.player == NULL){ end }
		local.key = local.sid + "|" + local.mast + "|" + local.mvlk + "|" + local.txt + "|" + local.fk + "|" + local.fqt[1] + "|" + local.fqt[2] + "|" + local.fqt[3] + "|" + local.fqt[4] + "|" + local.fqt[5] + "|" + local.fqt[6] + "|" + local.fqt[7]
""", """		if(local.player == NULL){ end }
		//[v1.10.68 finishes2] the SECOND chip row (fids level.coop_fs2Fid[], loadoutskins.scr): open = this gun's own rung on its kill
		//ladder (level.coop_finCid[wid][fid], finish_challenges.py). No legacy account token exists for these. The wid is resolved once
		//per slot (chal_widFromModel is a long containsText chain); a gun without that finish, or with no kill stat, stays locked.
		local.f2k = ""
		local.k2 = ""
		local.w2 = ""
		if(local.sid != "" && local.give != NIL && local.give != "" && getcvar("coop_lockLoadout") != "0"){
			local.w2 = waitthread coop_mod/challenges.scr::chal_widFromModel local.give
			if(local.w2 == NIL){ local.w2 = "" }
			waitthread coop_mod/challenges.scr::chal_ensure local.player
			if(local.player == NULL){ end }
		}
		for(local.q = 0; local.q < level.coop_fs2FidN; local.q++){
			local.F = level.coop_fs2Fid[local.q]
			local.flk = 0
			local.fqt2[local.F] = ""
			if(getcvar("coop_lockLoadout") != "0" && local.sid != ""){
				local.flk = 1
				local.c2 = ""
				if(local.w2 != ""){
					if(level.coop_skinGive[local.give][local.F] != NIL){ local.c2 = level.coop_finCid[local.w2][local.F] }
				}
				if(local.c2 != NIL && local.c2 != ""){
					if(local.player.flags["coop_chalD_" + local.c2] == 1){
						local.flk = 0
					} else {
						local.ix2 = level.coop_chal_idx[local.c2]
						if(local.ix2 != NIL){
							local.cur2 = local.player.flags["coop_chalP_" + local.c2]
							if(local.cur2 == NIL){ local.cur2 = 0 }
							local.need2 = level.coop_chal_target[local.ix2]
							if(local.cur2 > local.need2){ local.cur2 = local.need2 }
							local.nm2 = level.coop_finGunName[local.w2]
							if(local.nm2 == NIL){ local.nm2 = local.w2 }
							local.fqt2[local.F] = "" + int(local.cur2) + " / " + local.need2 + " " + local.nm2 + " kills"
							if( local.fqt2[local.F].size > 24 ){ local.fqt2[local.F] = "" + int(local.cur2) + " / " + local.need2 + " " + local.nm2 }
						}
					}
				}
			}
			local.f2k = local.f2k + local.flk
			local.k2 = local.k2 + "|" + local.fqt2[local.F]
		}
		local.key = local.sid + "|" + local.mast + "|" + local.mvlk + "|" + local.txt + "|" + local.fk + "|" + local.fqt[1] + "|" + local.fqt[2] + "|" + local.fqt[3] + "|" + local.fqt[4] + "|" + local.fqt[5] + "|" + local.fqt[6] + "|" + local.fqt[7] + "|" + local.f2k + local.k2
"""))
LP.append(("""				local.f++
			}
			waitframe
			if(local.player == NULL){ end }
			if(local.mvlk == 1){
""", """				local.f++
			}
			waitframe
			if(local.player == NULL){ end }
			//[v1.10.68 finishes2] the second row: lkc<F>_<0|1>.cfg per fid (lkfs<n>.cfg applies them), progress for the locked ones
			for(local.q = 0; local.q < level.coop_fs2FidN; local.q++){
				local.F = level.coop_fs2Fid[local.q]
				local.player stufftext ( "seta coop_loMast" + local.sl + "_" + local.F + " exec ui/loadout/lkc" + local.F + "_" + local.f2k[local.q] + ".cfg" )
				if(local.fqt2[local.F] != ""){
					local.player stufftext ( "seta coop_loFq" + local.sl + "_" + local.F + " set coop_loFinNm " + local.fqt2[local.F] )
				}
				if(local.q == 6){
					waitframe
					if(local.player == NULL){ end }
				}
			}
			waitframe
			if(local.player == NULL){ end }
			if(local.mvlk == 1){
"""))

CH = []
CH.append(("""chal_finSeed local.player:{
	if( local.player == NULL ){ end }
	local.i = level.coop_chal_srCount
	while( local.i < level.coop_chal_count ){
		local.cid = level.coop_chal_id[local.i]
		if( level.coop_finIs[local.cid] == 1 && local.player.flags["coop_chalP_" + local.cid] == NIL ){
			local.stat = level.coop_chal_stat[local.i]
			local.m = 0
			local.cnt = level.coop_chal_statN[local.stat]
			for( local.k = 0; local.k < local.cnt; local.k++ ){
				local.j = level.coop_chal_statIdx[local.stat][local.k]
				local.pj = local.player.flags["coop_chalP_" + level.coop_chal_id[local.j]]
				if( local.pj != NIL && local.pj > local.m ){ local.m = local.pj }
			}
			if( local.m > level.coop_chal_target[local.i] ){ local.m = level.coop_chal_target[local.i] }
			if( local.m > 0 ){ local.player.flags["coop_chalP_" + local.cid] = local.m }
		}
		local.i++
	}
}end
""", """chal_finSeed local.player:{
	if( local.player == NULL ){ end }
	//[v1.10.68 finishes2] the best progress per STAT is found once (pass 1), not once per unseeded finish rung: finishes2 adds 13 rungs per
	//gun (~900), and the old nested scan was O(rungs x challenges-per-stat) in one frame at join. Same result: a rung with no progress yet
	//starts at the best progress any challenge on its stat holds, capped at its target.
	local.best["-"] = 0
	local.i = 0
	while( local.i < level.coop_chal_count ){
		local.pj = local.player.flags["coop_chalP_" + level.coop_chal_id[local.i]]
		if( local.pj != NIL ){
			local.stat = level.coop_chal_stat[local.i]
			if( local.best[local.stat] == NIL || local.pj > local.best[local.stat] ){ local.best[local.stat] = local.pj }
		}
		local.i++
	}
	local.i = level.coop_chal_srCount
	while( local.i < level.coop_chal_count ){
		local.cid = level.coop_chal_id[local.i]
		if( level.coop_finIs[local.cid] == 1 && local.player.flags["coop_chalP_" + local.cid] == NIL ){
			local.m = local.best[level.coop_chal_stat[local.i]]
			if( local.m == NIL ){ local.m = 0 }
			if( local.m > level.coop_chal_target[local.i] ){ local.m = level.coop_chal_target[local.i] }
			if( local.m > 0 ){ local.player.flags["coop_chalP_" + local.cid] = local.m }
		}
		local.i++
	}
}end
"""))

edit("coop_mod/loadoutpick.scr", LP)
edit("coop_mod/challenges.scr", CH)
if not APPLY:
    print("(dry run - pass --apply)")
