"""[eaguns] European Assault disc guns - the converter stage (runs on the PLAYER's PC). The EA twin of frontline/flguns.py.

The Frontline gun converter is reused as is: flgunsight solves the sight points from the ship-safe spec table
(frontline/discguns_sights.json, keys ea_*), flgunfit fits the disc mesh onto the base gun's bone block and writes the
skd / tik / shader / tga / wav files, flgunup upscales the textures. This module only adds what is EA-specific:

  * the cut: each gun's best copy (the level whose LEVEL_A.STR carries its highest-resolution textures) read with
    eaprops.read. An EA gun is one rigid mesh with SKIN WEIGHTS on a small per-gun skeleton (bone ids 0..7, no names on
    the disc): the moving parts (bolt, magazine, pump, rocket) ride their own bone. ROLES below says, per gun, which
    bone id is which part (read off the disc's own bind pose by position: a magazine is the bone hanging under the
    receiver, a bolt / cocking handle the one beside or on it). Every triangle goes whole to the bone carrying most of
    its corners, so a part is never torn.
  * the sounds: EA keys every sound by an alias id in SOUND/Audio.ubr (records: sample index, bank, alias); a sample is
    decoded from its bank (scr.abk / L1..L8.abk) with the converter's own vgmstream (subsong = index + 1).
  * GUNS / SOUNDS rows registered into flgunfit (the same row shapes as the Frontline rows).

Output: ONE pak in the home, zzzzzzzzzzzzzzzzzzzz_byo_guns_ea.pk3 with scripts/hzm_adssights_byo_ea.txt (the sight
rows; the engine's guns_ea ownership token). Same determinism rules as flguns (sorted entries, fixed timestamp).

    convert(image, home, mohaa, progress, opts) -> [pak path] or []
    opts: vgm (vgmstream-cli.exe), esrgan (realesrgan-ncnn-vulkan.exe), upscale (default True), keys"""
import os
import shutil
import struct
import tempfile
import zlib

import numpy as np

PAK = "zzzzzzzzzzzzzzzzzzzz_byo_guns_ea.pk3"
ROWS_FILE = "scripts/hzm_adssights_byo_ea.txt"

# key (= the sight spec key, "ea_" + the model name without _gun_geo / _geo) -> the disc model, its best copy, the base gun
# and the bone roles. Bone ids are the disc skin's; a bone not listed rides the gun body. hide: bones left out (a
# reload-pose part posed over the gun in the bind pose).
G = {
    "ea_smg_thompson": dict(model="smg_thompson_gun_geo", level="1_1", base="thompsonsmg", name="Thompson (European Assault)",
                            roles={"b1": "bolt", "b2": "mag"}),
    "ea_mg_bar": dict(model="mg_bar_gun_geo", level="1_21", base="bar", name="BAR (European Assault)",
                      roles={"b1": "bolt", "b2": "mag"}),
    "ea_smg_mp40": dict(model="smg_mp40_gun_geo", level="1_1", base="mp40", name="MP40 (European Assault)",
                        roles={"b1": "bolt", "b3": "mag"}),
    "ea_mg_stg": dict(model="mg_stg_gun_geo", level="1_15", base="mp44", name="StG 44 (European Assault)",
                      roles={"b3": "bolt", "b4": "mag"}),
    "ea_SMG_PPSH": dict(model="SMG_PPSH_gun_geo", level="1_11", base="ppsh_smg", name="PPSh-41 (European Assault)",
                        roles={"b5": "bolt", "b3": "mag"}),
    "ea_smg_mp28": dict(model="smg_mp28_gun_geo", level="2_59", base="coop_bergmann", name="MP28 (European Assault)",
                        roles={"b2": "bolt", "b1": "mag"}),
    "ea_smg_sten": dict(model="smg_sten_gun_geo", level="2_57", base="sten", stub="sten_mk2s_ea", body="sten_mk2s_ea",
                        name="Sten Mk II(S) (European Assault)", roles={"b1": "bolt", "b2": "mag"}),
    "ea_rifle_m1": dict(model="rifle_m1_gun_geo", level="1_1", base="m1_garand", name="M1 Garand (European Assault)",
                        roles={"b1": "bolt", "b2": "bolt", "b3": "mag", "b4": "mag"}),
    "ea_rifle_karabiner": dict(model="rifle_karabiner_gun_geo", level="1_1", base="kar98", name="Kar98k (European Assault)",
                               roles={"b2": "bolt", "b3": "bolt", "b4": "mag"}),
    "ea_rifle_gewehr": dict(model="rifle_gewehr_gun_geo", level="1_11", base="coop_g43_irons", name="G 43 (European Assault)",
                            roles={"b1": "bolt", "b2": "mag"}),
    "ea_rifle_mn1891": dict(model="rifle_mn1891_gun_geo", level="1_15", base="mosin_nagant_rifle",
                            name="Mosin-Nagant 1891 (European Assault)", roles={"b1": "bolt", "b2": "bolt", "b5": "bolt"}),
    "ea_rifle_shotgun": dict(model="rifle_shotgun_gun_geo", level="1_22", base="shotgun", name="Shotgun (European Assault)",
                             roles={"b1": "pump"}, maxtilt=4.0),     # as Frontline's: the pump fingers stay under the bead
    "ea_PISTOL_45auto": dict(model="PISTOL_45auto_gun_geo", level="1_2", base="colt45", name="Colt 45 (European Assault)",
                             roles={"b1": "bolt", "b2": "mag"}),
    # the scoped rifles: true scale, the fitted glass disc on the disc ocular (the base rifle's tint), slide 0 (eye relief = base)
    "ea_rifle_gewehrScoped": dict(model="rifle_gewehrScoped_gun_geo", level="1_21", base="g43",
                                  name="G 43 Sniper (European Assault)", roles={"b1": "bolt", "b2": "mag"}, glass="blue",
                                  slide=0.0),
    "ea_rifle_m1Scoped": dict(model="rifle_m1Scoped_gun_geo", level="1_22", base="garand_scoped",
                              name="M1 Garand Sniper (European Assault)",
                              roles={"b1": "bolt", "b2": "bolt", "b3": "mag", "b4": "mag"}, glass="blue", slide=0.0),
    # b7: the 5-round charger posed OVER the scope in the bind pose (a reload part) - left out
    "ea_rifle_enfieldScoped": dict(model="rifle_enfieldScoped_gun_geo", level="1_8", base="enfieldsniper",
                                   name="Lee-Enfield No.4 (T) (European Assault)", roles={"b3": "bolt", "b4": "bolt", "b5": "bolt"},
                                   hide=[7], glass="blue", slide=0.0),
    "ea_rifle_mnvp": dict(model="rifle_mnvp_gun_geo", level="2_52", base="nagant_sniper",
                          name="Mosin-Nagant Sniper (European Assault)", roles={"b1": "bolt", "b2": "bolt", "b3": "bolt"},
                          glass="blue", slide=0.0),
    # the launchers: the disc bore on the base bore (sight line VIRTUAL, see discguns_sights.json); the disc ROCKET is the
    # reload shell (role mag -> the base's toggled surface, bazookashell: hidden except while it goes in)
    "ea_misc_M1bazooka": dict(model="misc_M1bazooka_gun_geo", level="1_11", base="bazooka", name="M1 Bazooka (European Assault)",
                              roles={"b2": "mag"}, fit="bore", k=1.0, slide=12.0, snap_mag=True),
    "ea_misc_M9bazooka": dict(model="misc_M9bazooka_gun_geo", level="1_21", base="bazooka", stub="bazooka_ea2",
                              body="bazooka_ea2", name="M9 Bazooka (European Assault)", roles={"b4": "mag"}, fit="bore", k=1.0, snap_mag=True,
                              slide=12.0),
    # the grenades: no sight row, centred on the base grenade (true scale); the frag's whole mesh is the surface the base
    # anims hide after the throw (as Frontline's), the stick grenade's anims use `surface all`
    "ea_grenade_frag": dict(model="grenade_frag_gun_geo", level="1_21", base="m2frag_grenade_sp_start",
                            name="Frag Grenade (European Assault)", roles={"b": "mag"}),
    "ea_grenade_mills": dict(model="grenade_mills_geo", level="1_1", base="mills_grenade_sp_start",
                             name="Mills Bomb (European Assault)", roles={"b": "mag"}),
    "ea_grenade_stick": dict(model="grenade_stick_geo", level="1_15", base="steilhandgranate_start",
                             name="Stielhandgranate (European Assault)"),
}
KEYS = list(G)
ZIP_TIME = (2026, 1, 1, 0, 0, 0)
BANKS = {0x40000000: "SCR.ABK", 1: "L1.ABK", 2: "L2.ABK", 4: "L3.ABK", 8: "L4.ABK", 16: "L5.ABK", 32: "L6.ABK",
         64: "L7.ABK", 128: "L8.ABK"}

