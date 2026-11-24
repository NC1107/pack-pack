"""Turn vanilla plains village houses into a Lost Cities city style, so some domes are villages.

Lost Cities builds cities from "parts": 16x16 grids of characters, one string list per
block layer, resolved through a palette. Each vanilla house becomes one building made of
a 6-layer floor part plus a roof part, with its own palette. Villages only appear where
the dome profile's world style picks this city style.
"""

from __future__ import annotations

import gzip
import json
import zipfile
from pathlib import Path

import nbt

NAMESPACE_DIR = Path("data/lostcities/lostcities")
PREFIX = "packpack_village"
FLOOR_HEIGHT = 6  # Lost Cities floors are 6 blocks tall
HOUSES_PATH = "data/minecraft/structure/village/plains/houses/"
# Palette characters for house blocks. Lost Cities' own palettes use ASCII, so these
# never collide with a street, glass or rubble character from the style underneath.
CHAR_POOL = [chr(c) for c in range(0x00C0, 0x0250) if chr(c).isalpha()]

# Street and ground roles of the village style, by the characters Lost Cities' city styles
# assign to them (citystyle_common: street S, base b, variant B, border y, wall w,
# park elevation x), plus our own filler and rubble.
VILLAGE_PALETTE = [
    {"char": "S", "block": "minecraft:dirt_path"},
    {"char": "B", "block": "minecraft:coarse_dirt"},
    {"char": "b", "block": "minecraft:dirt"},
    {"char": "y", "block": "minecraft:grass_block"},
    {"char": "w", "block": "minecraft:oak_fence"},
    {"char": "x", "block": "minecraft:grass_block"},
    {"char": "Ʒ", "block": "minecraft:dirt"},          # building filler below a house
    {"char": "Ƹ", "block": "minecraft:coarse_dirt"},   # rubble
]
FILLER, RUBBLE = "Ʒ", "Ƹ"

LIGHTS = ("torch", "wall_torch", "lantern", "soul_lantern", "soul_torch", "soul_wall_torch")

# One villager per house, once: a trial spawner spawns its total and then waits out its
# cooldown, and this cooldown is ~3.4 years of game time. Drowned houses must never end up
# with a live villager, so every spawned villager starts tagged; a tick function removes a
# tagged villager that is in water (the spawner then sees it gone and goes on cooldown)
# and untags the rest, which leaves villagers players move around alone.
NEW_VILLAGER_TAG = "packpack_new_villager"
VILLAGER_SPAWNER = {
    "block": "minecraft:trial_spawner",
    "tag": {
        "required_player_range": 12,
        "target_cooldown_length": 2147483647,
        **{config: {
            "spawn_range": 2,
            "total_mobs": 1.0,
            "simultaneous_mobs": 1.0,
            "total_mobs_added_per_player": 0.0,
            "simultaneous_mobs_added_per_player": 0.0,
            "ticks_between_spawn": 20,
            "spawn_potentials": [{"weight": 1, "data": {
                "entity": {"id": "minecraft:villager", "Tags": [NEW_VILLAGER_TAG]},
            }}],
            "loot_tables_to_eject": [],
        } for config in ("normal_config", "ominous_config")},
    },
}


def block_string(entry: dict) -> str:
    props = entry.get("Properties")
    if not props:
        return entry["Name"]
    return entry["Name"] + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"


def house_blocks(template: dict) -> tuple[tuple, dict]:
    """Size and a {(x, y, z): palette entry} map, with jigsaws resolved to their final block."""
    palette = template["palette"]
    blocks = {}
    for block in template["blocks"]:
        state = palette[block["state"]]
        name = state["Name"]
        if name == "minecraft:structure_void":
            continue
        if name == "minecraft:jigsaw":
            final = block.get("nbt", {}).get("final_state", "minecraft:air")
            entry = {"block": final}
        elif name in ("minecraft:chest", "minecraft:barrel"):
            entry = {"block": block_string(state), "loot": "chestloot"}
        elif name.split(":")[1] in LIGHTS:
            entry = {"block": block_string(state), "torch": True}
        else:
            entry = {"block": block_string(state)}
        if entry["block"] != "minecraft:air":
            blocks[tuple(block["pos"])] = entry
    size = tuple(template["size"])
    spot = villager_spot(size, blocks)
    if spot:
        blocks[spot] = VILLAGER_SPAWNER
    return size, blocks


