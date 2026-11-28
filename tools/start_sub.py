"""The start sub players wake up in, as a map of block positions.

A relic saucer from the civilisation that built the domes: round, dark, with a band of pressure
glass all the way around at eye level so you can see out in every direction. Positions are
relative to the build origin at its centre: y=0 is the first layer above the sea floor. The hull
is a solid of revolution, PROFILE gives its outer radius per layer. The side airlock is two
doors with a small room between them, since a door keeps water out even while it is open.
"""

from __future__ import annotations

import math

# Outer radius per layer, bottom to top: a shallow keel, a rim flaring out at the deck, the glass
# band set back from it, a second rim at the ceiling and a low dome on top. The two rims are what
# make it read as a saucer rather than a can.
PROFILE = {0: 8.5, 1: 12.5, 2: 10.5, 3: 10.5, 4: 10.5, 5: 10.5, 6: 12.5, 7: 9.5, 8: 7.0, 9: 4.0}
DECK_Y = 1
GLASS_LAYERS = range(2, 6)
CEILING_Y = 7        # everything inside from here up is solid, so the cabin is 5 blocks tall
RADIUS = max(PROFILE.values())

HULL = "packpack_tweaks:relic_hull"
DECK = "packpack_tweaks:relic_hull"
WINDOW = "packpack_tweaks:relic_glass"
CEILING_LIGHT = "minecraft:sea_lantern"
# Lights in the ceiling: one in the middle and a ring of eight, so the edge of the deck stays lit.
LIGHT_CELLS = [(0, 0)] + [(round(5 * math.cos(a * math.pi / 4)), round(5 * math.sin(a * math.pi / 4))) for a in range(8)]

# An escape pod beside the saucer: where you wake up if the saucer is flooded or gone before you've
# reached a dome (tweaks mod LostSub, POD_OFFSET there), so breaking your own sub isn't a free trip
# to the domes. A separate sealed room with one door out to sea and a light.
POD_X = range(-18, -13)
POD_Y = range(0, 5)
POD_Z = range(-2, 3)
POD_DOOR = "minecraft:dark_oak_door[facing=west,hinge=left,open=false,powered=false"

# The only air supply there is at the start: a spare backtank standing under a hand crank.
# A placed backtank takes rotation from above and fills from it.
AIR_PUMP_TANK = "create:copper_backtank"
AIR_PUMP_CRANK = "create:hand_crank[facing=up]"
DOOR = "minecraft:dark_oak_door[facing=south,hinge=left,open=false,powered=false"

Cell = tuple[int, int, int]


def in_hull(x: int, y: int, z: int) -> bool:
    r = PROFILE.get(y)
    return r is not None and x * x + z * z <= r * r


def hull_cells() -> tuple[set[Cell], set[Cell]]:
    """Shell (every hull cell with a face neighbour outside it) and interior."""
    shell, interior = set(), set()
    reach = math.ceil(RADIUS)
    for y in PROFILE:
        for x in range(-reach, reach + 1):
            for z in range(-reach, reach + 1):
                if not in_hull(x, y, z):
                    continue
                outside = any(not in_hull(x + dx, y + dy, z + dz)
                              for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))
                (shell if outside else interior).add((x, y, z))
    return shell, interior


def blocks() -> dict[Cell, str]:
    """Every block the saucer places, air included."""
    shell, interior = hull_cells()
    placed: dict[Cell, str] = {}
    for x, y, z in interior:
        # Below the deck and above the ceiling is solid hull, so no closed, dark air is left
        # anywhere for monsters to spawn in.
        placed[(x, y, z)] = "minecraft:air" if DECK_Y < y < CEILING_Y else HULL
    for x, y, z in shell:
        placed[(x, y, z)] = WINDOW if y in GLASS_LAYERS else HULL
    for x, y, z in shell | interior:
        if y == DECK_Y:
            placed[(x, y, z)] = DECK
    for x, z in LIGHT_CELLS:
        placed[(x, CEILING_Y, z)] = CEILING_LIGHT
    placed.update(airlock(DECK_Y, shell))
    placed.update(escape_pod())
    placed.update(furniture(DECK_Y))
    return placed


def escape_pod() -> dict[Cell, str]:
    pod: dict[Cell, str] = {}
    for x in POD_X:
        for y in POD_Y:
            for z in POD_Z:
                edge = x in (POD_X[0], POD_X[-1]) or y in (POD_Y[0], POD_Y[-1]) or z in (POD_Z[0], POD_Z[-1])
                pod[(x, y, z)] = HULL if edge else "minecraft:air"
    pod[(POD_X[0] + 2, POD_Y[-1], 0)] = CEILING_LIGHT
    pod[(POD_X[0], POD_Y[0] + 1, 0)] = f"{POD_DOOR},half=lower]"
    pod[(POD_X[0], POD_Y[0] + 2, 0)] = f"{POD_DOOR},half=upper]"
    return pod


