# e3l4 cold-load SECOND overrun (0xc0000409) — investigation (2026-06-24)

Follow-up to `fix_e3l4_crash_compile.md` (BUG 1 = ParseMesh guard). e3l4 still
crashes with the same 0xc0000409 (STATUS_STACK_BUFFER_OVERRUN) signature AFTER
the ParseMesh guard shipped. This documents what the newest minidump and the
running binary actually prove, what was ruled out, and what the main session
must do next. **No engine source was changed in this pass** — see "Why no fix
landed yet" below; an unverified guard would just be a second guess like the
ParseMesh one.

---

## CONFIRMED facts (hard evidence)

### 1. Same GS-overrun signature, and it SURVIVED the ParseMesh fix
All nine recent openmohaa crash dumps fault at the identical address:
`ucrtbase.dll +0xa527e` = `__report_gsfailure` (the /GS security-cookie
handler), exception `0xc0000409`. (One outlier, dump 904 @ 20:07, is a
different code 0xc00000ff — unrelated true stack-overflow.)

The newest dump is **`%LOCALAPPDATA%\CrashDumps\openmohaa.exe.4072.dmp`**
(pid 4072 = 0xFE8, Jun 24 01:44). Its faulting thread id = 31724.

Binary-level proof the ParseMesh fix is live but did NOT stop the crash:
| dump | time | openmohaa.exe PE timestamp |
|------|------|----------------------------|
| 15776 (prior agent's) | 00:57 | `0x6a3b45de` |
| **4072 (newest)** | **01:44** | **`0x6a3b7617`** |

The on-disk running exe `G:\GOG\...\openmohaa.exe` has PE ts `0x6a3b7617`
(matches dump 4072 exactly: same timestamp AND SizeOfImage 0x2e53000) and
**contains the string `"ParseMesh: bad patch size (%i x %i)..."`** — i.e. the
ParseMesh guard is compiled into the build that crashed. So the second vector is
real and distinct, exactly as suspected.

### 2. ParseMesh guard NEVER fires for e3l4 (your ALSO question)
`"ParseMesh: bad patch size"` appears in **zero** qconsole logs
(`%APPDATA%\openmohaa\{main,maintt,mainta}\qconsole.log` and project tree).
Combined with (1), this confirms e3l4's BSP patch dims are within bounds and the
ParseMesh path is **not** the remaining crash. The extracted retail
`e3l4.bsp` ('EALA' v21) parses with max patch 9x11 — clean, as the prior note
said. The ParseMesh patch is correct and a no-op for e3l4; leave it in.

### 3. The crash is in the client MAP-LOAD / gamestate-parse + cgame-init phase
Static analysis of the running exe's `.pdata` (UNWIND_INFO) plus
string-reference anchoring of stack-resident return addresses places the
activity in the client load path. Unambiguously identified frames (resolved by
the literal C-strings each function references in the running binary):

- **`CL_ParseGamestate`** — refs `"MAX_GAMESTATE_CHARS exceeded"`,
  `"configstring > MAX_CONFIGSTRINGS"`, `"Baseline number out of range: %i"`,
  `"CL_ParseGamestate: bad command byte %i"` (= `code/client/cl_parse.cpp:534`).
- **`CL_ParseServerMessage` / `CL_ParseCommandString`** — refs
  `"Client command overflow"`, `"donedl"`, `"CL_ParseServerMessage: read past
  end of server message"`.
- **`CL_InitCGame`** — refs `"maps/%s.bsp"`, `"maps/%s_sml.bsp"`,
  `"CL_InitCGame: %5.2f seconds\n"` (= `code/client/cl_cgame.cpp`).

This matches the reported symptom (crash during ALIAS/SOUND loading, ~25 s into
load, right after the `coop_para_*` "DUPLICATE ALIASES" lines): on map load the
server sends the gamestate (all configstrings, including the ubersound/cache
alias set), the client parses it (`CL_ParseGamestate`) and starts cgame
(`CL_InitCGame`), which replays the alias/cache commands.

---

## Why no engine fix landed in this pass (the blocker)

**The crashing build cannot be symbolicated.** The exe that crashed
(`0x6a3b7617`, the Release config) was linked WITHOUT a CodeView/PDB record (the
dump's openmohaa module has no RSDS debug directory entry), and the ONLY PDB on
disk — `openmohaa-hzm\.cmake\RelWithDebInfo\openmohaa.pdb` — is **stale**: it was
built Jun 23 18:47, predates the ParseMesh fix (its exe does NOT contain the
`"ParseMesh: bad patch size"` string), and its function layout has diverged from
the running build. Resolving the dump's stack RVAs against it yields garbage
(e.g. it maps real renderer/console addresses onto unrelated jpeg/zlib symbols).
No `cdb.exe`/WinDbg is installed on this machine to do an authoritative
PDB-driven `!analyze`/unwind either.

Because of that, a flat stack scan conflates frames from multiple threads/stale
slots. Concretely: the one large-frame function I could fully decode
(`exe+0x117f0`, a 5472-byte `/GS` frame that looked like the victim) turned out,
after resolving its imported calls, to be **`Sys_ConsoleInput`** — it calls
`GetNumberOfConsoleInputEvents` + `ReadConsoleInputA` (the dedicated/console
input poller). That is NOT on the crash path; it is a coincidental stack-resident
frame. This is exactly the trap the prior ParseMesh guess fell into. I will not
ship a third guessed guard without the means to confirm which buffer overflows.

---

## Candidates audited and CLEARED (so the main session can skip them)

- `code/qcommon/alias.c` — both `convalias[MAX_ALIASLIST_NAME_LENGTH]` sites are
  already length-guarded (prior fix); `foundlist[256]` is `ARRAY_LEN`-guarded;
  `Alias_ListAdd` uses bounded `strncpy`; subtitle uses heap `Z_TagMalloc`. The
  `coop_para_*` alias names are short. **Not the overrun.** The "DUPLICATE
  ALIASES" line is benign `Com_DPrintf` (each `coop_para_*` has ~6 weighted
  entries; dup-detect fires for entries 2..n — normal).
- `code/client/cl_parse.cpp::CL_SystemInfoChanged` — `key[BIG_INFO_KEY]` /
  `value[BIG_INFO_VALUE]` are both 8192 and `Info_NextPair` cannot exceed the
  source systeminfo string (itself ≤ BIG_INFO_STRING 8192). Standard ioq3, safe.
- `code/qcommon/msg.cpp` `MSG_ReadScrambledString/BigString/ReadString` — all use
  `static` buffers with `l < sizeof-1` bound; static buffers don't trip /GS.
- `code/renderergl1/tr_curve.c::R_SubdividePatchToGrid` and the terrain loaders —
  `ctrl[65][65]`/`errorTable[2][65]` are the standard guarded ioq3 code;
  `r_subdivisions` is clamped [2,24]; terrain uses heap. Not it.

## Candidates NOT cleared — latent unbounded `strcat`, but NOT the e3l4 trigger
These build an alias parameter string with **unbounded `strcat` in a loop** into
a fixed stack buffer. They are genuine defects worth hardening, but the longest
real `coop_para`/ubersound/uberdialog line in the mod is ~724 chars (and the long
subtitle lines are commented out), well under the buffer size — so they do not
explain THIS crash:
- `code/cgame/cg_commands.cpp:4291` `ClientGameCommandManager::AliasCache` —
  `char parmbuffer[2048]` (client-side, runs during cgame init).
- `code/cgame/cg_commands.cpp:4344` `ClientGameCommandManager::Alias` — same.
- `code/fgame/scriptmaster.cpp:446` `RegisterAliasAndCache` —
  `char parameters[MAX_STRING_CHARS]` (2048).
- `code/fgame/scriptmaster.cpp:507` `RegisterAlias` — same.
(If hardened: bound each with the remaining space, e.g. `Q_strcat(parmbuffer,
sizeof(parmbuffer), s)` instead of `strcat`. Worth doing defensively but will
not fix e3l4 by itself.)

---

## NEXT STEP for the main session (the actual unblock)

To find the real buffer, the crashing build must be debuggable. Do ONE of:

1. **Build with matching symbols and reproduce.** Rebuild openmohaa from the
   CURRENT source (the tree that has the ParseMesh fix) as **RelWithDebInfo** (or
   add `/Zi` + `/DEBUG` to the Release config so a matching PDB is emitted), copy
   that exe to the game dir, and re-run the e3l4 cold-load. Then either:
   - read the new minidump with a PDB that actually matches, or
   - run under WinDbg/cdb (`cdb -z <dump> -y <symdir> -i <exedir>; !analyze -v; kP`).
   With a matching PDB the faulting frame + the exact `char buf[N]` will resolve
   directly, the same way BUG 1's ParseMesh root-cause did.

2. **Cheap interim bisect (no symbols needed).** Add an `iprintln`/`Com_Printf`
   breadcrumb right before and after `CL_InitCGame` and around the
   ubersound/cache replay (`ClientGameCommandManager::AliasCache`/`Alias` and
   `CacheResource`) so the qconsole tail pinpoints which command/alias is being
   processed at the instant of the crash. The last breadcrumb before the dump
   names the offending content and the buffer.

Once the faulting function + buffer are confirmed, apply the established
guard+named-constant pattern (like the ParseMesh and convalias guards) at that
exact `file:line`, never silently truncating needed content.

---

## Artifacts
- Newest dump: `C:\Users\curry\AppData\Local\CrashDumps\openmohaa.exe.4072.dmp`
  (pid 4072/0xFE8, faulting tid 31724, exc 0xc0000409 @ ucrtbase+0xa527e).
- Stale/mismatched PDB (do NOT trust for this build):
  `C:\mohaa-coop-dev\openmohaa-hzm\.cmake\RelWithDebInfo\openmohaa.pdb`.
- Running exe: `G:\GOG\Medal of Honor - Allied Assault War Chest\openmohaa.exe`
  (PE ts 0x6a3b7617) — confirmed to contain the ParseMesh guard string.