def villager_spot(size: tuple, blocks: dict) -> tuple | None:
    """A floor block with two blocks of air above it, next to a bed if the house has one."""
    sx, _, sz = size
    def open_floor(x, z):
        return (x, 0, z) in blocks and (x, 1, z) not in blocks and (x, 2, z) not in blocks
    beds = [(x, z) for (x, y, z), e in blocks.items() if y == 1 and "_bed" in e.get("block", "")]
    targets = beds or [(sx // 2, sz // 2)]
    candidates = [(x, z) for x in range(1, sx - 1) for z in range(1, sz - 1) if open_floor(x, z)]
    if not candidates:
        return None
    x, z = min(candidates, key=lambda c: min(abs(c[0] - bx) + abs(c[1] - bz) for bx, bz in targets))
    return (x, 0, z)


def to_parts(name: str, size: tuple, blocks: dict) -> list[dict]:
    sx, sy, sz = size
    ox, oz = (16 - sx) // 2, (16 - sz) // 2
    chars: dict[str, str] = {}
    palette = []

    def char_for(entry: dict) -> str:
        key = json.dumps(entry, sort_keys=True)
        if key not in chars:
            chars[key] = CHAR_POOL[len(chars)]
            palette.append({"char": chars[key], **entry})
        return chars[key]

    layers = []
    for y in range(max(sy, FLOOR_HEIGHT + 1)):
        rows = []
        for z in range(16):
            row = []
            for x in range(16):
                entry = blocks.get((x - ox, y, z - oz)) if 0 <= x - ox < sx and 0 <= z - oz < sz else None
                row.append(char_for(entry) if entry else " ")
            rows.append("".join(row))
        layers.append(rows)
    local = {"palette": palette}
    return [
        {"name": f"{name}_floor", "xsize": 16, "zsize": 16, "slices": layers[:FLOOR_HEIGHT], "palette": local},
        {"name": f"{name}_roof", "xsize": 16, "zsize": 16, "slices": layers[FLOOR_HEIGHT:], "palette": local},
    ]


def build(datapack: Path, vanilla_jar: Path, lost_cities_jar: Path, village_factor: float,
          city_factor: float) -> str:
    """Write the village assets into the datapack and return the dome world style's name."""
    out = datapack / NAMESPACE_DIR
    buildings = []
    with zipfile.ZipFile(vanilla_jar) as jar:
        houses = sorted(n for n in jar.namelist() if n.startswith(HOUSES_PATH) and n.endswith(".nbt"))
        for path in houses:
            template = nbt.read_bytes(gzip.decompress(jar.read(path)))
            size, blocks = house_blocks(template)
            if size[0] > 16 or size[2] > 16:
                continue
            name = f"{PREFIX}_{Path(path).stem}"
            floor, roof = to_parts(name, size, blocks)
            for part in (floor, roof):
                part_name = part.pop("name")
                (out / "parts").mkdir(parents=True, exist_ok=True)
                (out / "parts" / f"{part_name}.json").write_text(json.dumps(part, ensure_ascii=False) + "\n")
            (out / "buildings").mkdir(parents=True, exist_ok=True)
            (out / "buildings" / f"{name}.json").write_text(json.dumps({
                "filler": FILLER, "rubble": RUBBLE,
                "parts": [{"top": False, "part": f"{name}_floor"}, {"top": True, "part": f"{name}_roof"}],
            }) + "\n")
            buildings.append(name)

    with zipfile.ZipFile(lost_cities_jar) as jar:
        def lc(path: str) -> dict:
            return json.loads(jar.read(f"data/lostcities/lostcities/{path}.json"))
        standard_style, common = lc("styles/standard"), lc("citystyles/citystyle_common")
        world_style = lc("worldstyles/standard_everywhere")

    (out / "palettes").mkdir(parents=True, exist_ok=True)
    (out / "palettes" / f"{PREFIX}.json").write_text(json.dumps({"palette": VILLAGE_PALETTE}, ensure_ascii=False) + "\n")
    (out / "styles").mkdir(parents=True, exist_ok=True)
    # The standard palettes stay underneath so shared parts (stairs, parks) still find
    # every character they use; the village palette goes last and wins for streets.
    (out / "styles" / f"{PREFIX}.json").write_text(json.dumps({"randompalettes": [
        *standard_style["randompalettes"],
        [{"factor": 1.0, "palette": PREFIX}],
    ]}) + "\n")
    (out / "citystyles").mkdir(parents=True, exist_ok=True)
    # The world style asks every city area for at least one multi-chunk building, so a
    # village gets a 2x2 cluster of its own houses.
    (out / "multibuildings").mkdir(parents=True, exist_ok=True)
    cluster = f"{PREFIX}_cluster"
    (out / "multibuildings" / f"{cluster}.json").write_text(json.dumps({
        "dimx": 2, "dimz": 2, "buildings": [buildings[0:2], buildings[2:4]],
    }) + "\n")

    # Inheriting citystyle_common would merge its city buildings, fronts and fountains
    # into the village, so copy only the block roles and the selectors a village keeps.
    keep = ("stairs", "parks", "bridges", "largebridges")
    (out / "citystyles" / f"citystyle_{PREFIX}.json").write_text(json.dumps({
        "style": PREFIX,
        "inherit": "citystyle_config",
        **{k: common[k] for k in ("stuff_tags", "streetblocks", "parkblocks", "corridorblocks", "railblocks", "sphereblocks")},
        "buildingsettings": {"minfloors": 1, "maxfloors": 1, "mincellars": 0, "maxcellars": 0, "buildingchance": 0.6},
        "selectors": {
            "buildings": [{"factor": 1.0, "value": b} for b in buildings],
            "multibuildings": [{"factor": 1.0, "value": cluster}],
            **{k: common["selectors"][k] for k in keep},
        },
    }) + "\n")

    # Domes get their own world style: the standard one plus a rare village city style.
    style = world_style
    style["citystyles"] = [
        {"factor": city_factor, "citystyle": "citystyle_standard"},
        {"factor": village_factor, "citystyle": f"citystyle_{PREFIX}"},
    ]
    (out / "worldstyles").mkdir(parents=True, exist_ok=True)
    functions = datapack / "data/packpack/function"
    functions.mkdir(parents=True, exist_ok=True)
    (functions / "settle_new_villagers.mcfunction").write_text("\n".join([
        f"execute as @e[type=minecraft:villager,tag={NEW_VILLAGER_TAG}] at @s if block ~ ~ ~ minecraft:water run kill @s",
        f"tag @e[type=minecraft:villager,tag={NEW_VILLAGER_TAG}] remove {NEW_VILLAGER_TAG}",
    ]) + "\n")
    tick = datapack / "data/minecraft/tags/function/tick.json"
    tick.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(tick.read_text())["values"] if tick.is_file() else []
    tick.write_text(json.dumps({"values": [*existing, "packpack:settle_new_villagers"]}) + "\n")

    name = "packpack_domes"
    (out / "worldstyles" / f"{name}.json").write_text(json.dumps(style) + "\n")
    return name
