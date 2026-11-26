# Working on the pack

Same steps on fedora and windows unless it says otherwise.

## What you need

- git
- python 3.11 or newer (on windows use `python` instead of `python3` below)
- prism launcher
- packwiz, `go install github.com/packwiz/packwiz@latest`, or grab a windows build from the packwiz readme
- java 21 if you want to run the server boot test locally, temurin from adoptium works

On windows, run these once so git doesn't mess with line endings or choke on long paths:

```
git config --global core.autocrlf false
git config --global core.longpaths true
```

Also clone somewhere short like `C:\dev\pack-pack`.

## Testing what's on main

You just build the dev instance and import it into prism:

```
python3 tools/build_instance.py --channel dev
```

That makes `dist/pack-pack-dev.zip`.
In prism it's Add Instance, Import, pick the zip.
Every launch it syncs to whatever is on `main`, so after someone pushes you just relaunch.
Github's raw files can lag by a few minutes after a push.

## Testing your own changes before pushing

Run `packwiz serve` inside `pack/` and leave it running.
Then in the instance settings, under Custom commands, swap the github url in the pre-launch command for `http://localhost:8080/pack.toml`.
Now every launch syncs to your working copy instead.
Swap it back when you're done.

## Day to day

```
cd pack
packwiz mr add <modrinth-slug>       # or packwiz cf add <curseforge-slug>
packwiz refresh                      # after editing anything under pack/
cd ..
python3 tools/check_repo.py
python3 tools/boot_server.py --java <path-to-java-21>
python3 tools/boot_client.py --java <path-to-java-21> --hmc-java <path-to-java-25>
```

The client one needs `xvfb-run` (fedora: `sudo dnf install xorg-x11-server-Xvfb`) since it renders on a virtual display, so it's mostly a linux and CI thing.

If packwiz says a mod is marked for both sides but only needs one, pick on purpose and set `side` in its `.pw.toml`.
A client-only mod on the server crashes it.

Commits use `feat:`, `fix:`, `chore:` etc, release-please reads those to write the changelog and pick the next version.
Work on a branch and open a PR so CI runs before it lands on `main`.

## The world generation

The datapack in `pack/datapacks/pack-pack-worldgen` and the lost cities profiles in `pack/config/lostcities/profiles` are generated, don't edit them by hand.
Change `tools/build_worldgen.py` or `tools/lc_villages.py`, then:

```
python3 tools/boot_server.py --java <path-to-java-21>   # once, it installs the jars the generator reads from
python3 tools/build_worldgen.py
cd pack && packwiz refresh
```

`--preview-villages` makes every city a village and allows them near spawn, handy for looking at villages, just don't commit that build.

### Things that fooled us when testing world generation

- A pregenerated world never ticks, so nothing falls or flows in it.
  Sand that only falls once a player is near (like the sand under domes that drained into the void) only shows up in a live game, flying through fresh chunks while counting `falling_block` entities.
- Look at the whole height.
  The worldgen check reads y -70 to 125, and the bottom layer at y -64 has its own bedrock check because a hole there drains everything above it.
- A chunk that fails to generate is left out of the world, and its crash report used to end the pregeneration early.
  The check now fails on any `Error generating chunk` line, look for it in the server log whenever a dome looks broken.
- `tools/region.py` only returns fully generated block chunks, so it reads nothing from `world/entities`.
- Dome villagers don't exist until a player comes near, their houses spawn them from a trial spawner, so count trial spawners to find village domes.
- Villagers, pillagers and evokers at the sea surface are the crews of the ship structures, and the skeletons on the sea floor belong to underwater ruins.
- The four domes the check looks at are too few for anything rare: the village style and a dome missing part of its glass only showed up across 25 dome slots.

## What the tools do

- `tools/check_repo.py` checks line endings, case collisions, windows-reserved names, path length, and that the packwiz index matches the files. `--json` gives output an agent can read.
- `tools/check_worldgen.py` generates a patch of the ocean with four domes (after `boot_server.py` has installed the server) and fails if a dome's glass is missing, there is air in the water outside it, the ground around it is not level, there is water under the floor at its edge, blocks float in the drowned city between the domes, or a mod's biome got into the ocean.
  CI runs it on every PR with two seeds.
  `--seed` picks another seed, `--skip-generation` checks the world that is already there, and it prints how many chunks a second the generation took.
- Every Monday the `mod updates` workflow runs `packwiz update --all`, runs the full checks on the result, and opens a PR if they pass. It can pick beta builds, so read the list before merging. The patched jars in `pack/mods` are plain files and never get updated by it.
- `tests/` has pytest tests for the tools (the start dome is watertight, the fill commands cover it exactly, log and spark parsing). Run `python3 -m pytest -q tests` and `python3 -m ruff check tools tests`, CI runs both.
- `tools/boot_server.py` installs neoforge and the server side of the pack into `run/server`, boots it on a fixed seed, grabs a spark health report, and writes `run/boot-report.json`.
- `tools/boot_client.py` does the same for the client, it launches the game with headlessmc on a virtual display, mc-runtime-test makes a world and joins it, then it writes `run/client-report.json`.
- `tools/build_instance.py` builds the prism instance zips into `dist/`.
