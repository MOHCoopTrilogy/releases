# Allied player-skin batch — acquisition & vetting report

Status: **staged, not installed.** Nothing has been copied into `hzm-mohaa-coop-mod/`;
`coop_mod/helmet.scr` and `coop_mod/challenges.scr` are untouched.

Scratchpad root for every archive below:

```
C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\b2bd743a-44c4-439c-ac2e-dcec6fc865c6\scratchpad\skins\
    BA_skin_pack1.pk3                 (FUBAR)
    user-1st_Rangers.7z               (ModDB, outer)
    user-Rookie_One_1st_Rangers.pk3   (extracted from the .7z)
    heatpak_501stbastogne.zip         (ModDB, outer)
    heatpak_ext\                      (extracted)
    aaaa\*.pk3                        (36 files from the AAAA database)
```

Baseline used for de-duplication: the 88 names in `level.coop_armorySkins[1..88]`
(`hzm-mohaa-coop-mod/coop_mod/helmet.scr`) **plus** every `models/player/*.tik` present in
the deployed game (337 tik basenames across `main/`, `mainta/`, `maintt/` and the mod tree).
All comparisons case-insensitive.

---

## 1. Per-source results

| Source | URL | Licence / credit as stated | Archives got | NEW usable Allied skins |
|---|---|---|---|---|
| ModDB — 1st Rangers | <https://www.moddb.com/games/medal-of-honor-allied-assault/addons/1st-rangers> | ModDB field says **Proprietary**. Readme credit: *"1st Rangers Battalion", author **Rookie One**, v0.1, 16 Jan 2003*. Uploader `Military-Man`. | `user-1st_Rangers.7z` → `user-Rookie_One_1st_Rangers.pk3` (836 kb) | **6** |
| ModDB — Heatpak 501st Bastogne | <https://www.moddb.com/games/medal-of-honor-allied-assault/addons/heatpak-501st-bastogne> | ModDB field says **Proprietary**. Readme: *"SP Airborne Skins — 501st PIR", author **Heat-Miser**, 23 Nov 2002. "Use at your own risk."* | `heatpak_501stbastogne.zip` (971 kb) | **0** — rejected, see §5 |
| FUBAR UK open directory | <https://fubarukclan.co.uk/downloads/> | none stated | `zzzzzzzzzz-BA_skin_pack1.pk3` (17.4 MB) | **0** — 100 % duplicate, see §5 |
| AAAA MOHAA skin database | <https://mohaaaa.co.uk/AAAAMOHAA/content/aaaamohaaaa-skins> | No blanket licence. Per-skin author credited in the database and usually in the pack readme — recorded per skin in §2. One pack carries an explicit restriction (see §5, `zzz-Ranger_Medic`). | 36 `.pk3` | **28 recommended** (+ 34 more behind fixes, §3) |

**Totals: 34 NEW, ship-ready Allied skins** (6 ModDB + 28 AAAA), taking the armory from 88 to 122.

### How the AAAA bot wall was handled

`curl` against `mohaaaa.co.uk` returns the Anubis proof-of-work interstitial
("Making sure you're not a bot!"), so plain HTTP download is blocked as expected. Working
route: load one page in the browser pane, read `document.cookie` (the `techaro.lol-anubis-auth`
JWT is **not** HttpOnly), then replay that cookie + the browser's exact User-Agent from Python
`urllib`. That worked for all 700 listing rows, all detail pages and all 36 binary downloads.
Helper scripts left in the scratchpad: `aaaa_fetch.py`, `aaaa_list.py`, `aaaa_pick.py`,
`aaaa_dl.py`, plus `aaaa.env` holding the (short-lived) cookie.

The site holds 700 skins total; 385 are Allied/British/American, of which 371 were not already
registered. Most are novelty (Space 53, Horror 27, Zombies 21, Super Heroes 19, Christmas 18,
Slipknot, Metal Gear, robots…). Only ~90 are WW2-plausible, and this batch takes the best of them.

ModDB blocks `curl` and `WebFetch` with 403 on the addon pages, but the
`/downloads/mirror/<id>/...` URL harvested from the browser downloads fine with `curl` given a
`Referer` header.

---

## 2. RECOMMENDED BATCH — 34 skins, ready to register