# disc sound per base alias slot: (level, [variant, ...]); a variant = [(sample, ms), ...] = the samples EA starts together for
# ONE trigger pull and each one's start offset (ms, guest time) from the first. EA layers every shot (stereo main + mechanism
# + a random tail, the M1 alternates two mains); a MOHAA alias plays one clip, so each variant is BAKED here into one clip at
# the measured offsets, and the variants become <alias>1..<alias>N (the engine picks one at random per shot; names that go
# on with "_" are not in the pick, so <alias>_loaded etc. stay out). sample = the index in the level's SCR.ABK (BNKl table) =
# the vgmstream subsong - 1. level "mp" = the multiplayer bank DATA/2/MPAUDIO.
# Read off the running original (ref_xemu vprobe3, bug-11367): a gdb break on the voice start (0x2F0FEA) gives each voice's
# data ([[voice+0x70]+0xbc], size +0xc0); its first 96 bytes AND its size match exactly one sample channel of the level's
# SCR.ABK; offsets in KeTickCount ms (the guest clock stops at a break). Only the player's own pulls (weapon event 49 of the
# player character) and only layers present on EVERY pull are kept; a gun without an exact match keeps the base sound.
# Measured 2026-11-17 (vprobe3 + p2/ea_layers2, offsets corrected for the break cost; each list = one trigger pull, a sample
# listed twice is started twice together). Levels with the gun in hand at the start: 1_11 PPSh, 1_1 M1, 1_21 BAR, 1_22
# Thompson, 1_8 Enfield No.4 (T), 1_9 shotgun (+ the pickups below). Mono world sounds (impacts, shell casings, other soldiers) are left out.
SOUNDS = {
    # 230 x2 + mech 79, then ONE random tail of 306 / 307 / 308 at +105 ms (7 / 7 pulls)
    "ea_SMG_PPSH": {"ppsh41_snd_fire": ("1_11", [[(230, 0), (230, 0), (79, 0), (t, 105)] for t in (306, 307, 308)])},
    # mains alternate 155 / 156, mech 157 at +160 ms, tail 158 or 159 either with 157 or later (+310): 15 / 15 pulls.
    # 262 = the clip ping (the anim event of M1.aso "Fire"), on the 8th shot only (one clip observed)
    "ea_rifle_m1": {"m1_snd_fire": ("1_1", [[(155, 0), (157, 160), (158, 160)], [(156, 0), (157, 160), (159, 160)],
                                            [(155, 0), (157, 160), (159, 310)], [(156, 0), (157, 160), (158, 310)]]),
                    "snd_ping": ("1_1", [[(262, 0)]])},
    # 280 / 281 (a left / right pair of mono samples) x2 + mech 134, tail 282 / 283 x3 at +305 ms (5 / 5 pulls). A random
    # echo pair (111-116 + 117-120, +160 ms) came on 4 of 5 pulls only: left out
    "ea_mg_bar": {"bar_snd_fire": ("1_21", [[(280, 0), (280, 0), (281, 0), (281, 0), (134, 0)]
                                            + [(282, 305)] * 3 + [(283, 305)] * 3])},
    # 47 + 48 + 51 at 0, then 52 + 301 or 53 + 302 (alternating) with 115 / 116 / 303 / 304 at +110 ms (8 / 8 pulls)
    "ea_smg_thompson": {"thompson_snd_fire": ("1_22", [[(47, 0), (48, 0), (51, 0), (a, 110), (b, 110), (115, 110), (116, 110),
                                                        (303, 110), (304, 110)] for a, b in ((52, 301), (53, 302))])},
    # 145 x2 + 148 at 0, 147 + 47 + 48 at +103, 146 at +95 or +200 (5 / 5); the bolt: 95 at +375, 211 at +823 (5 / 5)
    "ea_rifle_enfieldScoped": {"LeeEnfield_fire": ("1_8", [[(145, 0), (145, 0), (148, 0), (147, 103), (47, 103), (48, 103),
                                                            (146, d)] for d in (95, 200)]),
                               "gen_rifle_bolt": ("1_8", [[(95, 0), (211, 448)]])},
    # 145 x2 at 0, 146 at +87, 147 at +180 or +260 (6 / 6); the pump: 133, then 136 156 ms later (6 / 6). The shot's own event
    # (Audio.ubr 4a8b953e) also carries 151 / 152 / 153 / 154 (mix classes 50c9584e / bab086c4, the same environment layers the
    # BAR and Thompson play): each starts with 146 (+87) or with 147 (+180); the four splits seen over 6 pulls are the variants.
    # The other mono samples (91-107) are the pellets striking the corridor walls (world sounds)
    "ea_rifle_shotgun": {"shotgun_snd_fire": ("1_9", [[(145, 0), (145, 0), (146, 87), (147, d)]
                                                      + [(e, 87) for e in early] + [(e, 180) for e in (151, 152, 153, 154)
                                                                                    if e not in early]
                                                      for d in (180, 260)
                                                      for early in ((152, 153), (151, 152), (), (151, 152, 153, 154))]),
                         "shotgun_snd_rechamber": ("1_9", [[(133, 0), (136, 156)]])},
    # --- pickups (2026-11-22): the level's own WeaponPowerup brought onto the player (ref_xemu ea_pullpu.py), then A / B (swap).
    # These rifles and launchers fire without event 49 on the player character: each pull is anchored on its first stereo voice.
    # G 43 (1_11): 298 + 299 at 0, then 300 + 301 + 155 at +130 ms (7 / 7 pulls); shell casings (41-43, mono) left out
    "ea_rifle_gewehr": {"gewehr43_snd_fire": ("1_11", [[(298, 0), (299, 0), (300, 130), (301, 130), (155, 130)]])},
    # M1 bazooka (1_11): 244 at 0, 243 + 245 + 247 at +128, 246 + 248 at +370 (5 shots, each from the same snapshot); the
    # rocket's impact (265, +1.3 s) left out
    "ea_misc_M1bazooka": {"bazooka_snd_fire": ("1_11", [[(244, 0), (243, 128), (245, 128), (247, 128), (246, 370),
                                                         (248, 370)]])},
    # StG 44 (1_15): 117 + 144 at 0, then 46 with ONE of 92 / 93 / 94 at +207 ms (4 / 4 pulls); 133 (2 of 4) left out
    "ea_mg_stg": {"mp44_snd_fire": ("1_15", [[(117, 0), (144, 0), (46, 207), (t, 207)] for t in (92, 93, 94)])},
    # M9 bazooka (1_21): the trigger click 243 + 247 x2 at 0, the blast 242 + 244 x3 + 246 at +245, 245 + 247 at +490 (3 shots,
    # at the sky and at a wall alike: the blast is the launcher's, not the impact)
    "ea_misc_M9bazooka": {"bazooka_snd_fire": ("1_21", [[(243, 0), (247, 0), (247, 0), (242, 245), (244, 245), (244, 245),
                                                         (244, 245), (246, 245), (245, 490), (247, 490)]])},
    # M1 Garand sniper (1_22): ONE of 105 / 123 / 124 at 0, mech 125 at +147, ONE of 106 / 126 at +300 (6 / 6 pulls); the
    # mono 112-114 (+300..490, one per pull) read as the casing and are left out
    "ea_rifle_m1Scoped": {"wawgarand_fire": ("1_22", [[(m, 0), (125, 147), (t, 300)] for m in (105, 123, 124)
                                                       for t in (106, 126)])},
    # --- STATIC (2026-11-22): guns no probe could hold. The layers are the gun"s own PC events read off Audio.ubr by name
    # (CRC32 "WpnFire_PC_<name>" + "_LP" / "_END", the scheme the 11 probed guns reproduce exactly); shell casings left out as
    # above; a random pick is one variant each. Offsets are NOT measured: each layer"s Delay Min / Max by the fit to the probed
    # guns (0 -> 0 ms, d -> 85 + 11 d ms) and an _END tail 200 ms after the shot (a tap"s release; probed 105-276 ms), the
    # earliest layer moved to 0. MP28 / Sten from DATA/2/MPAUDIO (level "mp", their only bank); the Sten"s event is
    # WpnFire_PC_Sten (no Sten_Silenced event exists on the disc).
    # MP40 (1_1): the event layers are static; the offsets are the ones the probes saw (in hand from its pickup, dg_stn_mp40:
    # 346 +280 after the shot, the _END tail 275 / 276 +273; under the break the MP40 fired erratically, so 1-2 sightings each)
    "ea_smg_mp40": {"mp40_snd_fire": ("1_1", [[(345, 0), (153, 0), (154, 0), (346, 280), (t, 273)] for t in (275, 276)])},
    # Kar98k PROBED (1_2, its pickup, 2 / 2 pulls; the same event WpnFire_PC_Kar98 under 1_2's sample numbers): 75 + 78 at 0,
    # tail 76 + 77 at +210
    "ea_rifle_karabiner": {"kar98_snd_fire": ("1_2", [[(75, 0), (78, 0), (76, 210), (77, 210)]])},
    "ea_PISTOL_45auto": {"colt45_snd_fire": ("1_2", [[(208, 0), (211, 11)], [(209, 0), (211, 11)], [(210, 0), (211, 11)]])},   # WpnFire_PC_Colt_45
    "ea_rifle_mn1891": {"nagantRif_snd_fire": ("1_15", [[(80, 96), (81, 0), (82, 151), (83, 151), (84, 96)]])},   # WpnFire_PC_Moisan
    "ea_rifle_gewehrScoped": {"gewehr43_snd_fire": ("1_21", [[(132, 0), (133, 0), (134, 0), (135, 0), (136, 0), (137, 96), (135, 0), (136, 0), (135, 0), (136, 0)]])},   # WpnFire_PC_Gewehr_Sniper
    "ea_smg_mp28": {"sten_snd_fire": ("mp", [[(155, 0), (72, 96)], [(155, 0)]])},   # WpnFire_PC_MP28
    # --- the grenades' PIN PULL (2026-11-22): EA plays it from the grenade's hand animation, state "Prep" of
    # PlayerWeapons\GRENADE_<x>\<x>Hands.aso (level stream): 12-byte anim sound records [u16 frame][f0ca][alias u32][0] (the same
    # record carries the M1's clip ping 7f95e8f9 at frame 0 of M1.aso Fire, proven by probe). Each event's samples + volume +
    # pitch from Audio.ubr as above; offsets = the record frames at the converter's EA anim rate (eaanim.FPS 30), the first at 0.
    # Frag (1_21, FragHands.aso): 0c64635b f2, 956d32e1 f2, e26a0277 f8, 7c0e97d4 f10
    "ea_grenade_frag": {"m2frag_snd_grenade_pull": ("1_21", [[(49, 0), (a, 0), (b, 200), (256, 267)]
                                                             for a in (277, 278) for b in (36, 35)])},
    # Mills (1_1, BritHands.aso): 067545a0 f2, 9f7c141a f2, e87b248c f8, 761fb12f f24
    "ea_grenade_mills": {"britgrenade_snd_grenade_pull": ("1_1", [[(34, 0), (281, 0), (b, 200), (256, 733)]
                                                                  for b in (151, 150)])},
    # Stielhandgranate (1_11, StickHands.aso): f17d0945 f12, 687458ff f15, 1f736869 f18, 8117fdca f19, f610cd5c f38
    "ea_grenade_stick": {"steilhandgranate_snd_grenade_pull": ("1_11", [[(262, 0), (225, 100), (120, 200), (262, 233),
                                                                         (355, 867)]])},
    "ea_smg_sten": {"sten_silenced": ("mp", [[(137, 0), (74, 0), (75, 96), (138, 0)]])},   # WpnFire_PC_Sten
}
# RELOAD / BOLT / PUMP (2026-11-22): the guns" own animation sound records (PlayerWeapons\<gun>\*.aso in the level stream,
# 12-byte [u16 frame][f0ca][event alias][0]; a state"s records come BEFORE its name - the M1 clip ping sits ahead of
# "FireLast", probe-proven). Per state: every event"s non-foley, non-casing layers, at frame / 30 s (+ the layer"s Delay by the
# fit above); random picks are variants. A slot the stub"s body already defines locally (the *_loaded reloads) gets ONE clip
# under its plain name (an alias name the body also defines would join the random pick). Coverage, see PLAN.md.
RELOADS = {
    "ea_smg_thompson": {
        "thompson_snd_reload": ("1_22", [[(121, 433), (5, 933), (39, 1667), (164, 2067)]]),
        "coop_thompson_snd_reload_loaded": ("1_22", [[(121, 433), (5, 933), (39, 1667), (164, 2067)]]),
    },
    "ea_mg_bar": {
        "bar_snd_reload": ("1_21", [[(145, 600), (342, 1067)]]),
        "bar_snd_reload_loaded": ("1_21", [[(145, 600), (342, 1067)]]),
    },
    "ea_smg_mp40": {
        "mp40_snd_reload": ("1_1", [[(142, 100), (60, 433), (142, 933), (261, 1267), (187, 2167)]]),
        "coop_mp40_snd_reload_loaded": ("1_1", [[(142, 100), (60, 433), (142, 933), (261, 1267), (187, 2167)]]),
    },
    "ea_mg_stg": {
        "mp44_snd_reload": ("1_22", [[(179, 400), (46, 1000), (189, 1933)]]),
        "mp44_snd_reload_loaded": ("1_22", [[(179, 400), (46, 1000), (189, 1933)]]),
    },
    "ea_SMG_PPSH": {
        "ppsh41_snd_reload": ("1_11", [[(174, 433), (341, 600), (312, 1367), (129, 1733), (181, 2633), (343, 3233)]]),
        "coop_ppsh41_snd_reload_loaded": ("1_11", [[(174, 433), (341, 600), (312, 1367), (129, 1733), (181, 2633), (343, 3233)]]),
    },
    "ea_smg_mp28": {
        "sten_snd_reload": ("mp", [[(38, 267), (182, 300), (38, 867), (152, 933), (140, 1167)]]),
        "coop_sten_snd_reload_loaded": ("mp", [[(38, 267), (182, 300), (38, 867), (152, 933), (140, 1167)]]),
    },
    "ea_smg_sten": {
        "sten_snd_reload": ("mp", [[(20, 500), (170, 933), (134, 1333)], [(117, 500), (170, 933), (134, 1333)]]),
        "coop_sten_snd_reload_loaded": ("mp", [[(20, 500), (170, 933), (134, 1333)]]),
    },
    "ea_rifle_m1": {
        "m1_snd_reload": ("1_1", [[(279, 733), (359, 800), (258, 967)]]),
    },
    "ea_rifle_m1Scoped": {
        "m1_snd_reload": ("1_22", [[(150, 733), (132, 800), (234, 967)]]),
    },
    "ea_rifle_karabiner": {
        "kar98_snd_reload": ("1_2", [[(160, 467), (265, 933), (200, 1262), (220, 2040), (200, 2229)]]),
        "kar98_snd_bolt": ("1_2", [[(160, 467), (220, 907)]]),
    },
    "ea_rifle_gewehr": {
        "gewehr43_snd_reload": ("1_11", [[(35, 300), (35, 300), (35, 2433)]]),
    },
    "ea_rifle_gewehrScoped": {
        "gewehr43_snd_reload": ("1_21", [[(50, 300), (279, 467), (200, 1400), (360, 1900), (50, 2433), (307, 2563)]]),
        "coop_gewehr43_snd_reload_loaded": ("1_21", [[(50, 300), (279, 467), (200, 1400), (360, 1900), (50, 2433), (307, 2563)]]),
    },
    "ea_rifle_mn1891": {
        "kar98_snd_bolt": ("1_15", [[(194, 100), (96, 422)], [(194, 100), (95, 422)], [(194, 100), (97, 422)]]),
        "nagantRif_snd_reload": ("1_15", [[(194, 0), (96, 322)], [(194, 0), (95, 322)], [(194, 0), (97, 322)]]),
    },
    "ea_rifle_shotgun": {
        "shotgun_snd_reload_single": ("1_9", [[(289, 100)], [(290, 100)]]),
        "shotgun_snd_reload_end": ("1_9", [[(133, 567), (136, 900)]]),
    },
    "ea_PISTOL_45auto": {
        "colt45_snd_reload": ("1_2", [[(197, 233), (297, 1000), (263, 2007), (170, 2196)]]),
        "colt45_snd_reload_loaded": ("1_2", [[(197, 233), (297, 1000), (263, 2007), (170, 2196)]]),
    },
    "ea_rifle_enfieldScoped": {
        "springfield_snd_reload_start": ("1_8", [[(95, 367), (113, 967), (211, 1674)]]),
    },
    "ea_rifle_mnvp": {
        "WaWnagant_bolt": ("mp", [[(153, 100)]]),
        "kar98sniper_snd_reload_start": ("mp", [[(153, 233)]]),
        "kar98sniper_snd_reload_single": ("mp", [[(157, 0)], [(158, 107)]]),
        "kar98sniper_snd_reload_end": ("mp", [[(107, 362)]]),
    },
    "ea_misc_M9bazooka": {
        "bazooka_snd_reload": ("1_21", [[(153, 0)]]),
    },
}
for _k, _sl in RELOADS.items():
    SOUNDS.setdefault(_k, {}).update(_sl)
