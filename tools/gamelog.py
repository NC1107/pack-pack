"""Reading Minecraft logs the same way for the server and client boot tests."""

from __future__ import annotations

import re
from pathlib import Path

LOG_ERROR = re.compile(r"/(ERROR|FATAL)\]")
GAME_TOOK = re.compile(r"Game took (?P<seconds>[\d.]+) seconds to start")
MENU_TO_WORLD = re.compile(r"Time from main menu to in-game was (?P<seconds>[\d.]+) seconds")


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
