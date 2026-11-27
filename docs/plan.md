# Plan

This is where we keep decisions and the stuff we still need to figure out, so nothing gets lost.
Tick things off when they're handled, add new ones when they come up.

## The goal

- Harder than most packs, with a completion time somewhere around gtnh or nomifactory.
- A modern version people can actually play.
- Runs well.
- A pipeline that catches what we'd miss, like recipe overlap, quests you can't finish, dupes, etc.
- Easy to version and test between the two of us, one on fedora and one on windows.

## Decisions

- **2026-11-23, minecraft 1.21.1 on neoforge, java 21.**
  It has the freshest versions of most big tech mods (create, mekanism, ae2, kubejs) and it's where neoforge and most mod authors are putting their time.
  The catch is gregtech modern is only pre-release there, if we end up using it.
- **2026-11-23, the pack lives on github only.**
  No curseforge or modrinth listing.
  You import an instance zip into prism, and every launch it syncs to `pack.toml` on github with packwiz.
  The mods still download from wherever their authors host them, so we never rehost anyone's jars.
- **2026-11-24, the overworld is lost cities.**
  Lost cities generates in the overworld of every new world, set through `dimensionsWithProfiles` in `config/lostcities/common.toml`.
  Loading a lost cities world pops vanilla's "experimental settings" warning every time, hide experimental warning removes it.
- **2026-11-24, it's an ocean world.**
  Everything is built by `tools/build_worldgen.py`, which writes the `pack-pack-worldgen` datapack (global packs loads it into every new world) and two lost cities profiles.
  - Lost worlds' spheres generator puts a sea floor around y=-15 with water up to y=160 everywhere outside lost cities' glass domes, and normal ground only inside them.
  - All biomes are ocean variants picked by temperature, deep ones where vanilla has ocean basins.
  - Terrain is flattened to a floor at y=64, which only matters inside domes, so an empty dome is a dry floor and not a hill filling the glass.
  - Cities inside domes are dry, cities between them are drowned, nothing within 500 blocks of spawn, and lost cities' railway tunnels are off since they floated through open water as a grid.
  - You start in a wrecked copper submarine on the sea floor under spawn (`tools/start_sub.py`), with an airlock, a diving suit and the expedition log.
    It's built once when the server starts (a storage flag keeps it from ever overwriting changes) and spawn is set inside it.
    A spare backtank under a hand crank by the bunks is the air supply, about two minutes of cranking for a 15 minute tank.
    The plan is to swap it for a real create sub later.
  - New players default to "bright" brightness and clear water removes the underwater fog, so it's readable without shaders.
- **2026-11-24, ocean structures.**
  Moog's ocean structures, unwrecked ships, YUNG's better ocean monuments and hopo better underwater ruins.
  Within 500 blocks you mostly get the small hopo ruins plus vanilla ocean ruins and a shipwreck, the bigger stuff starts around 850 to 1250 blocks out.
- **2026-11-24, villages in domes.**
  `tools/lc_villages.py` turns vanilla's plains village houses into a lost cities city style, about 1 in 9 dome cities.
  Lost cities picks a city style per world, not per dome, so a village city outside a dome comes out drowned, those have loot and no villagers.
  Each house has a trial spawner that spawns one villager once, and a tick function removes a new villager standing in water, so only dome villages keep villagers.
  `python3 tools/build_worldgen.py --preview-villages` makes every city a village with no spawn radius, for looking at them.
