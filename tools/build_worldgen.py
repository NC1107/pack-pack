#!/usr/bin/env python3
"""Generate the water world datapack and its matching Lost Cities profile.

    python3 tools/build_worldgen.py [--preview-villages]

Reads vanilla 1.21.1 worldgen files from the server that tools/boot_server.py
installed, so run that once first. Writes:
  pack/datapacks/pack-pack-worldgen/   sea level and all-ocean overworld biomes
  pack/config/lostcities/profiles/waterworld.json and waterworld_domes.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

import lc_villages

REPO = Path(__file__).resolve().parent.parent
SERVER = REPO / "run" / "server"
LOST_CITIES_PROFILES = SERVER / "config" / "lostcities" / "profiles"

DATAPACK = REPO / "pack" / "datapacks" / "pack-pack-worldgen"
PROFILES_OUT = REPO / "pack" / "config" / "lostcities" / "profiles"
DATA_PACK_FORMAT = 48  # Minecraft 1.21.1

# Vanilla terrain mostly sits between 63 and 120, so a waterline this high leaves only
# real mountain peaks above water. Lost Cities builds cities on terrain up to y=150.
SEA_LEVEL = 160

# Ocean variant per temperature band. Low continentalness is where vanilla puts its
# ocean basins, so those get the deep variants and former land gets the shallow ones.
TEMPERATURE_BANDS = [
    ((-1.0, -0.45), "deep_frozen_ocean", "frozen_ocean"),
    ((-0.45, -0.15), "deep_cold_ocean", "cold_ocean"),
    ((-0.15, 0.2), "deep_ocean", "ocean"),
    ((0.2, 0.55), "deep_lukewarm_ocean", "lukewarm_ocean"),
    ((0.55, 1.0), "warm_ocean", "warm_ocean"),  # vanilla has no deep warm ocean
]
DEEP_BELOW_CONTINENTALNESS = -0.3

# No cities within this many blocks of spawn, full city chance again past the second.
CITY_FREE_RADIUS = 500
CITY_FULL_RADIUS = 600

# Every new player starts in a small sealed pod on the sea floor under spawn: outer size
# x, y, z in blocks, so the air pocket inside is two smaller on each axis.
START_POD_SIZE = (6, 5, 6)

# Terrain only exists inside domes (Lost Worlds makes its own seabed outside them), and
# an empty dome should be a dry floor with room above it, not a hill filling the glass.
DOME_FLOOR_Y = 64

# How Lost Cities picks a city style for each domed city: mostly normal cities, sometimes
# a village built from vanilla's plains houses.
DOME_CITY_FACTOR = 0.5
DOME_VILLAGE_FACTOR = 0.06
FULL = [-1.0, 1.0]


def vanilla_jar() -> Path:
    jar = next(SERVER.glob("libraries/net/minecraft/server/1.21.1-*/server-1.21.1-*-extra.jar"), None)
    if jar is None or not (LOST_CITIES_PROFILES / "atlantis.json").is_file():
        raise SystemExit("run tools/boot_server.py once first, it installs the vanilla jar and Lost Cities profiles")
    return jar


def vanilla(path: str) -> dict:
    with zipfile.ZipFile(vanilla_jar()) as jar:
        return json.loads(jar.read(path))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def ocean_biome_source() -> dict:
    biomes = []
    for (t_min, t_max), deep, shallow in TEMPERATURE_BANDS:
        for biome, continentalness in ((deep, [-1.0, DEEP_BELOW_CONTINENTALNESS]),
                                       (shallow, [DEEP_BELOW_CONTINENTALNESS, 1.0])):
            biomes.append({
                "biome": f"minecraft:{biome}",
                "parameters": {
                    "temperature": [t_min, t_max], "humidity": FULL, "continentalness": continentalness,
                    "erosion": FULL, "weirdness": FULL, "depth": FULL, "offset": 0.0,
                },
            })
    return {"type": "minecraft:multi_noise", "biomes": biomes}


def lost_cities_jar() -> Path:
    jar = next((SERVER / "mods").glob("lostcities-*.jar"), None)
    if jar is None:
        raise SystemExit("run tools/boot_server.py once first, it installs Lost Cities")
    return jar


def build_datapack(village_factor: float) -> str:
    if DATAPACK.exists():
        shutil.rmtree(DATAPACK)
    write_json(DATAPACK / "pack.mcmeta", {"pack": {
        "pack_format": DATA_PACK_FORMAT,
        "description": f"pack-pack: domes on an ocean floor, sea level {SEA_LEVEL}",
    }})

    noise = vanilla("data/minecraft/worldgen/noise_settings/overworld.json")
    flat = {"type": "minecraft:y_clamped_gradient", "from_y": DOME_FLOOR_Y - 8, "to_y": DOME_FLOOR_Y + 8,
            "from_value": 1.0, "to_value": -1.0}
    noise["noise_router"]["final_density"] = flat
    noise["noise_router"]["initial_density_without_jaggedness"] = flat
    noise["aquifers_enabled"] = False
    write_json(DATAPACK / "data/minecraft/worldgen/noise_settings/overworld.json", noise)

    # The normal preset is what both new singleplayer worlds and servers use by default.
    # Lost Worlds' spheres generator runs normal terrain only inside Lost Cities' domes and
    # fills everything outside with a seabed and water up to its own sea level. Vanilla's
    # sea level (63) still applies inside the domes, so they stay dry.
    preset = vanilla("data/minecraft/worldgen/world_preset/normal.json")
    preset["dimensions"]["minecraft:overworld"]["generator"] = {
        "type": "lostworlds:lostworlds",
        "lwsettings": {"type": "spheres", "fog": "None", "sea_level": SEA_LEVEL},
        "biome_source": ocean_biome_source(),
        "settings": "minecraft:overworld",
    }
    write_json(DATAPACK / "data/minecraft/worldgen/world_preset/normal.json", preset)

    tick = DATAPACK / "data/minecraft/tags/function/tick.json"
    write_json(tick, {"values": write_start_pod()})
    return lc_villages.build(DATAPACK, vanilla_jar(), lost_cities_jar(), village_factor, DOME_CITY_FACTOR)


def write_start_pod() -> list[str]:
    """Write the start pod functions and return the function ids the tick tag must run."""
    functions = DATAPACK / "data/packpack/function"
    functions.mkdir(parents=True, exist_ok=True)
    sx, sy, sz = START_POD_SIZE
    x0, z0 = -(sx // 2) + 1, -(sz // 2) + 1
    x1, y1, z1 = x0 + sx - 1, sy - 1, z0 + sz - 1
    # In a new singleplayer world the load tag runs before the chunk under spawn exists, so
    # the pod is built from the tick tag instead: force-load that chunk, wait until it is
    # loaded, build once (a storage flag keeps it from ever overwriting player changes).
    (functions / "start_pod_tick.mcfunction").write_text("\n".join([
        "execute unless data storage packpack:start built run forceload add 8 8",
        "execute unless data storage packpack:start built positioned 8 0 8 if loaded ~ ~ ~"
        " positioned over ocean_floor run function packpack:build_start_pod",
        "execute if data storage packpack:start built as @a[tag=!packpack_started]"
        " run function packpack:place_new_player with storage packpack:start",
    ]) + "\n")
    # Runs at the seabed under spawn. "hollow" leaves a sealed air pocket that water
    # cannot get into, and the sea lantern floor lights it so mobs cannot spawn inside.
    (functions / "build_start_pod.mcfunction").write_text("\n".join([
        f"fill ~{x0} ~ ~{z0} ~{x1} ~{y1} ~{z1} minecraft:glass hollow",
        f"fill ~{x0} ~ ~{z0} ~{x1} ~ ~{z1} minecraft:sea_lantern",
        "setworldspawn ~ ~1 ~",
        "summon minecraft:marker ~ ~1 ~ {Tags:[\"packpack_pod\"]}",
        "execute store result storage packpack:start y int 1 run data get entity"
        " @e[type=minecraft:marker,tag=packpack_pod,limit=1] Pos[1]",
        "kill @e[type=minecraft:marker,tag=packpack_pod]",
        "data modify storage packpack:start built set value 1b",
        "forceload remove ~ ~",
    ]) + "\n")
    # Players who joined before the pod existed (a new singleplayer world) start in it too.
    (functions / "place_new_player.mcfunction").write_text("\n".join([
        "$tp @s 8.5 $(y) 8.5",
        "tag @s add packpack_started",
    ]) + "\n")
    (functions / "start.mcfunction").write_text("gamerule spawnRadius 0\n")
    write_json(DATAPACK / "data/minecraft/tags/function/load.json", {"values": ["packpack:start"]})
    return ["packpack:start_pod_tick"]


def read_only_copy(name: str) -> dict:
    profile = json.loads((LOST_CITIES_PROFILES / f"{name}.json").read_text())
    for section in profile.values():
        if isinstance(section, dict):
            section.pop("__readonly__", None)
    profile["lostcity"]["warning"] = ""
    return profile


def build_profiles(dome_world_style: str, city_free_radius: int) -> None:
    # Flooded cities: what generates outside the domes.
    flooded = read_only_copy("atlantis")
    flooded["lostcity"]["seaLevel"] = SEA_LEVEL
    # The standard style cuts city chance to 10% in ocean biomes, which in an all-ocean
    # overworld means almost no cities. standard_everywhere is the same without that.
    flooded["lostcity"]["worldStyle"] = "standard_everywhere"
    flooded["lostcity"]["description"] = f"pack-pack: drowned cities under a sea level of {SEA_LEVEL}"
    # Railways are underground tunnels; with no ground outside the domes they float through
    # open water as a 160-block grid. Domes keep their own monorail links (cityspheres).
    flooded["lostcity"]["railwaysEnabled"] = False
    flooded["cities"].update({
        "citySpawnDistance1": city_free_radius, "citySpawnMultiplier1": 0.0,
        "citySpawnDistance2": city_free_radius + CITY_FULL_RADIUS - CITY_FREE_RADIUS, "citySpawnMultiplier2": 1.0,
    })
    write_json(PROFILES_OUT / "waterworld.json", flooded)

    # Domed cities: dry glass spheres on the sea floor, flooded cities in between.
    domes = json.loads(json.dumps(flooded))
    # City chance, size and level heights from Lost Cities' own domed profile (biosphere),
    # so domes are filled by a city and its levels start near the dome floor.
    biosphere = read_only_copy("biosphere")["cities"]
    for key in ("cityChance", "cityThreshold", "cityMaxRadius", *(f"cityLevel{i}Height" for i in range(8))):
        domes["cities"][key] = biosphere[key]
    # Lights in dome buildings keep their torches (and let dome villagers spawn); more
    # lots become buildings instead of lawn.
    domes["lostcity"].update({"generateLighting": True, "buildingChance": 0.6, "parkChance": 0.1})
    domes["lostcity"].update({
        "landscapeType": "spheres",
        # Water inside a dome only fills up to this profile's sea level, so keep it below the floor.
        "seaLevel": 0,
        "description": "pack-pack: domed cities on the sea floor, drowned cities between them",
        "worldStyle": dome_world_style,
    })
    domes["cityspheres"].update({
        "outsideProfile": "waterworld",
        "citySphereChance": 0.5,
        "monorailChance": 0.8,
        # Clearing above a dome carves air unless the generator reports an outer sea level,
        # which only Lost Worlds' generator does, so leave the water above domes alone.
        "citySphereClearAbove": 0,
        "citySphereClearAboveUntilAir": False,
    })
    write_json(PROFILES_OUT / "waterworld_domes.json", domes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the water world datapack and Lost Cities profiles.")
    parser.add_argument("--preview-villages", action="store_true",
                        help="make every domed city a village and allow cities near spawn, for looking at villages")
    args = parser.parse_args()
    village_factor = 1000.0 if args.preview_villages else DOME_VILLAGE_FACTOR
    city_free_radius = 0 if args.preview_villages else CITY_FREE_RADIUS

    vanilla_jar()
    dome_world_style = build_datapack(village_factor)
    build_profiles(dome_world_style, city_free_radius)
    mode = " (village preview)" if args.preview_villages else ""
    print(f"sea level {SEA_LEVEL}{mode}: {DATAPACK.relative_to(REPO)} and profiles in {PROFILES_OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
