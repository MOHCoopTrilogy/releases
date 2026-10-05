# Mod (script) hunks for the HUD declutter. See hudops.py. Classification: ../PLAN.md section 2.
M = "mod"
FEED = "coop_mod/feed.scr::"


def FA(f, old, cat, key, text, n=1):
    """broadcast -> one feed line per player"""
    return (M, f, old, 'waitthread %sfeed_all %d "%s" %s' % (FEED, cat, key, text), n)


def FP(f, old, who, cat, key, text, n=1):
    """one player -> feed"""
    return (M, f, old, 'waitthread %sfeed_player %s %d "%s" %s' % (FEED, who, cat, key, text), n)


def HA(f, old, key, text, n=1):
    """broadcast tutorial line -> hint, once per profile"""
    return (M, f, old, 'waitthread %sfeed_hint_all "%s" %s' % (FEED, key, text), n)


def CUT(f, old, expr, n=1):
    """developer/redundant print -> console only (println is developer-gated, the log keeps it)"""
    return (M, f, old, 'println %s' % expr, n)


OPS = [
    (M, "coop_mod/feed.scr", None, r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\coop_mod\feed.scr", 0),
    (M, "ui/coop_lastmission.urc", None, r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\ui\coop_lastmission.urc", 0),

    # ================================================================ officer.scr
    FA("coop_mod/officer.scr", 'iprintlnbold "Intel reports a High-Ranking Officer is visiting this area."', 0, "off_spawn",
       '"Intel: a High-Ranking Officer is in the area with reinforcements"'),
    CUT("coop_mod/officer.scr", 'iprintlnbold "Be cautious of his reinforcements he brought with him."',
        '"Be cautious of his reinforcements he brought with him. (feed: merged into off_spawn)"'),
    (M, "coop_mod/officer.scr",
     '\t\twhile( level.coop_officer_spawn_tutorial[local.stl] != NIL ){\n'
     '\t\t\tiprintlnbold level.coop_officer_spawn_tutorial[local.stl]\n'
     '\t\t\tlocal.stl++\n'
     '\t\t}\n',
     '\t\t//[user 2026-10-05] HUD declutter: the per-map tutorial lines are ONE hint, shown once per player profile\n'
     '\t\tlocal.stxt = ""\n'
     '\t\twhile( level.coop_officer_spawn_tutorial[local.stl] != NIL ){\n'
     '\t\t\tlocal.stxt = local.stxt + level.coop_officer_spawn_tutorial[local.stl] + " "\n'
     '\t\t\tlocal.stl++\n'
     '\t\t}\n'
     '\t\twaitthread coop_mod/feed.scr::feed_hint_all "off_tut" local.stxt\n', 1),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer has slipped away to find a health post!"', 1, "off_heal",
       '"The Officer slipped away to find a health post"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "The Officer is drinking from his canteen to recover!"', 1, "off_canteen",
       '"The Officer is drinking from his canteen"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "You eliminated one of the Officer\'s bodyguards! He calls for reinforcements!"', 1, "bg_down",
       '"Bodyguard down - the Officer calls for reinforcements"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "The Officer\'s bodyguards have been eliminated!"', 1, "bg_all",
       '"All of the Officer\'s bodyguards are down"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer, with no support nearby, is slipping away to a distant aid post!"', 1, "off_heal",
       '"The Officer is slipping away to a distant aid post"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer is falling back to a health post - stop him before he heals!"', 1, "off_heal",
       '"The Officer is falling back to a health post - stop him"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer is slipping away to a health post - stop him before he heals!"', 1, "off_heal",
       '"The Officer is slipping away to a health post - stop him"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer is retreating to a health post - stop him before he heals!"', 1, "off_heal",
       '"The Officer is retreating to a health post - stop him"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "The Officer has been fully healed! Thresholds reset!"', 1, "off_healed",
       '"The Officer is fully healed"'),
    CUT("coop_mod/officer.scr", 'iprintlnbold "The Officer barks into his radio - but his reinforcements are not ready yet!"',
        '"^~^~^ OFFICER radio bark - reinforcements not ready (feed: cut)"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer has deployed an Elite Squad to hunt you down and eliminate you."', 0, "w_elite",
       '"Enemy wave: an Elite Squad is hunting you"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer has deployed a Wehrmacht Squad to hunt you down and eliminate you."', 0, "w_inf",
       '"Enemy wave: a Wehrmacht Squad is hunting you"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer has deployed an Elite Sniper to hunt you down and eliminate you."', 0, "w_sniper",
       '"Enemy wave: an Elite Sniper is hunting you"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer has deployed a Grenadier Squad to hunt you down and eliminate you."', 0, "w_gren",
       '"Enemy wave: a Grenadier Squad is hunting you"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer has deployed an Anti-Tank Team to hunt you down and eliminate you."', 0, "w_at",
       '"Enemy wave: an Anti-Tank Team is hunting you"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer has unleashed attack dogs to hunt you down."', 0, "w_dogs",
       '"Enemy wave: attack dogs are hunting you"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer has summoned a BATTALION! They are converging to protect him!"', 0, "w_bat",
       '"Enemy wave: a BATTALION is converging on the Officer"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "The Battalion has been wiped out!"', 1, "bat_down", '"The Battalion has been wiped out"'),
    FA("coop_mod/officer.scr", 'iprintlnbold (local.label + " eliminated.")', 1, "sq_down", '( local.label + " eliminated" )'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer is calling another wave to replace his losses!"', 1, "w_recall",
       '"The Officer is calling another wave"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "The officer has been eliminated!"', 1, "off_dead", '"The Officer has been eliminated"'),
    (M, "coop_mod/officer.scr", 'if( local.msg != NIL && local.msg != "" ){ iprintlnbold local.msg }',
     'if( local.msg != NIL && local.msg != "" ){ waitthread coop_mod/feed.scr::feed_all 0 "dbat" local.msg }', 1),
    FA("coop_mod/officer.scr", 'iprintlnbold "The officer dropped a Signal Smoke Grenade and Binoculars!"', 1, "off_drop",
       '"The Officer dropped a Signal Smoke Grenade and Binoculars"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "The officer dropped a Signal Smoke Grenade!"', 1, "off_drop", '"The Officer dropped a Signal Smoke Grenade"'),
    FA("coop_mod/officer.scr", 'iprintlnbold "The officer dropped a pair of Binoculars!"', 1, "off_drop", '"The Officer dropped a pair of Binoculars"'),
    FA("coop_mod/officer.scr", 'iprintlnbold (local.player.netname + " picked up the Signal Smoke!")', 1, "smoke",
       '(local.player.netname + " picked up the Signal Smoke")', 1),
    (M, "coop_mod/officer.scr",
     'iprintlnbold "Signal Smoke ready! Equip grenades and throw - Allied paradrop falls where it hits!"',
     'waitthread coop_mod/feed.scr::feed_hint local.player "smoke" "Signal Smoke: equip grenades and throw it - the Allied paradrop lands where it hits"', 1),
    FA("coop_mod/officer.scr", 'iprintlnbold (local.player.netname + " picked up Binoculars!")', 1, "binoc",
       '(local.player.netname + " picked up the Binoculars")'),
    (M, "coop_mod/officer.scr",
     '\t\t\twhile( level.coop_binoc_tutorial_msg[local.tl] != NIL ){\n'
     '\t\t\t\tiprintlnbold level.coop_binoc_tutorial_msg[local.tl]\n'
     '\t\t\t\tlocal.tl++\n'
     '\t\t\t}\n',
     '\t\t\t//[user 2026-10-05] HUD declutter: one hint to the carrier, once per profile\n'
     '\t\t\tlocal.btxt = ""\n'
     '\t\t\twhile( level.coop_binoc_tutorial_msg[local.tl] != NIL ){\n'
     '\t\t\t\tlocal.btxt = local.btxt + level.coop_binoc_tutorial_msg[local.tl] + " "\n'
     '\t\t\t\tlocal.tl++\n'
     '\t\t\t}\n'
     '\t\t\twaitthread coop_mod/feed.scr::feed_hint local.player "binoc_tut" local.btxt\n', 1),
    (M, "coop_mod/officer.scr",
     'iprintlnbold "Equip binoculars from pistol slot, aim and fire [LMB] to call bombing runs! (3 strikes)"',
     'waitthread coop_mod/feed.scr::feed_hint local.player "binoc" "Binoculars: equip from the pistol slot, aim and fire to call a bombing run (3 strikes)"', 1),
    FA("coop_mod/officer.scr", 'iprintlnbold (local.player.netname + " recovered the Binoculars! (" + level.coop_binoc_uses + " strikes left)")', 1, "binoc",
       '(local.player.netname + " recovered the Binoculars - " + level.coop_binoc_uses + " strikes left")'),
    (M, "coop_mod/officer.scr", 'iprintlnbold "Negative - no clear sky above target coordinates. Strike request denied."',
     'local.player iprint "Negative - no clear sky above target coordinates. Strike request denied." 1\t//[user 2026-10-05] caller only (was a broadcast)', 1),
    FA("coop_mod/officer.scr", 'iprintlnbold ("Fire mission requested... (" + level.coop_binoc_uses + " strikes remaining)")', 1, "firemission",
       '("Fire mission requested - " + level.coop_binoc_uses + " strikes remaining")'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Final fire mission requested... Bombing Run expended."', 1, "firemission",
       '"Final fire mission requested - Bombing Run expended"'),
    FA("coop_mod/officer.scr", 'iprintlnbold ("The Binoculars were dropped (" + level.coop_binoc_uses + " strikes left) - a teammate can recover them.")', 1, "binoc_drop",
       '("The Binoculars were dropped (" + level.coop_binoc_uses + " strikes left) - a teammate can recover them")'),
    FA("coop_mod/officer.scr", 'iprintlnbold "The Signal Smoke was dropped - a teammate can recover it."', 1, "smoke_drop",
       '"The Signal Smoke was dropped - a teammate can recover it"'),
    FA("coop_mod/officer.scr", 'iprintlnbold (local.player.netname + " recovered the Signal Smoke!")', 1, "smoke",
       '(local.player.netname + " recovered the Signal Smoke")'),
    FA("coop_mod/officer.scr", 'iprintlnbold (local.planter.netname + " planted explosives on the radio!")', 1, "radio",
       '(local.planter.netname + " planted explosives on the radio")'),
    FA("coop_mod/officer.scr", 'iprintlnbold "Radio destroyed! Reinforcements cannot be called!"', 1, "radio",
       '"Radio destroyed - no more reinforcements"'),

    # ================================================================ paradrop.scr
    CUT("coop_mod/paradrop.scr", 'iprintlnbold "Signal smoke! Allied paradrop inbound!"', '"^~^~^ PARADROP signal smoke (feed: the C-47 line follows)"'),
    FA("coop_mod/paradrop.scr", 'iprintlnbold "C-47 inbound! Allied paratroopers dropping in!"', 1, "para_in", '"C-47 inbound - Allied paratroopers dropping in"'),
    FA("coop_mod/paradrop.scr", 'iprintlnbold "Flak got one of the C-47s - fewer troopers inbound!"', 1, "para_flak", '"Flak hit a C-47 - fewer troopers inbound"'),
    FA("coop_mod/paradrop.scr", 'iprintlnbold "Allied paratroopers have landed!"', 1, "para_land", '"Allied paratroopers have landed"'),
    FA("coop_mod/paradrop.scr", 'iprintlnbold "An Allied Medic revived a teammate!"', 1, "para_medic", '"An Allied Medic revived a teammate"'),
    FP("coop_mod/paradrop.scr", 'iprintlnbold ("Allied Medic patched you up! HP: " + local.nh)', "local.target", 2, "para_patch",
       '("An Allied Medic patched you up - " + local.nh + " HP")'),
    FA("coop_mod/paradrop.scr", 'iprintlnbold "Allied paratroopers eliminated."', 1, "para_dead", '"Allied paratroopers eliminated"'),

    # ================================================================ objective_drop.scr
    FA("coop_mod/objective_drop.scr", 'iprintlnbold "Intel recovered: a Signal Smoke Grenade is stashed at the objective!"', 1, "od_smoke",
       '"Intel: a Signal Smoke Grenade is stashed at the objective"'),
    FA("coop_mod/objective_drop.scr", 'iprintlnbold "Intel recovered: a pair of Binoculars is stashed at the objective!"', 1, "od_binoc",
       '"Intel: a pair of Binoculars is stashed at the objective"'),
    FA("coop_mod/objective_drop.scr", 'iprintlnbold (local.player.netname + " picked up the Signal Smoke!")', 1, "smoke",
       '(local.player.netname + " picked up the Signal Smoke")'),
    (M, "coop_mod/objective_drop.scr", 'iprintlnbold "Signal Smoke ready! Equip grenades and throw - Allied paradrop falls where it hits!"',
     'waitthread coop_mod/feed.scr::feed_hint local.player "smoke" "Signal Smoke: equip grenades and throw it - the Allied paradrop lands where it hits"', 1),
    FA("coop_mod/objective_drop.scr", 'iprintlnbold (local.player.netname + " picked up Binoculars!")', 1, "binoc",
       '(local.player.netname + " picked up the Binoculars")'),
    (M, "coop_mod/objective_drop.scr", 'iprintlnbold "Equip binoculars from pistol slot, aim and fire [LMB] to call bombing runs! (3 strikes)"',
     'waitthread coop_mod/feed.scr::feed_hint local.player "binoc" "Binoculars: equip from the pistol slot, aim and fire to call a bombing run (3 strikes)"', 1),
    FA("coop_mod/objective_drop.scr", 'iprintlnbold ( "Binoculars recovered - " + level.coop_binoc_uses + " strike(s) left" )', 1, "binoc",
       '( "Binoculars recovered - " + level.coop_binoc_uses + " strike(s) left" )'),

    # ================================================================ squad / key items / aircraft
    FA("coop_mod/allysquad.scr", 'iprintlnbold ( "A squadmate is DOWN - look for the medkit marker and stand over them!" )', 0, "ally_down",
       '"A squadmate is down - stand over him to revive"'),
    FA("coop_mod/allysquad.scr", 'iprintlnbold ( "A squadmate bled out." )', 1, "ally_bled", '"A squadmate bled out"'),
    FA("coop_mod/allysquad.scr", 'iprintlnbold ( local.player.netname + " got a squadmate back on their feet - that was his last one." )', 1, "ally_rev",
       '( local.player.netname + " got a squadmate back on his feet" )'),
    FA("coop_mod/keyitems.scr", 'iprintlnbold ( local.player.netname + " dropped a heavy weapon where they fell - grab it to keep it in play." )', 1, "hw",
       '( local.player.netname + " dropped a heavy weapon where he fell" )'),
    FA("coop_mod/keyitems.scr", 'iprintlnbold ( local.player.netname + " recovered a heavy weapon!" )', 1, "hw",
       '( local.player.netname + " recovered a heavy weapon" )'),
    FA("coop_mod/aircraft.scr", 'iprintln ( "Allied fire brought down " + local.what + "!" )', 1, "air_down",
       '( "Allied fire brought down " + local.what )', 2),
    FA("coop_mod/aircraft.scr", 'iprintln_noloc ( local.a.netname + " shot down " + local.what + "!" )', 1, "air_down",
       '( local.a.netname + " shot down " + local.what )'),

    # ================================================================ DBNO (the bleed-out agent owns the ring/heartbeat/crawl hunks)
    CUT("coop_mod/dbno.scr", 'local.player iprint local.down_msg 1', 'local.down_msg\t//[user 2026-10-05] "the You are DOWN text needs to go" - the bleed-out ring, vignette and heartbeat carry it'),
    (M, "coop_mod/dbno.scr",
     '\tlocal.msg = local.player.netname + " is down - " + local.detail + " (" + local.actual_timer + " seconds)"\n'
     '\tlevel.coop_dbnoBannerUntil = level.time + 6\n',
     '\t//[user 2026-10-05] HUD declutter: the teammate alert is ONE quiet event-feed line (coop_mod/feed.scr). The medic icon\n'
     '\t//and mini ring over the downed player (cgame/cg_coopbleed.c) carry where he is and how long he has; the slot-216\n'
     '\t//banner below is left to a feed-less (older) cgame only.\n'
     '\twaitthread coop_mod/feed.scr::feed_others_cap local.player 0 ( "dn" + local.player.entnum ) ( local.player.netname + " is down" )\n'
     '\tlocal.msg = local.player.netname + " is down - " + local.detail + " (" + local.actual_timer + " seconds)"\n'
     '\tlevel.coop_dbnoBannerUntil = level.time + 6\n', 1),
    (M, "coop_mod/dbno.scr",
     '\tlocal.msg = local.player.netname + " is calling for a medic!"\n'
     '\tlevel.coop_dbnoBannerUntil = level.time + 6\n',
     '\t//[user 2026-10-05] HUD declutter: one feed line (see the down alert above); the banner only for an older cgame\n'
     '\twaitthread coop_mod/feed.scr::feed_others_cap local.player 0 ( "med" + local.player.entnum ) ( local.player.netname + " is calling for a medic" )\n'
     '\tlocal.msg = local.player.netname + " is calling for a medic!"\n'
     '\tlevel.coop_dbnoBannerUntil = level.time + 6\n', 1),
    # the 216 banner itself: only for a client without the feed (both banner loops)
    (M, "coop_mod/dbno.scr",
     '\t\t\tif( $player[local.i].flags["coop_isActive"] == 1 ){\n'
     '\t\t\t\tlocal.o = $player[local.i]\n'
     '\t\t\t\t//[2026-09-25, bug-2906] claim on show; dbno_downBannerClear re-sends the hide (hudresend.scr)\n',
     '\t\t\tif( $player[local.i].flags["coop_isActive"] == 1 && !(waitthread coop_mod/feed.scr::feed_capable $player[local.i]) ){\n'
     '\t\t\t\tlocal.o = $player[local.i]\n'
     '\t\t\t\t//[2026-09-25, bug-2906] claim on show; dbno_downBannerClear re-sends the hide (hudresend.scr)\n', 2),
    (M, "coop_mod/dbno.scr",
     '\t\t\t\t\tprintln( "^~^~^ DBNO teamrevive by=" + local.reviver.netname + " kitsLeft=" + ( local.mk - 1 ) )\n',
     '\t\t\t\t\tprintln( "^~^~^ DBNO teamrevive by=" + local.reviver.netname + " kitsLeft=" + ( local.mk - 1 ) )\n'
     '\t\t\t\t\t//[user 2026-10-05] HUD declutter: one quiet feed line for the squad\n'
     '\t\t\t\t\twaitthread coop_mod/feed.scr::feed_all 1 ( "rev" + local.downed.entnum ) ( local.reviver.netname + " revived " + local.downed.netname )\n', 1),
    CUT("coop_mod/dbno.scr", 'local.player iprint "A medkit brought you back to your feet!" 1', '"^~^~^ DBNO corpse revive by medkit (feed: cut)"'),
    (M, "coop_mod/dbno.scr", 'ihuddraw_string local.player 33 "An Allied Medic revived you!"',
     'ihuddraw_string local.player 33 ""\t//[user 2026-10-05] HUD declutter: the squad feed says it (paradrop.scr)', 1),

    # ================================================================ medkit.scr (self)
    FP("coop_mod/medkit.scr", 'local.player iprint "Medkit refilled!" 1', "local.player", 2, "mk", '"Medkit refilled"', 2),
    CUT("coop_mod/medkit.scr", 'local.player iprint "Pack detected nearby!" 1', '"^~^~^ MEDKIT pack detected nearby (feed: cut)"'),
    FP("coop_mod/medkit.scr", 'local.player iprint ( "Medkit stowed (" + ( local.mk3 + 1 ) + "/" + local.cap + ")" ) 1', "local.player", 2, "mk",
       '( "Medkit stowed (" + ( local.mk3 + 1 ) + "/" + local.cap + ")" )'),
    FP("coop_mod/medkit.scr", 'local.player iprint "Already at full health" 1', "local.player", 2, "mk", '"Already at full health"'),
    FP("coop_mod/medkit.scr", 'local.player iprint "No medkits remaining" 1', "local.player", 2, "mk", '"No medkits remaining"'),
    FP("coop_mod/medkit.scr", 'local.player iprint "Heal interrupted!" 1', "local.player", 2, "mk", '"Heal interrupted"'),
    FP("coop_mod/medkit.scr", 'local.player iprint "You have bandaged yourself up." 1', "local.player", 2, "mk", '"You bandaged yourself up"'),
    (M, "coop_mod/medkit.scr", 'if( local.msg != "" ){ local.healer iprint local.msg 1 }',
     'if( local.msg != "" ){ waitthread coop_mod/feed.scr::feed_player local.healer 2 "mk_heal" local.msg }', 1),
    FP("coop_mod/medkit.scr", 'local.healer iprint local.msg 1', "local.healer", 2, "mk_heal", "local.msg"),
    FP("coop_mod/medkit.scr", 'local.target iprint local.msg2 1', "local.target", 2, "mk_heal", "local.msg2"),
    FP("coop_mod/medkit.scr", 'local.player iprint "No medkits - cannot self-revive" 0', "local.player", 2, "mk", '"No medkits - cannot self-revive"'),
    FP("coop_mod/medkit.scr", 'local.player iprint "Hardcore: no self-revive while a teammate is up - keep holding [USE] to give up." 1', "local.player", 0, "hc_selfrev",
       '"Hardcore: no self-revive while a teammate is up - keep holding USE to give up"'),
    CUT("coop_mod/medkit.scr", 'iprintlnbold ("coop_scan: Found " + local.dbg_count + " health packs")', '("^~^~^ coop_scan: Found " + local.dbg_count + " health packs")'),

    # ================================================================ deployables, views, cosmetics (self)
    FP("coop_mod/ammobox.scr", 'local.player iprint "You have already deployed your ammo box this mission!" 1', "local.player", 2, "ammo",
       '"You already deployed your ammo box this mission"'),
    FP("coop_mod/ammobox.scr", 'local.player iprint "Not while you are in disguise." 1', "local.player", 2, "ammo", '"Not while you are in disguise"'),
    FP("coop_mod/ammobox.scr", 'local.player iprint "Ammo box deployed - each squadmate can resupply from it twice." 1', "local.player", 2, "ammo",
       '"Ammo box deployed - each squadmate can resupply from it twice"'),
    FP("coop_mod/ammobox.scr", 'local.player iprint local.msg 1', "local.player", 2, "ammo", "local.msg", 2),
    FP("coop_mod/cover.scr", 'local.player iprint "No sandbag placements remaining!" 1', "local.player", 2, "sandbag", '"No sandbag placements remaining"'),
    FP("coop_mod/cover.scr", 'local.player iprint "Not while you are in disguise." 1', "local.player", 2, "sandbag", '"Not while you are in disguise"'),
    FP("coop_mod/cover.scr", 'local.player iprint "Cannot place here - no ground!" 1', "local.player", 2, "sandbag", '"Cannot place here - no ground"'),
    FP("coop_mod/cover.scr", 'local.player iprint "Cannot place here - ground too high!" 1', "local.player", 2, "sandbag", '"Cannot place here - ground too high"'),
    FP("coop_mod/cover.scr", 'local.owner_ent iprint "Sandbag refunded!" 1', "local.owner_ent", 2, "sandbag", '"Sandbag refunded"'),
    CUT("coop_mod/takecover.scr", 'local.player iprint "Cover released"', '"^~^~^ TAKECOVER released (feed: cut)"'),
    FP("coop_mod/takecover.scr", 'local.player iprint "No cover here - face a low wall, sandbags or crates to crouch behind" 1', "local.player", 2, "cover",
       '"No cover here - face a low wall, sandbags or crates"'),
    CUT("coop_mod/takecover.scr", 'local.player iprint "In cover against the wall - hold FIRE to blind-fire around the opening"', '"^~^~^ TAKECOVER wall (feed: cut)"'),
    CUT("coop_mod/takecover.scr", 'local.player iprint "In cover - hold FIRE to blind-fire over the top"', '"^~^~^ TAKECOVER low (feed: cut)"'),
    CUT("coop_mod/thirdperson.scr", 'local.player iprint "View: First Person"', '"^~^~^ VIEW first person"'),
    CUT("coop_mod/thirdperson.scr", 'local.player iprint "View: Free Cam (body stays put)"', '"^~^~^ VIEW free cam"'),
    CUT("coop_mod/thirdperson.scr", 'local.player iprint "View: Third Person (chase)"', '"^~^~^ VIEW third person"'),
    FP("coop_mod/surrender.scr", 'local.player iprint "Recruited - he fights for you now"', "local.player", 2, "recruit", '"Recruited - he fights for you now"'),
    FP("coop_mod/helmet.scr", 'local.player iprint "Can\'t change helmet while down/dead." 1', "local.player", 2, "cosm", '"Can\'t change helmet while down"'),
    FP("coop_mod/helmet.scr", 'local.player iprint "No other helmets unlocked yet." 1', "local.player", 2, "cosm", '"No other helmets unlocked yet"'),
    FP("coop_mod/helmet.scr", 'local.player iprint ( "Helmet: " + level.coop_helmetName[local.idx] ) 1', "local.player", 2, "cosm",
       '( "Helmet: " + level.coop_helmetName[local.idx] )'),
    FP("coop_mod/helmet.scr", 'local.player iprint "Can\'t change skin while down/dead." 1', "local.player", 2, "cosm", '"Can\'t change uniform while down"'),
    FP("coop_mod/helmet.scr", 'local.player iprint "No other skins unlocked yet." 1', "local.player", 2, "cosm", '"No other uniforms unlocked yet"'),
    FP("coop_mod/helmet.scr", 'local.player iprint ( "Skin: " + local.skin )', "local.player", 2, "cosm", '( "Uniform: " + local.skin )'),
    # the automated lock notices: the armory's own REQ rows already show why an item is locked -> armory status only
    FP("coop_mod/helmet.scr", 'local.player iprint ( "Helmet locked: " + level.coop_helmetName[local.idx] + " - " + local.req ) 1', "local.player", 5, "lock",
       '( "Helmet locked: " + level.coop_helmetName[local.idx] + " - " + local.req )'),
    FP("coop_mod/helmet.scr", 'local.player iprint ( "Skin locked: " + level.coop_armorySkins[local.idx] + " - " + local.req ) 1', "local.player", 5, "lock",
       '( "Uniform locked: " + level.coop_armorySkins[local.idx] + " - " + local.req )'),
    FP("coop_mod/gloves.scr", 'local.player iprint ( "Gloves locked: " + level.coop_gloveName[local.idx] + " - " + local.req ) 1', "local.player", 5, "lock",
       '( "Gloves locked: " + level.coop_gloveName[local.idx] + " - " + local.req )'),
    FP("coop_mod/player.scr", 'local.player iprint ( "Armory: that skin is still locked - wearing " + local.heal )', "local.player", 2, "lock",
       '( "Armory: that uniform is still locked - wearing " + local.heal )'),

    # ================================================================ armory (loadoutpick.scr): confirmations -> status, denials -> self line
    FP("coop_mod/loadoutpick.scr", 'local.player iprint ("Armory: cleared PRIMARY " + local.other + " (one " + local.r["class"] + " per loadout)")', "local.player", 2, "armory",
       '("Armory: cleared " + local.other + " (one " + local.r["class"] + " per loadout)")'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint ("Armory: " + local.r["name"] + " equipped")', "local.player", 5, "armory",
       '("Armory: " + local.r["name"] + " equipped")'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint local.msg\n', "local.player", 2, "armory", 'local.msg\n'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint "Armory: kits are scripted on this mission - picks apply from the next map"', "local.player", 2, "armory",
       '"Armory: kits are scripted on this mission - picks apply from the next map"'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint "Armory: your loadout has been applied"', "local.player", 5, "armory", '"Armory: your loadout has been applied"'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint "Armory: picks cleared - using the standard mission kit"', "local.player", 5, "armory",
       '"Armory: picks cleared - using the standard mission kit"'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint "Standard"\n', "local.player", 5, "armory", '"Standard finish"\n'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint "Pick a weapon for that slot first"', "local.player", 2, "armory", '"Pick a weapon for that slot first"'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint ( "No " + level.coop_skinFinName[local.fid] + " finish for this weapon" )', "local.player", 2, "armory",
       '( "No " + level.coop_skinFinName[local.fid] + " finish for this weapon" )'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint ( level.coop_skinFinName[local.fid] + " is locked - see CHALLENGES" )', "local.player", 2, "armory",
       '( level.coop_skinFinName[local.fid] + " is locked - see CHALLENGES" )'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint "Master this weapon first (its kill challenge)"', "local.player", 2, "armory",
       '"Master this weapon first (its kill challenge)"', 2),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint ( level.coop_skinFinName[local.fid] + " finish applied" )', "local.player", 5, "armory",
       '( level.coop_skinFinName[local.fid] + " finish applied" )'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint "No model variants for this weapon"', "local.player", 2, "armory", '"No model variants for this weapon"'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint "This variant is locked - see CHALLENGES"', "local.player", 2, "armory", '"This variant is locked - see CHALLENGES"'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint "Standard model"', "local.player", 5, "armory", '"Standard model"'),
    FP("coop_mod/loadoutpick.scr", 'local.player iprint ( level.coop_skinMvName[local.give][local.fid] + " equipped" )', "local.player", 5, "armory",
       '( level.coop_skinMvName[local.give][local.fid] + " equipped" )'),

    # ================================================================ player / main / misc
    FA("coop_mod/player.scr", 'iprintlnbold_noloc("COOP: LMS inactive - Joining allowed")', 1, "lms_state", '"Last Man Standing off - late joining allowed"'),
    FA("coop_mod/player.scr", 'iprintlnbold_noloc("COOP: LMS active - No late joining")', 1, "lms_state", '"Last Man Standing on - no late joining"'),
    CUT("coop_mod/player.scr", 'local.player iprint ("manageNamechange - could not retrive command list")', '("^~^~^ manageNamechange - could not retrive command list")'),
    CUT("coop_mod/player.scr", 'local.player iprint ("playerNameCommand: Your Command is not on valid List")', '("^~^~^ playerNameCommand: Your Command is not on valid List")'),
    CUT("coop_mod/player.scr", 'local.player iprint "Coming soon" 1 }\n\telse if(local.arrayIndex==12){ local.player iprint "Coming soon" 1 }\n\telse if(local.arrayIndex==13){ local.player iprint "Coming soon" 1 }',
        '"^~^~^ name command 11 coming soon" }\n\telse if(local.arrayIndex==12){ println "^~^~^ name command 12 coming soon" }\n\telse if(local.arrayIndex==13){ println "^~^~^ name command 13 coming soon" }'),
    CUT("coop_mod/player.scr", 'local.player iprint "You salute"', '"^~^~^ EMOTE salute"'),
    CUT("coop_mod/player.scr", 'local.player iprint "At ease (move to stop)"', '"^~^~^ EMOTE at ease"'),
    CUT("coop_mod/player.scr", 'local.player iprint "Stretching (move to stop)"', '"^~^~^ EMOTE stretch"'),
    CUT("coop_mod/player.scr", 'iprintlnbold_noloc("COOPDEBUG: incolplete command, DEVELOPER please fix - playerExtractedStuck")',
        '("^~^~^ COOPDEBUG: incomplete command - playerExtractedStuck")'),
    FP("coop_mod/player.scr", 'local.player iprint "If you are stuck, press use to switch to a different spawnlocation" 1', "local.player", 2, "stuck",
       '"Stuck? Press USE to move to a different spawn point"'),
    FP("coop_mod/player.scr", 'local.player iprint "Moved you to a different spawnlocation" 1', "local.player", 2, "stuck", '"Moved you to a different spawn point"'),
    CUT("coop_mod/player.scr", 'local.player iprint ( "Spawn protection: " + local.secs + " seconds" ) 0', '( "^~^~^ SPAWNPROT " + local.secs + " seconds (feed: cut)" )'),
    FP("coop_mod/player.scr", 'local.player iprint local.deaths 0', "local.player", 0, "lms", "local.deaths"),
    FP("coop_mod/main.scr", 'local.player iprint ( "You have 0 lives left - LastManStanding is active!" ) 1', "local.player", 0, "lms",
       '"You have 0 lives left - Last Man Standing is active"'),
    FP("coop_mod/main.scr", 'local.player iprint "You are allowed back in the game!" 0', "local.player", 2, "lms", '"You are allowed back in the game"'),
    FA("coop_mod/main.scr", 'iprintlnbold_noloc("COOP: LMS inactive - Joining allowed")', 1, "lms_state", '"Last Man Standing off - late joining allowed"'),
    FA("coop_mod/main.scr", 'iprintlnbold_noloc("COOP: LMS active - No late joining")', 1, "lms_state", '"Last Man Standing on - no late joining"'),
    (M, "coop_mod/main.scr", 'local.player iprint local.message local.bold\n',
     '//[user 2026-10-05] HUD declutter: rate-limited contextual info (vehicle cooldowns, "not allowed to move") -> event feed\n'
     '\twaitthread coop_mod/feed.scr::feed_player local.player 2 "info" local.message\n', 1),
    FP("coop_mod/holdout.scr", 'local.p iprint "You are back in the fight!" 0', "local.p", 2, "holdout", '"You are back in the fight"'),
    FA("coop_mod/e1l4alarm.scr", 'iprintlnbold_noloc( "^3Alarm silenced." )', 1, "alarm", '"Alarm silenced"'),
    FA("coop_mod/admin.scr", 'iprintlnbold_noloc( "Admin kicked " + local.p.netname )', 1, "admin", '( "Admin kicked " + local.p.netname )'),
    FA("coop_mod/admin.scr", 'iprintlnbold_noloc( "Admin banned " + local.p.netname )', 1, "admin", '( "Admin banned " + local.p.netname )'),
    FA("coop_mod/admin.scr", 'iprintlnbold_noloc( "Banned player rejected: " + local.p.netname )', 1, "admin", '( "Banned player rejected: " + local.p.netname )'),
    FA("coop_mod/admin.scr", 'iprintlnbold_noloc( "Admin slayed " + local.p.netname )', 1, "admin", '( "Admin slayed " + local.p.netname )'),
    FA("coop_mod/admin.scr", 'iprintlnbold_noloc( "Admin restarting the map..." )', 1, "admin", '"Admin is restarting the map"'),
    CUT("coop_mod/admin.scr", 'iprintlnbold_noloc( "GO SLEEP! YOU ARE SLIPPING." )', '( "^~^~^ adminCommand: no data" )'),
    CUT("coop_mod/mom_login.scr", 'self iprint ( "Are you hacking dude ?" )', '( "^~^~^ mom_login rejected" )'),
    CUT("coop_mod/coop_placements.scr", 'iprintlnbold "COOP e1l2 placements: THREAD START"', '"^~^~^ COOP e1l2 placements: THREAD START"'),
    CUT("coop_mod/coop_placements.scr", 'iprintlnbold ("COOP e1l2 placements: DONE spawned " + local.bn + " objects")', '("^~^~^ COOP e1l2 placements: DONE spawned " + local.bn + " objects")'),
    CUT("coop_mod/replace.scr", 'iprintlnbold_noloc("Coop: WARNING: spawnclip - NULL entity given")', '("^~^~^ Coop: WARNING: spawnclip - NULL entity given")'),
    CUT("coop_mod/replace.scr", 'iprintlnbold_noloc(local.message)', '( "^~^~^ " + local.message )'),
    CUT("coop_mod/replace.scr", 'iprintlnbold_noloc("Coop Error: teleportToOnTouch parm2 entity("+local.targetnameParm1+") missing")',
        '("^~^~^ Coop Error: teleportToOnTouch parm2 entity("+local.targetnameParm1+") missing")'),
    CUT("coop_mod/spawnlocations.scr", 'iprintlnbold_noloc ( "MAXIMUM NUMBER OF COOP SPAWNPOINTS REACHED" )', '( "^~^~^ MAXIMUM NUMBER OF COOP SPAWNPOINTS REACHED" )'),
    FP("coop_mod/collectible.scr", 'local.best iprint "Press USE to take the blueprint" 1', "local.best", 2, "bp", '"Press USE to take the blueprint"'),
    FP("coop_mod/collectible.scr", 'local.player iprint "Blueprint set complete - report to debrief" 1', "local.player", 2, "bp", '"Blueprint set complete - see the debrief"'),
    FP("coop_mod/collectible.scr", 'local.player iprint ( "Blueprint cache " + local.total + ": the coin lands TAILS - nothing this time" ) 1', "local.player", 2, "bp",
       '( "Blueprint cache " + local.total + ": tails - nothing this time" )'),
    FP("coop_mod/collectible.scr", 'local.player iprint ( "Blueprint cache " + local.total + ": HEADS - but you already own everything" ) 1', "local.player", 2, "bp",
       '( "Blueprint cache " + local.total + ": heads - you already own everything" )'),
    FP("coop_mod/collectible.scr", 'local.player iprint ( "Blueprint cache " + local.total + ": HEADS! Unlocked: " + local.nm ) 1', "local.player", 2, "bp",
       '( "Blueprint cache " + local.total + ": heads - unlocked " + local.nm )'),
    CUT("coop_mod/mom_actions.scr", 'iprintlnbold_noloc ( "pressed 1" )', '( "^~^~^ mom pressed 1" )'),
    CUT("coop_mod/mom_actions.scr", 'iprintlnbold_noloc ( "pressed 2" )', '( "^~^~^ mom pressed 2" )'),
    CUT("coop_mod/mom_actions.scr", 'iprintlnbold_noloc ( "pressed 3" )', '( "^~^~^ mom pressed 3" )'),
    CUT("coop_mod/mom_actions.scr", 'iprintlnbold_noloc ( "pressed 4" )', '( "^~^~^ mom pressed 4" )'),
    CUT("coop_mod/mom_actions.scr", 'iprintlnbold_noloc ( "pressed 5" )', '( "^~^~^ mom pressed 5" )'),
    CUT("coop_mod/mom_actions.scr", 'iprintlnbold_noloc ( "pressed 6" )', '( "^~^~^ mom pressed 6" )'),
    CUT("coop_mod/mom_actions.scr", 'iprintlnbold_noloc ( "pressed 9" )', '( "^~^~^ mom pressed 9" )'),
    CUT("coop_mod/mom_actions.scr", 'iprintlnbold_noloc ( "pressed 12" )', '( "^~^~^ mom pressed 12" )'),

    # ================================================================ XP / challenges / debrief
    CUT("coop_mod/xp.scr", 'local.player iprint local.srline 1', '( "^~^~^ XP " + local.srline )'),
    (M, "coop_mod/xp.scr", 'local.player iprint ( "PRESTIGE STAR " + local.newprestige + "!" ) 1',
     'waitthread coop_mod/feed.scr::feed_player local.player 2 "promo" ( "Prestige star " + local.newprestige )\n'
     '\t\twaitthread coop_mod/feed.scr::feed_mapList local.player ( "Prestige star " + local.newprestige )', 1),
    (M, "coop_mod/xp.scr", '\t\tthread xp_hud_popup local.player\n',
     '\t\t//[user 2026-10-05] HUD declutter: the mid-mission rank bar is gone - rank and XP are on the debrief card and the\n'
     '\t\t//Service Record. coop_xpRankBar 1 brings the bar back. The crosshair "+N" micro popups are unchanged.\n'
     '\t\tif( getcvar( "coop_xpRankBar" ) == "1" ){ thread xp_hud_popup local.player }\n'
     '\t\telse { local.player.flags["coop_xp_popupGain"] = 0 }\t//nothing shows the accumulated gain - do not let it grow\n', 1),
    (M, "coop_mod/xp.scr",
     'xp_promo_ceremony local.player local.rank:{\n\tif( local.player == NULL ){ end }\n',
     'xp_promo_ceremony local.player local.rank:{\n\tif( local.player == NULL ){ end }\n'
     '\t//[user 2026-10-05] HUD declutter: mid-mission a promotion is ONE quiet feed line (no ceremony, no ping, no duck).\n'
     '\t//The debrief card still rolls every rank crossed with the full moment (xp_summary_card). An older cgame keeps\n'
     '\t//the ceremony below.\n'
     '\tif( level.coop_xp_summaryActive != 1 ){\n'
     '\t\tif( waitthread coop_mod/feed.scr::feed_capable local.player ){\n'
     '\t\t\twaitthread coop_mod/feed.scr::feed_player local.player 2 "promo" ( "Promoted: " + level.coop_xp_rankName[local.rank] )\n'
     '\t\t\tend\n'
     '\t\t}\n'
     '\t}\n', 1),
    (M, "coop_mod/xp.scr", 'ihuddraw_string      local.p 127 "UNLOCKED THIS MISSION:"',
     'ihuddraw_string      local.p 127 "EARNED THIS MISSION:"\t//[user 2026-10-05] + challenges, medals, prestige (feed.scr::feed_mapList)', 1),
    (M, "coop_mod/xp.scr",
     '\tif( local.p.flags["coop_xp_cardOn"] == 1 ){ end }\t\t// [user 07-18 bug-804] one card per player - a second thread on the same slots is the glitch machine\n'
     '\tlocal.p.flags["coop_xp_cardOn"] = 1\n',
     '\tif( local.p.flags["coop_xp_cardOn"] == 1 ){ end }\t\t// [user 07-18 bug-804] one card per player - a second thread on the same slots is the glitch machine\n'
     '\tlocal.p.flags["coop_xp_cardOn"] = 1\n'
     '\tthread coop_mod/feed.scr::feed_lastMission local.p\t//[user 2026-10-05] the LAST MISSION page (main menu) gets this debrief\n', 1),
    (M, "coop_mod/challenges.scr",
     'chal_toast_show local.player local.title:{\n\tif( local.player == NULL ){ end }\n',
     'chal_toast_show local.player local.title:{\n\tif( local.player == NULL ){ end }\n'
     '\t//[user 2026-10-05] HUD declutter: mid-mission a completion is ONE quiet feed line (no toast, no typewriter); the\n'
     '\t//title is listed on the debrief card. An older cgame keeps the toast below.\n'
     '\tif( waitthread coop_mod/feed.scr::feed_capable local.player ){\n'
     '\t\twaitthread coop_mod/feed.scr::feed_chalDone local.player local.title\n'
     '\t\tend\n'
     '\t}\n', 1),

    # ================================================================ global/items.scr - "You have acquired" -> pickup icon for the picker
    (M, "global/items.scr",
     'add_item local.passed_item local.nomessage:\n',
     'add_item local.passed_item local.nomessage:\n'
     '\t//[HZM coop 2026-10-05] HUD declutter: in coop the "You have acquired ..." line was an iprintln BROADCAST - every\n'
     '\t//player was told, wherever he was. It becomes a small pickup ICON + one word in the event feed, for every coop\n'
     '\t//player since every one receives the item (feed.scr::feed_itemPickup). Vanilla single player (gametype 0) is untouched.\n'
     '\tlocal.coopPickMsg = 0\n'
     '\tif( level.gametype != 0 ){\n'
     '\t\tif( local.nomessage == NIL ){ local.coopPickMsg = 1 }\n'
     '\t\tlocal.nomessage = 1\n'
     '\t}\n', 1),
    (M, "global/items.scr",
     '\t//*** draw the items on the screen\n\tthread draw_items\n\nadd_item_end:\n',
     '\t//*** draw the items on the screen\n\tthread draw_items\n'
     '\tif( local.coopPickMsg == 1 ){ thread coop_mod/feed.scr::feed_itemPickup NIL local.passed_item local.item_graphic }\n'
     '\nadd_item_end:\n', 1),

    # ================================================================ maps: developer prints (CUT)
    CUT("maps/e3l1.scr", 'iprintlnbold_noloc ("Fadein")', '("^~^~^ e3l1 Fadein")'),
    CUT("maps/e3l1.scr", 'iprintlnbold_noloc ("Briefing")', '("^~^~^ e3l1 Briefing")'),
    CUT("maps/e3l1.scr", 'iprintlnbold_noloc ("COOP SKIPPED: SetPlayerHealthScale")', '("^~^~^ e3l1 COOP SKIPPED: SetPlayerHealthScale")'),
    CUT("maps/e3l1/JeepRidePart3.scr", 'iprintlnbold_noloc ("jeepUseLoop - use")', '("^~^~^ jeepUseLoop - use")'),
    CUT("maps/e3l1/JeepRidePart3.scr", 'iprintlnbold_noloc ("jeepUseLoop - exit")', '("^~^~^ jeepUseLoop - exit")'),
    CUT("maps/e3l1/AfterSnipers.scr", 'iprintlnbold_noloc ("ExitStageRight")', '("^~^~^ ExitStageRight")'),
    CUT("maps/e3l1/AfterSnipers.scr", 'iprintlnbold_noloc ("RollOutTank2 -> playertank?")', '("^~^~^ RollOutTank2 -> playertank?")'),
    CUT("maps/e2l2/guardPost.scr", 'iprintlnbold_noloc("DoCappyAirFieldSpeech - moved players")', '("^~^~^ DoCappyAirFieldSpeech - moved players")'),
    CUT("maps/e2l2/guardPost.scr", 'iprintlnbold_noloc("DoCappyAirFieldSpeech - skipped dialog")', '("^~^~^ DoCappyAirFieldSpeech - skipped dialog")'),
    CUT("maps/e2l2/briefing.scr", 'iprintlnbold_noloc("golyndon - skipped dialog");', '("^~^~^ golyndon - skipped dialog");'),
    CUT("maps/e2l2/briefing.scr", 'iprintlnbold_noloc("golyndon - skipped to DoCappyAirFieldSpeech")', '("^~^~^ golyndon - skipped to DoCappyAirFieldSpeech")'),
    CUT("maps/e1l3/FinalEscape.scr", 'iprintlnbold_noloc("$playerChangingClothes waittill trigger")', '("^~^~^ $playerChangingClothes waittill trigger")'),
    CUT("maps/e1l3/FinalEscape.scr", 'iprintlnbold_noloc("$playerChangingClothes triggered")', '("^~^~^ $playerChangingClothes triggered")'),
    CUT("maps/e1l3/FinalEscape.scr", 'iprintlnbold_noloc("clausEscapeRoute waitForPlayer finished")', '("^~^~^ clausEscapeRoute waitForPlayer finished")'),
    CUT("maps/e1l3/FinalEscape.scr", 'iprintlnbold_noloc("$playerFullyDisguised triggered")', '("^~^~^ $playerFullyDisguised triggered")'),
    CUT("maps/e1l3/FinalEscape.scr", 'iprintlnbold_noloc("playerFullyDisguised done")', '("^~^~^ playerFullyDisguised done")'),
    CUT("maps/e1l3/Briefing.scr", 'iprintlnbold_noloc "briefing water mortar over"', '"^~^~^ briefing water mortar over"'),
    CUT("maps/e3l2/MiniCourtyard_Section.scr", 'iprintlnbold_noloc("$pow1_door should open now")', '("^~^~^ $pow1_door should open now")'),
    CUT("maps/e3l2/MiniCourtyard_Section.scr", 'iprintlnbold_noloc("$MCJailDoor is closing and will be locked")', '("^~^~^ $MCJailDoor is closing and will be locked")'),
    CUT("maps/e3l2/MiniCourtyard_Section.scr", 'iprintlnbold_noloc("$MCJailDoor unlocked")', '("^~^~^ $MCJailDoor unlocked")'),
    CUT("maps/e3l3/e3l3_AB41.scr", 'iprintlnbold "^~^~^ AB41 stall-recover: re-issuing drive"', '"^~^~^ AB41 stall-recover: re-issuing drive"'),
    CUT("maps/e3l1/BritHQ.scr", 'iprintln "KILLING WALL"', '"^~^~^ KILLING WALL"'),
    CUT("maps/e1l1/scene2.scr", 'iprintlnbold_noloc( "e1l1/scene2.scr::doMiddleDeath is triggering.... fixme" )', '( "^~^~^ e1l1/scene2.scr::doMiddleDeath is triggering" )'),
    CUT("maps/e2l1/gliderride.scr", 'iprintlnbold_noloc("e2l1/gliderride.scr::UnrestrictView - needs fixing")', '("^~^~^ e2l1/gliderride.scr::UnrestrictView")'),
    CUT("maps/e1l1.scr", 'iprintlnbold("error doMineField is not working: "+parm.other)', '("^~^~^ error doMineField is not working: "+parm.other)'),
    CUT("maps/e1l1/aicleanup.scr", 'iprintln "AICLEANUP >>>> local. trigger is NULL"', '"^~^~^ AICLEANUP local.trigger is NULL"'),
    CUT("maps/m1l2a.scr", 'iprintlnbold_noloc ( "this was disabled by chrissstrahl" )', '( "^~^~^ m1l2a: disabled path reached" )'),
    CUT("maps/e3l4/Outro.scr", 'iprintln ( $player[1].viewangles )', '( $player[1].viewangles )'),

    # ================================================================ maps: per-player ride notes, saves, map pickups
    FP("maps/e3l1.scr", 'local.player iprint "Back on the .30cal!" 1', "local.player", 2, "ride", '"Back on the .30cal"'),
    FP("maps/e3l1.scr", 'local.player iprint "Riding along - you unload when the jeep stops" 1', "local.player", 2, "ride", '"Riding along - you unload when the jeep stops"'),
    FP("maps/e3l3.scr", 'local.player iprint "Back aboard the AB41!" 1', "local.player", 2, "ride", '"Back aboard the AB41"'),
    FP("maps/e3l4.scr", 'local.player iprint "Back on the convoy .30cal!" 1', "local.player", 2, "ride", '"Back on the convoy .30cal"'),
    FA("maps/e1l3/Sneakers.scr", 'iprintlnbold_noloc("Coop Mission Progress has been saved!")', 1, "saved", '"Mission progress saved"'),
    FA("maps/e1l2/Artillery.scr", 'iprintlnbold_noloc "You have acquired the KAR98 Sniper Rifle"', 1, "pickup", '"Picked up: KAR98 sniper rifle"'),
    FA("maps/e1l2/Intro.scr", 'iprintlnbold (loc_convert_string ("You have acquired a mine detector"))', 1, "pickup", '"Picked up: mine detector"'),
    FA("maps/e3l4/Bunker4.scr", 'iprintln "You picked up a Bazooka."', 1, "pickup", '"Picked up: Bazooka"'),
    FA("maps/e3l4/Tunnel.scr", 'iprintln "You picked up an STG-44."', 1, "pickup", '"Picked up: StG 44"'),
    FA("maps/e3l4/Tunnel.scr", 'iprintln "You picked up a Shotgun."', 1, "pickup", '"Picked up: Shotgun"'),
    FA("maps/m4l2.scr", 'iprintlnbold "You have the KAR98 Sniper Rifle."', 1, "pickup", '"Picked up: KAR98 sniper rifle"'),
    FA("maps/m2l1.scr", 'iprintln "Document taken."', 1, "doc", '"Document taken"', 4),

    # ================================================================ maps: vanilla tutorial hints -> once per profile
    HA("maps/m1l1.scr", 'iprintlnbold_noloc (loc_convert_string "Press the USE key  ( ") (loc_convert_string local.key) (loc_convert_string " ) to grab items off tables.")', "use_items",
       '( (loc_convert_string "Press the USE key ( ") + (loc_convert_string local.key) + (loc_convert_string " ) to grab items off tables.") )'),
    HA("maps/m1l1.scr", 'iprintlnbold_noloc (loc_convert_string "Press the USE key to grab items off tables.")', "use_items", '(loc_convert_string "Press the USE key to grab items off tables.")'),
    HA("maps/m1l1.scr", 'iprintlnbold_noloc (loc_convert_string "Press the USE key  ( ") (loc_convert_string local.key) (loc_convert_string " ) to use mounted weapons.")', "use_mg",
       '( (loc_convert_string "Press the USE key ( ") + (loc_convert_string local.key) + (loc_convert_string " ) to use mounted weapons.") )'),
    HA("maps/m1l1.scr", 'iprintlnbold_noloc (loc_convert_string "Press the USE key to use mounted weapons.")', "use_mg", '(loc_convert_string "Press the USE key to use mounted weapons.")'),
    HA("maps/m1l1.scr", 'iprintlnbold_noloc (loc_convert_string "Press the FORWARD key  ( ") (loc_convert_string local.key) (loc_convert_string " ) to move out of the truck.")', "fwd_truck",
       '( (loc_convert_string "Press the FORWARD key ( ") + (loc_convert_string local.key) + (loc_convert_string " ) to move out of the truck.") )'),
    HA("maps/m1l1.scr", 'iprintlnbold_noloc (loc_convert_string "Press the FORWARD key to move out of the truck.")', "fwd_truck", '(loc_convert_string "Press the FORWARD key to move out of the truck.")'),
    HA("maps/m1l1.scr", 'iprintlnbold_noloc (loc_convert_string "Press the OBJECTIVE key  ( ") (loc_convert_string local.key) (loc_convert_string " ) to see your objectives.")', "obj_key",
       '( (loc_convert_string "Press the OBJECTIVE key ( ") + (loc_convert_string local.key) + (loc_convert_string " ) to see your objectives.") )'),
    HA("maps/m1l1.scr", 'iprintlnbold_noloc (loc_convert_string "Press the OBJECTIVE key to see your objectives.")', "obj_key", '(loc_convert_string "Press the OBJECTIVE key to see your objectives.")'),
    HA("maps/m1l1.scr", 'iprintlnbold ( "Use your compass to guide you to your next objective." )', "compass", '"Use your compass to guide you to your next objective."'),
    HA("maps/m1l1.scr", 'iprintlnbold "Use your compass to guide you to your next objective."', "compass", '"Use your compass to guide you to your next objective."'),
    HA("maps/m1l2a.scr", 'iprintlnbold "Press USE to open doors. If you cannot open the door, you will be able to hear the handle rattle."', "doors",
       '"Press USE to open doors. A locked door rattles its handle."'),
    HA("maps/m1l2a.scr", 'iprintlnbold "Sometimes an objective may be located directly above or below where the compass appears to indicate."', "compass_z",
       '"An objective can be directly above or below where the compass points."'),
    HA("maps/m1l2a.scr", 'iprintlnbold "TUTORIAL: Paratroopers can be deployed to the"', "para_tut",
       '"Paratroopers can be called in with Signal Smoke, usually carried by High-Ranking Officers: swap grenade types and throw it in the open - try the courtyard."'),
    CUT("maps/m1l2a.scr", 'iprintlnbold "battlefield through Smoke Signals, usually carried"', '"^~^~^ m1l2a paratrooper tutorial (feed: one hint)"'),
    CUT("maps/m1l2a.scr", 'iprintlnbold "by High-Ranking Officers. Deploy by swapping grenade"', '"^~^~^ m1l2a paratrooper tutorial 2"'),
    CUT("maps/m1l2a.scr", 'iprintlnbold "types. Place it in an open area - try the courtyard."', '"^~^~^ m1l2a paratrooper tutorial 3"'),
    HA("maps/m1l2b.scr", 'iprintlnbold_noloc ("See your objectives.")', "obj_key", '"Press the OBJECTIVE key to see your objectives."'),
    HA("maps/m1l2b.scr", 'iprintlnbold "Follow the arrow on your compass to reach your objectives."', "compass", '"Follow the arrow on your compass to reach your objectives."', 2),
    HA("maps/m1l2b.scr", 'iprintlnbold_noloc ("Walk when you want to sneak up on enemies.")', "walk", '"Walk when you want to sneak up on enemies."'),
    HA("maps/m1l2b.scr", 'iprintlnbold_noloc (loc_convert_string "Press ( ") (loc_convert_string local.key) (loc_convert_string " ) to see your objectives.")', "obj_key",
       '( (loc_convert_string "Press ( ") + (loc_convert_string local.key) + (loc_convert_string " ) to see your objectives.") )'),
    HA("maps/m1l2b.scr", 'iprintlnbold_noloc (loc_convert_string "Press ( ") (loc_convert_string local.key) (loc_convert_string " ) to walk. Walk when you want to sneak up on enemies.")', "walk",
       '( (loc_convert_string "Press ( ") + (loc_convert_string local.key) + (loc_convert_string " ) to walk. Walk when you want to sneak up on enemies.") )'),
    HA("maps/m4l2.scr", 'iprintlnbold_noloc (loc_convert_string "Press ( ") (loc_convert_string local.key) (loc_convert_string " ) to walk. Walk when you want to sneak up on enemies.")', "walk",
       '( (loc_convert_string "Press ( ") + (loc_convert_string local.key) + (loc_convert_string " ) to walk. Walk when you want to sneak up on enemies.") )'),
    HA("maps/m4l2.scr", 'iprintlnbold_noloc ("Walk when you want to sneak up on enemies.")', "walk", '"Walk when you want to sneak up on enemies."'),
    HA("maps/m2l1.scr", 'iprintlnbold_noloc (loc_convert_string "Press ") (loc_convert_string local.key) (loc_convert_string " to switch to the sniper rifle.")', "sniper_sw",
       '( (loc_convert_string "Press ") + (loc_convert_string local.key) + (loc_convert_string " to switch to the sniper rifle.") )'),
    HA("maps/m2l1.scr", 'iprintlnbold_noloc (loc_convert_string "Press ") (loc_convert_string local.key) (loc_convert_string " to use the scope on the sniper rifle.")', "scope",
       '( (loc_convert_string "Press ") + (loc_convert_string local.key) + (loc_convert_string " to use the scope on the sniper rifle.") )'),
    HA("maps/m2l1.scr", 'iprintlnbold_noloc ("Press (Secondary Attack) to use the scope on the sniper rifle.")', "scope", '"Press (Secondary Attack) to use the scope on the sniper rifle."'),
    HA("maps/m2l1.scr", 'iprintlnbold "You can only climb one side of a ladder."', "ladder_side",
       '"You can only climb one side of a ladder - approach this one from the west."'),
    CUT("maps/m2l1.scr", 'iprintlnbold "Approach this ladder from the west to climb it."', '"^~^~^ m2l1 ladder hint 2 (feed: one hint)"'),
    HA("maps/m2l1.scr", 'iprintlnbold_noloc (loc_convert_string "Look up and press your forward key ( ") (loc_convert_string local.key) (loc_convert_string " ) to climb a ladder.")', "ladder",
       '( (loc_convert_string "Look up and press your forward key ( ") + (loc_convert_string local.key) + (loc_convert_string " ) to climb a ladder.") )'),
    HA("maps/m2l1.scr", 'iprintlnbold_noloc (loc_convert_string "Look up and press your forward key to climb a ladder.")', "ladder",
       '(loc_convert_string "Look up and press your forward key to climb a ladder.")'),
    HA("maps/m2l2a.scr", 'iprintlnbold_noloc (loc_convert_string "Press the ( ") (loc_convert_string local.key) (loc_convert_string " ) key to holster your weapon.")', "holster",
       '( (loc_convert_string "Press the ( ") + (loc_convert_string local.key) + (loc_convert_string " ) key to holster your weapon.") )'),
    HA("maps/m2l2a.scr", 'iprintlnbold "If your weapon is not holstered"', "holster2", '"If your weapon is not holstered your cover will be blown."'),
    CUT("maps/m2l2a.scr", 'iprintlnbold "your cover will be blown."', '"^~^~^ m2l2a holster hint 2 (feed: one hint)"'),
    HA("maps/m2l2a.scr", 'iprintlnbold_noloc (loc_convert_string "Press the ( ") (loc_convert_string local.key) (loc_convert_string " ) key to show your papers.")', "papers",
       '( (loc_convert_string "Press the ( ") + (loc_convert_string local.key) + (loc_convert_string " ) key to show your papers.") )'),
    HA("maps/m2l2a.scr", 'iprintlnbold_noloc "If you are asked for your papers, press PRIMARY FIRE to show them."', "papers",
       '"If you are asked for your papers, press PRIMARY FIRE to show them."'),
]

# ================================================================ main menu: LAST MISSION button, stacked above WHAT'S NEW
OPS.append((M, "ui/main.urc",
    'resource\nButton\n{\nname "whatsnew"\n',
    '// [user 2026-10-05] LAST MISSION: the last coop debrief (mission, XP, promotion, what was earned) on demand - the\n'
    '// mid-mission rank/XP/unlock chatter moved to the debrief, this keeps it reachable. Same plate as WHAT\'S NEW. 100 wide: ends at x472, clear of the invisible credits hotspot (475 268 104 150).\n'
    'resource\nButton\n{\nname "lastmission"\ntitle "DEBRIEF"\nrect 372 402 100 20\nfgcolor 0.90 0.84 0.66 1.00\n'
    'bgcolor 0.14 0.10 0.06 0.94\nborderstyle "3D_BORDER"\nfont "facfont-20"\nclicksound "sound/menu/apply.wav"\n'
    'stuffcommand "pushmenu coop_lastmission"\n}\n\n'
    'resource\nButton\n{\nname "whatsnew"\n', 1))

# ================================================================ the two "onto your position" alerts: urgent but short-lived
# (coordinator 2026-10-05: kept bold they lingered ~45 s in the old box). Amber feed alert = 6 s, shown in Hardcore too.
OPS.append(FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer has called in a Stuka dive bomber onto your position."', 0, "w_stuka",
              '"Stuka dive bomber inbound on your position - take cover"'))
OPS.append(FA("coop_mod/officer.scr", 'iprintlnbold "Recon reports the Officer has called in an Artillery barrage onto your position."', 0, "w_arty",
              '"Artillery barrage inbound on your position - take cover"'))