# Each layer's own VOLUME and PITCH come from its Audio.ubr record (fields read by name: Volume Min / Max in %, Pitch Min / Max
# in 1/4096; the game picks a random value in each range, the bake uses the middle). EA builds a weapon's event names as
# CRC32("WpnFire_PC_<name>") (+ "_LP" held, "_END" released; XBE sprintf 0x14302c, name table .data 0x377188 - code-decode
# agent 2026-11-22), so the records are looked up in the gun's own events, listed here as those hashes. A sample of a variant
# that none of the gun's events carries keeps 100 % and pitch 1.
EVENTS = {
    "ea_SMG_PPSH": [0xa8fb3cc4, 0x1ec268a5, 0xb0e30b14],         # WpnFire_PC_PPSH_LP, WpnFire_PC_PPSH, the PPSh tail event
    "ea_rifle_m1": [0x2cf5ecd1, 0x7f95e8f9],                      # WpnFire_PC_M1_Garand, the M1.aso Fire (clip ping) event
    "ea_mg_bar": [0xf78cd964],                                    # WpnFire_PC_BAR
    "ea_smg_thompson": [0x0e4eebd3, 0x0c272cb5, 0xc3240e7b],      # WpnFire_PC_Thompson, _LP, _END
    "ea_rifle_enfieldScoped": [0x84d7e9de, 0x25d2163f, 0x745d699d],  # WpnFire_PC_Enfield_Sniper, the bolt events
    "ea_rifle_shotgun": [0x4a8b953e],                             # WpnFire_PC_Shotgun (the pump is in it: 133 / 136)
    "ea_rifle_gewehr": [0xaa38b44b],                              # WpnFire_PC_Gewehr
    "ea_misc_M1bazooka": [0xc9d8e816],                            # WpnFire_PC_Bazooka
    "ea_misc_M9bazooka": [0xc9d8e816],
    "ea_mg_stg": [0xa541f1d8, 0x20e024b5, 0xc308c973],            # WpnFire_PC_StG44, _LP, _END
    "ea_rifle_m1Scoped": [0x2cf5ecd1],                            # WpnFire_PC_M1_Garand
    "ea_smg_mp40": [0xc8d3e389, 0x2b6be2e4, 0xdf6f23d7],          # WpnFire_PC_MP40, _LP, _END
    "ea_rifle_karabiner": [0x0cae9f2b],                           # WpnFire_PC_Kar98
    "ea_PISTOL_45auto": [0x48530188],                             # WpnFire_PC_Colt_45
    "ea_rifle_mn1891": [0x2cbd97e4],                              # WpnFire_PC_Moisan
    "ea_rifle_gewehrScoped": [0x2467d0b8],                        # WpnFire_PC_Gewehr_Sniper
    "ea_smg_mp28": [0x9052cc3d],                                  # WpnFire_PC_MP28
    "ea_smg_sten": [0x68223dff],                                  # WpnFire_PC_Sten
    "ea_grenade_frag": [0x0c64635b, 0x956d32e1, 0xe26a0277, 0x7c0e97d4],       # FragHands.aso Prep
    "ea_grenade_mills": [0x067545a0, 0x9f7c141a, 0xe87b248c, 0x761fb12f],      # BritHands.aso Prep
    "ea_grenade_stick": [0xf17d0945, 0x687458ff, 0x1f736869, 0x8117fdca, 0xf610cd5c],  # StickHands.aso Prep
}
# the reload / bolt / pump states' own events (the hand / gun anim records above)
for _k, _hs in {
    "ea_smg_thompson": [0x98487620, 0x0141279a, 0x7646170c, 0xe82282af],
    "ea_mg_bar": [0x2d75e3d4, 0xc41646e1],
    "ea_smg_mp40": [0x230cb156, 0xba05e0ec, 0xcd02d07a, 0x536645d9],
    "ea_mg_stg": [0xa1604ac2, 0x628ca299, 0x64772c69],
    "ea_SMG_PPSH": [0x581a10a1, 0xc113411b, 0xb614718d, 0x2870e42e, 0x5f77d4b8, 0xc67e8502],
    "ea_smg_mp28": [0x0874bf32, 0x917dee88, 0xe67ade1e, 0x781e4bbd],
    "ea_smg_sten": [0x3b023004, 0xd50c5128, 0x4b68c48b],
    "ea_rifle_m1": [0x919b89d5, 0xe69cb943, 0x78f82ce0],
    "ea_rifle_m1Scoped": [0x919b89d5, 0xe69cb943, 0x78f82ce0],
    "ea_rifle_karabiner": [0x1aa3ec84, 0xf9efa08e, 0x412f7f6f, 0x4c4eab5c],
    "ea_rifle_gewehr": [0xc2587ffb],
    "ea_rifle_gewehrScoped": [0x189dd9ce, 0x977eeba8, 0x5ef2bcf7, 0xff10e740, 0xb5d4af15],
    "ea_rifle_mn1891": [0x67388582],
    "ea_rifle_shotgun": [0xd6b3b6e1, 0x3fd013d4, 0x48d72342],
    "ea_PISTOL_45auto": [0x3ac77b35, 0xa3ce2a8f, 0xd4c91a19, 0x4aad8fba],
    "ea_rifle_enfieldScoped": [0x25d2163f, 0x3eb10c31, 0x745d699d],
    "ea_rifle_mnvp": [0x67388582, 0x6c21e33e, 0x24bb455b],
    "ea_misc_M9bazooka": [0x3c56ee92],
}.items():
    EVENTS[_k] = EVENTS.get(_k, []) + [_h for _h in _hs if _h not in EVENTS.get(_k, [])]
