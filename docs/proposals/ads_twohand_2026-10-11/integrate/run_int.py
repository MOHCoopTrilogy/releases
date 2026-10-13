"""run_int.py - engine runs of the ADS integration on the private harness copy G:\\mohaa-hudfeed (owner "hudfeed",
net_port 12701, DISPLAY2 through harness_window only, never focused). Never touches G:\\mohaa-gl2 or the GOG root
(the GOG root is the read-only basepath).

    python run_int.py run <session> --bins <folder with exe/cgame/game/renderers> --code <mod rev> [--fixes <pk3>]
                          --guns bar,mp44,...  [--shot]
    python run_int.py ded <session> ...same options...       the same scenario against OUR dedicated server (omohaaded
                          from --bins, home G:\\mohaa-hudfeed\\home_srv_integ, 127.0.0.1:12702) with one client joined;
                          cvars and markers go through rcon; qconsole.log of the run = the SERVER log, client.log = client
    python run_int.py show <session> [--guns ...]            what each gun did, phase by phase
    python run_int.py aimed <session> [--guns ..]            client trace of the aimed phases (sight line, rounds seen)
    python run_int.py rows <session> [--guns ..] [--fixes-rev <docs rev>]   the hands row each phase played, by name
    python run_int.py cmp <sessionA> <sessionB> [--guns ..]  server timing A against B (reload, refill, fire states)
    python run_int.py errs <session> [<baseline session>]    error / missing-asset lines (new ones against a baseline)

What a session loads:  basepath = GOG root (retail + third-party paks + the DEPLOYED coop paks), and in the harness home:
  zzzzzz_co-op_hzm_mod_code.pk3   the mod's script bucket at --code (git archive of hzm-mohaa-coop-mod at that rev)
  zzzzzzzzzz_coop_fixes.pk3       --fixes (the REAL built fixes pak); without it the deployed (released) one is used
  zzzzzzzzzzzz_integtest.pk3      harness plumbing only: coop_mod/weather.scr of --code + the place/give hook and a
                                  SERVER-SIDE probe that prints the torso state and the reserve ammo when they change
                                  (^~^~^ INTP t=<level.time> st=<state> am=<reserve>) - the same probe for every build,
                                  so released and integrated runs are timed by the server, not by the client.
Client side: coop_reloadDebug 1 prints ^~^~^ WFEEL state=<view anim id> len=<length of the hands clip now playing>.
Per gun: hip fire, hip reload (rounds left), aim, aimed fire, aimed reload (rounds left), aimed emptied + reload,
crouched aimed fire + reload, hip emptied + reload.
"""
import hashlib, json, os, re, shutil, subprocess, sys, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import intlib as L
sys.path.insert(0, os.path.join(L.ROOT, 'docs', 'proposals', 'ironsights_2026-09-28', 'tools'))

CLIENT = r'G:\mohaa-hudfeed'
RUNS = 'G:/mohaa-hudfeed/runs_integ'
SCR = os.path.join(os.environ.get('INTEG_CACHE', os.path.join(os.environ.get('TEMP', '.'), 'integ_ads_cache')))
EXE = 'openmohaa_integ8.exe'
W = 'models/weapons/'
# key: (tik, class, reload wait ms)
GUNS = {
    'bar': ('bar.tik', 'auto', 5500), 'bar1918a': ('bar_bar1918a.tik', 'auto', 5500), 'bar1918a2': ('bar_bar1918a2.tik', 'auto', 5500),
    'barpa': ('bar_pabar.tik', 'auto', 5500), 'bar_gold': ('bar_gold.tik', 'auto', 5500),
    'mp44': ('mp44.tik', 'auto', 5500), 'mp44strap': ('mp44_mp44strap.tik', 'auto', 5500), 'mp44_gold': ('mp44_gold.tik', 'auto', 5500),
    'dp28': ('dp28.tik', 'auto', 6500), 'dp28_chrome': ('dp28_chrome.tik', 'auto', 6500),
    'shotgun': ('shotgun.tik', 'pump', 7500), 'sggold': ('shotgun_gold.tik', 'pump', 7500), 'sgcamo': ('shotgun_camo_winter.tik', 'pump', 7500),
    'mp40': ('mp40.tik', 'auto', 5000), 'mp40sil': ('mp40silenced.tik', 'auto', 5000), 'mp40_gold': ('mp40_gold.tik', 'auto', 5000),
    'kar98': ('kar98.tik', 'bolt', 5500), 'kar98_lite': ('kar98_lite.tik', 'bolt', 5500), 'springfield': ('springfield_unscoped.tik', 'bolt', 9000),
    'mosin': ('mosin_nagant_rifle.tik', 'bolt', 5500), 'enfield': ('enfield.tik', 'bolt', 6500),
    # out of scope - regression
    'colt45': ('colt45.tik', 'semi', 4500), 'thompson': ('thompsonsmg.tik', 'auto', 5000), 'sten': ('sten.tik', 'auto', 5000),
    'garand': ('m1_garand.tik', 'semi', 5000), 'fg42': ('FG42.tik', 'auto', 5500), 'lewis': ('bar_bar1918.tik', 'auto', 6500),
    'mp18': ('mp40_mp18.tik', 'auto', 5500),
    'grease': ('greasegun.tik', 'auto', 5000), 'pps43': ('ppsh43silenced.tik', 'auto', 5000), 'mp40r2': ('mp40_mp40r2.tik', 'auto', 5000),
    'kar98_winter': ('kar98_camo_winter.tik', 'bolt', 5500), 'mosin_gold': ('mosin_nagant_rifle_gold.tik', 'bolt', 5500),
    'mosin_lite': ('mosin_nagant_rifle_lite.tik', 'bolt', 5500), 'enfield_gold': ('enfield_gold.tik', 'bolt', 6500),
    'enfield_lite': ('enfield_lite.tik', 'bolt', 6500), 'g98': ('kar98_g98.tik', 'bolt', 5500),
    # ---- pass 2, step 4: pistols (class semi = magazine pistol, rev = revolver loaded round by round, bolt = Welrod)
    'colt45_gold': ('colt45_gold.tik', 'semi', 4500), 'guancolt': ('colt45_guancolt.tik', 'semi', 4500), 'coltpa': ('colt45_coltpa.tik', 'semi', 4500),
    'coltsil': ('colt_silenced.tik', 'semi', 4500), 'dbno': ('dbno_pistol.tik', 'semi', 4500),
    'p38': ('p38.tik', 'semi', 4500), 'p38tt': ('p38_lv_ttp38.tik', 'semi', 4500), 'p38sil': ('p38silenced.tik', 'semi', 4500),
    'beretta': ('it_w_beretta.tik', 'semi', 4500), 'berettasil': ('berettasilenced.tik', 'semi', 4500),
    'luger': ('lugerp08.tik', 'semi', 4500), 'lugersil': ('lugerp08silenced.tik', 'semi', 4500), 'nambu': ('nambu.tik', 'semi', 4500),
    'ppk': ('ppk.tik', 'semi', 4500), 'tt33': ('tt33.tik', 'semi', 4500), 'tt33sil': ('tt33silenced.tik', 'semi', 4500),
    'welrod': ('welrod.tik', 'bolt', 4500), 'histd': ('silencedpistol.tik', 'bolt', 4500),
    'webley': ('webley_revolver.tik', 'rev', 9000), 'webley_gold': ('webley_revolver_gold.tik', 'rev', 9000),
    'webley_desert': ('webley_revolver_camo_desert.tik', 'rev', 9000), 'webleytt': ('webley_revolver_lv_ttwebley.tik', 'rev', 9000),
    'mk6': ('colt45_colt1911w.tik', 'rev', 9000), 'nagant': ('nagant_revolver.tik', 'rev', 10500),
    'nagant_blued': ('nagant_revolver_blued.tik', 'rev', 10500), 'nagant_bloody': ('nagant_revolver_bloody.tik', 'rev', 10500),
    # held out by the pistol lane (must stay as released)
    'c96': ('mauser_c96.tik', 'semi', 5500), 'm10': ('m10_revolver.tik', 'rev', 6000),
    # ---- pass 2, step 5
    'g43': ('g43.tik', 'semi', 5000), 'g43irons': ('coop_g43_irons.tik', 'semi', 5000), 'g43irons_gold': ('coop_g43_irons_gold.tik', 'semi', 5000), 'g43irons_fleck': ('coop_g43_irons_dhg43fleck.tik', 'semi', 5000),
    # ---- pass 3, step B: the double barrel (class dbl = 2 shells, loaded one by one)
    'dbs': ('coop_dbshotgun.tik', 'dbl', 4500), 'dbs_gold': ('coop_dbshotgun_gold.tik', 'dbl', 4500), 'dbs_winter': ('coop_dbshotgun_camo_winter.tik', 'dbl', 4500),
}
GAP = {'semi': 450, 'bolt': 2100, 'pump': 1600, 'rev': 800, 'dbl': 450}
PRONE = ('colt45', 'p38', 'beretta', 'tt33', 'welrod', 'histd', 'webley', 'nagant', 'luger', 'c96', 'm10', 'coltsil', 'ppk', 'nambu')    # + a prone phase


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def tik_facts(tik):
    v = L.Vfs(L.FIX)
    t = v.read(W + tik).decode('latin-1')
    clip = int(re.search(r'(?mi)^\s*clipsize\s+(\d+)', t).group(1))
    ammo = re.search(r'(?mi)^\s*ammotype\s+"?(\w+)"?', t).group(1)
    return clip, ammo, L.tik_name(t)


