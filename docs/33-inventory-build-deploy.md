# Build, deploy and sandbox — as the scripts actually behave

Every claim here is anchored to a line in `build.ps1` / `publish_release.ps1` or to a file on disk,
observed 2026-07-29. Nothing is carried over from `CLAUDE.md`, which is stale on several of these.

---

## 1. `build.ps1` — what it really does

`C:\mohaa-coop-dev\build.ps1`, 153 lines. Mod-side only. It does **not** compile anything.

### Safety gate (runs first)

`build.ps1:35-43` — aborts if `openmohaa.exe` is running with a command line that does **not**
contain `dedicated 1`. Reason recorded inline: the engine memory-maps the pk3s at launch, so
overwriting them mid-session makes it read garbage at stale offsets (bug-241 — phantom
"label does not exist" errors and a watchdog server crash mid-playtest).

### Packing — three pk3s, not one

`build.ps1:20-26`. The old monolith `zzzzzz_co-op_hzm_mod_mohaa.pk3` is retired and actively
deleted from both deploy targets (`build.ps1:110-113`).

| pk3 | contents (`$assetDirs`, `build.ps1:28`) | size on disk 2026-07-29 |
|---|---|---:|
| `zzzzzz_co-op_hzm_mod_assets_snd.pk3` | `sound/` | 514.06 MB |
| `zzzzzz_co-op_hzm_mod_assets_tex.pk3` | `textures/ models/ gfx/ env/` | 645.06 MB |
| `zzzzzz_co-op_hzm_mod_code.pk3` | everything else (catch-all) | 18.86 MB |

Load order is alphabetical, so `code` sorts last and **overrides** the two asset paks
(`build.ps1:17-18`). Excluded from every pak: top-level `_notes/` and `_research/`
(`build.ps1:27`), plus `.gitignore`, `.gitattributes`, `README.md` (`build.ps1:28`), plus any
`.bak` / `.pk3` / `.git` path (`build.ps1:46-50`).

> `_research` was added to the exclude list very recently and that edit is **still uncommitted**
> in the workspace repo (`git diff build.ps1`, one line, `build.ps1:27`). Before that edit the
> research tree — pipeline notes and retail extracts — was shipping to players inside
> `..._code.pk3`.

### Determinism

`build.ps1:11-15` and `:66-80`. Packing must be byte-reproducible because the auto-updater
compares each pak's sha256 against the released manifest to decide whether a client needs to
re-download it (bug-237). The rules enforced: entries sorted by relative path, entry mtime set to
the **source file's** mtime rather than build time (`build.ps1:89`), git files excluded, and an
input digest cache under `build_out/` that skips repacking a bucket entirely when
`relpath|size|mtime` of every member is unchanged (`build.ps1:70-82`, cache written at
`build.ps1:98-99`).

### Every path it writes

