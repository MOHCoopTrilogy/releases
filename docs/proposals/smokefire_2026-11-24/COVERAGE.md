# Smoke and fire coverage (DERIVED - `python docs/tools/fx_coverage.py report`; do not edit)

Set: shipped v1.10.91 (69 paks). Status rules: `docs/tools/assets/fx/fx_coverage.json`.

## Totals

| family | upgraded | excluded | todo | other |
|---|---:|---:|---:|---:|
| artillery | 6 | 4 | 35 | 0 |
| disc missions | 0 | 0 | 2 | 0 |
| dust/debris | 6 | 5 | 39 | 0 |
| flak | 4 | 0 | 13 | 0 |
| grenade | 1 | 6 | 18 | 0 |
| impacts | 0 | 5 | 39 | 0 |
| map fire | 22 | 0 | 12 | 0 |
| muzzle | 2 | 0 | 16 | 0 |
| other smoke/fire (by content) | 3 | 2 | 30 | 0 |
| rocket/shell | 2 | 9 | 8 | 0 |
| set-piece blast | 13 | 2 | 33 | 0 |
| smoke grenade | 1 | 1 | 5 | 0 |
| smoke/steam | 4 | 2 | 27 | 0 |
| sparks | 1 | 0 | 11 | 0 |
| sprites | 11 | 2 | 103 | 0 |
| surfaces | 6 | 30 | 14 | 0 |
| vehicle/aircraft | 13 | 4 | 21 | 0 |
| volumetric smoke | 0 | 0 | 6 | 0 |

## FAIL (0)


## Defects seen (any status)

- `tik:models/emitters/barracks_explosion.tik` (todo, winner Pak0.pk3): parens +2
- `tik:models/fx/bh_dirt_hard.tik` (todo, winner zzzzzzzz_hd_fxfix.pk3): parens +1
- `tik:models/fx/bh_dirt_lite.tik` (todo, winner zzzzzzzz_hd_fxfix.pk3): parens +1
- `tik:models/fx/bh_mud_hard.tik` (todo, winner zzzzzzzz_hd_fxfix.pk3): parens +1
- `tik:models/fx/bh_mud_lite.tik` (todo, winner zzzzzzzz_hd_fxfix.pk3): parens +1
- `tik:models/fx/bh_wood_hard.tik` (todo, winner zzzzzzzz_hd_fxfix.pk3): parens +1
- `tik:models/fx/bh_wood_lite.tik` (todo, winner zzzzzzzz_hd_fxfix.pk3): parens +1
- `tik:models/fx/exp_flak_near_moving.tik` (todo, winner pak1.pk3): parens -1
- `tik:models/fx/smokegrenadeexplosion.tik` (todo, winner pak1.pk3): missing $include models/fx/SmokeGrenadeExplosion_base.txt
- `sprite:c47skytrain_fiery1` (todo, winner ): missing shader and image
- `sprite:c47skytrain_fiery2` (todo, winner ): missing shader and image
- `sprite:corona_util` (todo, winner pak1.pk3): draws 2.0x retail size
- `sprite:explosion1` (todo, winner ): missing shader and image
- `sprite:explshock` (todo, winner ): missing shader and image
- `sprite:explsmoke` (todo, winner ): missing shader and image
- `sprite:generalfireball_01` (todo, winner pak1.pk3): draws 4.0x retail size
- `sprite:puffystuff_light` (todo, winner pak1.pk3): draws 4.0x retail size
- `sprite:sandstorm02` (todo, winner pak1.pk3): draws 4.0x retail size
- `sprite:snowplume_k5` (todo, winner pak1.pk3): draws 4.0x retail size
- `surface:bh_stone_fastpiece` (excluded, winner ): missing shader and image

## Every asset

