"""models/weapons/coop_dbshotgun.tik - written from the numbers below (one place), surfaces from build/model.json.

    python tools/dbs_tik.py

Recipe = the pump gun's tik (models/weapons/shotgun.tik, retail + the mod's two additions) with a NEW mesh and these
differences. The tik NAME is "Shotgun (Double Barrel)": the mod's engine strips " (<finish>)" everywhere a weapon is
looked up by name (first-person rows cg_viewmodelanim.c:165, third-person statemap player_conditionals.cpp:236,
loot icon, ADS tune), so the gun inherits every Shotgun row with NO engine change, and
`coopr_shotgun_double_barrel_<row>` first-person rows override the ones it needs of its own.
"""
import os, json
import dbslib as L

NAME = 'coop_dbshotgun'
WEAPON_NAME = 'Shotgun (Double Barrel)'

# ---- the numbers (pump gun in brackets; coop runs the `dm` set, `sp` is kept in step)
N = dict(
    clipsize=2,                    # [5] two barrels
    firedelay=0.30,                # [0.75] no pump to work: the second barrel is a second trigger away
    dm_count=26, dm_damage=14,     # [20 x 14 = 280] 26 x 14 = 364 per barrel: both barrels were cut down from a full choke
    sp_count=38, sp_damage=10,     # [30 x 10]
    rl_count=26, rl_damage=17,     # [20 x 17] realism
    spread='115 115 135 135',      # [80 80 95 95] cylinder bore, 13 in barrels: ~1.4 x the cone
    brange=650,                    # [1000] pellets stop here: a 33 cm barrel throws them slower
    speed=1.0,                     # [0.99] short and light
    dm_ammo=40, sp_ammo=10,        # [60 / 5]
    # view kick: pitch min max, yaw min max, recentre, pattern, abs pitch, abs yaw, lose-control pitch
    kick='-23.0 -26.0  -2.0 2.0  12.0  "T"  14.0 6.0 12.0',      # [-20 -20 0.05 0.05 15.2 T 12 5 10]; run act1: -27 -31 threw the view 25 deg up
)


# ---- sounds: retail files only, own alias names (declared in the tik's client init like models/frag-n-rock.tik does,
# so ubersound.scr is not edited). volume volMod pitch pitchMod dist maxDist channel
MAPS = 'maps "m e t dm obj lib"'
ALIASES = [
    # the pump gun's report, lower and louder: two barrels' worth of powder out of 33 cm tubes [retail 1.95 .. 0.8 0.1 480]
    ('coop_dbs_snd_fire', 'sound/weapons/fire/ShotgunFire1.wav', '2.2 0.0 0.70 0.05 540 8000 weapon'),
    ('coop_dbs_snd_open', 'sound/weapons/foley/wpn_Webley_reloadstart.wav', '1.7 0.0 0.85 0.05 160 1000 item'),     # break-top latch
    ('coop_dbs_snd_shell', 'sound/weapons/foley/ShotgunFill1.wav', '1.2 0.01 0.90 0.06 160 1000 item'),           # a shell pushed home
    ('coop_dbs_snd_close', 'sound/weapons/foley/coop_wpn_action_heavy.wav', '1.1 0.05 0.85 0.05 160 1000 item'),  # swung shut
]


def aliases():
    return '\n'.join('\t\taliascache %s %s soundparms %s loaded %s' % (n, f, sp, MAPS) for n, f, sp in ALIASES)


def _flash(tag):
    return FLASH.replace('@TAG@', tag)


def _eject(frame, count):
    return EJECT % dict(frame=frame, count=count)


