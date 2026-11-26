# pack-pack tweaks

A small NeoForge mod with seven mixins and two event handlers, shipped as `pack/mods/packpack-tweaks-1.0.0.jar`.

- `KelpFeatureMixin` makes generated kelp up to 75 blocks tall instead of 10.
- `GrowingPlantHeadBlockMixin` keeps a growing kelp head from reaching the maximum age, so kelp keeps growing until it runs out of water.
- `WaterAnimalMixin` lets small fish (cod, salmon, tropical fish, pufferfish and any mod's `water_ambient` fish that use the vanilla rule) spawn anywhere under the Lost Worlds sea within 6 blocks of the floor or a reef.
  Vanilla only spawns them in the 13 blocks under the world's sea level, which here is a band at y 50 to 63 in open water.
  It finds Lost Worlds' generator by its interface name (`OuterSea`), so the mod doesn't depend on Lost Cities or Lost Worlds.
- `HapiSpawnRulesMixin` gives Hybrid Aquatic's spawn rules a sea level of y 19 under the Lost Worlds sea, so its fish spawn over the sea floor and its deep species in the trenches, instead of around y 63.
  Their rules also want to see the sky from below the water, which the tall kelp blocks, so that check passes under the Lost Worlds sea.
- `HapiSurfaceSpawnRulesMixin` gives its air breathers (orcas, dolphins, manatees, dugongs) the real surface instead, so they spawn where they can breathe.
- `WaterAnimalMixin` also lets vanilla dolphins spawn just under the real surface and squid anywhere in the water.
- `ItemEntityMixin` makes items sink slowly (about a block a second) instead of floating up, so drops end up on the floor below.
- `MobCategoryMixin` raises the small fish caps per player to 40 for vanilla's `water_ambient` and 60 for Hybrid Aquatic's own fish category (10 by default, which left the sea all cod and salmon), and the water creature cap (squid, sharks, rays) from 5 to 10.
- `SeaLife` runs when a mob enters the world:
  - mobs tagged `packpack:enlarged` (the big sharks, orca, sunfish, manta) get scale 1.5;
  - the predatory sharks (`packpack:drowned_hunters`, not whale or basking sharks) also target drowned;
  - bosses tagged `packpack:lair_bosses` (Karkinos, Shell Beast) remember where they first appeared, stay within 48 blocks of it and never despawn.
  The tags come from `tools/build_worldgen.py`, and In Control spawns the bosses rarely, only in trenches below y -36.
- `LostSub` runs when a player respawns: if they come back under the sea (the start sub is flooded or gone) they are moved to a random spot in one of the nearest domes with a diving suit and a full backtank, and that becomes their spawn.
  Someone whose own bed is under water is moved the same way but gets no suit, or a wet bed would hand one out on every death.
  It asks Lost Cities where the domes are through its API.

To rebuild: run `./gradlew build` here with `JAVA_HOME` pointing at Java 21, copy `build/libs/packpack-tweaks-1.0.0.jar` over the one in `pack/mods`, and run `packwiz refresh` in `pack/`.
The build is reproducible and CI compares its own build with the committed jar, so a jar that doesn't match the source fails.
