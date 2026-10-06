# Weapon HD textures: Phase 1 (audit + pilot)

**Status: PILOT STAGED, awaiting coordinator / user approval. Nothing deployed, committed or shipped.**
The only repo file touched outside this folder: `docs/tools/harness_guard.py` (registration of `G:\mohaa-weaponhd`,
slot "weaponhd"), plus the buglog entries.

| file | what |
|---|---|
| [AUDIT.md](AUDIT.md) | How weapons are drawn (1P = 3P), the pipeline, the randomisation research and recommendation |
| [AUDIT_TABLE.md](AUDIT_TABLE.md) | Generated: 72 base weapons, 178 sheets, variants and finishes, with resolution, format and winning pak |
| `tools/inventory.py`, `tools/audit.py` | Engine-accurate TIK -> shader -> image resolver (read-only) and the table generator |
| `tools/skd.py` | Minimal SKD reader (UVs, normals, bone-space positions) |
| `tools/weaponhd.py` | The pipeline: `python weaponhd.py kar98 thompsonsmg colt45` (env `WHD_WEAR`, `WHD_STAGE`, `WHD_NOENC`) |
| `tools/estimate.py` | Full-set size estimate |
| `tools/run_weaponhd.py`, `tools/stills_sheet.py` | The batched in-engine run (private `G:\mohaa-weaponhd`) and the still sheets |
| `stage/` | **The pilot pak content (final):** 3 DXT1 sheets with full mips |
| `stage_run2_ingame/` | The exact build the in-engine stills of run 2 were shot with (one review round older) |
| `previews/` | Offline before/after texture crops and overviews (final build) |
| `stills/` | In-engine stills: `zoom_<gun>_<view>.jpg` (gun region, 1.5x) and `full_<gun>_<view>.jpg` |

## Pilot outputs

| sheet | today | pilot (stage/) | md5 | QA corr / mean shift |
|---|---|---|---|---|
| kar98/kar98.dds | HRRTM 2048x1024 DXT5, 2.8 MB | 4096x2048 DXT1, 5.6 MB | f73a5874 | 0.994 / +0.0% |
| thompsonsmg/thompsonsmg.dds | HRRTM 2048x2048 DXT5, 5.6 MB | 4096x4096 DXT1, 11.2 MB | bfb49882 | 0.989 / -0.6% |
| colt45/colt45.dds | HRRTM 2048x2048 DXT5, 5.6 MB | 4096x4096 DXT1, 11.2 MB | 87cd57a8 | 0.985 / +0.1% |

- Pak `zzzzzzzzzz_coop_hd_weapons.pk3` for the 3 guns: **28.0 MB raw, 17.3 MB zipped**.
- VRAM is 2x today, not 4x, because DXT1 replaces DXT5 (no pilot sheet uses alpha).
- The in-engine imagelist confirms the new sheets load:
  - Kar98: `4096x2048 DXT1`
  - Thompson and Colt: `4096x4096 DXT1`
- The reload magazines, `_lite` AI TIKs, `static_kar98`, the dbno pistol and the gold/chrome/blued finishes paint from
  the same sheets, so they follow automatically.

## In-engine runs (slot "weaponhd", 2 batched runs, m3l2, 1920x1080, fov 80, gl2)

Binaries were byte copies of the LIVE G:\mohaa-gl2 set:
- exe d23dd662
- cgame d563b759
- game 6f68255a
- gl2 16b8534d

Logs are at `G:\mohaa-weaponhd\runs\<session>\qconsole.log` (0 Script Errors).

- Run 1 (before / after): 1P idle and 1P ADS are good. **The 3P framing failed**: the camera sat behind the body.
- Run 2 (before2 / after2 / heavy2):
  - 1P idle and ADS were re-shot.
  - 3P was re-shot with a right-side, pitched camera. The gun is visible but small.
  - The heavy-wear option was tested at WHD_WEAR 1.8.

**Honest result:**
- **1P idle at 1080p: almost no visible difference.** HRRTM's art already resolves at that distance.
- **ADS: visibly crisper.** On the Thompson receiver top and rear sight, the Kar98 cocking piece and receiver
  rear, and the Colt slide rear, grain, chips and edges now resolve.
- **3P: no visible difference.** The gun covers a few dozen pixels. 3P matches 1P by construction (same TIK and
  sheet), not by any extra work.