def fire(cls, n, clip):
    if cls == 'auto':
        ms = 250 if n < clip else clip * 160 + 900
        return ['+attackprimary', 'wait %d' % ms, '-attackprimary']
    out = []
    for _k in range(n):
        out += ['+attackprimary', 'wait 70', '-attackprimary', 'wait %d' % GAP[cls]]
    return out


def scenario(key, shot):
    tik, cls, rw = GUNS[key]
    clip, ammo, _name = tik_facts(tik)
    burst = 2 if cls != 'auto' else 3
    m = lambda ph: ['echo ^~^~^ INTM %s %s' % (key, ph)]
    Lc = ['set coop_intAmmo %s' % ammo]
    if cls == 'dbl':
        # pass 3, the double barrel: one barrel + reload with a shell left, both barrels (the gun opens by itself 1.2 s
        # after the last shell), the same aimed, a reload broken off by the trigger. ONE picture (aim) with --shot.
        one = ['+attackprimary', 'wait 70', '-attackprimary']
        both = one + ['wait 450'] + one
        Lc += m('hipfire') + one + ['wait 1500']
        Lc += m('hipreload') + ['reload', 'wait 4500']
        Lc += m('hipempty') + both + ['wait 6500']
        Lc += m('aim') + ['+button13', 'wait 1900']
        if '--shot' in sys.argv and key == 'dbs':
            Lc += ['screenshot int_%s' % key, 'wait 150']
        Lc += m('aimfire') + ['set cg_adsSightDebug 2'] + one + ['wait 1500']
        Lc += m('aimreload') + ['reload', 'wait 4500']
        Lc += m('aimempty') + both + ['wait 6500', 'set cg_adsSightDebug 1', '-button13', 'wait 900']
        Lc += m('breakoff') + one + ['wait 1500', 'reload', 'wait 600'] + one + ['wait 3500', 'reload', 'wait 4500']
        Lc += m('end')
        return Lc
    if cls == 'pump' and '--pumpsheet' in sys.argv:
        # step 7, the look the coordinator asked for: a picture 0.45 s after aimed shots 1, 3 and 5 (the LAST shell) and
        # after three hip shots - hull in the air, support hand at the rear of its stroke
        one = lambda tag: ['+attackprimary', 'wait 70', '-attackprimary', 'wait 380', 'screenshot pump_%s' % tag, 'wait %d' % (GAP[cls] - 380)]
        two = ['+attackprimary', 'wait 70', '-attackprimary', 'wait %d' % GAP[cls]]
        Lc += m('aim') + ['+button13', 'wait 1900', 'screenshot pump_aim0', 'wait 200']
        Lc += m('aimempty') + one('aim1') + two + one('aim3') + two + one('aim5_last') + ['wait 6500', '-button13', 'wait 900', 'screenshot pump_hip0', 'wait 200']
        Lc += m('hipfire') + one('hip1') + one('hip2') + one('hip3') + ['wait 1300'] + m('end')
        return Lc
    Lc += m('hipfire') + fire(cls, burst, clip) + ['wait 1300']
    Lc += m('hipreload') + ['reload', 'wait %d' % rw]
    Lc += m('aim') + ['+button13', 'wait 1900']
    if shot:
        Lc += ['screenshot int_%s' % key, 'wait 150']
    if cls == 'pump' and shot:
        # step 7: ONE picture 0.45 s after an aimed shot (the hull leaves at 0.35 s, the forend / hand are at the rear)
        Lc += m('aimfire') + ['set cg_adsSightDebug 2', '+attackprimary', 'wait 70', '-attackprimary', 'wait 380', 'screenshot int_%s_pump' % key,
                              'wait %d' % (GAP[cls] - 380)] + fire(cls, burst - 1, clip) + ['wait 1300']
    else:
        Lc += m('aimfire') + ['set cg_adsSightDebug 2'] + fire(cls, burst, clip) + ['wait 1300']
    Lc += m('aimreload') + ['reload', 'wait %d' % rw]
    Lc += m('aimempty') + fire(cls, clip, clip) + ['wait 700', 'reload', 'wait %d' % (rw + 1500), 'set cg_adsSightDebug 1']
    Lc += m('crouch') + ['set coop_proneHold 999', '+movedown', 'wait 1200'] + fire(cls, burst, clip) + ['wait 1300', 'reload',
                                                                                                       'wait %d' % rw, '-movedown', 'wait 800', 'set coop_proneHold 0.5']
    if key in PRONE:
        # prone (run_ironsights: the crouch key held for coop_proneHold), aimed: fire + reload - the declared prone pistol reload
        Lc += m('prone') + ['set coop_proneHold 0.5', '+movedown', 'wait 900', '-movedown', 'wait 2200'] + fire(cls, burst, clip) + [
            'wait 1300', 'reload', 'wait %d' % (rw + 600), '+movedown', 'wait 200', '-movedown', 'wait 2500']
    Lc += ['-button13', 'wait 900']
    Lc += m('hipempty') + fire(cls, clip, clip) + ['wait 700', 'reload', 'wait %d' % (rw + 1500)]
    if cls == 'pump':
        # the trigger pressed in the middle of a reload: a round is chambered (quick break-off) / the gun was empty
        Lc += m('breakoff') + fire(cls, burst, clip) + ['wait 1300', 'reload', 'wait 1500', '+attackprimary', 'wait 70', '-attackprimary', 'wait 3500',
                                                       'reload', 'wait %d' % rw]
        Lc += m('breakempty') + fire(cls, clip, clip) + ['wait 700', 'reload', 'wait 2100', '+attackprimary', 'wait 70', '-attackprimary', 'wait 3500',
                                                        'reload', 'wait %d' % rw]
    if shot and '--weather' in sys.argv:
        # rain fix (rainfix-next 5376f59e): ONE level picture at the hip with the weather pinned, a minute into the session
        Lc += ['wait 800', 'screenshot int_rain', 'wait 300']
    Lc += m('end')
    return Lc


