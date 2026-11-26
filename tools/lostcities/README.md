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
- After flooding, any block that doesn't connect to the ground or the chunk edge goes, inside domes too (air in a dome, water outside), which clears ruin debris like chains, cobwebs and lone slabs, and anything flowing water would wash away (plants, tripwire, torches) becomes water too, so it never drops as items floating around the ruins.
- Under the outer sea the spawn point is set at 0,0 right away. Upstream searches for dry ground to stand on, and in an ocean world it generated chunks hundreds of blocks out on the main thread before a new world opened (a minute or more in singleplayer).
- The ring Lost Cities clears around each sphere in the space landscape only goes from the dome floor up under the outer sea. Cleared all the way, it left a ring of water down to bedrock around every dome.
- Sand, gravel and clay right above water or air outside domes collapse into water in the flood pass. Lost Worlds keeps its sea floor hills inside cities, and over ruined, flooded buildings that sand hung in the water and fell as soon as its chunk updated, thousands of falling blocks around a player.
- The glass tubes between domes get light blocks every four blocks along their middle. They were the only air outside domes, and dark enough for zombies, skeletons and creepers to spawn in them.
- The deferred sapling growth only runs once its chunk and the ones around it are fully loaded (`getChunkNow`). Upstream checks `isAreaLoaded`, which with C2ME can be true for a chunk still generating, and then blocked the server thread until it finished: 2 to 10 second stalls while exploring.
- Every chunk inside a dome takes the city style of the dome's centre. Upstream picks a style per chunk from all the city centres around it, so a village dome came out as a few village houses mixed into a normal city (19 of 21 domes had some, none was a village).
- A chunk of a multi building no longer gets more cellars than its own building allows. It copies the top-left chunk's count, which across a dome's edge can be another building's, and then had no parts for those cellars: `Misconfiguration! No part condition matches`, the chunk failed and left a hole in the dome glass.
- A dome's lower shell never replaces bedrock. Big domes reach the bottom of the world, and our shell is sand, so sand took the place of the bottom bedrock with only the void under it: once its chunk updated, the whole column under the dome drained out of the world (up to 7000 falling blocks at once while flying past domes).
- Domes are lit: invisible light blocks sit three blocks above the street, lawn or roof on a six block grid, since no daylight gets through the sea above them.
- Cities inside domes are all on one level. Upstream steps them up towards the middle of a sphere, which on a flat dome floor left retaining walls and overhangs.

To rebuild: clone upstream at 1.21-8.4.8, apply `lostcities.patch` with `patch -p1`, run `./gradlew build` with Java 21, copy `build/libs/lostcities-1.21-8.4.8.jar` over the one in `pack/mods`.