- **Heavy wear (1.8x):**
  - In-game it looks nearly the same as normal.
  - At texture level it amplifies the procedural look.
  - **Dropped**, as the independent review recommended.

**Independent review** (a read-only agent; full list in the coordinator report):
- No blockers.
- No gibberish or misspelled text; the Colt and Auto-Ordnance markings are legible.
- No tiling or clones, and no wood grain on metal.
- Should-fixes found, all four fixed after review in `stage/` (offline-verified in `previews/`, **not re-shot
  in-engine**, because both slot runs are used):
  - The Colt lost its parkerized speckle. Now restored: the source's own band-passed detail plus an additive matte speckle.
  - The Kar98's top metal was airbrushed. Now restored the same way.
  - Scratches were an even scatter. They now cluster at contact zones and edges.
  - A bright copper edge on the plastic Colt grips. Edge wear is now excluded on plastic, and the polish is softened.
- Remaining nits:
  - faint darker wedges inside a Kar98 receiver part (inherited from the source and amplified slightly)
  - the Thompson's source diagonal hatching is a little stronger

## Findings outside the pilot (logged)

| bug | finding |
|---|---|
| bug-3397 (OPEN) | The Thompson sheet is uploaded twice on every Thompson map: our generated skin shaders use the lower-case path, while HRRTM/retail use `ThompsonSMG/ThompsonSMG`, and the image cache is case-sensitive. That is 6 MB wasted today and 12 MB at 4096. |
| bug-3378 | `p38 - Copy.tik` is a stray file inside the third-party HRRTM pak. Harmless, left alone. |
| (AUDIT.md section 1) | The Omaha pak `zzzzzzzzzz_coop_hd_m3l1a.pk3` wins 14 weapon sheets globally (BAR, MG42, m1clip, bazookashell...). The new pak out-sorts it by name without touching it. |
| bug-3374/3375/3376/3377 | Pipeline defects caught and fixed during the pilot: ESRGAN crackle, ESRGAN darkening, wear-shape slop, heredoc corruption |

## Full set: size, VRAM and effort

Sizes are DXT1 + mips. Zip ratio measured on the pilot: about 0.6.

| scope | sheets | raw | download (zip) |
|---|---:|---:|---:|
| A. Core, **balanced**: 4096 only for the 11 sheets with real >= 1280 px art (HRRTM set + BAR), the rest <= 2048 (4x source), small parts <= 1024 | ~167 | ~380 MB | ~230 MB |
| A'. Core, every main sheet at 4096 | ~167 | ~795 MB | ~475 MB |
| B. Skin variants (Hobbs/Guan/LV/DH/coop_v3), <= 2048 | ~134 | ~320 MB | ~190 MB |
| C. Re-bake baked finishes (bloody + 3 camo) from the HD bases at 1024 (today 128-620 px, 24 MB) | ~416 | ~290 MB | ~175 MB |

**VRAM** is paid only for guns present on a map. A typical map with ~10-12 guns costs about 60-120 MB for the
balanced tier, against roughly 40-60 MB today.

**Effort:**
- About 35-45 agent-hours. Most of it is the per-gun set-up: finish type, material overrides, contact zones and crop QA. That is ~20-30 min per gun for 60 base guns, plus extra care for the 113 LOW (<= 800 px) sheets, where ESRGAN hallucination risk is highest.
- Plus about 10-15 h of unattended single-job encoding. The project's mean-holding BC1 encoder takes 1-7 min per 4096 sheet.
- Plus 2 batched in-engine runs (all guns, idle + ADS).

## Questions for the coordinator / user

1. Scope and tier:
   - A (balanced) or A' (all 4096)?
   - Should B (skin variants) and C (finish re-bake) be included?
   - Every option ships in the separate pak; the 1.2 GB tex pak is not touched.
2. Given that the gain shows mainly in ADS, is the user happy with the pilot's wear strength (normal, not heavy)?
3. Tier B per-instance wear (AUDIT.md section 4) needs game.dll (about 30 lines in `Weapon::AttachToOwner`) plus TIK
   rows plus 2 extra 2048 variants per gun (~5.6 MB each). Approve, or stay with one unique wear per gun?
4. May the fix for bug-3397 (case-consistent paths in `gen_skins.py` / `gen_clip_art.py`) go in with the full set?
5. Normal maps on weapons would need tangent output in the skeletal draw path (engine work). Out of scope unless asked.
