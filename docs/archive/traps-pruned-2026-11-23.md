# TRAPS pruned 2026-11-23 (verbatim, from T14 'THE TOOL LIED')

Moved to keep docs/TRAPS.md under its ceiling.

*(e)* **The preprocessor dropped it**: the menu-theme picker passed build, audit and deploy from
`snd_main_new.cpp`, never compiled here (bug-2572). **After an engine
change, `grep -a -c` one of its string literals in the built binary.** *(g)* **GLSL lint + glslang never
see C**: staged `tr_hzm_wet.c` used file-static `s_worldData` and passed both (bug-3150) -
under a no-build rule, `cl /Zs` the touched files.
*(f)* **PowerShell 5.1 re-splits embedded double quotes to a native exe** (rcon `stufftext "..."` split): use python.

*(d)* **`check_map_compiles.py` is flaky against a LIVE server and only proves the map INITS** (bug-2530).
