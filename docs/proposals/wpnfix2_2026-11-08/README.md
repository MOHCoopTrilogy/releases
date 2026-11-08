# v1.10.64 wpnfix2: drum Thompsons under the Thompson Drum, one Beretta M38A (2026-11-08)

Mod branch `wpnfix2` (off hotfix-1.10.53 4c95b3fd). No engine change. The wpnfix pak changes: build it into the base checkout at
integration (`python docs/tools/gen_wpnfix_pak.py build`, 95 members, sha256 a7d468cd...).

## 1. Thompson Drum (Armory 25)

**Which variants are drum-fed** (`media/thompson_meshes_magazines.jpg`, every variant's skd drawn side + top): only the
**1928 Tommy** (`thompsonsmg_tommy1928d`, `coop_tommy1928d/ThompsonSMG.skd`, its own drum reload). The **M1928
(`tommy28`) carries a 30-round stick** - narrow from the top like the M1 - so it stays on the M1's ladder (open question:
move it anyway as "an M1928"?). 27A1, M1A1, Hobbs, Guanshire and both Leon skins are stick guns on the M1 mesh.

* the 1928 Tommy is the Drum's variant 8; the M1's fid 9 is **reserved** (`wire_mv2.py` retired entry, later fids and their
  challenge ids do not move). Its unlock stays `wpn_thompson_mv9` (250 Thompson kills, same SR row): `variant_challenges.py`
  MOVED. Its tik (wpnfix pak) now holds **50** rounds - it was a drum gun with the M1's 30.
* the Drum gets the seven finishes through `gen_skins.py add thompson50` (new mode: derives them from the load-order WINNER -
  the stress pak's thompson50.tik - ranks unique against every coop pak, splices only this gun's blocks into coop_skins.shader,
  writes the loadoutskins rows, bakes, and ships tiks + bakes in the wpnfix pak because mod-tree jpgs are git-ignored).
  The Drum's kills are Thompson kills (wid `thompson`), so **its finishes are the Thompson's finish ladder**: anyone with a
  Thompson finish has the same Drum finish.
* an archived Thompson + variant-9 pick lands on the Drum + 1928 Tommy and the client archive is rewritten
  (`loadout_finish` via `coop_skinMvMovedId/Fid`, `loadout_migArchive`).

## 2. Beretta M38A (one gun)

**Correction to the brief:** `moschetto.tik` is not the original MOHAA model. It ships in `zzzzz_xw_weapons.pk3` (Soares93,
Extra WW2 Weapons pack); `it_w_moschetto.tik` is the stock Breakthrough model (pak1). The structure asked for holds:
33 (it_w_moschetto, finishes) is the gun, renamed **BERETTA M38A** (card BERETTA 38; the history text names the Moschetto
Automatico Beretta 1938A); 34 is retired (slot reserved) and moschetto.tik is 33's variant 8, labelled **BERETTA M38A (SOARES93)**.

* gate: the rank-15 token gun 34 was unlocked by (`coop_skinMvTok`, `variant_challenges.py` TOKEN; no new chal_def, so the
  Service Record is unchanged at 447 rows) and no mastery rule, which 34 never had. Rank 14 still unlocks the gun, so
  everyone who had either one keeps it.
* an archived pick of 34 lands on 33 + that variant (`loadout_setBody` -> `loadout_migArchive`; the join's finish replay
  then applies it once).

## Verified (private client, DISPLAY2, coop m2l1, 0 Script Errors every run)

| run | result |
|---|---|
| viewer | Drum 1/9 standard, 2-8 finishes, 9/9 1928 Tommy; M38A 1/9, 9/9 Soares93 model (unlock "Reach rank 15") |
| Armory SMG tab | one BERETTA M38A tile; Drum inspect with MODEL; variant chain pages 25 / 33 |
| pick 25 + gold | THOMPSON DRUM equipped, GOLD applied, 50 + 50 shots per drum, reload |
| pick 33 | BERETTA M38A equipped, 40 + 40 shots, reload |
| archived 24 + f9 | `migrate slot 1 -> 25 fid 8`, 1928 Tommy equipped, 50 + 50 shots; archive now 25 / ,f18 |
| archived 34 | `migrate slot 1 -> 33 fid 8`, Soares93 M38A equipped, fires; archive now 33 / ,f18 |

Gates: gen_loadout check EXACT, gen_lktab EXACT, gen_weapon_viewer 0 stale, gen_wpnfix_pak OK, check_mp_isolation 22/0,
tik-surfaces clean, check_anim_aliases OK. Testing needed a game.dll with `COOP_COVER_THROW` (the hotfix tip's legs state file):
built from rel-1.10.38-engine 6977f069 in the wpnfix-eng tree (detached, branch restored).

Found on the way (fixed): `lktab3` never got the FG 42 irons (79) or the Lewis (81) padlock recompute (gen_lktab was not run
for either); the Lewis' deny text read "Not currently obtainable" and it had no progress bar (armory_unlocks / gen_armory read
only challenges.scr, not the variant challenge that unlocks it).
