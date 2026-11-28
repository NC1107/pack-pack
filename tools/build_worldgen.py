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
import start_sub

REPO = Path(__file__).resolve().parent.parent
SERVER = REPO / "run" / "server"
LOST_CITIES_PROFILES = SERVER / "config" / "lostcities" / "profiles"

DATAPACK = REPO / "pack" / "datapacks" / "pack-pack-worldgen"
PROFILES_OUT = REPO / "pack" / "config" / "lostcities" / "profiles"
DATA_PACK_FORMAT = 48  # Minecraft 1.21.1

# Everything is placed relative to the sea floor. Lost Worlds puts its ocean floor at
# y=-15 plus a little noise (hardcoded), so that is the reference: dome floors, Lost
# Cities' ground level and city levels all sit on it. The sea surface at 186 puts the floor
# 200 blocks down, an easy number to remember, with ~50 blocks of rock below it.
SEABED_Y = -14
# The deepest trenches of the sea floor (Lost Worlds SeaFloor.MIN)
SEA_FLOOR_MIN_Y = -56
SEA_LEVEL = 186

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

# Every new player starts in a wrecked submarine on the sea floor at 0,0 (tools/start_sub.py).
# It is built by a function once the chunks under it exist.

# Domes sit this far above the sea floor, so their glass base is not buried in it. Lost
# Cities centres every dome on one ground level, so this raises all domes, not just the start.
DOME_RAISE = 1

# Terrain only exists inside domes (Lost Worlds makes its own seabed outside them). Inside
# a dome it is a flat floor level with the sea floor, so domes sit on the bottom like a
# city that survived the water rising.
DOME_FLOOR_Y = SEABED_Y + DOME_RAISE
# A dome every 64 chunks (1024 blocks), with the patched Lost Cities' gridChunks: fewer domes, each
# one worth the trip. The grid sits on chunk (40, 8), so the nearest dome is ~660 blocks east of
# spawn (648, 136) and always there; the one at chunk x -24 falls inside the empty ring around spawn.
# Sphere centres must be 8 mod 16 chunks, Lost Cities looks spheres up by 16 chunk cells.
DOME_GRID_CHUNKS = 64
DOME_GRID_OFFSET = (40, 8)
# City radius in blocks and the fraction of it that becomes the dome radius (62 to 74 with the
# patched Lost Cities; upstream only scaled the random part, which made domes 100+ blocks wide).
DOME_CITY_RADIUS = (100, 120)
DOME_SPHERE_FACTOR = 0.62

# Vanilla only spawns fish, squid and dolphins in the top 13 blocks of water, and they
# despawn when no player is within 128 blocks, so nothing swims near the sea floor.
# In Control's spawner spawns each biome's own water mobs around players at any depth.
INCONTROL_SPAWNER = REPO / "pack" / "config" / "incontrol" / "spawner.json"

# How Lost Cities picks a city style for each domed city: mostly normal cities, about one
# dome in four a village built from vanilla's plains houses (domes are 1024 blocks apart).
DOME_CITY_FACTOR = 0.5
DOME_VILLAGE_FACTOR = 0.17
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
    write_underwater_air_filters()
    write_disabled_mod_modifiers()
    write_hapi_spawns()
    write_cold_water_spawns()
    write_entity_tags()
    return lc_villages.build(DATAPACK, vanilla_jar(), lost_cities_jar(), village_factor, DOME_CITY_FACTOR)


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


