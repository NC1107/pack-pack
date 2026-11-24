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

# Everything is placed relative to the sea floor. Lost Worlds puts its ocean floor at
# y=-15 plus a little noise (hardcoded), so that is the reference: dome floors, Lost
# Cities' ground level and city levels all sit on it. With the sea surface at 160 that
# is ~175 blocks of water above the floor and ~50 blocks of rock below it.
SEABED_Y = -15
SEA_LEVEL = 160

# Ocean variant per temperature band. Low continentalness is where vanilla puts its
# ocean basins, so those get the deep variants and former land gets the shallow ones.
# Warm ocean is the only biome with coral reefs, so it gets the widest band.
TEMPERATURE_BANDS = [
    ((-1.0, -0.45), "deep_frozen_ocean", "frozen_ocean"),
    ((-0.45, -0.2), "deep_cold_ocean", "cold_ocean"),
    ((-0.2, 0.0), "deep_ocean", "ocean"),
    ((0.0, 0.2), "deep_lukewarm_ocean", "lukewarm_ocean"),
    ((0.2, 1.0), "warm_ocean", "warm_ocean"),  # vanilla has no deep warm ocean
]

# Lost Worlds builds the sea floor outside domes as bare stone (it skips vanilla's surface
# rules there), so ocean biomes get a sand or gravel cover laid over it as a feature.
SEABED_COVER = {
    "sand": ["warm_ocean", "lukewarm_ocean", "deep_lukewarm_ocean"],
    "mixed": ["ocean", "deep_ocean"],
    "gravel": ["cold_ocean", "deep_cold_ocean", "frozen_ocean", "deep_frozen_ocean"],
}
DEEP_BELOW_CONTINENTALNESS = -0.3

# No cities within this many blocks of spawn, full city chance again past the second.
CITY_FREE_RADIUS = 500
CITY_FULL_RADIUS = 600

# Every new player starts in a small glass sphere on the sea floor at 0,0. It is a Lost
# Cities predefined sphere, so the glass and the dry floor are part of world generation.
# Its centre sits on a chunk corner because Lost Worlds only builds a sphere into a chunk
# when one of the chunk's corners is inside it.
START_SPHERE = "start"
START_SPHERE_RADIUS = 7
START_SPHERE_CENTER = (0, 0)
# No buildings in the chunks around the start sphere (Lost Cities measures from each
# chunk's corner, so this covers the four chunks that meet at 0,0).
START_CLEAR_RADIUS = 32

# Domes sit this far above the sea floor, so their glass base is not buried in it. Lost
# Cities centres every dome on one ground level, so this raises all domes, not just the start.
DOME_RAISE = 2

# Terrain only exists inside domes (Lost Worlds makes its own seabed outside them). Inside
# a dome it is a flat floor level with the sea floor, so domes sit on the bottom like a
# city that survived the water rising.
DOME_FLOOR_Y = SEABED_Y + DOME_RAISE
# Lost Cities can put a dome every 32 chunks (512 blocks) instead of every 16.
DOME_GRID_32 = True

# Vanilla only spawns fish, squid and dolphins in the top 13 blocks of water, and they
# despawn when no player is within 128 blocks, so nothing swims near the sea floor.
# In Control's spawner spawns each biome's own water mobs around players at any depth.
INCONTROL_SPAWNER = REPO / "pack" / "config" / "incontrol" / "spawner.json"

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
    # Vanilla searches for a spawn point in climate that suits land, which in this world
    # lands anywhere and generates 121 chunks there. Any climate will do: the start
    # function moves the spawn into the start sphere before the first player joins.
    noise["spawn_target"] = [{
        "temperature": FULL, "humidity": FULL, "continentalness": FULL, "erosion": FULL,
        "weirdness": FULL, "depth": 0.0, "offset": 0.0,
    }]
    noise["noise_router"]["final_density"] = flat
    noise["noise_router"]["initial_density_without_jaggedness"] = flat
    noise["aquifers_enabled"] = False
    # This sea level only fills air inside domes (Lost Worlds fills the ocean itself), so
    # keep it below every dome floor.
    noise["sea_level"] = -64
    # Vanilla only applies sand, gravel and grass above the "preliminary surface", which the
    # flattened terrain puts far above the sea floor, leaving bare stone and ores there.
    # Apply the same surface rules everywhere.
    noise["surface_rule"]["sequence"] = [
        rule["then_run"] if rule.get("if_true", {}).get("type") == "minecraft:above_preliminary_surface" else rule
        for rule in noise["surface_rule"]["sequence"]
    ]
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

    write_json(DATAPACK / f"data/lostcities/lostcities/predefinedspheres/{START_SPHERE}.json", {
        "dimension": "minecraft:overworld", "chunkx": 0, "chunkz": 0,
        "centerx": START_SPHERE_CENTER[0], "centerz": START_SPHERE_CENTER[1], "radius": START_SPHERE_RADIUS,
    })
    tick = DATAPACK / "data/minecraft/tags/function/tick.json"
    write_json(tick, {"values": write_start_functions()})
    write_seabed_cover()
    lc_villages.write_start_city(DATAPACK, START_SPHERE_CENTER, START_SPHERE_RADIUS)
    return lc_villages.build(DATAPACK, vanilla_jar(), lost_cities_jar(), village_factor, DOME_CITY_FACTOR)


