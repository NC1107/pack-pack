"""The wrecked submarine players start in, as a map of block positions.

Positions are relative to the build origin: x runs along the hull, y=0 is the first layer above
the sea floor, z is across the hull. The hull is a capsule: a circle of radius RADIUS around the
axis at y=RADIUS for the middle stretch, tapering to a point over TAPER blocks at each end. The
side airlock is two doors with a small room between them, since a door keeps water out even
while it is open.
"""

from __future__ import annotations

import math

RADIUS = 4
MIDDLE = 9           # half the length of the straight part of the hull
TAPER = 4            # length of each tapered end
LENGTH = MIDDLE + TAPER
AXIS_Y = RADIUS
DECK_Y = 1

HULL = "minecraft:waxed_weathered_cut_copper"
HULL_BAND = "minecraft:waxed_oxidized_cut_copper"
DECK = "minecraft:waxed_exposed_cut_copper"
PORTHOLE = "minecraft:glass"
CEILING_LIGHT = "minecraft:sea_lantern"
TOWER = "minecraft:waxed_weathered_copper"

PORTHOLE_X = (-8, -4, 0, 4, 8)
LIGHT_X = (-9, -5, 5, 9)
AIRLOCK_X = 6
DOOR = "minecraft:oak_door[facing=south,hinge=left,open=false,powered=false"

Cell = tuple[int, int, int]


def hull_radius(x: int) -> float:
    beyond = abs(x) - MIDDLE
    if beyond <= 0:
        return RADIUS
    return RADIUS * math.sqrt(max(0.0, 1 - (beyond / (TAPER + 1)) ** 2))


def in_hull(x: int, y: int, z: int) -> bool:
    r = hull_radius(x)
    return abs(x) <= LENGTH and (y - AXIS_Y) ** 2 + z * z <= r * r + 0.5


def hull_cells() -> tuple[set[Cell], set[Cell]]:
    """Shell (every hull cell with a face neighbour outside it) and interior."""
    shell, interior = set(), set()
    for x in range(-LENGTH, LENGTH + 1):
        for y in range(0, 2 * RADIUS + 1):
            for z in range(-RADIUS, RADIUS + 1):
                if not in_hull(x, y, z):
                    continue
                outside = any(not in_hull(x + dx, y + dy, z + dz)
                              for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))
                (shell if outside else interior).add((x, y, z))
    return shell, interior


def blocks() -> dict[Cell, str]:
    """Every block the submarine places, air included."""
    shell, interior = hull_cells()
    placed: dict[Cell, str] = {}
    for cell in interior:
        placed[cell] = "minecraft:air"
    for x, y, z in shell:
        placed[(x, y, z)] = HULL_BAND if y == AXIS_Y + 2 else HULL
    # The lowest full row is plated over as the deck, the curve of the keel below it stays hull.
    for x, y, z in shell | interior:
        if y == DECK_Y:
            placed[(x, y, z)] = DECK
    for x in PORTHOLE_X:
        for z in (-RADIUS, RADIUS):
            placed[(x, AXIS_Y, z)] = PORTHOLE
    top = AXIS_Y + RADIUS
    for x in LIGHT_X:
        placed[(x, top, 0)] = CEILING_LIGHT
    # Conning tower: a closed box on top of the hull with windows, part of the silhouette.
    for x in range(-2, 3):
        for z in range(-1, 2):
            for y in range(top + 1, top + 4):
                edge = x in (-2, 2) or z in (-1, 1) or y == top + 3
                placed[(x, y, z)] = (PORTHOLE if y == top + 2 and x == 0 else TOWER) if edge else "minecraft:air"
    placed.update(airlock(DECK_Y, shell))
    placed.update(furniture(DECK_Y))
    return placed


def airlock(deck_y: int, shell: set[Cell]) -> dict[Cell, str]:
    """A room on the south side of the hull with a door into the hull and one out to sea."""
    wall_z = max(z for x, y, z in shell if x == AIRLOCK_X and y == deck_y + 1)
    out_z = wall_z + 4
    room: dict[Cell, str] = {}
    for x in range(AIRLOCK_X - 1, AIRLOCK_X + 2):
        for y in range(deck_y, deck_y + 4):
            for z in range(wall_z, out_z + 1):
                edge = x != AIRLOCK_X or y in (deck_y, deck_y + 3) or z in (wall_z, out_z)
                room[(x, y, z)] = HULL if edge else "minecraft:air"
    for z in (wall_z, out_z):
        room[(AIRLOCK_X, deck_y + 1, z)] = f"{DOOR},half=lower]"
        room[(AIRLOCK_X, deck_y + 2, z)] = f"{DOOR},half=upper]"
    return room


def furniture(deck_y: int) -> dict[Cell, str]:
    """A cramped, dead control room at the bow and bunks at the stern."""
    y = deck_y + 1
    return {
        (LENGTH - 4, y, 0): "minecraft:lectern[facing=east]",
        (LENGTH - 4, y, -1): "minecraft:polished_blackstone_button[face=floor,facing=west]",
        (LENGTH - 4, y, 1): "minecraft:redstone_lamp[lit=false]",
        (LENGTH - 5, y, -2): "minecraft:barrel[facing=up]",
        (-LENGTH + 4, y, -1): "minecraft:red_bed[facing=west,part=head]",
        (-LENGTH + 5, y, -1): "minecraft:red_bed[facing=west,part=foot]",
        (-LENGTH + 4, y, 1): "minecraft:chest[facing=north]",
        (-LENGTH + 6, y, 1): "minecraft:crafting_table",
        (-LENGTH + 6, y, -2): "minecraft:furnace[facing=east]",
    }
