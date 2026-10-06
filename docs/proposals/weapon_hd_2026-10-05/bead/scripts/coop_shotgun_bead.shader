// Front brass bead for the M1897 shotgun (ADS sight aid, user-approved via the coordinator 2026-10-05).
// Stage 1: aged brass, lit like the rest of the gun. Stage 2: a faint glint from the shared finish sphere map
// (textures/coop_skins/env_sheen.tga, coop tex pak) so the bead reads against dark backgrounds without glowing.
// rgbGen const takes three bare numbers - NO parentheses (bug-1913: "(" parses as 0).
coop_shotgun_bead
{
	{
		map textures/coop_wpn/shotgun_bead.tga
		rgbGen lightingDiffuse
	}
	{
		map textures/coop_skins/env_sheen.tga
		blendFunc add
		tcGen environment
		rgbGen const 0.14 0.11 0.05
	}
}
