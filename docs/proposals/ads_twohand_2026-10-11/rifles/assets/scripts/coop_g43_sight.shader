// HZM coop [rifle lane 2026-10-12] iron-sight G43 (tools/g43irons.py): the tangent sight's notch plate and the front
// post, dark steel on every finish. rgbGen lightingSpherical is what every model shader of the mod uses (lightingDiffuse
// draws BLACK on a model in this engine, bug-3696); the unlit floor keeps the sights from going black in a dark room.
// rgbGen const takes three bare numbers - NO parentheses (bug-1913).
coop_g43_sight
{
	{
		map textures/coop_wpn/g43_sight.tga
		rgbGen const 0.30 0.30 0.30
	}
	{
		map textures/coop_wpn/g43_sight.tga
		blendFunc add
		rgbGen lightingSpherical
	}
}