BASE_SND = {
    "ppsh41_snd_fire": ("sound/weapons/fire/wpnfire_PPSH_SMG02.wav", "1.82 0.01 0.95 0.1 480 8000 weapon"),
    "LeeEnfield_fire": ("sound/weapons/fire/LeeEnfield_fire.wav", "1.7 0.1 1.0 0.0 400 8000 weapon"),
    "wawgarand_fire": ("sound/weapons/fire/WAWgarand_fire.wav", "3.3 0.2 1.0 0.0 400 8000 weapon"),
    "kar98_snd_fire": ("sound/weapons/fire/Mauser98Fire1.wav", "1.22 0.1 0.8 0.1 480 8000 weapon"),
    "nagantRif_snd_fire": ("sound/weapons/fire/wpnfire_NagantRiffle_2.wav", "1.56 0.1 1.0 0.1 480 8000 weapon"),
    "sten_snd_fire": ("sound/weapons/fire/wpnfire_sten02.wav", "1.82 0.01 0.95 0.1 480 8000 weapon"),
    "sten_silenced": ("sound/weapons/fire/sten_silenced.wav", "1.4 0.1 1.0 0.0 400 8000 weapon"),
    "m2frag_snd_grenade_pull": ("sound/weapons/foley/Grenade_Pull.wav", "1.0 0.2 0.98 0.2 160 1000 weapon"),
    "britgrenade_snd_grenade_pull": ("sound/weapons/foley/wpn_Mills_pinpull.wav", "0.9 0.2 1.0 0.05 160 1000 weapon"),
    "steilhandgranate_snd_grenade_pull": ("sound/weapons/fire/Grenade_Pull.wav", "1.17 0.2 0.8 0.2 480 1000 weapon"),
    "thompson_snd_reload": ("sound/weapons/foley/ThompsonReload1a.wav", "0.9 0.2 0.95 0.1 160 1000 item"),
    "coop_thompson_snd_reload_loaded": ("sound/weapons/foley/coop_thompson_snd_reload_loaded.wav", "1.5 0.0 1.0 0.05 160 1000 item"),
    "bar_snd_reload": ("sound/weapons/foley/BARReload1.wav", "0.9 0.2 1.0 0.05 160 1000 auto"),
    "bar_snd_reload_loaded": ("sound/weapons/foley/coop_bar_reload_loaded.wav", "0.9 0.2 1.0 0.0 160 1000 auto"),
    "mp40_snd_reload": ("sound/weapons/foley/MP40Reload1a.wav", "1.5 0.0 1.0 0.05 160 1000 item"),
    "coop_mp40_snd_reload_loaded": ("sound/weapons/foley/coop_mp40_snd_reload_loaded.wav", "1.5 0.0 1.0 0.05 160 1000 item"),
    "mp44_snd_reload": ("sound/weapons/foley/MP44Reload1.wav", "0.9 0.2 1.0 0.05 160 1000 item"),
    "mp44_snd_reload_loaded": ("sound/weapons/foley/coop_mp44_reload_loaded.wav", "0.9 0.2 1.0 0.0 160 1000 item"),
    "ppsh41_snd_reload": ("sound/weapons/foley/wpn_PPSH_reload.wav", "1.2 0.2 0.95 0.1 160 1000 item"),
    "coop_ppsh41_snd_reload_loaded": ("sound/weapons/foley/coop_ppsh41_snd_reload_loaded.wav", "1.5 0.0 1.0 0.05 160 1000 item"),
    "sten_snd_reload": ("sound/weapons/foley/wpn_Sten_reload.wav", "1.0 0.1 1.0 0.1 160 1000 item"),
    "coop_sten_snd_reload_loaded": ("sound/weapons/foley/coop_sten_snd_reload_loaded.wav", "1.5 0.0 1.0 0.05 160 1000 item"),
    "m1_snd_reload": ("sound/weapons/foley/m1_reload.wav", "0.9 0.2 0.95 0.1 160 1000 item"),
    "kar98_snd_reload": ("sound/weapons/foley/KARReload1.wav", "1.2 0.1 1.0 0.05 160 1000 item"),
    "kar98_snd_bolt": ("sound/weapons/foley/KARRechamber1.wav", "1.3 0.1 1.0 0.05 160 1000 item"),
    "gewehr43_snd_reload": ("sound/weapons/foley/wpn_G43_reload.wav", "1.0 0.2 0.95 0.1 160 1000 item"),
    "coop_gewehr43_snd_reload_loaded": ("sound/weapons/foley/coop_gewehr43_snd_reload_loaded.wav", "1.5 0.0 1.0 0.05 160 1000 item"),
    "nagantRif_snd_reload": ("sound/weapons/foley/wpn_NagantRif_reload.wav", "1.2 0.1 1.0 0.05 160 1000 item"),
    "colt45_snd_reload": ("sound/weapons/foley/Colt45Reload1b.wav", "0.9 0.2 1.0 0.0 160 1000 item"),
    "colt45_snd_reload_loaded": ("sound/weapons/foley/coop_colt45_reload_loaded.wav", "0.9 0.2 1.0 0.0 160 1000 item"),
    "springfield_snd_reload_start": ("sound/weapons/foley/SpringfieldReloadStart1.wav", "1.3 0.2 1.0 0.0 160 1000 item"),
    "WaWnagant_bolt": ("sound/weapons/foley/KARRechamber1.wav", "9.3 0.1 1.0 0.0 160 1000 item"),
    "kar98sniper_snd_reload_start": ("sound/weapons/foley/KARSniperReloadStart1.wav", "1.3 0.2 1.0 0.0 160 1000 item"),
    "kar98sniper_snd_reload_single": ("sound/weapons/foley/KARSniperReloadFill2.wav", "1.3 0.2 0.92 0.15 160 1000 auto"),
    "kar98sniper_snd_reload_end": ("sound/weapons/foley/KARSniperReloadEnd1.wav", "0.9 0.2 0.95 0.1 160 1000 item"),
    "bazooka_snd_reload": ("sound/weapons/foley/BazookaReload1.wav", "0.9 0.2 1.0 0.0 160 1000 item"),
    "shotgun_snd_reload_end": ("sound/weapons/foley/ShotgunReloadEnd1.wav", "1.5 0.0 0.95 0.1 160 1000 item"),
    # gen_rifle_bolt's own clip is an mp3 (the loudness match reads wav): matched to the Kar98 bolt wav, its own soundparms
    "gen_rifle_bolt": ("sound/weapons/foley/KARRechamber1.wav", "4.3 0.1 1.0 0.0 160 1000 item"),
}


