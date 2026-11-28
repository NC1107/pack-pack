# pack-pack tweaks

A small NeoForge mod with eight mixins and two event handlers, shipped as `pack/mods/packpack-tweaks-1.0.0.jar`.

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
- `BacktankFillMixin` makes a placed Create backtank fill faster from slow rotation: a full tank takes a bit over 2 minutes on a hand crank instead of 10 and a half.
  The hand pump in the start sub is the only air at first. Fast shafts fill as quickly as before.
- `SeaLife` runs when a mob enters the world:
  - mobs tagged `packpack:enlarged` (the big sharks, orca, sunfish, manta) get scale 1.5;
  - the predatory sharks (`packpack:drowned_hunters`, not whale or basking sharks) also target drowned;
  - bosses tagged `packpack:lair_bosses` (Karkinos, Shell Beast) remember where they first appeared, stay within 48 blocks of it and never despawn.
  The tags come from `tools/build_worldgen.py`, and In Control spawns the bosses rarely, only in trenches below y -36.
- `LostSub` runs when a player respawns: if they come back under the sea (the start sub is flooded or gone) they are moved to the escape pod beside the sub with a diving suit and a full backtank.
  Once they've been inside a dome (checked every 5 seconds, the `packpack_reached_dome` tag), or if the pod is flooded too, they go to a random spot in one of the nearest domes instead, and that becomes their spawn.
  The pod first means wrecking your own sub isn't a free trip to the domes.
  Someone whose own bed is under water is moved the same way but gets no suit, or a wet bed would hand one out on every death.
  It asks Lost Cities where the domes are through its API.
- `DiverDepthMixin` lowers Deep Seas' depth limit for a diver in the full Copper Diving Suit from 280 m to 220 m, so the suit covers the 200 m floor but not the trenches (about 240 m), which later suits are for.
- `ToxicAir` makes the air above the sea toxic: with their head out of the water under open sky, a survival player's breath runs down as underwater (about 15 seconds) and then they take a heart of damage a second ("breathed the air above the sea").
  Anywhere with a roof overhead is safe, like a sub's cabin at the surface.
  It's why sailing over the top is no shortcut to the domes.
- `RelicBlocks` adds the start sub's relic hull plating and relic pressure glass, made by the civilisation that built the domes.
  They're as hard as obsidian and drop nothing, so the start sub can't be stripped for deep-rated plating, and they're not unbreakable because the sub has to assemble into a Sable ship later.
  Deep Seas would rate the glass like normal glass (30 m), so `pack/config/submarine_hull.json` sets both to 400 m, the most it allows for blocks from other mods. Deep Seas fills in every other block itself.
  `art/relic_textures.py` draws their textures.

To rebuild: run `./gradlew build` here with `JAVA_HOME` pointing at Java 21, copy `build/libs/packpack-tweaks-1.0.0.jar` over the one in `pack/mods`, and run `packwiz refresh` in `pack/`.
The build is reproducible and CI compares its own build with the committed jar, so a jar that doesn't match the source fails.
