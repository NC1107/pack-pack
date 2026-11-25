# Patched Lost Cities

The pack ships `pack/mods/lostcities-1.21-8.4.8-packpack.jar`, a patched build of The Lost Cities (MIT licensed, https://github.com/McJty/LostCities, version 1.21-8.4.8).

What changes:

- Spheres (domes) are not generated within the profile's `citySpawnDistance1` of the world origin, so nothing is visible from spawn.
  A monorail tube between two domes is not built if its path comes within that distance of the origin, so there are no tube stubs ending in the open.
- The sphere cache read no longer returns null when another thread clears it between a check and a read, which showed up as `Error generating chunk ... "sphere" is null`.
- A part that uses an undefined palette character no longer aborts the whole chunk with `"state" is null`, that block is just skipped.
  Before, a failed chunk was left empty inside a dome.

- The sphere factor scales the whole city radius. Upstream only scaled the random part, which made our domes over 100 blocks wide.
- Under an outer sea, any air left below sea level outside a dome (rooms of drowned cities, structure templates) is flooded as the last step of generation, so there are no air pockets in the water. Grass there turns to moss.

- The pass that floods air outside domes runs before the tubes between domes are built, so the tubes keep their air. When it ran after them it filled the tubes and the domes opened straight into water.
- Under the sea, building foundations and streets fill through the water down to the sea floor (upstream only fills air and stops at y 1), so drowned buildings next to sea floor hills don't hang in the water.
- After flooding, any block in a drowned chunk that doesn't connect to the floor or the chunk edge becomes water, which clears ruin debris like chains, cobwebs and lone slabs, and anything flowing water would wash away (plants, tripwire, torches) becomes water too, so it never drops as items floating around the ruins.
- Domes are lit: invisible light blocks sit three blocks above the street, lawn or roof on a six block grid, since no daylight gets through the sea above them.
- Cities inside domes are all on one level. Upstream steps them up towards the middle of a sphere, which on a flat dome floor left retaining walls and overhangs.

To rebuild: clone upstream at 1.21-8.4.8, apply `lostcities.patch` with `patch -p1`, run `./gradlew build` with Java 21, copy `build/libs/lostcities-1.21-8.4.8.jar` over the one in `pack/mods`.