def stub_of(key):
    c = G[key]
    return c.get("stub") or "%s_ea" % c["base"]


def register():
    """the EA rows into flgunfit's tables (the fit / write code reads them by key)"""
    import flgunfit
    for k, c in G.items():
        row = dict(base=c["base"], stub=stub_of(k), name=c["name"], roles=c.get("roles"))
        for o in ("glass", "slide", "fit", "k", "shift", "maxtilt", "keep_base", "drop", "bones", "body", "snap_mag"):
            if o in c:
                row[o] = c[o]
        if "body" not in row:
            row["body"] = stub_of(k)
        flgunfit.GUNS[k] = row
    for k, s in SOUNDS.items():
        flgunfit.SOUNDS[k] = {a: [snd_ref(lv, var, EVENTS.get(k)) for var in vs] for a, (lv, vs) in s.items()}
    flgunfit.BASE_SND.update(BASE_SND)


# ------------------------------------------------------------------ the disc cut
def level_stream(disc, lv):
    return disc.read("DATA/%s/%s/LEVEL_A.STR" % (lv.split("_")[0], lv))


class DiscGuns:
    """the player's EA disc: load(key) -> {"parts": [...], "tex": {name: (w, h, rgba)}} (flguns.DiscGuns shape; part bones
    are "b<disc bone id>")"""

    def __init__(self, disc):
        self.disc = disc
        self._lv = None
        self._d = None

    def _stream(self, lv):
        if self._lv != lv:
            self._d, self._lv = level_stream(self.disc, lv), lv
        return self._d

    def load(self, key):
        import eachar
        import eaprops
        c = G[key]
        d = self._stream(c["level"])
        at = d.find(("__Model:::%s.mesh" % c["model"]).encode())
        typ = None
        for p, cid, t, sz in eachar._chunks(d):
            if p <= at < p + sz:
                typ = t
                break
        m = eaprops.read(d, c["model"], typ) if typ is not None else None
        if not m:
            raise KeyError("%s: %s not on level %s" % (key, c["model"], c["level"]))
        dom = eaprops.dominant_bones(m)
        hide = set(c.get("hide", []))
        parts, texs = [], {}
        for k, (pos, uv, tris, shape) in enumerate(m["meshes"]):
            sh = (shape or "none").split("#")[0]
            im = m["textures"].get(sh)
            if im is None:
                continue
            db = dom[k] or [0] * len(pos)
            V, UV, BN, T, vmap = [], [], [], [], {}
            for tr in tris:
                bs = [db[i] for i in tr]
                b = max(set(bs), key=lambda x: (bs.count(x), -bs.index(x)))
                if b in hide:
                    continue
                t = []
                for i in tr:
                    if (i, b) not in vmap:
                        vmap[(i, b)] = len(V)
                        V.append(pos[i])
                        UV.append(uv[i])
                        BN.append("b%d" % b)
                    t.append(vmap[(i, b)])
                T.append(t)
            if not T:
                continue
            texs[sh] = (im["w"], im["h"], bytes(im["rgba"]))
            parts.append({"tex": sh, "V": np.array(V, float), "UV": np.array(UV, float), "T": np.array(T),
                          "bone": BN})
        return {"parts": parts, "tex": texs}


