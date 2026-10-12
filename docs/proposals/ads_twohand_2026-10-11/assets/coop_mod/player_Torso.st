//[200] Smithy - default file changed to call weaponstate.scr during various anim events
//               search for 'Smithy' to see changes

	// ======================================================= //
	// Action state machine for Mike Powell, the hero of MoH PC //
	// ======================================================= //

// Authored by Carl glave and Michael Boon, 5-23-2000

// The action state machine takes care of
// a) all torso-only animations which are layer on top of leg animations
// b) most full-body animations
// c) which states are to take their full-body animations from the leg state
//    machine.
// The states which control only torso animations have "movetype legs" and 
// animations under the token "action".  This allows the leg state to continue
// controlling the leg animations.  The states which control the whole body have
// movetype not legs and animations under the token "action". This overrides the
// leg state machine. States such as STAND, below, which have "none" specified
// as the torso animation, take the torso animation from the leg animaiton
// specified in the legs state machine.

//==============================================================================
//==============================================================================
//
// Stand (really means not doing an action)
//
//==============================================================================

state STAND
{
	movetype legs

	camera behind

	entrycommands
	{
		viewmodelanim idle
	}
	
	action
	{
		none				: default // no torso animation
	}

	states
	{
		KILLED				: KILLED

		VEHICLE_START			: IS_USING_VEHICLE
		TURRET_START			: IS_USING_TURRET

		// if we're on a ladder, make sure we're climbing the ladder
		LADDER_IDLE_LEFT			: ON_LADDER
	
		// Using objects is dictated by the object being used.  The three objects 
		// here are for objects which trigger interactive actions when touched, 
		// for objects which the player uses (such as doors), and for when the 
		// player tries to use an object that is not usable.
		USE_LADDER				: ONGROUND +USE AT_LADDER CHECK_HEIGHT "stand"
		// latch onto ladder in mid-air
		USE_LADDER				: +USE AT_LADDER CHECK_HEIGHT "stand" // can also latch onto a ladder in mid-air
		// auto use of ladder when at the bottom (AT_LADDER check is last because it does a trace)
		USE_LADDER				: ONGROUND FORWARD LOOKING_UP "35" !PUTAWAYMAIN !NEW_WEAPON !RELOAD !ATTACK_PRIMARY !ATTACK_SECONDARY AT_LADDER CHECK_HEIGHT "stand"
		// auto use of ladder when at the top (AT_LADDER check is last because it does a trace)
		USE_LADDER				: ONGROUND FORWARD !LOOKING_UP "-35" !PUTAWAYMAIN !NEW_WEAPON !RELOAD !ATTACK_PRIMARY !ATTACK_SECONDARY AT_LADDER CHECK_HEIGHT "stand"

		// This is not functional for the prototype, but is here as a placeholder for
		// future functionality.
		// While the player can only fire weapons with his right hand, he can switch them 
		// to his left if he wants to use an item with his left.  Gameplay-wise, this should 
		// be the same as putting the weapon away, but it will create a nice graphical "cool 
		// factor" which is always good in computer games.
		// When we have two items out, the game code will flag them both as putaway, and we 
		// need to put the right one away first, followed by the left.
		PUTAWAY_MAIN			: PUTAWAYMAIN	// Basic put weapon away move.
		RAISE_WEAPON			: NEW_WEAPON

		STAND_MINEDETECTOR	       	: IS_WEAPON_ACTIVE "mainhand" "Minedetector"
		STAND_MINEDETECTOR	       	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat"

		RELOAD_WEAPON			: RELOAD

		// HZM coop - TAKE COVER [214]: while the engine says a cover pose is live, park the
		// torso in COVER_TORSO (action none) so the full-body legs cover/blind-fire anims own
		// every bone and the hip ATTACK dispatch below can't fight them. Must sit ABOVE the
		// attack edges; weapon switch/reload still work from inside COVER_TORSO.
		// [user 2026-08-28] BRACING BEATS COVER. These two rows sit above the AIM row, and first match
		// wins - so crouched at a wall, auto-cover-low took the torso before COOP_ADS was ever evaluated and
		// a mounted player never reached the sights. Standing was fine only because low cover was not firing.
		// The mount already clears the cover flags, but only on the frame it is taken; auto-cover re-requests
		// on the next one, so the flag clear alone cannot hold. This is the user's rule from 2026-08-27 -
		// mounting overrides cover rather than competing with it - expressed where the contest is decided.
		COVER_TORSO			: COOP_COVER !COOP_BRACED
		COVER_TORSO			: COOP_COVER_LOW !COOP_BRACED

		CHECK_MORTARRIFLE       	: +ATTACK_PRIMARY IS_WEAPON_ACTIVE "mainhand" "Gewehrgranate"
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_SEMIAUTO "mainhand" IS_WEAPON_READY_TO_FIRE "mainhand"
		CHECK_PRIMARY_ATTACK_FULLAUTO	: ATTACK_PRIMARY !IS_WEAPON_SEMIAUTO "mainhand" IS_WEAPON_READY_TO_FIRE "mainhand"

		// HZM coop - AIM DOWN SIGHTS: hold the dedicated ADS button (RMB by default, its own bind) to
		// raise the weapon to the iron sights. Decoupled from secondary-fire so the native bash works
		// again on +attacksecondary (V). Guarded so grenades, rocket launchers, the mine detector and
		// items keep their normal secondary action; they never had an iron-sight pose anyway.
		AIM				: COOP_ADS !IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "grenade" !IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "item" !IS_WEAPON_ACTIVE "mainhand" "Bazooka" !IS_WEAPON_ACTIVE "mainhand" "Panzerschreck" !IS_WEAPON_ACTIVE "mainhand" "PIAT" !IS_WEAPON_ACTIVE "mainhand" "Minedetector" !IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat" !IS_WEAPON_ACTIVE "mainhand" "Springfield '03 Sniper" !IS_WEAPON_ACTIVE "mainhand" "KAR98 - Sniper" !IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1"

		CHECK_SECONDARY_ATTACK		: +ATTACK_SECONDARY

		// check for needing to restart the STAND state so that we can select a different 
		// viewmodel anim (part of the viewmodel idle anim setting code)
		STAND	: +CHECK_MOVEMENT_SPEED "mainhand"
		STAND	: -CHECK_MOVEMENT_SPEED "mainhand"
	}
}

//==============================================================================
//
// AIM DOWN SIGHTS  (HZM coop iron-sight raise)
//
// Entered from STAND while the secondary-fire button (RMB) is HELD. Raises the
// weapon to the sights with the per-weapon "adsraise" viewmodel pose defined in
// models/player/base/fps_anims_*.txt (a graceful no-op for weapons without one).
// Firing routes through the normal primary-attack dispatch (brief hip dip, then
// STAND re-enters AIM while RMB stays held); releasing RMB returns to STAND.
// PURELY ADDITIVE: references only pre-existing states + the new adsraise alias.
//
//==============================================================================
state AIM
{
	movetype legs

	camera behind

	entrycommands
	{
		// Raise the gun to the iron sights via the per-weapon "charge" aim pose (defined as <gun>_charge
		// in models/player/base/fps_anims_*.txt). This is the RAISED pose the per-gun s_adsGunTune values
		// were dialled against - kept so all that tuning stays valid. (Trade-off: these raise poses bake a
		// fixed support-hand position for their original gun, so on borrowed/HD-remodelled guns the off
		// hand can hover - that is only fully fixable with authored per-gun poses, not a tuning change.)
		viewmodelanim charge
	}

	// HZM coop [227] - the gun stays RAISED AND LEVEL the entire time the shoulder aim is held:
	// standing, strafing, forward, back - the TRUE shouldered aim holds (coop_aim_* aliases, the
	// AI aiming anims) on the upper body, never a carry. The [223] stand_idle rows were the
	// muzzle-up patrol carry - "gun should stay raised... not relaxed at any point" (user).
	// Torso slot masks to upper bones; the legs keep their run/strafe anims underneath.
	action
	{
		// [user 2026-09-25] MOUNTED = THE RMB AIM POSE: "when you use brace/mount in third person, it should be just like
		// aiming over shoulder and holding right mouse down (rifle aimed, arm steady)". The mount forces COOP_ADS, so the
		// per-weapon rows below serve it exactly as they serve RMB; the 08-27 braced-only poses (aim-over-cover /
		// brace_stand) were removed. Prone keeps its prone pose; cover rows are unchanged.

		// HZM coop [user 2026-08-24] PRONE. These action blocks ALREADY select by stance via
		// POSITION_TYPE "crouching"/"standing", and the prone legs state calls moveposflags "prone",
		// so POSITION_TYPE "prone" is true for free. Listed FIRST because the first match wins - the
		// per-gun standing poses below would otherwise put an upright torso on a flat body.
		coop_supine_aim			: COOP_SUPINE
		coop_prone_aim_pistol	: POSITION_TYPE "prone" IS_WEAPONCLASS_ACTIVE "mainhand" "pistol"
		coop_prone_aim			: POSITION_TYPE "prone"

		coop_aim_smg			: IS_WEAPON_ACTIVE "mainhand" "MP40"
		coop_aim_mg			: IS_WEAPON_ACTIVE "mainhand" "StG 44"
		coop_aim_rifle			: IS_WEAPON_ACTIVE "mainhand" "Shotgun"
		coop_aim_pistol			: IS_WEAPONCLASS_ACTIVE "mainhand" "pistol"
		coop_aim_rifle			: IS_WEAPONCLASS_ACTIVE "mainhand" "rifle"
		coop_aim_smg			: IS_WEAPONCLASS_ACTIVE "mainhand" "smg"
		coop_aim_mg			: IS_WEAPONCLASS_ACTIVE "mainhand" "mg"
		none				: default
	}

	states
	{
		KILLED				: KILLED

		VEHICLE_START			: IS_USING_VEHICLE
		TURRET_START			: IS_USING_TURRET
		LADDER_IDLE_LEFT		: ON_LADDER

		// release the ADS button -> drop out of the sights
		STAND				: !COOP_ADS

		PUTAWAY_MAIN			: PUTAWAYMAIN
		RAISE_WEAPON			: NEW_WEAPON
		RELOAD_WEAPON			: RELOAD

		// SEMI-AUTO (rifle/pistol/shotgun): fire while staying centered at the sights (aim-fire states).
		ATTACK_RIFLE_PRIMARY_AIM	: +ATTACK_PRIMARY IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "rifle"
		ATTACK_PISTOL_PRIMARY_AIM	: +ATTACK_PRIMARY IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "pistol"
		ATTACK_SHOTGUN_PRIMARY_AIM	: +ATTACK_PRIMARY IS_WEAPON_ACTIVE "mainhand" "Shotgun"
		// FULL-AUTO (smg/mg): normal hip dispatch - continuous fire needs the hip "fire" restart that a
		// static aim pose can't retrigger, so full-auto fires reliably here (slight kick during a spray).
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_SEMIAUTO "mainhand" IS_WEAPON_READY_TO_FIRE "mainhand"
		CHECK_PRIMARY_ATTACK_FULLAUTO	: ATTACK_PRIMARY !IS_WEAPON_SEMIAUTO "mainhand" IS_WEAPON_READY_TO_FIRE "mainhand"
		// HZM coop [234] - LOOP the upper-body aim hold: re-pitch AIM every time the torso aim
		// anim finishes, so the raised gun is held CONSTANTLY while ADS is down. Without this the
		// hold played ONCE and then the legs' full-body run/strafe anim bled back onto the arms
		// mid-move ("raised gun torso should be the constant state regardless of walking f/b/l/r"
		// - user). Sits below the attack rows so firing still dispatches; COOP_ADS guard = only
		// while aiming. Same re-pitch pattern as the vanilla rechamber->AIM return.
		AIM				: ANIMDONE_TORSO COOP_ADS
		// re-assert the raised pose on movement-speed change (start/stop/turn) too, covering the
		// single frame between an anim finishing and the next ANIMDONE re-pitch.
		AIM				: +CHECK_MOVEMENT_SPEED "mainhand"
		AIM				: -CHECK_MOVEMENT_SPEED "mainhand"
	}
}

//==============================================================================
//
// TAKE COVER torso (HZM coop [214])
//
// Parked here while a cover pose is live (COOP_COVER / COOP_COVER_LOW from
// Player::TickCoopCover). action "none" hands the WHOLE body to the legs
// machine (COVER_WALL / COVER_LOW / COVER_*_FIRE full-body anims - the same
// recipe as the emotes/DBNO states). No attack edges on purpose: blind-fire
// rounds come from the "N fire" frame commands baked on the legs blind-fire
// aliases, so the hip/ADS fire states must never run while covered. Reload and
// weapon switching stay available (they return to STAND, which re-enters here
// while the pose holds).
//
//==============================================================================
state COVER_TORSO
{
	movetype legs

	camera behind

	entrycommands
	{
		viewmodelanim idle
	}

	action
	{
		none				: default // no torso anim; the legs cover anims drive the body
	}

	states
	{
		KILLED				: KILLED

		VEHICLE_START			: IS_USING_VEHICLE
		TURRET_START			: IS_USING_TURRET
		LADDER_IDLE_LEFT		: ON_LADDER

		// both poses gone (released, moved, or geometry lost) -> back to normal
		COVER_PEEK_TORSO	: COOP_COVER_PEEK
		STAND				: !COOP_COVER !COOP_COVER_LOW

		PUTAWAY_MAIN			: PUTAWAYMAIN
		RAISE_WEAPON			: NEW_WEAPON
		RELOAD_WEAPON			: RELOAD
	}
}

//==============================================================================
// TAKE COVER peek torso (HZM coop [217]) - RMB pop-out aiming WITHOUT routing
// through the vanilla AIM state: AIM's own exits bounced AIM->STAND->COVER_TORSO
// ->AIM in one frame = engine infinite-loop guard = server kill (bug-313). This
// state is cover-owned: it only tucks back into COVER_TORSO or leaves to STAND
// when the pose ends. Firing uses the same dispatch rows as AIM.
//==============================================================================
state COVER_PEEK_TORSO
{
	movetype legs

	camera behind

	entrycommands
	{
		viewmodelanim idle
	}

	// HZM coop [224] - while peeked, hold a TRUE shouldered AIM on the upper body: the AI aiming
	// anims (coop_aim_* aliases, anims_shared.txt) keep the barrel LEVEL at the view. The [223]
	// stand_idle rows were a muzzle-up patrol CARRY - "gun always aims up instead of straight"
	// (user, shot0019). Shotgun shares the rifle aim (both shouldered long guns), BAR/StG the
	// mp44 aim.
	action
	{
		coop_aim_smg			: IS_WEAPON_ACTIVE "mainhand" "MP40"
		coop_aim_mg			: IS_WEAPON_ACTIVE "mainhand" "StG 44"
		coop_aim_rifle			: IS_WEAPON_ACTIVE "mainhand" "Shotgun"
		coop_aim_pistol			: IS_WEAPONCLASS_ACTIVE "mainhand" "pistol"
		coop_aim_rifle			: IS_WEAPONCLASS_ACTIVE "mainhand" "rifle"
		coop_aim_smg			: IS_WEAPONCLASS_ACTIVE "mainhand" "smg"
		coop_aim_mg			: IS_WEAPONCLASS_ACTIVE "mainhand" "mg"
		none				: default
	}

	states
	{
		KILLED				: KILLED

		// tuck back in when the peek ends but the pose still holds
		COVER_TORSO			: !COOP_COVER_PEEK COOP_COVER
		COVER_TORSO			: !COOP_COVER_PEEK COOP_COVER_LOW
		// pose dropped entirely
		STAND				: !COOP_COVER !COOP_COVER_LOW

		RELOAD_WEAPON			: RELOAD
		// aimed firing while peeked (same dispatch as the AIM state)
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_SEMIAUTO "mainhand" IS_WEAPON_READY_TO_FIRE "mainhand"
		CHECK_PRIMARY_ATTACK_FULLAUTO	: ATTACK_PRIMARY !IS_WEAPON_SEMIAUTO "mainhand" IS_WEAPON_READY_TO_FIRE "mainhand"
	}
}

//==============================================================================
// AIM-FIRE states (HZM coop) - fire while staying at the iron sights.
// Each is a clone of the matching hip-fire ATTACK state (same 3rd-person action anims, same
// weaponstate.scr call so firing/disguise behave identically) EXCEPT the first-person view stays in
// the "charge" aim pose instead of the hip-fire kick. On anim-done they return to AIM while RMB is
// held (which re-dispatches the next shot for full-auto) or to STAND when RMB is released.
//==============================================================================
state ATTACK_SMG_PRIMARY_AIM
{
	movetype legs

	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_SMG_PRIMARY"
		viewmodelanim charge
	}

	action
	{
		// HZM coop [user 2026-08-24] PRONE. These action blocks ALREADY select by stance via
		// POSITION_TYPE "crouching"/"standing", and the prone legs state calls moveposflags "prone",
		// so POSITION_TYPE "prone" is true for free. Listed FIRST because the first match wins - the
		// per-gun standing poses below would otherwise put an upright torso on a flat body.
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot_smg		: POSITION_TYPE "prone"

		mp40_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "MP40" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		mp40_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "MP40" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		mp40_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "MP40" POSITION_TYPE "crouching"
		mp40_stand_fire			: IS_WEAPON_ACTIVE "mainhand" "MP40"

		sten_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		sten_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		sten_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II" POSITION_TYPE "crouching"
		sten_stand_fire			: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II"

		moschetto_stand_run_fire	: IS_WEAPON_ACTIVE "mainhand" "Moschetto" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		moschetto_crouch_run_fire	: IS_WEAPON_ACTIVE "mainhand" "Moschetto" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		moschetto_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Moschetto" POSITION_TYPE "crouching"
		moschetto_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Moschetto"

		smg_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		smg_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		smg_crouch_fire			: POSITION_TYPE "crouching"
		smg_stand_fire			: default
	}

	states
	{
		STAND				: KILLED
		// FULL-AUTO loop on WEAPON-READY (the charge aim pose has no usable anim-done). The FULLAUTO
		// dispatch routes back here while RMB is held, so the gun keeps firing at the sights (centered).
		CHECK_PRIMARY_ATTACK_FULLAUTO	: ATTACK_PRIMARY +IS_WEAPON_READY_TO_FIRE "mainhand"
		CHECK_PRIMARY_ATTACK_FULLAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
		AIM				: !ATTACK_PRIMARY COOP_ADS
		STAND				: !ATTACK_PRIMARY
	}
}

