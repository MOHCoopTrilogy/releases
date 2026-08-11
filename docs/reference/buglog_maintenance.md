# buglog.json maintenance hazards

Moved out of `docs/TRAPS.md` 2026-08-10 - these are about maintaining the LOG, not about the game
breaking.

- **Ids are not all numeric** — ~25 use slugs (`bug-gl2-ztagmalloc`, `bug-ps-home-var`…). Numeric-only
  tooling silently skips them; `re.fullmatch(r"bug-(\d+)")` before `int()` or it throws.
- **Append, never rewrite.** A post-write hook once rewrote the log wholesale under its own schema,
  and `readJSON` returns a fallback on *any* parse failure, so one transient read failure = total
  loss. 523 entries had to be rebuilt from transcripts.