# ------------------------------------------------------------------ the sounds
def ubr_aliases(ubr):
    """{alias id: [(bank, sample index)]} from a level's Audio.ubr (fields read by name, eapack.sounddefs)"""
    nf, nr, st = struct.unpack_from("<III", ubr, 16)
    off = {}
    for i in range(nf):
        c, t, o = struct.unpack_from("<III", ubr, 32 + 12 * i)
        off[c] = o
    fa = off[zlib.crc32(b"Alias") & 0xffffffff]
    fb = off[zlib.crc32(b"Bank Type") & 0xffffffff]
    fs = off[0xBC1069FF]
    base = 32 + 12 * nf
    out = {}
    for r in range(nr):
        rs = base + r * st
        if rs + st > len(ubr):
            break
        out.setdefault(struct.unpack_from("<I", ubr, rs + fa)[0], []).append(
            (struct.unpack_from("<I", ubr, rs + fb)[0], struct.unpack_from("<H", ubr, rs + fs)[0]))
    return out


def snd_ref(lv, var, events=None):
    """one baked variant as a stable key: "<level>|<event hex>,...|<sample>@<ms>+..." """
    return "%s|%s|%s" % (lv, ",".join("%08x" % e for e in (events or [])), "+".join("%d@%d" % (i, ms) for i, ms in var))