state ATTACK_MG_PRIMARY_AIM
{
	movetype legs

	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_MG_PRIMARY"
		viewmodelanim charge
	}

	action
	{
		// HZM coop [user 2026-08-24] PRONE. These action blocks ALREADY select by stance via
		// POSITION_TYPE "crouching"/"standing", and the prone legs state calls moveposflags "prone",
		// so POSITION_TYPE "prone" is true for free. Listed FIRST because the first match wins - the
		// per-gun standing poses below would otherwise put an upright torso on a flat body.
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot_mg		: POSITION_TYPE "prone"

		vickers_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		vickers_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		vickers_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier" POSITION_TYPE "crouching"
		vickers_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier"

		mp44_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "StG 44" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		mp44_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "StG 44" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		mp44_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "StG 44" POSITION_TYPE "crouching"
		mp44_stand_fire			: IS_WEAPON_ACTIVE "mainhand" "StG 44"

		mg_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		mg_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		mg_crouch_fire			: POSITION_TYPE "crouching"
		mg_stand_fire			: default
	}

	states
	{
		STAND				: KILLED
		// FULL-AUTO loop on WEAPON-READY (see ATTACK_SMG_PRIMARY_AIM) so the BAR/StG keeps firing centered.
		CHECK_PRIMARY_ATTACK_FULLAUTO	: ATTACK_PRIMARY +IS_WEAPON_READY_TO_FIRE "mainhand"
		CHECK_PRIMARY_ATTACK_FULLAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
		AIM				: !ATTACK_PRIMARY COOP_ADS
		STAND				: !ATTACK_PRIMARY
	}
}

state ATTACK_RIFLE_PRIMARY_AIM
{
	movetype legs

	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_RIFLE_PRIMARY"
		viewmodelanim charge
	}

	action
	{
		// HZM coop [user 2026-08-24] PRONE. These action blocks ALREADY select by stance via
		// POSITION_TYPE "crouching"/"standing", and the prone legs state calls moveposflags "prone",
		// so POSITION_TYPE "prone" is true for free. Listed FIRST because the first match wins - the
		// per-gun standing poses below would otherwise put an upright torso on a flat body.
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot			: POSITION_TYPE "prone"

		enfieldl42a1_stand_run_fire	: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		enfieldl42a1_crouch_run_fire	: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		enfieldl42a1_crouch_fire	: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1" POSITION_TYPE "crouching"
		enfieldl42a1_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1"

		carcano_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Carcano" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		carcano_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Carcano" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		carcano_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Carcano" POSITION_TYPE "crouching"
		carcano_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Carcano"

		delisle_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "DeLisle" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		delisle_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "DeLisle" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		delisle_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "DeLisle" POSITION_TYPE "crouching"
		delisle_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "DeLisle"

		rifle_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		rifle_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		rifle_stand_walk_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "walking"
		rifle_crouch_fire		: POSITION_TYPE "crouching"
		rifle_stand_fire		: default
	}

	states
	{
		STAND				: KILLED

		ATTACK_SPRINGFIELD_RECHAMBER	: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Springfield '03 Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Gewehrgranate"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Mauser KAR 98K"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "KAR98 - Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Mosin Nagant Rifle"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Lee-Enfield"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "DeLisle"
		//[user 07-12] imported bolt guns: route into the bolt-cycle state after each shot. Their tiks
		//all carry the 'rechamber' viewmodel anim - without these rows they fired but never bolted.
		ATTACK_SPRINGFIELD_RECHAMBER	: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Springfield M1903"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Arisaka Type 99"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Arisaka Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Carcano Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Mosin-Nagant Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Silenced Mosin Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Silenced Kar98 Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Lee-Enfield Sniper"

		AIM				: ANIMDONE_TORSO COOP_ADS
		STAND				: ANIMDONE_TORSO
	}
}

state ATTACK_PISTOL_PRIMARY_AIM
{
	movetype legs

	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_PISTOL_PRIMARY"
		viewmodelanim charge
	}

	action
	{
		// HZM coop [user 2026-08-24] PRONE. These action blocks ALREADY select by stance via
		// POSITION_TYPE "crouching"/"standing", and the prone legs state calls moveposflags "prone",
		// so POSITION_TYPE "prone" is true for free. Listed FIRST because the first match wins - the
		// per-gun standing poses below would otherwise put an upright torso on a flat body.
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot_pistol	: POSITION_TYPE "prone"

		beretta_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Beretta" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		beretta_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Beretta" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		beretta_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Beretta" POSITION_TYPE "crouching"
		beretta_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Beretta"

		pistol_silenced_stand_run_fire	: POSITION_TYPE "standing" MOVEMENT_TYPE "running" IS_WEAPON_ACTIVE "mainhand" "Hi-Standard Silenced"
		pistol_silenced_crouch_run_fire	: POSITION_TYPE "crouching" MOVEMENT_TYPE "running" IS_WEAPON_ACTIVE "mainhand" "Hi-Standard Silenced"
		pistol_silenced_crouch_fire	: POSITION_TYPE "crouching" IS_WEAPON_ACTIVE "mainhand" "Hi-Standard Silenced"
		pistol_silenced_stand_fire	: IS_WEAPON_ACTIVE "mainhand" "Hi-Standard Silenced"

		pistol_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		pistol_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		pistol_crouch_fire		: POSITION_TYPE "crouching"
		pistol_stand_fire		: default
	}

	states
	{
		STAND				: KILLED
		// HZM coop - FAST semi-auto re-fire while aiming: re-enter the aim-fire state directly on the next
		// click as soon as the weapon is ready, instead of waiting for the full fire anim (ANIMDONE) to
		// drop back to AIM first. That ANIMDONE wait was capping the ADS rate below hip; this mirrors the
		// hip ATTACK_PISTOL_PRIMARY state's re-fire, so ADS fires exactly as fast as the hip (still gated by
		// IS_WEAPON_READY_TO_FIRE = the weapon's natural fire delay).
		ATTACK_PISTOL_PRIMARY_AIM	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand" COOP_ADS
		AIM				: ANIMDONE_TORSO COOP_ADS
		STAND				: ANIMDONE_TORSO
	}
}

state ATTACK_SHOTGUN_PRIMARY_AIM
{
	movetype legs

	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_SHOTGUN_PRIMARY"
		viewmodelanim charge
	}

	action
	{
		// HZM coop [user 2026-08-24] PRONE. These action blocks ALREADY select by stance via
		// POSITION_TYPE "crouching"/"standing", and the prone legs state calls moveposflags "prone",
		// so POSITION_TYPE "prone" is true for free. Listed FIRST because the first match wins - the
		// per-gun standing poses below would otherwise put an upright torso on a flat body.
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot			: POSITION_TYPE "prone"

		shotgun_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		shotgun_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		shotgun_crouch_fire		: POSITION_TYPE "crouching"
		shotgun_stand_fire		: default
	}

	states
	{
		STAND				: KILLED
		AIM				: ANIMDONE_TORSO COOP_ADS
		STAND				: ANIMDONE_TORSO
	}
}

state STAND_MINEDETECTOR
{
	movetype legs

	entrycommands
	{
		viewmodelanim idle0
	}
	
	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_supine_aim		: COOP_SUPINE
		coop_prone_aim			: POSITION_TYPE "prone"

		minedetector_stand_idle0	: default
		minedetectoraxis_stand_idle0	: default
	}

	states
	{
		// auto use of ladder when at the bottom (AT_LADDER check is last because it does a trace)
		USE_LADDER				: ONGROUND FORWARD LOOKING_UP "35" !PUTAWAYMAIN !NEW_WEAPON !RELOAD !ATTACK_PRIMARY !ATTACK_SECONDARY AT_LADDER CHECK_HEIGHT "stand"
		// auto use of ladder when at the top (AT_LADDER check is last because it does a trace)
		USE_LADDER				: ONGROUND FORWARD !LOOKING_UP "-35" !PUTAWAYMAIN !NEW_WEAPON !RELOAD !ATTACK_PRIMARY !ATTACK_SECONDARY AT_LADDER CHECK_HEIGHT "stand"

		KILLED				: KILLED

		PUTAWAY_MAIN			: PUTAWAYMAIN	// Basic put weapon away move.
		RAISE_WEAPON			: NEW_WEAPON
	
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
		CHECK_SECONDARY_ATTACK		: +ATTACK_SECONDARY ABLE_TO_DEFUSE

		STAND_MINEDETECTOR_ON		: ON_LANDMINE
		STAND_MINEDETECTOR_NEAR		: NEAR_LANDMINE
	}
}

state STAND_MINEDETECTOR_NEAR
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim idle1
	}
	
// 	exitcommands
// 	{
// 		viewmodelanim idle0
// 	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_supine_aim		: COOP_SUPINE
		coop_prone_aim			: POSITION_TYPE "prone"

		minedetector_stand_idle1	: default
		minedetectoraxis_stand_idle1	: default
	}

	states
	{
		// auto use of ladder when at the bottom (AT_LADDER check is last because it does a trace)
		USE_LADDER				: ONGROUND FORWARD LOOKING_UP "35" !PUTAWAYMAIN !NEW_WEAPON !RELOAD !ATTACK_PRIMARY !ATTACK_SECONDARY AT_LADDER CHECK_HEIGHT "stand"
		// auto use of ladder when at the top (AT_LADDER check is last because it does a trace)
		USE_LADDER				: ONGROUND FORWARD !LOOKING_UP "-35" !PUTAWAYMAIN !NEW_WEAPON !RELOAD !ATTACK_PRIMARY !ATTACK_SECONDARY AT_LADDER CHECK_HEIGHT "stand"

		KILLED				: KILLED

		PUTAWAY_MAIN			: PUTAWAYMAIN	// Basic put weapon away move.
		RAISE_WEAPON			: NEW_WEAPON
	
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
		CHECK_SECONDARY_ATTACK		: +ATTACK_SECONDARY ABLE_TO_DEFUSE

		STAND_MINEDETECTOR_ON		: ON_LANDMINE
		STAND_MINEDETECTOR		: !NEAR_LANDMINE
	}
}

state STAND_MINEDETECTOR_ON
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim idle2
	}
	
// 	exitcommands
// 	{
// 		viewmodelanim idle0
// 	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_supine_aim		: COOP_SUPINE
		coop_prone_aim			: POSITION_TYPE "prone"

		minedetector_stand_idle2	: default
		minedetectoraxis_stand_idle2	: default
	}

	states
	{
		// auto use of ladder when at the bottom (AT_LADDER check is last because it does a trace)
		USE_LADDER				: ONGROUND FORWARD LOOKING_UP "35" !PUTAWAYMAIN !NEW_WEAPON !RELOAD !ATTACK_PRIMARY !ATTACK_SECONDARY AT_LADDER CHECK_HEIGHT "stand"
		// auto use of ladder when at the top (AT_LADDER check is last because it does a trace)
		USE_LADDER				: ONGROUND FORWARD !LOOKING_UP "-35" !PUTAWAYMAIN !NEW_WEAPON !RELOAD !ATTACK_PRIMARY !ATTACK_SECONDARY AT_LADDER CHECK_HEIGHT "stand"

		KILLED				: KILLED

		PUTAWAY_MAIN			: PUTAWAYMAIN	// Basic put weapon away move.
		RAISE_WEAPON			: NEW_WEAPON
	
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
		CHECK_SECONDARY_ATTACK		: +ATTACK_SECONDARY ABLE_TO_DEFUSE

		STAND_MINEDETECTOR_NEAR		: NEAR_LANDMINE !ON_LANDMINE
		STAND_MINEDETECTOR		: !ON_LANDMINE
	}
}

//==============================================================================
//==============================================================================
//
// Primary Attacks - Full Auto
//
//==============================================================================

state CHECK_PRIMARY_ATTACK_FULLAUTO
{
	movetype legs

	action
	{
		none				: default // stop torso animation
	}

	states
	{
		STAND				: KILLED
	
		STAND				: NEW_WEAPON
		STAND				: RELOAD
		STAND				: !IS_WEAPON_READY_TO_FIRE     "mainhand"
		
		// HZM coop - while aiming (RMB held) keep full-auto fire in the centered aim-fire states.
		ATTACK_SMG_PRIMARY_AIM		: COOP_ADS IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "smg"
		ATTACK_MG_PRIMARY_AIM		: COOP_ADS IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "mg"

		ATTACK_SMG_PRIMARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "smg"
		ATTACK_SMG_PRIMARY		: IS_WEAPON_READY_TO_FIRE      "mainhand" "Moschetto"
		ATTACK_MG_PRIMARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "mg"

		// HZM coop [user 07-12] SAFETY NET: full-auto-flagged guns that are neither smg nor mg class
		// used to DEAD-END here (bounce to STAND = the "only fires in ADS" bug: the imported pistols
		// shipped with 'semiauto' commented out, the StG44 Scoped and the vanilla FG42 are genuine
		// full-auto rifle-class). Route them to their class attack states so they fire from the hip.
		ATTACK_RIFLE_PRIMARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "rifle"
		ATTACK_PISTOL_PRIMARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "pistol"

		STAND				: !ATTACK_PRIMARY
	}
}

state ATTACK_SMG_PRIMARY
{
	movetype legs

	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_SMG_PRIMARY" //[200] Smithy - call weaponstate script
		viewmodelanim fire 1
	}

	action
	{
		// [user 2026-09-25] MOUNTED = THE RMB AIM POSE: "when you use brace/mount in third person, it should be just like
		// aiming over shoulder and holding right mouse down (rifle aimed, arm steady)". The mount forces COOP_ADS, so the
		// per-weapon rows below serve it exactly as they serve RMB; the 08-27 braced-only poses (aim-over-cover /
		// brace_stand) were removed. Prone keeps its prone pose; cover rows are unchanged.

		// [user 2026-08-25] prone. Only the _AIM variants were patched first time round, so hip-fire
		// and rechamber still played standing poses - "my upper torso pops up as though I am crouched".
		// RECHAMBER deliberately uses coop_prone_aim, NOT coop_prone_shoot: the shoot alias carries a
		// `first fire` notetrack and would discharge a round every time you worked the bolt.
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot_smg		: POSITION_TYPE "prone"

		mp40_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "MP40" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		mp40_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "MP40" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		mp40_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "MP40" POSITION_TYPE "crouching"
		mp40_stand_fire			: IS_WEAPON_ACTIVE "mainhand" "MP40"

		sten_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		sten_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		sten_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II" POSITION_TYPE "crouching"
		sten_stand_fire			: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II"

		moschetto_stand_run_fire	: IS_WEAPON_ACTIVE "mainhand" "Moschetto" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		moschetto_crouch_run_fire	: IS_WEAPON_ACTIVE "mainhand" "Moschetto" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		moschetto_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Moschetto" POSITION_TYPE "crouching"
		moschetto_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Moschetto"

		smg_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		smg_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		smg_crouch_fire			: POSITION_TYPE "crouching"
		smg_stand_fire			: default
	}

	states
	{
		STAND					: KILLED

		STAND					: !ATTACK_PRIMARY ANIMDONE_TORSO 
		STAND					: ANIMDONE_TORSO !IS_WEAPON_READY_TO_FIRE "mainhand"
		STAND					: RELOAD !ATTACK_PRIMARY
		
		CHECK_PRIMARY_ATTACK_FULLAUTO	: ATTACK_PRIMARY +IS_WEAPON_READY_TO_FIRE "mainhand"
		CHECK_PRIMARY_ATTACK_FULLAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
	}
}

state ATTACK_MG_PRIMARY
{
	movetype legs

	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_MG_PRIMARY" //[200] Smithy - call weaponstate script
		viewmodelanim fire 1
	}

	action
	{
		// [user 2026-09-25] MOUNTED = THE RMB AIM POSE: "when you use brace/mount in third person, it should be just like
		// aiming over shoulder and holding right mouse down (rifle aimed, arm steady)". The mount forces COOP_ADS, so the
		// per-weapon rows below serve it exactly as they serve RMB; the 08-27 braced-only poses (aim-over-cover /
		// brace_stand) were removed. Prone keeps its prone pose; cover rows are unchanged.

		// [user 2026-08-25] prone. Only the _AIM variants were patched first time round, so hip-fire
		// and rechamber still played standing poses - "my upper torso pops up as though I am crouched".
		// RECHAMBER deliberately uses coop_prone_aim, NOT coop_prone_shoot: the shoot alias carries a
		// `first fire` notetrack and would discharge a round every time you worked the bolt.
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot_mg		: POSITION_TYPE "prone"

	      vickers_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		vickers_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		vickers_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier" POSITION_TYPE "crouching"
		vickers_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier"

		mp44_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "StG 44" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		mp44_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "StG 44" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		mp44_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "StG 44" POSITION_TYPE "crouching"
		mp44_stand_fire			: IS_WEAPON_ACTIVE "mainhand" "StG 44"

		mg_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		mg_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		mg_crouch_fire			: POSITION_TYPE "crouching"
		mg_stand_fire			: default
	}

	states
	{
		STAND				: KILLED
		STAND				: !ATTACK_PRIMARY ANIMDONE_TORSO 
		STAND				: ANIMDONE_TORSO !IS_WEAPON_READY_TO_FIRE "mainhand"
		STAND				: RELOAD !ATTACK_PRIMARY
		
		CHECK_PRIMARY_ATTACK_FULLAUTO	: ATTACK_PRIMARY +IS_WEAPON_READY_TO_FIRE "mainhand"
		CHECK_PRIMARY_ATTACK_FULLAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
	}
}

//==============================================================================
//==============================================================================
//
// Primary Attacks - Semi-Auto
//
//==============================================================================

state CHECK_PRIMARY_ATTACK_SEMIAUTO
{
	movetype legs

	action
	{
		none                    	: default // stop torso animation
	}

	states
	{
		STAND				: KILLED
	
		STAND				: NEW_WEAPON
		STAND				: RELOAD
		STAND				: !IS_WEAPON_READY_TO_FIRE "mainhand"

		ATTACK_PISTOL_PRIMARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "pistol"
		ATTACK_RIFLE_PRIMARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "rifle"
		RELEASE_ATTACK_LANDMINE		: IS_WEAPON_ACTIVE             "mainhand" "Minedetector" CAN_PLACE_LANDMINE
		RELEASE_ATTACK_LANDMINE		: IS_WEAPON_ACTIVE             "mainhand" "Minensuchgerat" CAN_PLACE_LANDMINE
		RELEASE_ATTACK_LANDMINE		: IS_WEAPON_ACTIVE             "mainhand" "LandmineAxis" CAN_PLACE_LANDMINE
		RELEASE_ATTACK_LANDMINE		: IS_WEAPON_ACTIVE             "mainhand" "LandmineAllies" CAN_PLACE_LANDMINE
		STAND				: IS_WEAPON_ACTIVE             "mainhand" "Minedetector"
		STAND				: IS_WEAPON_ACTIVE             "mainhand" "Minensuchgerat"
		STAND				: IS_WEAPON_ACTIVE             "mainhand" "LandmineAxis"
		STAND				: IS_WEAPON_ACTIVE             "mainhand" "LandmineAllies"
		CHARGE_ATTACK_GRENADE		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "grenade"
		ATTACK_ITEM_PRIMARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "item"
		ATTACK_BAZOOKA_PRIMARY		: IS_WEAPON_ACTIVE             "mainhand" "Bazooka"
		ATTACK_BAZOOKA_PRIMARY		: IS_WEAPON_ACTIVE             "mainhand" "PIAT" 
		ATTACK_BAZOOKA_PRIMARY		: IS_WEAPON_ACTIVE             "mainhand" "Panzerschreck"
		ATTACK_SHOTGUN_PRIMARY		: IS_WEAPON_ACTIVE             "mainhand" "Shotgun"

		STAND				: !ATTACK_PRIMARY
	}
}

