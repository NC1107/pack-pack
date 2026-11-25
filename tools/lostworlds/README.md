# Patched Lost Worlds

The pack ships `pack/mods/lostworlds-1.21-2.0.0-packpack.jar`, a patched build of Lost Worlds LC (MIT licensed, https://github.com/McJty/LostWorlds, 1.21.1 NeoForge port commit 2959906).

Two things change, only for the `spheres` generator with a custom sea level:

- The sea floor outside domes comes from `SeaFloor.java`: broad plates, ridges, trenches, seamounts and hills, flat around the dome grid and around spawn.
- Under the floor it is sand for 30 blocks (SeaFloor.SAND_DEPTH) in the chunk generator, and the pack's noise settings use sand as the default block, so there is no stone or ore and no bedrock showing on slopes.
- Height lookups (`getBaseHeight`, `getBaseColumn`) answer from that same floor, in block coordinates.
  Upstream returns the world minimum there, which put structures in the wrong place and kept Lost Cities from generating drowned cities outside domes.

`SeaFloor` assumes a dome slot every 512 blocks offset by 128, which is Lost Cities with `grid32` on.
Change both together.

To rebuild: clone upstream at the commit above, copy `SeaFloor.java` into `src/main/java/mcjty/lostworlds/worldgen/`, apply `LWChunkGenerator.patch` with `patch -p1`, run `./gradlew build` with Java 21, and copy the jar from `build/libs` over the one in `pack/mods`.

No structure may start within 10 chunks of 0,0 under the outer sea (in `LWChunkGenerator.tryGenerateStructure`, Lost Worlds' own copy of the vanilla method), so nothing generates through the start dome.
