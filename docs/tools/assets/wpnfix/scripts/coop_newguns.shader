// HZM coop [newguns 2026-11-09] shaders of the new CC-model guns (docs/proposals/newguns_2026-11-09)

// [newguns 2026-11-09] the Bren Mk I's sheet: maximiliaanmaene's Bren Mk1 LMG (CC BY 4.0, modified), PBR baked to one diffuse
coop_bren
{
	qer_editorimage textures/models/weapons/coop_bren/bren.jpg
	{
		map textures/models/weapons/coop_bren/bren.jpg
		rgbGen lightingSpherical
	}
}

// [newguns 2026-11-09] the MP 28's sheet: BrendanStakenburg's MP-28 (CC BY 4.0, modified), PBR baked to one diffuse
coop_bergmann
{
	qer_editorimage textures/models/weapons/coop_bergmann/mp28.jpg
	{
		map textures/models/weapons/coop_bergmann/mp28.jpg
		rgbGen lightingSpherical
	}
}

// [newguns 2026-11-09] the Panzerfaust 60's sheet: marcusww's Panzerfaust 60 (CC BY 4.0, modified), PBR baked to one diffuse
coop_panzerfaust
{
	qer_editorimage textures/models/weapons/coop_panzerfaust/pzf.jpg
	{
		map textures/models/weapons/coop_panzerfaust/pzf.jpg
		rgbGen lightingSpherical
	}
}

// [newguns2 2026-11-09] the Bren's rebuilt sights (drum bracket, arm, aperture leaf, blade, ears, bracket): their own sheet,
// the Bren sheet's parkerized steel with edge wear (bren_sights.texture). The skd surface `coop_bren_sight` has no tik line,
// so every Bren tik (finishes included) draws it with this shader: the sights stay plain steel
coop_bren_sight
{
	qer_editorimage textures/models/weapons/coop_bren/bren_sight.jpg
	{
		map textures/models/weapons/coop_bren/bren_sight.jpg
		rgbGen lightingSpherical
	}
}