state ATTACK_RIFLE_PRIMARY
{
	movetype legs

	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_RIFLE_PRIMARY" //[200] Smithy - call weaponstate script
		viewmodelanim fire 1
	}

	action
	{
		// [user 2026-09-25] MOUNTED = THE RMB AIM POSE: "when you use brace/mount in third person, it should be just like
		// aiming over shoulder and holding right mouse down (rifle aimed, arm steady)". The mount forces COOP_ADS, so the
		// per-weapon rows below serve it exactly as they serve RMB; the 08-27 braced-only poses (aim-over-cover /
		// brace_stand) were removed. Prone keeps its prone pose; cover rows are unchanged.

		// [user 2026-08-25] prone. Only the _AIM variants were patched first time round, so hip-fire
		// and rechamber still played standing poses - "my upper torso pops up as though I am crouched".
		// RECHAMBER deliberately uses coop_prone_aim, NOT coop_prone_shoot: the shoot alias carries a
		// `first fire` notetrack and would discharge a round every time you worked the bolt.
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot			: POSITION_TYPE "prone"

		// Fire from the hip when jogging,
		// from the shoulder when walking or standing
	      enfieldl42a1_stand_run_fire	: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		enfieldl42a1_crouch_run_fire	: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		enfieldl42a1_crouch_fire	: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1" POSITION_TYPE "crouching"
		enfieldl42a1_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1"

	      carcano_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Carcano" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		carcano_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Carcano" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		carcano_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Carcano" POSITION_TYPE "crouching"
		carcano_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Carcano"

	      delisle_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "DeLisle" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		delisle_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "DeLisle" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		delisle_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "DeLisle" POSITION_TYPE "crouching"
		delisle_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "DeLisle"

		rifle_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		rifle_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		rifle_stand_walk_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "walking"
		rifle_crouch_fire		: POSITION_TYPE "crouching"
		rifle_stand_fire		: default
	}

	states
	{
		STAND				: KILLED

		ATTACK_SPRINGFIELD_RECHAMBER	: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Springfield '03 Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Gewehrgranate"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Mauser KAR 98K"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "KAR98 - Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Mosin Nagant Rifle"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Lee-Enfield"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "DeLisle"
		//[user 07-12] imported bolt guns: route into the bolt-cycle state after each shot. Their tiks
		//all carry the 'rechamber' viewmodel anim - without these rows they fired but never bolted.
		ATTACK_SPRINGFIELD_RECHAMBER	: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Springfield M1903"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Arisaka Type 99"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Arisaka Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Carcano Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Mosin-Nagant Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Silenced Mosin Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Silenced Kar98 Sniper"
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO IS_WEAPON_ACTIVE "mainhand" "Lee-Enfield Sniper"
		STAND				: ANIMDONE_TORSO 
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
	}
}

state ATTACK_SPRINGFIELD_RECHAMBER
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim rechamber
	}
	
	action
	{
		// [user 2026-08-26, bug-2118] prone substitution REMOVED - the real rechamber anim plays, bent by
		// the spine action tier like shooting. The static coop_prone_aim pose here was the notetrack trap
		// a FOURTH time: the real alias carries `entry weaponcommand mainhand anim "rechamber"`, which is
		// what makes the WEAPON MODEL play its bolt animation - so the substitution froze both the hands
		// AND the gun ("k98 in prone no longer pulls bolt after each shot"). Its `last weaponcommand
		// mainhand idle` also returns the weapon to idle; a pose alias drops that too.

		springfield_crouch_rechamber	: POSITION_TYPE "crouching"
		springfield_stand_rechamber	: default
	}
	
	states
	{
		STAND				: KILLED
	
		STAND				: ANIMDONE_TORSO 
	}
}

state ATTACK_RIFLE_RECHAMBER
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim rechamber
	}
	
	action
	{
		// [user 2026-08-26, bug-2118] prone substitution REMOVED - the real rechamber anim plays, bent by
		// the spine action tier like shooting. The static coop_prone_aim pose here was the notetrack trap
		// a FOURTH time: the real alias carries `entry weaponcommand mainhand anim "rechamber"`, which is
		// what makes the WEAPON MODEL play its bolt animation - so the substitution froze both the hands
		// AND the gun ("k98 in prone no longer pulls bolt after each shot"). Its `last weaponcommand
		// mainhand idle` also returns the weapon to idle; a pose alias drops that too.

		enfield_crouch_rechamber	: POSITION_TYPE "crouching" IS_WEAPON_ACTIVE "mainhand" "Lee-Enfield"
		enfield_stand_rechamber		: IS_WEAPON_ACTIVE "mainhand" "Lee-Enfield"

		delisle_crouch_rechamber	: POSITION_TYPE "crouching" IS_WEAPON_ACTIVE "mainhand" "DeLisle"
		delisle_stand_rechamber		: IS_WEAPON_ACTIVE "mainhand" "DeLisle"

		enfieldl42a1_crouch_rechamber	: POSITION_TYPE "crouching" IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1"
		enfieldl42a1_stand_rechamber	: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1"


		mosin_crouch_rechamber		: POSITION_TYPE "crouching" IS_WEAPON_ACTIVE "mainhand" "Mosin Nagant Rifle"
		mosin_stand_rechamber		: IS_WEAPON_ACTIVE "mainhand" "Mosin Nagant Rifle"

		svt_crouch_rechamber		: POSITION_TYPE "crouching" IS_WEAPON_ACTIVE "mainhand" "SVT 40"
		svt_stand_rechamber		: IS_WEAPON_ACTIVE "mainhand" "SVT 40"

		kar98_crouch_rechamber		: POSITION_TYPE "crouching"
		kar98_stand_rechamber		: default
	}
	
	states
	{
		STAND				: KILLED
	
		STAND				: ANIMDONE_TORSO 
	}
}

state ATTACK_PISTOL_PRIMARY
{
	movetype legs

	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_PISTOL_PRIMARY" //[200] Smithy - call weaponstate script
		viewmodelanim fire 1
	}

	action
	{
		// [user 2026-09-25] MOUNTED = THE RMB AIM POSE: "when you use brace/mount in third person, it should be just like
		// aiming over shoulder and holding right mouse down (rifle aimed, arm steady)". The mount forces COOP_ADS, so the
		// per-weapon rows below serve it exactly as they serve RMB; the 08-27 braced-only poses (aim-over-cover /
		// brace_stand) were removed. Prone keeps its prone pose; cover rows are unchanged.

		// [user 2026-08-25] prone. Only the _AIM variants were patched first time round, so hip-fire
		// and rechamber still played standing poses - "my upper torso pops up as though I am crouched".
		// RECHAMBER deliberately uses coop_prone_aim, NOT coop_prone_shoot: the shoot alias carries a
		// `first fire` notetrack and would discharge a round every time you worked the bolt.
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot_pistol	: POSITION_TYPE "prone"

		// Fire from the hip when jogging, from the shoulder when
		// walking, or standing

	      beretta_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Beretta" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		beretta_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "Beretta" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		beretta_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Beretta" POSITION_TYPE "crouching"
		beretta_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Beretta"

		pistol_silenced_stand_run_fire	: POSITION_TYPE "standing" MOVEMENT_TYPE "running" IS_WEAPON_ACTIVE "mainhand" "Hi-Standard Silenced"
		pistol_silenced_crouch_run_fire	: POSITION_TYPE "crouching" MOVEMENT_TYPE "running" IS_WEAPON_ACTIVE "mainhand" "Hi-Standard Silenced"
		pistol_silenced_crouch_fire	: POSITION_TYPE "crouching" IS_WEAPON_ACTIVE "mainhand" "Hi-Standard Silenced"
		pistol_silenced_stand_fire	: IS_WEAPON_ACTIVE "mainhand" "Hi-Standard Silenced"

		pistol_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		pistol_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		pistol_crouch_fire		: POSITION_TYPE "crouching"
		pistol_stand_fire		: default
	}

	states
	{
		STAND				: KILLED
 
		STAND				: ANIMDONE_TORSO 
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"

		// allow pistol whip immediatly after firing
		ATTACK_PISTOL_SECONDARY		: +ATTACK_SECONDARY IS_WEAPON_READY_TO_FIRE "mainhand"
	}
}

state ATTACK_ITEM_PRIMARY
{
	movetype legs

	entrycommands
	{
		weaponcommand mainhand anim fire
	}
	
	states
	{
		STAND				: KILLED

		STAND				: !ATTACK_PRIMARY
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
	}
}

state ATTACK_BAZOOKA_PRIMARY
{
	movetype legs
	
	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_BAZOOKA_PRIMARY" //[200] Smithy - call weaponstate script
		viewmodelanim fire 1
	}
	
	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot		: POSITION_TYPE "prone"

		piat_stand_run_fire		: IS_WEAPON_ACTIVE "mainhand" "PIAT" POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		piat_crouch_run_fire		: IS_WEAPON_ACTIVE "mainhand" "PIAT" POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		piat_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "PIAT" POSITION_TYPE "crouching"
		piat_stand_fire			: IS_WEAPON_ACTIVE "mainhand" "PIAT"

		bazooka_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		bazooka_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		bazooka_crouch_fire		: POSITION_TYPE "crouching"
		bazooka_stand_fire		: default
	}
	
	states
	{
		STAND				: KILLED

		STAND				: !ATTACK_PRIMARY ANIMDONE_TORSO 
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
	}
}

state ATTACK_SHOTGUN_PRIMARY
{
	movetype legs
	
	entrycommands
	{
		exec coop_mod/weaponstate.scr "ATTACK_SHOTGUN_PRIMARY" //[200] Smithy - call weaponstate script
		viewmodelanim fire 1
	}
	
	action
	{
		// [user 2026-09-25] MOUNTED = THE RMB AIM POSE: "when you use brace/mount in third person, it should be just like
		// aiming over shoulder and holding right mouse down (rifle aimed, arm steady)". The mount forces COOP_ADS, so the
		// per-weapon rows below serve it exactly as they serve RMB; the 08-27 braced-only poses (aim-over-cover /
		// brace_stand) were removed. Prone keeps its prone pose; cover rows are unchanged.

		// [user 2026-08-25] prone. Only the _AIM variants were patched first time round, so hip-fire
		// and rechamber still played standing poses - "my upper torso pops up as though I am crouched".
		// RECHAMBER deliberately uses coop_prone_aim, NOT coop_prone_shoot: the shoot alias carries a
		// `first fire` notetrack and would discharge a round every time you worked the bolt.
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot			: POSITION_TYPE "prone"

		shotgun_stand_run_fire	     	: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		shotgun_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		shotgun_crouch_fire	     	: POSITION_TYPE "crouching"
		shotgun_stand_fire	     	: default
	}
	
	states
	{
		STAND				: KILLED

		STAND				: !ATTACK_PRIMARY ANIMDONE_TORSO 
		CHECK_PRIMARY_ATTACK_SEMIAUTO	: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
	}
}

//==============================================================================
//==============================================================================
//
// Secondary Attacks (Always Semi-Auto fire)
//
//==============================================================================
state CHECK_SECONDARY_ATTACK
{
	movetype legs

	action
	{
		none : default // no torso animation
	}

	states
	{
		STAND					: KILLED

		CHARGE_ATTACK_LANDMINE_SECONDARY	: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "grenade" "secondary" IS_WEAPON_ACTIVE "mainhand" "Minedetector"
		CHARGE_ATTACK_LANDMINE_SECONDARY	: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "grenade" "secondary" IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat"
		CHARGE_ATTACK_LANDMINE_SECONDARY	: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "grenade" "secondary" IS_WEAPON_ACTIVE "mainhand" "LandmineAxis"
		CHARGE_ATTACK_LANDMINE_SECONDARY	: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "grenade" "secondary" IS_WEAPON_ACTIVE "mainhand" "LandmineAllies"

		STAND				: !HAS_AMMO_IN_CLIP "mainhand" "secondary"
		
		ATTACK_PISTOL_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "pistol" "secondary" IS_WEAPON_ACTIVE "mainhand" "Beretta"
		ATTACK_PISTOL_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "pistol" "secondary"

		CHECK_SECONDARY_MORTARRIFLE 	: IS_WEAPON_ACTIVE "mainhand" "Gewehrgranate"		
		ATTACK_RIFLE_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "rifle" "secondary" IS_WEAPON_ACTIVE "mainhand" "M1 Garand"
		ATTACK_RIFLE_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "rifle" "secondary" IS_WEAPON_ACTIVE "mainhand" "Mauser KAR 98K"
		ATTACK_RIFLE_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "rifle" "secondary" IS_WEAPON_ACTIVE "mainhand" "Lee-Enfield"
		ATTACK_RIFLE_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "rifle" "secondary" IS_WEAPON_ACTIVE "mainhand" "Mosin Nagant Rifle"
		ATTACK_RIFLE_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "rifle" "secondary" IS_WEAPON_ACTIVE "mainhand" "Carcano"
		ATTACK_RIFLE_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "rifle" "secondary" IS_WEAPON_ACTIVE "mainhand" "DeLisle"


		ATTACK_SMG_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "smg" "secondary" IS_WEAPON_ACTIVE "mainhand" "Thompson"
		ATTACK_SMG_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "smg" "secondary" IS_WEAPON_ACTIVE "mainhand" "MP40"
		ATTACK_SMG_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "smg" "secondary" IS_WEAPON_ACTIVE "mainhand" "Sten Mark II"
		ATTACK_SMG_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "smg" "secondary" IS_WEAPON_ACTIVE "mainhand" "PPSH SMG"
		ATTACK_SMG_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "smg" "secondary" IS_WEAPON_ACTIVE "mainhand" "Moschetto"              
 
		ATTACK_MG_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "mg" "secondary" IS_WEAPON_ACTIVE "mainhand" "BAR"
		//[reload audit 2026-10-05] the Lewis gun variant was "BAR (M1918 WWI)" (suffix-matched "BAR" above); keep its butt-stroke
		ATTACK_MG_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "mg" "secondary" IS_WEAPON_ACTIVE "mainhand" "Lewis Gun"
		ATTACK_MG_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "mg" "secondary" IS_WEAPON_ACTIVE "mainhand" "StG 44"
		ATTACK_MG_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "mg" "secondary" IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier"

		ATTACK_HEAVY_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "heavy" "secondary" IS_WEAPON_ACTIVE "mainhand" "Shotgun"


        	CHARGE_ATTACK_GRENADE_SECONDARY 	: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "grenade" "secondary" IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano"
        	CHARGE_ATTACK_GRENADE_SECONDARY 	: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "grenade" "secondary" IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda"

	  	CHARGE_ATTACK_GRENADE_SECONDARY 	: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "grenade" "secondary"


		PUT_AWAY_ITEM			: IS_WEAPON_ACTIVE "mainhand" "Spy Camera"
		PUT_AWAY_ITEM			: IS_WEAPON_ACTIVE "mainhand" "Binoculars"
		ATTACK_ITEM_SECONDARY		: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "item" "secondary"

		STAND				: default
	}
}

// Pistol whip for silent kills
state ATTACK_PISTOL_SECONDARY
{
	movetype legs

	entrycommands
	{
		viewmodelanim fire_secondary 1
	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_butt_supine		: COOP_SUPINE
		coop_butt_prone		: POSITION_TYPE "prone"

		beretta_butt  	  		: IS_WEAPON_ACTIVE "mainhand" "Beretta"
		pistol_butt			: default
	}
	
	states
	{
		STAND	 			: KILLED
		STAND 				: ANIMDONE_TORSO
	}
}

state CHECK_MORTARRIFLE
{
	movetype legs

	action
	{
		none : default // stop torso animation
	}

	states
	{
		STAND				: KILLED	
		STAND				: NEW_WEAPON
		STAND				: RELOAD
		ATTACK_KAR98MORTAR_PRIMARY	: IS_WEAPON_READY_TO_FIRE "mainhand" WEAPON_CURRENT_FIRE_ANIM "mainhand" "0"
		ATTACK_KAR98MORTAR_SECONDARY	: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "heavy" "secondary" WEAPON_CURRENT_FIRE_ANIM "mainhand" "1"
		STAND				: !ATTACK_PRIMARY
	}
}

state CHECK_SECONDARY_MORTARRIFLE
{
	movetype legs

	action
	{
		none 					: default // stop torso animation
	}

	states
	{
		STAND				: KILLED	
		STAND				: NEW_WEAPON
		STAND				: RELOAD
		ATTACK_KAR98MORTAR_PREPARE	: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "heavy" "secondary" WEAPON_CURRENT_FIRE_ANIM "mainhand" "0"
		ATTACK_KAR98MORTAR_SECONDARY	: IS_WEAPONCLASS_READY_TO_FIRE "mainhand" "heavy" "secondary" WEAPON_CURRENT_FIRE_ANIM "mainhand" "1"
		STAND				: !ATTACK_PRIMARY
	}
}


state ATTACK_KAR98MORTAR_PRIMARY
{
	movetype legs

	entrycommands
	{
		viewmodelanim fire 1
	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_supine_shoot		: COOP_SUPINE
		coop_prone_shoot		: POSITION_TYPE "prone"

		// Fire from the hip when jogging,
		// from the shoulder when walking or standing
		rifle_stand_run_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		rifle_crouch_run_fire		: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		rifle_stand_walk_fire		: POSITION_TYPE "standing" MOVEMENT_TYPE "walking"
		rifle_crouch_fire		: POSITION_TYPE "crouching"
		rifle_stand_fire		: default
	}

	states
	{
		STAND					: KILLED
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO
	}
}

state ATTACK_KAR98MORTAR_SECONDARY
{
	movetype legs

	entrycommands
	{
		viewmodelanim fire 1
		weaponcommand mainhand surface kar98Gren_proj +nodraw
	}

	exitcommands
	{
		weaponcommand mainhand setcurrentfireanim 0
	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_supine_shoot_sec	: COOP_SUPINE
		coop_prone_shoot_sec	: POSITION_TYPE "prone"

		// Fire from the hip when jogging,
		// from the shoulder when walking or standing
		mortarrifle_stand_run_fire	: POSITION_TYPE "standing" MOVEMENT_TYPE "running"
		mortarrifle_crouch_run_fire	: POSITION_TYPE "crouching" MOVEMENT_TYPE "running"
		mortarrifle_stand_walk_fire	: POSITION_TYPE "standing" MOVEMENT_TYPE "walking"
		mortarrifle_crouch_fire		: POSITION_TYPE "crouching"
		mortarrifle_stand_fire		: default
	}
	
	states
	{
		STAND	 	               	: KILLED
		ATTACK_RIFLE_RECHAMBER		: ANIMDONE_TORSO
	}
}