# A small working submarine for learning how Create, Aeronautics and Deep Seas fit together,
# built near the surface (hulls implode deep down) and assembled into a ship by Sable.
# Run with /function packpack:test_sub (needs cheats). Levers sit on top of the clutch and
# gearshift: a powered clutch disconnects, a powered gearshift reverses.
PORTHOLE_GLASS = "create_submarine:iron_pressurizer"
TEST_SUB = [
    # Cut copper: normal weight and good to about 85 m. Iron blocks count as storage blocks,
    # which Sable makes four times heavier, and the iron hull sank whatever the ballast did.
    "fill ~0 ~0 ~0 ~10 ~4 ~4 minecraft:waxed_cut_copper hollow",
    # Portholes of Deep Seas' pressurized glass: plain glass gives way at about 28 m.
    *[f"setblock ~{x} ~2 ~{z} {PORTHOLE_GLASS}" for x, z in ((3, 0), (5, 0), (8, 0), (2, 4), (8, 4))],
    f"setblock ~10 ~2 ~2 {PORTHOLE_GLASS}",
    # Stern: creative motor -> clutch (stop/go) -> gearshift (forward/reverse) -> shaft through the
    # hull -> a 3x3 of propellers outside, which merge into one 81 times stronger. Centred on the
    # hull so it pushes straight; at 64 RPM it cruises at about 8 to 10 blocks a second (a single
    # propeller at 256 RPM managed about 1, a 2x2 off centre spun the sub around).
    "setblock ~3 ~2 ~2 create:creative_motor[facing=west]{ScrollValue:64}",
    "setblock ~2 ~2 ~2 create:clutch[axis=x,powered=true]",
    "setblock ~2 ~3 ~2 minecraft:lever[face=floor,facing=north,powered=true]",
    "setblock ~1 ~2 ~2 create:gearshift[axis=x,powered=false]",
    "setblock ~1 ~3 ~2 minecraft:lever[face=floor,facing=north,powered=false]",
    "setblock ~0 ~2 ~2 create:andesite_encased_shaft[axis=x]",
    *[f"setblock ~-1 ~{y} ~{z} create_submarine:submarine_propeller[facing=west,reversed=false]"
      for y in (1, 2, 3) for z in (1, 2, 3)],
    # Ballast: vent in the keel -> pump controller -> the two tanks above it. The Onboard Computer
    # drives the controller (direction and speed) to hold the depth set on its screen. Pumps
    # turn like cogwheels, so a cogwheel beside it carries the motor's rotation in. Ballast goes
    # by how full the tanks are on average, so every tank must be fed; floaters carry the rest
    # of the hull's weight instead of extra tanks that would never fill.
    "setblock ~6 ~0 ~2 create_submarine:ballast_vent",
    "setblock ~6 ~1 ~2 create_submarine:pump_controller[facing=up]",
    "setblock ~6 ~2 ~2 create_submarine:ballast_tank",
    "setblock ~6 ~3 ~2 create_submarine:ballast_tank",
    *[f"setblock ~{x} ~{y} ~{z} create_submarine:floater" for x, y, z in ((2, 1, 1), (2, 1, 3), (8, 3, 1), (8, 3, 3))],
    "setblock ~7 ~1 ~2 create:cogwheel[axis=y]",
    "setblock ~7 ~2 ~2 create:creative_motor[facing=down]{ScrollValue:256}",
    # Starts at depth 0 so the sub waits at the surface until a depth is set.
    "setblock ~4 ~1 ~1 create_submarine:command_sub[facing=south]{TargetDepth:0}",
    # Air, and an iron door with a button on each side (an oak door gives way at about 49 m)
    "setblock ~9 ~1 ~1 create_submarine:creative_oxygenator",
    "setblock ~4 ~1 ~4 minecraft:iron_door[facing=north,hinge=left,open=false,powered=false,half=lower]",
    "setblock ~4 ~2 ~4 minecraft:iron_door[facing=north,hinge=left,open=false,powered=false,half=upper]",
    "setblock ~5 ~2 ~3 minecraft:stone_button[face=wall,facing=north]",
    "setblock ~5 ~2 ~5 minecraft:stone_button[face=wall,facing=south]",
    # Only the sub becomes the ship: clear the water around it first, put it back after.
    "fill ~-2 ~-1 ~-1 ~11 ~5 ~5 minecraft:air replace minecraft:water",
    "tp @s ~5 ~1 ~2",
    "sable assemble area ~-2 ~-1 ~-1 ~11 ~5 ~5",
    "fill ~-2 ~-1 ~-1 ~11 ~5 ~5 minecraft:water replace minecraft:air",
    'tellraw @s ["",{"text":"You are inside the test sub. ","color":"aqua"},'
    '"At the stern, the lever on the clutch starts and stops the propeller (about 8 blocks a '
    'second) and the one on the gearshift reverses it. It waits at the surface: set a depth on '
    'the Onboard Computer screen and it fills and drains the ballast to get there. The shaft '
    'through the hull holds to about 68 m."]',
]


