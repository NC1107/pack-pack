# pack-pack

A long, hard tech modpack for minecraft 1.21.1 on neoforge.
It's early, there's pretty much nothing to play yet, it's just the setup so far.

## Playing it

You import a zip into prism launcher and it keeps itself updated from this repo.

1. Grab `pack-pack-stable.zip` from the latest release, or `pack-pack-dev.zip` if you're testing.
2. In prism, Add Instance, Import, pick the zip.
3. Launch it.

Before the game starts it pulls whatever mods the pack currently lists, so updates just show up the next time you launch.
The mods themselves still download from modrinth or curseforge since that's where their authors host them, but the pack itself lives here on github.

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