state ATTACK_KAR98MORTAR_PREPARE
{
	movetype legs

	entrycommands
	{
		viewmodelanim fire_secondary 1
		weaponcommand mainhand setcurrentfireanim 1
		weaponcommand mainhand anim attachgrenade
	}
	exitcommands
	{
		weaponcommand mainhand surface kar98Gren_proj -nodraw
	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_supine_aim		: COOP_SUPINE
		coop_prone_aim			: POSITION_TYPE "prone"

		mortarrifle_attachmortar  		: default
	}
	
	states
	{
		STAND	 				: KILLED
		STAND					: ANIMDONE_TORSO
	}
}



state ATTACK_RIFLE_SECONDARY
{
	movetype legs

	entrycommands
	{
		viewmodelanim fire_secondary 1
	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_butt_supine		: COOP_SUPINE
		coop_butt_prone		: POSITION_TYPE "prone"

		carcano_butt	     		: IS_WEAPON_ACTIVE "mainhand" "Carcano"
		delisle_butt	     		: IS_WEAPON_ACTIVE "mainhand" "DeLisle"
		rifle_butt			: default
	}
	
	states
	{
		STAND	 				: KILLED
		STAND	 				: ANIMDONE_TORSO
	}
}

state ATTACK_SMG_SECONDARY
{
	movetype legs

	entrycommands
	{
		viewmodelanim fire_secondary 1
	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_butt_supine		: COOP_SUPINE
		coop_butt_prone		: POSITION_TYPE "prone"

		mp40_butt	  		: IS_WEAPON_ACTIVE "mainhand" "MP40"
		sten_butt	  		: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II"
		moschetto_butt    		: IS_WEAPON_ACTIVE "mainhand" "Moschetto"
		smg_butt			: default
	}
	
	states
	{
		STAND	 				: KILLED
		
		STAND	 				: ANIMDONE_TORSO
	}
}

state ATTACK_MG_SECONDARY
{
	movetype legs

	entrycommands
	{
		viewmodelanim fire_secondary 1
	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_butt_supine		: COOP_SUPINE
		coop_butt_prone		: POSITION_TYPE "prone"

	      	vickers_butt			: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier"
		mp44_butt			: IS_WEAPON_ACTIVE "mainhand" "StG 44"
		mg_butt				: default
	}
	
	states
	{
		STAND	 				: KILLED
		
		STAND	 				: ANIMDONE_TORSO
	}
}

state ATTACK_HEAVY_SECONDARY
{
	movetype legs

	entrycommands
	{
		viewmodelanim fire_secondary 1
	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_butt_supine		: COOP_SUPINE
		coop_butt_prone		: POSITION_TYPE "prone"

		shotgun_butt	      	: default
	}
	
	states
	{
		STAND		 			: KILLED
		
		STAND	 				: ANIMDONE_TORSO
	}
}

// put away the item and pull out the last active weapon
state PUT_AWAY_ITEM
{
	entrycommands
	{
		commanddelay 0.05 uselast
	}

	states
	{
		STAND		         		: default
	}
}

state ATTACK_ITEM_SECONDARY
{
	movetype legs

	entrycommands
	{
		weaponcommand mainhand anim secondaryfire
	}
	
	states
	{
		STAND					: KILLED

		STAND					: !ATTACK_PRIMARY
		CHECK_PRIMARY_ATTACK_SEMIAUTO		: +ATTACK_PRIMARY IS_WEAPON_READY_TO_FIRE "mainhand"
	}
}

//==============================================================================
//==============================================================================
//
// Primary Charge Up Attacks (landmine)
//
//==============================================================================

state CHARGE_ATTACK_LANDMINE
{
	movetype anim

	entrycommands
	{
		viewmodelanim charge
	}
	
	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_mine_supine_charge	: COOP_SUPINE
		coop_mine_prone_charge	: POSITION_TYPE "prone"

		minedetector_crouch_charge	: IS_WEAPON_ACTIVE "mainhand" "Minedetector" POSITION_TYPE "crouching"
		minedetector_stand_charge	: IS_WEAPON_ACTIVE "mainhand" "Minedetector"
		minedetectoraxis_crouch_charge	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat" POSITION_TYPE "crouching"
		minedetectoraxis_stand_charge	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat"

		mine_crouch_charge		: POSITION_TYPE "crouching"
		mine_stand_charge		: default
	}

	states
	{
		STAND				: !CAN_PLACE_LANDMINE
		STAND				: MOVEMENT_TYPE "running"
		RELEASE_KILLED_FRAG		: KILLED
		RELEASE_ATTACK_LANDMINE		: !ATTACK_PRIMARY MIN_CHARGE_TIME_MET "mainhand"
	}
}

state RELEASE_ATTACK_LANDMINE
{
	movetype anim

	entrycommands
	{
		viewmodelanim fire
	}
	exitcommands
	{
		correctweaponattachments
	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_mine_supine_fire	: COOP_SUPINE
		coop_mine_prone_fire	: POSITION_TYPE "prone"

		minedetector_crouch_fire	: IS_WEAPON_ACTIVE "mainhand" "Minedetector" POSITION_TYPE "crouching"
		minedetector_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Minedetector"
		minedetectoraxis_crouch_fire	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat" POSITION_TYPE "crouching"
		minedetectoraxis_stand_fire	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat"

		//mine_stand_idle		: MOVEMENT_TYPE "running"
		mine_crouch_fire		: POSITION_TYPE "crouching"
		mine_stand_fire			: default
	}

	states
	{
		//STAND				: !CAN_PLACE_LANDMINE
		RELEASE_KILLED_FRAG		: KILLED MIN_CHARGE_TIME_MET "mainhand" // killed before the grenade was released
		STAND	 			: KILLED
		STAND 				: ANIMDONE_TORSO
	}
}

state CHARGE_ATTACK_LANDMINE_SECONDARY
{
	movetype anim

	entrycommands
	{
		viewmodelanim charge
	}
	
	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_mine_supine_charge	: COOP_SUPINE
		coop_mine_prone_charge	: POSITION_TYPE "prone"

		minedetector_crouch_charge_secondary		: IS_WEAPON_ACTIVE "mainhand" "Minedetector" POSITION_TYPE "crouching"
		minedetector_stand_charge_secondary		: IS_WEAPON_ACTIVE "mainhand" "Minedetector"
		minedetectoraxis_crouch_charge_secondary	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat" POSITION_TYPE "crouching"
		minedetectoraxis_stand_charge_secondary		: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat"

		mine_crouch_charge_secondary			: POSITION_TYPE "crouching"
		mine_stand_charge_secondary			: default
	}

	states
	{
		STAND					: MOVEMENT_TYPE "running"
		STAND					: !ABLE_TO_DEFUSE
		RELEASE_KILLED_FRAG			: KILLED
		RELEASE_ATTACK_LANDMINE_SECONDARY	: !ATTACK_PRIMARY MIN_CHARGE_TIME_MET "mainhand"
	}
}

state RELEASE_ATTACK_LANDMINE_SECONDARY
{
	movetype anim

	entrycommands
	{
		viewmodelanim fire_secondary
	}
	exitcommands
	{
		correctweaponattachments
	}

	action
	{
		// [pass3, bug-2126] prone/supine rows - this state was missed by the 08-25 sweep
		coop_mine_supine_fire_sec	: COOP_SUPINE
		coop_mine_prone_fire_sec	: POSITION_TYPE "prone"

		minedetector_stand_idle_secondary	: !ABLE_TO_DEFUSE
		minedetector_stand_idle_secondary	: IS_WEAPON_ACTIVE "mainhand" "Minedetector" MOVEMENT_TYPE "running"
		minedetector_crouch_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "Minedetector" POSITION_TYPE "crouching"
		minedetector_stand_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "Minedetector"
		minedetectoraxis_stand_idle_secondary	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat" MOVEMENT_TYPE "running"
		minedetectoraxis_crouch_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat" POSITION_TYPE "crouching"
		minedetectoraxis_stand_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat"

		mine_stand_idle_secondary		: MOVEMENT_TYPE "running"
		mine_crouch_fire_secondary		: POSITION_TYPE "crouching"
		mine_stand_fire_secondary		: default
	}

	states
	{
		RELEASE_KILLED_FRAG		: KILLED MIN_CHARGE_TIME_MET "mainhand" // killed before the grenade was released
		STAND	 			: KILLED
		STAND 				: ANIMDONE_TORSO
	}
}

//==============================================================================
//==============================================================================
//
// Primary Charge Up Attacks (grenades)
//
//==============================================================================

state CHARGE_ATTACK_GRENADE
{
	movetype legs

	entrycommands
	{
		viewmodelanim charge
	}
	
	action
	{
		coop_gren_prone_charge	: POSITION_TYPE "prone"
		bomba_crouch_charge		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano" POSITION_TYPE "crouching"
		bomba_stand_charge		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano"

		bombabreda_crouch_charge	: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda" POSITION_TYPE "crouching"
		bombabreda_stand_charge		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda"

//		mine_crouch_charge		: IS_WEAPON_ACTIVE "mainhand" "Landmine" POSITION_TYPE "crouching"
//		mine_stand_charge		: IS_WEAPON_ACTIVE "mainhand" "Landmine"

		steilhandgranate_crouch_charge	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate" POSITION_TYPE "crouching"
		steilhandgranate_stand_charge	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate"

//		nebelhandgranate_crouch_charge	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate" POSITION_TYPE "crouching"
		nebelhandgranate_stand_charge	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate"

//		nebelhandgranate_crouch_charge	: IS_WEAPON_ACTIVE "mainhand" "RDG-1 Smoke Grenade" POSITION_TYPE "crouching"
//		nebelhandgranate_stand_charge	: IS_WEAPON_ACTIVE "mainhand" "RDG-1 Smoke Grenade"

//		nebelhandgranate_crouch_charge	: IS_WEAPON_ACTIVE "mainhand" "M18 Smoke Grenade" POSITION_TYPE "crouching"
//		nebelhandgranate_stand_charge	: IS_WEAPON_ACTIVE "mainhand" "M18 Smoke Grenade"
	
		grenade_crouch_charge		: POSITION_TYPE "crouching"
		grenade_stand_charge		: default
	}

	states
	{
		RELEASE_KILLED_FRAG		: KILLED
		STAND				: !HAS_WEAPON		
		RELEASE_ATTACK_GRENADE		: !ATTACK_PRIMARY MIN_CHARGE_TIME_MET "mainhand"
	}
}

state RELEASE_ATTACK_GRENADE
{
	movetype legs

	entrycommands
	{
		viewmodelanim fire
	}

	action
	{
		coop_gren_prone_throw	: POSITION_TYPE "prone"
		steilhandgranate_crouch_fire	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate" POSITION_TYPE "crouching"
		steilhandgranate_stand_fire	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate"

		steilhandgranate_crouch_fire	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate" POSITION_TYPE "crouching"
		steilhandgranate_stand_fire	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate"
	
		steilhandgranate_crouch_fire	: IS_WEAPON_ACTIVE "mainhand" "RDG-1 Smoke Grenade" POSITION_TYPE "crouching"
		steilhandgranate_stand_fire	: IS_WEAPON_ACTIVE "mainhand" "RDG-1 Smoke Grenade"

		steilhandgranate_crouch_fire	: IS_WEAPON_ACTIVE "mainhand" "M18 Smoke Grenade" POSITION_TYPE "crouching"
		steilhandgranate_stand_fire	: IS_WEAPON_ACTIVE "mainhand" "M18 Smoke Grenade"
              
            bomba_crouch_fire			: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano" POSITION_TYPE "crouching"
		bomba_stand_fire			: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano"

            bombabreda_crouch_fire		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda" POSITION_TYPE "crouching"
		bombabreda_stand_fire		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda"

//		mine_crouch_fire			: IS_WEAPON_ACTIVE "mainhand" "Landmine" POSITION_TYPE "crouching"
//		mine_stand_fire			: IS_WEAPON_ACTIVE "mainhand" "Landmine"

		grenade_crouch_fire		: POSITION_TYPE "crouching"
		grenade_stand_fire		: default
	}

	states
	{
		RELEASE_KILLED_FRAG 		: KILLED MIN_CHARGE_TIME_MET "mainhand" // killed before the grenade was released
		STAND	 				: KILLED

		STAND 				: ANIMDONE_TORSO
	}
}

state CHARGE_ATTACK_GRENADE_SECONDARY
{
	movetype legs

	entrycommands
	{
		viewmodelanim charge
	}
	
	action
	{
		coop_gren_prone_charge2	: POSITION_TYPE "prone"
		steilhandgranate_crouch_charge_secondary	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate" POSITION_TYPE "crouching"
		steilhandgranate_stand_charge_secondary	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate"

//		nebelhandgranate_crouch_charge_secondary	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate" POSITION_TYPE "crouching"
		nebelhandgranate_stand_charge_secondary	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate"

//		nebelhandgranate_crouch_charge_secondary	: IS_WEAPON_ACTIVE "mainhand" "RDG-1 Smoke Grenade" POSITION_TYPE "crouching"
//		nebelhandgranate_stand_charge_secondary	: IS_WEAPON_ACTIVE "mainhand" "RDG-1 Smoke Grenade"

//		nebelhandgranate_crouch_charge_secondary	: IS_WEAPON_ACTIVE "mainhand" "M18 Smoke Grenade" POSITION_TYPE "crouching"
//		nebelhandgranate_stand_charge_secondary	: IS_WEAPON_ACTIVE "mainhand" "M18 Smoke Grenade"

//          bomba_crouch_charge_secondary			: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano" POSITION_TYPE "crouching"
//		bomba_stand_charge_secondary			: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano"

//          bombabreda_crouch_charge_secondary		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda" POSITION_TYPE "crouching"
//		bombabreda_stand_charge_secondary		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda"
	
		grenade_crouch_charge_secondary		: POSITION_TYPE "crouching"
		grenade_stand_charge_secondary		: default
	}

	states
	{
//		RELEASE_ATTACK_GRENADE_SECONDARY		: PAIN	// This would make the player 
// drop a grenade when he gets hit
//		RELEASE_ATTACK_GRENADE_SECONDARY		: KILLED
		STAND						: !HAS_WEAPON		
		RELEASE_KILLED_FRAG				: KILLED
		RELEASE_ATTACK_GRENADE_SECONDARY		: !ATTACK_SECONDARY MIN_CHARGE_TIME_MET "mainhand"
	}
}

state RELEASE_ATTACK_GRENADE_SECONDARY
{
	movetype legs

	entrycommands
	{
		viewmodelanim fire
	}

	action
	{
		coop_gren_prone_throw2	: POSITION_TYPE "prone"
		steilhandgranate_crouch_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate" POSITION_TYPE "crouching"
		steilhandgranate_stand_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate"

		steilhandgranate_crouch_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate" POSITION_TYPE "crouching"
		steilhandgranate_stand_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate"
	
		steilhandgranate_crouch_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "RDG-1 Smoke Grenade" POSITION_TYPE "crouching"
		steilhandgranate_stand_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "RDG-1 Smoke Grenade"

		steilhandgranate_crouch_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "M18 Smoke Grenade" POSITION_TYPE "crouching"
		steilhandgranate_stand_fire_secondary	: IS_WEAPON_ACTIVE "mainhand" "M18 Smoke Grenade"

            bomba_crouch_fire_secondary			: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano" POSITION_TYPE "crouching"
		bomba_stand_fire_secondary			: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano"

		//mine_crouch_fire_secondary			: IS_WEAPON_ACTIVE "mainhand" "Landmine" POSITION_TYPE "crouching"
		//mine_stand_fire_secondary			: IS_WEAPON_ACTIVE "mainhand" "Landmine"

            bombabreda_crouch_fire_secondary		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda" POSITION_TYPE "crouching"
		bombabreda_stand_fire_secondary		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda"

		grenade_crouch_fire_secondary			: POSITION_TYPE "crouching"
		grenade_stand_fire_secondary			: default
	}

	states
	{
		RELEASE_KILLED_FRAG : KILLED MIN_CHARGE_TIME_MET "mainhand" // killed before the grenade was released
		STAND	 			     	: KILLED

		STAND 				: ANIMDONE_TORSO
	}
}

// killed while charging a frag grenade
state RELEASE_KILLED_FRAG
{
	entrycommands
	{
		charge mainhand secondary      // prep to drop the grenade
		releasefire mainhand secondary // drop the grenade
	}
	
	states
	{
		STAND	                       	: default
	}
}


//==============================================================================
//==============================================================================
//
// PUTAWAY
//
//==============================================================================

state PUTAWAY_MAIN
{

	entrycommands
	{
		exec coop_mod/weaponstate.scr "PUTAWAY_MAIN" //[200] Smithy - call weaponstate script
		
		zoomoff
		viewmodelanim putaway
	}

	states
	{
		// don't go through the putaway anim if 
		// we're switching to another weapon
		// only do if g_immediateswitch is set
		PUTAWAY_SKIPANIM			: IMMEDIATE_SWITCH NEW_WEAPON
	
		PUTAWAY_PISTOL			: IS_WEAPONCLASS_ACTIVE "mainhand" "pistol"
            PUTAWAY_PISTOL			: IS_WEAPON_ACTIVE      "mainhand" "Beretta"
		PUTAWAY_RIFLE			: IS_WEAPONCLASS_ACTIVE "mainhand" "rifle"
            PUTAWAY_RIFLE			: IS_WEAPON_ACTIVE      "mainhand" "Enfield L42A1"
		PUTAWAY_RIFLE			: IS_WEAPON_ACTIVE      "mainhand" "Carcano"
		PUTAWAY_RIFLE			: IS_WEAPON_ACTIVE      "mainhand" "DeLisle"
		PUTAWAY_RIFLE			: IS_WEAPON_ACTIVE      "mainhand" "Gewehrgranate"		
		PUTAWAY_GRENADE			: IS_WEAPONCLASS_ACTIVE "mainhand" "grenade"
		PUTAWAY_SMG				: IS_WEAPONCLASS_ACTIVE "mainhand" "smg"
            PUTAWAY_SMG				: IS_WEAPON_ACTIVE      "mainhand" "Moschetto"
		PUTAWAY_MG				: IS_WEAPONCLASS_ACTIVE "mainhand" "mg"
            PUTAWAY_MG				: IS_WEAPON_ACTIVE      "mainhand" "Vickers-Berthier"
		PUTAWAY_HEAVY			: IS_WEAPONCLASS_ACTIVE "mainhand" "heavy"
            PUTAWAY_HEAVY			: IS_WEAPON_ACTIVE      "mainhand" "PIAT"

		// Catchall at the end		
		PUTAWAY_NOANIM			: default
	}
}

