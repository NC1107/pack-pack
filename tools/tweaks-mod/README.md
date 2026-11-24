# pack-pack tweaks

A small NeoForge mod with two mixins, shipped as `pack/mods/packpack-tweaks-1.0.0.jar`.

- `KelpFeatureMixin` makes generated kelp up to 75 blocks tall instead of 10.
- `GrowingPlantHeadBlockMixin` keeps a growing kelp head from reaching the maximum age, so kelp keeps growing until it runs out of water.

To rebuild: run `./gradlew build` here with Java 21 and copy `build/libs/packpack-tweaks-1.0.0.jar` over the one in `pack/mods`.
