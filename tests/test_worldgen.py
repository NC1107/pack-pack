import re
from collections import deque

import build_worldgen as wg
import check_worldgen
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


def test_worldgen_area_holds_every_dome_window():
    for area in (check_worldgen.Area(), check_worldgen.Area(3, 3)):
        assert len(area.domes) == area.across * area.down
        chunks = set(area.chunks())
        for gx, gz in area.domes:
            for x in (gx - check_worldgen.WINDOW, gx + check_worldgen.WINDOW - 1):
                for z in (gz - check_worldgen.WINDOW, gz + check_worldgen.WINDOW - 1):
                    assert (x >> 4, z >> 4) in chunks
        x0, z0, size = check_worldgen.BETWEEN
        assert (x0 >> 4, z0 >> 4) in chunks and ((x0 + size) >> 4, (z0 + size) >> 4) in chunks


def test_worldgen_slots_match_the_dome_grid():
    """The check looks for domes where the generator puts them: chunk (40, 8) and every 64 chunks."""
    grid, (ox, oz) = wg.DOME_GRID_CHUNKS, wg.DOME_GRID_OFFSET
    assert check_worldgen.SLOT_SPACING == grid * 16
    assert check_worldgen.FIRST_SLOT == (ox * 16, oz * 16)
    assert ox % 16 == 8 and oz % 16 == 8, "Lost Cities looks spheres up by 16 chunk cells centred on 8"
    assert check_worldgen.Area().domes == [(640, 128), (1664, 128)]


def test_start_saucer_has_glass_all_the_way_round():
    """Standing in the middle at eye level, the wall is relic glass in every direction except the airlock."""
    import math
    furniture = start_sub.furniture(start_sub.DECK_Y)
    airlock = start_sub.airlock(start_sub.DECK_Y, start_sub.hull_cells()[0])
    placed = {cell: block for cell, block in start_sub.blocks().items() if cell not in furniture}
    eye = start_sub.DECK_Y + 2
    for step in range(72):
        angle = step * math.tau / 72
        # Fine steps, so the ray can't hop diagonally past two blocks that meet at a corner.
        for twentieth in range(20, 400):
            r = twentieth / 20
            cell = (round(r * math.cos(angle)), eye, round(r * math.sin(angle)))
            block = placed.get(cell, "minecraft:air")
            if block != "minecraft:air":
                break
        assert block == start_sub.WINDOW or cell in airlock, f"{block} blocks the view at {angle:.2f} rad"


def test_escape_pod_offset_matches_the_tweaks_mod():
    """LostSub moves players to the pod by an offset from the world spawn; it must be the pod."""
    from pathlib import Path
    java = (Path(__file__).resolve().parents[1] / "tools/tweaks-mod/src/main/java/dev/nc1107/packpack/LostSub.java").read_text()
    offset = tuple(int(v) for v in re.search(r"POD_OFFSET = new BlockPos\((-?\d+), (-?\d+), (-?\d+)\)", java).groups())
    x, y, z = start_sub.pod_feet()
    assert offset == (x, y - (start_sub.DECK_Y + 1), z)
    placed = start_sub.blocks()
    assert placed[(x, y, z)] == "minecraft:air" and placed[(x, y + 1, z)] == "minecraft:air"