def layer_params(ubr, events):
    """{SCR.ABK sample: [(volume 0..1, pitch), ...]} from the records of the given events, in event then layer order (a sample
    a gun plays twice, e.g. the BAR's 280 on layers 1 and 3, has one entry per layer: the n-th use in a variant takes the n-th),
    the middle of each random range; fields by name (Audio.ubr is self-describing)"""
    nf, nr, st = struct.unpack_from("<III", ubr, 16)
    off = {}
    for i in range(nf):
        c, t, o = struct.unpack_from("<III", ubr, 32 + 12 * i)
        off[c] = o
    crc = lambda n: zlib.crc32(n.encode()) & 0xffffffff
    need = [crc(n) for n in ("Alias", "Bank Type", "Volume Min", "Volume Max", "Pitch Min", "Pitch Max")]
    if any(c not in off for c in need) or 0xBC1069FF not in off:
        return {}
    fa, fb, v0, v1, p0, p1 = (off[c] for c in need)
    fs = off[0xBC1069FF]
    fl = off.get(0xC016BADA)      # the layer number (a byte)
    base = 32 + 12 * nf
    found = {}
    for r in range(nr):
        rs = base + r * st
        if rs + st > len(ubr):
            break
        a = struct.unpack_from("<I", ubr, rs + fa)[0]
        if a not in events or struct.unpack_from("<I", ubr, rs + fb)[0] != 0x40000000:
            continue
        idx = struct.unpack_from("<H", ubr, rs + fs)[0]
        vol = (ubr[rs + v0] + ubr[rs + v1]) / 200.0
        pit = (struct.unpack_from("<H", ubr, rs + p0)[0] + struct.unpack_from("<H", ubr, rs + p1)[0]) / 8192.0
        layer = ubr[rs + fl] if fl is not None else 0
        found.setdefault((events.index(a), layer, r), (idx, vol, pit))
    out = {}
    for _k, (idx, vol, pit) in sorted(found.items()):
        out.setdefault(idx, []).append((vol, pit))
    return out


def _snd_dir(lv):
    return "DATA/2/MPAUDIO/SOUND/" if lv == "mp" else "DATA/%s/%s/SOUND/" % (lv.split("_")[0], lv)