| # | Destination | What | Anchor |
|---|---|---|---|
| 1 | `hzm-mohaa-coop-mod\<pak>.pk3` | the three paks, in the source tree | `build.ps1:76,86` |
| 2 | `build_out\<pak>.pk3` + `.inputs` | the determinism cache | `build.ps1:98-99` |
| 3 | `G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\` | three paks (basepath) | `build.ps1:5,107-109` |
| 4 | `%APPDATA%\openmohaa\maintt\` | three paks (homepath, wins over basepath) | `build.ps1:6,107-109` |
| 5 | both of the above | `autoexec.cfg` | `build.ps1:119-120` |
| 6 | both of the above | `coop_defaults.cfg` | `build.ps1:127-128` |
| 7 | `G:\GOG\Medal of Honor - Allied Assault War Chest\` (**root**) | `cgame.dll` | `build.ps1:132-142` |
| 8 | `G:\GOG\Medal of Honor - Allied Assault War Chest\` (**root**) | `renderer_opengl1.dll` | `build.ps1:144-152` |

Sources for 7 and 8 are the CMake Release outputs
(`openmohaa-hzm\.cmake\code\client\cgame\Release\cgame.dll`, `build.ps1:133`;
`...\code\renderercommon\renderergl1\Release\renderer_opengl1.dll`, `build.ps1:145`).
Both copies are wrapped in
try/catch and downgrade to a printed **WARNING** on failure — a locked file means the binary
silently does not update while the script still reports success.

### The hazard: it writes into the real GOG install

Targets 3, 5, 6, 7 and 8 are inside the player's actual retail installation. There is:

- no backup taken by the script,
- no version stamp,
- no rollback,
- and no verification that the copy landed.

The `.bak` sprawl in the GOG root is the manual compensation for this — as of 2026-07-29 the root
holds 8 `openmohaa.exe.*_bak`, 7 `game.dll.*_bak`, 5 `cgame.dll.*_bak` and 11
`renderer_opengl2.dll.*_bak` files, named by feature (`pre_ent2048_bak`, `pre_cs8192_bak`,
`pre_ssao_bak`, …). This is the project's real rollback mechanism for binaries and it is entirely
by hand.

### What `build.ps1` does NOT deploy

`openmohaa.exe`, `game.dll` and `renderer_opengl2.dll` are **manual copies**. This matters because
several engine changes are documented as requiring the binaries to ship **together** — the
`GENTITYNUM_BITS 11` protocol change (`qcommon/q_shared.h:1667`) and the `MAX_SOUNDS` raise
(`qcommon/q_shared.h:1742`) both alter the wire format shared by exe + cgame + game.

Observed state, 2026-07-29 (mid-session; another workflow was building at the time, so read these
as a snapshot of the *mechanism*, not a permanent defect):

| binary | in GOG root | latest CMake build | delta |
|---|---|---|---|
| `openmohaa.exe` | Jul 21 17:15, 1 708 544 B | Jul 28 21:46, 1 710 592 B | root is 7 days behind |
| `game.dll` | Jul 24 09:33, 3 999 744 B | Jul 29 01:07, 4 004 864 B | root is 5 days behind |
| `cgame.dll` | Jul 28 22:57, 617 984 B | Jul 29 01:07, 619 008 B | auto-deployed, near-current |
| `renderer_opengl1.dll` | Jul 28 22:57, 844 288 B | Jul 29 01:07, 845 824 B | auto-deployed, near-current |
| `renderer_opengl2.dll` | **Jul 3**, 939 520 B | Jul 29 01:18, 1 069 568 B | **root is 26 days behind** |

The gl2 gap is structural, not accidental: `build.ps1` has a deploy block for
`renderer_opengl1.dll` and none for `renderer_opengl2.dll`. All renderergl2 work — 29 files,
+5 794 / −281 lines currently uncommitted — is therefore invisible in the real install and only
observable in the sandbox below.

### A stale `cgame.dll` is sitting in the homepath

`%APPDATA%\openmohaa\maintt\cgame.dll` — dated **Jun 26**, 570 880 B — a month older and 47 KB
smaller than the deployed root copy. `build.ps1` never writes it and never removes it. Alongside
it is `cgame_pre_soundlimit_bak.dll`. If any load path prefers homepath over the GOG root, the
game runs a month-old cgame against current scripts. Nothing in the tree establishes which path
wins; this is unresolved and worth a deliberate check.

---

## 2. `publish_release.ps1` — releases are staged from the deployed install

Flow, `publish_release.ps1:4` — preflight → build → stage → manifest with asset reuse → `gh`
release (draft → publish). Guardrails: it refuses to overwrite a published tag
(`publish_release.ps1:37`), it verifies every staged path exists before hashing
(`publish_release.ps1:89`), and it refuses to publish if `manifests/latest.json` already carries
the version being published — the leftover-from-an-aborted-run case, with the restore command
printed in the error (`publish_release.ps1:99-103`).

**The load-bearing detail** (`publish_release.ps1:48-55`, comment dated 07-21 v1.1.51): the five
engine binaries are staged from `$gog` — the **deployed GOG root** — not from the build tree. The
stated reason is that a `--clean-first` rebuild would ship binaries nobody has played. So the
release artifact is *the exact binary set that was tested*, which is a real correctness win, and
simultaneously means **a release is not reproducible from source**: there is no recorded mapping
from a shipped `openmohaa.exe` back to a commit.

Manifest history: `manifests/` holds 30 files, `manifest-1.1.26.json` … `manifest-1.1.55.json`
plus `latest.json`. Current release **1.1.55**, created `2026-07-27T01:31:38Z`. Per-file asset
reuse is visible in the manifest — inside 1.1.55, `game.dll` points at the v1.1.55 download URL
while `openmohaa.exe` and `cgame.dll` still point at v1.1.51, `renderer_opengl1.dll` at v1.1.50
and `updater.ps1` at v1.1.44. Unchanged files are not re-uploaded.

---

## 3. The two installs

### Real install — `G:\GOG\Medal of Honor - Allied Assault War Chest`

Basepath. Homepath is the separate `%APPDATA%\openmohaa\`. Homepath wins over basepath, so the
three coop paks exist in **both** and the `%APPDATA%` copies are the ones actually loaded. Verified
identical sizes on 2026-07-29 (514.06 / 645.06 / 18.86 MB in each location).

The homepath `maintt/` also carries the third-party HD packs that are **not** built by
`build.ps1` and are staged into releases from the GOG root
(`publish_release.ps1:79-84`): `zzzzzz_hd_world.pk3` (360 MB), `zzzzzz_hd_charskins.pk3` (88 MB),
`zzzzz_hd_foliage.pk3` (185 MB), `zzzzzz_hd_skybox.pk3`, `zzzzzz_hd_fx.pk3`,
`zzzzz_geared_soldiers.pk3`, `zzzzz_xw_weapons.pk3` (38 MB), `zzzzzzz_dds_hdmem.pk3`.
It also holds 14 `boot_<map>.cfg` files and a `cmpatch/` directory (the e1l2 collision-brush
surgery data).

### Sandbox — `G:\mohaa-gl2`

A **complete second game installation**, not a symlink or an overlay. Its own `main/`, `mainta/`,
`maintt/` (with its own copies of the retail paks and the HD packs), its own binaries, and its own
homepath at `G:\mohaa-gl2\home` — plus a second one, `G:\mohaa-gl2\home_test`.

Launcher `G:\mohaa-gl2\PLAY-GL2.bat` pins everything explicitly:

```
openmohaa.exe +set com_target_game 2 +set fs_basepath "G:\mohaa-gl2"
  +set fs_homepath "G:\mohaa-gl2\home" +set cl_renderer opengl2
  +set r_ext_framebuffer_multisample 8 +set r_ext_multisample 8
  +set r_uselod 0 +set r_lodscale 28
  +set r_mode -1 +set r_customwidth 3440 +set r_customheight 1440 +set r_fullscreen 1
  +set developer 1 +set r_drawSunRays 1
  +set r_specularMapping 0 +set r_cmdtrace 0 +set r_skeldiag 0 +set logfile 2
