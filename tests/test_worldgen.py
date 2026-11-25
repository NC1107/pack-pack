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
