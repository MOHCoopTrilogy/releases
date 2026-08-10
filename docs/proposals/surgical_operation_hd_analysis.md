# Surgical Operation (HD) — analysis vs the HZM Coop Mod

**Date:** 2026-08-08 · **Analyst pass:** read-only. Nothing was installed; nothing outside this
file and the scratchpad was written.

**Bottom line:** Surgical Operation is a **texture / audio / FX reskin**, not a content mod. The
obtainable release adds **zero new weapons** — every weapon file in it overwrites a retail one. It
has **two** things worth considering (a re-authored impact-FX layer and a fresh-recorded gun-audio
set), and both are already covered by work we shipped. It carries **three hard blockers** for this
project. Recommendation: **do not import any part of it.**

---

## 1. Provenance of the files analysed

| | |
|---|---|
| Mod page | `https://www.moddb.com/mods/surgical-operation-hd` (author `fukun`, released 2016) |
| File analysed | `so2.zip` — "surgical operation0.1a(formohaa)", 970,141,484 bytes |
| **MD5** | `6d9064b1ed375a283c761b6e185283f3` — **MATCHES** the hash printed on the ModDB file page |
| Local copy | `…\scratchpad\surgop\so2.zip` (scratchpad only) |

### The later versions are not obtainable

| Version | Status |
|---|---|
| 0.1a (2016) | **Downloaded and analysed.** The only real payload on ModDB. |
| 1.0 (2017) | ModDB file is a **242-byte link stub** (MD5 `8476f64864d02b0e764d94c193a5cf21`, also verified) containing one line: a `pan.baidu.com` URL. A ModDB news post gives a MEGA mirror; the MEGA API returns **error −16 (administratively blocked)**. Page comments confirm both links are dead. |
| 2.0 / 5.0 | Never released. Page comments (2026) say the author now sells it privately over WeChat. |

**Everything in §3–§6 below is verified against files in `so2.zip`.** Claims sourced only from the
mod's own ModDB text are labelled *(author's claim, not verified)*.

### Provenance red flags — read before considering any asset

1. **The author states the textures are ripped from other commercial games.** From the 0.1a file
   page's own description: *"Time Spent Making : one year texture form: call of duty:world at war /
   Medal of honor:airborne / call of duty2 / call of duty1 / crysis:war[head] / Enemy front /
   S.T.A.L.K.E.R"*. That is a first-party admission covering the bulk of the 900 MB payload.
   A mechanical scan for `COD`/`WaW`/`MW`/`Crysis`/`STALKER`/publisher strings across all 165
   text-bearing files in the archive returned **0 real hits** (the 8 raw hits were vanilla MOHAA
   `usmaps/airborne/` paths — the US Airborne uniform, not *MOH: Airborne*), so there is **no
   in-file marker** — but the author's own statement is sufficient. **This alone disqualifies the
   texture packs for a project that ships publicly.**
2. **A third-party mod is redistributed inside it.** `zzz_healthmeter.pk3` contains
   `REAME.txt`: *"Made: Jan. 6, 2006 … [Please do not modify my works without written permission.]
   -Tag: A Cowboys Job / Nosebleed"*. Not credited on the ModDB page.
3. `textures/models/vehicles/panzer_iv_d/panzer_iv_destroyed.max` — a raw 3ds Max source file left
   in the pack, origin unknown.
4. Shipping junk: 2 `.DS_Store`, 2 `Thumbs.db`, 1 Paint Shop Pro `.psp`.

---

## 2. What is actually inside (10 nested pk3s, 2,108 files)