def anims():
    a = ['animations', '{', '\tidle\tcoop_dbs_idle.skc']
    for nm, tag in (('fire', 'tag_dbs_r'), ('fire_empty', 'tag_dbs_l')):
        a += ['\t%s\tcoop_dbs_%s.skc' % (nm, nm), '\t{', '\t\tserver', '\t\t{', '\t\t\tentry shoot', '\t\t}', '\t\tclient', '\t\t{',
              '\t\t\tentry stopaliaschannel coop_dbs_snd_fire', '\t\t\tentry sound coop_dbs_snd_fire',
              '\t\t\tentry viewkick %s' % N['kick'], _flash(tag), '\t\t}', '\t}']
    for nm, count in (('reload', 1), ('reload_empty', 2)):
        a += ['\t%s\tcoop_dbs_%s.skc' % (nm, nm), '\t{', '\t\tclient', '\t\t{', '\t\t\tentry sound coop_dbs_snd_open',
              _eject(10, count), '\t\t}', '\t}']
    for nm in ('reload_single', 'reload_single_first'):
        a += ['\t%s\tcoop_dbs_%s.skc' % (nm, nm), '\t{', '\t\tclient', '\t\t{', '\t\t\t12 stopaliaschannel coop_dbs_snd_shell',
              '\t\t\t12 sound coop_dbs_snd_shell', '\t\t}', '\t}']
    a += ['\treload_end\tcoop_dbs_reload_end.skc', '\t{', '\t\tserver', '\t\t{', '\t\t\tlast idle', '\t\t}', '\t\tclient', '\t\t{',
          '\t\t\t12 sound coop_dbs_snd_close', '\t\t}', '\t}']
    a += ['\tsecondaryfire\tcoop_dbs_idle.skc', '\t{', '\t\tserver', '\t\t{', '\t\t\tentry shoot secondary', '\t\t}', '\t}', '}']
    return '\n'.join(a)


# the pump gun's muzzle effects, on the barrel that fired
FLASH = """			entry tagdlight @TAG@ 0.25 0.2 0.15 150 0.11
			entry tagspawnlinked @TAG@
			(
				scale 0.45
				offsetalongaxis 1.5 0 0
				count 1
				model muzsprite.spr
				angles 0 0 crandom 25
				life 0.06
			)
			entry tagspawn @TAG@
			(
				spawnrate 1.00
				model models/fx/bh_metal_fastpiece.tik
				count 3
				color 1.00 1.00 1.00
				scale 0.20
				life 0.30
				radius 3.00
				velocity 100.00
				randvel 100 0 0
				accel 0.00 0.00 -120.00
				offsetalongaxis 4 0 0
				fade
				align
			)
			entry tagspawnlinked @TAG@
			(
				spawnrate 1.00
				model muzsprite.spr
				color 1.00 1.00 1.00
				scale 0.70
				life 0.09
				scalerate 12.00
				velocity 33.00
				offsetalongaxis 4 0 0
				fade
				randomroll
			)
			entry commanddelay 0.010 originspawn
			(
				model vsssource.spr
				count 6
				alpha 0.30
				color 1.00 1.00 1.00
				spritegridlighting
				scale 0.80
				life 0.55
				scalerate 6.00
				cone 8.00 2.00
				velocity 300.00
				radialvelocity 11.00 60.00 120.00
				accel 0.00 0.00 -30.00
				friction 5.00
				offset crandom -5 crandom -5 crandom -5
				offsetalongaxis 22 0 0
				fade
				randomroll
			)"""

# the pump gun's case (its shell eject block), thrown by the ejectors as the action opens
EJECT = """			%(frame)d tagspawn tag_eject
			(
				count %(count)d
				model models/ammo/shotgunshell.tik
				spawnrange 1024
				scale 1.0
				velocity 90
				randvel crandom 14 crandom 14 random 20
				emitterangles 0 0 0
				avelocity crandom 120 crandom 120 0
				accel 0 0 -800
				physicsrate 20
				life 2.0
				fadedelay 1.7
				collision
				bouncefactor 0.2
				bouncesoundonce snd_shotgun_shell
			)"""


