# docs/tools — the documentation-maintenance system

*This file is authored. Everything it produces is not.*

## The problem this exists to solve

This project accumulated 1,820 `.md` files and no working authority. Three of OpenWolf's four
memory artifacts had rotted, and in each case **the rot was the direct consequence of the
instruction that governed them**:

| Artifact | Instruction | Result |
|---|---|---|
| `.wolf/anatomy.md` | "a 2-3 line description for every file in the project", but the only update rules were *reactive* — add a file when you happen to read it | Named ~2% of the tree while promising completeness, so every session trusted it and concluded missing files did not exist. Total coverage was **structurally impossible under its own rules**. |
| `.wolf/memory.md` | append per "significant action", with no ceiling, rotation or pruning rule anywhere | 1.29 MB. That is what compliance produces. |
| `.wolf/cerebrum.md` | "the bar is LOW, if in doubt add it" — while a second rule said "read it before generating code" | 525 KB / ~130k tokens. The filling rule made the using rule impossible. |
| `.wolf/buglog.json` | **the same** "the threshold is LOW" language | Works fine at 645 entries. |

The buglog is the control. Same low bar, opposite outcome — because it is **keyed, schema'd
and one entry per event**. Low bar + schema = a database. Low bar + free prose = sludge.

So this system is built on two rules:

1. **Anything extractable from code, git or `buglog.json` is generated, never hand-maintained.**
   A regenerated doc cannot drift.
2. **What genuinely needs judgement stays authored — under a size budget with a merge-and-prune
   rule**, because accumulation is the failure mode that killed `cerebrum.md`.

## What is here

| File | What |
|---|---|
| `docgen.py` | The generator. No third-party dependencies. |
| `docs.ps1` / `docs.cmd` | Thin wrappers so you can type `docs check`. |

Output goes to `docs/generated/`, visibly separate from the authored files and carrying a
DO-NOT-EDIT banner. The authored files (`SOURCE_OF_TRUTH.md`, `TRAPS.md`, `DECISIONS.md`,
`OPEN.md`, `FEATURES.md`, `ENGINE.md`, `HISTORY.md`) are never touched by this tool.

## Running it

```powershell
python docs\tools\docgen.py build          # regenerate; no-op if inputs unchanged
python docs\tools\docgen.py build --force  # regenerate unconditionally
python docs\tools\docgen.py check          # exit 1 if docs/generated is stale
python docs\tools\docgen.py status         # fingerprint + staleness, writes nothing

.\docs\tools\docs.ps1 check                # same thing, shorter
```

**You rarely need to.** `.wolf/hooks/stop.js` runs `build` at the end of any session that
touched the project.

## How it stays honest

**Determinism.** Output is a pure function of repository state: no wall-clock timestamps
anywhere in a generated file, sorted iteration, LF newlines, UTF-8 without BOM. Without this,
`check` would fail on every run and the guarantee would be worthless. The only wall-clock
lives in `docs/generated/.docgen-state.json`, which is excluded from `check` by construction.

**No self-reference.** `docs/generated/` is excluded from the sweep, from the census and from
every git dirty count. Its own output must not be one of its inputs, or generation never
reaches a fixed point. `.claude/` and `.wolf/` are skipped for the same reason — they mutate
every turn, and counting them would make the docs read as stale for reasons that have nothing
to do with documentation. (`.wolf/buglog.json` is still read directly and fingerprinted by its
own size and mtime.)

**Fingerprint granularity matches output granularity.** Project files are fingerprinted at
path+size; reference dumps appear in the census only as (count, bytes), so that is exactly
what they are fingerprinted at. If the fingerprint were coarser than the output, the fast path
would say "up to date" while `check` disagreed.

**The fast path also verifies the output.** An unchanged fingerprint is not sufficient: someone
can edit a generated file without touching any input. `build` re-hashes the files against
`manifest.json` and rebuilds if they do not match, so a hand-edit is repaired rather than
preserved forever.

**Write-if-different.** Files whose content did not change are not rewritten, so mtimes stay
stable and the fingerprint does not churn.

**Omissions are reported, not hidden.** Engine cvars registered with a computed name, and
script cvars whose name is built by concatenation, are counted and listed as such rather than
guessed at or silently dropped. If those counts grow, something is escaping the inventory.

## Extending it

Add a `gen_*()` function returning a string, register it in `build_outputs()`, and it is
automatically covered by `check`, by the manifest and by the hook. Two constraints: **no wall
clock in the output**, and **sort every iteration**.

If you catch yourself hand-writing an inventory, that is the signal to extend this file
instead. That is the whole thesis.
