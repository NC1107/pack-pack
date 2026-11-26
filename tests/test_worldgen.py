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


def test_start_submarine_air_pump_crank_drives_the_tank():
    """A backtank only takes rotation from above, and a hand crank's shaft is opposite its handle."""
    furniture = start_sub.furniture(start_sub.DECK_Y)
    (x, y, z), = [cell for cell, block in furniture.items() if block == start_sub.AIR_PUMP_TANK]
    assert furniture[(x, y + 1, z)] == start_sub.AIR_PUMP_CRANK
    assert start_sub.AIR_PUMP_CRANK.endswith("[facing=up]")
    # Room to stand next to it and reach the crank
    assert any(start_sub.blocks().get((x + dx, y, z + dz)) == "minecraft:air" for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))


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


def test_start_refresh_touches_every_section_of_the_wreck(tmp_path):
    wg.write_start_refresh(tmp_path, [(x, y, z) for x in range(-20, 20) for y in range(0, 20) for z in range(-8, 10)])
    lines = (tmp_path / "refresh_start.mcfunction").read_text().splitlines()
    done = (tmp_path / "refresh_start_done.mcfunction").read_text().splitlines()
    cells = [tuple(map(int, re.search(r"setblock (-?\d+) (-?\d+) (-?\d+)", line).groups())) for line in lines[:-1]]
    sections = {(x >> 4, (wg.DOME_FLOOR_Y + y) >> 4, z >> 4) for x, y, z in start_sub.blocks()}
    assert sections <= {(x >> 4, y >> 4, z >> 4) for x, y, z in cells}
    assert lines[-1].startswith("schedule function packpack:refresh_start_done")
    assert len(done) == len(cells) and all("minecraft:water" in line for line in done)


def test_only_water_open_to_the_sea_counts_as_under_the_floor():
    import numpy as np
    import check_worldgen
    # From the bottom: water under ground, ground, a sealed pocket, a slab, then open water.
    column = np.array([[[3], [0], [3], [4], [3], [3], [3]]])
    open_cells = check_worldgen.open_to_sea(column)[0, :, 0].tolist()
    assert open_cells == [False, False, False, False, True, True, True]


def test_expedition_log_fits_the_lectern_command():
    command = wg.expedition_log()
    assert command.startswith("setblock ") and "has_book=true" in command
    for page in start_sub.LOG_PAGES:
        assert "'" not in page and '"' not in page
        assert len(page) <= 256
