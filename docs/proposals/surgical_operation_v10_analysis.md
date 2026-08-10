# Surgical Operation **1.0** (2.9 GB) — analysis vs the HZM Coop Mod

**Date:** 2026-08-08 · **Analyst pass:** read-only. Nothing was installed. The archive lives only in
the session scratchpad; `hzm-mohaa-coop-mod\`, `G:\mohaa-gl2` and the GOG install were **read but
never written**.

Companion docs: [`surgical_operation_hd_analysis.md`](surgical_operation_hd_analysis.md) (the 0.1a
payload) and [`surgical_operation_version_hunt.md`](surgical_operation_version_hunt.md) (why 1.0 is
the highest obtainable build).

---

## 0. Bottom line

The 2.9 GB **1.0** is ~3.1× the bytes of 0.1a and the payload really is bigger — but the growth is
**almost entirely world/menu textures**. On the question this pull was made to answer:

> **Weapons: still zero. "They have, we don't" is EMPTY, again.**
> 1.0 ships **14** `models/weapons/*.tik`. **12 overwrite a retail name.** The other two are not
> weapons: one is a sound-alias carrier on a `dontdraw` dummy model, and the other is the same dead
> Thompson stub 0.1a shipped, still pointing at a directory that does not exist.

One blocker **did** improve: the Breakthrough-killing `effects.shader` override is **gone** — 1.0
renames that file, so `maintt\pak1.pk3`'s copy survives. Four *other* shader files took its place at
smaller scale (26 names lost against `maintt`, not 36), and the rename created a new hazard: **110
shader names now exist twice**, with the winner decided by shader-file parse order.

Recommendation unchanged: **import nothing.** The one idea worth building ourselves is still the
per-surface impact-FX rework, and 1.0's version of it is materially bigger than 0.1a's.

---

## 1. The download

| Field | Value |
|---|---|
| Page | `https://www.gamepressure.com/download/medal-of-honor-allied-assault-surgical-operations-v10-mod/z1fafd` |
| Page-stated size | 2907.4 MB |
| Real transfer URL | `https://metrocf.gameplay.pl/s/surgicaloperation10formohaa.zip?st=…` |
| **Bytes received** | **3,048,601,095** (2907.4 MiB — matches the page exactly) |
| **MD5** | `6DBCDF840B979FF1A35FE331A355F17D` |
| **SHA-256** | `90FC3DEE9A2BA598247B1E02AABF1D36EC19F87E7BB72D34D1AAF2803CB982CC` |
| Local copy | `…\scratchpad\surgop10\so10.zip` (scratchpad only) |
| Content-Type | `application/zip`, HTTP 200 |

**No published hash exists for this mirror.** gamepressure prints no checksum, and ModDB's 1.0 entry
is a 242-byte link stub, so there is nothing to compare against. The MD5 above is stated for
*future* comparison, **not** as a verified match.

### How the link was resolved

gamepressure serves an intermediate page, not the file. The `DOWNLOAD` button is a jQuery handler in
`https://cdn.gracza.pl/js_gp/gp2.js` that POSTs `FORM_TYPE=POBIERZ_ZA_DARMO` to the same URL, waits
`timelimit` seconds (10), then POSTs `FORM_TYPE=POBIERZ_TERAZ`. The second response contains
`downloadFile('https://metrocf.gameplay.pl/s/…')`. Reproduced with `curl` + a cookie jar, a browser
User-Agent and a matching `Referer:`. No login, no captcha.

**The file is what the page claims.** It is a real 15-member zip of MOHAA pk3s, not a stub or a
redirect page.

---

## 2. Proof the scans ran

| Scan | Archives opened | Files enumerated |
|---|---:|---:|
| **SurgOp 1.0** (`so10.zip` + 15 nested pk3s) | **16** | **7,033** unique paths |
| — decompression test (every member) | 16 | **7,032 OK / 1 corrupt** |
| **Retail baseline** — every `*.pk3` in `G:\mohaa-gl2\{main,mainta,maintt}` **excluding `co-op_hzm`** | **41** | 43,586 entries → **33,067** unique paths; 497 `scripts/*.shader` → **7,754** names |
| — *original* subset (`Pak*.pk3` only, 17 archives) | 17 | 27,235 paths, **7,041** shader names |
| **Our side** — `hzm-mohaa-coop-mod\` tree walk + `zzzzz_xw_weapons.pk3` | 1 | **7,295** paths; 61 shader files → **1,254** names; **78** weapon TIKs |

The 7,041 figure for the original paks reproduces the 0.1a analysis's count exactly, which validates
the depth-0 shader-name parser used throughout.

**One corrupt member:** `textures/models/items/armchairposh.tga` inside
`zzzzzzzzz_KUN Texture4.pk3` fails zlib inflate (`invalid stored block lengths`). The other 7,032
members decompress cleanly, so this is a defect in the mod's own archive, not a truncated download
(the outer zip's central directory is intact and the byte count matches the page).

### The 15 nested pk3s

| pk3 | bytes | files | What it is |
|---|---:|---:|---|
| `zzzzzz_KUN Texture1.pk3` | 1,726,219,876 | 2,761 | **New in 1.0.** World textures (`models`, `mohtest`, `general_structure`, `das_boot`, `misc_outside`, `central_europe_winter`…). 1,311 jpg / 963 tga / 481 dds. This single pak is 57% of the archive. |
| `zzzzzzzzz_KUN Texture2.pk3` | 469,488,730 | 351 | `algiers`, `wilderness`, `test`. Was 346 files in 0.1a. |
| `zzzzzzzzz_KUN Texture3.pk3` | 259,968,485 | 693 | Character/model textures. |
| `zzzzzzzzz_KUN Texture4.pk3` | 230,145,266 | 455 | More character/model textures. |
| `zzzzz_alhpa.pk3` | 142,287,096 | 1,263 | **New in 1.0.** 1,074 files under `textures/modelsss/` (see §5, dead directory) + `textures/common` + 23 shader files. |
| `zzzzz_kunmohmenu.pk3` | 139,138,710 | 680 | **New in 1.0.** Complete `textures/mohmenu` retexture, including 40 level-briefing plates. |
| `zzzzz_kun0.1a.pk3` | 32,112,156 | 287 | **The 0.1a audio pack, by its own filename.** 215 `sound/weapons` + 63 `sound/characters` + 5 menu + 4 mp3. |
| `zzzzz_weapon.pk3` (`zzzz_weapon.pk3`) | 26,878,095 | 295 | Weapon models/textures/shaders, HUD art, 19 `.urc`, 1 `.scr`. |
| `zzzzzzzzzzzzzz__Experience_Effects.pk3` | 17,516,216 | 361 | Impact/explosion FX rework. **Grew from 56 files in 0.1a to 361.** |
| `zzzzz_blood.pk3` | 3,846,190 | 26 | Blood decal rework. |
| `garandWinRAR ZIP.pk3` | 1,769,062 | 27 | **New in 1.0.** HD Garand + `sounds.tik`. |
| `zzzzz_sp03.pk3` | 1,015,999 | 16 | **New in 1.0.** HD Springfield. |
| `ZZzzzzz_highThompson.pk3` | 459,939 | 11 | Thompson `.dds` + `.lod`. |
| `ZZfirekunmade.pk3` | 71,946 | 12 | Muzzle-flash textures. |
| `zzz_healthmeter.pk3` | 39,457 | 10 | The 2006 third-party circular health meter — **byte-for-byte the same third-party redistribution as 0.1a** (§7). |

Extension census across all 7,033 paths: 3,917 `.tga`, 1,666 `.jpg`, 950 `.dds`, 283 `.wav`,
59 `.tik`, 45 `.shader`, 43 `.skc`, 25 `.skd`, 20 `.urc`, 6 `.lod`, 4 `.mp3`, 3 `.txt`, 2 `.max`,
2 `Thumbs.db`, 1 `.bmp`, 1 `.cfg`, 1 `.scr`, plus `.DS_Store` files.

**5,682 of 7,033 paths (81%) overwrite a retail file.**

---

## 3. WEAPONS — the headline

### 3.1 The roster

All 14 `models/weapons/*.tik` in the archive:

| TIK | Verdict |
|---|---|
| `bar.tik` `bazooka.tik` `colt45.tik` `kar98.tik` `kar98sniper.tik` `m1_garand.tik` `mp40.tik` `mp44.tik` `p38.tik` `shotgun.tik` `silencedpistol.tik` `springfield.tik` | **12 overwrite a retail TIK of the same name.** No new weapon registered. |
| `sounds.tik` | **Not a weapon.** `classname ScriptModel`, `rendereffects +dontdraw`, `notsolid`, `path models/fx/dummy` / `skelmodel dummy3.skd`. Its whole body is nine `aliascache` lines for Garand and carbine sounds. **Nothing in the archive references it** (grepped all `.tik`/`.shader`/`.urc`/`.scr`). It is a stray sound-alias carrier the author left in `garandWinRAR ZIP.pk3`. |
| `thompsonsmg111.tik` | **Dead — identical failure to 0.1a.** Its setup reads `path models/weapons/Thompson` + `skelmodel ThompsonSMG.skd`. The pack ships its high-poly Thompson at `models/weapons/thompson11/` and **no `models/weapons/thompson/` directory exists in the pack or in any retail pak**. **Nothing references it.** ⚠️ Footnote: `models/weapons/thompson/thompsonsmg.skd` **does** exist — in **our** `zzzzz_xw_weapons.pk3`. So this stub is inert in a vanilla install but, if ever imported into *our* tree, would silently bind to **our** xw Thompson, not fukun's. |

### **"They have, we don't" list: EMPTY.**

There is no weapon in Surgical Operation 1.0 that this project does not already field. For scale,
our side ships **78** weapon TIKs of which **36 are not in any original `Pak*.pk3`** — Arisaka +
sniper, Type 100, Nambu, TT-33 + silenced, Luger P08 + silenced, PPK, Welrod, Grease Gun +
silenced, M1 Carbine, Carcano sniper, Enfield sniper, G43 sniper, Nagant sniper + silenced,
Moschetto, portable MG42 / .30cal, Thompson M1928 50-round, Beretta silenced, Colt silenced, Garand
scoped + silenced, Kar98 sniper silenced, MP40 silenced, MP44 scoped, PPSh silenced, P38 silenced,
Springfield unscoped, plus our own `coop_binoculars`, `coop_smoke_grenade`, `dbno_pistol`.

The 60-gun and 130-gun rosters advertised for the unreleased 4.0/5.x builds are **not in this file**
and are not obtainable (see the version-hunt doc). Nothing changed there.

### 3.2 Model quality — measured from SKD headers, against the **original** `Pak*.pk3` only

⚠️ **Methodology correction worth keeping.** A first pass compared against *whatever* archive held
the path and silently picked HD community packs (`zzzzzz-HRRTM_*`) as "retail", inflating the
baseline. The table below reads the baseline from the 17 `Pak*.pk3` originals **only**.

| Weapon | retail `Pak*` tris | SurgOp 1.0 tris | Δ | vs 0.1a |
|---|---:|---:|---|---|
| Springfield `springfield/springfield.skd` | 1,201 | **4,433** | **3.7× up** | 0.1a was 2,351 — genuinely improved |
| Bazooka `bazooka/bazooka.skd` | 548 | **2,152** | **3.9× up** | same as 0.1a |
| M1 Garand `m1_garand/garand.skd` | 1,905 | **2,007** | 1.05× up | 0.1a was 943 (**a downgrade**) — fixed in 1.0 |
| MP44 / StG44 | 1,400 | 1,496 | 1.07× | same |
| Colt 45 | 861 | 861 | **byte-identical model — retexture only** | same |
| MG42 statweapon `mg42.skd` | 1,481 | 1,481 | identical | same |
| MG42 **viewmodel** | 1,481 | 1,435 | 0.97× **down** | — |
| Kar98 sniper | 1,483 | 1,299 | **0.88× DOWN** | same |
| MP40 | 1,497 | 1,074 | **0.72× DOWN** | same |
| Kar98 | 1,457 | 963 | **0.66× DOWN** | same |
| P38 | 1,114 (`p38/p38.skd`) | 1,156 (`p38/p38_model.skd`, **new file**, `p38.tik` repointed) | ~same, **but a full new anim set**: `p38_idle/fire/empty/reload2.skc` | same |
| Panzerschreck | 842 (`panzerschreck/panzerschreck.skd`) | 1,439 — **but shipped at `models/weapons/bazooka/panzerschreck.skd`**, a path no TIK in the pack or in retail references. **Dead asset.** | — | 0.1a counted this as a live 1.7× upgrade; it is not |
| Thompson `thompson11/thompsonsmg.skd` | 1,166 (`thompsonsmg/thompsonsmg.skd`) | 2,815 — **unreachable**, see §3.1 | — | same |
| BAR | 1,332 (`models/weapons/bar/bar.skd`) | 4,432 at **`models/weapons/bar_lmg/bar.skd`** | 3.3× up | see warning below |

⚠️ **The BAR is a direct collision with our S93 pack.** SurgOp's `bar.tik` is repointed to
`path models/weapons/BAR_lmg`, and `models/weapons/bar_lmg/bar.skd` is **exactly the path our
`zzzzz_xw_weapons.pk3` uses** for its own 4,838-tri BAR. The two models are not identical (4,432 vs
4,838 tris) but they occupy the same non-vanilla directory with the same four filenames
(`bar.skd`, `bar.skc`, `fire_bar.skc`, `reload_bar.skc`). Importing SurgOp's `zzzz_weapon.pk3` would
**overwrite our xw BAR model and all three of its animations**. *(Whether the two derive from a
common third-party source is **not verified** — the shared non-retail path convention is suggestive,
the byte contents differ.)*

**Net:** four of the most-used guns in the game are still **lower**-poly than retail
(Kar98, Kar98 sniper, MP40, MG42 viewmodel). For those, "HD" means the texture only. 1.0 fixed the
Garand and improved the Springfield; everything else is as 0.1a.

### 3.3 Self-containment

**Yes, and cleanly.** Every weapon replacement ships its own `.skd`/`.skc`, its own textures, and
its own `scripts/<gun>.shader`. Reference check across the 18 weapon/HUD shader files:
**59 texture references — 52 resolve inside the pack, 5 resolve only from retail, 2 unresolvable**
(`models/ammo/us_bomb/reflection2.tga` in `weapons_allied.shader`;
`textures/hp/healthstealthback.tga` in `hp.shader` — the same broken healthmeter reference 0.1a had).

**But 10 of its shader files are malformed** — measured by running brace depth, they go negative
(a stray `}` at depth 0) or end non-zero:
`03`, `bazookanl`, `hi_standardhd`, `m1911`, `m1918a2_bar`, `m1928a1`, `m97`, `schmeissermp40`,
`stg`, `walther`. Clean: `garand`, `karabiner98k`, `karabiner98sniper`, `blood`, `hp`, `spr03`,
and all the retail-name overrides.

⚠️ Its weapon textures still sit at `textures/` **root** with names like `hd.jpg`, `03.jpg`,
`metal1.jpg`, `bar.jpg`, `thompson.jpg`, and the shader names include `hd`, `m9`, `m11`, `stg1`,
`stg2`, `mp401`. Any adoption would need the [TRAPS.md § T6 isolation recipe](../TRAPS.md#t6)
(fresh name + private texture path).

### 3.4 Weapon stat rebalance (verified diff vs `main\Pak0.pk3`)

1.0 retunes damage, and **the numbers moved since 0.1a**:

| Weapon | `bulletdamage` | `dmbulletdamage` | other |
|---|---|---|---|
| Shotgun | 10 → **90** | 17 → 40 | range 1000→2000, firedelay 0.75→0.85, `dmbulletcount` 20→**50** |
| MP40 | 23.5 → **50** | 25 → 40 | range 4000→**3000**, dmfiredelay 0.086→0.109 |
| MP44 | 40 → 50 | 27 → 49 | firedelay 0.086→**0.12**, movementspeed 0.9→1.0 |
| BAR | 60 → 75 | 30 → **80** | firedelay 0.12→0.0923 |
| Colt 45 | 35 → 50 | — | — |
| Kar98 | 75 → 80 | — | — |
| M1 Garand | — | 48 → **75** | firedelay 0.15→**0.18** (slower, was *faster* in 0.1a), dmbulletspread `10 10 80 80`→`4 4 60 60` |
| Silenced pistol | — | — | firedelay **1.0 → 0.1**, `semiauto` added |
| Kar98 sniper | — | — | `crosshair 1 → 0` |
| Bazooka / P38 / Springfield | — | — | no stat change |

`zoom 35` is still bolted onto five normally-unscoped weapons (BAR, Kar98, MP40, MP44, shotgun) and
`zoom 20` on the bazooka. **That is the pack's ADS substitute** — a plain FOV pull. Our iron-sight
ADS + per-gun tune table is strictly better; nothing to take.

**Correction retained from the 0.1a pass:** per-weapon `movementspeed` is **vanilla MOHAA**, not a
SurgOp invention.

---

## 4. Anything else genuinely new?

Cross-checked against `docs\FEATURES.md` and `.wolf\buglog.json`.

| SurgOp 1.0 feature | Verified in | Do we have it? |
|---|---|---|
| **Re-authored per-surface impact / explosion FX** — 35 `models/fx/*.tik`, **25 of which grew by more than 5 lines**, several 2–4×: `bh_stone_hard/lite` 137/82 → **242**, `bh_metal_lite` 66 → **206**, `grenexp_fireball` 14 → **98**, `grenexp_metal` 41 → **151**, `grenexp_mud` 41 → **157**, `grenexp_paper` 41 → **148**, `bh_wood_hard` 86 → **142**, `bh_dirt_*` 67 → **119**. Backed by 250 new `textures/effects` + 69 `textures/sprites`. | `zzzzzzzzzzzzzz__Experience_Effects.pk3` (361 files) | **Partly — this is still the one genuinely additive idea.** We ship `coop_smokeWhip`, suppression FX, blood trails, `coop_barrelsmoke.tik`/`coop_gunsmoke.tik`, but we have **never** re-authored the stock per-surface bullet-impact emitters. 1.0's version is 6.4× the file count of 0.1a's. |
| Fresh gun / impact / footstep audio | `zzzzz_kun0.1a.pk3` — **the 0.1a pack unchanged, by its own filename** | **Yes, and better.** 47 re-recorded gun sounds, 24 footstep surfaces, 44 surface impacts, whizbys, casings, plus reverb/HRTF/occlusion/distance-tails. **123 of its 287 sound files collide with files we already ship.** Only **18** of its 287 sounds are not retail paths at all. |
| Blood decal rework (`blood_long`, `blood_splat`, `blood_splat2`; `bh_human_uniform_hard/lite` 77/75 → **140** lines) | `zzzzz_blood.pk3` | **Yes, and far better.** 4-tier gore, drip + growing pool, bone-attached wound props, renderer UV wounds (`tr_gore.c`), headshot burst/wall-splat. |
| **Complete main-menu retexture** — 680 `textures/mohmenu` TGAs incl. 40 level-briefing plates | `zzzzz_kunmohmenu.pk3` (**new in 1.0**) | **No, and we do not want it.** It collides with **186** of our `textures/mohmenu` files — the Start Game wall board, corkboard case file, medal case, coop settings plaques. Wholesale overwrite of our menu identity. |
| Circular analogue health meter | `zzz_healthmeter.pk3` | **No.** Third-party 2006 asset with a no-modification notice, and one of its two textures is still unresolvable. Cosmetic; not recommended. |
| Bigger crosshair (`ui/crosshair.urc`) | `zzzz_weapon.pk3` | **Yes, better** — true-aim crosshair tied to ADS. |
| Higher-res muzzle flash | `ZZfirekunmade.pk3` | **Yes**, we already override `flashnode1.tga`. |
| HD world / character textures (~4,300 files) | KUN Texture1/2/3/4 | **Yes, and larger.** Our ESRGAN ×4 packs + `zzzzzzz_dds_override.pk3` + `zzzzzzz_dds_hdmem.pk3` + AA_HD_Project. And ours are not ripped. |
| Menu music / stingers (`serenade`, `colonel`, `success`, `beschuss` mp3) | `zzzzz_kun0.1a.pk3` | **Yes** — 339 cues / 103 min from the Frontline PS3 extraction. |
| **Gameplay scripts** | — | **One `.scr` in 2.9 GB**: `global/ambient.scr` (§6), and it is a **downgrade**. |
| **AI changes** | — | **None.** Zero AI scripts, zero `global/ai*.scr`, zero actor TIKs. |
| **Animations** | — | 43 `.skc`, **9 net-new**: the P38 set (idle/fire/empty/reload2), Thompson (idle/fire/reload — unreachable), panzerschreck (idle/reload — dead path). No character animation whatsoever. |
| **Engine binaries** | — | **Zero `.dll`/`.exe`.** The "SOF2 engine code" claim from the 2021 news posts is not in this file. |
| **Readme / credits / licence** | — | **None.** The only `.txt` files are the 2006 third-party healthmeter readme and two copies of retail `faces.txt`. §7. |

### Systems SurgOp still has nothing of

Coop framework, DBNO, medkit, officer boss waves, AI dynamics/squad/morale/retreat, enemy
count-scaling, difficulty director, XP/rank, challenges/medals, armory loadout picker, lobby,
objectives HUD, sprint/stamina/cover/emotes, 3P camera suite, dynamic weather, build mode, map-test
harness, NAT hole-punch, holdout gamemode. Unchanged from 0.1a.

---

## 5. Dead weight and junk

- **`textures/modelsss/` — 1,074 files, ~140 MB, entirely dead.** Measured: **1,073 of 1,074** have
  a `textures/models/` twin that exists in retail, and of the 1,053 whose twin also ships *inside*
  the pack, **1,034 differ** from it. Nothing can reference `modelsss` — it is not a search path the
  engine or any shader uses. It is a parked backup of the model textures under a typo'd directory.
- **`textures/scripts/effects.shader` and `textures/sprites/effects.shader`** — two more copies of
  the effects shader filed under `textures/`, where the engine never scans for shaders. Dead.
- `models/weapons/springfield/1springfield.skd` (2,588 tris) — unreferenced.
- `models/weapons/bazooka/panzerschreck.skd` + 2 `.skc` — unreferenced (§3.2).
- `models/weapons/sounds.tik`, `models/weapons/thompsonsmg111.tik` — unreferenced (§3.1).
- Shipping junk: 2 `.DS_Store`, 2 `Thumbs.db`, 2 `.max` (raw 3ds Max sources), 1 `q3ase.cfg`,
  files named `… - 副本` ("copy").
- 1 corrupt archive member (§2).

---

## 6. `global/ambient.scr` — still the pre-patch AA version

`zzzz_weapon.pk3` ships a 6,265-byte `global/ambient.scr`. Same defect as 0.1a: it is the **2002 AA**
file. It declares `main local.music:` and resolves music through `local.music`, and it carries
**neither** the `level.ambient_script_run` re-entry guard **nor** the
`level.gametype = int(getcvar(g_gametype))` assignment that the expansion-era version has. We ship
our own `global/ambient.scr`; this would silently replace it. **`level.gametype` is the flag the
entire coop framework gates on** (`level.gametype != 0`), so this file alone is a coop-breaking
import.

---

## 7. PROVENANCE — the blocker did not change, and 1.0 adds filename-level corroboration

**Do not re-litigate; recorded for completeness.**

1. **1.0 ships no readme, no credits and no licence of its own.** The only `.txt` files in 2.9 GB
   are two copies of retail `faces.txt` and the third-party healthmeter readme. The author's ModDB
   description for the family still states the textures come from *Call of Duty: World at War /
   MOH: Airborne / CoD2 / CoD1 / Crysis Warhead / Enemy Front / S.T.A.L.K.E.R.* **Nothing in 1.0
   contradicts or qualifies that.**
2. **The third-party redistribution is still inside it, unchanged.** `zzz_healthmeter.pk3` still
   carries `REAME.txt`: *"Made: Jan. 6, 2006 … [Please do not modify my works without written
   permission.] -Tag: A Cowboys Job / Nosebleed"*. Still uncredited on the mod page.
3. **New in 1.0 — filename-level markers of other games.** The 0.1a scan found *zero* in-file
   provenance strings. 1.0's much larger texture set contains file **names** that do not belong to
   MOHAA:
   - `textures/general_structure/战团木头.dds` — 战团 is the Chinese community name for
     *Mount & Blade: Warband*; 木头 = "wood". A second `木头.dds` sits beside it.
   - `textures/central_europe/okinawa_door_shuri_int_twdr_02_c.dds` — "Okinawa / Shuri" naming.
   - `textures/central_europe_winter/rtcwsnow_s.tga` — RtCW.
   - `textures/general_industrial/wood_m05_usata.jpg`.
   ⚠️ **These are filenames, not verified content.** They corroborate the author's own admission;
   they do not independently prove any specific asset's origin. Per the project rule, no claim is
   made about what the pixels are.
4. **Two raw `.max` source files** are still shipped, origin unknown.

**Verdict unchanged: this disqualifies the texture and audio packs for a project that ships
publicly.**

---

## 8. SHADER COLLISIONS

**Scan basis:** 41 retail `*.pk3` opened across `G:\mohaa-gl2\{main,mainta,maintt}` **excluding every
filename containing `co-op_hzm`** → 497 `scripts/*.shader` → **7,754 unique names at brace depth 0**
(the 17 `Pak*` originals alone give 7,041). Our side: 61 shader files → 1,254 names. SurgOp 1.0:
**41 shader files → 669 unique names.**

| Result | Count |
|---|---:|
| SurgOp names that **collide with retail** | **641** |
| SurgOp names that **collide with the HZM coop tree** | **1** (`binoculars`) |
| SurgOp names that are genuinely **new** | **28** |

The 28 new names: `03`, `barrel_water_splat1`, `bh_snow_puff1`, `bh_snow_puff2`, `garand_clip`,
`garand_metal`, `garand_stock`, `hd`, `k98_metal`, `k98_metal_s`, `k98_scope`, `k98_stock`,
`k98_stock_s`, `m11`, `m1918a2_bar`, `m1928a1_thompson`, `m9`, `m97_shotgun`, `mp401`, `mp402`,
`mp403`, `p38parabellum`, `springfield_1`, `stg1`, `stg2`, `textures/hp/healthmeter`,
`textures/hp/healthmeterflash`, `textures/hp/healthstealthback`.
⚠️ `hd`, `m9`, `m11`, `stg1`, `stg2`, `mp401`, `03` are dangerously generic.

⚠️ **`binoculars` is a real collision with us** — SurgOp redefines it in its `items.shader`, and we
define it in our tree (`coop_binoculars.tik` is a shipped reward item). 0.1a had **zero** HZM shader
collisions; 1.0 has one.

### The 641 retail collisions split into two very different hazards

**(a) Whole-file overrides — 521 names, and they delete.** Twelve SurgOp shader files carry a
*retail filename*, so the engine's `FS_ListFiles`/`FS_ReadFile` picks exactly one copy and the other
disappears entirely:

| SurgOp file | names | deletes vs `maintt\pak1.pk3` |
|---|---:|---|
| `items.shader` | 202 | **17** — `beam_cross`, `book2_pulse`, `colonel_holster`, `crate_1942`, `document1_pulse`, `envelope_pulse`, `inventory_stickybomb_stickybomb`, `inventory_stickybomb_stickybomb_pulsing`, `parachute_pack`, `parachute_pack2`, `radiopack`, `sc_al_brit_inf_gear`, `sc_al_us_inf_gear`, `sc_al_us_infpack`, `sc_p_campfire`, `sc_p_firestone`, `sticky_backpack` |
| `weapons_german.shader` | 12 | **5** — `kar98gren`, `kar98gren_cup`, `kar98gren_proj`, `kar98gren_sight`, `kar98gren_wrap` |
| `jeep.shader` | 8 | **3** — `jeep_des`, `jeep_glider`, `jeep_win_d` |
| `static_obstacles.shader` | 15 | **1** — `static_hedgehog_snowy` |
| `static_items.shader` (104), `submodels.shader` (141), `weapons_allied.shader` (21), `higgins.shader` (3), `p47.shader` (6), `protoamerican.shader` (7), `howitzer.shader` (1), `shells.shader` (1) | 284 | **0** |

**Total: 26 shader names lost against Breakthrough**, down from 36 in 0.1a — and now spread across
four files instead of one. The casualties changed character too: 0.1a killed FX (flak, snowfall,
C-47 smoke, tracers, water rings); 1.0 kills **Breakthrough item and gear shaders** —
paratrooper packs, the sticky bomb, radio packs, Allied infantry gear, campfires, the rifle-grenade
Kar98, the glider jeep.

**(b) Duplicate-name registration — ~110 names, non-deterministic winner.** `effectsssss.shader`
(113 names) and `effectsyuanlai.shader` (112) do **not** carry a retail filename, so retail's
`effects.shader` still loads *alongside* them. Verified in the engine
(`renderergl1/tr_shader.c`): `ScanAndLoadShaderFiles` concatenates the shader files in reverse list
order and `AddShaderTextToHash` **prepends**, while `FindShaderText` returns the **first** chain
match — so the *last-parsed* definition wins, and parse order comes from `FS_ListFiles`, not from
pk3 sort order. Result: 110 effect shaders (`bh_*`, explosion, smoke, blood) would resolve to
whichever copy the file listing happened to put last. This is exactly the contested-shader-name
failure mode in [TRAPS.md § T6](../TRAPS.md#t6).

### ⚠️ Install-location caveat (correcting the 0.1a note)

The 0.1a analysis asserted that `zzzzzzzzzzzzzz_*` "sorts after everything, so this file wins
outright." That is only true **within one game directory**. Verified in
`openmohaa-hzm/code/qcommon/files.cpp` (`FS_Startup`, lines 3477–3546, and the HZM unify block at
3509): `FS_AddGameDirectory` prepends, later adds win, and the order is
`main` → `mainta` → `maintt`. So **`maintt` beats `mainta` beats `main`.**

- The mod's own instruction is *"unzip all things in your MOHAA/Main/ directory"* — installed there
  under a Breakthrough profile, **its shader files never beat `maintt\pak1.pk3` at all**, and both
  §8(a) hazards evaporate (while §8(b) remains, because that one is name-based, not file-based).
- Installed into **`maintt\`** — which is where *our* build deploys — the `zzz*` names sort after
  `pak1.pk3` inside the same directory and **do** win. §8(a) applies in full.

---

## 9. Did 1.0 fix the Breakthrough incompatibility? **Partly — by rename, not by design.**

**Direct answer to the question asked: no, `effects.shader` no longer deletes anything, because
SurgOp 1.0 does not ship a `scripts/effects.shader` at all.**

| | 0.1a | 1.0 |
|---|---|---|
| Ships `scripts/effects.shader`? | **Yes** | **No** — renamed to `scripts/effectsssss.shader`; the backup copy is `scripts/effectsyuanlai.shader` (原来 = "original") |
| Deletions from `maintt\pak1.pk3`'s `effects.shader` | **36** | **0** |
| Deletions from `maintt\pak1.pk3` overall | 36 | **26** (via `items` 17 / `weapons_german` 5 / `jeep` 3 / `static_obstacles` 1) |
| New failure mode | — | **110 duplicate shader-name registrations** across `effectsssss` + `effectsyuanlai` + retail `effects.shader` |

Measured content of the renamed file: `effectsssss.shader` = the **`main\Pak0.pk3`** effects shader
(110 names, 110/110 shared, **0 dropped**) **plus 3** — `bh_snow_puff1`, `bh_snow_puff2`,
`barrel_water_splat1`. Against `maintt\pak1.pk3`'s 146-name copy it is short by 36, exactly the 0.1a
delta — the *content* is still 2002-vanilla; only the filename changed, which is what saves us.
`effectsyuanlai.shader` is the same base with `blood_long`, `blood_splat`, `blood_splat2` instead.

So the flak bursts, C-47 crash smoke, snowfall, tracers, water rings and mortar snow FX **survive**
in 1.0. What breaks instead is Breakthrough item/gear shading, and only if installed into `maintt\`.

**The pack is still built against 2002 vanilla `main/`.** Two of the three 0.1a proofs stand
unchanged: the pre-patch `global/ambient.scr` (§6) and
`models/statweapons/mg42_gun_fake.tik`, which still reverts the expansion-era per-mode
`sp`/`dm`/`realism` blocks to flat AA syntax.

---

## 10. Collision surface against our tree

**375 of SurgOp's 7,033 paths collide with files we ship** (up from 156 in 0.1a).

| Group | Count | Impact |
|---|---:|---|
| `textures/mohmenu/*` | **186** | **New in 1.0.** Would overwrite our menu identity — Start Game wall board, level-briefing plates, medal case, sign plaques. |
| `sound/weapons` + `sound/characters` | **123** | Would revert our recorded gun/foley set. |
| `models/weapons/*` | **25** | Includes **12 weapon TIKs** carrying our uncommented `holstertag`/`holsteroffset` lines — importing reverts **weapons-on-back** (`SHIPPED-VERIFIED`) for the entire starter loadout. Also 13 paths that collide with **`zzzzz_xw_weapons.pk3`**: the whole `bar_lmg/` set (model + 3 anims), `kar98.skc`, `mp40_fire/reload.skc`, `mp44.skc`, and 5 Springfield `.skc`. |
| `textures/models`, `misc_outside`, `hud`, `gametext`, `wilderness` | 36 | HD texture regressions. |
| `global/ambient.scr` | 1 | §6 — coop-breaking. |
| `models/statweapons/mg42_gun_fake.tik` | 1 | Expansion-syntax revert. |
| `models/fx/muzflash/flashnode1.tga`, `ui/hud_health.urc`, `textures/.ds_store` | 3 | — |

---

## 11. Recommendation

**Take nothing as-is. Do not import any pk3 from Surgical Operation 1.0.**

The weapons question — the reason this 2.9 GB was pulled — has the same one-line answer it had for
0.1a: **there is nothing to port.**

The single idea still worth acting on, built from scratch in our own pak with our own names:

> **Re-author the per-surface bullet-impact and grenade emitters** (`models/fx/bh_*_hard/lite.tik`,
> `grenexp_*.tik`) with lingering multi-stage smoke and per-axis acceleration, the way
> `__Experience_Effects` does — 25 of its 35 FX TIKs grew substantially, several 2–4×, and the
> emitter work is real. This remains a genuine gap: we have muzzle/impact gun smoke and suppression
> FX but have never touched the stock impact emitters. Doing it ourselves carries none of §7–§10.

Everything else the pack does we already do better (audio, gore, HD textures, ADS, crosshair, muzzle
flash, menus), or it is actively harmful (§6, §8, §10), or it is sourced in a way this project
cannot ship (§7).

---

## Appendix — how to reproduce

Scripts in `…\scratchpad\surgop10\`. Run with `PYTHONIOENCODING=utf-8` (the pack contains GBK-encoded
path names) and **native Windows Python with Windows paths** — MSYS `/c/…` paths make
`os.path.isdir` return False and silently scan nothing.

| Script | Purpose |
|---|---|
| `findlink*.py` | Resolve the gamepressure POST flow to the real `metrocf.gameplay.pl` URL. |
| `baseline.py retail` / `baseline.py ours` | Build `retail_index.json` (41 paks, `co-op_hzm` excluded) and `ours_index.json`. |
| `analyse.py` | Flat index of the outer zip + 15 nested pk3s; weapon TIK census; SKD tri counts; NEW-vs-retail; shader-name collisions; effects.shader diff; script/binary listing. |
| `analyse2.py` | Per-file shader deletions vs retail; TIK/SKC/URC/sound census; collisions with our tree; per-pk3 census. |
| `analyse3.py` | `effectsssss`/`effectsyuanlai` vs retail `effects.shader`; weapon stat diff; `modelsss` probe. |
| `analyse4.py` | Full decompression integrity test; `modelsss` twin comparison; new-file list. |
| `analyse5.py` | Cross-reference hunt (who references what); `rank` audit; FX TIK line growth; malformed-shader brace-depth scan. |
| `analyse6.py`–`analyse10.py` | SKD tri counts against **original `Pak*` only**; panzerschreck/BAR path resolution; xw-pack collision list; weapon-shader texture-reference resolution. |