def write_test_sub(functions: Path) -> None:
    (functions / "test_sub_build.mcfunction").write_text("\n".join(TEST_SUB) + "\n")
    (functions / "test_sub.mcfunction").write_text(
        "execute at @s positioned ~ 150 ~ run function packpack:test_sub_build\n")


# The wreck is usually built in the same tick the first player joins, after their client has
# the chunks: the client then holds the wreck's blocks but keeps drawing the old sea floor
# (the hull is invisible from inside). Any later block change in a section redraws it, so a
# little after a player is placed, one water block in every section the wreck touches becomes
# an invisible light block for a moment.
REFRESH_DELAY_TICKS = 60


def write_start_refresh(functions: Path, water: list) -> None:
    cells = {}
    for x, y, z in sorted(water):
        cells.setdefault((x >> 4, (DOME_FLOOR_Y + y) >> 4, z >> 4), (x, DOME_FLOOR_Y + y, z))
    (functions / "refresh_start.mcfunction").write_text("\n".join([
        *[f"execute if block {x} {y} {z} minecraft:water run setblock {x} {y} {z} minecraft:light[level=0,waterlogged=true]"
          for x, y, z in cells.values()],
        "schedule function packpack:refresh_start_done 5t",
    ]) + "\n")
    (functions / "refresh_start_done.mcfunction").write_text("\n".join(
        f"execute if block {x} {y} {z} minecraft:light run setblock {x} {y} {z} minecraft:water"
        for x, y, z in cells.values()) + "\n")


def expedition_log() -> str:
    (x, y, z), block = start_sub.lectern()
    pages = ",".join(f"'{json.dumps(page)}'" for page in start_sub.LOG_PAGES)
    book = (f'{{id:"minecraft:written_book",count:1,components:{{"minecraft:written_book_content":'
            f'{{title:"{start_sub.LOG_TITLE}",author:"{start_sub.LOG_AUTHOR}",pages:[{pages}]}}}}}}')
    return f"setblock ~{x} ~{y} ~{z} {block.replace(']', ',has_book=true]')}{{Book:{book},Page:0}} replace"


