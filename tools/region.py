"""Read blocks and biomes straight from a world's region files, without running the game."""

from __future__ import annotations

import math
import zlib
from pathlib import Path

import numpy as np

import nbt


class Region:
    """Fully generated chunks of one dimension's region folder."""

    def __init__(self, region_dir: Path):
        self.region_dir = region_dir
        self.files: dict[tuple[int, int], bytes | None] = {}

    def chunk(self, cx: int, cz: int) -> dict | None:
        key = (cx >> 5, cz >> 5)
        if key not in self.files:
            path = self.region_dir / f"r.{key[0]}.{key[1]}.mca"
            self.files[key] = path.read_bytes() if path.is_file() else None
        data = self.files[key]
        if data is None:
            return None
        i = 4 * ((cx & 31) + (cz & 31) * 32)
        offset = int.from_bytes(data[i:i + 3], "big") * 4096
        if offset == 0:
            return None
        length = int.from_bytes(data[offset:offset + 4], "big")
        if data[offset + 4] != 2:
            return None
        try:
            chunk = nbt.read_bytes(zlib.decompress(data[offset + 5:offset + 4 + length]))
        except (zlib.error, ValueError, IndexError):
            return None  # still being written
        return chunk if chunk.get("Status") == "minecraft:full" else None


def section_ids(section: dict) -> tuple[list[str], np.ndarray]:
    """Palette and a 16x16x16 (y, z, x) array of palette indices for one chunk section."""
    states = section.get("block_states", {})
    palette = [p["Name"] for p in states.get("palette", [{"Name": "minecraft:air"}])]
    if len(palette) == 1:
        return palette, np.zeros((16, 16, 16), dtype=np.int32)
    bits = max(4, math.ceil(math.log2(len(palette))))
    per_long = 64 // bits
    words = np.array([w & ((1 << 64) - 1) for w in states["data"]], dtype=np.uint64)
    shifts = np.arange(per_long, dtype=np.uint64) * np.uint64(bits)
    ids = ((words[:, None] >> shifts[None, :]) & np.uint64((1 << bits) - 1)).reshape(-1)[:4096]
    return palette, ids.astype(np.int32).reshape(16, 16, 16)