def tik(surfaces):
    surf = '\n'.join('\tsurface %s shader %s' % (s, 'coop_dbshotgun_parts' if s.startswith('dbsx') else 'coop_dbshotgun')
                     for s in surfaces)
    return TEMPLATE % dict(N, surf=surf, name=WEAPON_NAME, anims=anims(), aliases=aliases())


TEMPLATE = r"""TIKI
// HZM coop: sawn-off double-barrel shotgun. Mesh: "Double Barrel Shotgun" by Jean PFP (CC0, opengameart.org),
// converted by docs/proposals/dbshotgun_2026-10-12/tools (dbs_tik.py writes this file - edit the numbers THERE).
setup
{
	scale 0.52
	path models/weapons/coop_dbshotgun
	skelmodel coop_dbshotgun.skd
%(surf)s
}

init
{
	server
	{
		classname		Weapon
		weapontype		heavy
		weaponsubtype		2
		name			"%(name)s"
		rank			640 640

		sp bulletrange		%(brange)d
		sp bulletspread		%(spread)s
		dm bulletrange		%(brange)d
		dm bulletspread		%(spread)s
		realism bulletrange		%(brange)d
		realism bulletspread		%(spread)s

		sp bulletcount		%(sp_count)d
		sp bulletdamage		%(sp_damage)d
		dm bulletcount		%(dm_count)d
		dm bulletdamage		%(dm_damage)d
		realism bulletcount		%(rl_count)d
		realism bulletdamage		%(rl_damage)d

		sp firedelay		%(firedelay).2f
		dm firedelay		%(firedelay).2f
		realism firedelay		%(firedelay).2f

		sp movementspeed	%(speed).2f
		dm movementspeed 	%(speed).2f
		realism movementspeed 	%(speed).2f

		secondary firetype		melee
		secondary ammotype		none
		secondary ammorequired		0
		secondary meansofdeath		bash
		secondary bulletknockback	50
		secondary quiet
		sp secondary bulletrange	64
		sp secondary bulletdamage	60
		dm secondary bulletrange	96
		dm secondary bulletdamage	60
		realism secondary bulletrange	96
		realism secondary bulletdamage	60

		firetype		bullet
		ammotype		"shotgun"
		meansofdeath	shotgun
		semiauto
		clipsize		%(clipsize)d
		ammorequired	1

		sp startammo	%(sp_ammo)d
		dm startammo	%(dm_ammo)d
		sprealism startammo	%(sp_ammo)d
		dmrealism startammo	%(dm_ammo)d

		dm additionalstartammo "grenade" 2
		dm additionalstartammo "smokegrenade" 1
		dmrealism additionalstartammo "grenade" 2
		dmrealism additionalstartammo "smokegrenade" 1

		tracerfrequency 0
		crosshair		1

		pickupsound		shotgun_snd_pickup
		ammopickupsound	shotgun_snd_pickup_ammo
		noammosound		shotgun_snd_noammo

		holstertag				"Bip01 Spine2"
		holsteroffset			"8.0 -7.75 6.5"
		holsterangles			"0 185 -25"
		holsterScale			1.0

		weapongroup		rifle
		airange			short

		exec coop_mod/itemhandler.scr "initialiseItem" "shotgun" "Shotgun"
	}
	client
	{
		cache tracer.spr
		cache muzsprite.spr
		cache model models/fx/bh_metal_fastpiece.tik
		cache models/ammo/shotgunshell.tik
%(aliases)s
	}
}

%(anims)s

/*QUAKED addon_playerweapon_coop_dbshotgun (0.0 0.0 1.0) (-8 -8 -8) (8 8 8)
Weapon - sawn-off double-barrel shotgun (HZM coop)
*/
"""


def main():
    m = json.load(open(os.path.join(L.BUILD, 'model.json')))
    p = os.path.join(L.ASSETS, 'models', 'weapons', NAME + '.tik')
    open(p, 'w', newline='\n').write(tik(m['surfaces']))
    print('wrote', p, len(m['surfaces']), 'surfaces')


if __name__ == '__main__':
    main()
