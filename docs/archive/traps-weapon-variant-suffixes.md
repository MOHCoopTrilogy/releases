# Weapon variant suffixes - every consumer must strip them

Pruned out of `TRAPS.md` on 2026-09-08 for space; the rule and the pointer stay there.

A variant exists twice under two different spellings, and an exact-name key misses almost the whole set
in both. **TIK FILENAME `<base>_<finish>`** (`G43_dhg43fleck`): 481 weapon TIKs ship and only ~41 are
base guns, so an exact key covers ~8% - dead on 428 while working on the handful you test with. **Try
the full name, then drop trailing `_segments` one at a time; never cut at the FIRST underscore**, since
real base names contain one (`m1_garand`, `svt_rifle`). **DISPLAY STRING `"<Base Gun> (<Finish>)"`**:
whole-string comparison of `weapon->item_name` mismatches all 247 variants and falls through to the
default. `CoopStripSkinSuffix` splits on `" ("` - a different convention for a different string, so
neither substitutes for the other. FOUR consumers, one missed for three days: `CG_GetVMAnimPrefixIndex`
and `CG_FindAdsTune` (`cg_modelanim.c`), and `Player::CondWeaponActive` (`player_conditionals.cpp`)
inline. The missed one read as the wrong MAGAZINE during reload - the clip is not part of the gun, it is
an `Animate` spawned by an `attachmodel` frame command in the THIRD-PERSON torso anim, picked by
`IS_WEAPON_ACTIVE`. **Any new consumer tries the exact match first, then the stripped base name.**
(bug-1982)
