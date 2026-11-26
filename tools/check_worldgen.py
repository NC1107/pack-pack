#!/usr/bin/env python3
"""Generate a patch of the ocean world and check the domes in it.

Runs the server installed by boot_server.py with Chunky, pre-generates a square that holds four
domes on Lost Cities' 512 block grid, then reads the region files and checks every dome: the glass
shell is complete, no air touches the water (in the dome or in the tunnels out of it), there is no
other air in the water outside it, nothing floats in the drowned city between the domes, and the ground outside the rim is level with the ground inside. It also fails if a mod's biome shows up, since Lost Cities does not
build in those (that is how domes lost their glass before).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib

import numpy as np

import boot_server
from downloads import cached_download
from region import Region, section_ids

CHUNKY_URL = "https://cdn.modrinth.com/data/fALzjamp/versions/LuFhm4eU/Chunky-NeoForge-1.4.23.jar"
CHUNKY_SHA256 = "d72f235cf1f56f2c374f52c00bdda5034524b28142305a84cfc123a3f92ad274"
# A square holding four dome slots on the 512 block grid (128 + 512k), with room for each
# dome's window. Each slot has a dome about 80% of the time.
CENTRE = (896, 896)
RADIUS = 420
DOMES = [(640, 640), (640, 1152), (1152, 640), (1152, 1152)]
WINDOW = 135
Y_MIN, Y_MAX = -70, 125
GROUND = {"sand", "gravel", "dirt", "grass_block", "clay"}
# What counts as a pass. A few air blocks hug a shell where its voxels meet the water.
MAX_SHELL_MISSING = 0.01
MAX_AIR_OUTSIDE = 200
MAX_LEAKS = 20
# The floor is flat around a dome, so there is no water below it around the dome's edge.
MAX_WATER_UNDER_FLOOR = 20
# Tunnels leave a dome along the 16 block wide chunk row and column that hold its centre.
TUNNEL_WIDTH = 16
RIM_GROUND = range(-15, -12)
# The drowned city between the four domes, clear of their shells.
BETWEEN = (736, 736, 320)
MAX_FLOATING = 200
CHUNK_ERROR = re.compile(r"Error generating chunk -?\d+,-?\d+: .{0,160}")
# Sand or gravel resting on water or air falls as soon as its chunk updates: thousands of
# falling block entities once hills in drowned cities hung over flooded ruins.
MAX_LOOSE_OVER_WATER = 20


def neoforge_version() -> str:
    return tomllib.loads(boot_server.PACK_TOML.read_text("utf-8"))["versions"]["neoforge"]


def use_seed(seed: str) -> None:
    """Point the boot test server at another world seed for the next generation."""
    properties = boot_server.SERVER / "server.properties"
    text = re.sub(r"(?m)^level-seed=.*$", f"level-seed={seed}", properties.read_text())
    properties.write_text(text)


def pregenerate(java: str) -> tuple[float, list[str]]:
    """Generate the test square; return how many chunks a second that took and the chunks that
    failed to generate (a failed chunk is left out of the world, e.g. a hole in a dome)."""
    mods = boot_server.SERVER / "mods"
    jar = mods / "chunky.jar"
    shutil.copy(cached_download(CHUNKY_URL, CHUNKY_SHA256), jar)
    shutil.rmtree(boot_server.SERVER / "world", ignore_errors=True)
    shutil.rmtree(boot_server.SERVER / "config" / "chunky" / "tasks", ignore_errors=True)
    finished = threading.Event()
    started = None
    failed = []
    try:
        proc = subprocess.Popen(boot_server.server_command(java, neoforge_version()), cwd=boot_server.SERVER,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        assert proc.stdin and proc.stdout
        for line in proc.stdout:
            if error := CHUNK_ERROR.search(line):
                failed.append(error.group(0))
            if boot_server.DONE_LINE.search(line):
                started = time.monotonic()
                proc.stdin.write(f"chunky world minecraft:overworld\nchunky center {CENTRE[0]} {CENTRE[1]}\n"
                                 f"chunky radius {RADIUS}\nchunky start\n")
                proc.stdin.flush()
            if re.search(r"\[Chunky\] Task (finished|stopped|cancelled)", line) or "Preparing crash report" in line:
                elapsed = time.monotonic() - (started or time.monotonic())
                finished.set()
                proc.stdin.write("save-all flush\nstop\n")
                proc.stdin.flush()
        proc.wait(timeout=120)
    finally:
        jar.unlink(missing_ok=True)
    if not finished.is_set():
        raise SystemExit("pre-generation did not finish")
    chunks = (2 * RADIUS // 16 + 1) ** 2
    return chunks / max(elapsed, 1e-6), failed


def load(region: Region, x0: int, z0: int, size: int, classify=None) -> np.ndarray:
    """Block classes in a box: 0 other, 1 glass, 2 air, 3 water, 4 ground (or classify's own)."""
    classify = classify or classify_block
    blocks = np.zeros((size, Y_MAX - Y_MIN, size), np.uint8)
    for cx in range(x0 >> 4, ((x0 + size - 1) >> 4) + 1):
        for cz in range(z0 >> 4, ((z0 + size - 1) >> 4) + 1):
            chunk = region.chunk(cx, cz)
            if not chunk:
                continue
            for section in chunk["sections"]:
                sy = section["Y"] * 16
                if sy + 16 <= Y_MIN or sy >= Y_MAX:
                    continue
                palette, ids = section_ids(section)
                code = np.array([classify(b) for b in palette], np.uint8)[ids]
                xa, xb = max(cx * 16, x0), min(cx * 16 + 16, x0 + size)
                za, zb = max(cz * 16, z0), min(cz * 16 + 16, z0 + size)
                for ly in range(16):
                    y = sy + ly
                    if Y_MIN <= y < Y_MAX:
                        blocks[xa - x0:xb - x0, y - Y_MIN, za - z0:zb - z0] = \
                            code[ly][za - cz * 16:zb - cz * 16, xa - cx * 16:xb - cx * 16].T
    return blocks


def classify_block(block: str) -> int:
    name = block.split(":", 1)[1]
    if "glass" in name and "pane" not in name:
        return 1
    if name in ("air", "light"):
        return 2
    if name == "water":
        return 3
    return 4 if name in GROUND else 0


def fit_sphere(blocks: np.ndarray, origin: np.ndarray) -> tuple[np.ndarray, float]:
    points = np.argwhere(blocks == 1)
    points = points[points[:, 1] + Y_MIN >= 0] + origin + 0.5
    for _ in range(2):
        a = np.c_[2 * points, np.ones(len(points))]
        solution = np.linalg.lstsq(a, (points ** 2).sum(1), rcond=None)[0]
        centre = solution[:3]
        radius = float(np.sqrt(solution[3] + centre @ centre))
        points = points[np.abs(np.linalg.norm(points - centre, axis=1) - radius) < 4]
    return centre, radius


def touching(mask: np.ndarray) -> np.ndarray:
    """Cells with a face neighbour in mask."""
    padded = np.pad(mask, 1)
    return (padded[2:, 1:-1, 1:-1] | padded[:-2, 1:-1, 1:-1] | padded[1:-1, 2:, 1:-1]
            | padded[1:-1, :-2, 1:-1] | padded[1:-1, 1:-1, 2:] | padded[1:-1, 1:-1, :-2])


def open_to_sea(blocks: np.ndarray) -> np.ndarray:
    """Cells with nothing but water between them and the top of the box."""
    water = blocks == 3
    return np.flip(np.logical_and.accumulate(np.flip(water, 1), 1), 1)


def check_dome(region: Region, gx: int, gz: int) -> dict:
    origin = np.array([gx - WINDOW, Y_MIN, gz - WINDOW])
    blocks = load(region, gx - WINDOW, gz - WINDOW, 2 * WINDOW)
    # Tunnels bring plenty of glass too, but they stay below y 0 while a dome rises far above.
    if (blocks[:, -Y_MIN:, :] == 1).sum() < 5000:
        return {"dome": [gx, gz], "present": False}
    centre, radius = fit_sphere(blocks, origin)

    n = 4000
    k = np.arange(n) + 0.5
    phi, theta = np.arccos(1 - k / n), np.pi * (1 + 5 ** 0.5) * k
    directions = np.c_[np.sin(phi) * np.cos(theta), np.cos(phi), np.sin(phi) * np.sin(theta)]
    directions = directions[directions[:, 1] > np.sin(np.radians(8))]
    missing = 0
    for d in directions:
        cells = ((centre + np.outer(np.arange(radius - 3, radius + 2, 0.5), d)) - origin).astype(int)
        inside = cells[((cells >= 0) & (cells < blocks.shape)).all(1)]
        missing += not (blocks[tuple(inside.T)] == 1).any()

    x, y, z = np.indices(blocks.shape)
    distance = np.sqrt((x + origin[0] + 0.5 - centre[0]) ** 2 + (y + Y_MIN + 0.5 - centre[1]) ** 2
                       + (z + origin[2] + 0.5 - centre[2]) ** 2)
    in_tunnel = (0 <= x + origin[0] - gx) & (x + origin[0] - gx < TUNNEL_WIDTH) \
        | (0 <= z + origin[2] - gz) & (z + origin[2] - gz < TUNNEL_WIDTH)
    air = blocks == 2
    outside = (distance > radius + 0.7) & (y + Y_MIN < 150)
    air_outside = int((air & outside & ~in_tunnel).sum())
    # Inside the shell air meets water at ponds and fountains, outside it only at a leak.
    leaks = int((air & outside & touching(blocks == 3)).sum())
    horizontal = np.sqrt((x + origin[0] + 0.5 - centre[0]) ** 2 + (z + origin[2] + 0.5 - centre[2]) ** 2)
    # Only around the edge: inside, cellars and pools of the city's buildings hold water. A gap
    # under the floor is open to the sea above; flooded rooms of a buried building are not.
    edge = (horizontal > radius - 2) & (horizontal < radius + 10)
    under_floor = int(((blocks == 3) & open_to_sea(blocks) & (y + Y_MIN < RIM_GROUND.start) & edge).sum())

    rim = []
    # Between the tunnels, which leave the dome at 0, 90, 180 and 270 degrees.
    for angle in np.radians(np.arange(15, 360, 30)):
        column = blocks[int(centre[0] + (radius + 6) * np.cos(angle) - origin[0]), :,
                        int(centre[2] + (radius + 6) * np.sin(angle) - origin[2])]
        ground = np.where(column == 4)[0]
        rim.append(int(ground.max() + Y_MIN) if len(ground) else None)

    shell_missing = missing / len(directions)
    problems = []
    if shell_missing > MAX_SHELL_MISSING:
        problems.append(f"{shell_missing:.1%} of the shell is missing")
    if air_outside > MAX_AIR_OUTSIDE:
        problems.append(f"{air_outside} air blocks in the water outside the shell")
    if leaks > MAX_LEAKS:
        problems.append(f"{leaks} air blocks outside the shell touch the water")
    if under_floor > MAX_WATER_UNDER_FLOOR:
        problems.append(f"{under_floor} water blocks below the floor around the dome")
    if sum(h in RIM_GROUND for h in rim if h is not None) < 10:
        problems.append(f"ground outside the rim is not level with the dome: {rim}")
    return {"dome": [gx, gz], "present": True, "radius": round(radius, 1), "shell_missing": round(shell_missing, 4),
            "air_outside": air_outside, "leaks": leaks, "water_under_floor": under_floor, "rim_ground": rim, "problems": problems}


FALLING_GROUND = {"sand", "red_sand", "gravel", "suspicious_sand", "suspicious_gravel"}


def falls_or_open(block: str) -> int:
    """1 for blocks that fall when nothing holds them up, 2 for air and water, 0 otherwise."""
    name = block.split(":", 1)[1]
    return 1 if name in FALLING_GROUND else 2 if name in ("air", "water") else 0


def loose_over_water(region: Region) -> int:
    """Sand and gravel in the drowned city with water or air directly below them."""
    x0, z0, size = BETWEEN
    blocks = load(region, x0, z0, size, falls_or_open)
    return int(((blocks[:, 1:, :] == 1) & (blocks[:, :-1, :] == 2)).sum())


def floating_blocks(region: Region) -> int:
    """Solid blocks in the drowned city that do not connect to the sea floor.

    Contact along an edge or a corner counts: coral trees and claws branch out diagonally.
    """
    x0, z0, size = BETWEEN
    blocks = load(region, x0, z0, size)
    solid = (blocks != 2) & (blocks != 3)
    supported = solid.copy()
    supported[:, 1:, :] = False
    while True:
        grow = solid & ~supported & touching_any_way(supported)
        if not grow.any():
            return int((solid & ~supported).sum())
        supported |= grow


def touching_any_way(mask: np.ndarray) -> np.ndarray:
    """Cells with a neighbour in mask through a face, an edge or a corner."""
    padded = np.pad(mask, 1)
    near = np.zeros_like(mask)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if dx or dy or dz:
                    near |= padded[1 + dx:1 + dx + mask.shape[0], 1 + dy:1 + dy + mask.shape[1],
                                   1 + dz:1 + dz + mask.shape[2]]
    return near


def foreign_biomes(region: Region) -> list[str]:
    found = set()
    for cx in range((CENTRE[0] - RADIUS) >> 4, (CENTRE[0] + RADIUS) >> 4, 4):
        for cz in range((CENTRE[1] - RADIUS) >> 4, (CENTRE[1] + RADIUS) >> 4, 4):
            chunk = region.chunk(cx, cz)
            for section in (chunk or {}).get("sections", []):
                found.update(b for b in section.get("biomes", {}).get("palette", []) if not b.startswith("minecraft:"))
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--java", default="java", help="Java 21 for the server")
    parser.add_argument("--skip-generation", action="store_true", help="check the world that is already there")
    parser.add_argument("--seed", help="generate with this seed instead of the boot test's")
    args = parser.parse_args()
    speed, failed = None, []
    if not args.skip_generation:
        if args.seed:
            use_seed(args.seed)
        speed, failed = pregenerate(args.java)
    region = Region(boot_server.SERVER / "world" / "region")
    domes = [check_dome(region, gx, gz) for gx, gz in DOMES]
    biomes = foreign_biomes(region)
    floating = floating_blocks(region)
    loose = loose_over_water(region)
    report = {"domes": domes, "foreign_biomes": biomes, "floating_blocks": floating, "loose_over_water": loose,
              "chunks_per_second": round(speed, 1) if speed else None}
    (boot_server.RUN / "worldgen-report.json").write_text(json.dumps(report, indent=2) + "\n")

    failures = [f"dome at {d['dome']}: {p}" for d in domes for p in d.get("problems", [])]
    if failed:
        failures.append(f"{len(failed)} chunks failed to generate, the first: {failed[0]}")
    if not any(d["present"] for d in domes):
        failures.append("no domes generated in the test area")
    if biomes:
        failures.append(f"biomes from mods in the ocean, Lost Cities skips them: {biomes}")
    if floating > MAX_FLOATING:
        failures.append(f"{floating} blocks float in the water between the domes")
    if loose > MAX_LOOSE_OVER_WATER:
        failures.append(f"{loose} sand or gravel blocks rest on water between the domes, they will fall")
    for d in domes:
        state = "absent" if not d["present"] else (
            f"radius {d['radius']}, shell missing {d['shell_missing']:.1%}, air outside {d['air_outside']}, "
            f"leaks {d['leaks']}, water under floor {d['water_under_floor']}")
        print(f"[worldgen] dome {d['dome']}: {state}")
    print(f"[worldgen] floating blocks between the domes: {floating}, loose ground over water: {loose}")
    if speed:
        print(f"[worldgen] generation: {speed:.0f} chunks a second")
    for failure in failures:
        print(f"[worldgen] FAIL: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
