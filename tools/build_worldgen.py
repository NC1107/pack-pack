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
import collections
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

# Every new player starts under a one block thick glass half dome resting on the sea floor
# at 0,0. It is built by a function once the chunks under it exist, because Lost Cities'
# own spheres are whole spheres that cut a pit into the floor.
START_DOME_RADIUS = 7

# Domes sit this far above the sea floor, so their glass base is not buried in it. Lost
# Cities centres every dome on one ground level, so this raises all domes, not just the start.
DOME_RAISE = 2

# Terrain only exists inside domes (Lost Worlds makes its own seabed outside them). Inside
# a dome it is a flat floor level with the sea floor, so domes sit on the bottom like a
# city that survived the water rising.
DOME_FLOOR_Y = SEABED_Y + DOME_RAISE
# Lost Cities can put a dome every 32 chunks (512 blocks) instead of every 16.
DOME_GRID_32 = False
# City radius in blocks and the fraction of it that becomes the dome radius (60 to 72).
DOME_CITY_RADIUS = (100, 120)
DOME_SPHERE_FACTOR = 0.6

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
    # Nothing to mine: the ground is sand (Lost Worlds puts 30 blocks of it under the sea floor,
    # then bedrock), so there is no ore and nothing to carve into around domes. The deepslate
    # rule would turn dome ground back into rock.
    noise["default_block"] = {"Name": "minecraft:sand"}
    noise["surface_rule"]["sequence"] = [
        rule for rule in noise["surface_rule"]["sequence"]
        if rule.get("if_true", {}).get("random_name") != "minecraft:deepslate"
    ]
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

    tick = DATAPACK / "data/minecraft/tags/function/tick.json"
    write_json(tick, {"values": write_start_functions()})
    write_seabed_cover()
    write_structure_overrides()
    write_ocean_biomes()
    write_structure_set_filters()
    return lc_villages.build(DATAPACK, vanilla_jar(), lost_cities_jar(), village_factor, DOME_CITY_FACTOR)


def dome_cells(radius: int) -> tuple[list, list, list]:
    """Floor, shell and interior cells (x, y, z) of a half dome centred on x=0, z=0.

    The shell is every cell inside the sphere with a face-neighbour outside it, which is
    exactly one block thick and watertight.
    """
    def inside(x, y, z):
        return y >= 0 and x * x + y * y + z * z <= radius * radius
    floor, shell, interior = [], [], []
    for y in range(0, radius + 1):
        for x in range(-radius, radius + 1):
            for z in range(-radius, radius + 1):
                if not inside(x, y, z):
                    continue
                if y == 0:
                    floor.append((x, y, z))
                elif any(not inside(x + dx, y + dy, z + dz)
                         for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1))):
                    shell.append((x, y, z))
                else:
                    interior.append((x, y, z))
    return floor, shell, interior


def fill_runs(cells: list, block: str) -> list[str]:
    """One fill command per run of cells along z."""
    lines, run = [], None
    for x, y, z in sorted(cells):
        if run and run[0] == (x, y) and run[2] == z - 1:
            run[2] = z
            continue
        if run:
            lines.append(f"fill ~{run[0][0]} ~{run[0][1]} ~{run[1]} ~{run[0][0]} ~{run[0][1]} ~{run[2]} {block}")
        run = [(x, y), z, z]
    if run:
        lines.append(f"fill ~{run[0][0]} ~{run[0][1]} ~{run[1]} ~{run[0][0]} ~{run[0][1]} ~{run[2]} {block}")
    return lines


