"""eadawn_sky.py: the night-to-dawn sky layers for a converted European Assault night level (user request 2026-11-22,
Dying Breath: "can we make it go from night to day ... end up fighting early in the morning with the sun rising").

NOT disc data: every texel is computed here from a small analytic sky (zenith / horizon gradient, a sun-side glow and a
sun disc), so the layers carry nothing from the original. The converter (flconvert.py, sky block) writes them as
textures/<game>/<level>/dawn_<name>.tga and adds one stage per layer to the level's sky shader, drawn over the night
box in order, each blended in over its own window of the dawn progress p:

	alphaGen oneMinusSkyAlpha <lo> <hi>      (p = 1 - $world skyalpha; renderer dawn-eng, gl1 and gl2)

coop_mod/eadawn.scr moves $world skyalpha from 1 (night, the original; also the engine's default, so a server with the
dawn off shows exactly the converted night) to 0 over the mission's elapsed time.

The stages draw on the sky DOME (skyParms cloud height), whose texture coordinates are the engine's R_InitSkyTexCoords
s = acos(v.x), t = acos(v.y) in radians, v the unit vector from the "planet" centre (radius 4096, eye on top) to the
dome point at the cloud height. The texture is laid out in that space after the stage's own
	tcMod transform K 0 0 K T T          (s' = K s + T, centred on the zenith s = t = pi / 2)
and each texel is mapped back to a view direction, so the layer is exact in elevation and azimuth.

build(cfg) -> {"name": (w, h, rgba bytes, lo, hi)}, plus shader_stages(game, level, cfg) for the shader text.
"""
import math

R_WORLD = 4096.0        # tr_sky.c R_InitSkyTexCoords radiusWorld
SIZE = 1024
SPAN = 0.62             # +-SPAN radians of s / t round pi/2 fill the texture: the horizon sits at +-0.476, -6 deg at +-0.6; clampmap repeats the edge below that
K = 0.5 / SPAN
T = 0.5 - K * math.pi / 2

# the layers, drawn in this order (each covers the one before as it comes in). Colours are LINEAR-ish texture values
# before the map grade; eadawn.scr's fog keyframes match each layer's horizon at the layer's window end.
#   zen / hor : zenith and horizon colour; hs : the elevation scale (deg) of the gradient
#   glow      : sun-side horizon glow colour, its strength, its azimuth width (deg) and height (deg)
#   halo      : the bright ring round the sun: colour, strength, angular width (deg)
#   sun       : disc elevation (deg), radius (deg), colour; None = below the horizon
DEFAULT_LAYERS = [
    {"name": "bluehour", "lo": 0.00, "hi": 0.30,
     "zen": (0.030, 0.042, 0.095), "hor": (0.190, 0.220, 0.280), "hs": 22.0,
     "glow": ((0.42, 0.27, 0.22), 0.55, 55.0, 7.0), "halo": None, "sun": None},
    {"name": "sunrise", "lo": 0.30, "hi": 0.50,
     "zen": (0.090, 0.130, 0.250), "hor": (0.270, 0.250, 0.270), "hs": 18.0,
     "glow": ((0.95, 0.50, 0.24), 0.85, 45.0, 8.0), "halo": ((1.0, 0.62, 0.30), 0.6, 7.0),
     "sun": (0.35, 0.75, (1.0, 0.55, 0.28))},
    {"name": "sunup", "lo": 0.54, "hi": 0.72,
     "zen": (0.130, 0.200, 0.340), "hor": (0.340, 0.320, 0.320), "hs": 16.0,
     "glow": ((1.0, 0.68, 0.40), 0.70, 50.0, 10.0), "halo": ((1.0, 0.80, 0.55), 0.7, 6.0),
     "sun": (2.0, 0.75, (1.0, 0.80, 0.55))},
    {"name": "morning", "lo": 0.76, "hi": 0.96,
     "zen": (0.170, 0.260, 0.420), "hor": (0.380, 0.400, 0.430), "hs": 15.0,
     "glow": ((1.0, 0.86, 0.66), 0.45, 60.0, 12.0), "halo": ((1.0, 0.93, 0.80), 0.8, 5.0),
     "sun": (4.0, 0.75, (1.0, 0.96, 0.86))},
]


def dirs(size=SIZE, cloud=512.0):
    """per texel: (elevation rad, azimuth yaw rad, valid) of the view direction the dome shows there"""
    import numpy as np
    c = (np.arange(size) + 0.5) / size
    s = (c - T) / K                              # radians, texture u
    t = (c - T) / K                              # radians, texture v (row 0 = t' 0)
    vx = np.cos(s)[None, :]
    vy = np.cos(t)[:, None]
    r2 = vx * vx + vy * vy
    ok = r2 < 1.0
    vz = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))
    rc = R_WORLD + cloud
    px, py, pz = vx * rc, vy * rc, vz * rc - R_WORLD
    n = np.sqrt(px * px + py * py + pz * pz) + 1e-9
    elev = np.arcsin(np.clip(pz / n, -1.0, 1.0))
    yaw = np.arctan2(py, px)
    return elev, yaw, ok


