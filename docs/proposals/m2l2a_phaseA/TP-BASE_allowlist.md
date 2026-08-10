# TP-BASE - m2l2a baseline Script Error allowlist

Captured **2026-08-10**, before any Phase A edit, from `G:\mohaa-gl2\home\maintt\qconsole.log`
(the live launch profile's log; `qconsole.log` truncates per boot, so this file is the archive).

## Result: the baseline is EMPTY - zero `Script Error` lines.

Whole log scanned: 11,087 lines, 1 m2l2a load, **0 `Script Error` occurrences**.

### Why the empty result is trustworthy (not a silenced log)

`Script Error` printing is developer-gated, so an empty set is only meaningful with evidence that
gated output was flowing:

| Check | Evidence |
|---|---|
| `developer` on | `hzm-mohaa-coop-mod/autoexec.cfg:36` `set developer 1` (the `seta developer 0` at `:31` is the archived seed; the later `set` wins for the session) |
| script `println` reaching the log | 394 `^~^~^` marker lines in the run |
| the map genuinely ran | `SOUNDTRACK: Loading music/m2l2a.mus`, blueprint registration, STEALTHWATCH census, AGGRO BLOCKED traffic |

`-#-#-` thread-trace lines are absent, which is expected: those are gated on the per-file
`level.cMTE_*` variables, none of which the test recipe sets. Their absence is not evidence of a
silenced log.

## Scope caveat - read this before citing the allowlist

The captured run is **901 lines from map load**: spawn, the locker room, the descent, the papers
checker and the Naxos wing. It is **not** a full playthrough. Specifically NOT exercised:

- the papers1 -> papers2 swap and `sentry2dude` (the map's only disguise-level-2 check)
- the endlevel trigger and the transition to m2l2b
- any alarm cycle (`level.alarm` never reached 1 in this run)
- any player death, DBNO, spectate or reconnect

Therefore the correct criterion for later stages is:

> no `Script Error` outside this recorded set **for the portion of the map the stage covers**,

and a stage that reaches unexercised territory (papers2, alarm, endlevel) must **extend** this
allowlist with whatever it finds there on unmodified code before treating those lines as new
breakage. bug-1632 (blueprint pickup) is a known live emitter elsewhere in the tree and may appear
once a stage covers it.

## Why the criterion is "outside the recorded set", never "no new errors"

A `Script Error` **skips the offending statement and lets the thread continue**
(`code/script/scriptvm.cpp:1881-1883`). Errors therefore accumulate silently across a session
instead of announcing themselves, and a plain "no new Script Error" test would either pass
vacuously or fail on pre-existing noise.

## Reproduce

```bash
python - <<'EOF'
import re, collections
d = open(r"G:\mohaa-gl2\home\maintt\qconsole.log", 'rb').read().decode('latin-1', 'replace')
errs = collections.Counter()
for l in d.split('\n'):
    if 'Script Error' in l:
        errs[re.sub(r'^\[[^\]]*\]\s*', '', l).strip()] += 1
for k, v in errs.most_common():
    print(v, k)
EOF
```
