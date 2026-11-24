# Patched Lost Worlds

The pack ships `pack/mods/lostworlds-1.21-2.0.0-packpack.jar`, a patched build of Lost Worlds LC (MIT licensed, https://github.com/McJty/LostWorlds, 1.21.1 NeoForge port commit 2959906).

Two things change, only for the `spheres` generator with a custom sea level:

- The sea floor outside domes comes from `SeaFloor.java`: broad plates, ridges, trenches, seamounts and hills, flat around the dome grid and around spawn.
- Height lookups (`getBaseHeight`, `getBaseColumn`) answer from that same floor, in block coordinates.
  Upstream returns the world minimum there, which put structures in the wrong place and kept Lost Cities from generating drowned cities outside domes.

`SeaFloor` assumes a dome every 256 blocks offset by 128, which is Lost Cities with `grid32` off.
Change both together.

To rebuild: clone upstream at the commit above, copy `SeaFloor.java` into `src/main/java/mcjty/lostworlds/worldgen/`, apply `LWChunkGenerator.patch` with `patch -p1`, run `./gradlew build` with Java 21, and copy the jar from `build/libs` over the one in `pack/mods`.