def pod_feet() -> Cell:
    """Where a player stands in the escape pod, relative to the build origin."""
    return (POD_X[0] + 2, POD_Y[0] + 1, 0)


def airlock(deck_y: int, shell: set[Cell]) -> dict[Cell, str]:
    """A room on the south side with a door into the cabin and one out to sea."""
    wall_z = max(z for x, y, z in shell if x == 0 and y == deck_y + 1)
    out_z = wall_z + 4
    room: dict[Cell, str] = {}
    for x in range(-1, 2):
        for y in range(deck_y, deck_y + 4):
            for z in range(wall_z, out_z + 1):
                edge = x != 0 or y in (deck_y, deck_y + 3) or z in (wall_z, out_z)
                room[(x, y, z)] = HULL if edge else "minecraft:air"
    for z in (wall_z, out_z):
        room[(0, deck_y + 1, z)] = f"{DOOR},half=lower]"
        room[(0, deck_y + 2, z)] = f"{DOOR},half=upper]"
    return room


def furniture(deck_y: int) -> dict[Cell, str]:
    """A dead bridge on the north side, the bunk, stores and the air pump around the walls."""
    y = deck_y + 1
    return {
        (0, y, -6): "minecraft:lectern[facing=south]",
        (-1, y, -6): "minecraft:redstone_lamp[lit=false]",
        (1, y, -6): "minecraft:redstone_lamp[lit=false]",
        (6, y, 1): AIR_PUMP_TANK,
        (6, y + 1, 1): AIR_PUMP_CRANK,
        (6, y, -2): "minecraft:crafting_table",
        (6, y, -3): "minecraft:furnace[facing=west]",
        (-6, y, 2): "minecraft:red_bed[facing=west,part=head]",
        (-5, y, 2): "minecraft:red_bed[facing=west,part=foot]",
        (-6, y, -1): "minecraft:chest[facing=east]",
        (-6, y, -3): "minecraft:barrel[facing=up]",
    }


# Deep Seas crushes players swimming past 120 m (dead at 180 m) unless they wear the full
# Copper Diving Suit, good to 280 m. The sea floor here is 200 m down, so the wreck keeps
# a suit and a full backtank to breathe from: suiting up is how anyone gets outside.
STARTER_KIT = [
    "create:copper_diving_helmet",
    "create_submarine:diving_chestplate",
    "create_submarine:diving_leggings",
    "create:copper_diving_boots",
    "create:copper_backtank[create:banktank_air=900]",
]


# The story, on the bridge lectern: you are a scientist who left your dome to find out what floods
# the world and poisons the air, ran out of fuel, and sank when something broke. No quotes or apostrophes, it is embedded in SNBT.
LOG_TITLE = "Expedition Log"
LOG_AUTHOR = "You"
LOG_PAGES = [
    "Day 1. Left the dome at first light. The water rises every year and the air above it burns. "
    "The council says no answer lies past the glass. I mean to find one. Fuel for nine days, air for twenty.",
    "Day 6. Past the last of the drowned towers. Kelp and sand in every direction. "
    "Fuel is lower than it should be. Turning for home.",
    "Day 7. Out of fuel, drifting. Then a bang from the stern and water in the engine bay. "
    "Sealed it off, but she would not hold her trim. Going down.",
    "Day 7, later. On the bottom, two hundred metres down. The hull held. "
    "The lights are gone and the motor with them. The airlock still works.",
    "The diving suit and the backtank are in the chest by the bunks. Wear all of it outside, "
    "the water crushes anyone without it this deep. The tank holds about fifteen minutes of air.",
    "The hand pump by the bunks still works, there is a spare tank standing on it. "
    "Hold the crank and it fills, a couple of minutes for a full tank. Break a tank to pick it up, "
    "set an empty one under the crank to fill it again.",
    "The domes are out there, the nearest more than five hundred blocks away. Too far on one tank. "
    "First air, then power, then get this boat moving again.",
]


def lectern() -> tuple[Cell, str]:
    """Where the log goes and the lectern block it sits on."""
    return next((cell, block) for cell, block in furniture(DECK_Y).items() if block.startswith("minecraft:lectern"))


def starter_chest() -> Cell:
    """The chest the starter kit goes in."""
    return next(cell for cell, block in furniture(DECK_Y).items() if block.startswith("minecraft:chest"))