def write_start_functions() -> list[str]:
    """Write the start submarine functions and return the function ids the tick tag must run."""
    functions = DATAPACK / "data/packpack/function"
    functions.mkdir(parents=True, exist_ok=True)
    sub = start_sub.blocks()
    # Anything already there is washed out first, so the wreck lies on bare sea floor.
    xs, ys, zs = (sorted({c[i] for c in sub}) for i in range(3))
    clear = [(x, y, z) for x in range(xs[0] - 2, xs[-1] + 3) for y in range(0, ys[-1] + 3)
             for z in range(zs[0] - 2, zs[-1] + 3)]
    by_block: dict[str, list] = {}
    for cell, block in sub.items():
        by_block.setdefault(block, []).append(cell)
    # Doors and beds are two blocks that only stay when both halves exist, so they are placed
    # one block at a time, lower half or head first, after everything around them.
    two_part = {b for b in by_block if "_door[" in b or "_bed[" in b}
    build = [
        *fill_runs(clear, "minecraft:water"),
        *[line for block, cells in by_block.items() if block not in two_part for line in fill_runs(cells, block)],
        *[f"setblock ~{x} ~{y} ~{z} {block}" for block in sorted(two_part, key=lambda b: ("upper" in b or "foot" in b, b))
          for x, y, z in by_block[block]],
        *[f"item replace block ~{start_sub.starter_chest()[0]} ~{start_sub.starter_chest()[1]} ~{start_sub.starter_chest()[2]}"
          f" container.{slot} with {item}" for slot, item in enumerate(start_sub.STARTER_KIT)],
        expedition_log(),
        f"setworldspawn ~ ~{start_sub.DECK_Y + 1} ~",
        f"summon minecraft:marker ~ ~{start_sub.DECK_Y + 1} ~ {{Tags:[\"packpack_start\"]}}",
        "execute store result storage packpack:start y int 1 run data get entity"
        " @e[type=minecraft:marker,tag=packpack_start,limit=1] Pos[1]",
        "kill @e[type=minecraft:marker,tag=packpack_start]",
        "data modify storage packpack:start built set value 1b",
        "forceload remove -17 -17 17 17",
    ]
    (functions / "build_start.mcfunction").write_text("\n".join(build) + "\n")
    write_start_refresh(functions, [cell for cell in clear if cell not in sub])
    # In a new world the load tag runs before the chunks under spawn exist, so the wreck is
    # built from the tick tag instead: force-load the chunks around 0,0, wait until they are
    # loaded, then build once at the sea floor (a storage flag keeps it from ever overwriting
    # player changes) and move anyone who already joined into it.
    corners = " ".join(f"if loaded {x} 0 {z}" for x in (-17, 17) for z in (-17, 17))
    (functions / "start_tick.mcfunction").write_text("\n".join([
        "execute unless data storage packpack:start built run forceload add -17 -17 17 17",
        # The floor is flat around spawn, so the wreck goes at a fixed height on it.
        f"execute unless data storage packpack:start built positioned 0 {DOME_FLOOR_Y} 0 {corners}"
        " run function packpack:build_start",
        "execute if data storage packpack:start built as @a[tag=!packpack_started]"
        " run function packpack:place_new_player with storage packpack:start",
    ]) + "\n")
    (functions / "place_new_player.mcfunction").write_text("\n".join([
        "$tp @s 0.5 $(y) 0.5",
        "give @s ftbquests:book",
        "tag @s add packpack_started",
        f"schedule function packpack:refresh_start {REFRESH_DELAY_TICKS}t",
    ]) + "\n")
    (functions / "start.mcfunction").write_text("gamerule spawnRadius 0\n")
    write_test_sub(functions)
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
DEEP_WATER_COLOR = 0x0b3c6b


AIR_CARVING_FEATURES = {
    "minecraft:amethyst_geode", "minecraft:monster_room", "minecraft:monster_room_deep",
    "minecraft:spring_water", "minecraft:spring_lava", "minecraft:spring_lava_frozen",
}


def write_ocean_biomes() -> None:
    """Override the vanilla ocean biomes: no caves, and underwater fog the colour of deep water.

    The sky and air fog stay vanilla, so the surface still looks like daytime.
    """
    ocean_biomes = sorted({b for _, deep, shallow in TEMPERATURE_BANDS for b in (deep, shallow)})
    for name in ocean_biomes:
        biome = vanilla(f"data/minecraft/worldgen/biome/{name}.json")
        # Carvers cut air pockets into the water column because the aquifers are switched off.
        biome["carvers"] = {}
        # Features that hollow out air under the floor: geodes and dungeons leave air pockets in
        # the sand that show up as bubbles where they break through, springs pour out of them.
        biome["features"] = [[f for f in step if f not in AIR_CARVING_FEATURES] for step in biome["features"]]
        # Vanilla ocean water fog is almost black, which hides everything past a few chunks.
        biome["effects"]["water_fog_color"] = DEEP_WATER_COLOR
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


