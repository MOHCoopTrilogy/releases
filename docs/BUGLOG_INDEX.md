# Buglog Mining - Index

What was mined: `.wolf/buglog.json`, the only project record that still works, because it is
structured and has a lookup key. **639 entries** at snapshot time (2026-07-29 01:25), spanning
2026-06-26 to 2026-07-29.

| File | What it is | When to open it |
|---|---|---|
| **`recurring_traps.md`** | **12 trap families** - defects that recurred under different bug ids. The single highest-value output. | **Before writing any code.** Especially T1 (parse killers), T3 (build/deploy), T7 (engine limits). |
| **`open_defects.md`** | OPEN / PLANNED / REVERTED registers + **7 record-vs-code discrepancies** | Before claiming something is fixed, and whenever the record and the tree disagree. |
| **`fix_ledger.md`** | Chronological one-line ledger of all 639 entries (`id / date / file / symptom / fix`) | Lookup by date, file, or symptom. Regenerate rather than hand-edit. |

## How to read a buglog entry safely

1. **Search for the id in later entries before trusting it.** There is no `superseded_by` field.
   bug-1173 reads as an applied fix; bug-1184 reverts it. Reading bug-1173 alone is what caused the
   error this audit was commissioned to correct.
2. **Then check the code.** The tree is the authority. Two of the three claims spot-checked this
   session had drifted (see `open_defects.md` D-2, D-3).
3. **"Fixed" rarely means "playtested".** Only 17 entries carry a machine-readable status field
   (`fix_verified: false`, June only). Everything after that is prose. Look for the literal words
   *verified* / *rcon-verified* / *user confirmed* in the `fix` text; their absence means unverified.
4. **Gaps in the id sequence are not missing entries.** 632 of `bug-1..bug-1222` were never assigned.
   All 8 `.bak` files were diffed and contain zero entries absent from the current file.

## Structural defects in the format itself

The buglog works, but four things are missing and every one of them has cost time:

- no `status` field (SHIPPED / VERIFIED / REVERTED / OPEN)
- no `superseded_by` / `supersedes` link
- no `verified_by` (log line, rcon transcript, screenshot, playtest date)
- no `code_anchor` (`file:line` or commit) - `file` is free text and often lists 8 paths

The file is also **live and concurrently written** (it grew by 5 entries during this audit).
Append, never rewrite - `bug-buglog-dataloss` is already in the log.

## Regenerating the ledger

```
python - <<'EOF'
# see the generator inlined at the top of fix_ledger.md's provenance note;
# sorts by (timestamp, id), truncates error_message to 150 and fix to 170 chars
EOF
```

Read-only audit. Nothing outside `docs/` was created or modified.
