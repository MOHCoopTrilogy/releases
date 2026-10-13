// HZM coop [heavy lane 2026-10-13] iron-sight FG 42 (tools/fg42irons.py): the rear aperture sight and the front
// post (both raised), dark steel on every finish. rgbGen lightingSpherical is what every model shader of the mod uses (lightingDiffuse
// draws BLACK on a model in this engine, bug-3696); the unlit floor keeps the sights from going black in a dark room.
// rgbGen const takes three bare numbers - NO parentheses (bug-1913).
coop_fg42_sight
{
	cull none
	{
		map textures/coop_wpn/fg42_sight.tga
		rgbGen const 0.30 0.30 0.30
	}
	{
		map textures/coop_wpn/fg42_sight.tga
		blendFunc add
		rgbGen lightingSpherical
	}
}
