# What's New card draft - v1.10.32

Card = `ui/coop_whatsnew.urc` (title + 8 lines, about 45 characters each at verdana-12; the longest shipped line is 49). The version cfg is derived from the title (`gen_version_cfg.py build`), and `publish_release.ps1` refuses to publish unless the title equals the release version.

Title: `UPDATE v1.10.32 - LOBBY + ARMORY + FINALE`
Subtitle (unchanged): `squad bulletin - discord.gg/cVjMYPBFZ`

| line | text |
|---|---|
| f1 | `LOBBY: every mission starts in the lobby` |
| f2 | `ARMORY: new Showroom, every gun fits its card` |
| f3 | `FINALE: stand in the DEFEND zone to win` |
| f4 | `ALARM: snipers on roofs, mortar crews` |
| f5 | `PROMPTS: key icons and one smooth hold ring` |
| f6 | `PAD: menus work with a controller` |
| f7 | `NEW: Mauser C96 model, night searchlights` |
| f8 | `OFFICERS: smoke OR binoculars, not both` |

Applied to the integration mod branch (`integ-1.10.32-mod`) as one commit, so the release only needs the version bump check.