def _layer(L, elev, yaw, ok, sun_yaw):
    import numpy as np
    ed = np.degrees(elev)
    eu = np.clip(ed, 0.0, 90.0)
    f = 1.0 - np.exp(-eu / L["hs"])               # 0 at the horizon -> 1 at the zenith
    zen, hor = np.array(L["zen"]), np.array(L["hor"])
    col = hor[None, None, :] * (1.0 - f[..., None]) + zen[None, None, :] * f[..., None]
    # azimuth from the sun, degrees (0 = toward the sun)
    da = np.degrees(np.abs((yaw - math.radians(sun_yaw) + math.pi) % (2 * math.pi) - math.pi))
    if L.get("glow"):
        gc, gs, gw, gh = L["glow"]
        g = gs * np.exp(-(da / gw) ** 2) * np.exp(-eu / gh)
        col = col + (np.array(gc)[None, None, :] - col) * np.clip(g, 0, 1)[..., None]
    sun = L.get("sun")
    if sun is not None:
        se, sr, sc = sun
        sd = np.array([math.cos(math.radians(se)) * math.cos(math.radians(sun_yaw)),
                       math.cos(math.radians(se)) * math.sin(math.radians(sun_yaw)), math.sin(math.radians(se))])
        vd = np.stack([np.cos(elev) * np.cos(yaw), np.cos(elev) * np.sin(yaw), np.sin(elev)], -1)
        gam = np.degrees(np.arccos(np.clip(vd @ sd, -1.0, 1.0)))
        if L.get("halo"):
            hc, hs_, hw = L["halo"]
            h = hs_ * np.exp(-gam / hw)
            col = col + (np.array(hc)[None, None, :] - col) * np.clip(h, 0, 1)[..., None]
        disc = np.clip((sr - gam) / 0.12 + 0.5, 0.0, 1.0)      # ~0.12 deg soft limb
        col = col + (np.array(sc)[None, None, :] - col) * disc[..., None]
    # below the horizon: the horizon colour, a touch darker toward the ground (the fog hides it in play)
    below = np.clip(-ed / 12.0, 0.0, 1.0)[..., None]
    col = col * (1.0 - 0.25 * below)
    col = np.where(ok[..., None], col, hor[None, None, :] * 0.75)
    return np.clip(col, 0.0, 1.0)


def build(cfg=None, size=SIZE, cloud=512.0):
    """{name: (w, h, rgba bytes, lo, hi)} - rows top-down (t' = 0 first), alpha 255"""
    import numpy as np
    cfg = cfg or {}
    sun_yaw = float(cfg.get("sun_yaw", 70.0))
    layers = cfg.get("layers") or DEFAULT_LAYERS
    elev, yaw, ok = dirs(size, cloud)
    out = {}
    rng = np.random.default_rng(1943)
    for L in layers:
        c = _layer(L, elev, yaw, ok, sun_yaw)
        # 1/2-LSB dither so the long, dark gradients do not band in 8 bits
        c = c * 255.0 + rng.uniform(-0.5, 0.5, c.shape)
        a = np.full(c.shape[:2] + (1,), 255.0)
        px = np.concatenate([np.clip(np.round(c), 0, 255), a], -1).astype(np.uint8)
        out[L["name"]] = (size, size, px.tobytes(), float(L["lo"]), float(L["hi"]))
    return out


def shader_stages(game, level, layers):
    """the dawn stages for the sky shader: one per layer, over the night box, fog-free like it"""
    st = ""
    for name, (_w, _h, _px, lo, hi) in layers.items():
        st += ("\t{\n\t\tclampmap textures/%s/%s/dawn_%s.tga\n\t\tblendFunc blend\n\t\ttcMod transform %.6f 0 0 %.6f %.6f %.6f\n"
               "\t\trgbGen identity\n\t\talphaGen oneMinusSkyAlpha %.3f %.3f\n\t\tnofog\n\t}\n"
               % (game, level, name, K, K, T, T, lo, hi))
    return st


def cloud_dawn_stages(game, level, cloud_layers, cfg=None):
    """the original's cloud layers again, lit by the morning (warm grey), coming in over the night-tinted ones"""
    cfg = cfg or {}
    rgb = cfg.get("cloud_rgb", (0.62, 0.55, 0.52))
    lo, hi = cfg.get("cloud_window", (0.30, 0.85))
    st = ""
    for cl in cloud_layers:
        # [0.7.59] the layer's elevation fade (easky.cloud_fade) as its last tcMod, like the night layer
        fd = ("\t\ttcMod hzmSkyFade %s\n" % " ".join("%g %g" % k_ for k_ in cl["fade"])) if cl.get("fade") else ""
        st += ("\t{\n\t\tmap textures/%s/%s/sky_clouds.tga\n\t\tblendFunc blend\n\t\ttcMod scale %g %g\n"
               "\t\ttcMod scroll %g %g\n%s\t\trgbGen const %g %g %g\n\t\talphaGen oneMinusSkyAlpha %.3f %.3f\n\t\tnofog\n\t}\n"
               % (game, level, cl["scale"], cl["scale"], cl["scroll"][0], cl["scroll"][1], fd, rgb[0], rgb[1], rgb[2], lo, hi))
    return st


if __name__ == "__main__":
    # preview: python -I eadawn_sky.py <out_dir> [sun_yaw]  -> one PNG per layer, plus a test layer with yaw marks
    import os
    import sys
    from PIL import Image
    od = sys.argv[1]
    os.makedirs(od, exist_ok=True)
    cfg = {"sun_yaw": float(sys.argv[2])} if len(sys.argv) > 2 else {}
    for n, (w, h, px, lo, hi) in build(cfg, size=512).items():
        Image.frombytes("RGBA", (w, h), px).convert("RGB").save(os.path.join(od, "dawn_%s.png" % n))
        print(n, lo, hi)