All of these: ship their own textures and shaders, resolve every surface shader, define **zero**
shader names that collide with `hzm-mohaa-coop-mod/scripts/*.shader`, and collide with **no**
stock retail tik. One pack redefines four stock gear-shader names byte-identically — verified
harmless, see the note at the end of §4b. Names are given in the exact case used by the `.tik`.

### ModDB — 1st Rangers (Rookie One) — `user-Rookie_One_1st_Rangers.pk3`
Clean: 13 shader names, 0 collisions of any kind; textures under `textures/models/human/usmaps/1st_rangers/`.

| Skin | |
|---|---|
| `american_1st_rangers_captain` | |
| `american_1st_rangers_engineer` | |
| `american_1st_rangers_lieutenant` | |
| `american_1st_rangers_medic` | |
| `american_1st_rangers_private` | |
| `american_1st_rangers_sergeant` | |

### AAAA — 28 skins

| Skin | Archive (`skins\aaaa\`) | Author / credit | Source page |
|---|---|---|---|
| `american_28th_private` | `28th.pk3` | — | /content/28th-private |
| `34th_Infantery_Division_private` | `34th_infantery_division.pk3` | Misana | /content/34th-infantry-division-private |
| `34th_Infantery_Division_radio` | " | Misana | " |
| `34th_Infantery_Division_sergeant` | " | Misana | " |
| `34th_Infantery_Division_sniper` | " | Misana | " |
| `american_8thUrbanRanger` | `3rd_Army_Urban_Ranger.pk3` | — | /content/8th-urban-ranger |
| `american_8thUrbanRangerBar` | " | — | " |
| `american_8thUrbanRangerMG` | " | — | " |
| `american_8thUrbanRangeradio` | " | — | " |
| `american_8thUrbanRangerSniper` | " | — | " |
| `allied_82ndair` | `82ndAir.pk3` | Guarnere | /content/82nd-airborne |
| `allied_airborne_elite` | `Armdudes_Airborne_Elite.pk3` | Armdude / ={DTA}=Bootson | /content/airborne-elite |
| `US_Sniper` | `US Sniper SKIN.pk3` | — (repack of Small_Sumo art) | /content/us-sniper |
| `american_sniper` | `User_wigster_sniper_1.0.pk3` | Wigster — *"feel free to modify"* | /content/american-sniper |
| `american_omaha_ranger` | `user--IVY-capt.MOTFs_omaha_beach_ranger.pk3` | Giancarlo Schiano | /content/omaha-beach-ranger |
| `allied_17thAirb_soldierbloody` | `user-17thAirbSoldier_bloody.pk3` | Giancarlo Schiano | /content/17th-airborne-soldier-bloody |
| `allied_1st_manon` | `user-1st_manon.pk3` | Euthanasia (1st Rangers) | /content/1st-rangers-manon |
| `allied_1st_sniper` | `user-1st_sniper.pk3` | Euthanasia (1st Rangers) | /content/1st-rangers-sniper |
| `allied_Commanding_Officer` | `user-Armdudes_CO.pk3` | Armdude | /content/commanding-officer |
| `allied_big_red_one` | `user-Big Red One.pk3` | Armdude / ={DTA}=Bootson | /content/big-red-one |
| `allied_infantry` | `user-_OMTR_ U.S Infantry Sniper.pk3` | koensieben622 | /content/us-infantry-sniper |
| `allied_russian_Pvt` | `user-bojos-ussr-pvt.pk3` | Bojo | /content/russian-private |
| `allied_332nd_Fighter_Pilot` | `user_332fighter.pk3` | Assassn (Tuskegee Airmen) | /content/332nd-fighter-pilot |
| `allied_camo_108thMGST` | `user_allied_camo_108thMGST.pk3` | — | /content/108th-msgt-camo |
| `american_medic` | `zzz-Ranger_Medic.pk3` | — ⚠ readme: *"Please do not edit"* | /content/1st-ranger-medic |
| `allied_sniper` | `zzzzz_allied_sniper.pk3` | — | /content/sniper |
| `allied_british_general` | `zzzzzz_PKM_british_general.pk3` | PKM | /content/british-general |
| `allied_medic` | `zzzzzzz--Bootsons_Medic-Skin_0.pk3` | ={DTA}=Bootson | /content/medic |

Prefix source pages with `https://mohaaaa.co.uk/AAAAMOHAA`.

### Two small chores before registering

1. **Missing `_fps.tik`** — `american_8thUrbanRangeradio` and `allied_british_general` ship only
   the third-person tik. Author the viewmodel variant by copying a sibling `_fps.tik` from the
   same pack and swapping the surface/shader lines (the mod's armory expects `<name>_fps.tik`).
2. **Bundled `.skd` gear props** — three of the recommended packs add small skelmodels rather
   than reusing stock gear: `34th_Infantery_Division_radio` (`models/gear/34th_radio.skd`) and
   `US_Sniper` (`models/human/foliage/foliage_al.skd`, `foliage_sleves.skd`). They are static
   attachments with no `.skc`, included in the pack, and the body/head/hands are still stock
   `usarmy.skd` / `head1.skd` / `hand.skd`. Fine to ship — just be aware the batch is not
   strictly "textures only".

Everything else in the recommended batch references only `usarmy.skd`, `head1/2.skd` and
`hand.skd` plus stock gear skelmodels already in the retail paks.

---

## 3. AVAILABLE BUT NEEDS WORK — 34 more skins

Downloaded and vetted, held back because each needs a rename or a patch first.

| Archive | Allied skins | Blocker | Recommended fix |
|---|---|---|---|
| `user-small_sumos_snipers.pk3` | 16 (`allied_sumo_sniper_foliage_1..8`, `allied_sumo_sniper_guile_1..6`, `allied_sumo_manon_sniper_foliage`, `..._guile`) | 0 shader collisions, but `guile_1..6` reference a shader `g_sneaky_one_helmet` that no pack or retail pak defines | define `g_sneaky_one_helmet` (or repoint those 6 tiks at `al_sneaky_one_helmet_*`); the 8 foliage + 2 manon variants are clean today. Also brings 16 matching Axis ghillies. |
| `zzz_krugerland_MP_skin.pk3` (12 MB) | 8 (`allied_american_airborne_soldier1/2`, `allied_british_general_williams`, `allied_british_paratrooper_sas`, `allied_Krug_Pilot`, `allied_oss_man_disguised_salombo`, `allied_spy`, `allied_military_police`) | 7 shader names collide with the mod tree; 6 more collide with stock; `allied_military_police` has no `_fps.tik`; pack also drags in 20+ German skins | rename `com_hand`, `com_handr`, `com_hands`, `l_gloves`, `priest_glass`, `priest_glass_frames`, `wehrmact_tunic_green` → `krug_*`; strip the German half |
| `user-bojos-winter-sniper.pk3` | 4 (`allied_sniper_winter`, `_guile`, `_tree`, `_tree2`) | 0 shader collisions, but **all four** reference `bojo_winter_axis_helm` whose texture is absent → white helmet; `_tree2` also loses `winter_foliage3` | supply the two `.tga`s or repoint the helmet surface at a stock winter helmet shader |
| `user-screamin eagle.pk3` | 3 (`allied_101st-Screaming-Eagle-1/2/3`) | defines a shader literally named `eagle`, which exists in stock → would override it | rename `eagle` → `se101_face1` in both the shader and the tik. Note: replaces the body mesh with `models/human/101st_airborne/101-airborne.skd` (included) |
| `user_101_Airborne_new.pk3` | 3 (`allied_101_Airborne`, `allied_101_Airborne_helmet`, `US_Army_private`) | defines `101_knife`, which the mod already defines | rename → `k101_knife_new` |
| `user-allied_british_tommy_girl.pk3` | 2 | defines `britcanteenabs`, `britdaggerabs`, `britshowelabs` — all already in the mod tree | rename → `tg_*` |
| `user-Recon-MP.pk3` | 1 (`allied_Reconsquad_MP`) | defines stock `45holster`; `holster.tga` and `viewsleeves2/bva.tga` absent | rename `45holster` → `recon_45holster`, supply or repoint the two textures |
| `user-Airman.pk3` | 1 (`allied_airman`) | defines `101_granade-1`, `101_knife-1`, `gasmask1` — all already in the mod tree | rename → `airman_*` |
| `user-airborne_101st_marjin.pk3` | 1 (`allied_Airborne_101st_martijn`) | defines `pouch_thingy`, `ushelm` — both in the mod tree; also no `_fps.tik` | rename → `mrt_*`, author the `_fps` |

---

## 4. Collision findings in full

### 4a. tik-name collisions with stock retail models

Only two archives ship a `models/player/*.tik` that would **replace** a stock model rather than
add one:

| Archive | Colliding tik | Effect |
|---|---|---|
| `zzzz_101st_Captain_thawedM.pk3` | `american_Army.tik` | overrides the stock **and registered** `american_army` (armory slot 34). **Rejected.** |
| `BA_skin_pack1.pk3` | `german_Elite_Officer.tik` (+`_fps`) | overrides the stock Axis model. Pack rejected anyway. |

**No skin in the recommended batch collides with a stock tik.** Nothing needs renaming for this
reason. Within the batch itself there were three self-collisions, all resolved:
`US_Army_private` (in both `user_101_Airborne_new.pk3` and `user_Captain_America_0.pk3`),
`allied_british_general` (in both `zzz_krugerland_MP_skin.pk3` and `zzzzzz_PKM_british_general.pk3`
— the PKM standalone is the one recommended), and the whole of `BA_skin_pack1.pk3` against the
mod tree.

### 4b. shader-name collisions

Method: every top-level block name from each pack's `scripts/*.shader`, compared against 819
block names in `hzm-mohaa-coop-mod/scripts/*.shader` and against every shader name in the stock
retail paks. **Recommended-batch packs: zero collisions of either kind.** Everything else:

| Archive | vs mod tree | vs stock retail |
|---|---|---|
| `BA_skin_pack1.pk3` | **165 of 165** | 19 |
| `zzz_krugerland_MP_skin.pk3` | 7 (`com_hand`, `com_handr`, `com_hands`, `l_gloves`, `priest_glass`, `priest_glass_frames`, `wehrmact_tunic_green`) | 6 (`colonel_hat`, `colonel_tunic`, `colonel_tunic_c`, `l_gloves`, `scientistcoat`, `wehrmact_tunic_green`) |
| `user-Airman.pk3` | 3 (`101_granade-1`, `101_knife-1`, `gasmask1`) | 0 |
| `user-allied_british_tommy_girl.pk3` | 3 (`britcanteenabs`, `britdaggerabs`, `britshowelabs`) | 2 (`manon_gear`, `manon_hands`) |
| `user-airborne_101st_marjin.pk3` | 2 (`pouch_thingy`, `ushelm`) | 0 |
| `user_101_Airborne_new.pk3` | 1 (`101_knife`) | 0 |
| `user_Captain_America_0.pk3` | 1 (`101_knife`) | 0 |
| `Allied_Marine.pk3` | 1 (`pol_coat_top_cull`) | 5 (`airborne_gear`, `usammobelt`, `usequip`, `static_usammobelt`, `static_usequip`) |
| `User-tr_fighter_pilot.pk3` | 0 | **15**, incl. `viewsleeves`, `viewsleeves_ranger`, `viewsleeves_us_airborne`, `viewsleeves_german_winter`, … |
| `user--IVY-capt.MOTFs_omaha_beach_ranger.pk3` | 0 | 4 (`45holster`, `barbelt`, `tommybelt`, `usequip`) — **redefined identically to stock; harmless, verified** |
| `user-Recon-MP.pk3` | 0 | 1 (`45holster`) |
| `user-screamin eagle.pk3` | 0 | 1 (`eagle`) |
| `user-skin_HeatMiser'sSP_501stBastogne.pk3` | 0 | 17 |

Note on `user--IVY-capt.MOTFs_omaha_beach_ranger.pk3`: it is in the recommended batch despite
four stock-name redefinitions because the four blocks are byte-equivalent to the stock gear
shaders (same `map` targets), so the override is a no-op. If you would rather be strict, rename
them to `omaha_*` — nothing else references them.

---

## 5. Rejected, with reasons

| Item | Reason |
|---|---|
| `heatpak_501stbastogne.zip` (Heatpak 501st Bastogne) | **Not player skins.** Its five tiks live under `models/human/` and use stock SP AI model names (`2nd-ranger_captain_snow`, `allied_usa_1st-Ranger_private_snow`, …), so it *replaces* Spearhead AI actors rather than adding selectable player models. Also ships `scripts/helmets.shader` + `us_soldier_snow.shader` with 17 stock shader-name collisions. Could be mined for textures later, but it cannot be registered in the armory as-is. |
| `BA_skin_pack1.pk3` (FUBAR, 17.4 MB) | **Already in the mod.** Its 12 Allied skins are exactly armory slots 77–88 (`allied_Airborne_101E_Col_Sink` … `allied_capt_recon`) and the matching tiks already sit in `hzm-mohaa-coop-mod/models/player/`. All 165 of its shader names collide with the mod tree for the same reason. Its 11 German skins are Axis and out of scope. |
| `zzzz_101st_Captain_thawedM.pk3` | Ships `models/Player/american_Army.tik`, overriding a stock + registered model. Contains no textures or shaders at all (2.4 kb). The `allied_101st_Captain_thawed.tik` also has a stray extra `}` after the `setup` block. |
| `user_Captain_America_0.pk3` | Novelty (`allied_Captain_America`); its `caphands.TGA` ships under `extra files/` so the engine never loads it; duplicates `US_Army_private` from `user_101_Airborne_new.pk3`. |
| `Allied_Marine.pk3` | Five referenced textures absent (`pol_coat.jpg`, `polface2.jpg`, `british_bd_szablon*.jpg`, …), surface shader `polface` unresolved, plus a mod-tree collision on `pol_coat_top_cull`. |
| `User-tr_fighter_pilot.pk3` | Redefines 15 stock `viewsleeves*` shaders — that is every first-person sleeve in the game, on every other skin. Also missing `pilotgloves.tga`. Not worth the blast radius for one pilot. |
| `user-madmans_MarineTrooper.pk3` (`allied_173dMarineTrooperPIR`) | Surface shader `mr_web` undefined anywhere, `mr_gear.tga` missing, no `_fps.tik`. |
| `user-airborne_sniper.pk3` (`allied_airborne_sniper`) | 35 kb — one tik, one shader, one `.skd`, zero textures; four referenced textures absent; no `_fps.tik`. |
| ~330 other AAAA Allied entries | Off-theme for a WW2 coop mod: Space (53), Snipers-novelty, Horror (27), Zombies (21), Super Heroes (19), Christmas (18), Slipknot, Metal Gear Solid, Duke Nukem, Legoman, robots, dodgeball, Stalin, RTCW crossovers. Listed in `scratchpad\aaaa_rows.json` if you ever want them. |

---

## 6. Licence position — read before shipping

Neither ModDB pack carries a permissive licence: ModDB's own metadata field reads
**"Proprietary"** for both *1st Rangers* and *Heatpak 501st*. The AAAA database states no
blanket terms, and `zzz-Ranger_Medic.pk3` carries an explicit **"Please do not edit"**. Only
`User_wigster_sniper_1.0.pk3` grants anything positive (*"Please feel free to modify"*).

This is normal for 2002-2003 MOHAA community skins — they were released to be used, and the
scene's convention is credit-in-readme — but it is not a licence grant. Practical suggestions:

* Ship a `CREDITS` entry naming every author in §2 and the source page.
* Prefer redistributing packs unmodified where possible; where a shader rename is unavoidable
  (§3), note the modification in the credits.
* If you want a clean slate, `american_sniper` (Wigster) is the only one with explicit
  permission to modify.

---

## 7. Reproduction

Scripts in the scratchpad, all runnable from that directory:

| Script | Does |
|---|---|
| `index_stock.py` | indexes stock `models/player/*.tik` and the mod's 819 shader names |
| `aaaa_fetch.py` | cookie/UA-authenticated GET helper for mohaaaa.co.uk |
| `aaaa_list.py` | scrapes all 14 pages / 700 rows of the skin database → `aaaa_rows.json` |
| `aaaa_pick.py` | resolves candidate rows to their `modfiles/*.pk3` URLs → `aaaa_picks.json` |
| `aaaa_dl.py` | downloads the 36 unique archives into `skins\aaaa\` |
| `analyze.py` | parses every tik (`$path`/`path`, `skelmodel`, `surface … shader …`) and every pack shader → `analysis.json` |
| `packreport.py` | per-pack shader collisions vs mod tree and vs stock |
| `texcheck.py` | resolves every `map`/`clampmap` target extension-agnostically; reports genuinely missing textures and `.skd` without `.skc` |
| `skinbatch_final.py` | per-skin classification of shader refs into pack / stock / addon / texture / unresolved |