// called when we want to skip the putaway anim
state PUTAWAY_SKIPANIM
{
	entrycommands
	{
		deactivateweapon righthand
	}
	
	states
	{ 
		RAISE_WEAPON	         	: default
	}
}

state PUTAWAY_NOANIM
{
	entrycommands
	{
		deactivateweapon righthand
	}

	states
	{
		RAISE_WEAPON	          	: NEW_WEAPON
		STAND			        	: default
	}
}

state PUTAWAY_PISTOL
{
	
	action
	{
		coop_prone_lower		: POSITION_TYPE "prone"
            beretta_crouch_lower		: IS_WEAPON_ACTIVE "mainhand" "Beretta" POSITION_TYPE "crouching"
		beretta_stand_lower	      : IS_WEAPON_ACTIVE "mainhand" "Beretta"

		pistol_crouch_lower	      : POSITION_TYPE "crouching"
		pistol_stand_lower	      : default
	}
	legs
	{
           	beretta_stand_idle		: IS_WEAPON_ACTIVE "mainhand" "Beretta" ON_LADDER
		pistol_stand_idle	       	: ON_LADDER
	}
	
	states
	{
		STAND	 				: KILLED
		
		GET_ON_LADDER		      : ANIMDONE_TORSO ON_LADDER
		STAND	 				: ANIMDONE_TORSO
	}
}

state PUTAWAY_RIFLE
{
	
	action
	{
		coop_prone_lower		: POSITION_TYPE "prone"
            enfieldl42a1_crouch_lower	: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1" POSITION_TYPE "crouching"
		enfieldl42a1_stand_lower	: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1"

		carcano_crouch_lower		: IS_WEAPON_ACTIVE "mainhand" "Carcano" POSITION_TYPE "crouching"
		carcano_stand_lower		: IS_WEAPON_ACTIVE "mainhand" "Carcano"
 
		delisle_crouch_lower		: IS_WEAPON_ACTIVE "mainhand" "DeLisle" POSITION_TYPE "crouching"
		delisle_stand_lower		: IS_WEAPON_ACTIVE "mainhand" "DeLisle"
 
		rifle_crouch_lower	      : POSITION_TYPE "crouching"
		rifle_stand_lower	        	: default
	}
	legs
	{
            enfieldl42a1_stand_idle		: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1" ON_LADDER
		carcano_stand_idle		: IS_WEAPON_ACTIVE "mainhand" "Carcano" ON_LADDER
		delisle_stand_idle		: IS_WEAPON_ACTIVE "mainhand" "DeLisle" ON_LADDER
		rifle_stand_idle	        	: ON_LADDER
	}
	
	states
	{
		STAND	 				: KILLED
		
		GET_ON_LADDER		      : ANIMDONE_TORSO ON_LADDER
		STAND	 				: ANIMDONE_TORSO
	}
}

state PUTAWAY_SMG
{
	
	action
	{
		coop_prone_lower		: POSITION_TYPE "prone"
		mp40_crouch_lower	        	: IS_WEAPON_ACTIVE "mainhand" "MP40" POSITION_TYPE "crouching"
		mp40_stand_lower	        	: IS_WEAPON_ACTIVE "mainhand" "MP40"

		sten_crouch_lower	        	: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II" POSITION_TYPE "crouching"
		sten_stand_lower	        	: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II"

		moschetto_crouch_lower	      : IS_WEAPON_ACTIVE "mainhand" "Moschetto" POSITION_TYPE "crouching"
		moschetto_stand_lower	      : IS_WEAPON_ACTIVE "mainhand" "Moschetto"

		smg_crouch_lower	        	: POSITION_TYPE "crouching"
		smg_stand_lower		      : default
	}
	legs
	{
		mp40_stand_idle		      : IS_WEAPON_ACTIVE "mainhand" "MP40" ON_LADDER
		sten_stand_idle		      : IS_WEAPON_ACTIVE "mainhand" "Sten Mark II" ON_LADDER
                moschetto_stand_idle	: IS_WEAPON_ACTIVE "mainhand" "Moschetto" ON_LADDER
		smg_stand_idle		      : ON_LADDER
	}
	
	states
	{
		STAND	 				: KILLED
		
		GET_ON_LADDER		      : ANIMDONE_TORSO ON_LADDER
		STAND	 				: ANIMDONE_TORSO
	}
}

state PUTAWAY_MG
{
	//please add bubble and duck code here
	action
	{
		coop_prone_lower		: POSITION_TYPE "prone"
            vickers_crouch_lower		: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier" POSITION_TYPE "crouching"
		vickers_stand_lower	      : IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier"

		mp44_crouch_lower	        	: IS_WEAPON_ACTIVE "mainhand" "StG 44" POSITION_TYPE "crouching"
		mp44_stand_lower	        	: IS_WEAPON_ACTIVE "mainhand" "StG 44"

		mg_crouch_lower		      : POSITION_TYPE "crouching"
		mg_stand_lower		      : default
	}
	legs
	{
            vickers_stand_idle		: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier" ON_LADDER
		mp44_stand_idle		      : IS_WEAPON_ACTIVE "mainhand" "StG 44" ON_LADDER	
		mg_stand_idle		      : ON_LADDER
	}
	
	states
	{
		STAND	 				: KILLED
		
		GET_ON_LADDER		      : ANIMDONE_TORSO ON_LADDER
		STAND	 				: ANIMDONE_TORSO
	}
}

state PUTAWAY_GRENADE
{
	
	action
	{
		coop_gren_prone_lower	: POSITION_TYPE "prone"
		steilhandgranate_crouch_lower	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate" POSITION_TYPE "crouching"
		steilhandgranate_stand_lower	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate"

		steilhandgranate_crouch_lower	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate" POSITION_TYPE "crouching"
		steilhandgranate_stand_lower	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate"

		bomba_crouch_lower		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano" POSITION_TYPE "crouching"
		bomba_stand_lower			: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano"

		minedetector_crouch_lower	: IS_WEAPON_ACTIVE "mainhand" "Minedetector" POSITION_TYPE "crouching"
		minedetector_stand_lower	: IS_WEAPON_ACTIVE "mainhand" "Minedetector"

		minedetectoraxis_crouch_lower	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat" POSITION_TYPE "crouching"
		minedetectoraxis_stand_lower	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat"

		mine_crouch_lower		: IS_WEAPON_ACTIVE "mainhand" "LandmineAxis" POSITION_TYPE "crouching"
		mine_stand_lower		: IS_WEAPON_ACTIVE "mainhand" "LandmineAxis"

		mine_crouch_lower		: IS_WEAPON_ACTIVE "mainhand" "LandmineAllies" POSITION_TYPE "crouching"
		mine_stand_lower		: IS_WEAPON_ACTIVE "mainhand" "LandmineAllies"

		bombabreda_crouch_lower		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda" POSITION_TYPE "crouching"
		bombabreda_stand_lower		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda"
	
		grenade_crouch_lower		: POSITION_TYPE "crouching"
		grenade_stand_lower		: default
	}
	legs
	{
		steilhandgranate_stand_idle	: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate"
		steilhandgranate_stand_idle	: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate"
		bomba_stand_idle		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano"
		minedetector_stand_idle		: IS_WEAPON_ACTIVE "mainhand" "Minedetector"
		minedetectoraxis_stand_idle	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat"
		mine_stand_idle			: IS_WEAPON_ACTIVE "mainhand" "LandmineAxis"
		mine_stand_idle			: IS_WEAPON_ACTIVE "mainhand" "LandmineAllies"
		bombabreda_stand_idle		: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda"
		grenade_stand_idle		: IS_WEAPONCLASS_ACTIVE "mainhand" "grenade"
		grenade_stand_idle		: ON_LADDER
	}
	
	states
	{
		STAND	 				: KILLED
		
		GET_ON_LADDER			: ANIMDONE_TORSO ON_LADDER
		STAND	 				: ANIMDONE_TORSO
	}
}

state PUTAWAY_HEAVY
{
	
	action
	{
		coop_prone_lower		: POSITION_TYPE "prone"
            piat_crouch_lower	   		: IS_WEAPON_ACTIVE "mainhand" "PIAT" POSITION_TYPE "crouching"
		piat_stand_lower	        	: IS_WEAPON_ACTIVE "mainhand" "PIAT"

		shotgun_crouch_lower	    	: POSITION_TYPE "crouching" IS_WEAPON_ACTIVE "mainhand" "Shotgun"
		shotgun_stand_lower		: IS_WEAPON_ACTIVE "mainhand" "Shotgun"
		
		bazooka_crouch_lower	     	: POSITION_TYPE "crouching"
		bazooka_stand_lower		: default
	}
	legs
	{
            piat_stand_idle			: IS_WEAPON_ACTIVE "mainhand" "PIAT" ON_LADDER
		shotgun_stand_idle		: ON_LADDER IS_WEAPON_ACTIVE "mainhand" "Shotgun"		
		bazooka_stand_idle		: ON_LADDER
	}
	
	states
	{
		STAND	 				: KILLED
		
		GET_ON_LADDER			: ANIMDONE_TORSO ON_LADDER
		STAND	 				: ANIMDONE_TORSO
	}
}

//==============================================================================
//==============================================================================
//
// RAISE_WEAPON
//
//==============================================================================

state RAISE_WEAPON
{
	movetype legs

	entrycommands
	{	
		exec coop_mod/weaponstate.scr "RAISE_WEAPON" //[200] Smithy - call weaponstate script

		viewmodelanim pullout

		// just to make sure nothing funky's 
		// attached that shouldn't be.
		correctweaponattachments
	}

	states
	{
		RAISE_PISTOL			: IS_NEW_WEAPONCLASS "mainhand" "pistol"
		RAISE_PISTOL			: IS_NEW_WEAPON      "mainhand" "Beretta"
		RAISE_RIFLE			: IS_NEW_WEAPONCLASS "mainhand" "rifle"
		RAISE_RIFLE			: IS_NEW_WEAPON      "mainhand" "Enfield L42A1"
		RAISE_RIFLE			: IS_NEW_WEAPON      "mainhand" "Carcano"
		RAISE_RIFLE			: IS_NEW_WEAPON      "mainhand" "DeLisle"
		RAISE_RIFLE			: IS_NEW_WEAPON      "mainhand" "Gewehrgranate"		
		RAISE_GRENADE			: IS_NEW_WEAPONCLASS "mainhand" "grenade"
		RAISE_SMG			: IS_NEW_WEAPONCLASS "mainhand" "smg"
            	RAISE_SMG			: IS_NEW_WEAPON      "mainhand" "Moschetto"
		RAISE_MG			: IS_NEW_WEAPONCLASS "mainhand" "mg"
		RAISE_MG			: IS_NEW_WEAPON      "mainhand" "Vickers-Berthier"
		RAISE_HEAVY			: IS_NEW_WEAPONCLASS "mainhand" "heavy"
		RAISE_HEAVY			: IS_NEW_WEAPON      "mainhand" "PIAT"
		RAISE_PAPERS			: IS_NEW_WEAPON      "mainhand" "Papers"
		
		RAISE_NOANIM			: default
	}
}

state RAISE_NOANIM
{
	entrycommands
	{
		// delay the activation for a frame so that the player
		// spends at least one frame without a weapon, thus 
		// letting the legs state know that we've switched
		commanddelay 0.05 activatenewweapon
		commanddelay 0.05 forcetorsostate "STAND"
	}

}

state RAISE_RIFLE
{
	movetype legs
	
	action
	{
		coop_prone_raise		: POSITION_TYPE "prone"
		enfieldl42a1_crouch_raise	: IS_NEW_WEAPON "mainhand" "Enfield L42A1" POSITION_TYPE "crouching"
		enfieldl42a1_stand_raise	: IS_NEW_WEAPON "mainhand" "Enfield L42A1" 

		carcano_crouch_raise    	: IS_NEW_WEAPON "mainhand" "Carcano" POSITION_TYPE "crouching"
		carcano_stand_raise		: IS_NEW_WEAPON "mainhand" "Carcano"

		delisle_crouch_raise    	: IS_NEW_WEAPON "mainhand" "DeLisle" POSITION_TYPE "crouching"
		delisle_stand_raise		: IS_NEW_WEAPON "mainhand" "DeLisle"

		rifle_crouch_raise		: POSITION_TYPE "crouching"
		rifle_stand_raise	      	: default
	}
	
	states
	{
		STAND	 				: KILLED
		
		STAND	 				: ANIMDONE_TORSO
		
		// allow immediate switching to a different weapon instead
		RAISE_ABORT				: +NEW_WEAPON
	}
}

state RAISE_SMG
{
	movetype legs
	
	action
	{
		coop_prone_raise		: POSITION_TYPE "prone"
		moschetto_crouch_raise  	: IS_NEW_WEAPON "mainhand" "Moschetto" POSITION_TYPE "crouching"
		moschetto_stand_raise		: IS_NEW_WEAPON "mainhand" "Moschetto" 

		mp40_crouch_raise			: IS_NEW_WEAPON "mainhand" "MP40" POSITION_TYPE "crouching"
		mp40_stand_raise			: IS_NEW_WEAPON "mainhand" "MP40"

		sten_crouch_raise			: IS_NEW_WEAPON "mainhand" "Sten Mark II" POSITION_TYPE "crouching"
		sten_stand_raise			: IS_NEW_WEAPON "mainhand" "Sten Mark II"

		smg_crouch_raise			: POSITION_TYPE "crouching"
		smg_stand_raise			: default
	}
	
	states
	{
		STAND	 				: KILLED		
		STAND	 				: ANIMDONE_TORSO
		
		// allow immediate switching to a different weapon instead
		RAISE_ABORT				: +NEW_WEAPON
	}
}

state RAISE_MG
{
	movetype legs
	
	action
	{
		coop_prone_raise		: POSITION_TYPE "prone"
		vickers_crouch_raise         	: IS_NEW_WEAPON "mainhand" "Vickers-Berthier" POSITION_TYPE "crouching"
		vickers_stand_raise	     	: IS_NEW_WEAPON "mainhand" "Vickers-Berthier" 

		mp44_crouch_raise	       	: IS_NEW_WEAPON "mainhand" "StG 44" POSITION_TYPE "crouching"
		mp44_stand_raise	       	: IS_NEW_WEAPON "mainhand" "StG 44"

		mg_crouch_raise	           	: POSITION_TYPE "crouching"
		mg_stand_raise	           	: default
	}
	
	states
	{
		STAND	 				: KILLED		
		STAND	 				: ANIMDONE_TORSO
		
		// allow immediate switching to a different weapon instead
		RAISE_ABORT				: +NEW_WEAPON
	}
}

state RAISE_PISTOL
{
	movetype legs
	
	action
	{
		coop_prone_raise		: POSITION_TYPE "prone"
		beretta_crouch_raise          : IS_NEW_WEAPON "mainhand" "Beretta" POSITION_TYPE "crouching"
		beretta_stand_raise	      : IS_NEW_WEAPON "mainhand" "Beretta"

		pistol_crouch_raise	      : POSITION_TYPE "crouching"
		pistol_stand_raise	      : default
	}
	
	states
	{
		STAND	 				: KILLED		
		STAND	 				: ANIMDONE_TORSO
		
		// allow immediate switching to a different weapon instead
		RAISE_ABORT				: +NEW_WEAPON
	}
}

state RAISE_GRENADE
{
	movetype legs
	
	action
	{
		coop_gren_prone_raise	: POSITION_TYPE "prone"
		steilhandgranate_crouch_raise	: IS_NEW_WEAPON "mainhand" "Stielhandgranate" POSITION_TYPE "crouching"
		steilhandgranate_stand_raise	: IS_NEW_WEAPON "mainhand" "Stielhandgranate"

		steilhandgranate_crouch_raise	: IS_NEW_WEAPON "mainhand" "Nebelhandgranate" POSITION_TYPE "crouching"
		steilhandgranate_stand_raise	: IS_NEW_WEAPON "mainhand" "Nebelhandgranate"

		bomba_crouch_raise		: IS_NEW_WEAPON "mainhand" "Bomba A Mano" POSITION_TYPE "crouching"
		bomba_stand_raise		: IS_NEW_WEAPON "mainhand" "Bomba A Mano"

		minedetector_crouch_raise	: IS_NEW_WEAPON "mainhand" "Minedetector" POSITION_TYPE "crouching"
		minedetector_stand_raise	: IS_NEW_WEAPON "mainhand" "Minedetector"

		minedetectoraxis_crouch_raise	: IS_NEW_WEAPON "mainhand" "Minensuchgerat" POSITION_TYPE "crouching"
		minedetectoraxis_stand_raise	: IS_NEW_WEAPON "mainhand" "Minensuchgerat"

		mine_crouch_raise		: IS_NEW_WEAPON "mainhand" "LandmineAxis" POSITION_TYPE "crouching"
		mine_stand_raise		: IS_NEW_WEAPON "mainhand" "LandmineAxis"

		mine_crouch_raise		: IS_NEW_WEAPON "mainhand" "LandmineAllies" POSITION_TYPE "crouching"
		mine_stand_raise		: IS_NEW_WEAPON "mainhand" "LandmineAllies"

		bombabreda_crouch_raise		: IS_NEW_WEAPON "mainhand" "Bomba A Mano Breda" POSITION_TYPE "crouching"
		bombabreda_stand_raise		: IS_NEW_WEAPON "mainhand" "Bomba A Mano Breda"
	
		grenade_crouch_raise		: POSITION_TYPE "crouching"
		grenade_stand_raise		: default
	}
	
	states
	{
		STAND	 				: KILLED		
		STAND	 				: ANIMDONE_TORSO
		
		// allow immediate switching to a different weapon instead
		RAISE_ABORT				: +NEW_WEAPON
	}
}

state RAISE_HEAVY
{
	movetype legs
	
	action
	{
		coop_prone_raise		: POSITION_TYPE "prone"
		piat_crouch_raise             : IS_NEW_WEAPON "mainhand" "PIAT" POSITION_TYPE "crouching"
		piat_stand_raise	        	: IS_NEW_WEAPON "mainhand" "PIAT"

		shotgun_crouch_raise	      : POSITION_TYPE "crouching" IS_NEW_WEAPON "mainhand" "Shotgun"
		shotgun_stand_raise		: IS_NEW_WEAPON "mainhand" "Shotgun"
		
		bazooka_crouch_raise	      : POSITION_TYPE "crouching"
		bazooka_stand_raise		: default
	}
	
	states
	{
		STAND	 				: KILLED		
		STAND	 				: ANIMDONE_TORSO
		
		// allow immediate switching to a different weapon instead
		RAISE_ABORT				: +NEW_WEAPON
	}
}