def _wav_f(path):
    import wave
    w = wave.open(path)
    ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    a = np.frombuffer(w.readframes(n), "<i2" if sw == 2 else np.uint8).astype(np.float64)
    if sw == 1:
        a = (a - 128) * 256
    return a.reshape(-1, ch), sr


def bake(parts):
    """[(stereo/mono float array, sr, ms[, volume, pitch])] -> one clip (all at the first part's rate, channel count = the
    widest), every part at its own offset, its record's volume and its pitch (played faster / slower = resampled), summed (the
    loudness match of the whole clip comes after, in flgunfit.sound_files)"""
    sr = parts[0][1]
    nch = max(p[0].shape[1] for p in parts)
    rs = []
    for part in parts:
        a, r, ms = part[:3]
        vol, pit = (part[3], part[4]) if len(part) > 4 else (1.0, 1.0)    # part[5] (the sample index) is bookkeeping only
        step = (r / sr) * pit    # source samples per output sample: the rate change and the record's pitch together
        if abs(step - 1.0) > 1e-9:
            t = np.arange(int(len(a) / step)) * step
            a = np.stack([np.interp(t, np.arange(len(a)), a[:, c]) for c in range(a.shape[1])], 1)
        a = a * vol
        if a.shape[1] < nch:
            a = np.repeat(a, nch, 1)
        rs.append((a, int(round(ms * sr / 1000.0))))
    out = np.zeros((max(len(a) + o for a, o in rs), nch))
    for a, o in rs:
        out[o:o + len(a)] += a
    return out, sr


def decode_sounds(disc, refs, tmp, vgm):
    """refs: {snd_ref} -> {ref: baked wav path}; each sample of a variant decoded from its level's SCR.ABK with the converter's
    vgmstream (subsong = index + 1), then baked at its offsets. {} without vgmstream; a ref whose bank or sample is missing
    is left out (that alias keeps the base sound)."""
    import subprocess
    import wave
    if not vgm or not os.path.exists(vgm):
        return {}
    out, banks, dec, prm = {}, {}, {}, {}
    for ref in sorted(refs):
        lv, evs, body = ref.split("|")
        evs = [int(e, 16) for e in evs.split(",") if e]
        pk = (lv, tuple(evs))
        if pk not in prm:
            try:
                prm[pk] = layer_params(disc.read(_snd_dir(lv) + "AUDIO.UBR"), evs) if evs else {}
            except Exception:
                prm[pk] = {}
        src = os.path.join(tmp, "%s_SCR.ABK" % lv)
        if src not in banks:
            try:
                open(src, "wb").write(disc.read(_snd_dir(lv) + "SCR.ABK"))
                banks[src] = True
            except Exception:
                banks[src] = False
        if not banks[src]:
            continue
        parts = []
        for tok in body.split("+"):
            idx, ms = (int(x) for x in tok.split("@"))
            k = (lv, idx)
            if k not in dec:
                dst = os.path.join(tmp, "%s_scr_%d.wav" % (lv, idx))
                r = subprocess.run([vgm, "-s", str(idx + 1), "-i", "-o", dst, src], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   creationflags=(0x08000000 | 0x00000040) if os.name == "nt" else 0)
                dec[k] = _wav_f(dst) if r.returncode == 0 and os.path.exists(dst) else None
            if dec[k] is None:
                parts = None
                break
            uses = sum(1 for q in parts if q[5] == idx)
            got = prm[pk].get(idx) or [(1.0, 1.0)]
            vol, pit = got[min(uses, len(got) - 1)]
            parts.append((dec[k][0], dec[k][1], ms, vol, pit, idx))
        if not parts:
            continue
        a, sr = bake(parts)
        dst = os.path.join(tmp, "baked_%d.wav" % len(out))
        w = wave.open(dst, "wb")
        w.setnchannels(a.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.clip(a, -32768, 32767).astype("<i2").tobytes())
        w.close()
        out[ref] = dst
    return out


# ------------------------------------------------------------------ the stage
def build_files(image, home, mohaa, progress=lambda **kv: None, opts=None):
    """-> ({pak path: bytes}, {key: fit info}) - everything the EA guns pak holds, nothing written yet"""
    import flcore
    import flgunvfs
    import flgunfit
    import flgunsight
    opts = opts or {}
    register()
    flgunvfs.setup(mohaa, home)
    disc = flcore.Disc(image)
    guns = DiscGuns(disc)
    specs = flgunsight.load_specs(opts.get("specs"))
    tmp = tempfile.mkdtemp(prefix="eaguns_")
    files, rows, report = {}, [], {}
    try:
        keys = opts.get("keys", KEYS)
        refs = sorted({r for k in keys for v in flgunfit.SOUNDS.get(k, {}).values() for r in (v if isinstance(v, list) else [v])})
        snd = decode_sounds(disc, refs, tmp, opts.get("vgm"))
        if refs and not snd:
            progress(step="guns_sounds", skipped="no vgmstream: the base sounds stay")
        for k in keys:
            progress(step="guns", gun=k)
            try:
                d = guns.load(k)
                fr = flgunsight.solve_key(k, d, specs[k])
                f, info = flgunfit.write_gun(k, d, fr, snd, opts.get("rows"))
            except flgunfit.MissingBase as e:
                progress(step="guns", gun=k, skipped="not in this mod build: %s" % e)
                continue
            if "_row" in f:
                rows.append(f.pop("_row").decode())
            files.update(f)
            report[k] = info
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not files:
        return {}, report
    files[ROWS_FILE] = ("// HZM coop discguns: converted on this PC (sight rows of the fitted European Assault meshes)\n"
                        + "\n".join(sorted(rows, key=lambda r: r.split()[1])) + "\n").encode()
    if opts.get("upscale", True):
        try:
            import flgunup
            report["_upscale"] = flgunup.upscale_files(files, opts.get("esrgan"), progress)
        except Exception as e:
            progress(step="guns_upscale", skipped=str(e))
    return files, report


def convert(image, home, mohaa, progress=lambda **kv: None, opts=None):
    import flguns
    out = os.path.join(home, PAK)
    try:
        files, report = build_files(image, home, mohaa, progress, opts)
    finally:
        if os.path.exists(out + ".tmp"):
            os.remove(out + ".tmp")
    if not files:
        if os.path.exists(out):
            os.remove(out)
        return []
    return [flguns.write_pak(files, out)]