def write_start_functions() -> list[str]:
    """Write the start dome functions and return the function ids the tick tag must run."""
    functions = DATAPACK / "data/packpack/function"
    functions.mkdir(parents=True, exist_ok=True)
    r = START_DOME_RADIUS
    floor, shell, interior = dome_cells(r)
    lights = [(0, 0, 0), (3, 0, 0), (-3, 0, 0), (0, 0, 3), (0, 0, -3)]
    # No light reaches the sea floor, so sea lanterns in the floor keep mobs from spawning inside.
    build = [
        *fill_runs(interior, "minecraft:air"),
        *fill_runs(floor, "minecraft:grass_block"),
        *fill_runs(shell, "minecraft:glass"),
        *[f"setblock ~{x} ~{y} ~{z} minecraft:sea_lantern" for x, y, z in lights],
        "setworldspawn ~ ~1 ~",
        "summon minecraft:marker ~ ~1 ~ {Tags:[\"packpack_dome\"]}",
        "execute store result storage packpack:start y int 1 run data get entity"
        " @e[type=minecraft:marker,tag=packpack_dome,limit=1] Pos[1]",
        "kill @e[type=minecraft:marker,tag=packpack_dome]",
        "data modify storage packpack:start built set value 1b",
        "forceload remove -8 -8 8 8",
    ]
    (functions / "build_start_dome.mcfunction").write_text("\n".join(build) + "\n")
    # In a new world the load tag runs before the chunks under spawn exist, so the dome is
    # built from the tick tag instead: force-load the four chunks around 0,0, wait until
    # they are loaded, then build once at the real sea floor (a storage flag keeps it from
    # ever overwriting player changes) and move anyone who already joined into it.
    corners = " ".join(f"if loaded {x} 0 {z}" for x in (-8, 8) for z in (-8, 8))
    (functions / "start_tick.mcfunction").write_text("\n".join([
        "execute unless data storage packpack:start built run forceload add -8 -8 8 8",
        f"execute unless data storage packpack:start built positioned 0 0 0 {corners}"
        " positioned over ocean_floor run function packpack:build_start_dome",
        "execute if data storage packpack:start built as @a[tag=!packpack_started]"
        " run function packpack:place_new_player with storage packpack:start",
    ]) + "\n")
    (functions / "place_new_player.mcfunction").write_text("\n".join([
        "$tp @s 0.5 $(y) 0.5",
        "give @s ftbquests:book",
        "tag @s add packpack_started",
    ]) + "\n")
    (functions / "start.mcfunction").write_text("gamerule spawnRadius 0\n")
    write_json(DATAPACK / "data/minecraft/tags/function/load.json", {"values": ["packpack:start"]})
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


# Vanilla structures that generate in the rock below the sea floor. With the floor only
# 50 blocks above bedrock their tops stick out of it, so they are switched off. Strongholds
# stay: they are the only way to the End.
DISABLED_STRUCTURE_SETS = ["trial_chambers", "mineshafts"]


def write_structure_overrides() -> None:
    for name in DISABLED_STRUCTURE_SETS:
        structure_set = vanilla(f"data/minecraft/worldgen/structure_set/{name}.json")
        structure_set["structures"] = []
        write_json(DATAPACK / f"data/minecraft/worldgen/structure_set/{name}.json", structure_set)


# Colour of the water far away, which is also what shows beyond the last loaded chunk.
# Vanilla ocean sky and fog are the bright overworld blue.
DEEP_WATER_COLOR = 0x061a3a


def write_ocean_biomes() -> None:
    """Override the vanilla ocean biomes: no caves, and sky and fog the colour of deep water."""
    ocean_biomes = sorted({b for _, deep, shallow in TEMPERATURE_BANDS for b in (deep, shallow)})
    for name in ocean_biomes:
        biome = vanilla(f"data/minecraft/worldgen/biome/{name}.json")
        # Carvers cut air pockets into the water column because the aquifers are switched off.
        biome["carvers"] = {}
        biome["effects"]["sky_color"] = DEEP_WATER_COLOR
        biome["effects"]["fog_color"] = DEEP_WATER_COLOR
        # Vanilla ocean water fog is almost black, which hides everything past a few chunks.
        write_json(DATAPACK / f"data/minecraft/worldgen/biome/{name}.json", biome)


# Structures dropped from mod structure sets. The sea dragon skeletons are long serpents that
# cut through domes and hang in the middle of the water.
REMOVED_STRUCTURES = {"mos:sea_dragon_skeleton", "mos:dragon_skeleton"}


def write_structure_set_filters() -> None:
    for jar in sorted((SERVER / "mods").glob("*.jar")):
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if "/worldgen/structure_set/" not in name or not name.endswith(".json"):
                    continue
                structure_set = json.loads(z.read(name))
                kept = [e for e in structure_set["structures"] if e["structure"] not in REMOVED_STRUCTURES]
                if len(kept) != len(structure_set["structures"]):
                    structure_set["structures"] = kept
                    write_json(DATAPACK / name, structure_set)


