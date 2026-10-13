// TEST ONLY (rainfix_2026-10-13): the shipped coop_rain.shader with the depth test switched OFF in every stage
// HZM coop [bug-3529] the twelve rain streak images had no shader, so the engine drew them as 2D pictures:
// no depth test, rain through every wall. Same blend as before, depth-tested.

textures/rain0
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain0.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain1
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain1.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain2
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain2.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain3
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain3.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain4
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain4.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain5
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain5.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain6
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain6.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain7
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain7.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain8
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain8.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain9
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain9.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain10
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain10.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}

textures/rain11
{
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull none
	{
		map textures/rain11.tga
		blendFunc blend
		noDepthTest
		rgbGen vertex
		alphaGen vertex
	}
}
