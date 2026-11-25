# pack-pack tweaks

A small NeoForge mod with five mixins, shipped as `pack/mods/packpack-tweaks-1.0.0.jar`.

- `KelpFeatureMixin` makes generated kelp up to 75 blocks tall instead of 10.
- `GrowingPlantHeadBlockMixin` keeps a growing kelp head from reaching the maximum age, so kelp keeps growing until it runs out of water.
- `WaterAnimalMixin` lets small fish (cod, salmon, tropical fish, pufferfish and any mod's `water_ambient` fish that use the vanilla rule) spawn anywhere under the Lost Worlds sea within 6 blocks of the floor or a reef.
  Vanilla only spawns them in the 13 blocks under the world's sea level, which here is a band at y 50 to 63 in open water.
  It finds Lost Worlds' generator by its interface name (`OuterSea`), so the mod doesn't depend on Lost Cities or Lost Worlds.
- `HapiSpawnRulesMixin` gives Hybrid Aquatic's spawn rules a sea level of y 19 under the Lost Worlds sea, so its fish spawn over the sea floor and its deep species in the trenches, instead of around y 63.
- `MobCategoryMixin` raises the small fish cap from 20 to 50 per player, since dozens of species share it.

To rebuild: run `./gradlew build` here with Java 21 and copy `build/libs/packpack-tweaks-1.0.0.jar` over the one in `pack/mods`.