HOOK = '''	if( getcvar( "coop_isPoll" ) == "1" ){ thread coop_is_test }	//TEST OVERLAY ONLY
	if( getcvar( "coop_isPoll" ) == "1" ){ thread coop_int_probe }	//TEST OVERLAY ONLY
	if( getcvar( "coop_isPoll" ) == "1" ){ thread coop_int_xt }	//TEST OVERLAY ONLY
'''
FUNCS = '''
//TEST OVERLAY ONLY (integrate/run_int.py): place + face + give, and the server-side timing probe.
coop_is_test:{
	local.last = ""
	while( 1 ){
		local.s = getcvar( "coop_isSeq" )
		if( local.s != "" && local.s != local.last && $player != NULL && $player.size >= 1 ){
			local.last = local.s
			local.p = $player[1]
			local.p nodamage
			local.p notarget 1
			local.x = float( getcvar( "coop_isX" ) )
			local.y = float( getcvar( "coop_isY" ) )
			local.z = float( getcvar( "coop_isZ" ) )
			local.pi = float( getcvar( "coop_isPitch" ) )
			local.w = float( getcvar( "coop_isYaw" ) )
			local.t = getcvar( "coop_isTik" )
			local.p.origin = ( local.x local.y local.z )
			local.p.viewangles = ( local.pi local.w 0 )
			local.p.velocity = ( 0 0 0 )
			if( local.t != "" && local.t != "none" ){
				local.p.flags["coop_chal_unlocks"] = local.t
				local.p give local.t
				local.p ammo smg 400
				local.p ammo mg 400
				local.p ammo rifle 400
				local.p ammo pistol 400
				local.p ammo shotgun 400
				wait 0.3
				local.p use local.t
				for( local.k = 1; local.k <= 3; local.k++ ){
					wait 0.7
					local.p use local.t
				}
			}
			println( "^~^~^ ISTEST seq=" + local.s + " tik=" + local.t + " at " + local.p.origin + " ang " + local.p.viewangles )
		}
		waitframe
	}
}end

coop_int_probe:{
	local.ls = ""
	local.lm = ""
	local.la = 0 - 1
	while( 1 ){
		if( $player != NULL && $player.size >= 1 ){
			local.p = $player[1]
			local.s = local.p gettorsostate
			local.mk = getcvar( "coop_intMark" )
			if( local.mk != local.lm ){
				local.lm = local.mk
				println( "^~^~^ INTM " + local.mk )
			}
			local.ty = getcvar( "coop_intAmmo" )
			local.a = 0
			if( local.ty != "" ){ local.a = local.p getammo local.ty }
			if( local.s != local.ls || local.a != local.la ){
				println( "^~^~^ INTP t=" + level.time + " st=" + local.s + " am=" + local.a )
				local.ls = local.s
				local.la = local.a
			}
		}
		waitframe
	}
}end
'''


FUNCS += '''
//TEST OVERLAY ONLY - the UNLOCK PATH probe (the rifles lane's srvtime_ov.py xpprobe, run_unlock.py): coop_xtCmd = one word
coop_int_xt:{
	while( 1 ){
		local.c = getcvar( "coop_xtCmd" )
		if( local.c != "" && $player != NULL && $player.size >= 1 ){
			setcvar "coop_xtCmd" ""
			local.p = $player[1]
			if( local.p.flags["coop_xp_id"] == NIL ){ waitthread coop_mod/xp.scr::xp_identify local.p }
			waitthread coop_mod/challenges.scr::chal_ensure local.p
			if( local.c == "seed" ){
				waitthread coop_mod/challenges.scr::chal_add_unlock local.p "models/weapons/bar.tik"
				waitthread coop_mod/challenges.scr::chal_add_unlock local.p "models/weapons/kar98sniper.tik"
				println "^~^~^ XT seed done"
			}
			if( local.c == "under2" ){
				local.thr = level.coop_xp_rankXP[2]
				local.gain = int( 10 * level.coop_xp_scale )
				local.pre = local.thr + 2 - local.gain
				local.p.flags["coop_xp_total"] = local.pre
				local.p.flags["coop_xp_rank"] = 1
				local.p.flags["coop_xp_barMark"] = int( local.pre / 100 )
				local.p.flags["coop_xp_popupOn"] = NIL
				local.p.flags["coop_xp_ceremony"] = NIL
				thread coop_mod/loadoutpick.scr::loadout_ui_exportUnlocks local.p
				println ( "^~^~^ XT under2 thr=" + local.thr + " gain=" + local.gain + " pre=" + local.pre )
			}
			if( local.c == "award" ){
				println "^~^~^ XT award 10 kills"
				thread coop_mod/xp.scr::xp_award local.p 10 "kills" "Rank probe"
			}
			if( local.c == "g43kills" ){
				waitthread coop_mod/challenges.scr::chal_bump local.p "wpn_g43" 225
				thread coop_mod/loadoutpick.scr::loadout_ui_exportUnlocks local.p
				println "^~^~^ XT g43kills 225 (wpn_g43)"
			}
			if( local.c == "sg59" ){
				waitthread coop_mod/challenges.scr::chal_bump local.p "wpn_shotgun" 59
				println "^~^~^ XT sg59 (wpn_shotgun +59)"
			}
			if( local.c == "sg1" ){
				waitthread coop_mod/challenges.scr::chal_bump local.p "wpn_shotgun" 1
				println "^~^~^ XT sg1 (wpn_shotgun +1)"
			}
			if( local.c == "snow150" ){
				waitthread coop_mod/challenges.scr::chal_bump local.p "kill_snow" 150
				println "^~^~^ XT snow150 (kill_snow +150)"
			}
			if( local.c == "dbstate" || local.c == "sg59" || local.c == "sg1" || local.c == "snow150" ){
				local.k = waitthread coop_mod/loadoutpick.scr::loadout_isUnlocked local.p "models/weapons/coop_dbshotgun.tik"
				local.v2 = local.p.flags["coop_loSlot1"]
				if( local.v2 == NIL ){ local.v2 = "NIL" }
				local.v3 = local.p.flags["coop_loSlotId1"]
				if( local.v3 == NIL ){ local.v3 = "NIL" }
				local.v4 = local.p.flags["coop_loFin1"]
				if( local.v4 == NIL ){ local.v4 = "NIL" }
				println ( "^~^~^ XT dbstate dbs=" + local.k + " slot1=" + local.v2 + " id1=" + local.v3 + " fin1=" + local.v4 )
			}
			if( local.c == "held" ){
				local.w = local.p getactiveweap 0
				local.m = "none"
				if( local.w != NULL && local.w != NIL ){ local.m = local.w.model }
				println ( "^~^~^ XT held=" + local.m )
			}
			if( local.c == "state" || local.c == "seed" || local.c == "g43kills" ){
				local.u = local.p.flags["coop_chal_unlocks"]
				if( local.u == NIL ){ local.u = "" }
				local.k = waitthread coop_mod/loadoutpick.scr::loadout_isUnlocked local.p "models/weapons/coop_g43_irons.tik"
				local.v = waitthread coop_mod/loadoutpick.scr::loadout_mvUnlocked local.p "models/weapons/coop_g43_irons.tik" 8
				println ( "^~^~^ XT state rank=" + local.p.flags["coop_xp_rank"] + " total=" + local.p.flags["coop_xp_total"] + " irons=" + local.k + " ironsFleck=" + local.v )
				println ( "^~^~^ XT record=" + local.u )
			}
		}
		wait 0.2
	}
}end
'''


def git_mod(*a, **kw):
    return subprocess.run(['git', '-C', L.MOD] + list(a), capture_output=True, check=True, **kw).stdout


