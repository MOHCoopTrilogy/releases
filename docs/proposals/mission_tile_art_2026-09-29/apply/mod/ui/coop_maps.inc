//[202][hotfix] chrissstrahl - added hzm coop mod logo
resource
Widget
{
	name "coop_startServerLogo"
	rect 190 130 256 256
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	shader "textures/mohmenu/coop/hzm_coop_mod_logo"
}

resource
Label
{
	title "1. Select a Mission\n2. Select a Map\n3. Click Apply"
	name "coop_startMapSelect"
	rect 50 200 400 300
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign left
}

//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC1"
	rect 10 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt1_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS1"
	rect 10 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt1_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap1"
	rect 10 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}
//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC2"
	rect 114 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt2_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS2"
	rect 114 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt2_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap2"
	rect 114 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}
//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC3"
	rect 218 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt3_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS3"
	rect 218 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt3_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap3"
	rect 218 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}
//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC4"
	rect 322 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt4_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS4"
	rect 322 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt4_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap4"
	rect 322 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}
//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC5"
	rect 426 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt5_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS5"
	rect 426 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt5_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap5"
	rect 426 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}
//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC6"
	rect 530 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt6_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS6"
	rect 530 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt6_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap6"
	rect 530 138 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}
//second row
//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC7"
	rect 10 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt7_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS7"
	rect 10 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt7_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap7"
	rect 10 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}
//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC8"
	rect 114 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt8_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS8"
	rect 114 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt8_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap8"
	rect 114 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}
//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC9"
	rect 218 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt9_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS9"
	rect 218 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt9_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap9"
	rect 218 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}
//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC10"
	rect 322 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt10_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS10"
	rect 322 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt10_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap10"
	rect 322 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}
//[mission tile art] the tile's art, one Label per menu layout; the Button below stays the click target
resource
Label
{
	name "coop_tileArtC11"
	rect 426 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt11_c"
	linkcvartoshader
	enabledcvar "ui_menuCenter"
}
resource
Label
{
	name "coop_tileArtS11"
	rect 426 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.00 0.00 0.00 0.00
	borderstyle "NONE"
	linkcvar "coop_tileArt11_s"
	linkcvartoshader
	enabledcvar "!ui_menuCenter"
}
resource
Button
{
	title ""
	name "coop_startMap11"
	rect 426 258 100 100
	fgcolor 1.00 1.00 1.00 1.00
	bgcolor 0.50 0.50 0.50 0.00
	borderstyle "NONE"
	font facfont-20
	textalign center
}