state RAISE_PAPERS
{
	movetype legs
	
	action
	{
		coop_prone_raise		: POSITION_TYPE "prone" // [pass4, bug-2127] the one RAISE_ state every sweep missed

		show_papers	: default
	}
	
	states
	{
		STAND					: KILLED
		
		STAND					: ANIMDONE_TORSO
		
		// allow immediate switching to a different weapon instead
		//RAISE_ABORT				: +NEW_WEAPON
	}
}

// This state allows the player to abort the raising 
// of a weapon in favor of a different new weapon.
state RAISE_ABORT
{
	entrycommands
	{
		deactivateweapon righthand
	}
	
	states
	{
		RAISE_WEAPON			: default
	}
}

//==============================================================================
//==============================================================================
//
// Weapon Reloading
//
//==============================================================================

//=========================================================================
// [user 2026-08-26] PRONE RELOAD, exiting on the WEAPON rather than on the animation.
//
// The first attempt put coop_prone_reload in each RELOAD_* action block. Those states exit on
// ANIMDONE_TORSO, and the borrowed pistol animation is SHORTER than a rifle reload - so the torso
// finished early, popped to STAND, found the weapon still reloading, re-entered and replayed. The
// user saw exactly that: "the pistol anim I think would have worked if it actually ended versus
// constantly played on repeat", plus the torso rising between each loop.
//
// A reload does NOT end when a body animation ends. Weapon::DoneReloading (weapon.cpp:3932) clears
// ShouldReload when the WEAPON's own reload animation completes, and the RELOAD conditional reads
// exactly that. Exiting on !RELOAD therefore tracks the real reload for every weapon, whatever its
// length, with no per-weapon timing to get wrong.
//
// Nothing re-enters this state, so the one-shot animation holds its LAST FRAME for the remainder -
// a prone pose - instead of looping. That is the same one-shot behaviour the crawl states rely on.
//=========================================================================
state COOP_RELOAD_PRONE
{
	movetype legs

	entrycommands
	{
		zoomoff
		viewmodelanim reload
	}

	action
	{
		coop_prone_reload		: default
	}

	states
	{
		STAND					: KILLED
		STAND					: !RELOAD
		RELOAD_INTERUPTED		: NEW_WEAPON
		RELOAD_INTERUPTED		: IS_USING_VEHICLE
		RELOAD_INTERUPTED		: IS_USING_TURRET
	}
}

state RELOAD_WEAPON
{
	states
	{
		//[user 2026-08-26] ROUTE DISABLED: exiting on !RELOAD locked the player out of firing
		//("cant shoot after I reload in prone") - ShouldReload evidently does not clear the way this
		//assumed, so the state never released the torso. A cosmetic pop is survivable; being unable to
		//shoot is not. State kept below, unreachable, as the starting point for a third attempt.
		//COOP_RELOAD_PRONE		: POSITION_TYPE "prone"

		RELOAD_SPRINGFIELD		: IS_WEAPON_ACTIVE "mainhand" "Springfield '03 Sniper"
		RELOAD_SPRINGFIELD		: IS_WEAPON_ACTIVE "mainhand" "KAR98 - Sniper"
		//[reload audit 2026-10-05] these two already wear the one-round-at-a-time hands (cgame maps
		//them to the springfield/kar98sniper prefix) but fell to RELOAD_RIFLE's Garand en-bloc torso:
		//only the start clip played, no round went in on screen, and a Garand clip sat in the hand.
		RELOAD_SPRINGFIELD		: IS_WEAPON_ACTIVE "mainhand" "Springfield M1903"
		RELOAD_SPRINGFIELD		: IS_WEAPON_ACTIVE "mainhand" "Silenced Kar98 Sniper"
		//[reload audit phase B 2026-10-05] scoped bolt rifles load ONE ROUND AT A TIME (the scope sits over the
		//action, so stripper clips cannot be used - historically correct, user decision). Their hands are the
		//coopr_<gun>_reload* aliases in anims_shared.txt (the kar98sniper single-round set; ejection ports within ~1u).
		RELOAD_SPRINGFIELD		: IS_WEAPON_ACTIVE "mainhand" "Arisaka Sniper"
		RELOAD_SPRINGFIELD		: IS_WEAPON_ACTIVE "mainhand" "Mosin-Nagant Sniper"
		RELOAD_SPRINGFIELD		: IS_WEAPON_ACTIVE "mainhand" "Silenced Mosin Sniper"
		RELOAD_SPRINGFIELD		: IS_WEAPON_ACTIVE "mainhand" "Lee-Enfield Sniper"
		//[reload audit 2026-10-05] StG44 Scoped is class rifle but wears StG 44 hands: give it the
		//MG reload state (magazine prop + attachment correction on interrupt), not the Garand's.
		RELOAD_MG			: IS_WEAPON_ACTIVE "mainhand" "StG44 Scoped"
		RELOAD_SHOTGUN			: IS_WEAPON_ACTIVE "mainhand" "Shotgun"
		RELOAD_NAGANTREV		: IS_WEAPON_ACTIVE "mainhand" "Nagant Revolver"
		RELOAD_M10				: IS_WEAPON_ACTIVE "mainhand" "S&W M10 .38"
		RELOAD_WEBLEY			: IS_WEAPON_ACTIVE "mainhand" "Webley Revolver"
		//[reload audit phase B 2026-10-05] the renamed colt45_colt1911w.tik is a Webley break-top mesh
		RELOAD_WEBLEY			: IS_WEAPON_ACTIVE "mainhand" "Webley Mk VI"

		RELOAD_PISTOL			: IS_WEAPONCLASS_ACTIVE "mainhand" "pistol"
		RELOAD_PISTOL			: IS_WEAPON_ACTIVE      "mainhand" "Beretta"
		RELOAD_RIFLE			: IS_WEAPONCLASS_ACTIVE "mainhand" "rifle"
		RELOAD_RIFLE			: IS_WEAPON_ACTIVE      "mainhand" "Enfield L42A1"
		RELOAD_RIFLE			: IS_WEAPON_ACTIVE      "mainhand" "DeLisle"
		RELOAD_RIFLE			: IS_WEAPON_ACTIVE      "mainhand" "Carcano"
		RELOAD_RIFLE			: IS_WEAPON_ACTIVE      "mainhand" "Gewehrgranate"		
		RELOAD_SMG			: IS_WEAPONCLASS_ACTIVE "mainhand" "smg"
		RELOAD_MG			: IS_WEAPONCLASS_ACTIVE "mainhand" "mg"
		RELOAD_MG			: IS_WEAPON_ACTIVE      "mainhand" "Vickers-Berthier"

		RELOAD_GRENADE			: IS_WEAPONCLASS_ACTIVE "mainhand" "grenade"
		RELOAD_HEAVY			: IS_WEAPONCLASS_ACTIVE "mainhand" "heavy"
		RELOAD_HEAVY			: IS_WEAPON_ACTIVE      "mainhand" "PIAT"

		RELOAD_RIFLE			: default	
	}
}

state RELOAD_RIFLE
{
	movetype legs

	entrycommands
	{
		zoomoff
		viewmodelanim reload
	}

	action
	{
		kar98_reload			: IS_WEAPON_ACTIVE "mainhand" "Gewehrgranate"
		kar98_reload			: IS_WEAPON_ACTIVE "mainhand" "Mauser KAR 98K"
		enfield_reload			: IS_WEAPON_ACTIVE "mainhand" "Lee-Enfield"
		svt_reload				: IS_WEAPON_ACTIVE "mainhand" "SVT 40"
		mosin_reload			: IS_WEAPON_ACTIVE "mainhand" "Mosin Nagant Rifle"
		g43_reload				: IS_WEAPON_ACTIVE "mainhand" "G 43"
		enfieldl42a1_reload		: IS_WEAPON_ACTIVE "mainhand" "Enfield L42A1"
		carcano_reload			: IS_WEAPON_ACTIVE "mainhand" "Carcano"
		delisle_reload			: IS_WEAPON_ACTIVE "mainhand" "DeLisle"
		//[reload audit 2026-10-05] each of these wears its BASE gun's first-person reload (cgame
		//prefix) but fell through to rifle_reload: Garand en-bloc prop, gun handed back to the right
		//hand at 1.9 s mid-clip, and the reload ended at 2.03 s while the hands clip ran 2.9-3.9 s.
		kar98_reload			: IS_WEAPON_ACTIVE "mainhand" "Arisaka Type 99"
		g43_reload				: IS_WEAPON_ACTIVE "mainhand" "G43 Sniper"
		carcano_reload			: IS_WEAPON_ACTIVE "mainhand" "Carcano Sniper"
		coop_reload_johnson		: IS_WEAPON_ACTIVE "mainhand" "Johnson M1941"
		//[reload audit phase B 2026-10-05] the M1 Carbine's 15-round box magazine: the G43 torso (bottom box,
		//g43_clip prop, 2.93 s) under its own retargeted hands (coopr_m1_carbine_reload); was the Garand en-bloc.
		g43_reload				: IS_WEAPON_ACTIVE "mainhand" "M1 Carbine"
		rifle_reload			: default
	}

	states
	{
		STAND	 				: KILLED
		STAND					: ANIMDONE_TORSO
		RELOAD_INTERUPTED			: NEW_WEAPON
		
		RELOAD_INTERUPTED			: IS_USING_VEHICLE
		RELOAD_INTERUPTED			: IS_USING_TURRET

	}
}

state RELOAD_SMG
{
	movetype legs

	entrycommands
	{
		viewmodelanim reload
	}

	action
	{
		//[reload audit phase B 2026-10-05] DRUM guns (exact names - above the "MP40" row, which would match "MP40 (MP18)"
		//through the skin-suffix strip): the drum comes off sideways, own drum props.
		coop_reload_mp18			: IS_WEAPON_ACTIVE "mainhand" "MP40 (MP18)"
		coop_reload_tommydrum50		: IS_WEAPON_ACTIVE "mainhand" "Thompson 50rd"
		coop_reload_tommydrum1928		: IS_WEAPON_ACTIVE "mainhand" "Thompson (1928 Tommy)"
		mp40_reload				: IS_WEAPON_ACTIVE "mainhand" "MP40"
		sten_reload				: IS_WEAPON_ACTIVE "mainhand" "Sten Mark II"
		ppsh_reload				: IS_WEAPON_ACTIVE "mainhand" "PPSH SMG"
            moschetto_reload          	: IS_WEAPON_ACTIVE "mainhand" "Moschetto"
		//[reload audit 2026-10-05] guns that wear MP40 / Moschetto hands get that gun's torso too
		//(its magazine prop and its exact clip length) instead of the Thompson default.
		mp40_reload				: IS_WEAPON_ACTIVE "mainhand" "Silenced MP40"
		mp40_reload				: IS_WEAPON_ACTIVE "mainhand" "M3 Grease Gun"
		mp40_reload				: IS_WEAPON_ACTIVE "mainhand" "Silenced Grease Gun"
		mp40_reload				: IS_WEAPON_ACTIVE "mainhand" "Silenced PPS-43"
		moschetto_reload			: IS_WEAPON_ACTIVE "mainhand" "Beretta M38"
		smg_reload				: default
                
	}

	states
	{
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS : KILLED
		STAND				      : ANIMDONE_TORSO
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: NEW_WEAPON
		
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET

		//RELOAD_INTERUPTED_CORRECT_ATTACHMENTS_SECONDARYATTACK	: +ATTACK_SECONDARY
	}
}

state RELOAD_MG
{
	movetype legs

	entrycommands
	{
		viewmodelanim reload
	}

	action
	{
	      vickers_reload		   	: IS_WEAPON_ACTIVE "mainhand" "Vickers-Berthier"
		mp44_reload			      : IS_WEAPON_ACTIVE "mainhand" "StG 44"
		mp44_reload			      : IS_WEAPON_ACTIVE "mainhand" "StG44 Scoped"
		//[reload audit 2026-10-05] was fg42_reload (= the BAR torso: 3.27 s, a BAR magazine held
		//upright, shown together with the gun's own magazine 1.32-1.65 s). coop_reload_fg42 matches
		//DaRKaNGeL's 2.34 s hands and carries the FG42's own magazine on the hand's away window.
		coop_reload_fg42		      : IS_WEAPON_ACTIVE "mainhand" "FG 42"
		//[reload audit 2026-10-05] the Breda's own TA torso (whole-reload hand swap, 5.73 s) existed
		//in anims_breda.txt but was never selected: mg_reload cut its hands clip at 57 %.
		breda_reload			      : IS_WEAPON_ACTIVE "mainhand" "Breda"
		coop_reload_dp28		      : IS_WEAPON_ACTIVE "mainhand" "DP-28"
		//[reload audit phase B 2026-10-05] BELT reloads with an opening top cover (were the BAR box-magazine torso)
		coop_reload_mg42		      : IS_WEAPON_ACTIVE "mainhand" "MG42"
		coop_reload_m1919		      : IS_WEAPON_ACTIVE "mainhand" "M1919 30cal"
		//[reload audit phase B 2026-10-05] the Lewis gun's top pan (was the BAR box-magazine torso)
		coop_reload_lewis		      : IS_WEAPON_ACTIVE "mainhand" "Lewis Gun"
		mg_reload			      : default
	}

	states
	{
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS : KILLED
		STAND				      : ANIMDONE_TORSO

		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: NEW_WEAPON		
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
	}
}

state RELOAD_PISTOL
{
	movetype legs

	entrycommands
	{
		viewmodelanim reload
	}

	action
	{
		// [user 2026-08-26] the one class with a NATIVE prone reload. Duration honestly changes to
		// the animation's real 1.50s (standing colt reload is ~1.5s too - net wash, stated anyway).
		coop_prone_reload_pistol	: POSITION_TYPE "prone"
	      beretta_reload			  : IS_WEAPON_ACTIVE "mainhand" "Beretta"
		p38_reload			        : IS_WEAPON_ACTIVE "mainhand" "Walther P38"
		histandard_reload	              : IS_WEAPON_ACTIVE "mainhand" "Hi-Standard Silenced"
		//[reload audit 2026-10-05] East's revolver hands; pistol_reload hung a Colt MAGAZINE in the hand
		coop_reload_m10		        : IS_WEAPON_ACTIVE "mainhand" "S&W M10 .38"
		//[reload audit phase B 2026-10-05] the C96 loads from the TOP with a stripper clip (was the P38 grip swap)
		coop_reload_c96		        : IS_WEAPON_ACTIVE "mainhand" "Mauser C96"
		pistol_reload		        : default
	}

	states
	{
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS   : KILLED
		STAND				        : ANIMDONE_TORSO
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: NEW_WEAPON
		
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
	}
}

// start of reloading the webley revolver
state RELOAD_WEBLEY
{
	movetype legs

	entrycommands
	{
		viewmodelanim reload
	}

	action
	{
		//[reload audit phase B 2026-10-05] user: "revolvers should also drop old shells" - the same torso clip, plus the
		//star extractor throwing ALL fired cases at the break-open (anims_shared.txt coop_reload_webley_start)
		coop_reload_webley_start	     	: default
	}

	states
	{
		STAND	 				: KILLED
		RELOAD_WEBLEY_START_ARMED	      : +ATTACK_PRIMARY
		RELOAD_WEBLEY_SINGLE	      : ANIMDONE_TORSO
		RELOAD_INTERUPTED		      : NEW_WEAPON
		
		RELOAD_INTERUPTED		      : IS_USING_VEHICLE
		RELOAD_INTERUPTED		      : IS_USING_TURRET
	}
}
state RELOAD_WEBLEY_START_ARMED
{
	movetype legs
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_WEBLEY_BREAK_END	: ANIMDONE_TORSO HAS_AMMO_IN_CLIP "mainhand"
		RELOAD_WEBLEY_FETCH_FORCED	: ANIMDONE_TORSO
	}
}

// loads in a single webley revolver bullet
// HZM coop [revolver reload 2026-10-12] one round = FETCH (hand to the pouch) + SEAT (round in, counted);
// a fire press breaks the reload off: at once from FETCH, after the round is in from SEAT; then close and fire.
state RELOAD_WEBLEY_SINGLE
{
	movetype legs
	entrycommands
	{
		viewmodelanim reload_single 1
	}
	action
	{
		coop_reload_webley_fetch	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_WEBLEY_END	: NEW_WEAPON
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_WEBLEY_BREAK_END	: +ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand"
		RELOAD_WEBLEY_FETCH_ARMED	: +ATTACK_PRIMARY
		RELOAD_WEBLEY_END	: PUTAWAYMAIN
		RELOAD_WEBLEY_SEAT	: ANIMDONE_TORSO
	}
}
state RELOAD_WEBLEY_FETCH_ARMED
{
	movetype legs
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_WEBLEY_SEAT_FORCED	: ANIMDONE_TORSO
	}
}
state RELOAD_WEBLEY_FETCH_FORCED
{
	movetype legs
	entrycommands
	{
		viewmodelanim reload_single 1
	}
	action
	{
		coop_reload_webley_fetch	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_WEBLEY_SEAT_FORCED	: ANIMDONE_TORSO
	}
}
state RELOAD_WEBLEY_SEAT
{
	movetype legs
	action
	{
		coop_reload_webley_seat	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_WEBLEY_SEAT_ARMED	: +ATTACK_PRIMARY
		RELOAD_WEBLEY_CHECK_CONTINUE	: ANIMDONE_TORSO
	}
}
state RELOAD_WEBLEY_SEAT_ARMED
{
	movetype legs
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_WEBLEY_BREAK_END	: ANIMDONE_TORSO
	}
}
state RELOAD_WEBLEY_SEAT_FORCED
{
	movetype legs
	action
	{
		coop_reload_webley_seat	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_WEBLEY_BREAK_END	: ANIMDONE_TORSO
	}
}
state RELOAD_WEBLEY_BREAK_END
{
	movetype legs
	entrycommands
	{
		viewmodelanim reload_end
	}
	action
	{
		WEBLEY_reload_end	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_WEBLEY_BREAK_FIRE	: ANIMDONE_TORSO
	}
}
state RELOAD_WEBLEY_BREAK_FIRE
{
	movetype legs
	action
	{
		none	: default
	}
	states
	{
		STAND	: KILLED
		ATTACK_PISTOL_PRIMARY_AIM	: COOP_ADS HAS_AMMO_IN_CLIP "mainhand"
		ATTACK_PISTOL_PRIMARY	: HAS_AMMO_IN_CLIP "mainhand"
		STAND	: default
	}
}

