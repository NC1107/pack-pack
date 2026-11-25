import re
from collections import deque

import build_worldgen as wg


def test_start_dome_is_watertight():
    """Water from outside the dome must not be able to reach any interior air cell."""
    r = wg.START_DOME_RADIUS
    floor, shell, interior = wg.dome_cells(r)
    walls = set(floor) | set(shell)
    inside = set(interior)
    lo, hi = -r - 2, r + 2
    start = (lo, 0, lo)
    seen = {start}
    todo = deque([start])
    while todo:
        x, y, z = todo.popleft()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + dx, y + dy, z + dz)
            if n in seen or n in walls or not (lo <= n[0] <= hi and 0 <= n[1] <= hi and lo <= n[2] <= hi):
                continue
            assert n not in inside, f"water reaches the dome interior at {n}"
            seen.add(n)
            todo.append(n)


def test_fill_runs_cover_exactly_the_cells():
    _, shell, _ = wg.dome_cells(wg.START_DOME_RADIUS)
    covered = set()
    for line in wg.fill_runs(shell, "minecraft:glass"):
        x1, y1, z1, x2, y2, z2 = map(int, re.findall(r"~(-?\d+)", line))
        assert (x1, y1) == (x2, y2)
        covered.update((x1, y1, z) for z in range(z1, z2 + 1))
    assert covered == set(shell)


def test_ocean_temperature_bands_cover_the_whole_range():
    bands = sorted(band for band, _, _ in wg.TEMPERATURE_BANDS)
    assert bands[0][0] == -1.0 and bands[-1][1] == 1.0
    for (_, end), (start, _) in zip(bands, bands[1:], strict=False):
        assert end == start
