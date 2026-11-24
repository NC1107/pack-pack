#!/usr/bin/env python3
"""Repository hygiene checks that keep the pack working on both Linux and Windows.

Run from anywhere: python3 tools/check_repo.py [--json]
Exits 1 if any problem is found.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parent.parent
PACK_DIR = REPO / "pack"

# Windows MAX_PATH is 260 characters including the checkout location, so leave
# roughly 100 characters for wherever a contributor clones the repo.
MAX_REPO_PATH_LENGTH = 160

WINDOWS_RESERVED_STEMS = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}
WINDOWS_INVALID_CHARS = set('<>:"\\|?*')
CRLF_ALLOWED_SUFFIXES = {".bat", ".cmd", ".ps1"}
BINARY_SUFFIXES = {".jar", ".zip", ".png", ".jpg", ".ogg", ".nbt", ".dat", ".mca"}

# packwiz never indexes these, so they must not count as unindexed files.
PACKWIZ_UNINDEXED = {"pack.toml", "index.toml", ".packwizignore"}


@dataclass(frozen=True)
class Problem:
    check: str
    path: str
    message: str


def repo_files() -> list[PurePosixPath]:
    """Tracked plus untracked-but-not-ignored files, so checks work before the first commit."""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=REPO, check=True, capture_output=True,
    ).stdout.decode("utf-8")
    return sorted({PurePosixPath(p) for p in out.split("\0") if p and (REPO / p).is_file()})


def check_case_collisions(files: list[PurePosixPath]) -> list[Problem]:
    seen: dict[str, PurePosixPath] = {}
    problems = []
    for f in files:
        key = str(f).lower()
        if key in seen:
            problems.append(Problem("case-collision", str(f),
                                    f"differs from {seen[key]} only by case; Windows sees one file"))
        else:
            seen[key] = f
    return problems


def check_windows_names(files: list[PurePosixPath]) -> list[Problem]:
    problems = []
    for f in files:
        if len(str(f)) > MAX_REPO_PATH_LENGTH:
            problems.append(Problem("path-length", str(f),
                                    f"{len(str(f))} characters; keep repo paths under {MAX_REPO_PATH_LENGTH} for Windows"))
        for part in f.parts:
            bad = WINDOWS_INVALID_CHARS & set(part)
            if bad:
                problems.append(Problem("windows-name", str(f), f"'{part}' contains {''.join(sorted(bad))}"))
            if part.split(".")[0].lower() in WINDOWS_RESERVED_STEMS:
                problems.append(Problem("windows-name", str(f), f"'{part}' is a reserved device name on Windows"))
            if part.endswith((" ", ".")):
                problems.append(Problem("windows-name", str(f), f"'{part}' ends with a space or dot"))
    return problems


def check_line_endings(files: list[PurePosixPath]) -> list[Problem]:
    problems = []
    for f in files:
        if f.suffix.lower() in BINARY_SUFFIXES | CRLF_ALLOWED_SUFFIXES:
            continue
        data = (REPO / f).read_bytes()
        if b"\0" in data[:8192]:
            continue
        if b"\r\n" in data:
            problems.append(Problem("line-endings", str(f), "contains CRLF; this repo uses LF (see .gitattributes)"))
    return problems


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_packwiz_index() -> list[Problem]:
    """Verify the packwiz index matches the files on disk without running packwiz (which rewrites them)."""
    pack_toml = PACK_DIR / "pack.toml"
    if not pack_toml.is_file():
        return [Problem("packwiz-index", "pack/pack.toml", "missing")]
    pack = tomllib.loads(pack_toml.read_text("utf-8"))
    index_path = PACK_DIR / pack["index"]["file"]
    rel_index = index_path.relative_to(REPO).as_posix()
    stale = "out of date; run `packwiz refresh` in pack/"

    if pack["index"].get("hash-format") != "sha256":
        return [Problem("packwiz-index", "pack/pack.toml", "expected sha256 index hashes")]
    if sha256_of(index_path) != pack["index"]["hash"]:
        return [Problem("packwiz-index", rel_index, f"hash does not match pack.toml; {stale}")]

    index = tomllib.loads(index_path.read_text("utf-8"))
    problems = []
    indexed = set()
    for entry in index.get("files", []):
        rel = entry["file"]
        indexed.add(rel)
        target = PACK_DIR / rel
        if not target.is_file():
            problems.append(Problem("packwiz-index", f"pack/{rel}", f"listed in index but missing; {stale}"))
        elif sha256_of(target) != entry["hash"]:
            problems.append(Problem("packwiz-index", f"pack/{rel}", f"hash differs from index; {stale}"))

    for f in sorted(PACK_DIR.rglob("*")):
        rel = f.relative_to(PACK_DIR).as_posix()
        if f.is_file() and rel not in indexed and rel not in PACKWIZ_UNINDEXED:
            problems.append(Problem("packwiz-index", f"pack/{rel}", f"not in index; {stale}"))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-platform repository hygiene checks for the pack.")
    parser.add_argument("--json", action="store_true", help="print problems as JSON for agents and CI")
    args = parser.parse_args()

    files = repo_files()
    problems = [
        *check_case_collisions(files),
        *check_windows_names(files),
        *check_line_endings(files),
        *check_packwiz_index(),
    ]

    if args.json:
        print(json.dumps({"files_checked": len(files), "problems": [asdict(p) for p in problems]}, indent=2))
    else:
        for p in problems:
            print(f"{p.path}: [{p.check}] {p.message}")
        print(f"{len(files)} files checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
