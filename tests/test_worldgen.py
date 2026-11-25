import re
from collections import deque

import build_worldgen as wg
import start_sub


def test_start_submarine_is_watertight():
    """Water from outside the wreck must not be able to reach any air inside it."""
    placed = start_sub.blocks()
    air = {cell for cell, block in placed.items() if block == "minecraft:air"}
    solid = set(placed) - air
    lo = tuple(min(c[i] for c in placed) - 2 for i in range(3))
    hi = tuple(max(c[i] for c in placed) + 2 for i in range(3))
    start = (lo[0], 0, lo[2])
    seen = {start}
    todo = deque([start])
    while todo:
        x, y, z = todo.popleft()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + dx, y + dy, z + dz)
            if n in seen or n in solid or not all(max(lo[i], 0) <= n[i] <= hi[i] for i in range(3)):
                continue
            assert n not in air, f"water reaches the submarine interior at {n}"
            seen.add(n)
            todo.append(n)


def test_start_submarine_furniture_stands_on_the_deck():
    placed = start_sub.blocks()
    for (x, y, z), block in start_sub.furniture(start_sub.DECK_Y).items():
        below = placed[(x, y - 1, z)]
        assert below not in ("minecraft:air", None), f"{block} at {(x, y, z)} has nothing under it"


def test_start_submarine_has_no_dark_floor():
    """Monsters spawn at block light 0, so every spot a mob could stand on in the wreck is lit."""
    placed = start_sub.blocks()
    open_cells = {cell for cell, block in placed.items() if block == "minecraft:air"}
    # Light passes through the airlock doors too
    lit_through = open_cells | {cell for cell, block in placed.items() if "_door[" in block}
    light = {cell: 15 for cell, block in placed.items() if block == start_sub.CEILING_LIGHT}
    todo = deque(light)
    while todo:
        x, y, z = todo.popleft()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + dx, y + dy, z + dz)
            if n in lit_through and light.get(n, 0) < light[(x, y, z)] - 1:
                light[n] = light[(x, y, z)] - 1
                todo.append(n)
    standing = [(x, y, z) for x, y, z in open_cells
                if (x, y + 1, z) in open_cells and placed.get((x, y - 1, z), "minecraft:air") != "minecraft:air"]
    dark = [cell for cell in standing if light.get(cell, 0) == 0]
    assert not dark, f"monsters could spawn in the dark at {sorted(dark)[:5]}"


def test_fill_runs_cover_exactly_the_cells():
    shell, _ = start_sub.hull_cells()
    covered = set()
    for line in wg.fill_runs(list(shell), "minecraft:glass"):
        x1, y1, z1, x2, y2, z2 = map(int, re.findall(r"~(-?\d+)", line))
        assert (x1, y1) == (x2, y2)
        covered.update((x1, y1, z) for z in range(z1, z2 + 1))
    assert covered == shell


def test_ocean_temperature_bands_cover_the_whole_range():
    bands = sorted(band for band, _, _ in wg.TEMPERATURE_BANDS)
    assert bands[0][0] == -1.0 and bands[-1][1] == 1.0
    for (_, end), (start, _) in zip(bands, bands[1:], strict=False):
        assert end == start
