"""Reading Minecraft logs the same way for the server and client boot tests."""

from __future__ import annotations

import re
from pathlib import Path

LOG_ERROR = re.compile(r"/(ERROR|FATAL)\]")
GAME_TOOK = re.compile(r"Game took (?P<seconds>[\d.]+) seconds to start")
MENU_TO_WORLD = re.compile(r"Time from main menu to in-game was (?P<seconds>[\d.]+) seconds")

# Errors caused by bugs in mods we ship that are already reported upstream. They are
# listed by exact text with the issue, kept out of the failure count, and still shown
# in the reports, so anything new still fails and these get dropped once fixed.
KNOWN_UPSTREAM_ERRORS = {
    # Lost Cities saves a spawner block entity where its block later ended up as air or
    # water (its ruin pass on drowned buildings); vanilla throws the block entity away.
    "Failed to create block entity minecraft:mob_spawner": "https://github.com/McJty/LostCities/issues/786",
    "Failed to create block entity minecraft:trial_spawner": "https://github.com/McJty/LostCities/issues/786",
    # C2ME ships a client module (uncapped view distance) whose mixins name client classes; on a
    # dedicated server NeoForge refuses to load them and logs it, then the server runs normally.
    # Not reported upstream yet.
    # LambDynamicLights bundles its pridelib library with an access transformer entry for a file
    # that is not in the jar. NeoForge logs it and carries on. Not reported upstream yet.
    "Access transformer file META-INF/accesstransformer.cfg provided by mod pride does not exist":
        "https://github.com/LambdAurora/LambDynamicLights/issues",
    # Sodium Extra 0.9.3 (pinned with Sodium 0.8.12 for Veil) names an access transformer that is
    # not in its jar. NeoForge logs it and carries on. Fixed in later Sodium Extra releases.
    "Access transformer file accesstransformer.cfg provided by mod sodium_extra does not exist":
        "https://github.com/FlashyReese/sodium-extra/issues",
    "Attempted to load class net/minecraft/client/Options for invalid dist DEDICATED_SERVER":
        "https://github.com/RelativityMC/C2ME-neoforge/issues",
    "Attempted to load class net/minecraft/client/renderer/LevelRenderer for invalid dist DEDICATED_SERVER":
        "https://github.com/RelativityMC/C2ME-neoforge/issues",
    # KubeJS's Rhino indexes GregTech's classes for scripts; on a dedicated server GTItems names a
    # client class that NeoForge refuses to load, so Rhino skips that class. Our scripts don't use
    # it. Not reported upstream yet.
    "Attempted to load class net/minecraft/client/multiplayer/ClientLevel for invalid dist DEDICATED_SERVER":
        "https://github.com/KubeJS-Mods/Rhino/issues",
    # GregTech's 1.21.1 snapshot ships a font licence inside its textures; vanilla rejects the
    # upper-case file name as a resource path, logs it and skips the file. Not reported upstream yet.
    "Invalid path in pack: gtceu:textures/font/LICENSE.txt":
        "https://github.com/GregTechCEu/GregTech-Modern/issues",
}


def read_log(game_dir: Path) -> str:
    latest = game_dir / "logs" / "latest.log"
    return latest.read_text("utf-8", errors="replace") if latest.is_file() else ""


def error_lines(log: str) -> list[str]:
    return [line.rstrip() for line in log.splitlines() if LOG_ERROR.search(line)]


def crash_reports(game_dir: Path) -> list[str]:
    reports = game_dir / "crash-reports"
    return sorted(p.name for p in reports.glob("*.txt")) if reports.is_dir() else []


def mod_jars(game_dir: Path) -> list[str]:
    mods = game_dir / "mods"
    return sorted(p.name for p in mods.glob("*.jar")) if mods.is_dir() else []


def seconds(pattern: re.Pattern, log: str) -> float | None:
    match = pattern.search(log)
    return round(float(match["seconds"]), 2) if match else None


def known_upstream(line: str) -> str | None:
    return next((issue for text, issue in KNOWN_UPSTREAM_ERRORS.items() if text in line), None)
