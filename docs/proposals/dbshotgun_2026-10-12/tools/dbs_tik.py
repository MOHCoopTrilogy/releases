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
    kick='-27.0 -31.0  -2.5 2.5  11.0  "T"  16.0 7.0 13.0',      # [-20 -20 0.05 0.05 15.2 T 12 5 10]
)


def tik(surfaces):
    surf = '\n'.join('\tsurface %s shader %s' % (s, 'coop_dbshotgun_parts' if s.startswith('dbsx') else 'coop_dbshotgun')
                     for s in surfaces)
    return TEMPLATE % dict(N, surf=surf, name=WEAPON_NAME)


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
	}
}

animations
{
	idle	coop_dbs_idle.skc
	reload 	coop_dbs_idle.skc
	{
		client
		{
			entry sound shotgun_snd_reload_start
		}
	}
	reload_single coop_dbs_idle.skc
	{
		client
		{
			entry stopaliaschannel shotgun_snd_reload_single
			entry sound shotgun_snd_reload_single
		}
	}
	reload_end coop_dbs_idle.skc
	{
		server
		{
			last idle
		}
		client
		{
			entry sound shotgun_snd_reload_end
		}
	}
	secondaryfire     coop_dbs_idle.skc
	{
		server
		{
			entry shoot secondary
		}
	}
	fire	coop_dbs_idle.skc
	{
		server
		{
			entry shoot
		}
		client
		{
			entry stopaliaschannel shotgun_snd_fire
			entry sound shotgun_snd_fire

			entry viewkick %(kick)s

			entry tagdlight tag_barrel 0.25 0.2 0.15 140 0.11
			entry tagspawnlinked tag_barrel
			(
				scale 0.4
				offsetalongaxis 1.5 0 0
				count 1
				model muzsprite.spr
				angles 0 0 crandom 25
				life 0.06
			)
			entry tagspawn tag_barrel
			(
				spawnrate 1.00
				model models/fx/bh_metal_fastpiece.tik
				count 2
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
			entry tagspawnlinked tag_barrel
			(
				spawnrate 1.00
				model muzsprite.spr
				color 1.00 1.00 1.00
				scale 0.60
				life 0.09
				scalerate 12.00
				velocity 33.00
				offsetalongaxis 4 0 0
				fade
				randomroll
			)
			entry tagspawnlinked tag_barrel
			(
				spawnrate 1.00
				model muzsprite.spr
				color 1.00 1.00 1.00
				scale 0.60
				life 0.10
				scalerate 3.00
				velocity 40.00
				offsetalongaxis 5 0 0
				randomroll
			)
			entry commanddelay 0.010 originspawn
			(
				model vsssource.spr
				count 5
				alpha 0.30
				color 1.00 1.00 1.00
				spritegridlighting
				scale 0.70
				life 0.50
				scalerate 6.00
				cone 6.00 2.00
				velocity 320.00
				radialvelocity 11.00 60.00 120.00
				accel 0.00 0.00 -30.00
				friction 5.00
				offset crandom -5 crandom -5 crandom -5
				offsetalongaxis 30 0 0
				fade
				randomroll
			)
		}
	}
}

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