// this check to see if the webley revolver should continue reloading, or if it's done
state RELOAD_WEBLEY_CHECK_CONTINUE
{
	movetype legs
	entrycommands
	{
		reload // this makes the weapon want to continue reloading if it can
	}
	action
	{
		none	: default
	}
	states
	{
		RELOAD_WEBLEY_END	: NEW_WEAPON
		RELOAD_WEBLEY_END	: PUTAWAYMAIN
		RELOAD_WEBLEY_SINGLE	: RELOAD
		RELOAD_WEBLEY_END	: default
	}
}

// this is the end of the webley revolver reload sequence
state RELOAD_WEBLEY_END
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim reload_end
	}
	
	action
	{
		WEBLEY_reload_end	        	: default
	}

	states
	{
		STAND	 				: KILLED
		STAND	 				: ANIMDONE_TORSO
	}
}

// start of reloading the nagant revolver

// HZM coop [revolver reload 2026-10-12] S&W M10: open / one round per loop / close - the Webley's states, cloned
state RELOAD_M10
{
	movetype legs

	entrycommands
	{
		viewmodelanim reload
	}

	action
	{
		//[reload audit phase B 2026-10-05] user: "revolvers should also drop old shells" - the same torso clip, plus the
		//star extractor throwing ALL fired cases at the break-open (anims_shared.txt coop_reload_m10_start)
		coop_reload_m10_start	     	: default
	}

	states
	{
		STAND	 				: KILLED
		RELOAD_M10_START_ARMED	      : +ATTACK_PRIMARY
		RELOAD_M10_SINGLE	      : ANIMDONE_TORSO
		RELOAD_INTERUPTED		      : NEW_WEAPON
		
		RELOAD_INTERUPTED		      : IS_USING_VEHICLE
		RELOAD_INTERUPTED		      : IS_USING_TURRET
	}
}
state RELOAD_M10_START_ARMED
{
	movetype legs
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_M10_BREAK_END	: ANIMDONE_TORSO HAS_AMMO_IN_CLIP "mainhand"
		RELOAD_M10_FETCH_FORCED	: ANIMDONE_TORSO
	}
}

// loads in a single webley revolver bullet
// HZM coop [revolver reload 2026-10-12] one round = FETCH (hand to the pouch) + SEAT (round in, counted);
// a fire press breaks the reload off: at once from FETCH, after the round is in from SEAT; then close and fire.
state RELOAD_M10_SINGLE
{
	movetype legs
	entrycommands
	{
		viewmodelanim reload_single 1
	}
	action
	{
		coop_reload_m10_fetch	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_M10_END	: NEW_WEAPON
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_M10_BREAK_END	: +ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand"
		RELOAD_M10_FETCH_ARMED	: +ATTACK_PRIMARY
		RELOAD_M10_END	: PUTAWAYMAIN
		RELOAD_M10_SEAT	: ANIMDONE_TORSO
	}
}
state RELOAD_M10_FETCH_ARMED
{
	movetype legs
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_M10_SEAT_FORCED	: ANIMDONE_TORSO
	}
}
state RELOAD_M10_FETCH_FORCED
{
	movetype legs
	entrycommands
	{
		viewmodelanim reload_single 1
	}
	action
	{
		coop_reload_m10_fetch	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_M10_SEAT_FORCED	: ANIMDONE_TORSO
	}
}
state RELOAD_M10_SEAT
{
	movetype legs
	action
	{
		coop_reload_m10_seat	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_M10_SEAT_ARMED	: +ATTACK_PRIMARY
		RELOAD_M10_CHECK_CONTINUE	: ANIMDONE_TORSO
	}
}
state RELOAD_M10_SEAT_ARMED
{
	movetype legs
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_M10_BREAK_END	: ANIMDONE_TORSO
	}
}
state RELOAD_M10_SEAT_FORCED
{
	movetype legs
	action
	{
		coop_reload_m10_seat	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_M10_BREAK_END	: ANIMDONE_TORSO
	}
}
state RELOAD_M10_BREAK_END
{
	movetype legs
	entrycommands
	{
		viewmodelanim reload_end
	}
	action
	{
		coop_reload_m10_end	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_M10_BREAK_FIRE	: ANIMDONE_TORSO
	}
}
state RELOAD_M10_BREAK_FIRE
{
	movetype legs
	action
	{
		none	: default
	}
	states
	{
		STAND	: KILLED
		ATTACK_PISTOL_PRIMARY_AIM	: COOP_ADS HAS_AMMO_IN_CLIP "mainhand"
		ATTACK_PISTOL_PRIMARY	: HAS_AMMO_IN_CLIP "mainhand"
		STAND	: default
	}
}

// this check to see if the webley revolver should continue reloading, or if it's done
state RELOAD_M10_CHECK_CONTINUE
{
	movetype legs
	entrycommands
	{
		reload // this makes the weapon want to continue reloading if it can
	}
	action
	{
		none	: default
	}
	states
	{
		RELOAD_M10_END	: NEW_WEAPON
		RELOAD_M10_END	: PUTAWAYMAIN
		RELOAD_M10_SINGLE	: RELOAD
		RELOAD_M10_END	: default
	}
}

// this is the end of the webley revolver reload sequence
state RELOAD_M10_END
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim reload_end
	}
	
	action
	{
		coop_reload_m10_end	        	: default
	}

	states
	{
		STAND	 				: KILLED
		STAND	 				: ANIMDONE_TORSO
	}
}

// start of reloading the nagant revolver

state RELOAD_NAGANTREV
{
	movetype legs

	entrycommands
	{
		viewmodelanim reload
	}

	action
	{
		nagantrev_reload_start		: default
	}

	states
	{
		STAND	 				: KILLED
		RELOAD_NAGANTREV_START_ARMED	      : +ATTACK_PRIMARY
		RELOAD_NAGANTREV_SINGLE	      : ANIMDONE_TORSO
		RELOAD_INTERUPTED		      : NEW_WEAPON
		
		RELOAD_INTERUPTED		      : IS_USING_VEHICLE
		RELOAD_INTERUPTED		      : IS_USING_TURRET

		//RELOAD_INTERUPTED_SECONDARYATTACK	: +ATTACK_SECONDARY
	}
}
state RELOAD_NAGANTREV_START_ARMED
{
	movetype legs
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_NAGANTREV_BREAK_END	: ANIMDONE_TORSO HAS_AMMO_IN_CLIP "mainhand"
		RELOAD_NAGANTREV_FETCH_FORCED	: ANIMDONE_TORSO
	}
}

// loads in a single nagant revolver bullet
// HZM coop [revolver reload 2026-10-12] one round = FETCH (hand to the pouch) + SEAT (round in, counted);
// a fire press breaks the reload off: at once from FETCH, after the round is in from SEAT; then close and fire.
state RELOAD_NAGANTREV_SINGLE
{
	movetype legs
	entrycommands
	{
		viewmodelanim reload_single 1
	}
	action
	{
		coop_reload_nagantrev_fetch	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_NAGANTREV_END	: NEW_WEAPON
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_NAGANTREV_BREAK_END	: +ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand"
		RELOAD_NAGANTREV_FETCH_ARMED	: +ATTACK_PRIMARY
		RELOAD_NAGANTREV_END	: PUTAWAYMAIN
		RELOAD_NAGANTREV_SEAT	: ANIMDONE_TORSO
	}
}
state RELOAD_NAGANTREV_FETCH_ARMED
{
	movetype legs
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_NAGANTREV_SEAT_FORCED	: ANIMDONE_TORSO
	}
}
state RELOAD_NAGANTREV_FETCH_FORCED
{
	movetype legs
	entrycommands
	{
		viewmodelanim reload_single 1
	}
	action
	{
		coop_reload_nagantrev_fetch	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_NAGANTREV_SEAT_FORCED	: ANIMDONE_TORSO
	}
}
state RELOAD_NAGANTREV_SEAT
{
	movetype legs
	action
	{
		coop_reload_nagantrev_seat	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_NAGANTREV_SEAT_ARMED	: +ATTACK_PRIMARY
		RELOAD_NAGANTREV_CHECK_CONTINUE	: ANIMDONE_TORSO
	}
}
state RELOAD_NAGANTREV_SEAT_ARMED
{
	movetype legs
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_NAGANTREV_BREAK_END	: ANIMDONE_TORSO
	}
}
state RELOAD_NAGANTREV_SEAT_FORCED
{
	movetype legs
	action
	{
		coop_reload_nagantrev_seat	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
		RELOAD_NAGANTREV_BREAK_END	: ANIMDONE_TORSO
	}
}
state RELOAD_NAGANTREV_BREAK_END
{
	movetype legs
	entrycommands
	{
		viewmodelanim reload_end
	}
	action
	{
		nagantrev_reload_end	: default
	}
	states
	{
		STAND	: KILLED
		RELOAD_NAGANTREV_BREAK_FIRE	: ANIMDONE_TORSO
	}
}
state RELOAD_NAGANTREV_BREAK_FIRE
{
	movetype legs
	action
	{
		none	: default
	}
	states
	{
		STAND	: KILLED
		ATTACK_PISTOL_PRIMARY_AIM	: COOP_ADS HAS_AMMO_IN_CLIP "mainhand"
		ATTACK_PISTOL_PRIMARY	: HAS_AMMO_IN_CLIP "mainhand"
		STAND	: default
	}
}

// this check to see if the nagant revolver should continue reloading, or if it's done
state RELOAD_NAGANTREV_CHECK_CONTINUE
{
	movetype legs
	entrycommands
	{
		reload // this makes the weapon want to continue reloading if it can
	}
	action
	{
		none	: default
	}
	states
	{
		RELOAD_NAGANTREV_END	: NEW_WEAPON
		RELOAD_NAGANTREV_END	: PUTAWAYMAIN
		RELOAD_NAGANTREV_SINGLE	: RELOAD
		RELOAD_NAGANTREV_END	: default
	}
}

// this is the end of the nagant revolver reload sequence
state RELOAD_NAGANTREV_END
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim reload_end

	}
	
	action
	{
		nagantrev_reload_end	      : default
	}

	states
	{
		STAND	 				: KILLED
		STAND	 				: ANIMDONE_TORSO
	}
}

state RELOAD_GRENADE
{
	movetype legs

	entrycommands
	{
		viewmodelanim reload
	}

	action
	{
		steilhandgranate_reload		: IS_WEAPON_ACTIVE "mainhand" "Stielhandgranate"
		steilhandgranate_reload		: IS_WEAPON_ACTIVE "mainhand" "Nebelhandgranate"
		bomba_reload			: IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano"
		minedetector_reload	       	: IS_WEAPON_ACTIVE "mainhand" "Minedetector"
		minedetectoraxis_reload	       	: IS_WEAPON_ACTIVE "mainhand" "Minensuchgerat"
		mine_reload	        	: IS_WEAPON_ACTIVE "mainhand" "LandmineAxis"
		mine_reload	        	: IS_WEAPON_ACTIVE "mainhand" "LandmineAllies"
		bombabreda_reload	        : IS_WEAPON_ACTIVE "mainhand" "Bomba A Mano Breda"
		grenade_reload			: default
	}

	states
	{
		STAND	 				: KILLED
		STAND					: ANIMDONE_TORSO
//		RELOAD_INTERUPTED			: NEW_WEAPON // so quick, don't bother with interupting it
	}
}

state RELOAD_HEAVY
{
	movetype legs

	entrycommands
	{
		viewmodelanim reload
	}

	action
	{
		piat_reload			: IS_WEAPON_ACTIVE "mainhand" "PIAT"
		panzerschreck_reload		: IS_WEAPON_ACTIVE "mainhand" "Panzerschreck"
		bazooka_reload			: default
	}

	states
	{
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: KILLED
		STAND					: ANIMDONE_TORSO
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: NEW_WEAPON
		
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET
	}
}


// start of reloading the springfield
state RELOAD_SPRINGFIELD
{
	movetype legs

	entrycommands
	{
		zoomoff
		viewmodelanim reload
	}

	action
	{
		springfield_reload_start	: default
	}

	states
	{
		STAND	 				: KILLED
		RELOAD_SPRINGFIELD_SINGLE	: ANIMDONE_TORSO
		RELOAD_INTERUPTED			: NEW_WEAPON
		
		RELOAD_INTERUPTED	        	: IS_USING_VEHICLE
		RELOAD_INTERUPTED	        	: IS_USING_TURRET
	}
}

// loads in a single bullet
state RELOAD_SPRINGFIELD_SINGLE
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim reload_single 1
	}
	
	action
	{
		springfield_reload_loop		: default
	}
	
	states
	{
		STAND	 				: KILLED
		RELOAD_SPRINGFIELD_END		: NEW_WEAPON
		
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET

		// allow early out
		RELOAD_SPRINGFIELD_END		: +ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand" !RELOAD
		RELOAD_SPRINGFIELD_END		: PUTAWAYMAIN

		RELOAD_SPRINGFIELD_CHECK_CONTINUE	: ANIMDONE_TORSO
	}
}

// this check to see if the springfield should continue reloading, or if it's done
state RELOAD_SPRINGFIELD_CHECK_CONTINUE
{
	movetype legs

	entrycommands
	{
		reload // this makes the weapon want to continue reloading if it can
	}
	
	action
	{
		none					: default
	}
	
	states
	{
		RELOAD_SPRINGFIELD_SINGLE	: RELOAD
		RELOAD_SPRINGFIELD_END		: default
	}
}

// this is the end of the shotgun reload sequence
state RELOAD_SPRINGFIELD_END
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim reload_end
	}
	
	action
	{
		springfield_reload_end	        : default
	}

	states
	{
		STAND	 				: KILLED
		STAND	 				: ANIMDONE_TORSO
	}
}


// start of reloading the shotgun
state RELOAD_SHOTGUN
{
	movetype legs

	entrycommands
	{
		viewmodelanim reload
	}

	action
	{
		shotgun_reload_start		: default
	}

	states
	{
		STAND	 				: KILLED
		RELOAD_SHOTGUN_SINGLE		: ANIMDONE_TORSO
		RELOAD_INTERUPTED			: NEW_WEAPON
		
		RELOAD_INTERUPTED			: IS_USING_VEHICLE
		RELOAD_INTERUPTED			: IS_USING_TURRET
	}
}

// loads in a single shotgun shell
state RELOAD_SHOTGUN_SINGLE
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim reload_single 1
	}
	
	action
	{
		shotgun_reload_loop		: default
	}
	
	states
	{
		STAND	 				: KILLED
		RELOAD_SHOTGUN_END		: NEW_WEAPON
		
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_VEHICLE
		RELOAD_INTERUPTED_CORRECT_ATTACHMENTS	: IS_USING_TURRET

		// allow early out
		RELOAD_SHOTGUN_END		: +ATTACK_PRIMARY HAS_AMMO_IN_CLIP "mainhand" !RELOAD
		RELOAD_SHOTGUN_END		: PUTAWAYMAIN
		
		RELOAD_SHOTGUN_CHECK_CONTINUE		: ANIMDONE_TORSO
	}
}

// this check to see if the shotgun should continue reloading, or if it's done
state RELOAD_SHOTGUN_CHECK_CONTINUE
{
	movetype legs

	entrycommands
	{
		reload // this makes the weapon want to continue reloading if it can
	}
	
	action
	{
		none					: default
	}
	
	states
	{
		RELOAD_SHOTGUN_SINGLE	      : RELOAD		
		RELOAD_SHOTGUN_END		: default
	}
}

// this is the end of the shotgun reload sequence
state RELOAD_SHOTGUN_END
{
	movetype legs
	
	entrycommands
	{
		viewmodelanim reload_end
	}
	
	action
	{
		shotgun_reload_end	    	: default
	}

	states
	{
		STAND	 				: KILLED
		STAND	 				: ANIMDONE_TORSO
	}
}

state RELOAD_INTERUPTED
{
	entrycommands
	{
		weaponcommand anim idle
	}
	states
	{
		STAND					: default
	}
}

state RELOAD_INTERUPTED_CORRECT_ATTACHMENTS
{
	entrycommands
	{
		correctweaponattachments
		weaponcommand anim idle
	}
	
	states
	{
		STAND					: default
	}
}

state RELOAD_INTERUPTED_SECONDARYATTACK
{
	states
	{
		CHECK_SECONDARY_ATTACK		: default
	}
}

state RELOAD_INTERUPTED_CORRECT_ATTACHMENTS_SECONDARYATTACK
{
	entrycommands
	{
		correctweaponattachments
	}
	
	states
	{
		CHECK_SECONDARY_ATTACK		: default
	}
}

//==============================================================================
//
// Death
//
//==============================================================================

state KILLED
{
	movetype anim

	entrycommands
	{
		exec coop_mod/events.scr "playerdeath" //[200] Smithy - trigger playerdeath event
		nextpaintime -1 // allow all pain calls to work properly for death anim selection
	}

	states
	{
		// [user 2026-08-26] dying while prone stays flat instead of standing up to die
		// [spec A8/P1] dying ON YOUR BACK stays on your back - COOP_DIED_SUPINE is latched by the
		// engine before the death path wipes the stance flags (the live supine flag is gone by the
		// time this dispatcher runs, which is why a COOP_SUPINE route here could never work).
		KILLED_SUPINE		: COOP_DIED_SUPINE
		KILLED_PRONE		: POSITION_TYPE "prone"
		EXPLOSION_KILLED	: PAIN_TYPE "explosion"
		EXPLOSION_KILLED	: PAIN_TYPE "grenade"
		EXPLOSION_KILLED	: PAIN_TYPE "rocket"
		KILLED_GENERIC		: default
	}
}