def code_pak(rev):
    full = git_mod('rev-parse', rev).decode().strip()
    out = os.path.join(SCR, 'code_%s.pk3' % full[:10])
    if not os.path.isfile(out):
        tops = [t for t in git_mod('ls-tree', '--name-only', full).decode().splitlines()
                if t not in ('sound', 'textures', 'models', 'gfx', 'env') and not t.lower().endswith('.pk3') and not t.startswith('.git')]
        subprocess.run(['git', '-C', L.MOD, 'archive', '--format=zip', '-1', '-o', out, full, '--'] + tops, check=True)
    return out, full


def plumbing_pak(rev):
    full = git_mod('rev-parse', rev).decode().strip()
    out = os.path.join(SCR, 'plumb2_%s.pk3' % full[:10])
    w = git_mod('show', full + ':coop_mod/weather.scr').decode('latin-1').replace('\r\n', '\n')
    anchor = '\twaitthread coop_mod/duststorm.scr::coop_dust_boot\n'
    assert w.count(anchor) == 1
    w = w.replace(anchor, anchor + HOOK) + FUNCS
    d = 0
    for ln in w.split('\n'):
        t = ln.split('//')[0]
        d += t.count('{') - t.count('}')
        assert d >= 0
    assert d == 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('coop_mod/weather.scr', w.replace('\n', '\r\n'))
    return out


def fixes_from_rev(rev):
    """the fixes pak as docs-repo revision `rev` would build it (--fixes rev:<rev>): the release candidate's pak"""
    out = os.path.join(SCR, 'fixes_%s.pk3' % rev)
    if not os.path.isfile(out):
        pre = 'docs/tools/assets/fixes/'
        names = subprocess.run(['git', '-C', L.ROOT, 'ls-tree', '-r', '--name-only', rev, pre], capture_output=True, text=True,
                               check=True).stdout.splitlines()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_STORED) as z:
            for n in sorted(names):
                if not n.endswith('fixes_manifest.json'):
                    z.writestr(n[len(pre):], subprocess.run(['git', '-C', L.ROOT, 'show', rev + ':' + n], capture_output=True, check=True).stdout)
    return out


