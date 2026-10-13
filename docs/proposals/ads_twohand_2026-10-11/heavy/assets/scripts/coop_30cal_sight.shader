// HZM coop [heavy lane 2026-10-13] M1919 .30 cal (tools/m1919sights.py): the rear leaf's notch slider and the front
// blade, dark steel. rgbGen lightingSpherical is what every model shader of the mod uses (lightingDiffuse
// draws BLACK on a model in this engine, bug-3696); the unlit floor keeps the sights from going black in a dark room.
// rgbGen const takes three bare numbers - NO parentheses (bug-1913).
coop_30cal_sight
{
	cull none
	{
		map textures/coop_wpn/30cal_sight.tga
		rgbGen const 0.30 0.30 0.30
	}
	{
		map textures/coop_wpn/30cal_sight.tga
		blendFunc add
		rgbGen lightingSpherical
	}
}