```

The batch file's own comments record why the latched cvars are set on the command line: applying
them from the in-game menu triggers a `vid_restart` that **crashes under gl2**. `r_drawSunRays 1`
is `CVAR_LATCH` and only became meaningful once the bug-1154 sun bridge gave rend2 a real per-map
sun direction from worldspawn.

Companion bisect harnesses live beside it: `PLAY-GL1-BISECT.bat`,
`BISECT-vanilla-models.bat`, `TEST-A-our-gore-only.bat`, `TEST-B-full-retail-chain.bat`,
`RESTORE-packs.bat`, `UNDO-tests.bat`, and a `_disabled_packs/` staging directory — i.e. the
sandbox exists specifically to bisect asset-pack and renderer interactions by adding and removing
whole paks.

### The consequence for status honesty

On 2026-07-29 the sandbox held a **uniform** binary set, all stamped Jul 28 22:22 —
`openmohaa.exe` 1 710 592 B, `game.dll` 4 004 864 B, `cgame.dll` 619 008 B,
`renderer_opengl1.dll` 845 312 B, `renderer_opengl2.dll` 1 067 008 B. The real install held a
**mixed** set spanning Jul 3 → Jul 28.

> **The two installs are running different engines.** Anything confirmed working in
> `G:\mohaa-gl2` is SHIPPED-UNVERIFIED with respect to the real install until it is re-checked
> there, and vice versa. This distinction is not currently recorded anywhere in the logs, and it
> silently invalidates any "verified" claim that does not name which install it was verified on.

---

## 4. Cross-references

- `docs/30-inventory-coop-subsystems.md` — every `coop_mod/*.scr` and the real `main.scr::main` boot chain
- `docs/31-inventory-coop-cvars.md` — all 642 `coop_*` cvars, defaults and anchors
- `docs/32-inventory-engine-cvars.md` — all 217 HZM engine cvars, defaults, flags, and the 8 registration conflicts