| asset | family | status | winner | detail / reason |
|---|---|---|---|---|
| `tik:models/fx/exp_artshell_snowa.tik` | artillery | excluded | pak1.pk3 | sprites ; spawns mortar_snow.tik; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/explosionartilleryshell.tik` | artillery | excluded | pak1.pk3 | sprites ; spawns mortar_snow.tik; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/granatwerferexplosion.tik` | artillery | excluded | pak1.pk3 | sprites ; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/granatwerferexplosion_far.tik` | artillery | excluded | pak1.pk3 | sprites ; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/emitters/mortar_dirt_dustcloud.tik` | artillery | todo | Pak0.pk3 | sprites bh_dirt_piece,vsssource; lights 1 - retail look |
| `tik:models/emitters/mortar_dirt_nebelwerfer.tik` | artillery | todo | pak1.pk3 | sprites dirtplume,mortar_dirthit,mortar_dirthit2; spawns mortar_dirt_dustcloud.tik - retail look |
| `tik:models/emitters/mortar_dirt_nodamage.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,snowclump,vsssource_new; spawns mortar_dirt_dustcloud.tik - retail look |
| `tik:models/emitters/mortar_dirt_nosound.tik` | artillery | todo | pak1.pk3 | sprites dirtplume,mortar_dirthit,mortar_dirthit2; vss mist; spawns mortar_dirt_dustcloud.tik - retail look |
| `tik:models/emitters/mortar_hay.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,vsssource; spawns bh_wood_piece.tik,wood_flap.tik,woodbeams.tik - retail look |
| `tik:models/emitters/mortar_snow_cloud.tik` | artillery | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/mortar_snow_combo.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_snowhit; spawns mortar_dirt_dustcloud.tik,mortar_snow_cloud.tik - retail look |
| `tik:models/emitters/mortar_snow_old1.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_snowhit; spawns mortar_dirt_dustcloud.tik,mortar_snow_cloud.tik - retail look |
| `tik:models/emitters/mortar_snow_old2.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,mortar_snowhit,snowclump...; spawns mortar_dirt_dustcloud.tik - retail look |
| `tik:models/emitters/mortar_snow_playereffect.tik` | artillery | todo | pak1.pk3 | sprites snowclump - retail look |
| `tik:models/emitters/mortar_snow_t2l2.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,mortar_snowhit,snowclump...; spawns mortar_dirt_dustcloud.tik; lights 2 - retail look |
| `tik:models/emitters/mortar_snow_triggerable.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,mortar_snowhit,snowclump...; spawns mortar_dirt_dustcloud.tik - retail look |
| `tik:models/emitters/mortar_snowdeadly.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,mortar_snowhit,vsssource_new; spawns mortar_dirt_dustcloud.tik; lights 7 - retail look |
| `tik:models/emitters/mortar_snowdeadly2.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_snowhit; spawns mortar_dirt_dustcloud.tik,mortar_snow_cloud.tik - retail look |
| `tik:models/emitters/mortar_snowdeadly_mark.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_snowhit; spawns mortar_dirt_dustcloud.tik,mortar_snow_cloud.tik,mortar_snow_playereffect.tik - retail look |
| `tik:models/emitters/mortar_snowhit.tik` | artillery | todo | pak1.pk3 | sprites bh_dirt_piece,dustdrop,snowclump,vsssource; spawns mortar_snow.tik; lights 1 - retail look |
| `tik:models/emitters/mortar_snowhitnodamage.tik` | artillery | todo | pak1.pk3 | sprites bh_dirt_piece,dustdrop,snowclump,vsssource; spawns mortar_snow.tik; lights 1 - retail look |
| `tik:models/emitters/mortar_snownodamage.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,mortar_snowhit,snowclump...; spawns mortar_dirt_dustcloud.tik; lights 9 - retail look |
| `tik:models/emitters/mortar_tree_t2l2.tik` | artillery | todo | pak1.pk3 | sprites gren_boom,vsssource; spawns bh_wood_piece.tik,wood_flap.tik,woodbeams.tik; lights 3 - retail look |
| `tik:models/emitters/nebel_snowexplosion.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,mortar_snowhit,snowclump...; spawns mortar_dirt_dustcloud.tik - retail look |
| `tik:models/emitters/nebelwerfer_death.tik` | artillery | todo | Pak0.pk3 | sprites dirtplume,mortar_dirthit,mortar_dirthit2; vss mist; spawns mortar_dirt_dustcloud.tik - retail look |
| `tik:models/emitters/smoke_airstrike_crater.tik` | artillery | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/fx/exp_nebelwerfer.tik` | artillery | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/fx_nebelwerfer.tik` | artillery | todo | Pak0.pk3 | sprites vsssource; surfaces bazookashell; spawns bazookaexplosion.tik; lights 1 - retail look |
| `tik:models/fx/heavyshellexp_dirt.tik` | artillery | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,snowclump,vsssource_new; spawns mortar_dirt_dustcloud.tik - retail look |
| `tik:models/fx/heavyshellexp_snow.tik` | artillery | todo | pak1.pk3 | sprites snowclump,snowplume_02,strafe_snowhit2; lights 3 - retail look |
| `tik:models/fx/heavyshellexp_stone.tik` | artillery | todo | pak1.pk3 | sprites bridgecharge,puffystuff_light,thrownstone2; spawns fx_smoketrail_concrete.tik,fx_smoketrail_concrete_big.tik - retail look |
| `tik:models/fx/hs_artillery_concrete.tik` | artillery | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/hs_artillery_dirt.tik` | artillery | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/hs_artillery_snow.tik` | artillery | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/hs_artillery_structure.tik` | artillery | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/hs_artillery_vehicle.tik` | artillery | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/mortarburst_tree.tik` | artillery | todo | pak1.pk3 | sprites bridgecharge,snowplume_01,splinter1,splinter2...; lights 3 - retail look |
| `tik:models/fx/mortarhit.tik` | artillery | todo | Pak0.pk3 | sprites ; surfaces mortarhit - retail look |
| `tik:models/fx/nebelwerfer_exhaust.tik` | artillery | todo | pak1.pk3 | sprites puffystuff_dark,trainspark_01 - retail look |
| `tik:models/emitters/mortar_concrete.tik` | artillery | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_dust,cfx_ember,cfx_fire_fb...; spawns chunkcrete.tik,concrete2.tik,rebarblock.tik; lights 5 - fx_1025 (v1.10.37) |
| `tik:models/emitters/mortar_dirt.tik` | artillery | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_dust,cfx_ember,cfx_fire_fb...; lights 5 - fx_1025 (v1.10.37) |
| `tik:models/emitters/mortar_higgins.tik` | artillery | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_dust,cfx_ember,cfx_fire_fb...; spawns higgins_mushroom.tik; lights 5 - fx_1025 (v1.10.37) |
| `tik:models/emitters/mortar_snow.tik` | artillery | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_dust,cfx_ember,cfx_fire_fb...; lights 5 - fx_1025 (v1.10.37) |
| `tik:models/emitters/mortar_tree.tik` | artillery | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_dust,cfx_ember,cfx_fire_fb...; spawns bh_wood_piece.tik,woodbeams.tik; lights 5 - fx_1025 (v1.10.37) |
| `tik:models/fx/heavyshellexp_base.tik` | artillery | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `disc:ea:eafx` | disc missions | todo | (player's converted pak) | Euro Assault effect packages (docs/tools/ea/eafx.py) - built on the player's PC - fidelity-first pass, PLAN Phase 4 / section 6 (built on the player's PC) |
| `disc:fl:flpfx` | disc missions | todo | (player's converted pak) | Frontline particle systems (docs/tools/frontline/flpfx.py) - built on the player's PC - fidelity-first pass, PLAN Phase 4 / section 6 (built on the player's PC) |
| `tik:models/emitters/metaljibs_1.tik` | dust/debris | excluded | Pak0.pk3 | sprites ; spawns heavy_pipe.tik,ibeam_piece.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/emitters/metaljibs_2.tik` | dust/debris | excluded | Pak0.pk3 | sprites ; spawns heavy_pipe.tik,ibeam_piece.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/crates/debris_0.tik` | dust/debris | excluded | Pak0.pk3 | sprites ; spawns crate-jib-chunk.tik,crate-jib-plank.tik,crate-jib-smallchunk.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/crates/debris_1.tik` | dust/debris | excluded | Pak0.pk3 | sprites ; spawns crate-jib-chunk.tik,crate-jib-plank.tik,crate-jib-smallchunk.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/crates/debris_255.tik` | dust/debris | excluded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites ; spawns crate-jib-chunk.tik,crate-jib-plank.tik,crate-jib-smallchunk.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/emitters/bunker_dust.tik` | dust/debris | todo | Pak0.pk3 | sprites dustdrop - retail look |
| `tik:models/emitters/ces3_concrete.tik` | dust/debris | todo | pak1.pk3 | sprites mortar_dirthit,mortar_snowhit,snowclump,vsssource_new; lights 3 - retail look |
| `tik:models/emitters/ces3_dirt.tik` | dust/debris | todo | pak1.pk3 | sprites mortar_dirthit,snowclump,vsssource_new; spawns mortar_dirt_dustcloud.tik; lights 3 - retail look |
| `tik:models/emitters/cinematics_bigdust.tik` | dust/debris | todo | pak1.pk3 | sprites tehaodebris_01,textures/effects/woodsplinters,vsssource - retail look |
| `tik:models/emitters/cinematics_sidedust.tik` | dust/debris | todo | pak1.pk3 | sprites tehaodebris_01,vsssource - retail look |
| `tik:models/emitters/concjibs_1.tik` | dust/debris | todo | Pak0.pk3 | sprites vsssource; spawns concrete1.tik,concrete2.tik - retail look |
| `tik:models/emitters/js_dust_puff.tik` | dust/debris | todo | pak1.pk3 | sprites willys_dust - retail look |
| `tik:models/emitters/js_wheel_dirt_plume.tik` | dust/debris | todo | pak1.pk3 | sprites willys_dirt,willys_dust - retail look |
| `tik:models/emitters/js_wheel_dust_plume.tik` | dust/debris | todo | pak1.pk3 | sprites willys_dust - retail look |
| `tik:models/emitters/m1dust1.tik` | dust/debris | todo | Pak0.pk3 | sprites ; vss smokegrenade - retail look |
| `tik:models/emitters/m1dust2.tik` | dust/debris | todo | Pak0.pk3 | sprites ; vss smokegrenade - retail look |
| `tik:models/emitters/m1dust3.tik` | dust/debris | todo | Pak0.pk3 | sprites ; vss smokegrenade - retail look |
| `tik:models/emitters/tankdust.tik` | dust/debris | todo | Pak0.pk3 | sprites ; vss steam - retail look |
| `tik:models/fx/bikewheel_dirt.tik` | dust/debris | todo | pak1.pk3 | sprites snowclump,snowplume_01 - retail look |
| `tik:models/fx/blockcrete.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces blockcrete - retail look |
| `tik:models/fx/bp_debris1.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces bp_debris1 - retail look |
| `tik:models/fx/bp_debris2.tik` | dust/debris | todo | Pak0.pk3 | sprites vsssource; surfaces bp_debris2 - retail look |
| `tik:models/fx/bp_debris2g.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces bp_debris2g - retail look |
| `tik:models/fx/bp_debris3.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces bp_debris3 - retail look |
| `tik:models/fx/bp_debris3g.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces bp_debris3g - retail look |
| `tik:models/fx/bridgedust.tik` | dust/debris | todo | pak1.pk3 | sprites snowplume_01 - retail look |
| `tik:models/fx/chunkcrete.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces concrete2 - retail look |
| `tik:models/fx/concrete1.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces concrete1 - retail look |
| `tik:models/fx/concrete2.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces concrete2 - retail look |
| `tik:models/fx/crates/crate-jib-chunk.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces crate-jibs - retail look |
| `tik:models/fx/crates/crate-jib-plank.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces crate-jibs - retail look |
| `tik:models/fx/crates/crate-jib-smallchunk.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces crate-jibs - retail look |
| `tik:models/fx/crates/crate-jib-smallplank.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces crate-jibs - retail look |
| `tik:models/fx/crates/crate-jib-splinter.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces crate-jibs - retail look |
| `tik:models/fx/crates/debris_2.tik` | dust/debris | todo | Pak0.pk3 | sprites cardboard_light; lights 1 - retail look |
| `tik:models/fx/crates/debris_3.tik` | dust/debris | todo | pak1.pk3 | sprites cardboard_light - retail look |
| `tik:models/fx/fallingdirt_narrow.tik` | dust/debris | todo | pak1.pk3 | sprites fallingdirt - retail look |
| `tik:models/fx/fallingdirt_wide.tik` | dust/debris | todo | pak1.pk3 | sprites fallingdirt - retail look |
| `tik:models/fx/windows/debris_0.tik` | dust/debris | todo | Pak0.pk3 | sprites glass_small - retail look |
| `tik:models/fx/windows/debris_1.tik` | dust/debris | todo | Pak0.pk3 | sprites glass_small - retail look |
| `tik:models/fx/windows/debris_2.tik` | dust/debris | todo | Pak0.pk3 | sprites glass_small - retail look |
| `tik:models/fx/windows/debris_3.tik` | dust/debris | todo | Pak0.pk3 | sprites glass_small - retail look |
| `tik:models/fx/wplumelarge.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces wplumelarge - retail look |
| `tik:models/fx/wplumesmall.tik` | dust/debris | todo | Pak0.pk3 | sprites ; surfaces wplumesmall - retail look |
| `tik:models/emitters/coop_dustveil_day.tik` | dust/debris | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites sandstorm01,sandstorm02,sandstorm_gust; surfaces coop_dustveil_day - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/coop_dustveil_night.tik` | dust/debris | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites sandstorm01,sandstorm02,sandstorm_gust; surfaces coop_dustveil_night - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/coop_dustveil_rain.tik` | dust/debris | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites ; surfaces coop_dustveil_rain - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/coop_dustveil_rainnight.tik` | dust/debris | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites ; surfaces coop_dustveil_rainnight - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/coop_dustveil_snow.tik` | dust/debris | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites ; surfaces coop_dustveil_snow - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/coop_dustveil_snownight.tik` | dust/debris | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites ; surfaces coop_dustveil_snownight - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/fx/88_flakcanon.tik` | flak | todo | pak1.pk3 | sprites muzzleblast_01,muzzlecharge,snowplume_01,trainspark_01 - retail look |
| `tik:models/fx/demodamage_flak88.tik` | flak | todo | pak1.pk3 | sprites grenadefire,puffystuff_dark,trainspark_01 - retail look |
| `tik:models/fx/exp_flak_far1.tik` | flak | todo | pak1.pk3 | sprites bh_snow_puff - retail look |
| `tik:models/fx/exp_flak_far2.tik` | flak | todo | pak1.pk3 | sprites bh_snow_puff - retail look |
| `tik:models/fx/exp_flak_far3.tik` | flak | todo | pak1.pk3 | sprites bh_snow_puff - retail look |
| `tik:models/fx/exp_flak_near01.tik` | flak | todo | pak1.pk3 | sprites bh_snow_puff,vsssource - retail look |
| `tik:models/fx/exp_flak_near02.tik` | flak | todo | pak1.pk3 | sprites bh_snow_puff,vsssource - retail look |
| `tik:models/fx/exp_flak_near03.tik` | flak | todo | pak1.pk3 | sprites bh_snow_puff,vsssource - retail look |
| `tik:models/fx/exp_flak_near_moving.tik` | flak | todo | pak1.pk3 | sprites c47skytrain_fiery1,c47skytrain_fiery2,flak_cloud01,flak_cloud03... - retail look |
| `tik:models/fx/exp_flak_near_v2.tik` | flak | todo | pak1.pk3 | sprites c47skytrain_fiery1,c47skytrain_fiery2,flak_cloud01,flak_cloud03... - retail look |
| `tik:models/fx/exp_flak_near_v3.tik` | flak | todo | pak1.pk3 | sprites c47skytrain_fiery1,c47skytrain_fiery2,flak_cloud01,flak_cloud03... - retail look |
| `tik:models/fx/exp_flak_skybox.tik` | flak | todo | pak1.pk3 | sprites flakflash_skybox,flaksmoke_skybox - retail look |
| `tik:models/fx/fx_miniaa.tik` | flak | todo | pak1.pk3 | sprites ; surfaces miniaa - retail look |
| `tik:models/fx/exp_flak88.tik` | flak | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_fire_fb,cfx_puff,cfx_smoke_fb; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/exp_flak_far.tik` | flak | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_fire_fb,cfx_puff,cfx_smoke_fb; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/exp_flak_near.tik` | flak | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_fire_fb,cfx_puff,cfx_smoke_fb; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/fx_flak88_explosion.tik` | flak | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_fire_fb,cfx_puff,cfx_smoke_fb; spawns bp_debris1.tik,gas_mushroom_cloud.tik; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/deadlygrenadeexplosion.tik` | grenade | excluded | pak1.pk3 | sprites ; explosioneffect grenade - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/f1grenadeexplosion.tik` | grenade | excluded | pak1.pk3 | sprites ; explosioneffect grenade - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/grenexp_wood.tik` | grenade | excluded | Pak0.pk3 | sprites ; spawns bh_wood_piece.tik,wood_flap.tik,woodbeams.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/m2fgrenadeexplosion.tik` | grenade | excluded | Pak0.pk3 | sprites ; explosioneffect grenade - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/millsgrenadeexplosion.tik` | grenade | excluded | pak1.pk3 | sprites ; explosioneffect grenade - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/riflegrenadeexplosion.tik` | grenade | excluded | pak1.pk3 | sprites ; explosioneffect grenade - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/exp_grenade_gen.tik` | grenade | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/exp_grenade_snow.tik` | grenade | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/fx_grenade_explosion.tik` | grenade | todo | Pak0.pk3 | sprites explosion1,explshock,explsmoke; spawns explrock.tik,fx_spark.tik - retail look |
| `tik:models/fx/grenexp_base.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites gren_boom,vsssource; lights 3 - PLAN D1: our copy loses to zzzzzzzz_hd_fxfix since v1.10.37; the fix is staged (gen_fx_pak.py -> H:/hzm_work/smokefire/paks), awaiting the user's look sign-off - then flip to upgraded/expect coop_fx |
| `tik:models/fx/grenexp_carpet.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites dirtplume,explosed,mortar_dirthit,mortar_dirthit2; vss mist; spawns bh_metal_fastpiece.tik; lights 1 - retail look |
| `tik:models/fx/grenexp_dirt.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites dirtplume,explosed,mortar_dirthit,mortar_dirthit2; vss mist; spawns bh_metal_fastpiece.tik; lights 1 - retail look |
| `tik:models/fx/grenexp_fireball.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites explosed2,fire_ring,vsssource - retail look |
| `tik:models/fx/grenexp_foliage.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites dirtplume,explosed,mortar_dirthit,mortar_dirthit2; vss mist; spawns bh_metal_fastpiece.tik; lights 1 - retail look |
| `tik:models/fx/grenexp_grass.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites dirtplume,explosed,mortar_dirthit,mortar_dirthit2; vss mist; spawns bh_metal_fastpiece.tik; lights 1 - retail look |
| `tik:models/fx/grenexp_gravel.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites dirtplume,mortar_dirthit,mortar_dirthit2,stonechip; vss mist; spawns bh_metal_fastpiece.tik; lights 1 - retail look |
| `tik:models/fx/grenexp_metal.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites dirtplume,explosed; vss mist; spawns bh_metal_fastpiece.tik; lights 1 - retail look |
| `tik:models/fx/grenexp_mud.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites dirtplume,explosed,mortar_dirthit,mortar_dirthit2; vss mist; spawns bh_metal_fastpiece.tik; lights 1 - retail look |
| `tik:models/fx/grenexp_paper.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites explosed; vss mist; spawns bh_metal_fastpiece.tik; lights 1 - retail look |
| `tik:models/fx/grenexp_sand.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites dirtplume,explosed,mortar_dirthit,mortar_dirthit2; vss mist; spawns bh_metal_fastpiece.tik; lights 1 - retail look |
| `tik:models/fx/grenexp_snow.tik` | grenade | todo | zzzzzzzz_hd_fxfix.pk3 | sprites dirtplume,explosed,mortar_dirthit,mortar_dirthit2; vss mist; spawns bh_metal_fastpiece.tik; lights 1 - PLAN D1: our copy loses to zzzzzzzz_hd_fxfix since v1.10.37; the fix is staged (gen_fx_pak.py -> H:/hzm_work/smokefire/paks), awaiting the user's look sign-off - then flip to upgraded/expect coop_fx |
| `tik:models/fx/grenexp_stone.tik` | grenade | todo | pak1.pk3 | sprites mortar_dirthit,mortar_snowhit,snowclump,vsssource_new; lights 3 - retail look |
| `tik:models/fx/grenexp_water.tik` | grenade | todo | Pak0.pk3 | sprites explosed,oceanspray,water_g,waterplume; lights 4 - retail look |
| `tik:models/fx/maingrenade.tik` | grenade | todo | pak1.pk3 | sprites grenadefire,snowplume_01; spawns grenadetrail.tik; explosioneffect grenade - retail look |
| `tik:models/emitters/gren_exp.tik` | grenade | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/bh_carpet_lite.tik` | impacts | excluded | Pak0.pk3 | sprites ; spawns bh_wood_piece.tik,bh_wood_puff.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/bh_foliage_hard.tik` | impacts | excluded | Pak0.pk3 | sprites ; spawns bh_foliage_leaf.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/bh_foliage_lite.tik` | impacts | excluded | Pak0.pk3 | sprites ; spawns bh_foliage_leaf.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/bh_paper_lite.tik` | impacts | excluded | Pak0.pk3 | sprites  - no sprite, no volumetric smoke, spawns nothing (solid debris / model only) |
| `tik:models/fx/fs_grass.tik` | impacts | excluded | Pak0.pk3 | sprites ; spawns bh_grass_piece.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/bh_carpet_hard.tik` | impacts | todo | Pak0.pk3 | sprites ; vss bulletimpact; spawns bh_wood_piece.tik,bh_wood_puff.tik - retail look |
| `tik:models/fx/bh_dirt_hard.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_dirt_piece,dustdrop; lights 1 - retail look |
| `tik:models/fx/bh_dirt_lite.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_dirt_piece,dustdrop; lights 1 - retail look |
| `tik:models/fx/bh_foliage_leaf.tik` | impacts | todo | Pak0.pk3 | sprites ; surfaces bh_foliage_leaf - retail look |
| `tik:models/fx/bh_glass_hard.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites glass_small; spawns bh_stone_puff.tik - retail look |
| `tik:models/fx/bh_glass_lite.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites glass_small; spawns bh_stone_puff.tik - retail look |
| `tik:models/fx/bh_grass_hard.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_dirt_piece,dustdrop; spawns bh_grass_piece.tik; lights 2 - retail look |
| `tik:models/fx/bh_grass_lite.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_dirt_piece,dustdrop; spawns bh_grass_piece.tik; lights 2 - retail look |
| `tik:models/fx/bh_grass_piece.tik` | impacts | todo | Pak0.pk3 | sprites ; surfaces bh_grass_piece - retail look |
| `tik:models/fx/bh_human_uniform_hard.tik` | impacts | todo | zzzzzzz-HRRTM_Blood_effects_Addon.pk3 | sprites bodyhitpuff; spawns blood_long.tik - retail look |
| `tik:models/fx/bh_human_uniform_lite.tik` | impacts | todo | zzzzzzz-HRRTM_Blood_effects_Addon.pk3 | sprites bodyhitpuff; spawns blood_long.tik - retail look |
| `tik:models/fx/bh_metal_fastpiece.tik` | impacts | todo | Pak0.pk3 | sprites ; surfaces bh_metal_fastpiece - retail look |
| `tik:models/fx/bh_metal_hard.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_metal_spark,corona_util,vsssource; vss bulletimpact; spawns bh_metal_fastpiece.tik; lights 2 - retail look |
| `tik:models/fx/bh_metal_lite.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_metal_spark,corona_util,vsssource; vss bulletimpact; spawns bh_metal_fastpiece.tik; lights 2 - retail look |
| `tik:models/fx/bh_mud_hard.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_dirt_piece,dustdrop; lights 1 - retail look |
| `tik:models/fx/bh_mud_lite.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_dirt_piece,dustdrop; lights 1 - retail look |
| `tik:models/fx/bh_paper_hard.tik` | impacts | todo | Pak0.pk3 | sprites cardboard_light; vss bulletimpact; spawns bh_wood_puff.tik - retail look |
| `tik:models/fx/bh_sand_hard.tik` | impacts | todo | pak1.pk3 | sprites bh_sand,vsssource; lights 2 - retail look |
| `tik:models/fx/bh_sand_lite.tik` | impacts | todo | pak1.pk3 | sprites bh_sand,vsssource; lights 2 - retail look |
| `tik:models/fx/bh_snow_hard.tik` | impacts | todo | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites coop_snowplume,snowclump,strafe_snowhit2 - retail look |
| `tik:models/fx/bh_snow_lite.tik` | impacts | todo | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites coop_snowplume,snowclump - retail look |
| `tik:models/fx/bh_stone_fastpiece.tik` | impacts | todo | Pak0.pk3 | sprites ; surfaces bh_stone_fastpiece - retail look |
| `tik:models/fx/bh_stone_hard.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_snow_puff1,bh_stone_piece,stonechip,vsssource; lights 3 - retail look |
| `tik:models/fx/bh_stone_lite.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_snow_puff1,bh_stone_piece,stonechip,vsssource; lights 3 - retail look |
| `tik:models/fx/bh_stone_puff.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites ; surfaces bh_stone_puff - retail look |
| `tik:models/fx/bh_water_hard.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_water_ring,vsssource2,waterplume; lights 5 - retail look |
| `tik:models/fx/bh_water_lite.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_water_ring,vsssource2,waterplume; lights 5 - retail look |
| `tik:models/fx/bh_wood_hard.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites smokegrenade; spawns bh_wood_piece.tik,bh_wood_puff.tik; lights 1 - retail look |
| `tik:models/fx/bh_wood_lite.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites smokegrenade; spawns bh_wood_piece.tik,bh_wood_puff.tik; lights 1 - retail look |
| `tik:models/fx/bh_wood_piece.tik` | impacts | todo | Pak0.pk3 | sprites ; surfaces bh_wood_piece - retail look |
| `tik:models/fx/bh_wood_puff.tik` | impacts | todo | Pak0.pk3 | sprites ; surfaces bh_wood_puff - retail look |
| `tik:models/fx/bh_wood_puff_simple.tik` | impacts | todo | pak1.pk3 | sprites ; surfaces bh_wood_puff_simple - retail look |
| `tik:models/fx/fs_dirt.tik` | impacts | todo | zzzzzzzz_hd_fxfix.pk3 | sprites bh_dirt_piece,dustdrop; lights 1 - retail look |
| `tik:models/fx/fs_heavy_dust.tik` | impacts | todo | Pak0.pk3 | sprites dustdrop - retail look |
| `tik:models/fx/fs_light_dust.tik` | impacts | todo | Pak0.pk3 | sprites dustdrop - retail look |
| `tik:models/fx/fs_mud.tik` | impacts | todo | Pak0.pk3 | sprites bh_dirt_piece; lights 1 - retail look |
| `tik:models/fx/fs_puddle.tik` | impacts | todo | Pak0.pk3 | sprites bh_water_ring; spawns water_splash_drop.tik; lights 5 - retail look |
| `tik:models/fx/fs_sand.tik` | impacts | todo | Pak0.pk3 | sprites ; vss bulletdirtimpact - retail look |
| `tik:models/fx/fs_snow.tik` | impacts | todo | Pak0.pk3 | sprites bh_snow_puff; lights 4 - retail look |
| `tik:models/emitters/blowtorch_cutter.tik` | map fire | todo | Pak0.pk3 | sprites corona_util,vsssource; spawns bh_metal_fastpiece.tik - retail look |
| `tik:models/emitters/candle_standing_fire.tik` | map fire | todo | pak1.pk3 | sprites tehao_candellight_02; surfaces candle_standing_t - retail look |
| `tik:models/emitters/electrical_fire.tik` | map fire | todo | Pak0.pk3 | sprites corona_util,vsssource; spawns bh_metal_fastpiece.tik - retail look |
| `tik:models/emitters/fireball_matrix.tik` | map fire | todo | Pak0.pk3 | sprites fireball_pj - retail look |
| `tik:models/emitters/fireflies.tik` | map fire | todo | Pak0.pk3 | sprites firefly - retail look |
| `tik:models/emitters/firescreen.tik` | map fire | todo | Pak0.pk3 | sprites fire_ring - retail look |
| `tik:models/emitters/lanternflame.tik` | map fire | todo | Pak0.pk3 | sprites corona_reg; spawns bh_metal_fastpiece.tik - retail look |
| `tik:models/emitters/tehao_candleholder_withfire.tik` | map fire | todo | pak1.pk3 | sprites tehao_candellight_02; surfaces candleholder - retail look |
| `tik:models/emitters/tehao_candlelight.tik` | map fire | todo | pak1.pk3 | sprites tehao_candellight_02,vsssource; surfaces corona_spiky - retail look |
| `tik:models/emitters/tehao_firesmoke_collide.tik` | map fire | todo | pak1.pk3 | sprites tehaosmoke_dark - retail look |
| `tik:models/fx/hallfire2.tik` | map fire | todo | Pak0.pk3 | sprites air_explosion,gren_explosion - retail look |
| `tik:models/fx/lanternflame.tik` | map fire | todo | Pak0.pk3 | sprites ; surfaces lampflame - retail look |
| `tik:models/emitters/coop_fin_fire_big.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_fin_flame,cfx_fin_flame_b,cfx_puff; lights 2 - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/coop_fin_fire_m.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_fin_flame,cfx_fin_flame_b,cfx_puff; lights 2 - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/coop_fin_fire_s.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_fin_flame,cfx_fin_flame_b,cfx_puff; lights 1 - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/coop_fire_l.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/coop_fire_m.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/coop_fire_s.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/fancyfire.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/fire.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/fireandsmoke.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; surfaces fire_back,fire_front,fire_middle; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/firefill.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/firegood.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/firesmoke.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_puff; lights 1 - fx_1025 (v1.10.37) |
| `tik:models/emitters/inferno.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/residual_fire.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/t2l4_fire.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/tehao_cheapfire.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/tehao_fire.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; surfaces transparency; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/tehao_firesmoke.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_puff; lights 1 - fx_1025 (v1.10.37) |
| `tik:models/emitters/tehao_firesmoke_long.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_puff; lights 1 - fx_1025 (v1.10.37) |
| `tik:models/emitters/tehao_firesmoke_superlong.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_puff; lights 1 - fx_1025 (v1.10.37) |
| `tik:models/fx/sustainedfire.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/fx/t2l4_fire.tik` | map fire | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/fx/garandsmoke.tik` | muzzle | todo | pak1.pk3 | sprites vsssource; lights 3 - retail look |
| `tik:models/fx/snipesmoke.tik` | muzzle | todo | Pak0.pk3 | sprites vsssource; lights 3 - retail look |
| `tik:models/fx/tankcanon.tik` | muzzle | todo | pak1.pk3 | sprites bridgecharge - retail look |
| `tik:models/fx/tankcanon2.tik` | muzzle | todo | pak1.pk3 | sprites muzzleblast_01,muzzlecharge,snowplume_01,trainspark_01 - retail look |
| `tik:models/fx/tankcanon_pov.tik` | muzzle | todo | pak1.pk3 | sprites muzzleblast_01,muzzlecharge_02,snowplume_01 - retail look |
| `weaponsmoke:campfire_01` | muzzle | todo |  | 1 weapon tiks, e.g. it_w_k5des.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `weaponsmoke:campfire_02` | muzzle | todo |  | 1 weapon tiks, e.g. it_w_k5des.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `weaponsmoke:campfire_03` | muzzle | todo |  | 1 weapon tiks, e.g. it_w_k5des.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `weaponsmoke:explosion_burst` | muzzle | todo |  | 1 weapon tiks, e.g. it_w_k5des.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `weaponsmoke:gren_explosion` | muzzle | todo |  | 2 weapon tiks, e.g. it_w_k5fx_02.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `weaponsmoke:puffystuff_dark` | muzzle | todo |  | 1 weapon tiks, e.g. it_w_k5des.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `weaponsmoke:puffystuff_light` | muzzle | todo |  | 1 weapon tiks, e.g. it_w_k5des.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `weaponsmoke:snowplume_01` | muzzle | todo |  | 8 weapon tiks, e.g. kar98_mortar.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `weaponsmoke:snowplume_k5` | muzzle | todo |  | 1 weapon tiks, e.g. it_w_k5.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `weaponsmoke:vsssource` | muzzle | todo |  | 1214 weapon tiks, e.g. 30calportable.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `weaponsmoke:vsssource2` | muzzle | todo |  | 74 weapon tiks, e.g. ppsh_smg_ea.tik - muzzle smoke inside weapon tiks - PLAN Phase 1.2 (same intensity, new art) |
| `tik:models/fx/coop_barrelsmoke.tik` | muzzle | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites vsssource; lights 1 - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/fx/coop_gunsmoke.tik` | muzzle | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites vsssource; lights 2 - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/coop_fl_mine.tik` | other smoke/fire (by content) | excluded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,vsssource; lights 1 - Frontline mission effect - fidelity path (converter) |
| `tik:models/fx/coop_bloodcloud.tik` | other smoke/fire (by content) | excluded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites coop_blood_drop,coop_bloodcloud - blood / gore, not smoke or fire |
| `tik:models/emitters/ces3_snow.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites mortar_dirthit,mortar_snowhit,snowclump,vsssource_new; lights 5 - retail look |
| `tik:models/emitters/cinematics_falling.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites tehaosmoke_light - retail look |
| `tik:models/emitters/rooflift_pj.tik` | other smoke/fire (by content) | todo | Pak0.pk3 | sprites vsssource; spawns wood_brace.tik,wood_latice.tik,woodbeams.tik - retail look |
| `tik:models/emitters/sennsfence.tik` | other smoke/fire (by content) | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/short_grey_fat_trans.tik` | other smoke/fire (by content) | todo | Pak0.pk3 | sprites ; vss greasefire - retail look |
| `tik:models/emitters/tehao_feathers.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites feather_01,feather_02,vsssource - retail look |
| `tik:models/emitters/tehao_minesweeperfx.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites dirtcloud,mortar_dirthit,vsssource - retail look |
| `tik:models/emitters/tehao_waterpuddle.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites tehaoripple,tehaoripple_sub; surfaces waterpuddle - retail look |
| `tik:models/emitters/tehao_waterpuddle_big.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites tehaoripple,tehaoripple_sub; surfaces waterpuddle - retail look |
| `tik:models/emitters/thin_black_short.tik` | other smoke/fire (by content) | todo | Pak0.pk3 | sprites ; vss greasefire - retail look |
| `tik:models/emitters/thin_long_grey.tik` | other smoke/fire (by content) | todo | Pak0.pk3 | sprites ; vss greasefire - retail look |
| `tik:models/emitters/wallsplitter.tik` | other smoke/fire (by content) | todo | Pak0.pk3 | sprites vsssource2; spawns blockcrete.tik,concrete1.tik,shard_piece.tik - retail look |
| `tik:models/emitters/wide_dark_trans_tall.tik` | other smoke/fire (by content) | todo | Pak0.pk3 | sprites ; vss greasefire - retail look |
| `tik:models/emitters/wider_black_tall.tik` | other smoke/fire (by content) | todo | Pak0.pk3 | sprites ; vss greasefire - retail look |
| `tik:models/fx/barrel_gas_destroyed.tik` | other smoke/fire (by content) | todo | Pak0.pk3 | sprites air_explosion,explosed,explosed2,vsssource; spawns bp_debris3.tik - retail look |
| `tik:models/fx/bridge_splash01.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites bigsplash,waterblast01 - retail look |
| `tik:models/fx/bridge_splash02.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites bigsplash,waterblast01 - retail look |
| `tik:models/fx/democharge_bridge.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites bridgecharge,snowplume_01,trainspark_01 - retail look |
| `tik:models/fx/dudimpact.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites generalfireball_01,generalspark_01,snowplume_01 - retail look |
| `tik:models/fx/exp_treeexplode.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites explosed2,fire_ring,textures/effects/woodsplinters,vsssource; lights 2 - retail look |
| `tik:models/fx/grenadetrail.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites snowplume_01; surfaces metaldebris_01 - retail look |
| `tik:models/fx/hs_airplane_bullet_snow.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/hs_airplane_strafe_snow.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/strafe_snow1.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites snowclump,snowplume_02,strafe_snowhit2 - retail look |
| `tik:models/fx/strafe_snow2.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites snowclump,snowplume_02,strafe_snowhit2 - retail look |
| `tik:models/fx/strafe_snow3.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites snowclump,snowplume_02 - retail look |
| `tik:models/fx/truckslide_drag.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites enginesmoke_01,trainspark_01 - retail look |
| `tik:models/fx/truckslide_push.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites enginesmoke_01 - retail look |
| `tik:models/fx/truckslide_push2.tik` | other smoke/fire (by content) | todo | pak1.pk3 | sprites snowplume_01; lights 1 - retail look |
| `tik:models/fx/waterhelper.tik` | other smoke/fire (by content) | todo | Pak0.pk3 | sprites explosed,oceanspray,water_drop1,water_g - retail look |
| `tik:models/fx/exp_dynamic1.tik` | other smoke/fire (by content) | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/exp_dynamic2.tik` | other smoke/fire (by content) | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/exp_general.tik` | other smoke/fire (by content) | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/bazookaexplosion.tik` | rocket/shell | excluded | zzzzzzzz_hd_fxfix.pk3 | sprites ; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/bazookaexplosion_dm.tik` | rocket/shell | excluded | zzzzzzzz_hd_fxfix.pk3 | sprites ; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/explosionkingtigershell.tik` | rocket/shell | excluded | zzzzzz-HRRTM_Pak4_Weapons.pk3 | sprites ; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/explosionpanzerivshell.tik` | rocket/shell | excluded | zzzzzz-HRRTM_Pak4_Weapons.pk3 | sprites ; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/explosionpiatshell.tik` | rocket/shell | excluded | pak1.pk3 | sprites ; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/explosionpzb41shell.tik` | rocket/shell | excluded | pak1.pk3 | sprites ; explosioneffect heavyshell - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/explosiontigershell.tik` | rocket/shell | excluded | zzzzzz-HRRTM_Pak4_Weapons.pk3 | sprites ; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/scriptbazookaexplosion.tik` | rocket/shell | excluded | Pak0.pk3 | sprites ; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/tankshellexplosion.tik` | rocket/shell | excluded | Pak0.pk3 | sprites ; explosioneffect bazooka - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/bazookaexp_base.tik` | rocket/shell | todo | zzzzzzzz_hd_fxfix.pk3 | sprites gren_boom,vsssource; lights 3 - PLAN D1: our copy loses to zzzzzzzz_hd_fxfix since v1.10.37; the fix is staged (gen_fx_pak.py -> H:/hzm_work/smokefire/paks), awaiting the user's look sign-off - then flip to upgraded/expect coop_fx |
| `tik:models/fx/bazookaexp_dirt.tik` | rocket/shell | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,snowclump,vsssource_new; spawns mortar_dirt_dustcloud.tik - retail look |
| `tik:models/fx/bazookaexp_snow.tik` | rocket/shell | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,mortar_snowhit,snowclump... - retail look |
| `tik:models/fx/bazookaexp_stone.tik` | rocket/shell | todo | pak1.pk3 | sprites bridgecharge,puffystuff_light,thrownstone2; spawns fx_smoketrail_concrete.tik,fx_smoketrail_concrete_big.tik - retail look |
| `tik:models/fx/shelldamage_tank.tik` | rocket/shell | todo | pak1.pk3 | sprites bridgecharge,emberblast,grenadefire,puffystuff_dark... - retail look |
| `tik:models/fx/tankexp_dirt.tik` | rocket/shell | todo | pak1.pk3 | sprites bh_snow_puff,mortar_dirthit,snowclump,vsssource_new - retail look |
| `tik:models/fx/tankexp_snow.tik` | rocket/shell | todo | pak1.pk3 | sprites bh_snow_puff,mortar_snowhit; spawns mortar_snow_cloud.tik - retail look |
| `tik:models/fx/tankexp_stone.tik` | rocket/shell | todo | pak1.pk3 | sprites bridgecharge,puffystuff_light,thrownstone2; spawns fx_smoketrail_concrete.tik,fx_smoketrail_concrete_big.tik - retail look |
| `tik:models/emitters/rocketgood.tik` | rocket/shell | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites fire_ring2,vsssource - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/fx/tankexp_base.tik` | rocket/shell | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/emitters/roof_popper.tik` | set-piece blast | excluded | Pak0.pk3 | sprites ; spawns roof_popper2.tik,wood_brace.tik,wood_latice.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/explosionfoliage.tik` | set-piece blast | excluded | pak1.pk3 | sprites ; spawns bh_foliage_leaf.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/emitters/barracks_explosion.tik` | set-piece blast | todo | Pak0.pk3 | sprites air_explosion,vsssource,vsssource2; spawns metal_section.tik - retail look |
| `tik:models/emitters/cinematics_camexplosion.tik` | set-piece blast | todo | pak1.pk3 | sprites bridgecharge,burst,puffystuff_light,thrownstone2; lights 1 - retail look |
| `tik:models/emitters/cinematics_explosion01.tik` | set-piece blast | todo | pak1.pk3 | sprites grndblst1,tehaosmoke_light,thrownstone2; spawns cinematics_smoketrail.tik - retail look |
| `tik:models/emitters/cinematics_explosion02.tik` | set-piece blast | todo | pak1.pk3 | sprites cinematicexplosion_02 - retail look |
| `tik:models/emitters/cinematics_foregroundexplosion01.tik` | set-piece blast | todo | pak1.pk3 | sprites bridgecharge,grndblst1,mortar_dirthit,vsssource; lights 1 - retail look |
| `tik:models/emitters/cinematics_foregroundexplosion02.tik` | set-piece blast | todo | pak1.pk3 | sprites bridgecharge,grndblst1,mortar_dirthit,vsssource; lights 1 - retail look |
| `tik:models/emitters/cinematics_foregroundexplosion03.tik` | set-piece blast | todo | pak1.pk3 | sprites bridgecharge,grndblst1,mortar_dirthit,puffystuff_light...; lights 1 - retail look |
| `tik:models/emitters/cinematics_groundexplosion.tik` | set-piece blast | todo | pak1.pk3 | sprites bridgecharge,cinematic_sparks,gren_explosion - retail look |
| `tik:models/emitters/explosion_conflagration.tik` | set-piece blast | todo | Pak0.pk3 | sprites explosed2,vsssource - retail look |
| `tik:models/emitters/explosion_mine_shockwave.tik` | set-piece blast | todo | pak1.pk3 | sprites dirtcloud,vsssource - retail look |
| `tik:models/emitters/fx_explosion_mine.tik` | set-piece blast | todo | Pak0.pk3 | sprites bh_dirt_piece,grndblst1,mortar_dirthit,vsssource; spawns explosion_mine_shockwave.tik; lights 2 - retail look |
| `tik:models/emitters/generalblast_concrete.tik` | set-piece blast | todo | pak1.pk3 | sprites bridgecharge,puffystuff_light,thrownstone2; spawns fx_smoketrail_concrete.tik - retail look |
| `tik:models/emitters/generalblast_dirt.tik` | set-piece blast | todo | pak1.pk3 | sprites bridgecharge,puffystuff_dark,thrownstone1; spawns fx_smoketrail_dirt.tik - retail look |
| `tik:models/emitters/groundexplosion_e1l1.tik` | set-piece blast | todo | pak1.pk3 | sprites bh_dirt_piece,mortar_dirthit,tehaosmoke_light,vsssource; spawns groundexplosion_shockwave.tik; lights 1 - retail look |
| `tik:models/emitters/groundexplosion_shockwave.tik` | set-piece blast | todo | pak1.pk3 | sprites dirtcloud,vsssource - retail look |
| `tik:models/emitters/higgins_mushroom.tik` | set-piece blast | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/roof_popper2.tik` | set-piece blast | todo | Pak0.pk3 | sprites vsssource; spawns stickblock.tik - retail look |
| `tik:models/emitters/sm_explosion.tik` | set-piece blast | todo | pak1.pk3 | sprites ; surfaces sm_explosion_01,sm_explosion_02,sm_explosion_03 - retail look |
| `tik:models/emitters/tehao_e1l2_bigexplosion.tik` | set-piece blast | todo | pak1.pk3 | sprites grndblst1,sandstorm01,tehaodebris_01,tehaosmoke_light... - retail look |
| `tik:models/emitters/tehao_explosiondust.tik` | set-piece blast | todo | pak1.pk3 | sprites sandstorm01,tehaodebris_01,tehaosmoke_light,vsssource; surfaces transparency - retail look |
| `tik:models/emitters/tehao_pilarexplosion.tik` | set-piece blast | todo | pak1.pk3 | sprites tehaosmoke_light,thrownstone2,vsssource - retail look |
| `tik:models/emitters/tehao_skyexplosion.tik` | set-piece blast | todo | pak1.pk3 | sprites bridgecharge,vsssource; spawns sm_explosion.tik - retail look |
| `tik:models/emitters/tehao_vineyardexplosion.tik` | set-piece blast | todo | pak1.pk3 | sprites bh_dirt_piece,grndblst1,mortar_dirthit,tehaosmoke_light...; lights 2 - retail look |
| `tik:models/fx/bombabredaexplosion.tik` | set-piece blast | todo | pak1.pk3 | sprites smokegrenade; surfaces m18_smoke_gren; lights 1 - retail look |
| `tik:models/fx/bombblast_snow.tik` | set-piece blast | todo | pak1.pk3 | sprites bh_snow_puff,bombblast_bigdirt,vsssource,vsssource_new; spawns fx_bombblast_rock.tik,fx_bombblast_rockblack.tik - retail look |
| `tik:models/fx/explosionberlinbomb.tik` | set-piece blast | todo | pak1.pk3 | sprites bridgecharge,puffystuff_light,thrownstone2; spawns fx_smoketrail_concrete.tik - retail look |
| `tik:models/fx/fx_bombblast_rock.tik` | set-piece blast | todo | pak1.pk3 | sprites vsssource; surfaces dirtdebris_01; lights 1 - retail look |
| `tik:models/fx/fx_bombblast_rockblack.tik` | set-piece blast | todo | pak1.pk3 | sprites snowplume_01; surfaces dirtdebris_01; lights 1 - retail look |
| `tik:models/fx/fx_waterexplosion.tik` | set-piece blast | todo | zzzzzzzz_hd_fxfix.pk3 | sprites explosed,oceanspray,water_g,waterplume; lights 4 - retail look |
| `tik:models/fx/gas_mushroom_cloud.tik` | set-piece blast | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/fx/gas_mushroom_column.tik` | set-piece blast | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/fx/roof_banger.tik` | set-piece blast | todo | Pak0.pk3 | sprites bh_dirt_piece,grndblst1,mortar_dirthit,vsssource; spawns explosion_mine_shockwave.tik; lights 1 - retail look |
| `tik:models/fx/wall_exploder.tik` | set-piece blast | todo | Pak0.pk3 | sprites air_explosion,bh_stone_piece,fire_ring; spawns crate-jib-chunk.tik - retail look |
| `tik:models/emitters/explosion_bombdirt.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_dust,cfx_ember,cfx_fire_fb...; spawns explosion_bombdirt_shockwave.tik; lights 5 - fx_1025 (v1.10.37) |
| `tik:models/emitters/explosion_bombmetalwall.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/emitters/explosion_bombwall.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/emitters/explosion_bridge.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/emitters/explosion_mine.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; spawns explosion_mine_shockwave.tik; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/emitters/tehao_bridgeexplosion.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; spawns fx_smoketrail_concrete.tik; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/emitters/tehao_explosionwall.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; surfaces transparency; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/coop_blast_air.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_fire_fb,cfx_puff,cfx_smoke_fb; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/coop_blast_l.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/coop_blast_m.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/coop_blast_s.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/coop_blast_xl.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/fx_explosion.tik` | set-piece blast | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/emitters/coop_smokescreen.tik` | smoke grenade | excluded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites vsssource; lights 1 - Omaha only (m3l1a smoke barrage) - user 2026-11-24: Omaha stays excluded |
| `tik:models/fx/m18_smoke_grenadeexplosion.tik` | smoke grenade | todo | pak1.pk3 | sprites ; surfaces m18_smoke_gren - retail look |
| `tik:models/fx/nebelhandgranateexplosion.tik` | smoke grenade | todo | pak1.pk3 | sprites smokegrenade_german; surfaces germ_smoke_gren; lights 1 - retail look |
| `tik:models/fx/rdg-1_smoke_grenadeexplosion.tik` | smoke grenade | todo | pak1.pk3 | sprites smokegrenade_soviet; surfaces rdg-1_grenade; lights 1 - retail look |
| `tik:models/fx/signalsmoketrail.tik` | smoke grenade | todo | pak1.pk3 | sprites smokegrenade_german; lights 1 - retail look |
| `tik:models/fx/smokegrenadeexplosion.tik` | smoke grenade | todo | pak1.pk3 | sprites ; surfaces m2fraggrenade - retail look |
| `tik:models/fx/coop_screensmoke.tik` | smoke grenade | upgraded | zzzzzzzzzzzz_coop_fixes2.pk3 | sprites vsssource; surfaces m18_smoke_gren; lights 1 - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/cinematics_shootsmoke.tik` | smoke/steam | excluded | pak1.pk3 | sprites ; spawns cinematics_firetrail.tik,cinematics_smoketrail.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/fx_smokeexample.tik` | smoke/steam | excluded | Pak0.pk3 | sprites  - no sprite, no volumetric smoke, spawns nothing (solid debris / model only) |
| `tik:models/emitters/breath_emitter.tik` | smoke/steam | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/breath_steam_emitter.tik` | smoke/steam | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/cheapsmoke.tik` | smoke/steam | todo | pak1.pk3 | sprites smokegrenade; lights 1 - retail look |
| `tik:models/emitters/cinematics_groundsmoke.tik` | smoke/steam | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/ddaysmoke.tik` | smoke/steam | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/ddaysmoke2.tik` | smoke/steam | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/hexsmoke01.tik` | smoke/steam | todo | Pak0.pk3 | sprites ; vss fire - retail look |
| `tik:models/emitters/linger_smoke.tik` | smoke/steam | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/linger_smoke02.tik` | smoke/steam | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/maltasmoke.tik` | smoke/steam | todo | pak1.pk3 | sprites snowplume_01 - retail look |
| `tik:models/emitters/pipe_steam.tik` | smoke/steam | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/senn_smokey.tik` | smoke/steam | todo | Pak0.pk3 | sprites ; vss greasefire - retail look |
| `tik:models/emitters/smoke_smallfry.tik` | smoke/steam | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/smokestack1.tik` | smoke/steam | todo | Pak0.pk3 | sprites ; vss fire - retail look |
| `tik:models/emitters/tehao_steampipe.tik` | smoke/steam | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/tehao_steamysmoke.tik` | smoke/steam | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/tehaosmoke_e1l1.tik` | smoke/steam | todo | pak1.pk3 | sprites tehaosmoke_dark - retail look |
| `tik:models/fx/cannonsmoke.tik` | smoke/steam | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/fx/fx_cannonsmoke.tik` | smoke/steam | todo | Pak0.pk3 | sprites ; vss bulletimpact - retail look |
| `tik:models/fx/fx_edsmoke.tik` | smoke/steam | todo | pak1.pk3 | sprites smokegrenade_german - retail look |
| `tik:models/fx/fx_fattysmoke.tik` | smoke/steam | todo | zzzzzzzz_hd_fxfix.pk3 | sprites ; vss fire - retail look |
| `tik:models/fx/fx_lowsmoke.tik` | smoke/steam | todo | Pak0.pk3 | sprites ; vss heavy - retail look |
| `tik:models/fx/fx_trainsmoke.tik` | smoke/steam | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/steamworks.tik` | smoke/steam | todo | Pak0.pk3 | sprites oceanspray - retail look |
| `tik:models/fx/trainsmoke.tik` | smoke/steam | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/trainsteam_collision.tik` | smoke/steam | todo | pak1.pk3 | sprites vsssource - retail look |
| `tik:models/fx/trucksteam.tik` | smoke/steam | todo | pak1.pk3 | sprites puffystuff_dark,snowplume_01 - retail look |
| `tik:models/emitters/coop_smokecol.tik` | smoke/steam | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_puff; lights 1 - fx_1025 (v1.10.37) |
| `tik:models/emitters/debris_smoke.tik` | smoke/steam | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_puff; lights 1 - fx_1025 (v1.10.37) |
| `tik:models/emitters/norbigstacksmoke.tik` | smoke/steam | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_puff; lights 1 - fx_1025 (v1.10.37) |
| `tik:models/emitters/tehao_thicksmoke.tik` | smoke/steam | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_puff; lights 1 - fx_1025 (v1.10.37) |
| `tik:models/emitters/adamspark.tik` | sparks | todo | Pak0.pk3 | sprites corona_reg,vsssource; spawns bh_metal_fastpiece.tik - retail look |
| `tik:models/emitters/cinematics_shootsparks.tik` | sparks | todo | pak1.pk3 | sprites shootsparks; spawns cinematics_smoketrail.tik - retail look |
| `tik:models/emitters/electric_arc.tik` | sparks | todo | Pak0.pk3 | sprites electric - retail look |
| `tik:models/emitters/electric_panelmelt.tik` | sparks | todo | Pak0.pk3 | sprites corona_reg,corona_util,vsssource; spawns bh_metal_fastpiece.tik - retail look |
| `tik:models/emitters/generic_spark.tik` | sparks | todo | pak1.pk3 | sprites corona_white; spawns bh_metal_fastpiece.tik - retail look |
| `tik:models/emitters/generic_spark_big_pulse.tik` | sparks | todo | pak1.pk3 | sprites corona_white; spawns bh_metal_fastpiece.tik - retail look |
| `tik:models/emitters/generic_spark_small.tik` | sparks | todo | pak1.pk3 | sprites corona_util; spawns bh_metal_fastpiece.tik - retail look |
| `tik:models/emitters/welding_spark.tik` | sparks | todo | Pak0.pk3 | sprites corona_util,vsssource; spawns bh_metal_fastpiece.tik - retail look |
| `tik:models/fx/corona_brokenlight01.tik` | sparks | todo | pak1.pk3 | sprites ; surfaces corona_brokenlight01 - retail look |
| `tik:models/fx/trainsparks.tik` | sparks | todo | pak1.pk3 | sprites trainspark_01 - retail look |
| `tik:models/fx/trainsparks_collision.tik` | sparks | todo | pak1.pk3 | sprites trainspark_01 - retail look |
| `tik:models/fx/coop_hullspark.tik` | sparks | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites ; spawns bh_metal_fastpiece.tik - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `sprite:coop_blood_drop` | sprites | excluded | zzzzzz_co-op_hzm_mod_code.pk3 | other smoke/fire (by content); 32 px, 1 fr, gl_src_alpha gl_one_minus_src_alpha; img zzzzzz_co-op_hzm_mod_assets_tex.pk3 - blood / gore, not smoke or fire |
| `sprite:coop_bloodcloud` | sprites | excluded | zzzzzz_co-op_hzm_mod_code.pk3 | other smoke/fire (by content); 32 px, 1 fr, gl_src_alpha gl_one_minus_src_alpha; img zzzzzz_co-op_hzm_mod_assets_tex.pk3 - blood / gore, not smoke or fire |
| `sprite:air_explosion` | sprites | todo | pak1.pk3 | map fire/other smoke/fire (by content)/set-piece blast/vehicle/aircraft; 256 px, 10 fr, add; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bh_dirt_piece` | sprites | todo | pak1.pk3 | artillery/grenade/impacts/other smoke/fire (by content)/rocket/shell/set-piece blast/vehicle/aircraft; 8 px, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bh_metal_spark` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | impacts; 128 px x0.125, 1 fr, gl_one gl_one; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bh_sand` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | impacts; 128 px x0.5, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bh_snow_puff` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/flak/impacts/rocket/shell/set-piece blast; 128 px x0.25, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bh_snow_puff1` | sprites | todo | zzzzzz_co-op_hzm_mod_code.pk3 | impacts; 128 px, 1 fr, gl_src_alpha gl_one_minus_src_alpha; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bh_stone_piece` | sprites | todo | pak1.pk3 | impacts/set-piece blast; 8 px, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bh_water_ring` | sprites | todo | pak1.pk3 | impacts; 32 px, 1 fr, gl_src_alpha gl_one; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bigsplash` | sprites | todo | pak1.pk3 | other smoke/fire (by content); 256 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bodyhitpuff` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | impacts; 256 px x0.125, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bombblast_bigdirt` | sprites | todo | pak1.pk3 | set-piece blast; 256 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:bridgecharge` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/muzzle/other smoke/fire (by content)/rocket/shell/set-piece blast/vehicle/aircraft; 512 px x0.25, 1 fr, alphaadd; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:burst` | sprites | todo | pak1.pk3 | set-piece blast; 128 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:c47skytrain_burst1` | sprites | todo | pak1.pk3 | vehicle/aircraft; 32 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:c47skytrain_fiery` | sprites | todo | pak1.pk3 | vehicle/aircraft; 256 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:c47skytrain_fiery1` | sprites | todo |  | flak; ? px, 1 fr, -; img MISSING - retail sprite (an HD upscale alone is still todo) |
| `sprite:c47skytrain_fiery2` | sprites | todo |  | flak; ? px, 1 fr, -; img MISSING - retail sprite (an HD upscale alone is still todo) |
| `sprite:c47skytrain_smoke2` | sprites | todo | pak1.pk3 | vehicle/aircraft; 128 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:c47skytrain_smoke3` | sprites | todo | pak1.pk3 | vehicle/aircraft; 128 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:campfire_01` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | muzzle/vehicle/aircraft; 512 px x0.25, 1 fr, alphaadd; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:campfire_02` | sprites | todo | pak1.pk3 | muzzle; 128 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:campfire_03` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | muzzle/vehicle/aircraft; 512 px x0.25, 1 fr, alphaadd; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:cardboard_light` | sprites | todo | pak1.pk3 | dust/debris/impacts; 64 px, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:cinematic_sparks` | sprites | todo | pak1.pk3 | set-piece blast/vehicle/aircraft; 64 px, 6 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:cinematicexplosion_02` | sprites | todo | pak1.pk3 | set-piece blast; 256 px, 19 fr, alphaadd; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:corona_reg` | sprites | todo | pak1.pk3 | map fire/sparks; 128 px, 1 fr, add; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:corona_util` | sprites | todo | pak1.pk3 | impacts/map fire/sparks; 256 px, 1 fr, add; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:corona_white` | sprites | todo | pak1.pk3 | sparks; 64 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:dirtcloud` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | other smoke/fire (by content)/set-piece blast; 256 px x0.5, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:dirtplume` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/grenade; 256 px x0.5, 1 fr, -; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:dustdrop` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/dust/debris/impacts; 256 px x0.5, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:electric` | sprites | todo | pak1.pk3 | sparks; 256 px, 3 fr, alphaadd; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:emberblast` | sprites | todo | pak1.pk3 | rocket/shell; 256 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:enginesmoke_01` | sprites | todo | pak1.pk3 | other smoke/fire (by content)/vehicle/aircraft; 64 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:explosed` | sprites | todo | pak1.pk3 | grenade/other smoke/fire (by content)/set-piece blast/vehicle/aircraft; 64 px, 1 fr, alphaadd; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:explosed2` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | grenade/other smoke/fire (by content)/set-piece blast/vehicle/aircraft; 256 px x0.25, 1 fr, alphaadd; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:explosion1` | sprites | todo |  | grenade; ? px, 1 fr, -; img MISSING - retail sprite (an HD upscale alone is still todo) |
| `sprite:explosion_burst` | sprites | todo | pak1.pk3 | muzzle; 128 px, 8 fr, gl_one gl_one; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:explshock` | sprites | todo |  | grenade; ? px, 1 fr, -; img MISSING - retail sprite (an HD upscale alone is still todo) |
| `sprite:explsmoke` | sprites | todo |  | grenade; ? px, 1 fr, -; img MISSING - retail sprite (an HD upscale alone is still todo) |
| `sprite:fallingdirt` | sprites | todo | pak1.pk3 | dust/debris; 16 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:feather_01` | sprites | todo | pak1.pk3 | other smoke/fire (by content); 64 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:feather_02` | sprites | todo | pak1.pk3 | other smoke/fire (by content); 64 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:fire_ring` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | grenade/map fire/other smoke/fire (by content)/set-piece blast/vehicle/aircraft; 576 px x0.25, 1 fr, alphaadd; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:fire_ring2` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | rocket/shell; 576 px x0.25, 1 fr, alphaadd; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:fireball_pj` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | map fire; 128 px x0.5, 15 fr, alphaadd; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:firefly` | sprites | todo | pak1.pk3 | map fire; 16 px, 1 fr, add; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:flak_cloud01` | sprites | todo | pak1.pk3 | flak; 128 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:flak_cloud03` | sprites | todo | pak1.pk3 | flak; 128 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:flak_cloud04` | sprites | todo | pak1.pk3 | flak; 128 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:flakflash_skybox` | sprites | todo | pak1.pk3 | flak; 64 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:flaksmoke_skybox` | sprites | todo | pak1.pk3 | flak; 64 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:generalfireball_01` | sprites | todo | pak1.pk3 | other smoke/fire (by content); 512 px, 1 fr, alphaadd; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:generalspark_01` | sprites | todo | pak1.pk3 | other smoke/fire (by content); 32 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:glass_small` | sprites | todo | pak1.pk3 | dust/debris/impacts; 32 px, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:gren_boom` | sprites | todo | pak1.pk3 | artillery/grenade/rocket/shell; 256 px, 34 fr, add; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:gren_explosion` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | map fire/muzzle/set-piece blast/vehicle/aircraft; 128 px x0.5, 15 fr, add; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:grenadefire` | sprites | todo | pak1.pk3 | flak/grenade/rocket/shell; 128 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:grndblst1` | sprites | todo | pak1.pk3 | set-piece blast/vehicle/aircraft; 64 px, 1 fr, gl_src_alpha gl_one; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:mortar_dirthit` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/dust/debris/grenade/other smoke/fire (by content)/rocket/shell/set-piece blast; 1024 px x0.25, 1 fr, -; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:mortar_dirthit2` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/grenade; 1024 px x0.25, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:mortar_snowhit` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/dust/debris/grenade/other smoke/fire (by content)/rocket/shell; 1024 px x0.25, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:muzzleblast_01` | sprites | todo | pak1.pk3 | flak/muzzle; 128 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:muzzlecharge` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | flak/muzzle; 512 px x0.25, 1 fr, alphaadd; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:muzzlecharge_02` | sprites | todo | pak1.pk3 | muzzle; 128 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:oceanspray` | sprites | todo | pak1.pk3 | grenade/other smoke/fire (by content)/set-piece blast/smoke/steam; 64 px, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:puffystuff_dark` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/flak/muzzle/rocket/shell/set-piece blast/smoke/steam/vehicle/aircraft; 512 px x0.25, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:puffystuff_light` | sprites | todo | pak1.pk3 | artillery/muzzle/rocket/shell/set-piece blast/vehicle/aircraft; 512 px, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:sandstorm01` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | dust/debris/set-piece blast; 256 px x0.25, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:sandstorm02` | sprites | todo | pak1.pk3 | dust/debris; 256 px, 1 fr, gl_src_alpha gl_one_minus_src_alpha; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:sandstorm_gust` | sprites | todo | pak1.pk3 | dust/debris; 64 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:shootsparks` | sprites | todo | pak1.pk3 | sparks; 32 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:smokegrenade` | sprites | todo | pak1.pk3 | impacts/set-piece blast/smoke/steam; 128 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:smokegrenade_german` | sprites | todo | pak1.pk3 | smoke grenade/smoke/steam; 128 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:smokegrenade_soviet` | sprites | todo | pak1.pk3 | smoke grenade; 128 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:smoketrail_fire` | sprites | todo | pak1.pk3 | vehicle/aircraft; 128 px, 1 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:snowclump` | sprites | todo | pak1.pk3 | artillery/dust/debris/grenade/impacts/other smoke/fire (by content)/rocket/shell; 16 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:snowplume_01` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/dust/debris/flak/grenade/muzzle/other smoke/fire (by content)/set-piece blast/smoke/steam/vehicle/aircraft; 256 px x0.25, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:snowplume_02` | sprites | todo | pak1.pk3 | artillery/other smoke/fire (by content); 64 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:snowplume_k5` | sprites | todo | pak1.pk3 | muzzle; 256 px, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:splinter1` | sprites | todo | pak1.pk3 | artillery; 32 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:splinter2` | sprites | todo | pak1.pk3 | artillery; 32 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:stonechip` | sprites | todo | pak1.pk3 | grenade/impacts; 16 px, 1 fr, -; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:strafe_snowhit2` | sprites | todo | pak1.pk3 | artillery/impacts/other smoke/fire (by content); 64 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:tehao_candellight_02` | sprites | todo | pak1.pk3 | map fire; 32 px, 64 fr, alphaadd; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:tehaodebris_01` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | dust/debris/set-piece blast; 128 px x1, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:tehaoripple` | sprites | todo | pak1.pk3 | other smoke/fire (by content); 64 px, 1 fr, gl_src_alpha gl_one; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:tehaoripple_sub` | sprites | todo | pak1.pk3 | other smoke/fire (by content); 64 px, 1 fr, gl_src_alpha gl_one; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:tehaosmoke_dark` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | map fire/smoke/steam/vehicle/aircraft; 512 px x0.25, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:tehaosmoke_light` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | other smoke/fire (by content)/set-piece blast/vehicle/aircraft; 512 px x0.25, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:textures/effects/woodsplinters` | sprites | todo | pak1.pk3 | dust/debris/other smoke/fire (by content); 128 px, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:thrownstone1` | sprites | todo | pak1.pk3 | set-piece blast; 64 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:thrownstone2` | sprites | todo | pak1.pk3 | artillery/rocket/shell/set-piece blast/vehicle/aircraft; 64 px, 1 fr, blend; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:trainspark_01` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/flak/muzzle/other smoke/fire (by content)/rocket/shell/sparks; 128 px x0.25, 1 fr, alphaadd; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:vsssource` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/dust/debris/flak/grenade/impacts/map fire/muzzle/other smoke/fire (by content)/rocket/shell/set-piece blast/smoke grenade/smoke/steam/sparks/vehicle/aircraft/volumetric smoke; 128 px x0.25, 1 fr, gl_src_alpha gl_one_minus_src_alpha; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:vsssource2` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | impacts/muzzle/other smoke/fire (by content)/set-piece blast/vehicle/aircraft/volumetric smoke; 128 px x0.25, 1 fr, gl_src_alpha gl_one_minus_src_alpha; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:vsssource_new` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | artillery/dust/debris/grenade/other smoke/fire (by content)/rocket/shell/set-piece blast; 128 px x0.25, 1 fr, gl_src_alpha gl_one_minus_src_alpha; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:water_drop1` | sprites | todo | pak1.pk3 | other smoke/fire (by content); 16 px, 1 fr, add; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:water_g` | sprites | todo | pak1.pk3 | grenade/other smoke/fire (by content)/set-piece blast; 64 px, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:waterblast01` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | other smoke/fire (by content); 256 px x0.5, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:waterplume` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | grenade/impacts/set-piece blast; 256 px x0.5, 1 fr, blend; img zzzzzz_hd_fx.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:willys_dirt` | sprites | todo | pak1.pk3 | dust/debris; 256 px, 1 fr, gl_src_alpha gl_one_minus_src_alpha; img pak1.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:willys_dust` | sprites | todo | zzzzzzzzzz_coop_hd_discstock.pk3 | dust/debris; 512 px x0.25, 1 fr, gl_src_alpha gl_one_minus_src_alpha; img zzzzzzzzzz_coop_hd_discstock.pk3 - retail sprite (an HD upscale alone is still todo) |
| `sprite:cfx_dust` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | artillery/set-piece blast; 256 px, 24 fr, blend; img zzzzzzzzzzzzz_coop_fx.pk3 - our own flipbook / sprite |
| `sprite:cfx_ember` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | artillery/flak/grenade/map fire/other smoke/fire (by content)/rocket/shell/set-piece blast/vehicle/aircraft; 32 px, 1 fr, add; img zzzzzzzzzzzzz_coop_fx.pk3 - our own flipbook / sprite |
| `sprite:cfx_fin_flame` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | map fire; 256 px, 26 fr, gl_src_alpha gl_one; img zzzzzzzzzzzzz_coop_fx.pk3 - our own flipbook / sprite |
| `sprite:cfx_fin_flame_b` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | map fire; 256 px, 26 fr, gl_src_alpha gl_one; img zzzzzzzzzzzzz_coop_fx.pk3 - our own flipbook / sprite |
| `sprite:cfx_fire_fb` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | artillery/flak/grenade/other smoke/fire (by content)/set-piece blast/vehicle/aircraft; 512 px, 36 fr, add; img zzzzzzzzzzzzz_coop_fx.pk3 - our own flipbook / sprite |
| `sprite:cfx_fire_tk` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | artillery/rocket/shell/set-piece blast/vehicle/aircraft; 512 px, 40 fr, add; img zzzzzzzzzzzzz_coop_fx.pk3 - our own flipbook / sprite |
| `sprite:cfx_flame` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | map fire/vehicle/aircraft; 256 px, 26 fr, add; img zzzzzzzzzzzzz_coop_fx.pk3 - our own flipbook / sprite |
| `sprite:cfx_puff` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | artillery/flak/grenade/map fire/other smoke/fire (by content)/rocket/shell/set-piece blast/smoke/steam/vehicle/aircraft; 256 px, 16 fr, blend; img zzzzzzzzzzzzz_coop_fx.pk3 - our own flipbook / sprite |
| `sprite:cfx_smoke_fb` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | artillery/flak/grenade/other smoke/fire (by content)/set-piece blast/vehicle/aircraft; 256 px, 40 fr, blend; img zzzzzzzzzzzzz_coop_fx.pk3 - our own flipbook / sprite |
| `sprite:cfx_smoke_tk` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | artillery/rocket/shell/set-piece blast/vehicle/aircraft; 256 px, 32 fr, blend; img zzzzzzzzzzzzz_coop_fx.pk3 - our own flipbook / sprite |
| `sprite:coop_snowplume` | sprites | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | impacts; 64 px, 1 fr, blend; img pak1.pk3 - our own flipbook / sprite |
| `surface:bazookashell` | surfaces | excluded | zzzzzz-HRRTM_Pak4_Weapons.pk3 | artillery; 2048 px, 1 fr, -; img zzzzzzzzzz_coop_hd_m3l1a.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bh_foliage_leaf` | surfaces | excluded | pak1.pk3 | impacts; 32 px, 1 fr, blend; img Pak0.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bh_grass_piece` | surfaces | excluded | pak1.pk3 | impacts; 8 px, 1 fr, blend; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bh_metal_fastpiece` | surfaces | excluded | pak1.pk3 | impacts; 8 px, 1 fr, add; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bh_stone_fastpiece` | surfaces | excluded |  | impacts; ? px, 1 fr, -; img MISSING - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bh_wood_piece` | surfaces | excluded | pak1.pk3 | impacts; 8 px, 1 fr, blend; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:blockcrete` | surfaces | excluded | pak1.pk3 | dust/debris; 256 px, 1 fr, -; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bp_debris1` | surfaces | excluded | pak1.pk3 | dust/debris; 64 px, 1 fr, -; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bp_debris2` | surfaces | excluded | pak1.pk3 | dust/debris; 64 px, 1 fr, -; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bp_debris2g` | surfaces | excluded | pak1.pk3 | dust/debris; 64 px, 1 fr, -; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bp_debris3` | surfaces | excluded | pak1.pk3 | dust/debris; 64 px, 1 fr, -; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bp_debris3g` | surfaces | excluded | pak1.pk3 | dust/debris; 64 px, 1 fr, -; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:candle_standing_t` | surfaces | excluded | pak1.pk3 | map fire; 512 px, 1 fr, add; img zzzzzzz_dds_hdmem.pk3 - model skin (smoke-grenade body, candle holder / candle wax), not an effect surface |
| `surface:candleholder` | surfaces | excluded | pak1.pk3 | map fire; 512 px, 1 fr, add; img zzzzzzz_dds_hdmem.pk3 - model skin (smoke-grenade body, candle holder / candle wax), not an effect surface |
| `surface:concrete1` | surfaces | excluded | pak1.pk3 | dust/debris; 128 px, 1 fr, -; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:concrete2` | surfaces | excluded | pak1.pk3 | dust/debris; 128 px, 1 fr, -; img zzzzzz_hd_fx.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:concretedebris_01` | surfaces | excluded | pak1.pk3 | vehicle/aircraft; 64 px, 1 fr, blend; img pak1.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:crate-jibs` | surfaces | excluded | Pak0.pk3 | dust/debris; 256 px, 1 fr, blend; img zzzzzzzzzz_coop_hd_discstock.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:deathsod_01` | surfaces | excluded | pak1.pk3 | vehicle/aircraft; 64 px, 1 fr, blend; img pak1.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:dirtdebris_01` | surfaces | excluded | pak1.pk3 | set-piece blast; 64 px, 1 fr, blend; img pak1.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:germ_smoke_gren` | surfaces | excluded | pak1.pk3 | smoke grenade; 1024 px, 1 fr, -; img zzzzzzz_dds_override.pk3 - model skin (smoke-grenade body, candle holder / candle wax), not an effect surface |
| `surface:m18_smoke_gren` | surfaces | excluded | pak1.pk3 | set-piece blast/smoke grenade; 2048 px, 1 fr, -; img zzzzzzzzzz_coop_hd_wpn_1low.pk3 - model skin (smoke-grenade body, candle holder / candle wax), not an effect surface |
| `surface:m2fraggrenade` | surfaces | excluded | Pak0.pk3 | smoke grenade; 1024 px, 1 fr, -; img zzzzzzz_dds_override.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:metaldebris_01` | surfaces | excluded | pak1.pk3 | other smoke/fire (by content); 32 px, 1 fr, blend; img pak1.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:miniaa` | surfaces | excluded | pak1.pk3 | flak; 32 px, 1 fr, blend; img pak1.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:mortarhit` | surfaces | excluded | pak1.pk3 | artillery; ? px, 1 fr, blend; img MISSING - model skin (grenade body, holder, debris), not an effect surface |
| `surface:rdg-1_grenade` | surfaces | excluded | pak1.pk3 | smoke grenade; 1024 px, 1 fr, -; img zzzzzzz_dds_override.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:thrownstone3` | surfaces | excluded | pak1.pk3 | vehicle/aircraft; 64 px, 1 fr, blend; img pak1.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:transparency` | surfaces | excluded | pak1.pk3 | map fire/set-piece blast; 32 px, 1 fr, blend; img zzzzzzzzzz_coop_hd_m3l1a.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:waterpuddle` | surfaces | excluded | pak1.pk3 | other smoke/fire (by content); 128 px, 1 fr, blend; img pak1.pk3 - model skin (grenade body, holder, debris), not an effect surface |
| `surface:bh_stone_puff` | surfaces | todo | pak1.pk3 | impacts; 64 px, 7 fr, blend; img zzzzzz_hd_fx.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:bh_wood_puff` | surfaces | todo | pak1.pk3 | impacts; 16 px, 7 fr, blend; img Pak2.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:bh_wood_puff_simple` | surfaces | todo | pak1.pk3 | impacts; 16 px, 1 fr, blend; img Pak2.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:corona_brokenlight01` | surfaces | todo | pak1.pk3 | sparks; 16 px, 63 fr, add; img pak1.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:corona_spiky` | surfaces | todo | pak1.pk3 | map fire; 64 px, 1 fr, alphaadd; img pak1.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:fire_back` | surfaces | todo | pak1.pk3 | map fire; 512 px, 32 fr, add; img zzzzzzzzzz_coop_hd_discstock.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:fire_front` | surfaces | todo | pak1.pk3 | map fire; 512 px, 32 fr, add; img zzzzzzzzzz_coop_hd_discstock.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:fire_middle` | surfaces | todo | pak1.pk3 | map fire; 512 px, 32 fr, add; img zzzzzzzzzz_coop_hd_discstock.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:lampflame` | surfaces | todo | pak1.pk3 | map fire; 64 px, 7 fr, add; img zzzzzz_hd_fx.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:sm_explosion_01` | surfaces | todo | pak1.pk3 | set-piece blast; 128 px, 27 fr, alphaadd; img pak1.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:sm_explosion_02` | surfaces | todo | pak1.pk3 | set-piece blast; 128 px, 27 fr, alphaadd; img pak1.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:sm_explosion_03` | surfaces | todo | pak1.pk3 | set-piece blast; 128 px, 27 fr, alphaadd; img pak1.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:wplumelarge` | surfaces | todo | pak1.pk3 | dust/debris; 128 px, 1 fr, blend; img Pak2.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:wplumesmall` | surfaces | todo | pak1.pk3 | dust/debris; 128 px, 1 fr, blend; img Pak2.pk3 - effect surface on a model-based effect (unitsquare / spritebeam / fire planes) |
| `surface:coop_dustveil_day` | surfaces | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | dust/debris; 128 px, 30 fr, blend; img pak1.pk3 - our own effect surface |
| `surface:coop_dustveil_night` | surfaces | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | dust/debris; 128 px, 30 fr, blend; img zzzzzz_co-op_hzm_mod_assets_tex.pk3 - our own effect surface |
| `surface:coop_dustveil_rain` | surfaces | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | dust/debris; 128 px, 30 fr, blend; img zzzzzz_co-op_hzm_mod_assets_tex.pk3 - our own effect surface |
| `surface:coop_dustveil_rainnight` | surfaces | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | dust/debris; 128 px, 30 fr, blend; img zzzzzz_co-op_hzm_mod_assets_tex.pk3 - our own effect surface |
| `surface:coop_dustveil_snow` | surfaces | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | dust/debris; 128 px, 30 fr, blend; img zzzzzz_co-op_hzm_mod_assets_tex.pk3 - our own effect surface |
| `surface:coop_dustveil_snownight` | surfaces | upgraded | zzzzzz_co-op_hzm_mod_code.pk3 | dust/debris; 128 px, 30 fr, blend; img zzzzzz_co-op_hzm_mod_assets_tex.pk3 - our own effect surface |
| `tik:models/emitters/c47_fleet.tik` | vehicle/aircraft | excluded | pak1.pk3 | sprites ; spawns c47_particle.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/emitters/shermansmoke.tik` | vehicle/aircraft | excluded | Pak0.pk3 | sprites vsssource - Omaha only (m3l1a coopified + precache) - user 2026-11-24: Omaha stays excluded |
| `tik:models/fx/explosionstukaround.tik` | vehicle/aircraft | excluded | pak1.pk3 | sprites ; explosioneffect heavyshell - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/fx/fx_pe8_fleet.tik` | vehicle/aircraft | excluded | pak1.pk3 | sprites ; spawns pe8_particle.tik - wrapper - its look is the tiks / explosion effect it spawns (each listed on its own row) |
| `tik:models/emitters/aircraft_explosion.tik` | vehicle/aircraft | todo | Pak0.pk3 | sprites air_explosion,vsssource2; spawns ibeam_piece.tik,metal_section.tik - retail look |
| `tik:models/emitters/cinematics_firetrail.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites cinematic_sparks,vsssource; surfaces smoketrail_fire - retail look |
| `tik:models/emitters/cinematics_smoketrail.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites smoketrail_fire,vsssource; surfaces smoketrail_fire - retail look |
| `tik:models/emitters/explosion_tank_sideplume.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites bridgecharge,campfire_01,campfire_03,tehaosmoke_dark - retail look |
| `tik:models/emitters/plane_smoke.tik` | vehicle/aircraft | todo | Pak0.pk3 | sprites vsssource - retail look |
| `tik:models/emitters/planesmoke.tik` | vehicle/aircraft | todo | Pak0.pk3 | sprites ; vss greasefire - retail look |
| `tik:models/emitters/planesmokefly.tik` | vehicle/aircraft | todo | Pak0.pk3 | sprites ; vss greasefire - retail look |
| `tik:models/emitters/planesmokeplume.tik` | vehicle/aircraft | todo | Pak0.pk3 | sprites ; vss steam - retail look |
| `tik:models/emitters/planesmokeplumered.tik` | vehicle/aircraft | todo | Pak0.pk3 | sprites ; vss steam - retail look |
| `tik:models/emitters/planesmokeplumeyellow.tik` | vehicle/aircraft | todo | Pak0.pk3 | sprites ; vss steam - retail look |
| `tik:models/emitters/tanksmoke.tik` | vehicle/aircraft | todo | Pak0.pk3 | sprites ; vss greasefire - retail look |
| `tik:models/emitters/tehao_tankcrashwall.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites bridgecharge,campfire_01,grndblst1,tehaosmoke_light...; spawns bp_debris1.tik - retail look |
| `tik:models/fx/c47_collision_fire.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites bridgecharge,c47skytrain_burst1 - retail look |
| `tik:models/fx/c47_collision_firespare.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites c47skytrain_burst1,c47skytrain_fiery - retail look |
| `tik:models/fx/c47_collision_smoke.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites c47skytrain_smoke2,c47skytrain_smoke3 - retail look |
| `tik:models/fx/fx_flying_stuka_explosion.tik` | vehicle/aircraft | todo | Pak0.pk3 | sprites air_explosion,explosed2,fire_ring,vsssource - retail look |
| `tik:models/fx/fx_smoketrail_concrete.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites puffystuff_light; surfaces thrownstone3; lights 1 - retail look |
| `tik:models/fx/fx_smoketrail_concrete_big.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites puffystuff_light; surfaces concretedebris_01; lights 1 - retail look |
| `tik:models/fx/fx_smoketrail_dirt.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites puffystuff_dark; surfaces deathsod_01; lights 1 - retail look |
| `tik:models/fx/supplytruck_dmg.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites enginesmoke_01,snowplume_01 - retail look |
| `tik:models/fx/veltro_explode2.tik` | vehicle/aircraft | todo | pak1.pk3 | sprites gren_explosion,vsssource; spawns gas_mushroom_cloud.tik - retail look |
| `tik:models/emitters/coop_planesmoke_trail.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites campfire_01,tehaosmoke_dark,tehaosmoke_light - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/emitters/coop_wreck.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_flame,cfx_puff; lights 2 - fx_1025 (v1.10.37) |
| `tik:models/emitters/coop_wreck_lo.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_flame,cfx_puff; lights 1 - fx_1025 (v1.10.37) |
| `tik:models/emitters/coop_wreck_pops.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites cfx_ember,cfx_fire_fb; lights 3 - fx_1025 (v1.10.37) |
| `tik:models/emitters/explosion_tank.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; spawns explosion_tank_sideplume.tik; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/emitters/explosion_tank2.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; spawns higgins_mushroom.tik; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/coop_tank_explosion.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tex.pk3 | sprites air_explosion,explosed,vsssource; spawns ibeam_piece.tik - mod's own effect (gun smoke, screens, finale fires, plane trail, dust veils) |
| `tik:models/fx/exp_tank_gen.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/exp_truck.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/fx_bike_explosion.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_fb,cfx_puff...; spawns bp_debris1.tik,ibeam_piece.tik; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/fx_stuka_explosion.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; spawns bp_debris1.tik,exp_dynamic2.tik; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/fx_tank_explosion.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; spawns ibeam_piece.tik; lights 4 - fx_1025 (v1.10.37) |
| `tik:models/fx/fx_truck_explosion.tik` | vehicle/aircraft | upgraded | zzzzzz_co-op_hzm_mod_assets_tey.pk3 | sprites bh_dirt_piece,cfx_ember,cfx_fire_tk,cfx_puff...; spawns bp_debris1.tik,gas_mushroom_cloud.tik,heavy_pipe.tik; lights 4 - fx_1025 (v1.10.37) |
| `vss:bulletimpact` | volumetric smoke | todo |  | renders VSSSource.spr / VSSSource2.spr (cg_volumetricsmoke.cpp:1167) - volumetric smoke type - PLAN Phase 1.2 |
| `vss:fire` | volumetric smoke | todo |  | renders VSSSource.spr / VSSSource2.spr (cg_volumetricsmoke.cpp:1167) - volumetric smoke type - PLAN Phase 1.2 |
| `vss:greasefire` | volumetric smoke | todo |  | renders VSSSource.spr / VSSSource2.spr (cg_volumetricsmoke.cpp:1167) - volumetric smoke type - PLAN Phase 1.2 |
| `vss:heavy` | volumetric smoke | todo |  | renders VSSSource.spr / VSSSource2.spr (cg_volumetricsmoke.cpp:1167) - volumetric smoke type - PLAN Phase 1.2 |
| `vss:mist` | volumetric smoke | todo |  | renders VSSSource.spr / VSSSource2.spr (cg_volumetricsmoke.cpp:1167) - volumetric smoke type - PLAN Phase 1.2 |
| `vss:steam` | volumetric smoke | todo |  | renders VSSSource.spr / VSSSource2.spr (cg_volumetricsmoke.cpp:1167) - volumetric smoke type - PLAN Phase 1.2 |
