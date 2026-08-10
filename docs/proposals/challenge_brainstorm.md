# Challenge brainstorm — from how the campaign plays

**2026-08-08. This is ideation, not a verified list.** The two companion documents handle feasibility:
`objective_challenges.md` (script hooks) and `coop_native_challenges.md` (our own systems). This one
is deliberately upstream of that — ideas that come from what the campaign *feels* like to play, which
is where good challenges come from in the first place. Filter later.

Grounded in how the games actually read: Omaha as dread and attrition, the disguise missions as
held breath, Sniper Town as a corridor of fear, Bastogne as a siege, and Spearhead's finale handing
you the levers of a tank.

---

## 1. Play against the mission's design intent

The strongest challenges invert what a level wants from you. MOHAA levels have very clear intentions,
which makes them easy to subvert deliberately.

| Idea | Why it works |
|---|---|
| **Twenty Yards** — cross Omaha to the shingle in under 90 seconds | The level is built to make you crawl for ten minutes. Sprinting it is heresy, and terrifying |
| **No Cover Given** — reach the seawall without ever touching a hedgehog or crater | Removes the one mercy the level offers |
| **Eyes Open** — clear Sniper Town without ever using the scope | The level is a scope tutorial. Doing it iron-sighted is a real skill test |
| **Blown Cover** — deliberately break the disguise on entry and fight the U-boat pens loud | The mission is written for held breath; this is the other movie |
| **Peacetime** — finish a disguise mission without firing once | And the mirror image of the above |
| **The Long Way** — complete the bocage house defence without using the mounted MG | Removes the intended answer |

## 2. Challenges made of the campaign's own cruelty

MOHAA repeatedly asks you to do something awful. Reward doing it *well* rather than merely surviving.

| Idea | Why it works |
|---|---|
| **Sent Back** — retrieve the bangalores without being wounded | The game orders you back into the killing zone. Doing it untouched is the flex |
| **First Through the Gap** — be the first man through the MG gauntlet | Every scripted soldier ahead of you dies there. Beat them to it |
| **They Made It** — reach the trench with every Ranger who started the crossing alive | Fights the level's attrition premise directly |
| **Not One Yard Back** — hold Bastogne without a single breach | The siege is designed to leak |
| **Ten Miles From Brest** — finish Sniper Town having never been hit by a sniper | The level's whole identity |

## 3. Doctrine runs — fight like the man you're playing

A ruleset for the whole mission, not a single moment. These are the ones players invent for
themselves anyway, which is a good sign.

| Idea | Why it works |
|---|---|
| **Issued Kit Only** — complete a mission using only weapons your side actually fielded | No captured MP40s. Suddenly the Garand ping matters |
| **Quartermaster's Nightmare** — finish a mission having picked up no ammo | Forces trigger discipline for an hour |
| **Rifleman** — bolt-action only, whole mission | Slow, deliberate, period-correct |
| **Battlefield Pickup** — the inverse: German weapons only, from the moment you find one | Reads as scavenging your way through |
| **The Sergeant's Way** — no grenades, no explosives, no mounted guns | Everything the game gives you to make it easy, refused |

## 4. Escort and squad — the game's weakest point, turned into the goal

MOHAA's NPCs die constantly and the campaign barely notices. Making that the scoreboard turns a flaw
into content — and it is the one place the coop mod's new ally-DBNO system pays off directly.

| Idea | Why it works |
|---|---|
| **Whole Section Home** — finish a mission with every allied NPC alive who was alive when you arrived | Almost never happens naturally |
| **Nobody Bled Out** — every ally who went down was picked back up | Directly rewards the system built today |
| **Escort of the Damned** — bring the tank crew through Sniper Town untouched | The crew are the reason the level exists |
| **Field Hospital** — revive an ally while under fire from an emplacement | Rewards doing it at the worst possible moment |
| **Last Man Carries** — finish a mission where every ally was downed at least once and none died | A near-run thing, made legible |

## 5. Coop theatre — things only four players can stage

The mod is coop; the campaign was not. That gap is a creative opportunity, not a problem.

| Idea | Why it works |
|---|---|
| **Four Abreast** — all four players reach the Omaha shingle alive | The landing, done as a squad |
| **Crew Served** — one player drives the tank, another mans the turret, and you kill together | Spearhead's finale hands you levers; this makes it a two-man job |
| **Box Formation** — each player holds a different approach on a holdout wave | Turns a defence into an assignment |
| **Simultaneous Salvation** — two revives within ten seconds of each other | Coordination you can feel |
| **One Man Left** — win a wave with three players down and one still fighting | The story everyone retells afterwards |
| **Nobody Walks Alone** — every player revives someone, in the same mission | Everyone participates or it doesn't count |

## 6. Reward noticing things

The campaign is full of authored detail nobody is asked to look at. Challenges are permission to
look.

| Idea | Why it works |
|---|---|
| **Bedside Manner** — pass every medic tending wounded on Omaha without breaking stride | They are scripted set dressing nobody registers |
| **Needle Drop** — find the gramophone playing the original Medal of Honor's German dialogue | A real easter egg, in the campaign, uncredited |
| **Roll Call** — finish a mission having met every named NPC in it | Turns walk-past characters into a collection |
| **Tourist** — visit the hidden Farm House level | It exists and almost nobody has seen it |
| **The Devs Argued About This** — reach a spot the level clearly did not intend you to reach | The mod already has this voice (`BreakTheGame.SCR`) |

## 7. Whole-campaign runs

Big, slow, and the ones people actually chase.

| Idea | Why it works |
|---|---|
| **The Longest Day** — complete every beach, siege and holdout across the trilogy | Ties AA, Spearhead and Breakthrough into one thread |
| **Three Uniforms** — finish a mission in each campaign wearing that theatre's correct kit | Uses the armory as roleplay |
| **No Angel on My Shoulder** — a full mission with no health pack and no revive | Clean, brutal, universally understood |
| **Unbroken Line** — every defensive mission in the trilogy without a single breach | Bastogne, the bridge, the bocage house, Anzio |
| **The Whole War** — every campaign, in order, in one session | The endurance badge |

---

## Notes on turning these into real challenges

**Which of these are cheap:** anything counting allies, revives, players, weapons, time or damage —
the mod already tracks all of it, or owns the code that would.

**Which are expensive:** anything needing "was seen", "which weapon was picked up where", or a route
("without touching a crater"). Those need new tracking, and some cannot be measured at all.

**Which are impossible, and why that matters:** anything asking the player to change a scripted
outcome. The m1l1 checkpoint always goes loud. The m5l3 plunger is destroyed by the tank on script.
An idea in section 1 or 2 that happens to land on a cutscene is dead no matter how good it sounds —
check before building, not after.

**The best ideas above are section 4 and 5**, because the coop mod already owns that code, the
campaign gives them dramatic weight, and no other MOHAA install could offer them.