def write_start_functions() -> list[str]:
    """Write the start sphere functions and return the function ids the tick tag must run."""
    functions = DATAPACK / "data/packpack/function"
    functions.mkdir(parents=True, exist_ok=True)
    cx, cz = START_SPHERE_CENTER
    # Load functions run on the server's first tick, before it handles any player login, so
    # the very first player already spawns in the sphere. The chunk does not have to exist
    # yet: the sphere's floor height is fixed by world generation. Only done once, so a
    # spawn moved later by an operator stays where they put it.
    (functions / "start.mcfunction").write_text("\n".join([
        "gamerule spawnRadius 0",
        f"execute unless data storage packpack:start spawn run setworldspawn {cx} {DOME_FLOOR_Y} {cz}",
        "data modify storage packpack:start spawn set value 1b",
    ]) + "\n")
    write_json(DATAPACK / "data/minecraft/tags/function/load.json", {"values": ["packpack:start"]})
    # No light reaches the sea floor, so the start sphere gets one sea lantern in its floor,
    # once it is generated.
    (functions / "light_start_sphere.mcfunction").write_text("\n".join([
        f"setblock {cx} {DOME_FLOOR_Y - 1} {cz} minecraft:sea_lantern",
        "data modify storage packpack:start lit set value 1b",
    ]) + "\n")
    (functions / "start_tick.mcfunction").write_text(
        f"execute unless data storage packpack:start lit if loaded {cx} {DOME_FLOOR_Y} {cz}"
        " run function packpack:light_start_sphere\n")
    return ["packpack:start_tick"]


def disk(block: str, radius: tuple[int, int], half_height: int, target: dict) -> dict:
    return {"type": "minecraft:disk", "config": {
        "state_provider": {"fallback": {"type": "minecraft:simple_state_provider", "state": {"Name": block}}, "rules": []},
        "target": target,
        "radius": {"type": "minecraft:uniform", "min_inclusive": radius[0], "max_inclusive": radius[1]},
        "half_height": half_height,
    }}


def on_seabed(feature: str, count: int, rarity: int = 1) -> dict:
    return {"feature": feature, "placement": [
        {"type": "minecraft:count", "count": count},
        {"type": "minecraft:rarity_filter", "chance": rarity},
        {"type": "minecraft:in_square"},
        {"type": "minecraft:heightmap", "heightmap": "OCEAN_FLOOR_WG"},
        # Only under open water, so dry dome floors keep their grass.
        {"type": "minecraft:block_predicate_filter", "predicate": {"type": "minecraft:matching_fluids", "fluids": "minecraft:water"}},
        {"type": "minecraft:biome"},
    ]}


def write_seabed_cover() -> None:
    # Disks of up to radius 8, ten per chunk, leave well under 1% of the floor uncovered.
    # They run after ores, so ore that was showing on the floor gets covered too.
    bare_floor = {"type": "minecraft:any_of", "predicates": [
        {"type": "minecraft:matching_block_tag", "tag": "minecraft:base_stone_overworld"},
        {"type": "minecraft:matching_block_tag", "tag": "c:ores"},
    ]}
    covered = {"type": "minecraft:matching_blocks", "blocks": ["minecraft:sand", "minecraft:gravel"]}
    worldgen = DATAPACK / "data/packpack/worldgen"
    configured = {
        "seabed_sand": disk("minecraft:sand", (5, 8), 3, bare_floor),
        "seabed_gravel": disk("minecraft:gravel", (5, 8), 3, bare_floor),
        "seabed_gravel_patch": disk("minecraft:gravel", (2, 5), 1, covered),
        "seabed_clay_patch": disk("minecraft:clay", (2, 3), 1, covered),
    }
    # (count per chunk, 1 in how many chunks)
    placed = {
        "seabed_sand": (10, 1), "seabed_gravel": (10, 1), "seabed_gravel_patch": (2, 1), "seabed_clay_patch": (1, 3),
    }
    for name, feature in configured.items():
        write_json(worldgen / "configured_feature" / f"{name}.json", feature)
        write_json(worldgen / "placed_feature" / f"{name}.json", on_seabed(f"packpack:{name}", *placed[name]))
    features = {
        "sand": ["seabed_sand", "seabed_clay_patch"],
        "mixed": ["seabed_sand", "seabed_gravel_patch", "seabed_clay_patch"],
        "gravel": ["seabed_gravel", "seabed_clay_patch"],
    }
    for cover, biomes in SEABED_COVER.items():
        write_json(DATAPACK / f"data/packpack/neoforge/biome_modifier/seabed_{cover}.json", {
            "type": "neoforge:add_features",
            "biomes": [f"minecraft:{b}" for b in biomes],
            "features": [f"packpack:{f}" for f in features[cover]],
            "step": "underground_decoration",
        })


