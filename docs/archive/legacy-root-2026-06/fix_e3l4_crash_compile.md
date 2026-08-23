# e3l4 cold-load: crash + compile fixes (2026-06-24)

Two e3l4 cold-load bugs. Scripts edited under the mod tree; one engine C
change to rebuild. No GOG files touched. No game launch, no exe/pk3 rebuild
performed here (main session rebuilds).

---

## BUG 1 (ENGINE crash, 0xc0000409 /GS stack-buffer-overrun)

### Root cause (confirmed via crash dump + symbols)
`ParseMesh()` in **`code/renderergl1/tr_bsp.c`** writes a BSP curved-patch
surface into a **fixed-size stack buffer** with **no bounds check**:

```
MAC_STATIC drawVert_t points[MAX_PATCH_SIZE*MAX_PATCH_SIZE];   // MAX_PATCH_SIZE = 32 -> points[1024]
...
numPoints = width * height;          // width/height come straight from the BSP (ds->patchWidth/patchHeight)
for ( i = 0 ; i < numPoints ; i++ )  // writes points[i] up to numPoints, UNCHECKED
```

- `MAC_STATIC` expands to nothing (`code/qcommon/q_platform.h:79`), so `points[]`
  is a ~60 KB **stack** array (`drawVert_t` is ~60 bytes x 1024).
- `MAX_PATCH_SIZE = 32` (`code/renderergl1/tr_local.h:767`).
- If a patch surface's `patchWidth`/`patchHeight` (or their product) exceeds
  32 / 1024, the loop writes past `points[]`, corrupting the stack canary ->
  `__report_gsfailure` -> **exception 0xc0000409 in ucrtbase.dll +0xa527e**.
- The sibling `ParseFace()` already guards this (`tr_bsp.c:633`, `MAX_FACE_POINTS`).
  `ParseMesh()` was missing the equivalent guard that upstream ioq3 has
  (`ParseMesh: bad size`). This is the same bug-shape as the prior TIKI/skeletor
  overruns, but in a NEW unguarded site in the renderer BSP path.

### Evidence
- Windows Application event log (all recent openmohaa crashes incl. the 00:57
  e3l4 maptest, dump `openmohaa.exe.15776.dmp`): faulting module `ucrtbase.dll`,
  exception `0xc0000409`, fault offset `0xa527e` (= `__report_gsfailure`, the
  /GS handler). Exe PE timestamp `0x6A3B45DE` = the Release build.
- Minidump stack walk (faulting thread, only thread with engine frames):
  return addresses resolve (against the RelWithDebInfo PDB; approximate because
  the crash build is Release) into **`renderergl1/tr_bsp.c`** (ParseMesh region,
  ~line 722) and `tr_backend.c` (first-frame surface render) -- i.e. the BSP
  surface parse / first render, NOT the TIKI/skeletor parser. All previously
  fixed TIKI/skeletor/alias buffers were re-audited and remain correctly
  guarded (order[]/temp_aliases[] sized by MAX_TIKI_LOAD_ANIMS; loadsurfaces[]
  guarded; AddChannel MAX_GLOBAL_FROM_LOCAL; ChannelNameTable::RegisterChannel
  MAX_SKELETOR_CHANNELS; alias.c convalias[] both call sites; TIKI_SortLOD
  collapse[] guarded at SKB/SKD load by TIKI_MAX_VERTEXES). The renderer
  ParseMesh path is the one remaining unguarded fixed-size stack array.

### Note on the trigger asset
The extracted retail `e3l4.bsp` (BSP ident 'EALA', version 21) parses cleanly:
726 patch surfaces, max dims 9x11 (product 33) -- all within bounds. So a clean
single load of the retail BSP does not itself overflow. The crash is
intermittent (~9s post-load) and lands in the patch-parse/first-render path,
consistent with an over-size or corrupted `width*height` reaching ParseMesh.
Regardless of the exact source of the bad dimension, ParseMesh writing an
unbounded count into a fixed stack array is a real overrun vector that matches
the 0xc0000409 signature exactly; the guard closes it definitively and is a
no-op for valid input.

### FIX (implemented) -- FILE:LINE TO REBUILD
**`code/renderergl1/tr_bsp.c`**, function `ParseMesh`, inserted **after line 752**
(`height = LittleLong( ds->patchHeight );`), now at **lines 754-767**:

```c
    // HZM: bounds guard. points[] is a fixed-size stack buffer of
    // MAX_PATCH_SIZE*MAX_PATCH_SIZE drawVert_t. A patch surface in the BSP whose
    // patchWidth/patchHeight (or their product) exceeds that overruns the stack
    // and trips the /GS security cookie (exception 0xc0000409). ...
    if ( width <= 0 || height <= 0 || width > MAX_PATCH_SIZE || height > MAX_PATCH_SIZE
         || width * height > MAX_PATCH_SIZE * MAX_PATCH_SIZE ) {
        ri.Printf( PRINT_WARNING, "WARNING: ParseMesh: bad patch size (%i x %i), max %i; skipping surface\n",
                   width, height, MAX_PATCH_SIZE );
        surf->data = &skipData;
        return;
    }
```

Skips only the malformed surface (matches the existing NODRAW skip just above);
preserves the rest of the map. Uses only in-scope symbols (`skipData`,
`MAX_PATCH_SIZE`, `ri.Printf`).

**Rebuild:** `cmake --build C:\mohaa-coop-dev\openmohaa-hzm\.cmake --config Release --target openmohaa`
then copy `.cmake\Release\openmohaa.exe` to the game dir (same procedure as the
prior TIKI fix).

---

## BUG 2 (SCRIPT compile error) -- FIXED

`maps/e3l4/Bunker3.scr` line **555**. qconsole: `unknown command: guyexec` ->
`Couldn't compile 'maps/e3l4/bunker3.scr'`.

Typo: a misplaced space split the entity name `$piatguy` and merged `exec`:

```
- $piat guyexec coop_mod/replace.scr::lookat
+ $piatguy exec coop_mod/replace.scr::lookat
```

The fix matches the established pattern in the same file (lines 522, 544, 552,
566 all use `$piatguy exec coop_mod/replace.scr::...`). File is ASCII, CRLF, no
BOM. No other `guyexec` typos exist anywhere under `maps/e3l4/`.

**File edited:** `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\maps\e3l4\Bunker3.scr:555`
(ships in the mod pk3 -- main session rebuilds the pk3).