def write_seabed_cover() -> None:
    # Disks of up to radius 8, ten per chunk, leave well under 1% of the floor uncovered.
    # They run after ores, so ore that was showing on the floor gets covered too.
    sand = {"type": "minecraft:matching_blocks", "blocks": "minecraft:sand"}
    covered = {"type": "minecraft:matching_blocks", "blocks": ["minecraft:sand", "minecraft:gravel"]}
    worldgen = DATAPACK / "data/packpack/worldgen"
    configured = {
        "seabed_gravel": disk("minecraft:gravel", (5, 8), 3, sand),
        "seabed_gravel_patch": disk("minecraft:gravel", (2, 5), 1, covered),
        "seabed_clay_patch": disk("minecraft:clay", (2, 3), 1, covered),
    }
    # (count per chunk, 1 in how many chunks)
    placed = {
        "seabed_gravel": (10, 1), "seabed_gravel_patch": (2, 1), "seabed_clay_patch": (1, 3),
    }
    for name, feature in configured.items():
        write_json(worldgen / "configured_feature" / f"{name}.json", feature)
        write_json(worldgen / "placed_feature" / f"{name}.json", on_seabed(f"packpack:{name}", *placed[name]))
    features = {
        "sand": ["seabed_clay_patch"],
        "mixed": ["seabed_gravel_patch", "seabed_clay_patch"],
        "gravel": ["seabed_gravel", "seabed_clay_patch"],
    }
    for cover, biomes in SEABED_COVER.items():
        write_json(DATAPACK / f"data/packpack/neoforge/biome_modifier/seabed_{cover}.json", {
            "type": "neoforge:add_features",
            "biomes": [f"minecraft:{b}" for b in biomes],
            "features": [f"packpack:{f}" for f in features[cover]],
            "step": "underground_decoration",
        })


BIG_SEA_LIFE = [
    "hybrid_aquatic:orca", "hybrid_aquatic:basking_shark", "hybrid_aquatic:whale_shark",
    "hybrid_aquatic:great_white_shark", "hybrid_aquatic:hammerhead_shark", "hybrid_aquatic:manta_ray",
    "hybrid_aquatic:ocean_sunfish", "hybrid_aquatic:bull_shark", "hybrid_aquatic:thresher_shark",
    "hybrid_aquatic:sand_tiger_shark", "hybrid_aquatic:giant_isopod", "minecraft:dolphin",
]


def write_incontrol_spawner() -> None:
    # Spawned 16-48 blocks from a player, inside the 64 blocks where vanilla keeps fish
    # around; caps are per species for the whole world.
    def rule(category: str | list, per_second: float, amount: tuple[int, int], max_this: int, max_height: int,
             distance: tuple[int, int] = (16, 48)) -> dict:
        return {
            **({"mob": category} if isinstance(category, list) else {"mobsfrombiome": category}),
            "persecond": per_second,
            "attempts": 20,
            "amount": {"minimum": amount[0], "maximum": amount[1], "groupdistance": 4},
            "conditions": {
                "dimension": "minecraft:overworld",
                "inwater": True,
                "norestrictions": True,
                "mindist": distance[0], "maxdist": distance[1],
                "minheight": SEABED_Y - 10, "maxheight": max_height,
                "maxthis": max_this,
            },
        }
    write_json(INCONTROL_SPAWNER, [
        rule("water_ambient", 1.0, (3, 6), 25, SEA_LEVEL),           # cod, salmon, tropical fish
        rule("water_creature", 0.6, (1, 3), 8, SEA_LEVEL),           # squid, sharks, rays, orcas, jellyfish
        rule("underground_water_creature", 0.2, (1, 3), 12, SEABED_Y + 60),  # glow squid in the dark
        # Big animals, a few at a time, far enough out to see them whole
        rule(BIG_SEA_LIFE, 0.25, (1, 1), 3, SEA_LEVEL - 20, distance=(32, 96)),
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
        # Drowned cities only on the low plains: not on ridges, seamounts or in trenches.
        "cityMinHeight": SEABED_Y - 20, "cityMaxHeight": SEABED_Y + 12,
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
    domes["cities"]["cityThreshold"] = biosphere["cityThreshold"]
    # A lot is built up with a probability that falls from 1 at the city centre to 0 at the
    # city radius. A dome is as big as its city radius times the sphere factor, so a city
    # radius well past the dome keeps the whole dome built up instead of just its middle.
    domes["cities"].update({"cityMinRadius": DOME_CITY_RADIUS[0], "cityMaxRadius": DOME_CITY_RADIUS[1]})
    # Every dome is a city: biosphere leaves 20% of them as empty lawn.
    domes["cities"]["cityChance"] = 1.0
    # The patched Lost Cities also keeps domes themselves out of the city free radius, so
    # nothing is visible from spawn: players find the first dome by swimming out.
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
        "citySphereChance": 0.8,
        "citySphereFactor": DOME_SPHERE_FACTOR,
        # Every pair of neighbouring domes is linked by a glass monorail tube.
        "monorailChance": 0.9,
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