- **2026-11-24, QoL mods most packs ship.**
  Picked from the actual mod lists of the 20 most downloaded 1.21.1 neoforge packs on modrinth (61 to 311 mods each), only stuff that doesn't change gameplay:
  jei, jade, appleskin, mouse tweaks, controlling, FTB Chunks map and minimap (replaced Xaero's, see below), reese's sodium options, better advancements, shulker box tooltip, clumps, badoptimizations, no chat reports, and lootr so loot chests in the cities are per player in multiplayer.
  Left out on purpose since they're design calls: waystones, backpacks, curios, voice chat.
- **2026-11-24, iris with three shader packs to try.**
  Complementary reimagined, photon, and makeup ultra fast for weaker machines, all off by default, you pick one in video settings.
  All three compile with no errors over a lost city.
- **2026-11-25, create deep seas in, iris and the shader packs out.**
  Veil (pulled in by create aeronautics and sable) hooks sodium's water rendering in a way that only matches sodium 0.8.12, anything newer crashes the moment water renders.
  Sodium, sodium extra and reese's are pinned to the july builds, and iris is gone since its only sodium 0.8 build needs 0.8.13.
  Bring iris and the three packs back once veil works with a newer sodium.
  Sable has open issues with c2me and lithium (physics objects springing back) and with servers stalling while saving physics objects, so watch for those.

## Open questions and gaps

**(critical)** means it blocks real work or gets expensive to fix later.
*(verify)* means it's a best guess that hasn't been checked yet.

### What the pack is

- [ ] **(critical) No progression design yet.**
  We need a tier map, which mods show up at which tier, what each tier's challenge is, and what the end goal is.
  Pretty much every check in the pipeline needs this to know what "too early" means.
- [x] **(critical) Pick the backbone.**
  Gregtech's voltage tiers, like gtnh, nomifactory and monifactory (2026-11-27), with create alongside.
  Early power should feel like the ocean, a kelp boiler or gregtech's solar boiler.
  Where we need a machine gregtech doesn't have (like filling backtanks with oxygen), we make our own on gregtech's machine api, from kubejs or our mod.
  Metals come from mob drops and city loot, plus some way of our own to pull elements out of the minerals around you.
  Gregtech's own ore veins still generate where there's stone or tuff under the sea floor, keeping or dropping them is still open.
  Its raw oil sprouts are off, in open water they were oil columns 175 blocks tall, oil comes from its underground fluid veins instead.
  The tier map and the open questions are on the pack-pack canvas board for now.
- [ ] **(critical) Why play this over monifactory, star technology, gregtech odyssey or atm.**
  There's already a bunch of good expert tech packs, so it needs some kind of hook, a theme, a mechanic, a mod mix nobody else has, etc.
- [ ] **(critical) Content vs team size.**
  gtnh's length is a decade of work from a big team.
  With two people we probably want to ship one tier at a time and extend.
- [ ] **Modes.**
  Nomi and moni ship normal and expert modes, moni adds hard mode.
  Every mode multiplies testing and quest work, so decide early if it's one mode or more.
- [ ] **Advancements.**
  Vanilla advancements still fire and point people at vanilla goals.
  Decide if they get disabled, replaced, or kept next to the quest book, and check them like quests if kept.

### Water world

- [x] **Domes are dark between buildings.**
  No daylight gets through the sea, so the patched lost cities puts invisible light blocks three blocks above the ground on a six block grid in every dome, and in control keeps hostile mobs out of domes.
  Inside buildings it's still dark, which is on purpose.
- [ ] **Loot near spawn.**
  Hopo ruins (one right at spawn), vanilla ocean ruins and a shipwreck 35 blocks out all have loot inside the 500 block ring, check those loot tables against the tier plan.
- [ ] **Something has to gate the 500 block swim.**
  The idea is a crafted item you need before you can make it out to the cities.
- [x] **Coral reefs.**
  Hybrid Aquatic removed vanilla coral from warm oceans and kelp and seagrass from deep oceans, expecting its own reef biomes, which are off here.
  Those two removals are overridden, and a warm ocean sample went from 16 live coral blocks to about 30,000.
- [x] **Tunnels meeting domes, and air near them.**
  The tubes were fine, the pass that floods leftover air outside the domes ran after them and filled them with water, so every dome opened into a flooded tube.
  It runs before the tubes now, and the tubes are back on between every pair of neighbouring domes.
  The worldgen check counts air touching water outside every dome, which was 132 per junction before and is under 10 now.
- [x] **Dome edges still need a look.**
  The pools at dome edges were a ring of water down to bedrock around every dome, fixed in 0.21.1 and checked in CI.
  The air box above ocean monuments doesn't reproduce: the pack's Better Ocean Monuments at 800,-496 (seed pack-pack-benchmark) has no air at all in the water around it (2026-11-25).
- [x] **Really tall kelp.**
  A small mod of ours (`tools/tweaks-mod`) makes generated kelp 1 to 75 blocks tall and lets it keep growing until it runs out of water.
  Generation is measured (median 38, longest 76), and planted kelp grew 174 blocks to the surface in the real client.
- [ ] **Lost cities sometimes stalls worldgen.**
  One pre-generation hit a 60 second server tick and the watchdog killed the server, and once the client hung saving the world on quit.
  Two causes are fixed since: the quit hang was xaero's world map (gone), and lost cities growing saplings into chunks that weren't loaded stalled exploring (patched).
  Leave this open until a long soak comes back clean.
- [x] **Worldgen is slow.**
  It was 11 to 22 chunks a second before C2ME, the worldgen check now reports about 60 a second for its test square (2026-11-25, same machine).

### Mods

- [x] **Pick the version.** 1.21.1 neoforge.
- [x] **(critical) Which gregtech line.**
  The 8.0 beta (2026-11-27), the rolling `latest-1.21` snapshot, over 7.0.2 from 2025-07.
  It means less migration later but scripts that break as the api moves.
  The jar lives in `pack/mods`, see `docs/dev.md` for moving to a newer build.
- [ ] **Check every mod we want actually exists on 1.21.1 neoforge.**
  Thermal has no 1.21.1 release, immersive engineering hasn't been updated since mid 2025.
- [ ] **Who owns ore gen.**
  Pick one mod for ores, turn off everyone else's, and make sure every material a recipe or quest needs spawns somewhere you can get to.
- [ ] **Unification.**
  A bunch of mods add their own copper, tin, steel, etc.
  almostunified or kubejs should merge them early, otherwise you get conversion loops and a cluttered recipe viewer.
- [ ] **Curseforge distribution opt-outs.**
  Some curseforge authors block third-party downloads, and packwiz can't fetch those mods.
  Prefer modrinth versions and check any curseforge-only mod before adding it.
  Lost cities is curseforge only and it downloads fine.
- [ ] **Lost cities spawner bug.**
  Lost cities sometimes saves a spawner where the block ended up as air, vanilla throws it away and logs an error the first time that chunk loads.
  It's [LostCities#786](https://github.com/McJty/LostCities/issues/786), still open, so the boot tests list that one error in `tools/gamelog.py` and skip it.
  Take it out of that list once it's fixed upstream.
- [ ] **Recipe viewer.**
  Jei is what most packs ship (60% vs emi's 30% in that sample), but emi's recipe tree is really nice for long processing chains.
  Worth revisiting once the backbone is picked, emi can also show jei plugin recipes.

### Validation pipeline

- [ ] **(critical) A tier file.**
  A machine-readable file saying which tier each item, machine and quest belongs to.
  Without it an agent can find loops and orphans but can't tell a bug from a design choice.
- [ ] **(critical) Recipe data comes from the running game.**
  The idea is a kubejs script that dumps every recipe to json on the headless server.
  Whether that captures modded machine recipes fully (energy, fluids, chanced outputs, catalysts, etc) hasn't been checked, so test it against a few known recipes first.
- [ ] **(critical) Items come from more than recipes.**
  Loot chests, mob drops, worldgen, pumps and infinite fluids, byproducts, villager and wandering trader trades, bartering, fishing, quest rewards.
  Each one can leak late items early, so each needs checking against the tier file.
- [ ] **Dupes need a value model.**
  Finding loops is easy, knowing if a loop makes stuff from nothing needs some value per item and a balance check around each loop.
- [ ] **Not every dupe is a recipe.**
  Create contraptions, ae2, storage mods, nbt items and mod interactions can dupe in ways a recipe graph won't see.
  Keep a list of known exploits and gametests for the ones we can reproduce.
- [ ] **Quest reward farming.**
  Repeatable quests and team shared rewards can hand out infinite items, check rewards against the tier file.
- [ ] **Bypass mechanics.**
  Waystones, chunkloading, trash cans, cobble gens, mob farms, creative-ish items, etc.
  Decide per mechanic if it's allowed and at which tier.
- [ ] **Recipe viewer cleanup.**
  Removed recipes leave items sitting in emi/jei that look like bugs, check for items with no source and hide them.
- [ ] **Save upgrade test.**
  Keep a late game world from the last release, load it after each change, fail on missing blocks and items.
- [ ] **Fast agent loop.**
  A modded server boot takes a while, so run the static checks on dumped data and only redo the dump when mods or scripts change.
- [ ] **Humans sign off on balance.**
  Agents open an issue or PR for balance stuff, they don't change recipes on their own.
- [x] **Basic CI.**
  `check_repo.py` on linux and windows, then a server boot test and a client boot test that joins a world, on every push and PR.

### Performance

- [x] **Performance mods.**
  Client: sodium, sodium extra, immediatelyfast, entityculling, moreculling, dynamic fps. Both sides: modernfix, ferritecore, lithium, spark.
  That's pretty much the set big 1.21.1 neoforge packs like atm10 ship.
  C2ME went in on 2026-11-25 for worldgen speed.
  Skipped for now: scalablelux (still alpha), noisium (abandoned), krypton (no real neoforge build), alltheleaks (curseforge only).
  Later once there's content: fastsuite/fastworkbench/fastfurnace, polymorph, packet fixer, servercore.
- [x] **Modernfix dynamic resources is on.**
  It loads models when they're needed instead of baking all of them at startup.
  At this size it's within noise (10.7s vs 11.1s over 3 launches each), it should matter more once there's thousands of models.
  If a mod shows up with missing textures or a startup crash, this is the first thing to turn off.
  Lithium and modernfix both patch biome temperature, so modernfix's copy is off.
  They also overlap on one chunk method, modernfix just skips it and logs a warning, that one's fine.
- [x] **JVM flags.**
  The server boot test runs aikar's G1 flags since that's what most hosts use.
  The client gets 2-6GB and java 21's default G1, there's no java 21 data showing custom client flags help, so we'll revisit once the pack is big.
- [x] **Budgets for an idle server.**
  The boot test records boot time, tps, tick times and heap on a fixed seed, and since 2026-11-25 fails over budget: boot 60 s, idle TPS 19.5, median tick 10 ms, 95th percentile 25 ms, heap 3 GB (`BUDGETS` in `tools/boot_server.py`, set well above CI's numbers).
  Numbers so far (2026-11-23, fedora, java 21, rtx 5080):
  - server: about 4s to start, median tick 0.5ms, 95th percentile around 4-8ms
  - client with 4 mods: about 9.3s to the main menu
  - client with 21 mods: about 11s to the main menu, 2.1s from menu into a world
- [ ] *(verify)* **Kubejs makes startup slower over time** as recipe edits pile up, track it per release.
- [ ] **Late game load.**
  Big multiblocks, long pipe networks, create contraptions and big ae2 networks are what usually tank tps, so we need a late game benchmark world.
- [ ] **Worldgen.**
  Decide on pregen, world border, and whether distant horizons and shaders are supported.
- [ ] **Low end target.**
  Pick a minimum spec, ship memory defaults that fit it, and test on it.

### Saves and releases

- [ ] **(critical) Update safety policy before anyone plays seriously.**
  Removing a mod deletes its blocks from worlds, changing materials or multiblocks strands machines.
  One option is major means new world, minor adds content safely, patch is fixes only.
- [ ] **Quest ids never change.**
  Regenerating ftb quests ids can reset people's progress.
- [ ] **Know which config folder does what.**
  `defaultconfigs` only gets copied into a world when it's created, so changing it later doesn't reach existing worlds.
- [ ] **Multiplayer join test.**
  The boot test already installs only server side mods on a real dedicated server, still need a real client joining it.
- [ ] **Player support.**
  Crash assistant is in, when the game crashes it shows what went wrong and points people at a new github issue.
  Its log upload metadata to the author's server is turned off.
  Still need issue templates asking for version, logs and crash report.
- [x] **First launch.**
  New players skip the narrator/accessibility prompt and the tutorial popups, and the window opens at 1600x900 instead of 854x480.
  `options.txt` ships with `preserve = true` so it only gets written if you don't already have one, your settings never get overwritten.
- [x] **Releases.**
  release-please writes the changelog from commit messages, merging its PR tags the release, attaches the instance zips and moves the `stable` branch.

### Working between linux and windows

- [x] **Line endings and case.** `.gitattributes` forces lf and `check_repo.py` catches crlf and names that only differ by case.
- [x] **Windows path length.** `check_repo.py` caps paths at 160 characters, `docs/dev.md` covers `core.longpaths`.
- [x] **Hosting.** Public github repo, prism instances read `pack.toml` from raw github.
- [x] **Bootstrap rate limits.** The bootstrap self-updates through github's api, which can 403 and fail the launch, so the instance zip ships the installer jar next to it.
- [ ] *(verify)* **Ftb quests merge conflicts.**
  Ftb quests seems to store one snbt file per chapter, so two people editing one chapter will conflict.
  Split chapters between us and don't run the in-game editor on the same branch at the same time.
- [ ] **Same java on both machines.**
  Let prism manage java 21 on both instead of the system java, fedora's is 25.
- [ ] **Test worlds stay out of git.** Benchmark and save upgrade worlds go in release assets or git lfs.
- [ ] **Instance settings only apply on import.**
  Window size, memory and the pre-launch command live in prism's `instance.cfg`, which comes from the zip when you import it and never syncs after that.
  Mods and configs update every launch, but changing those settings means re-importing, or we find a way to sync them too.
- [ ] **Updates can take ~15 minutes to reach players after a release.**
  Github's raw file cdn keeps a separate cached copy for gzip requests, and packwiz-installer asks for gzip, so after the 0.4.0 release it kept getting the 0.3.0 `pack.toml` for about 15 minutes even though plain requests already got 0.4.0.
  Moving the pack to github pages, which purges its cache on every deploy, should fix it properly.
- [ ] **Shared test server.** Decide who hosts it and how it updates, probably packwiz on the server too.

### Players

- [ ] **(critical) Playtesting beyond us.**
  Whoever builds a pack plays it way faster than everyone else, so we need outside testers and some idea of time per tier.
- [ ] **The first ten hours.**
  Most people decide in the first few hours, so polish early game first and watch for walls where one resource blocks everything.
  Length should come from engineering problems, not grind.
- [ ] **In-game docs.** Quest text, tooltips, ponder or patchouli pages, it's usually more writing than the recipes.
- [ ] **Translations from day one.** All quest and tooltip text in lang files with stable keys, like atm10 does.
- [ ] **Accessibility.** Colorblind safe indicators, readable text, sane keybinds.
- [ ] **Licensing our own stuff.** Pick a license for scripts, quests and configs, keep a credits file, check licenses before borrowing scripts from other packs.

## Notes from research (2026-11-23)

- Monifactory (1.20.1, gregtech modern, kubejs, ftb quests) is the closest thing to what we want.
  It keeps normal/hard/expert as config override folders and boots a gametest server per mode on every PR.
- Nomifactory generates its changelog from commit messages and keeps translations in a separate repo.
- gtnh does its recipes in java inside hundreds of forked mods, way too heavy for two people.
- atm10 keeps quest text in lang files with 15 languages.
- Nothing exists yet for recipe conflicts, dupe loops, unobtainable items or unfinishable quests, we'll have to build it.
- `ftb-snbt-lib` (python) can read and write ftb quests files, spark can do health reports from the console.

## Sources

- Monifactory: https://github.com/Omicron-Industries/Monifactory
- Nomifactory CEu: https://github.com/Nomi-CEu/Nomi-CEu
- GT New Horizons: https://github.com/GTNewHorizons/GT-New-Horizons-Modpack
- All The Mods 10: https://github.com/AllTheMods/ATM-10
- Star Technology: https://github.com/StarT-Dev-Team/Star-Technology
- GregTech Odyssey: https://github.com/GregTech-Odyssey/GregTech-Odyssey
- GregTech CEu Modern releases: https://github.com/GregTechCEu/GregTech-Modern/releases
- packwiz: https://github.com/packwiz/packwiz
- ftb-snbt-lib: https://github.com/peunsu/ftb-snbt-lib
- spark commands: https://spark.lucko.me/docs/Command-Usage
- Curseforge third-party distribution and prism: https://prismlauncher.org/news/ftb-removal

## Audit, 2026-11-24

Three reviewers looked at the pack against real packs, the dev pipeline and the world generation.
Some of what they found is checked, some is their own judgement, so treat the details as leads.

### World direction

The world should feel post-apocalyptic.
Cities are covered by miles of water, only a few small domes survived, and the old flooded cities and roads are overrun by ocean life.
The sea floor needs real elevation, like ridges, trenches and plateaus.

- Lost Worlds answers every height lookup outside a dome with the world minimum, and it has a bug where it multiplies the block position by 16 first.
  Structures that place themselves by height end up buried or floating, and some get an air box cut into the ground.
  Mod structures now get a fixed start height from our datapack, which fixed the ones we checked.
- The ground is sand all the way down to bedrock at the bottom of the world, so there is nothing to mine and nothing to carve into around domes.
- Real elevation needed a change to the Lost Worlds ground function, which a datapack cannot do, so the pack ships a patched Lost Worlds, see `tools/lostworlds/README.md`.
  The floor now has plates, ridges, trenches and seamounts, ranging from about -57 to +50, flat around domes and spawn, and structures and drowned cities follow it.
- Done: the old note about this below is kept for the reasoning.
- Real elevation means changing the Lost Worlds ground function, which a datapack cannot do.
  The reviewer recommends a patched copy of Lost Worlds with a multi-scale ground function that is flat under domes, and a taller vertical budget.
  Replacing the generator with the vanilla one would lose the dry dome interiors, so it is not recommended.
- Overgrown cities and roads are a decoration pass after the city features, plus a higher ruin chance on the flooded profile.

### Pack design gaps

- There is no tier map yet, and everything else depends on it.
- The resource loop has no answer yet: with bedrock under the floor there is no ore, so where do the first metals, wood, fuel and food come from?
  Decide this before picking Create, Create Deep Seas or GregTech.
- The pod needs a survival loop, and the 500 block swim needs a gate.
- FTB Quests is installed but has no chapters.
- Pick one difficulty mode now and make the others config override folders later.
- Worldgen datapack changes do not touch existing worlds, so decide when a release means a new world.

### Xaero's World Map hang (gone)

Xaero's World Map 1.47.0 could deadlock while quitting a world ("Saving worlds") if it was loading map regions at that moment.
It was replaced by FTB Chunks, which also brings land claims for multiplayer.

### World notes, 2026-11-25

- The sky above the sea is vanilla again, only the underwater fog is the deep water colour, and it ends at 150 blocks so it closes before a normal render distance.
- Drowned: three quarters of their natural spawns are refused, which keeps it to about 3 to 6 within 64 blocks of a player instead of 12 to 22.
- Villages: Lost Cities picks the city style per chunk from the nearest city centre, so village houses show up 1 to 3 at a time inside ordinary domes as well as in the occasional full village dome, and drowned villages show up outside. It reads like a few survivors living in a dome, so it is left like that for now.

### Pipeline gaps

- [x] Capture evidence for hangs: the server boot test now takes a thread dump before killing a hung server (boot or shutdown) and CI uploads it.
- [x] A worldgen check in CI: generates four domes and checks shell, air, ground, water under the floor and floating blocks (`tools/check_worldgen.py`). It runs two seeds, the second has warm ocean and reefs. A weekly soak runs it over 25 dome slots for the rare errors.
- [x] Tests and lint for `tools/` (pytest and ruff in the hygiene job).
- A static check of mod metadata and dependencies before booting.
- [x] A scheduled mod update workflow (weekly, checked before the PR opens).
- Performance budgets with baselines.
- Recipe dump, overlap report, progression solvability graph and quest validator, in that order, once the tier map exists.