state KILLED_SUPINE
{
	action
	{
		coop_supine_death		: default
	}
	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_PRONE
{
	action
	{
		coop_prone_death		: default
	}
	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_GENERIC
{
	states
	{
		KILLED_RUNNING			: FORWARD_VELOCITY "130"
		KILLED_CROUCHING			: POSITION_TYPE "crouching"
		KILLED_STANDING			: default
	}
}

state KILLED_RUNNING
{
	action
	{
		death_knockedup			: PAIN_DIRECTION "front" PAIN_THRESHOLD "50" CHANCE "30"
		death_chest				: PAIN_DIRECTION "front" PAIN_THRESHOLD "50"
		death_run				: default
	}
	
	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_CROUCHING
{
	action
	{
		death_frontcrouch			: PAIN_DIRECTION "rear"
		rifle_pain_kneestodeath 	: default
	}

	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_STANDING
{
	states
	{
		KILLED_LOWER_TORSO		: PAIN_LOCATION "pelvis"
		KILLED_LOWER_TORSO		: PAIN_LOCATION "torso_lower"
		KILLED_UPPER_TORSO		: PAIN_LOCATION "torso_mid"
		KILLED_UPPER_TORSO		: PAIN_LOCATION "torso_upper"
		KILLED_NECK				: PAIN_LOCATION "neck"
		KILLED_HEAD				: PAIN_LOCATION "head"
		KILLED_HEAD				: PAIN_LOCATION "helmet"
		KILLED_RIGHT_ARM			: PAIN_LOCATION "r_arm_upper"
		KILLED_RIGHT_ARM			: PAIN_LOCATION "r_arm_lower"
		KILLED_RIGHT_ARM			: PAIN_LOCATION "r_hand"
		KILLED_LEFT_ARM			: PAIN_LOCATION "l_arm_upper"
		KILLED_LEFT_ARM			: PAIN_LOCATION "l_arm_lower"
		KILLED_LEFT_ARM			: PAIN_LOCATION "l_hand"
		KILLED_LEG				: PAIN_LOCATION "r_leg_upper"
		KILLED_LEG				: PAIN_LOCATION "r_leg_lower"
		KILLED_LEG				: PAIN_LOCATION "r_foot"
		KILLED_LEG				: PAIN_LOCATION "l_leg_upper"
		KILLED_LEG				: PAIN_LOCATION "l_leg_lower"
		KILLED_LEG				: PAIN_LOCATION "l_foot"

		KILLED_UPPER_TORSO		: default
	}
}

state KILLED_LOWER_TORSO
{
	action
	{
		death_back				: PAIN_DIRECTION "front" CHANCE "60"
		death_knockedup			: PAIN_DIRECTION "rear" CHANCE "35"
		death_run				: PAIN_DIRECTION "rear" CHANCE "70"
		death_crotch			: CHANCE "60"
		death_chest				: default
	}

	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_UPPER_TORSO
{
	action
	{
		death_knockedup			: PAIN_DIRECTION "front" CHANCE "20"
		death_back				: PAIN_DIRECTION "front" CHANCE "60"
		death_run				: PAIN_DIRECTION "rear" CHANCE "40"
		death_frontchoke			: CHANCE "30"
		death_shoot				: CHANCE "60"
		death_chest				: default
	}

	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_NECK
{
	action
	{
		death_frontchoke			: CHANCE "50"
		death_choke				: default
	}

	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_HEAD
{
	action
	{
		death_back				: PAIN_DIRECTION "front" CHANCE "50"
		death_head_flyforward   	: PAIN_DIRECTION "rear" CHANCE "30"
		death_headpistol			: CHANCE "20"
		death_twist				: CHANCE "25"
		death_shoot				: CHANCE "33"
		death_fall_to_knees		: CHANCE "50"
		death_collapse			: default
	}

	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_RIGHT_ARM
{
	action
	{
		death_twist				: PAIN_DIRECTION "rear" CHANCE "50"
		death_fall_back			: CHANCE "30"
		death_shoot				: CHANCE "50"
		death_chest				: default
	}

	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_LEFT_ARM
{
	action
	{
		death_twist				: PAIN_DIRECTION "front" CHANCE "50"
		death_fall_back			: CHANCE "30"
		death_shoot				: CHANCE "50"
		death_chest				: default
	}

	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_LEG
{
	action
	{
		death_knockedup	        	: PAIN_DIRECTION "rear" CHANCE "50"
		death_fall_back			: CHANCE "25"
		death_shoot				: CHANCE "33"
		death_fall_to_knees		: CHANCE "50"
		death_chest				: default
	}

	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state EXPLOSION_KILLED
{
	action
	{
		death_explosion_large		: PAIN_THRESHOLD "150"
		
		// directional death animations of in middle damage range
		death_explosion_back		: PAIN_DIRECTION "front"
		death_explosion_left		: PAIN_DIRECTION "left"
		death_explosion_right		: PAIN_DIRECTION "right"
		
		death_explosion_small		: default // a just-in-case catch-all
	}
	
	states
	{
		KILLED_WAIT_FOR_DONE		: default
	}
}

state KILLED_WAIT_FOR_DONE
{
	states
	{
		KILLED_DONE				: ANIMDONE_TORSO
	}

	exitcommands
	{
		dead	// Frees up resources and tells everyone I'm dead.
	}
}

state KILLED_DONE
{
	movetype anim
}


//==============================================================================
//==============================================================================
//
// Ladder Climbing
//
//==============================================================================

state USE_LADDER
{
	movetype climbwall
	
	entrycommands
	{
		safeholster 1 // put our weapon away
		attachtoladder // gets the ladder we're going to be climbing
	}
	
	states 
	{
		LADDER_PUTAWAY			: PUTAWAYMAIN
		LATCH_ONTO_LADDER			: !ONGROUND 
		GET_ON_LADDER			: default
	}
}

state LADDER_PUTAWAY
{
	entrycommands
	{
		deactivateweapon righthand
	}
	
	states
	{
		LATCH_ONTO_LADDER			: !ONGROUND 
		GET_ON_LADDER			: default
	}
}

state GET_ON_LADDER
{
	movetype climbwall


	// these entry commands ensure that the player 
	// will be standing when he gets off the ladder
	entrycommands
	{
		exec coop_mod/ladder_state.scr "ON_LADDER"
		modheight "stand"
		movementstealth "1.0"
		moveposflags "standing"
	}

	action
	{
		ladder_geton_top			: AT_TOP_OF_LADDER
		ladder_geton_bottom		: default
	}
	
	states
	{
		FINISHED_GET_OFF_LADDER		: KILLED
	
		// we go to LADDER_LEFT because the left hand will be up once we're on
		LADDER_IDLE_LEFT			: ANIMDONE_TORSO
	}
}

// This is for when the player grabs the ladder while not on the ground
state LATCH_ONTO_LADDER
{
	movetype climbwall

	// these entry commands ensure that the player 
	// will be standing when he gets off the ladder
	entrycommands
	{
		exec coop_mod/ladder_state.scr "ON_LADDER"
		modheight "stand"
		movementstealth "1.0"
		moveposflags "standing"
		tweakladderpos // make sure we're positioned properly on the ladder
	}
	
	states
	{
		LADDER_DOWN_LEFT			: default
	}
}

state GET_OFF_LADDER_TOP
{
	movetype climbwall
	
	action
	{
		ladder_getoff_top			: default
	}
	
	states
	{
		FINISHED_GET_OFF_LADDER		: KILLED
		
		FINISHED_GET_OFF_LADDER		: ANIMDONE_TORSO
	}
}

state GET_OFF_LADDER_BOTTOM
{
	movetype climbwall
	
	action
	{
		ladder_getoff_bottom		: default
	}
	
	states
	{
		FINISHED_GET_OFF_LADDER		: KILLED
	
		FINISHED_GET_OFF_LADDER		: ANIMDONE_TORSO
	}
}

state FINISHED_GET_OFF_LADDER
{
	movetype legs
	
	entrycommands
	{
		exec coop_mod/ladder_state.scr "OFF_LADDER"
		unattachfromladder
		safeholster 0 // pull weapon back out if we put it away to get on the ladder
	}

	states
	{
		STAND					: default
	}
}

// same as FINISHED_GET_OFF_LADDER, except that the player is jumping off
state JUMP_OFF_LADDER
{
	movetype legs
	
	entrycommands
	{
		exec coop_mod/ladder_state.scr "OFF_LADDER"
		unattachfromladder
		safeholster 0 // pull weapon back out if we put it away to get on the ladder
		jumpxy -70 0 150
	}

	states
	{
		STAND					: default
	}
}

// idling on a ladder with the left hand high
state LADDER_IDLE_LEFT
{
	movetype climbwall

	entrycommands
	{
		tweakladderpos // make sure we're positioned properly on the ladder
	}
	
	action
	{
		ladder_idle_left			: default
	}

	states
	{
		FINISHED_GET_OFF_LADDER	: KILLED
		
		// check for emergency getaway
		JUMP_OFF_LADDER			: +JUMP
		
		PUTAWAY_MAIN			: PUTAWAYMAIN	// just in case the weapon isn't put away yet
		
		// check for getting off top of the ladder
		GET_OFF_LADDER_TOP		: FORWARD LOOKING_UP "-30" CAN_GET_OFF_LADDER_TOP
		GET_OFF_LADDER_TOP		: BACKWARD !LOOKING_UP "-30" CAN_GET_OFF_LADDER_TOP

		// check for getting off bottom of the ladder
		GET_OFF_LADDER_BOTTOM	      : FORWARD !LOOKING_UP "-30" CAN_GET_OFF_LADDER_BOTTOM
		GET_OFF_LADDER_BOTTOM	      : BACKWARD LOOKING_UP "-30" CAN_GET_OFF_LADDER_BOTTOM
		
		LADDER_UP_RIGHT			: FORWARD LOOKING_UP "-30"
		LADDER_UP_RIGHT			: BACKWARD !LOOKING_UP "-30"
		
		LADDER_DOWN_LEFT			: FORWARD !LOOKING_UP "-30"
		LADDER_DOWN_LEFT			: BACKWARD LOOKING_UP "-30"
	}
}

// idling on a ladder with the right hand high
state LADDER_IDLE_RIGHT
{
	movetype climbwall
	
	entrycommands
	{
		tweakladderpos // make sure we're positioned properly on the ladder
	}
	
	action
	{
		ladder_idle_right			: default
	}
	
	states
	{
		FINISHED_GET_OFF_LADDER 	: KILLED
	
		// check for emergency getaway
		JUMP_OFF_LADDER			: +JUMP
		
		PUTAWAY_MAIN			: PUTAWAYMAIN	// just in case the weapon isn't put away yet
		
		// check for getting off top of the ladder
		GET_OFF_LADDER_TOP		: FORWARD LOOKING_UP "-30" CAN_GET_OFF_LADDER_TOP
		GET_OFF_LADDER_TOP		: BACKWARD !LOOKING_UP "-30" CAN_GET_OFF_LADDER_TOP

		// check for getting off bottom of the ladder
		GET_OFF_LADDER_BOTTOM	      : FORWARD !LOOKING_UP "-30" CAN_GET_OFF_LADDER_BOTTOM
		GET_OFF_LADDER_BOTTOM	      : BACKWARD LOOKING_UP "-30" CAN_GET_OFF_LADDER_BOTTOM
		
		LADDER_UP_LEFT			: FORWARD LOOKING_UP "-30"
		LADDER_UP_LEFT			: BACKWARD !LOOKING_UP "-30"
		
		LADDER_DOWN_RIGHT			: FORWARD !LOOKING_UP "-30"
		LADDER_DOWN_RIGHT			: BACKWARD LOOKING_UP "-30"
	}
}

state LADDER_UP_LEFT
{
	movetype climbwall
	
	entrycommands
	{
//		tweakladderpos // make sure we're positioned properly on the ladder
	}
	
	action
	{
		ladder_up_left			: default
	}
	
	states
	{
		FINISHED_GET_OFF_LADDER	      : KILLED
		
		// check for emergency getaway
		JUMP_OFF_LADDER			: +JUMP
		
		LADDER_IDLE_LEFT			: ANIMDONE_TORSO
	}
}

state LADDER_UP_RIGHT
{
	movetype climbwall
	
	entrycommands
	{
//		tweakladderpos // make sure we're positioned properly on the ladder
	}
	
	action
	{
		ladder_up_right			: default
	}
	
	states
	{
		FINISHED_GET_OFF_LADDER	      : KILLED
		
		// check for emergency getaway
		JUMP_OFF_LADDER			: +JUMP
		
		LADDER_IDLE_RIGHT			: ANIMDONE_TORSO
	}
}

state LADDER_DOWN_LEFT
{
	movetype climbwall
	
	entrycommands
	{
//		tweakladderpos // make sure we're positioned properly on the ladder
	}
	
	action
	{
		ladder_down_left			: default
	}
	
	states
	{
		FINISHED_GET_OFF_LADDER	      : KILLED
		
		// check for emergency getaway
		JUMP_OFF_LADDER			: +JUMP
		
		LADDER_IDLE_RIGHT			: ANIMDONE_TORSO
	}
}

state LADDER_DOWN_RIGHT
{
	movetype climbwall
	
	entrycommands
	{
//		tweakladderpos // make sure we're positioned properly on the ladder
	}
	
	action
	{
		ladder_down_right			: default
	}
	
	states
	{
		FINISHED_GET_OFF_LADDER	      : KILLED
		
		// check for emergency getaway
		JUMP_OFF_LADDER			: +JUMP
		
		LADDER_IDLE_LEFT			: ANIMDONE_TORSO
	}
}

state LADDER_SLIDE
{
	movetype climbwall
	
	action
	{
		ladder_slide			: default
	}
	
	states
	{
		FINISHED_GET_OFF_LADDER	      : KILLED
		
		// check for emergency getaway
		FINISHED_GET_OFF_LADDER	      : +JUMP
		
		FINISHED_GET_OFF_LADDER	      : ONGROUND
		LADDER_IDLE_LEFT			: !CROUCH
	}
}

//==============================================================================
//==============================================================================
//
// Generic Use
//
//==============================================================================

state GENERIC_USE
{
	entrycommands
	{
		usestuff
	}

	states
	{
		STAND	: default
	}
}


//==============================================================================
//==============================================================================
//
// Vehicles
//
//==============================================================================

state VEHICLE_PUTAWAY
{
	entrycommands
	{
		deactivateweapon righthand
	}
	
	states
	{
		VEHICLE_IDLE			: default
	}
}

state VEHICLE_START
{
	
	states
	{
		VEHICLE_PUTAWAY			: PUTAWAYMAIN	// Basic put weapon away move.
		VEHICLE_IDLE			: default
	}
}

state VEHICLE_TURRET_IDLE
{
	entrycommands
	{
		modheight "duck"
		moveposflags "crouching"
	}

	exitcommands
	{
		modheight "stand"
		moveposflags "standing"
	}

	movetype anim
	
	action
	{
		aagun_idle	  			: VEHICLE_TYPE "aagun"
		flak88_idle	  			: VEHICLE_TYPE "flak88"
		nebelwerfer_idle  		: VEHICLE_TYPE "nebelwerfer"
		granatwerfer_idle 		: VEHICLE_TYPE "granatwerfer"
		vehicle_idle	  		: default
	}
	
	states
	{
		VEHICLE_USE	  			: +USE
		STAND		  			: !IS_USING_VEHICLE
	}
}

state VEHICLE_NORMAL_IDLE
{
	movetype anim
	
	action
	{
		vehicle_idle	   		: default
	}
	
	states
	{
		VEHICLE_USE				: +USE
		STAND					: !IS_USING_VEHICLE
	}
}


state VEHICLE_IDLE
{
	states
	{
		// HZM coop [222] - vehicle GUNNER (jeep .30cal / halftrack MG): IS_USING_TURRET only ever
		// true for the slot gunner (EnterTurret), never for drivers/passengers. Must sit ABOVE the
		// default row - bug-309 final: while on a vehicle the TORSO state drives the whole body
		// (the legs statemap is engine-disabled, player.cpp EvaluateState:5754), so every legs-side
		// fix was writing to a machine that was switched off.
		COOP_VEHTURRET_MAN		: IS_USING_TURRET
		VEHICLE_TURRET_IDLE		: VEHICLE_TYPE "aagun"
		VEHICLE_TURRET_IDLE		: VEHICLE_TYPE "flak88"
		VEHICLE_TURRET_IDLE		: VEHICLE_TYPE "nebelwerfer"
		VEHICLE_TURRET_IDLE		: VEHICLE_TYPE "granatwerfer"
		VEHICLE_NORMAL_IDLE		: default
	}
}

// HZM coop [222] - full-body manning pose for vehicle-mounted guns (VEHICLE_TURRET_IDLE recipe:
// movetype anim + action block = full-body). r8: the MG42_stand set - the vanilla STANDING
// EMPLACEMENT GUNNER (upright, both hands on the spade grips at chest height) = the actual
// .30cal pedestal stance. Earlier tries: MG42_high (salute-arm misfit), MG42_crouch (ground
// tripod - hands drooped below the grips), flak88_idle (arms spread wide for flak wheels,
// torso pitched over the jeep). Aliases coop_turret_stand_* live in anims_shared.txt and now
// point at MG42_stand_idle_a(loop)/MG42_stand_firing.
state COOP_VEHTURRET_MAN
{
	movetype anim

	action
	{
		coop_turret_stand_fire	: ATTACK_PRIMARY_BUTTON
		coop_turret_stand_idle	: default
	}

	states
	{
		STAND					: !IS_USING_TURRET
		STAND					: !IS_USING_VEHICLE
	}
}

state VEHICLE_USE
{
	movetype anim

	action
	{
		vehicle_idle			: default
	}

	states
	{
		VEHICLE_IDLE			: default
	}
}


//==============================================================================
//==============================================================================
//
// Turrets
//
//==============================================================================

state TURRET_PUTAWAY
{
	entrycommands
	{
		deactivateweapon righthand
	}
	
	states
	{
		TURRET_IDLE				: default
	}
}

state TURRET_START
{
	// HZM coop - reverted to VANILLA (the duck/crouch + camera behind experiments made the mounted pose look
	// broken - lying down / detached gun). Clean first-person mounted view (g_turretcameras 0). We'll redo the
	// over-the-shoulder cam live.
	states
	{
		TURRET_PUTAWAY	        	: PUTAWAYMAIN	// Basic put weapon away move.
		TURRET_IDLE				: default
	}
}

state TURRET_IDLE
{
	movetype anim

	action
	{
		mg42tripod_crouch_aim_straight_straight	: IS_WEAPON_ACTIVE "mainhand" "Packed MG42 Turret"
		turret_idle				: default
	}

	states
	{
		STAND					: !IS_USING_TURRET
	}
}

// [user 2026-08-10] SELF-HEAL upper body. Deliberately a TORSO state, not a legs state: the user
// asked "can we make it so the legs dont change" and this is how - `movetype legs` means the torso
// follows whatever the legs are already doing, so the clip drives only the upper body. That also
// neutralises the one flaw in the source animation, whose legs are authored dangling from a pole.
// Exits on ANIMDONE_TORSO, and KILLED is listed first for the same reason every other state here
// does it - dying must win over any pose.
state COOP_SELFHEAL
{
	movetype legs

	camera behind

	entrycommands
	{
		viewmodelanim idle
	}

	action
	{
		// [pass4, bug-2127] the medkit heal is script-forced (forcetorsostate) and was
		// missed by every stance sweep - the standing heal loop sat the torso up for seconds.
		coop_supine_aim		: COOP_SUPINE
		coop_prone_aim			: POSITION_TYPE "prone"

		coop_selfheal			: default
	}

	states
	{
		KILLED				: KILLED
		//[user 2026-08-10] LOOP, do not exit. Self-transition on ANIMDONE_TORSO so the clip repeats for
		//as long as the heal runs - the user: "it may need to be repeated for the length of the revive".
		//Same pattern REVIVE_MEDIC uses in player_legs.st (REVIVE_MEDIC : ANIMDONE_LEGS).
		//Safe against sticking: medkit_use forces STAND at ALL FOUR of its exits (completion, gone
		//inactive, moved too far), and KILLED above outranks it.
		COOP_SELFHEAL			: ANIMDONE_TORSO
	}
}
