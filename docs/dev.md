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

## What the tools do

- `tools/check_repo.py` checks line endings, case collisions, windows-reserved names, path length, and that the packwiz index matches the files. `--json` gives output an agent can read.
- `tools/boot_server.py` installs neoforge and the server side of the pack into `run/server`, boots it on a fixed seed, grabs a spark health report, and writes `run/boot-report.json`.
- `tools/boot_client.py` does the same for the client, it launches the game with headlessmc on a virtual display, mc-runtime-test makes a world and joins it, then it writes `run/client-report.json`.
- `tools/build_instance.py` builds the prism instance zips into `dist/`.