# Underwater structure mods whose templates place air blocks. Placed under water, that air
# becomes floating air pockets, so their pieces skip air the way vanilla ocean ruins do.
UNDERWATER_STRUCTURE_MODS = {"underwater_village", "hopo", "mos", "hybrid_aquatic"}
IGNORE_AIR = {"processor_type": "minecraft:block_ignore", "blocks": [{"Name": "minecraft:air"}]}


def write_underwater_air_filters() -> None:
    jars = {}
    for jar in sorted((SERVER / "mods").glob("*.jar")):
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if name.endswith(".json") and ("/worldgen/template_pool/" in name or "/worldgen/processor_list/" in name):
                    jars[name] = z.read(name)

    def processor_list(ref) -> object:
        if isinstance(ref, dict):
            return {"processors": [*ref.get("processors", []), IGNORE_AIR]}
        namespace, path = (ref.split(":", 1) + [""])[:2] if ":" in ref else ("minecraft", ref)
        source = f"data/{namespace}/worldgen/processor_list/{path}.json"
        base = json.loads(jars[source])["processors"] if source in jars else []
        if ref == "minecraft:empty":
            base = []
        return {"processors": [*base, IGNORE_AIR]}

    def fix(element: dict) -> None:
        if "elements" in element:
            for inner in element["elements"]:
                fix(inner)
        if "processors" in element:
            element["processors"] = processor_list(element["processors"])

    for name, data in jars.items():
        parts = name.split("/")
        if "/worldgen/template_pool/" not in name or parts[1] not in UNDERWATER_STRUCTURE_MODS:
            continue
        pool = json.loads(data)
        for entry in pool.get("elements", []):
            fix(entry["element"])
        write_json(DATAPACK / name, pool)


# Hybrid Aquatic removes vanilla coral from warm oceans and kelp and seagrass from deep oceans,
# expecting its own reef biomes to replace them. Those biomes are off in this pack, so without
# these overrides the warm ocean has no reefs and half the sea floor has no kelp.
# GregTech's raw oil sprout is a column of oil fluid from the ground up to the surface, which here
# stands 175 blocks tall in open water. Oil still comes from GregTech's underground fluid veins.
DISABLED_MOD_MODIFIERS = [
    "data/hybrid_aquatic/neoforge/biome_modifier/warm_ocean_modifiers.json",
    "data/hybrid_aquatic/neoforge/biome_modifier/deep_ocean_modifier.json",
    "data/gtceu/neoforge/biome_modifier/raw_oil_sprout.json",
]


def write_disabled_mod_modifiers() -> None:
    for path in DISABLED_MOD_MODIFIERS:
        write_json(DATAPACK / path, {"type": "neoforge:none"})


# Hybrid Aquatic hands out its richest spawn lists (reef fish, seagrass, the deep trench animals)
# by its own biome tags, which only hold its own biomes, and those are off here. The same spawns
# go to the vanilla oceans that suit them; the whole sea floor is deep, so the deep oceans count
# as trenches too. Only the spawns are copied: adding vanilla biomes to the tags themselves also
# brings Hybrid Aquatic's reef features along, which breaks feature ordering in warm oceans.
HAPI_BIOME_TAGS = {
    "coral_reef": ["warm_ocean"],
    "seagrass_bed": ["lukewarm_ocean", "ocean"],
    "red_meadow": ["lukewarm_ocean"],
    "deep_reef": ["deep_lukewarm_ocean"],
    "all_trenches": ["deep_ocean", "deep_cold_ocean", "deep_frozen_ocean", "deep_lukewarm_ocean"],
    "cold_trench": ["deep_cold_ocean"],
    "frozen_trench": ["deep_frozen_ocean"],
    "temperate_trench": ["deep_ocean"],
    "lukewarm_trench": ["deep_lukewarm_ocean"],
    "warm_trench": ["deep_lukewarm_ocean"],
}