Scan basis: all 10 inner pk3s opened and fully enumerated; **1,917 of 2,108 files (91%) overwrite a
retail file.** Retail baseline = 17 `Pak*.pk3` archives across `G:\mohaa-gl2\{main,mainta,maintt}`
(29,134 files, 7,041 shader names). Our-side baseline = 6,936 files in
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod` + `zzzzz_xw_weapons.pk3`.

| pk3 | files | What it is |
|---|---:|---|
| `zzzzzzzzz_KUN Texture2.pk3` | 346 | World textures — `algiers`, `wilderness`, `test`. Textures only. |
| `zzzzzzzzz_KUN Texture3.pk3` | 688 | Character/model textures (`textures/models/**`). |
| `zzzzzzzzz_KUN Texture4.pk3` | 455 | More character/model textures. |
| `zzzzz_kun.pk3` | 280 | **Audio**: 208 `sound/weapons` + 63 `sound/characters` + 5 menu + 4 mp3. |
| `zzzz_weapon.pk3` | 294 | Weapon models/textures/shaders, HUD art, 20 `.urc`, **1 script**. |
| `zzzzzzzzzzzzzz_Realistic_Experience_Effects.pk3` | 56 | Re-authored impact/explosion FX + `scripts/effects.shader`. |
| `zzzzz_blood.pk3` | 12 | Blood decal/spray rework (`bh_human_uniform_*.tik` + new `blood.shader`). |
| `zzz_healthmeter.pk3` | 6 | Third-party 2006 circular health meter (`ui/hud_health.urc`). |
| `ZZfirekunmade.pk3` | 9 | Higher-res muzzle-flash textures. |
| `ZZzzzzz_highThompson.pk3` | 4 | A Thompson `.dds` + `.lod`. Texture-only. |

Extension census: 923 `.tga`, 473 `.dds`, 276 `.wav`, 227 `.jpg`, 98 `.tik`, 33 `.skc`, 23 `.skd`,
20 `.urc`, 17 `.shader`, 4 `.mp3`, 1 `.scr`, 1 `.max`.

---

## 3. WEAPONS — the headline answer

### They have nothing we don't. Zero net-new weapons.

Every `models/weapons/*.tik` in all 10 pk3s (13 total):

| TIK | Status |
|---|---|
| `bar.tik` `bazooka.tik` `colt45.tik` `kar98.tik` `kar98sniper.tik` `m1_garand.tik` `mp40.tik` `mp44.tik` `p38.tik` `shotgun.tik` `silencedpistol.tik` `springfield.tik` | **All 12 overwrite a retail TIK of the same name.** No new weapon is registered. |
| `thompsonsmg111.tik` | Only new-named file — and it is **dead**. Its `setup` block reads `path models/weapons/Thompson` + `skelmodel ThompsonSMG.skd`; that directory exists in **neither the pack nor retail** (the pack's high-poly Thompson ships under `models/weapons/thompson11/`). It also carries `rank 310 310`, colliding with the vanilla Thompson's select slot. It cannot load. |

**"They have, we don't" list: EMPTY.**

For scale, our side already fields **123** distinct weapon TIKs (82 retail + 5 net-new in the mod
tree + 32 net-new in `zzzzz_xw_weapons.pk3` + overlaps), including 32 guns SurgOp never had —
Arisaka, Type 100, Nambu, TT-33, Luger P08, PPK, Welrod, Grease Gun, M1 Carbine, portable MG42/.30cal
and 12 silenced/scoped variants. SurgOp's *unreleased* 2.0 roster post
(FG42, Nambu, Luger P08, Breda 30, SVT-40, L42A1, DeLisle) lists **seven guns we already ship**.

*(Author's claim, not verified — no obtainable build contains these.)* The 2021 news posts advertise
"60 kinds of guns" for the unreleased 5.0: 11 SMGs (Thompson M1928/M1921, M3A1, MP38, MP40-2, Steyr
MP34, PPD-40, PPSh-41, Sten Mk2, MAB-38, "STELIN") and 12 pistols (39H, PP-SD, P38, TT-30, HS,
C96 Mauser, M1895 Nagant, "Scott" M1910, M1911, SAA, VIS 35). Of the plausible ones, we already have
Thompson, MP40, PPSh-41, Sten, Moschetto/MAB-38, P38, TT-33, Luger, Nagant, Colt M1911. Genuinely
absent from our roster would be the **Steyr MP34, PPD-40, C96 Mauser, Radom VIS 35, Sauer 38H,
Colt SAA**. None of these are obtainable, so this is a wishlist, not a port target.

### Model quality — the "much more delicate" claim is half true

Triangle counts parsed from the SKD headers, mod vs `main\Pak0.pk3`:

| Weapon | Retail tris | SurgOp tris | Δ |
|---|---:|---:|---|
| Bazooka | 548 | 2,152 | **3.9× up** |
| BAR | 1,332 | 4,432 | **3.3× up** |
| Thompson (unreachable) | 1,166 | 2,815 | 2.4× up |
| Springfield | 1,201 | 2,351 | 2.0× up |
| Panzerschreck | 842 | 1,439 | 1.7× up |
| MP44 / StG44 | 1,400 | 1,496 | ~same |
| P38 | 1,114 | 1,156 | ~same (but a full new anim set: idle/fire/empty/reload2 `.skc`) |
| Colt 45 | 861 | 861 | **byte-identical model — retexture only** |
| MG42 (statweapon) | 1,481 | 1,481 | **identical** |
| Kar98 sniper | 1,483 | 1,299 | **0.88× DOWN** |
| MP40 | 1,497 | 1,074 | **0.72× DOWN** |
| Kar98 | 1,457 | 963 | **0.66× DOWN** |
| M1 Garand | 1,905 | 943 | **0.49× DOWN** |

Four of the most-used guns in the game are **lower**-poly than retail. For those, "HD" means the
texture only. This matches the ModDB comments asking the author to redo the MG42 and Kar98 sniper.

### Self-containment

The weapon replacements **are** self-contained — each ships its own `.skd`/`.skc`, its own
`textures/*.jpg|.tga|.dds`, and its own `scripts/<gun>.shader`. Nothing depends on a retail texture
we would have to keep in sync. That is the one thing the pack does structurally right.

**But 9 of its 13 weapon shader files are malformed** — `m1918a2_bar`, `m1928a1`, `schmeissermp40`,
`stg`, `m1911`, `walther`, `m97`, `bazookanl`, `03`, `hi_standardHD` all **open with a stray `}` at
brace depth 0** before the first shader name. (`garand.shader`, `karabiner98k.shader`,
`karabiner98sniper.shader` are clean.)

### Weapon stat rebalance (verified diff vs `main\Pak0.pk3`)

The pack is not cosmetic — it retunes damage:

| Weapon | `bulletdamage` retail → mod | `dmbulletdamage` retail → mod | Other |
|---|---|---|---|
| Shotgun | 10 → **90** | 17 → 40 | range 1000→2000, clip 5→6 |
| MP40 | 23.5 → **50** | 25 → 40 | range 4000→**3000** |
| M1 Garand | 45 → **70** | 48 → 68 | firedelay 0.15→0.125 |
| BAR | 60 → 75 | 30 → **80** | firedelay 0.12→0.0923 |
| Colt 45 | 35 → 50 | — | — |
| MP44 | 40 → 50 | 27 → 49 | firedelay 0.086→**0.12**, movementspeed 0.9→1.0 |
| Kar98 | 75 → 80 | — | — |
| Silenced pistol | — | — | **firedelay 1.0 → 0.1**, clip 8→10 |

It also adds `zoom 35` to eight normally-unscoped weapons (BAR, Kar98, Garand, MP40, MP44, shotgun,
bazooka `zoom 20`) and bumps Springfield `zoom 20 → 30`. **This is the pack's ADS substitute** — a
plain FOV pull with the crosshair still drawn, which is exactly what reviewers on the file page
complained about (*"you only see a crosshair when zoomed, it is unrealistic"*). Our shipped
iron-sight ADS + per-gun tune table (`cg_modelanim.c s_adsGunTune[]`, 45 guns hand-dialled) is
strictly better; there is nothing to take here.

**Correction worth recording:** per-weapon `movementspeed` is **vanilla MOHAA**, not a SurgOp
feature (`main\Pak0.pk3 models/weapons/bar.tik` already carries `movementspeed 0.9`). An earlier
read of this pack could easily mistake it for a new "weapon weight" system. It is not.

---

## 4. FEATURES — what it does that we do not

| SurgOp feature | Verified in | Do we have it? |
|---|---|---|
| **Re-authored impact / explosion FX** — 35 `models/fx/*.tik` rewritten (bullet holes per surface, grenade/bazooka explosions, water explosion). Real emitter work: `bh_stone_hard.tik` grows 138→242 lines adding two lingering-smoke `originspawn` stages with per-axis accel. | `zzzzzzzzzzzzzz_Realistic_Experience_Effects.pk3` | **Partly.** We have lingering gun smoke (`coop_smokeWhip`), suppression FX, blood trails, and our own `coop_barrelsmoke.tik`/`coop_gunsmoke.tik` — but we have **not** re-authored the per-surface bullet-impact emitters. This is the one genuinely additive idea in the pack. |
| **Fresh gun / impact / footstep audio** — 208 weapon wavs + 63 character wavs replaced. | `zzzzz_kun.pk3` | **Yes, and better.** FEATURES.md § Audio: 47 gun sounds re-recorded, 24 footstep surfaces, 44 surface impacts, whizbys, casings — plus reverb/HRTF/occlusion/distance-tails the pack has none of. **111 of its 280 sound files collide with files we already ship.** |
| **Blood decal rework** — new `blood_splat`/`blood_long` shaders, `bh_human_uniform_hard/lite.tik` rewritten to spray a `bouncedecal` with `decalradius 24`. | `zzzzz_blood.pk3` | **Yes, and far better.** Our 4-tier gore system (skin-bit blood tiers, drip + growing pool, bone-attached wound props, renderer UV wounds, `tr_gore.c`) plus `coop_blooddrip`, `coop_bloodleak`, headshot burst/wall-splat. |
| **Circular analogue health meter** | `zzz_healthmeter.pk3` | **No** — we use the retail bar plus HUD fade. This is a third-party 2006 asset with a no-modification licence notice. Cosmetic; not recommended. |
| **Bigger crosshair** — `ui/crosshair.urc` menu 16×16 → 50×50 with a 64px TGA. | `zzzz_weapon.pk3` | **Yes, better.** We ship a true-aim crosshair tied to ADS. |
| **Higher-res muzzle flash** — `flashnode1.tga` 12 KB → 262 KB. | `ZZfirekunmade.pk3` | **Yes.** We already override `models/fx/muzflash/flashnode1.tga`. |
| **HD world / character textures** (1,489 files) | KUN Texture2/3/4 | **Yes, and larger.** Our own ESRGAN ×4 packs (169 char skins, 1,133 world textures) + `zzzzzzz_dds_override.pk3` (872 DXT `.dds`, 485 MB) + the community AA_HD_Project paks. And ours are not ripped from other games. |
| Menu music / stingers (`serenade.mp3`, `colonel.mp3`, `success.mp3`, `beschuss.mp3`) | `zzzzz_kun.pk3` | **Yes.** MOH Frontline PS3 extraction — 339 cues / 103 min + 175 ambience beds. |
| *"Changed the engine code from SOF2 so you can see more and real blood"* | 2021 news post — **not verified**, no binary ships in 0.1a and no later build is obtainable. | We already ship engine-level gore in `renderergl1/tr_gore.c`. |

### Systems SurgOp has nothing of

Everything in our core value proposition is absent from it: coop framework, DBNO, medkit, officer
boss waves, AI dynamics/squad/morale/retreat, enemy count-scaling, difficulty director, XP/rank,
challenges/medals, armory loadout picker, lobby, objectives HUD, sprint/stamina/cover/emotes, 3P
camera suite, dynamic weather, build mode, map-test harness, NAT hole-punch. SurgOp ships exactly
**one** `.scr` file in 970 MB, and it is a downgrade (see §5).

---

## 5. BLOCKERS — why this must not be imported wholesale

### B1. The whole pack is built against 2002 vanilla `main/`, and would roll back the expansions

The install instruction on the file page is *"unzip all things in your MOHAA/Main/ directory."* Three
independent proofs that it targets plain AA, not War Chest:

1. **`scripts/effects.shader`.** SurgOp's copy is byte-for-byte the **`main\Pak0.pk3`** version plus
   3 names (`bh_snow_puff1`, `bh_snow_puff2`, `barrel_water_splat1`) — measured: **0 deletions vs
   Pak0**, but **36 deletions vs the Breakthrough `maintt\pak1.pk3` copy we actually run**. The 36
   lost shaders are:
   `bh_wood_puff_simple`, `c47_fire2smoke`, `c47_fire2smokeccw`, `c47skytrain_burst1`,
   `c47skytrain_fiery`, `c47skytrain_fieryccw`, `c47skytrain_smoke2`, `c47skytrain_smoke3`,
   `flak_cloud01/03/04`, `flak_flash`, `flakflash_skybox`, `flaksmoke_skybox`, `kingtiger_starflash`,
   `mortar_dirtchunks`, `mortar_snowhit`, `mortar_snowplume`, `snowclump`,
   `textures/fallout0`…`fallout11` (11 snowfall shaders), `tracer_fake`, `water_drop1`, `waterdrop`,
   `waterring`, `waterwake`.
   **Verified: 35 of those 36 are defined in `scripts/effects.shader` and nowhere else** in the 17
   retail paks (`snowclump` also lives in `tasprites.shader`). The engine dedupes by filename and
   `zzzzzzzzzzzzzz_*` sorts after everything, so this file **wins outright** — flak bursts, C-47
   crash smoke, snowfall, tracers, water rings and mortar snow FX go missing trilogy-wide. This is
   exactly the whole-file-override hazard in [TRAPS.md § T6](../TRAPS.md#t6).
2. **`global/ambient.scr`** (`zzzz_weapon.pk3`) — the pre-patch AA version. It **deletes the
   `level.ambient_script_run` re-entry guard** and the `level.gametype = int(getcvar(g_gametype))`
   assignment, and changes the music resolution from `level.music` to `local.music`. We ship our own
   7,473-byte `global/ambient.scr`; this would silently replace it.
3. **`models/statweapons/mg42_gun_fake.tik`** — reverts the expansion-era per-mode
   `sp`/`dm`/`realism` attribute blocks to flat AA syntax, and `spawnrangelinked`/`tagspawnlinked`
   back to `spawnrange`/`tagspawn`.

### B2. It would overwrite 156 files we ship — including 12 weapon TIKs we have modified

Mechanical diff of the pack against `hzm-mohaa-coop-mod/`: **156 overlapping paths.**

- **12 weapon TIKs** (`bar`, `bazooka`, `colt45`, `kar98`, `kar98sniper`, `m1_garand`, `mp40`,
  `mp44`, `p38`, `shotgun`, `silencedpistol`, `springfield`) — these are the exact files carrying our
  uncommented `holstertag`/`holsteroffset` lines (FEATURES.md § *Visible holstered weapons*, a
  `SHIPPED-VERIFIED` feature). Importing the pack **reverts weapons-on-back** for the whole starter
  loadout.
- **111 sound files** we already replaced with our own recorded set.
- `global/ambient.scr`, `models/statweapons/mg42_gun_fake.tik`,
  `models/fx/muzflash/flashnode1.tga`, `ui/hud_health.urc`, 5 HUD TGAs, 12 texture files.

### B3. Broken references it ships as-is

- **7 shader texture references resolve nowhere** (checked 455 refs against both the pack and the
  17 retail paks): `models/fx/muzflash/mg42_starflash.tga`, `mg42_spriteflash.tga`,
  `thompsonsmg_sideflash.tga`, `thompsonsmg_spriteflash.tga`, `textures/effects/water_wake.tga`,
  `textures/effects/barrel_blood_splat.tga`, `textures/hp/healthstealthback.tga`.
- **`ui/新建文件夹/` ("New folder") holds 20 `.urc` files** inside `zzzz_weapon.pk3` — the cause of
  the `recursive error … Couldn't load ui/hud_ammo_thompson11.urc` crash reported on the file page,
  whose community fix is "delete the folder in `ui` inside `zzzz_weapon.pk3`."
- `thompsonsmg111.tik` points at a non-existent model directory (§3).

---

## 6. SHADER-COLLISION RISK

**Scan basis (proof the scan ran):** 17 retail `Pak*.pk3` opened across
`G:\mohaa-gl2\{main,mainta,maintt}` → 445 `scripts/*.shader` files → **7,041 unique names at brace
depth 0**. (Widening to all 41 installed pk3s including the third-party HD packs gives 497 shader
files / 7,755 names; the `co-op_hzm` pak is excluded per instruction — it is not present in
`maintt` anyway, it deploys to homepath.) Our side: 52 shader files in
`hzm-mohaa-coop-mod/scripts/` → 1,166 names. SurgOp: 17 shader files → **140 names**.

| Result | Count |
|---|---|
| SurgOp names that **collide with retail** | **110** |
| SurgOp names that are **new** | 30 |
| SurgOp names that **collide with the HZM coop mod tree** | **0** |

- The 110 collisions are **all** in `scripts/effects.shader` and its duplicate copy
  `scripts/effectsyuanlai.shader` (`yuanlai` = 原来, "original" — a backup the author left in
  `zzzz_weapon.pk3`; it also defines 109 retail names). This is B1.
- **The 30 new names are clean** — no retail and no HZM collision:
  `garand_stock/metal/clip`, `k98_stock/metal/scope/stock_s/metal_s`, `m9`, `m11`, `m97_shotgun`,
  `m1918a2_bar`, `m1928a1_thompson`, `mp401/402/403`, `p38parabellum`, `springfield_1`, `stg1`,
  `stg2`, `hd`, `blood_long`, `blood_splat`, `blood_splat2`, `bh_snow_puff1/2`,
  `barrel_water_splat1`, `textures/hp/healthmeter`/`healthmeterflash`/`healthstealthback`.
  ⚠️ **`hd`, `m9`, `m11`, `stg1`, `stg2`, `mp401` are dangerously generic** and its weapon textures
  sit at `textures/` root with names like `metal1.jpg`, `hd.jpg`, `03.jpg`, `bar.jpg` — a future
  import collision waiting to happen. Any adoption must rename per the
  [TRAPS.md § T6 isolation recipe](../TRAPS.md#t6) (new name + private texture path).
- Positive note: the pack ships `.dds` alongside the same-name `.tga`/`.jpg` in **461** cases, which
  is the correct shape for our [T6 `.dds`-shadowing](../TRAPS.md#t6) rule.

---

## 7. Recommendation

**Take nothing as-is. Do not import any pk3 from this mod.**

If any single idea is worth acting on, it is **one**, and it should be built from scratch, not
lifted:

> **Re-author the per-surface bullet-impact emitters** (`models/fx/bh_*_hard/lite.tik`) to add a
> two-stage lingering smoke puff with per-axis acceleration, the way
> `Realistic_Experience_Effects` does. This is a gap in our FX coverage — we have muzzle/impact
> gun smoke and suppression FX but have never touched the stock impact emitters. Doing it in our
> own pak with our own names costs nothing and carries none of §5's blockers.

Everything else the pack does, we already do better (audio, gore, HD textures, ADS, crosshair,
muzzle flash), or it is actively harmful (§5), or it is licensed/sourced in a way this project
cannot ship (§1).

The weapons question has a one-line answer: **there is nothing to port.**

---

## Appendix — how to reproduce

Scripts in `…\scratchpad\surgop\`:

| Script | Purpose |
|---|---|
| `shaderscan.py` | Retail shader-name index from `G:\mohaa-gl2\*` (`pak` mode = retail only). |
| `slice.py` | Enumerate the nested pk3s inside `so2.zip` without full extraction. |
| `full.py` | Per-pk3 inventory: file census, NEW vs REPLACES-RETAIL, shader-name collisions. |
| `weapons.py` | Cross-index of every SurgOp file/shader vs retail **and** vs `hzm-mohaa-coop-mod/`; unresolvable texture references. |
| `megadl.py` | Pure-Python MEGA public-link probe (used to establish the 1.0 mirror is blocked). |

Run with `PYTHONIOENCODING=utf-8` — the pack contains GBK-encoded path names.
