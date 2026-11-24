"""Pinned downloads shared by the tools, cached in .cache/ and verified by sha256."""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / ".cache"
USER_AGENT = "pack-pack-tools"

# Pinned rather than "latest" so a run means the same thing on every machine.
PACKWIZ_INSTALLER_URL = "https://github.com/packwiz/packwiz-installer/releases/download/v0.5.14/packwiz-installer.jar"
PACKWIZ_INSTALLER_SHA256 = "c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598"
PACKWIZ_BOOTSTRAP_URL = "https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v0.0.3/packwiz-installer-bootstrap.jar"
PACKWIZ_BOOTSTRAP_SHA256 = "a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def cached_download(url: str, sha256: str) -> Path:
    target = CACHE / sha256[:16] / url.rsplit("/", 1)[-1]
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == sha256:
        return target
    print(f"downloading {url}", flush=True)
    data = fetch(url)
    actual = hashlib.sha256(data).hexdigest()
    if actual != sha256:
        raise SystemExit(f"checksum mismatch for {url}: expected {sha256}, got {actual}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def packwiz_installer() -> Path:
    return cached_download(PACKWIZ_INSTALLER_URL, PACKWIZ_INSTALLER_SHA256)


def packwiz_bootstrap() -> Path:
    return cached_download(PACKWIZ_BOOTSTRAP_URL, PACKWIZ_BOOTSTRAP_SHA256)