def md5f(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def seed(R, bins, code, fixes, sess):
    """binaries into the harness root, a clean set of test paks into its home; old test files are MOVED aside"""
    aside = os.path.join(CLIENT, '_aside_integ', sess + time.strftime('_%H%M%S'))
    os.makedirs(os.path.join(R.MAINTT, 'configs'), exist_ok=True)

    def put_aside(p):
        os.makedirs(aside, exist_ok=True)
        shutil.move(p, os.path.join(aside, os.path.basename(p)))
    for fn in os.listdir(R.MAINTT):
        p = os.path.join(R.MAINTT, fn)
        if fn.lower().endswith(('.pk3', '.pid')) or fn == 'qconsole.log':
            put_aside(p)
    for d in ('main', 'mainta'):
        dd = os.path.join(R.HOME, d)
        if os.path.isdir(dd):
            for fn in os.listdir(dd):
                if fn.lower().endswith('.pid'):
                    put_aside(os.path.join(dd, fn))
    os.makedirs(R.SHOTS, exist_ok=True)
    for fn in os.listdir(R.SHOTS):
        put_aside(os.path.join(R.SHOTS, fn))
    cfg = open(os.path.join(R.PRISTINE, 'omconfig.cfg'), 'rb').read().decode('latin-1')
    cfg = re.sub(r'(?im)^seta coop_loA([1-4]) "[^"\r\n]*"', r'seta coop_loA\1 ""', cfg)
    open(os.path.join(R.MAINTT, 'configs', 'omconfig.cfg'), 'wb').write(cfg.encode('latin-1'))
    for f in ('autoexec.cfg', 'coop_defaults.cfg'):
        shutil.copyfile(os.path.join(R.PRISTINE, f), os.path.join(R.MAINTT, f))
    open(os.path.join(R.MAINTT, 'whatsnew_pending.cfg'), 'wb').write(b'// up to date\r\n')
    md = {}
    for src, dst in (('openmohaa.exe', EXE), ('cgame.dll', 'cgame.dll'), ('game.dll', 'game.dll'),
                     ('renderer_opengl1.dll', 'renderer_opengl1.dll'), ('renderer_opengl2.dll', 'renderer_opengl2.dll')):
        s, d = os.path.join(bins, src), os.path.join(CLIENT, dst)
        if not os.path.isfile(d) or md5f(d) != md5f(s):
            shutil.copyfile(s, d)
        md[src] = md5f(d)[:8]
    cp, full = code_pak(code)
    shutil.copyfile(cp, os.path.join(R.MAINTT, 'zzzzzz_co-op_hzm_mod_code.pk3'))
    shutil.copyfile(plumbing_pak(code), os.path.join(R.MAINTT, 'zzzzzzzzzzzz_integtest.pk3'))
    if fixes and fixes.startswith('rev:'):
        fixes = fixes_from_rev(fixes[4:])
    if fixes:
        shutil.copyfile(fixes, os.path.join(R.MAINTT, L.FIXPAK))
        md['fixes'] = md5f(fixes)[:8] + ' (%d bytes)' % os.path.getsize(fixes)
    else:
        md['fixes'] = 'deployed ' + md5f(os.path.join(L.GOG, 'maintt', L.FIXPAK))[:8]
    md['code'] = full[:10]
    return md


def run(sess, bins, code, fixes, guns, shot, ded=False):
    import run_ironsights as R
    R.OWNER, R.CLIENT, R.PORT, R.MAP = 'hudfeed', CLIENT, 12701, 'm3l2'
    R.EXE = os.path.join(CLIENT, EXE)
    R.HOME = os.path.join(CLIENT, 'home')
    R.MAINTT = os.path.join(R.HOME, 'maintt')
    R.LOG = os.path.join(R.MAINTT, 'qconsole.log')
    R.SHOTS = os.path.join(R.MAINTT, 'screenshots')
    R.PRISTINE = os.path.join(CLIENT, 'pristine')
    rundir = os.path.join(RUNS, sess)
    assert not os.path.isdir(rundir), 'session id used: ' + sess
    os.makedirs(rundir)
    notes = {'session': sess, 'guns': guns, 'bins': bins}
    notes['md5'] = seed(R, bins, code, fixes, sess)
    log('seeded', notes['md5'])
    srv = None
    # dedicated: cvars go through rcon, and a phase marker is a server cvar the probe prints (an rcon echo is not logged)
    rc = (lambda lines: [('rcon set coop_intMark "%s"' % l[len('echo ^~^~^ INTM '):]) if l.startswith('echo ^~^~^ INTM')
                         else ('rcon ' + l) if l.startswith('set coop_') else l for l in lines]) if ded else (lambda lines: lines)
    try:
        extra = ['set coop_reloadDebug 1', 'set cg_adsSightDebug 0', 'set cg_drawviewmodel 2']
        if '--weather' in sys.argv:        # e.g. --weather 4 = the downpour pinned (docs/proposals/rainfix_2026-10-13)
            extra += ['set coop_weatherPin %s' % sys.argv[sys.argv.index('--weather') + 1]]
        if ded:
            srv, slog = start_server(R, bins)
            notes['server'] = {'pid': srv.pid, 'port': SRVPORT}
            t0 = time.time()
            while time.time() - t0 < 300:
                if srv.poll() is not None:
                    raise RuntimeError('dedicated server exited')
                lg = open(slog, 'rb').read().decode('latin-1') if os.path.isfile(slog) else ''
                if re.search(r'initialising coop weapon loadout|Detected Coop for', lg):
                    break
                time.sleep(1)
            else:
                raise RuntimeError('dedicated server: map never became ready')
            time.sleep(5)
            launch_client(R, 1280, 720, extra)
            if not R.wait_log(r'Detected Coop for|CL_InitCGame|CGame Initialization', 300):
                raise RuntimeError('client never loaded the map from the dedicated server')
        else:
            R.launch(1280, 720, extra=extra)
            m = R.wait_log(r'Could not load[^\r\n]*|Detected Coop for', 600)
            if not m or m.group(0).startswith('Could not load'):
                raise RuntimeError('map never became ready: %r' % (m.group(0) if m else None))
        time.sleep(8)
        notes['joined'] = R.join()
        time.sleep(22)
        spawned = False
        for _k in range(4):
            t_click = len(R.read_log())
            R.step(['popmenu 0', 'wait 20', '+attackprimary', 'wait 60', '-attackprimary', 'wait 200'])
            if ded:
                time.sleep(6)
                if re.search(r'\^~\^~\^ KITGIVE', open(slog, 'rb').read().decode('latin-1')):
                    spawned = True
                    break
            elif R.wait_log(r'\^~\^~\^ KITGIVE', 15, t_click):
                spawned = True
                break
        notes['spawned'] = spawned
        if not spawned:
            raise RuntimeError('player never spawned')
        time.sleep(8)
        if not ded:
            R.step(['dog 1', 'wait 200', 'notarget 1', 'wait 200'], timeout=30)
        first = True
        for g in guns:
            log('[%s] %s' % (sess, g))
            st = R.step(rc(R.give(W + GUNS[g][0])) + ['wait 4500'], timeout=60)
            notes.setdefault('gave', {})[g] = re.findall(r'\^~\^~\^ ISTEST[^\r\n]*', (open(slog, 'rb').read().decode('latin-1') if ded else R.read_log()[st:]))[-1:]
            R.step(rc(scenario(g, shot and first)), timeout=240)
            if first and '--imagelist' in sys.argv:      # pass 3 step A: which picture FILE the renderer holds for a texture
                R.step(['imagelist', 'wait 2500'], timeout=60)
            first = False
        notes['ok'] = True
    except Exception as e:
        notes['error'] = repr(e)
        log('ERROR', e)
    finally:
        proc = R.CL['proc']
        if proc is not None and proc.poll() is None:
            try:
                open(os.path.join(R.MAINTT, 'isstep.cfg'), 'w', newline='\n').write('quit\n')
                R.CL['c'].post_key(0x7B)
                proc.wait(40)
            except Exception:
                pass
        c = R.CL['c']
        if c is not None:
            c.close()
            wrep = c.report()
            notes['window'] = {'clean': wrep['clean'], 'violations': wrep['violations']}
        if os.path.isdir(R.SHOTS):
            for fn in sorted(os.listdir(R.SHOTS)):
                src = os.path.join(R.SHOTS, fn)
                if fn.lower().endswith('.tga'):
                    from PIL import Image
                    Image.open(src).save(os.path.join(rundir, fn[:-4] + '.jpg'), quality=88)
                    shutil.move(src, os.path.join(rundir, fn))
                else:
                    shutil.move(src, os.path.join(rundir, fn))
        if srv is not None:
            if srv.poll() is None:
                srv.terminate()          # OUR server pid only
                try:
                    srv.wait(20)
                except Exception:
                    pass
            if os.path.exists(R.LOG):
                shutil.copyfile(R.LOG, os.path.join(rundir, 'client.log'))
            if os.path.exists(slog):
                shutil.copyfile(slog, os.path.join(rundir, 'qconsole.log'))     # the SERVER log is the one parse() reads
        elif os.path.exists(R.LOG):
            shutil.copyfile(R.LOG, os.path.join(rundir, 'qconsole.log'))
        json.dump(notes, open(os.path.join(rundir, 'notes.json'), 'w'), indent=1)
        try:
            R.hg.release_slot(R.OWNER)
        except Exception as e:
            log('release_slot:', e)
        log('[%s] done: %s window %s' % (sess, 'ok' if notes.get('ok') else notes.get('error'), notes.get('window')))


def unlock(sess, bins, code, fixes, wid='78'):
    """the G 43 Irons' UNLOCK PATH on the integrated build + the real fixes pak (the rifles lane's run_unlock.py steps,
    with the mod's own xp_award): locked at rank 0 and 1, unlocked by the promotion to rank 2, picked, kept over a map
    restart, the Flecktarn variant behind the scoped G43's shared challenge. ONE screenshot. The test player's save
    files are put back as found after the game has quit (the run's own are MOVED into the run folder)."""
    import run_ironsights as R
    R.OWNER, R.CLIENT, R.PORT, R.MAP = 'hudfeed', CLIENT, 12701, 'm3l2'
    R.EXE = os.path.join(CLIENT, EXE)
    R.HOME = os.path.join(CLIENT, 'home')
    R.MAINTT = os.path.join(R.HOME, 'maintt')
    R.LOG = os.path.join(R.MAINTT, 'qconsole.log')
    R.SHOTS = os.path.join(R.MAINTT, 'screenshots')
    R.PRISTINE = os.path.join(CLIENT, 'pristine')
    rundir = os.path.join(RUNS, sess)
    assert not os.path.isdir(rundir), 'session id used: ' + sess
    os.makedirs(rundir)
    notes = {'session': sess, 'bins': bins, 'md5': seed(R, bins, code, fixes, sess)}
    log('seeded', notes['md5'])
    save = os.path.join(R.MAINTT, 'coop_mod', 'save')
    before = {f: open(os.path.join(save, f), 'rb').read() for f in (os.listdir(save) if os.path.isdir(save) else []) if os.path.isfile(os.path.join(save, f))}
    if '--fresh' in sys.argv:      # an EMPTY profile (rank 0, no unlock record): the save files are moved into the run folder for the run
        os.makedirs(os.path.join(rundir, 'save_before'), exist_ok=True)
        for f in before:
            shutil.move(os.path.join(save, f), os.path.join(rundir, 'save_before', f))
    xt = lambda cmd, wait=1500: ['set coop_xtCmd %s' % cmd, 'wait %d' % wait]
    menu = ['exec ui/loadout/open.cfg', 'wait 4000', 'pushmenu coop_loadout', 'wait 500', 'exec ui/loadout/init.cfg', 'wait 500',
            'exec ui/loadout/lktab0.cfg', 'wait 1500']
    cv = ['coop_lo1', 'coop_loS1', 'coop_loS1F', 'coop_loLkA%s' % wid, 'coop_lockLoadout', 'wait 200']
    click = ['exec ui/loadout/s1sel.cfg', 'wait 200', 'exec ui/loadout/t%s.cfg' % wid, 'wait 1800']

    def spawn_in():
        time.sleep(8)
        R.join()
        time.sleep(22)
        for _k in range(4):
            t_click = len(R.read_log())
            R.step(['popmenu 0', 'wait 20', '+attackprimary', 'wait 60', '-attackprimary', 'wait 200'])
            if R.wait_log(r'\^~\^~\^ KITGIVE', 15, t_click):
                return True
        return False

    def restart(tag):
        t1 = len(R.read_log())
        R.step(['popmenu 0', 'wait 300', 'exec coop_mod/start_server.cfg'], timeout=60)
        if not R.wait_log(r'Detected Coop for', 300, t1):
            raise RuntimeError('the map did not come back')
        if not spawn_in():
            raise RuntimeError('no spawn after the restart')
        R.step(['wait 6000', 'useweaponclass rifle', 'wait 3000', 'echo ^~^~^ UNLOCK %s:' % tag] + xt('held') + xt('state'), timeout=120)
    def respawn(tag):
        R.step(['kill', 'wait 3500'], timeout=60)
        ok = False
        for _k in range(5):
            t_click = len(R.read_log())
            R.step(['popmenu 0', 'wait 20', '+attackprimary', 'wait 60', '-attackprimary', 'wait 200'])
            if R.wait_log(r'\^~\^~\^ KITGIVE', 15, t_click):
                ok = True
                break
        R.step(['wait 5000', 'useweaponclass heavy', 'wait 3000', 'echo ^~^~^ UNLOCK %s: respawned=%s' % (tag, ok)] + xt('held') + xt('dbstate'), timeout=120)

    def change(mapname, tag):
        t1 = len(R.read_log())
        R.step(['popmenu 0', 'wait 300', 'set ui_dmmap %s' % mapname, 'ui_startdmmap 2'], timeout=60)
        if not R.wait_log(r'Detected Coop for', 400, t1):
            raise RuntimeError('the map %s did not come up' % mapname)
        if not spawn_in():
            raise RuntimeError('no spawn on %s' % mapname)
        R.step(['wait 6000', 'useweaponclass heavy', 'wait 3000', 'echo ^~^~^ UNLOCK %s:' % tag] + xt('held') + xt('dbstate'), timeout=120)
    heavy = ['exec ui/loadout/open.cfg', 'wait 6000',
             'set coop_loNP0 1', 'set coop_loP1 0', 'set coop_loP2 0', 'set coop_loP3 1', 'set coop_loP4 0', 'set coop_loP5 0', 'append name ,w0t3',
             'wait 2500', 'exec ui/loadout/lktab3.cfg', 'wait 1500']
    try:
        R.launch(1280, 720, extra=['set coop_reloadDebug 0', 'set cg_drawviewmodel 2', 'set ui_hud 1'] + (['set coop_lockLoadout 1'] if wid == '80' else []))
        m = R.wait_log(r'Could not load[^\r\n]*|Detected Coop for', 600)
        if not m or m.group(0).startswith('Could not load'):
            raise RuntimeError('map never became ready')
        if not spawn_in():
            raise RuntimeError('player never spawned')
        time.sleep(6)
        if wid == '80':
            # pass 3 step B, the double barrel: locked -> 59 Shotgun kills (still locked) -> the 60th -> unlocked -> picked
            # -> respawn holding it -> the winter finish (its own challenge) -> a map CHANGE keeps the pick and the finish
            R.step(['coop_dbShotgun', 'wait 200'] + xt('dbstate') + heavy + ['exec ui/loadout/req80.cfg', 'wait 400'] + click + ['popmenu 0', 'wait 400', 'echo ^~^~^ UNLOCK locked_click:'] + cv, timeout=120)
            R.step(xt('sg59', 5000) + heavy + click + ['popmenu 0', 'wait 400', 'echo ^~^~^ UNLOCK at59_click:'] + cv, timeout=120)
            click80 = ['exec ui/loadout/t80.cfg', 'wait 6000']
            R.step(xt('sg1', 6000) + heavy + ['coop_loLkA80', 'wait 200'] + click80 + ['popmenu 0', 'wait 800', 'echo ^~^~^ UNLOCK at60_click:'] + cv + xt('dbstate'), timeout=180)
            respawn('spawn_after_click_1')
            R.step(heavy + ['coop_loLkA80', 'wait 200'] + click80 + ['popmenu 0', 'wait 800', 'echo ^~^~^ UNLOCK click_2_after_respawn:'] + cv + xt('dbstate'), timeout=180)
            respawn('spawn_with_pick')
            R.step(xt('snow150', 5000) + ['append name ,f16', 'wait 7000', 'echo ^~^~^ UNLOCK finish_winter:'] + cv + xt('dbstate'), timeout=120)
            respawn('spawn_with_finish')
            change('m1l1', 'after_map_change')
        else:
            R.step(xt('state') + menu + ['exec ui/loadout/req%s.cfg' % wid, 'wait 400'] + click + ['popmenu 0', 'wait 400', 'echo ^~^~^ UNLOCK rank0_click:'] + cv, timeout=120)
            R.step(xt('seed', 2500) + xt('under2', 2500) + xt('state') + menu + click + ['popmenu 0', 'wait 400', 'echo ^~^~^ UNLOCK rank1_click:'] + cv, timeout=120)
            # the armory's own unlock export after a promotion takes a few seconds (75 roster entries, restarted by every menu
            # open): run u5b clicked 1.5 s after the tab was up and the tile was still padlocked on the CLIENT - wait for it
            R.step(xt('award', 1000) + ['wait 9000'] + xt('state') + menu + ['wait 8000', 'exec ui/loadout/lktab0.cfg', 'wait 1500'] + click + ['screenshot int_unlock_%s' % sess, 'wait 300', 'popmenu 0', 'wait 400',
                                                                                     'echo ^~^~^ UNLOCK rank2_click:'] + cv, timeout=120)
            restart('after_restart')
            R.step(menu + ['exec ui/loadout/s1sel.cfg', 'wait 200', 'exec ui/loadout/p%s.cfg' % wid, 'wait 600', 'exec ui/loadout/fin8_s1.cfg', 'wait 1800',
                           'popmenu 0', 'wait 400', 'echo ^~^~^ UNLOCK variant_locked:'] + cv, timeout=120)
            R.step(xt('g43kills', 4000) + xt('state') + menu + ['exec ui/loadout/s1sel.cfg', 'wait 200', 'exec ui/loadout/p%s.cfg' % wid, 'wait 600',
                                                                'exec ui/loadout/fin8_s1.cfg', 'wait 1800', 'popmenu 0', 'wait 400',
                                                                'echo ^~^~^ UNLOCK variant_unlocked:'] + cv, timeout=120)
            restart('after_variant_restart')
        notes['ok'] = True
    except Exception as e:
        notes['error'] = repr(e)
        log('ERROR', e)
    finally:
        proc = R.CL['proc']
        if proc is not None and proc.poll() is None:
            try:
                open(os.path.join(R.MAINTT, 'isstep.cfg'), 'w', newline='\n').write('quit\n')
                R.CL['c'].post_key(0x7B)
                proc.wait(40)
            except Exception:
                pass
        c = R.CL['c']
        if c is not None:
            c.close()
            wrep = c.report()
            notes['window'] = {'clean': wrep['clean'], 'violations': wrep['violations']}
        time.sleep(3)
        if os.path.isdir(R.SHOTS):
            for fn in sorted(os.listdir(R.SHOTS)):
                src = os.path.join(R.SHOTS, fn)
                if fn.lower().endswith('.tga'):
                    from PIL import Image
                    Image.open(src).save(os.path.join(rundir, fn[:-4] + '.jpg'), quality=88)
                shutil.move(src, os.path.join(rundir, fn))
        after = os.path.join(rundir, 'save_after')
        os.makedirs(after, exist_ok=True)
        for f in (os.listdir(save) if os.path.isdir(save) else []):
            if os.path.isfile(os.path.join(save, f)):
                shutil.move(os.path.join(save, f), os.path.join(after, f))
        os.makedirs(save, exist_ok=True)
        for f, bb in before.items():
            open(os.path.join(save, f), 'wb').write(bb)
        notes['save_files'] = 'put back as found: %d; the run\'s own moved to save_after' % len(before)
        if os.path.exists(R.LOG):
            shutil.copyfile(R.LOG, os.path.join(rundir, 'qconsole.log'))
        json.dump(notes, open(os.path.join(rundir, 'notes.json'), 'w'), indent=1)
        try:
            R.hg.release_slot(R.OWNER)
        except Exception as e:
            log('release_slot:', e)
        log('[%s] done: %s window %s' % (sess, 'ok' if notes.get('ok') else notes.get('error'), notes.get('window')))
    lg = open(os.path.join(rundir, 'qconsole.log'), 'rb').read().decode('latin-1')
    for ln in lg.splitlines():
        if re.search(r'\^~\^~\^ (XT|UNLOCK)|"coop_lo(1|S1|S1F|LkA%s)" is|"coop_lockLoadout" is|LOCKED|locked - see|Script Error|KITGIVE' % wid, ln):
            print(ln[33:260])


SRVPORT = 12702
SRVHOME = os.path.join(CLIENT, 'home_srv_integ')
RCON = 'integ8rc'


def start_server(R, bins):
    """OUR dedicated server: omohaaded from `bins` in the harness folder, its own home, 127.0.0.1:12702"""
    mt = os.path.join(SRVHOME, 'maintt')
    os.makedirs(mt, exist_ok=True)
    for fn in os.listdir(mt):
        if fn.lower().endswith(('.pk3', '.pid')) or fn == 'qconsole.log':
            os.makedirs(os.path.join(CLIENT, '_aside_integ', 'srv'), exist_ok=True)
            shutil.move(os.path.join(mt, fn), os.path.join(CLIENT, '_aside_integ', 'srv', time.strftime('%H%M%S_') + fn))
    for fn in os.listdir(R.MAINTT):
        if fn.lower().endswith('.pk3'):
            shutil.copyfile(os.path.join(R.MAINTT, fn), os.path.join(mt, fn))
    for f in ('autoexec.cfg', 'coop_defaults.cfg'):
        shutil.copyfile(os.path.join(R.PRISTINE, f), os.path.join(mt, f))
    open(os.path.join(mt, 'ded_integ.cfg'), 'w', newline='\n').write('\n'.join([
        'set rconPassword ' + RCON, 'set coop_isPoll 1', 'set sv_fps 40', 'set g_ai 0', 'set coop_dbno 0', 'set coop_dev 1',
        'set sv_maxbots 0', 'set sv_numbots 0', 'set coop_weatherPin 0', 'set coop_lockLoadout 0', 'map m3l2']) + '\n')
    exe = os.path.join(CLIENT, 'omohaaded_integ8.exe')
    if not os.path.isfile(exe) or md5f(exe) != md5f(os.path.join(bins, 'omohaaded.exe')):
        shutil.copyfile(os.path.join(bins, 'omohaaded.exe'), exe)
    args = [exe]
    for k, v in (('com_target_game', '2'), ('dedicated', '1'), ('fs_basepath', L.GOG.replace('/', os.sep)), ('fs_homepath', SRVHOME),
                 ('net_ip', '127.0.0.1'), ('net_port', str(SRVPORT)), ('sv_maxclients', '4'), ('g_gametype', '2'),
                 ('developer', '1'), ('logfile', '2')):
        args += ['+set', k, v]
    args += ['+exec', 'ded_integ.cfg']
    p = subprocess.Popen(args, cwd=CLIENT, creationflags=0x08000000, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    log('dedicated server pid', p.pid, 'port', SRVPORT)
    return p, os.path.join(mt, 'qconsole.log')


def launch_client(R, Wd, Hd, extra):
    """R.launch, but the client CONNECTS to our dedicated server instead of starting a listen server"""
    boot = ['bind F12 "exec isstep.cfg"', 'set rconPassword ' + RCON, 'set cg_drawviewmodel 1', 'set ui_gmbox 0', 'ui_checkrestart',
            'set ui_crosshair 0', 'set coop_idleInspect 0', 'set cg_adsSway 0', 'set coop_coverAuto 0', 'set coop_coverLean 0',
            'set ui_hud 0', 'set com_maxfps 60', 'set coop_tinnitus 0'] + list(extra)
    sets = [('com_target_game', '2'), ('fs_basepath', R.GOG), ('fs_homepath', R.HOME), ('cl_renderer', 'opengl2'),
            ('r_ext_framebuffer_multisample', '0'), ('r_ext_multisample', '0'), ('r_mode', '-1'),
            ('r_customwidth', str(Wd)), ('r_customheight', str(Hd)), ('r_fullscreen', '0'), ('developer', '1'),
            ('logfile', '2'), ('net_ip', '127.0.0.1'), ('net_port', str(R.PORT))]
    args = [R.EXE]
    for k, v in sets:
        args += ['+set', k, v]
    args += ['+exec', 'is_on.cfg', '+connect', '127.0.0.1:%d' % SRVPORT]
    args, late = R.hw.apply_policy(args, width=Wd, height=Hd)
    boot += late
    open(os.path.join(R.MAINTT, 'is_on.cfg'), 'w', newline='\n').write('\n'.join(boot) + '\n')
    R.hg.acquire_slot(R.OWNER, R.EXE, R.HOME, [R.PORT], 40)
    c = R.hw.launch_background(args[0], args[1:], R.CLIENT, policy=False, log=log)
    R.CL['c'], R.CL['proc'] = c, c.proc
    try:
        R.hg.set_slot_pid(R.OWNER, c.proc.pid)
    except Exception as e:
        log('slot pid note:', e)
    return c


# ---------------------------------------------------------------------------------------------------- analysis
def parse(sess):
    """{gun: {phase: dict(states=[(state, dur)], am=[(dt, reserve)], wfeel=[(id, len)])}}"""
    lp = os.path.join(RUNS, sess, 'qconsole.log')
    if not os.path.isfile(lp):          # a finished run lives in the archive
        lp = os.path.join(r'H:\hzm_archive\integrate', sess, 'qconsole.log')
    lg = open(lp, 'rb').read().decode('latin-1')
    out, gun, ph, t0, cur = {}, None, None, None, None
    last_state, last_t, last_am = None, None, None
    for ln in lg.splitlines():
        m = re.search(r'\^~\^~\^ INTM (\S+) (\S+)', ln)
        if m and not ln.lstrip().startswith(']') and 'echo' not in ln:
            gun, ph = m.group(1), m.group(2)
            cur = out.setdefault(gun, {}).setdefault(ph, dict(states=[], am=[], wfeel=[], t0=last_t))
            if last_state is not None:
                cur['states'].append([last_state, None, last_t])
            continue
        if cur is None:
            continue
        m = re.search(r'\^~\^~\^ INTP t=([\d.]+) st=(\S*) am=(-?\d+)', ln)
        if m:
            t, st, am = float(m.group(1)), m.group(2), int(m.group(3))
            if st != last_state:
                if cur['states'] and cur['states'][-1][1] is None:
                    cur['states'][-1][1] = round(t - cur['states'][-1][2], 3)
                cur['states'].append([st, None, t])
            if last_am is not None and am != last_am:
                cur['am'].append((round(t, 3), am - last_am))
            last_state, last_t, last_am = st, t, am
            continue
        m = re.search(r'\^~\^~\^ WFEEL state=(-?\d+) slot=\d+ len=([\d.]+)', ln)
        if m:
            cur['wfeel'].append((int(m.group(1)), float(m.group(2))))
            continue
        m = re.search(r'\^~\^~\^ ADSFRAME t=(\d+) .* anim=(-?\d+) .*sight=\((-?[\d.]+) (-?[\d.]+)\).* clip=(-?\d+) ammo=(-?\d+)', ln)
        if m:
            cur.setdefault('frames', []).append((int(m.group(1)), int(m.group(2)), float(m.group(3)), float(m.group(4)), int(m.group(5))))
    return out


def summarize(ph):
    """reload span (first RELOAD* entry -> first later non-RELOAD state), refill, state list"""
    sts = ph['states']
    rel = [s for s in sts if 'RELOAD' in s[0]]
    r = {}
    if rel:
        a = rel[0][2]
        ends = [s for s in sts if s[2] > rel[-1][2]]
        b = ends[0][2] if ends else None
        r['reload'] = round(b - a, 3) if b is not None else None
        r['reload_states'] = '>'.join('%s:%s' % (s[0], s[1]) for s in rel)
        ref = [x for x in ph['am'] if x[1] < 0]
        r['refill'] = ['%d@+%.3f' % (-x[1], x[0] - a) for x in ref]
    r['other'] = ' '.join('%s:%s' % (s[0], s[1]) for s in sts if 'RELOAD' not in s[0] and s[0] not in ('STAND', 'AIM'))
    r['wfeel'] = ' '.join('%d/%.3f' % w for w in ph['wfeel'])
    return r


def show(sess, guns):
    d = parse(sess)
    for g in d:
        if guns and g not in guns:
            continue
        for ph, v in d[g].items():
            if ph == 'end':
                continue
            s = summarize(v)
            print('%s %-9s | reload %s [%s] refill %s | %s | hands %s' % (g, ph, s.get('reload'), s.get('reload_states', ''), s.get('refill', ''),
                                                                         s['other'], s['wfeel']))


def cmp_(a, b, guns):
    A, B = parse(a), parse(b)
    bad = 0
    print('gun phase | %s | %s | verdict' % (a, b))
    for g in A:
        if g not in B or (guns and g not in guns):
            continue
        for ph in A[g]:
            if ph == 'end' or ph not in B[g]:
                continue
            x, y = summarize(A[g][ph]), summarize(B[g][ph])
            fx = 'reload %s refill %s | %s' % (x.get('reload'), ','.join(x.get('refill', [])), x['other'])
            fy = 'reload %s refill %s | %s' % (y.get('reload'), ','.join(y.get('refill', [])), y['other'])
            def nums(s):
                return [float(v) for v in re.findall(r'-?\d+\.\d+', s)]
            def shape(s):
                return re.sub(r'-?\d+\.\d+', '#', s)
            nx, ny = nums(fx), nums(fy)
            if shape(fx) == shape(fy) and len(nx) == len(ny) and all(abs(p - q) <= 0.0251 for p, q in zip(nx, ny)):
                v = 'equal (within one 25 ms server frame)' if nx != ny else 'equal'
            else:
                v = 'DIFFERENT'
                bad += 1
            print('%s %s | %s | %s | %s' % (g, ph, fx, fy, v))
    print('%d phase(s) differ' % bad)


# which hands rows a gun may play: the row-name tokens of its prefix / weapon key
PREF = {'bar': ('bar_', 'coopr_bar_'), 'mp44': ('mp44_',), 'dp28': ('dp28_',), 'shotgun': ('shotgun_',), 'sg': ('shotgun_',),
        'mp40sil': ('mp40_', 'coopr_silenced_mp40_'), 'mp40r2': ('mp40_', 'coopr_mp40_reactivated_', 'coopr_mp40_'),
        'mp40': ('mp40_', 'coopr_mp40_'), 'mp18': ('mp40_', 'coopr_mp40_mp18_'),
        'kar98': ('kar98_',), 'springfield': ('springfield_',), 'mosin': ('mosin_',), 'enfield': ('enfield_',),
        'colt45': ('colt45_',), 'thompson': ('thompson_',), 'sten': ('sten_',), 'garand': ('garand_',), 'fg42': ('fg42_',),
        'lewis': ('bar_', 'coopr_lewis'), 'grease': ('mp40_',)}


def rows(sess, guns, fixes_rev=None):
    """the hands clip each phase played, named: WFEEL prints the LENGTH of the clip in the view slot, and the lengths
    of the gun's candidate rows are read from the row files (fixes working copy, or the fixes at a docs revision)"""
    v = L.Vfs(('git', fixes_rev) if fixes_rev else L.FIX)
    table = {}
    for rel in list(v.fixnames.values()) + list(v.mod.values()):
        if re.match(r'models/player/base/(fps_anims_[^/]+|anims_shared)\.txt$', rel.lower()):
            for r in L.tik_rows(v.read(rel).decode('latin-1')):
                info = L.skc_info(v.read('models/human/animation/' + r[1]))
                if info:
                    table.setdefault(r[0], round((info[0] - 1) * info[1], 3))    # the engine's clip time = (frames - 1) x frame time
    d = parse(sess)
    for g in d:
        if guns and g not in guns:
            continue
        toks = next((PREF[k] for k in sorted(PREF, key=len, reverse=True) if g.startswith(k)), ())
        for ph, vv in d[g].items():
            if not vv['wfeel']:
                continue
            out = []
            for aid, ln in vv['wfeel']:
                names = sorted(n for n, t in table.items() if abs(t - ln) <= 0.0015 and n.startswith(toks)
                               and not re.search(r'(idle|walk|run|fire|pullout|putaway|charge)', n))
                out.append('%d:%.3f=%s' % (aid, ln, '/'.join(names) if names else '?'))
            print('%s %-9s | %s' % (g, ph, '  '.join(out)))


def aimed(sess, guns):
    """client side, aimed phases (merged cgame only): how far the sight line leaves the eye line while the reload /
    bolt clip plays, where it ends, and the rounds in the gun as the CLIENT counts them"""
    d = parse(sess)
    print('gun phase | frames | sight line off the eye line: max during view anims reload(6,7,8) / rechamber(5), deg | at the end, deg | clip as the client saw it')
    for g in d:
        if guns and g not in guns:
            continue
        for ph in ('aimfire', 'aimreload', 'aimempty'):
            fr = d[g].get(ph, {}).get('frames')
            if not fr:
                continue
            dev = lambda f: (f[2] ** 2 + f[3] ** 2) ** 0.5
            rel = [dev(f) for f in fr if f[1] in (6, 7, 8)]
            bolt = [dev(f) for f in fr if f[1] == 5]
            clips = []
            for f in fr:
                if not clips or clips[-1] != f[4]:
                    clips.append(f[4])
            if len(clips) > 14:
                clips = clips[:6] + ['..'] + clips[-6:]
            print('%s %s | %d | reload %s / bolt %s | %.2f | %s' % (g, ph, len(fr), '%.2f' % max(rel) if rel else '-',
                                                                 '%.2f' % max(bolt) if bolt else '-', dev(fr[-1]), ' '.join(str(c) for c in clips)))


ERR = re.compile(r"Script Error|\^1|ERROR|Couldn't|couldn't|not found|Cannot|cannot find|missing|no such|Unknown|unknown anim|failed|WARNING", re.I)


def errs(sess, base=None):
    def lines(s):
        lp = os.path.join(RUNS, s, 'qconsole.log')
        if not os.path.isfile(lp):
            lp = os.path.join('H:/hzm_archive/integrate', s, 'qconsole.log')
        lg = open(lp, 'rb').read().decode('latin-1')
        out = {}
        for ln in lg.splitlines():
            if ERR.search(ln) and '^~^~^' not in ln:
                k = re.sub(r'\d+', '#', ln.strip())[:200]
                out[k] = out.get(k, 0) + 1
        return out
    a = lines(sess)
    b = lines(base) if base else {}
    print('%s: %d distinct error-like lines%s' % (sess, len(a), ' (%d not in %s)' % (len([k for k in a if k not in b]), base) if base else ''))
    for k in sorted(a):
        if k not in b:
            print('  %4dx %s' % (a[k], k))


if __name__ == '__main__':
    cmd = sys.argv[1]
    arg = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
    guns = arg('--guns').split(',') if arg('--guns') else []
    if cmd in ('run', 'ded'):
        run(sys.argv[2], arg('--bins'), arg('--code', 'HEAD'), arg('--fixes'), guns, '--shot' in sys.argv, ded=(cmd == 'ded'))
    elif cmd == 'unlock':
        unlock(sys.argv[2], arg('--bins'), arg('--code', 'HEAD'), arg('--fixes'), wid='80' if '--dbs' in sys.argv else '78')
    elif cmd == 'show':
        show(sys.argv[2], guns)
    elif cmd == 'cmp':
        cmp_(sys.argv[2], sys.argv[3], guns)
    elif cmd == 'aimed':
        aimed(sys.argv[2], guns)
    elif cmd == 'rows':
        rows(sys.argv[2], guns, arg('--fixes-rev'))
    elif cmd == 'errs':
        errs(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None)