def hybrid_aquatic_jar() -> Path:
    jar = next((SERVER / "mods").glob("hybrid_aquatic-*.jar"), None)
    if jar is None:
        raise SystemExit("run tools/boot_server.py once first, it installs Hybrid Aquatic")
    return jar


# Big animals that read too small in a whole ocean world; the tweaks mod scales them up by 1.5.
ENLARGED = ["whale_shark", "basking_shark", "orca", "great_white_shark", "ocean_sunfish", "manta_ray"]
# Hybrid Aquatic's bosses only came from summoning. They now turn up rarely in the deep
# trenches, and the tweaks mod keeps each one within 48 blocks of where it was first found.
LAIR_BOSSES = ["karkinos", "shell_beast"]
# Sharks big and fierce enough to go after drowned; whale and basking sharks filter feed.
DROWNED_HUNTERS = ["bull_shark", "great_white_shark", "sand_tiger_shark", "hammerhead_shark", "thresher_shark",
                   "sixgill_shark", "sleeper_shark"]
TRENCH_TOP_Y = -36


def write_entity_tags() -> None:
    tags = DATAPACK / "data/packpack/tags/entity_type"
    write_json(tags / "enlarged.json", {"values": [f"hybrid_aquatic:{e}" for e in ENLARGED]})
    write_json(tags / "lair_bosses.json", {"values": [f"hybrid_aquatic:{e}" for e in LAIR_BOSSES]})
    write_json(tags / "drowned_hunters.json", {"values": [f"hybrid_aquatic:{e}" for e in DROWNED_HUNTERS]})


# Vanilla cod and salmon (weight 15 each) crowded out Hybrid Aquatic's few cold water fish, so
# the start, which is in cold ocean, was nearly all cod and salmon. More Hybrid Aquatic species
# that live in cold water: (entity, weight, min, max) per biome.
COLD_WATER_SPAWNS = {
    "cold_ocean": [("herring", 10, 4, 12), ("mackerel", 10, 4, 12), ("rockfish", 5, 1, 4), ("octopus", 6, 1, 1),
                   ("sea_bass", 4, 1, 3), ("wrasse", 3, 1, 2), ("arrow_squid", 6, 1, 2), ("sea_nettle", 3, 1, 4)],
    "deep_cold_ocean": [("rockfish", 4, 1, 4), ("john_dory", 3, 1, 2), ("mackerel", 5, 4, 12)],
    "frozen_ocean": [("herring", 8, 4, 12), ("mackerel", 6, 4, 12)],
    "deep_frozen_ocean": [("herring", 5, 4, 12)],
}


def write_cold_water_spawns() -> None:
    for biome, spawns in COLD_WATER_SPAWNS.items():
        write_json(DATAPACK / f"data/packpack/neoforge/biome_modifier/cold_water_{biome}.json", {
            "type": "neoforge:add_spawns",
            "biomes": f"minecraft:{biome}",
            "spawners": [{"type": f"hybrid_aquatic:{entity}", "weight": weight, "minCount": low, "maxCount": high}
                         for entity, weight, low, high in spawns],
        })


def write_hapi_spawns() -> None:
    prefix = "data/hybrid_aquatic/neoforge/biome_modifier/"
    with zipfile.ZipFile(hybrid_aquatic_jar()) as jar:
        for name in sorted(n for n in jar.namelist() if n.startswith(prefix) and n.endswith(".json")):
            modifier = json.loads(jar.read(name))
            tag = modifier.get("biomes")
            if modifier.get("type") != "neoforge:add_spawns" or not isinstance(tag, str):
                continue
            biomes = HAPI_BIOME_TAGS.get(tag.removeprefix("#hapi:"))
            if biomes:
                write_json(DATAPACK / f"data/packpack/neoforge/biome_modifier/ha_{name.removeprefix(prefix)}",
                           {**modifier, "biomes": [f"minecraft:{b}" for b in biomes]})


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



