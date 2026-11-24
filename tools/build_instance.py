#!/usr/bin/env python3
"""Build a Prism Launcher instance zip that keeps itself in sync with this repo.

    python3 tools/build_instance.py --channel dev      # follows the main branch
    python3 tools/build_instance.py --channel stable   # follows the latest release

The zip holds no mods. On every launch its pre-launch command runs packwiz-installer
against pack.toml on GitHub, which downloads whatever the channel currently lists.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tomllib
import zipfile
from pathlib import Path

from downloads import packwiz_bootstrap, packwiz_installer

REPO = Path(__file__).resolve().parent.parent
PACK_TOML = REPO / "pack" / "pack.toml"
DIST = REPO / "dist"

CHANNEL_BRANCHES = {"dev": "main", "stable": "stable"}
MIN_MEMORY_MB = 2048
MAX_MEMORY_MB = 6144


def github_repo() -> str:
    if repo := os.environ.get("GITHUB_REPOSITORY"):
        return repo
    url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=REPO,
                         check=True, capture_output=True, text=True).stdout.strip()
    match = re.search(r"github\.com[:/](?P<repo>[^/]+/[^/]+?)(\.git)?$", url)
    if not match:
        raise SystemExit(f"origin is not a GitHub remote: {url}")
    return match["repo"]


def ini_string(value: str) -> str:
    # Prism reads instance.cfg with Qt's INI parser, which drops bare quotes and
    # joins what is left, turning `"$INST_JAVA" -jar` into `$INST_JAVA-jar`.
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def instance_cfg(name: str, pack_url: str) -> str:
    pre_launch = f'"$INST_JAVA" -jar packwiz-installer-bootstrap.jar {pack_url}'
    return "\n".join([
        "[General]",
        "ConfigVersion=1.3",
        "InstanceType=OneSix",
        f"name={name}",
        "AutomaticJava=true",
        "OverrideMemory=true",
        f"MinMemAlloc={MIN_MEMORY_MB}",
        f"MaxMemAlloc={MAX_MEMORY_MB}",
        "OverrideCommands=true",
        f"PreLaunchCommand={ini_string(pre_launch)}",
        "",
    ])


def mmc_pack(versions: dict) -> str:
    return json.dumps({
        "formatVersion": 1,
        "components": [
            {"uid": "net.minecraft", "version": versions["minecraft"], "important": True},
            {"uid": "net.neoforged", "version": versions["neoforge"]},
        ],
    }, indent=2) + "\n"


def build(channel: str) -> Path:
    pack = tomllib.loads(PACK_TOML.read_text("utf-8"))
    repo = github_repo()
    branch = CHANNEL_BRANCHES[channel]
    pack_url = f"https://raw.githubusercontent.com/{repo}/{branch}/pack/pack.toml"
    name = pack["name"] if channel == "stable" else f"{pack['name']} (dev)"

    DIST.mkdir(exist_ok=True)
    out = DIST / f"{pack['name']}-{channel}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("instance.cfg", instance_cfg(name, pack_url))
        z.writestr("mmc-pack.json", mmc_pack(pack["versions"]))
        # The installer jar sits next to the bootstrap so a rate-limited GitHub API
        # during the bootstrap's self-update check cannot fail the launch.
        z.write(packwiz_bootstrap(), "minecraft/packwiz-installer-bootstrap.jar")
        z.write(packwiz_installer(), "minecraft/packwiz-installer.jar")
    print(f"{out.relative_to(REPO)} -> {pack_url}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a self-updating Prism Launcher instance zip.")
    parser.add_argument("--channel", choices=sorted(CHANNEL_BRANCHES), action="append",
                        help="channel to build (repeatable, default: both)")
    args = parser.parse_args()
    for channel in args.channel or sorted(CHANNEL_BRANCHES):
        build(channel)


if __name__ == "__main__":
    main()
