#!/usr/bin/env python3
"""Generate a patch of the ocean world and check the domes in it.

Runs the server installed by boot_server.py with Chunky, pre-generates a square that holds four
domes on Lost Cities' 512 block grid, then reads the region files and checks every dome: the glass
shell is complete, no air touches the water (in the dome or in the tunnels out of it), there is no
other air in the water outside it, and the ground outside the rim is level with the ground inside. It also fails if a mod's biome shows up, since Lost Cities does not
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
# Tunnels leave a dome along the 16 block wide chunk row and column that hold its centre.
TUNNEL_WIDTH = 16
RIM_GROUND = range(-15, -12)


def neoforge_version() -> str:
    return tomllib.loads(boot_server.PACK_TOML.read_text("utf-8"))["versions"]["neoforge"]


def pregenerate(java: str) -> None:
    mods = boot_server.SERVER / "mods"
    jar = mods / "chunky.jar"
    shutil.copy(cached_download(CHUNKY_URL, CHUNKY_SHA256), jar)
    shutil.rmtree(boot_server.SERVER / "world", ignore_errors=True)
    shutil.rmtree(boot_server.SERVER / "config" / "chunky" / "tasks", ignore_errors=True)
    finished = threading.Event()
    try:
        proc = subprocess.Popen(boot_server.server_command(java, neoforge_version()), cwd=boot_server.SERVER,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        assert proc.stdin and proc.stdout
        for line in proc.stdout:
            if boot_server.DONE_LINE.search(line):
                proc.stdin.write(f"chunky world minecraft:overworld\nchunky center {CENTRE[0]} {CENTRE[1]}\n"
                                 f"chunky radius {RADIUS}\nchunky start\n")
                proc.stdin.flush()
            if re.search(r"\[Chunky\] Task (finished|stopped|cancelled)", line) or "Preparing crash report" in line:
                finished.set()
                proc.stdin.write("save-all flush\nstop\n")
                proc.stdin.flush()
        proc.wait(timeout=120)
    finally:
        jar.unlink(missing_ok=True)
    if not finished.is_set():
        raise SystemExit("pre-generation did not finish")


def load(region: Region, x0: int, z0: int, size: int) -> np.ndarray:
    """Block classes in a box: 0 other, 1 glass, 2 air, 3 water, 4 ground."""
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


def classify(block: str) -> int:
    name = block.split(":", 1)[1]
    if "glass" in name and "pane" not in name:
        return 1
    if name == "air":
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


def check_dome(region: Region, gx: int, gz: int) -> dict:
    origin = np.array([gx - WINDOW, Y_MIN, gz - WINDOW])
    blocks = load(region, gx - WINDOW, gz - WINDOW, 2 * WINDOW)
    if (blocks == 1).sum() < 5000:
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

    rim = []
    for angle in np.radians(np.arange(0, 360, 30)):
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
    if sum(h in RIM_GROUND for h in rim if h is not None) < 10:
        problems.append(f"ground outside the rim is not level with the dome: {rim}")
    return {"dome": [gx, gz], "present": True, "radius": round(radius, 1), "shell_missing": round(shell_missing, 4),
            "air_outside": air_outside, "leaks": leaks, "rim_ground": rim, "problems": problems}


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
    args = parser.parse_args()
    if not args.skip_generation:
        pregenerate(args.java)
    region = Region(boot_server.SERVER / "world" / "region")
    domes = [check_dome(region, gx, gz) for gx, gz in DOMES]
    biomes = foreign_biomes(region)
    report = {"domes": domes, "foreign_biomes": biomes}
    (boot_server.RUN / "worldgen-report.json").write_text(json.dumps(report, indent=2) + "\n")

    failures = [f"dome at {d['dome']}: {p}" for d in domes for p in d.get("problems", [])]
    if not any(d["present"] for d in domes):
        failures.append("no domes generated in the test area")
    if biomes:
        failures.append(f"biomes from mods in the ocean, Lost Cities skips them: {biomes}")
    for d in domes:
        state = "absent" if not d["present"] else (
            f"radius {d['radius']}, shell missing {d['shell_missing']:.1%}, air outside {d['air_outside']}, "
            f"leaks {d['leaks']}")
        print(f"[worldgen] dome {d['dome']}: {state}")
    for failure in failures:
        print(f"[worldgen] FAIL: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
