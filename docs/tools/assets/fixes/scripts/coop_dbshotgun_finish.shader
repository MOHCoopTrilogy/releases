// HZM coop: double-barrel shotgun - the FINISH SET (tools/dbs_finish.py; the mod's recipe, gen_skins.py)
// NEW names, defined in this one file only (TRAPS T6)

coop_dbshotgun_gold
{
	qer_editorimage textures/models/weapons/coop_dbshotgun/coop_dbshotgun.jpg
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun.jpg
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
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun_fmask.jpg
		blendFunc GL_DST_COLOR GL_ZERO
	}
}

coop_dbshotgun_chrome
{
	qer_editorimage textures/models/weapons/coop_dbshotgun/coop_dbshotgun.jpg
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun.jpg
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
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun_fmask.jpg
		blendFunc GL_DST_COLOR GL_ZERO
	}
}

coop_dbshotgun_blued
{
	qer_editorimage textures/models/weapons/coop_dbshotgun/coop_dbshotgun.jpg
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun.jpg
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
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun_fmask.jpg
		blendFunc GL_DST_COLOR GL_ZERO
	}
}

coop_dbshotgun_bloody
{
	qer_editorimage textures/models/weapons/coop_dbshotgun/coop_dbshotgun_bloody.jpg
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun_bloody.jpg
		rgbGen lightingSpherical
	}
}

coop_dbshotgun_camo_woodland
{
	qer_editorimage textures/models/weapons/coop_dbshotgun/coop_dbshotgun_camo_woodland.jpg
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun_camo_woodland.jpg
		rgbGen lightingSpherical
	}
}

coop_dbshotgun_camo_winter
{
	qer_editorimage textures/models/weapons/coop_dbshotgun/coop_dbshotgun_camo_winter.jpg
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun_camo_winter.jpg
		rgbGen lightingSpherical
	}
}

coop_dbshotgun_camo_desert
{
	qer_editorimage textures/models/weapons/coop_dbshotgun/coop_dbshotgun_camo_desert.jpg
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun_camo_desert.jpg
		rgbGen lightingSpherical
	}
}
