# pack-pack

A long, hard tech modpack for minecraft 1.21.1 on neoforge.
It's early, there's pretty much nothing to play yet, it's just the setup so far.

## Playing it

You import a zip into prism launcher and it keeps itself updated from this repo.

1. Grab `pack-pack-stable.zip` from the latest release, or `pack-pack-dev.zip` if you're testing.
2. In prism, Add Instance, Import, pick the zip.
3. Launch it.

Before the game starts it pulls whatever mods the pack currently lists, so updates just show up the next time you launch.
Shaders are off by default, there's three packs in video settings if you want to try them.
There's a map and minimap (ftb chunks, it also does land claims for multiplayer), and `/sethome`, `/home`, `/back` and `/tpa` if you need them.

## The world

Pretty much the whole overworld is ocean, about 175 blocks of water over a sea floor with ridges, trenches and hills.
You start in a small glass dome on the sea floor with a door on the east side that keeps the water out, there's nothing else close by on purpose.
Past about 500 blocks out you start finding the domes, the last cities that kept the water out, with drowned cities around them that are mostly collapsed and overgrown.
Some domes have a few village houses with villagers living in them, and glass tubes with a rail in them run along the sea floor between neighbouring domes.
Under the floor it's sand down to bedrock, so there's no mining your way around anything.
Just make a new world with the default world type, it's all set up by the pack, an old world won't change.
The mods themselves still download from modrinth or curseforge since that's where their authors host them, but the pack itself lives here on github, and a few of them (lost cities, lost worlds and a small one of ours) are patched builds that live in the repo.

## Working on it

Setup and the day to day stuff is in [docs/dev.md](docs/dev.md).

## How it's checked

Every push and PR runs three checks on github:

- `tools/check_repo.py` looks for stuff that breaks between linux and windows, like crlf line endings, file names that only differ by case, paths that are too long, and a mod index that's out of date.
- `tools/boot_server.py` installs the pack on a real dedicated server and boots it.
  It fails if the server crashes, logs errors, or never finishes starting, and it records boot time and tick times so we can see when something gets slower.
- `tools/boot_client.py` installs the client side of the pack and launches the actual game on a virtual display.
  It creates a world, joins it, lets it tick for a bit, then quits, and fails on the same stuff as the server one.

The bigger checks (recipe overlap, dupes, quests you can't finish, etc) come later once there's content to check.

## Releases

Commit messages use the `feat:` / `fix:` style.
release-please keeps a release PR open with the changelog.
When you merge it, it tags the release, attaches both instance zips, and moves the `stable` branch to it.
Stable instances read from that branch, so merging the release PR is basically the publish button.

## Plan

Decisions, open questions and known gaps are in [docs/plan.md](docs/plan.md).
