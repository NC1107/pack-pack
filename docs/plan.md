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

## Open questions and gaps

**(critical)** means it blocks real work or gets expensive to fix later.
*(verify)* means it's a best guess that hasn't been checked yet.

### What the pack is

- [ ] **(critical) No progression design yet.**
  We need a tier map, which mods show up at which tier, what each tier's challenge is, and what the end goal is.
  Pretty much every check in the pipeline needs this to know what "too early" means.
- [ ] **(critical) Pick the backbone.**
  gtnh, nomifactory and monifactory get their length from gregtech's voltage tiers, but we don't have to use gregtech.
  Could also be a create or mekanism chain with heavy kubejs gating, or a few mid-size tech mods stitched together.
  This decides the mod list, ore gen, and how much of the length comes from mods vs our own scripts.
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

### Mods

- [x] **Pick the version.** 1.21.1 neoforge.
- [ ] **(critical, if gregtech) Which gregtech line.**
  7.0.2 is the last tagged 1.21.1 release (2025-07), 8.0.0 is a rolling pre-release on github with a rewritten ui and pipes.
  7.0.2 is stable but means a big migration later, 8.0.0 means less migration but scripts that break as the api moves.
  Since the pack is github only, pinning a github build by hash with packwiz should just work.
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
  `check_repo.py` on linux and windows, then the server boot test, on every push and PR.

### Performance

- [x] **Performance mods.**
  Client: sodium, sodium extra, immediatelyfast, entityculling, moreculling, dynamic fps. Both sides: modernfix, ferritecore, lithium, spark.
  That's pretty much the set big 1.21.1 neoforge packs like atm10 ship.
  Skipped for now: c2me and scalablelux (still alpha), noisium (abandoned), krypton (no real neoforge build), alltheleaks (curseforge only).
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
- [ ] **No budgets yet.**
  The boot test records boot time, tps, tick times and heap on a fixed seed, but nothing fails when they get worse.
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
