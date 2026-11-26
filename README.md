# pack-pack

A long, hard tech modpack for minecraft 1.21.1 on neoforge.
It's early, the world and the start are there but there's no progression to play through yet.

## Playing it

You import a zip into prism launcher and it keeps itself updated from this repo.

1. Grab `pack-pack-stable.zip` from the latest release, or `pack-pack-dev.zip` if you're testing.
2. In prism, Add Instance, Import, pick the zip.
3. Launch it.

Before the game starts it pulls whatever mods the pack currently lists, so updates just show up the next time you launch.
No shaders for now, create deep seas only runs on an older sodium that iris doesn't support yet.
There's a map and minimap (ftb chunks, it also does land claims for multiplayer), and `/sethome`, `/home`, `/back` and `/tpa` if you need them.

## The world

Pretty much the whole overworld is ocean, about 175 blocks of water over a sea floor with ridges, trenches and hills.
You start in a wrecked submarine lying on the sea floor, with an airlock on the side that keeps the water out, and there's nothing else close by on purpose.
It's your own sub, the log on the bridge lectern tells how you ended up down there.
You respawn in it when you die, and if it's ever flooded or gone you wake up in one of the nearest domes with a fresh diving suit instead.
The floor is about 173 m down and the water crushes you past 120 m, so put on the copper diving suit from the chest (and keep the backtank in your inventory) before you go out.
Past about 500 blocks out you start finding the domes, the last cities that kept the water out, with drowned cities around them that are mostly collapsed and overgrown.
About one dome in four has a village in it, the domes and the glass tubes with a rail that run between neighbouring domes are lit, and no monsters spawn in either.
Create and create deep seas are in, so submarines with pressure and oxygen are a thing, but there's no progression around them yet.
To try one out, `/function packpack:test_sub` (cheats on) builds a small working sub at the surface above you: levers at the stern start and reverse the propeller, and the onboard computer screen sets how deep it goes (good to about 68 m).
Under the floor it's sand down to bedrock, so there's no mining your way around anything.
The sea life spawns by biome, reef fish over the warm reefs, deep species down in the trenches, dolphins and orcas up at the surface, and now and then a boss in a trench that stays near where you found it.
Dropped items sink to the floor instead of floating off to the surface.
Just make a new world with the default world type, it's all set up by the pack, an old world won't change.
The mods themselves still download from modrinth or curseforge since that's where their authors host them, but the pack itself lives here on github, and a few of them (lost cities, lost worlds and a small one of ours) are patched builds that live in the repo.

## Working on it

Setup and the day to day stuff is in [docs/dev.md](docs/dev.md).

## How it's checked

Every push and PR runs these on github:

- `tools/check_repo.py` looks for stuff that breaks between linux and windows, like crlf line endings, file names that only differ by case, paths that are too long, and a mod index that's out of date.
- `tools/boot_server.py` installs the pack on a real dedicated server and boots it.
  It fails if the server crashes, logs errors, or never finishes starting, and it records boot time and tick times so we can see when something gets slower.
- `tools/boot_client.py` installs the client side of the pack and launches the actual game on a virtual display.
  It creates a world, joins it, lets it tick for a bit, then quits, and fails on the same stuff as the server one.
- `tools/check_worldgen.py` generates a patch of ocean with four domes on two seeds and fails on broken glass, leaks, air pockets, floating blocks, or a chunk that failed to generate.
  The same job regenerates the datapack and fails if it isn't what's committed.
- Our own small mod gets rebuilt from source and has to come out byte for byte the same as the jar in `pack/mods`.

The bigger checks (recipe overlap, dupes, quests you can't finish, etc) come later once there's content to check.

## Releases

Commit messages use the `feat:` / `fix:` style.
release-please keeps a release PR open with the changelog.
When you merge it, it tags the release, attaches both instance zips, and moves the `stable` branch to it.
Stable instances read from that branch, so merging the release PR is basically the publish button.

## Plan

Decisions, open questions and known gaps are in [docs/plan.md](docs/plan.md).