def write_incontrol_spawner() -> None:
    # Spawned 16-48 blocks from a player, inside the 64 blocks where vanilla keeps fish
    # around; caps are per species for the whole world.
    def rule(category: str, per_second: float, amount: tuple[int, int], max_this: int, max_height: int) -> dict:
        return {
            "mobsfrombiome": category,
            "persecond": per_second,
            "attempts": 20,
            "amount": {"minimum": amount[0], "maximum": amount[1], "groupdistance": 4},
            "conditions": {
                "dimension": "minecraft:overworld",
                "inwater": True,
                "norestrictions": True,
                "mindist": 16, "maxdist": 48,
                "minheight": SEABED_Y - 10, "maxheight": max_height,
                "maxthis": max_this,
            },
        }
    write_json(INCONTROL_SPAWNER, [
        rule("water_ambient", 1.0, (3, 6), 40, SEA_LEVEL),           # cod, salmon, tropical fish
        rule("water_creature", 0.2, (1, 3), 12, SEA_LEVEL),          # squid, dolphins
        rule("underground_water_creature", 0.2, (1, 3), 12, SEABED_Y + 60),  # glow squid in the dark
    ])


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
    flooded["lostcity"]["groundLevel"] = SEABED_Y
    flooded["cities"].update({
        **{f"cityLevel{i}Height": SEABED_Y + 8 * i for i in range(8)},
        "cityMinHeight": SEABED_Y - 20, "cityMaxHeight": SEABED_Y + 90,
    })
    # Highways ran past the domes instead of into them; domes connect by monorail instead.
    flooded["lostcity"]["highwayDistanceMask"] = 0
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
    for key in ("cityThreshold", "cityMaxRadius"):
        domes["cities"][key] = biosphere[key]
    # Every dome is a city: biosphere leaves 20% of them as empty lawn.
    domes["cities"]["cityChance"] = 1.0
    domes["cities"].update({
        "citySpawnDistance1": START_CLEAR_RADIUS, "citySpawnMultiplier1": 0.0,
        "citySpawnDistance2": START_CLEAR_RADIUS + 16, "citySpawnMultiplier2": 1.0,
    })
    domes["cities"].update({f"cityLevel{i}Height": DOME_FLOOR_Y + 6 * i for i in range(8)})
    # Lights in dome buildings keep their torches (and let dome villagers spawn); more
    # lots become buildings instead of lawn.
    domes["lostcity"].update({"generateLighting": True, "buildingChance": 0.6, "parkChance": 0.1})
    domes["lostcity"].update({
        # "space" is Lost Cities' floating-domes landscape. It is the only one that links
        # domes with monorails; Lost Worlds still builds the sea and floor around them.
        "landscapeType": "space",
        # Water inside a dome only fills up to this profile's sea level, so keep it well
        # below the floor (and any cellars).
        "seaLevel": DOME_FLOOR_Y - 40,
        "groundLevel": DOME_FLOOR_Y,
        "description": "pack-pack: domed cities on the sea floor, drowned cities between them",
        "worldStyle": dome_world_style,
    })
    domes["cityspheres"].update({
        "outsideProfile": "waterworld",
        "citySphereChance": 0.5,
        # Every pair of neighbouring domes is linked by a glass monorail tube.
        "monorailChance": 1.0,
        # Clearing above a dome carves air unless the generator reports an outer sea level,
        # which only Lost Worlds' generator does, so leave the water above domes alone.
        "citySphereClearAbove": 0,
        "citySphereClearAboveUntilAir": False,
        "grid32": DOME_GRID_32,
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
    write_incontrol_spawner()
    mode = " (village preview)" if args.preview_villages else ""
    print(f"sea level {SEA_LEVEL}{mode}: {DATAPACK.relative_to(REPO)} and profiles in {PROFILES_OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
