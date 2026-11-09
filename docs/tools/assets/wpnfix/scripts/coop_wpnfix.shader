// [v1.10.64 wpnfix] zzzzzzzzzzzzzzzz_coop_wpnfix.pk3 - shader overrides that must win over every coop pak (gen_wpnfix_pak.py)

// The Mills bomb drew solid BLACK in every menu preview (Armory hero, attic weapon viewer): its sheet
// (textures/models/weapons/mills_grenade, pak1 and the dds_override upscale) carries an alpha channel that is ~0
// over 99.95 % of the texels. Same stage, same lighting, on an RGB copy of the upscaled sheet (alpha 1 everywhere).
mills_grenade
{
	qer_editorimage textures/models/weapons/coop_mills_grenade.jpg
	{
		map textures/models/weapons/coop_mills_grenade.jpg
		rgbGen lightingSpherical
	}
}

// [v1.10.66 fg42hd] the FG 42 Irons' new sheet: Shorty_Digitan's FG42 (CC BY 4.0, modified), PBR baked to one diffuse
coop_fg42hd
{
	qer_editorimage textures/models/weapons/coop_fg42hd/fg42hd.jpg
	{
		map textures/models/weapons/coop_fg42hd/fg42hd.jpg
		rgbGen lightingSpherical
	}
}