INCONTROL_SPAWN_RULES = REPO / "pack" / "config" / "incontrol" / "spawn.json"
DROWNED_SPAWN_REFUSED = 0.75


def write_incontrol_spawn_rules() -> None:
    # Dome ground between buildings is too dark to stop hostile spawns, and domes are where the
    # last people live. In Control's Lost Cities condition keeps hostiles out of every sphere.
    write_json(INCONTROL_SPAWN_RULES, [
        {"dimension": "minecraft:overworld", "hostile": True, "insphere": True, "result": "deny"},
        # The whole sea floor is dark, so drowned spawn everywhere and pile up around a player
        # (12 to 22 within 64 blocks after a few minutes in testing). Most spawn attempts are
        # refused so despawning keeps it to a handful. A count limit does not work here: it
        # counts the whole dimension, including drowned that ocean ruins place when they generate.
        {"dimension": "minecraft:overworld", "mob": "minecraft:drowned", "random": DROWNED_SPAWN_REFUSED,
         "result": "deny"},
    ])


def write_incontrol_spawner() -> None:
    # Sea life spawns the vanilla way, from each biome's own spawn list with per player caps,
    # once the tweaks mod lets it spawn under our sea (see its WaterAnimalMixin and
    # HapiSpawnRulesMixin). In Control's spawner ignores biomes, so it only handles the bosses.
    # max_this caps a species across the whole world, but only for rules that name their mobs.
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
                "minheight": SEA_FLOOR_MIN_Y, "maxheight": max_height,
                "maxthis": max_this,
            },
        }
    write_json(INCONTROL_SPAWNER, [
        # A boss now and then, only down in the trenches, one at a time
        rule([f"hybrid_aquatic:{b}" for b in LAIR_BOSSES], 0.002, (1, 1), 1, TRENCH_TOP_Y, distance=(48, 96)),
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
    # The street level of a city is one above the top block of the floor.
    flooded["lostcity"]["groundLevel"] = DOME_FLOOR_Y
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
    # Drowned cities are what is left after the water came: most buildings have collapsed to
    # somewhere between a fifth and four fifths of their height.
    flooded["lostcity"].update({"ruinChance": 0.6, "ruinMinlevelPercent": 0.2, "ruinMaxlevelPercent": 0.8})
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
    # A dome's ground is flat, so every city level sits on it. Raised levels follow hills in
    # Lost Cities, and on flat ground they left lawns and plazas floating over open pits.
    domes["cities"].update({f"cityLevel{i}Height": DOME_FLOOR_Y for i in range(8)})
    # Lights in dome buildings keep their torches (and let dome villagers spawn); more
    # lots become buildings instead of lawn.
    domes["lostcity"].update({"generateLighting": True, "buildingChance": 0.6, "parkChance": 0.1})
    # The domes are the places that survived, so their buildings stand and their streets are clean.
    domes["lostcity"].update({"ruinChance": 0.05, "ruinMinlevelPercent": 0.8, "ruinMaxlevelPercent": 1.0,
                              "rubbleLayer": False})
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
        # Tubes join neighbouring domes, but Lost Cities only looks 63 chunks along a row for a
        # neighbour, so domes on the 64 chunk grid stand alone. Linked clusters come separately.
        "monorailChance": 1.0,
        # Clearing above a dome carves air unless the generator reports an outer sea level,
        # which only Lost Worlds' generator does, so leave the water above domes alone.
        "citySphereClearAbove": 0,
        "citySphereClearAboveUntilAir": False,
        "gridChunks": DOME_GRID_CHUNKS,
        "gridOffsetX": DOME_GRID_OFFSET[0],
        "gridOffsetZ": DOME_GRID_OFFSET[1],
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
    write_incontrol_spawn_rules()
    mode = " (village preview)" if args.preview_villages else ""
    print(f"sea level {SEA_LEVEL}{mode}: {DATAPACK.relative_to(REPO)} and profiles in {PROFILES_OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
