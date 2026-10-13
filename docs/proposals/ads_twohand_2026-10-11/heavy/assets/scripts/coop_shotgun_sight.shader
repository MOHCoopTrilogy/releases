// HZM coop [heavy lane 2026-10-13] M1897 shotgun sights (tools/stage_sgsight.py): brass front bead + the receiver's
// matted sighting groove. rgbGen const takes three bare numbers - NO parentheses (bug-1913: "(" parses as 0).
// rgbGen lightingSpherical is what every model shader of the mod uses; lightingDiffuse draws BLACK on a model in this
// engine (bug-3681's dark bead, run hj3's black groove).
// The bead: an unlit floor so it never goes black in a dark room, the lit part on top, a glint from the shared
// finish sphere map (textures/coop_skins/env_sheen.tga, coop tex pak).
coop_shotgun_bead
{
	{
		map textures/coop_wpn/shotgun_bead.tga
		rgbGen const 0.28 0.28 0.28
	}
	{
		map textures/coop_wpn/shotgun_bead.tga
		blendFunc add
		rgbGen lightingSpherical
	}
	{
		map textures/coop_skins/env_sheen.tga
		blendFunc add
		tcGen environment
		rgbGen const 0.22 0.17 0.07
	}
}

coop_shotgun_groove
{
	{
		map textures/coop_wpn/shotgun_groove.tga
		rgbGen lightingSpherical
	}
}
