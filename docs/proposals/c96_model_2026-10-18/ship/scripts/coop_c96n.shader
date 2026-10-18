// HZM coop: Mauser C96 (model "Mauser C96" by no12u, Sketchfab, CC BY 4.0) - base sheet + the finish set (tools/finishes.py)
// NEW names, defined in this one file only (TRAPS T6)

coop_c96n
{
	qer_editorimage textures/models/weapons/coop_c96n/coop_c96n.jpg
	{
		map textures/models/weapons/coop_c96n/coop_c96n.jpg
		rgbGen lightingSpherical
	}
}

coop_c96n_gold
{
	qer_editorimage textures/models/weapons/coop_c96n/coop_c96n.jpg
	{
		map textures/models/weapons/coop_c96n/coop_c96n.jpg
		rgbGen lightingSpherical
	}
	{
		map $whiteimage
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen const 1.00 0.78 0.30
	}
	{
		map textures/coop_skins/env_sheen.tga
		blendFunc add
		tcGen environment
		rgbGen const 0.40 0.31 0.12
	}
}

coop_c96n_chrome
{
	qer_editorimage textures/models/weapons/coop_c96n/coop_c96n.jpg
	{
		map textures/models/weapons/coop_c96n/coop_c96n.jpg
		rgbGen lightingSpherical
	}
	{
		map $whiteimage
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen const 0.88 0.92 0.98
	}
	{
		map textures/coop_skins/env_sheen.tga
		blendFunc add
		tcGen environment
		rgbGen const 0.55 0.58 0.64
	}
}

coop_c96n_blued
{
	qer_editorimage textures/models/weapons/coop_c96n/coop_c96n.jpg
	{
		map textures/models/weapons/coop_c96n/coop_c96n.jpg
		rgbGen lightingSpherical
	}
	{
		map $whiteimage
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen const 0.44 0.48 0.64
	}
	{
		map textures/coop_skins/env_sheen.tga
		blendFunc add
		tcGen environment
		rgbGen const 0.10 0.12 0.20
	}
}

coop_c96n_bloody
{
	qer_editorimage textures/models/weapons/coop_c96n/coop_c96n_bloody.jpg
	{
		map textures/models/weapons/coop_c96n/coop_c96n_bloody.jpg
		rgbGen lightingSpherical
	}
}

coop_c96n_camo_woodland
{
	qer_editorimage textures/models/weapons/coop_c96n/coop_c96n_camo_woodland.jpg
	{
		map textures/models/weapons/coop_c96n/coop_c96n_camo_woodland.jpg
		rgbGen lightingSpherical
	}
}

coop_c96n_camo_winter
{
	qer_editorimage textures/models/weapons/coop_c96n/coop_c96n_camo_winter.jpg
	{
		map textures/models/weapons/coop_c96n/coop_c96n_camo_winter.jpg
		rgbGen lightingSpherical
	}
}

coop_c96n_camo_desert
{
	qer_editorimage textures/models/weapons/coop_c96n/coop_c96n_camo_desert.jpg
	{
		map textures/models/weapons/coop_c96n/coop_c96n_camo_desert.jpg
		rgbGen lightingSpherical
	}
}
