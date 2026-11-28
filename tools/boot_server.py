#!/usr/bin/env python3
"""Install the pack on a dedicated NeoForge server, boot it, and report how it went.

Works the same on Linux, Windows and CI:
    python3 tools/boot_server.py --java /path/to/java21/bin/java

Writes run/boot-report.json and exits 1 if the server fails to reach "Done",
crashes, or logs more errors than --max-errors allows.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib
from pathlib import Path

import gamelog
import nbt
from downloads import cached_download, fetch, packwiz_bootstrap, packwiz_installer

REPO = Path(__file__).resolve().parent.parent
PACK_TOML = REPO / "pack" / "pack.toml"
RUN = REPO / "run"
SERVER = RUN / "server"
REPORT = RUN / "boot-report.json"

NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge"

DONE_LINE = re.compile(r"Done \((?P<seconds>[\d.]+)s\)! For help")
HEALTH_TPS = re.compile(r"^\s*(?P<tps>[\d.*]+),")
HEALTH_TICKS = re.compile(r"^\s*(?P<min>[\d.]+)/(?P<med>[\d.]+)/(?P<p95>[\d.]+)/(?P<max>[\d.]+);")
HEALTH_MEMORY = re.compile(r"^\s*(?P<used>[\d.]+) (?P<unit>[KMG]B) / (?P<total>[\d.]+) [KMG]B")

# Fixed settings so boot time and tick numbers are comparable between runs and machines.
SERVER_PROPERTIES = """\
level-seed=pack-pack-benchmark
level-name=world
view-distance=10
simulation-distance=10
online-mode=false
spawn-protection=0
"""
HEALTH_WAIT_SECONDS = 10
# Sable's physics runs in a native library that is only loaded once a ship exists, so the boot
# assembles a small iron block into one: proof the library loads on this OS (it has failed on
# Windows, Sable #1307 and #1616). Its chunk is force-loaded so the ship keeps ticking.
# It runs after the idle health sample, so building the ship doesn't count against the tick budget.
PHYSICS_SMOKE = [
    (HEALTH_WAIT_SECONDS + 1, "forceload add 48 48"),
    (HEALTH_WAIT_SECONDS + 2, "fill 48 100 48 49 101 49 minecraft:iron_block"),
    (HEALTH_WAIT_SECONDS + 3, "sable assemble area 48 100 48 49 101 49"),
    (HEALTH_WAIT_SECONDS + 8, "sable info @e"),
]
STOP_AFTER_SECONDS = HEALTH_WAIT_SECONDS + 10
SUB_LEVELS = re.compile(r"Found (?P<count>\d+) sub-levels")

# Every new world's overworld is meant to generate with The Lost Cities. Its in-game
# commands need a player, so instead read the city hub data it saves per dimension.
LOST_CITIES_DATA = Path("world") / "data" / "LostCityHighwayData.dat"

# Aikar's G1 flags (docs.papermc.io/paper/aikars-flags), the usual baseline for
# dedicated servers, so the boot test runs the way a host would.
SERVER_GC_FLAGS = [
    "-XX:+UseG1GC", "-XX:+ParallelRefProcEnabled", "-XX:MaxGCPauseMillis=200",
    "-XX:+UnlockExperimentalVMOptions", "-XX:+DisableExplicitGC", "-XX:+AlwaysPreTouch",
    "-XX:G1NewSizePercent=30", "-XX:G1MaxNewSizePercent=40", "-XX:G1HeapRegionSize=8M",
    "-XX:G1ReservePercent=20", "-XX:G1HeapWastePercent=5", "-XX:G1MixedGCCountTarget=4",
    "-XX:InitiatingHeapOccupancyPercent=15", "-XX:G1MixedGCLiveThresholdPercent=90",
    "-XX:G1RSetUpdatingPauseTimePercent=5", "-XX:SurvivorRatio=32", "-XX:+PerfDisableSharedMem",
    "-XX:MaxTenuringThreshold=1",
]


def log(msg: str) -> None:
    print(f"[boot] {msg}", flush=True)


def neoforge_installer(version: str) -> Path:
    url = f"{NEOFORGE_MAVEN}/{version}/neoforge-{version}-installer.jar"
    sha256 = fetch(url + ".sha256").decode().split()[0]
    return cached_download(url, sha256)


def java_major_version(java: str) -> int | None:
    out = subprocess.run([java, "-version"], capture_output=True, text=True, check=False).stderr
    match = re.search(r'version "(\d+)', out)
    return int(match[1]) if match else None


def install_server(java: str, neoforge_version: str) -> None:
    marker = SERVER / ".neoforge-version"
    if marker.is_file() and marker.read_text().strip() == neoforge_version:
        return
    if SERVER.exists():
        shutil.rmtree(SERVER)
    SERVER.mkdir(parents=True)
    installer = neoforge_installer(neoforge_version)
    log(f"installing NeoForge {neoforge_version} server")
    subprocess.run([java, "-jar", str(installer), "--install-server", str(SERVER)],
                   cwd=SERVER, check=True, stdout=subprocess.DEVNULL)
    marker.write_text(neoforge_version)


def install_pack(java: str) -> None:
    installer = packwiz_installer()
    bootstrap = packwiz_bootstrap()
    # The bootstrap would otherwise self-update packwiz-installer from GitHub;
    # handing it the pinned jar keeps runs reproducible and offline-friendly.
    shutil.copy(installer, SERVER / "packwiz-installer.jar")
    log("installing server-side mods with packwiz-installer")
    subprocess.run([java, "-jar", str(bootstrap), "--bootstrap-no-update", "-g", "-s", "server",
                    PACK_TOML.as_uri()], cwd=SERVER, check=True)


def prepare_world(memory: str) -> None:
    (SERVER / "eula.txt").write_text("eula=true\n")
    (SERVER / "server.properties").write_text(SERVER_PROPERTIES)
    (SERVER / "user_jvm_args.txt").write_text("\n".join([f"-Xms{memory}", f"-Xmx{memory}", *SERVER_GC_FLAGS]) + "\n")
    for stale in ("world", "logs", "crash-reports"):
        shutil.rmtree(SERVER / stale, ignore_errors=True)


def server_command(java: str, neoforge_version: str) -> list[str]:
    args_file = "win_args.txt" if os.name == "nt" else "unix_args.txt"
    libs = f"libraries/net/neoforged/neoforge/{neoforge_version}/{args_file}"
    return [java, "@user_jvm_args.txt", f"@{libs}", "nogui"]


def pump(stream, lines: queue.Queue) -> None:
    for line in iter(stream.readline, ""):
        lines.put(line)
    lines.put(None)


def send(proc: subprocess.Popen, command: str) -> None:
    if proc.poll() is None and proc.stdin:
        proc.stdin.write(command + "\n")
        proc.stdin.flush()


def parse_health(lines: list[str]) -> dict:
    """Pull the numbers out of spark's `health` console report."""
    health: dict = {}
    section = None
    for line in lines:
        if line.startswith("> TPS"):
            section = "tps"
        elif line.startswith("> Tick durations"):
            section = "ticks"
        elif line.startswith("> Memory"):
            section = "memory"
        elif section == "tps" and (m := HEALTH_TPS.match(line)):
            health["tps_5s"] = float(m["tps"].strip("*"))
            section = None
        elif section == "ticks" and (m := HEALTH_TICKS.match(line)):
            health["mspt_10s"] = {k: float(m[k]) for k in ("min", "med", "p95", "max")}
            section = None
        elif section == "memory" and (m := HEALTH_MEMORY.match(line)):
            health["heap_used"] = f"{m['used']} {m['unit']}"
            section = None
    return health


def save_thread_dump(java: str, pid: int) -> None:
    """Leave evidence of what a hung server was doing before it gets killed."""
    resolved = shutil.which(java) or java
    jcmd = Path(resolved).resolve().parent / ("jcmd.exe" if os.name == "nt" else "jcmd")
    try:
        result = subprocess.run([str(jcmd), str(pid), "Thread.print"], capture_output=True, text=True,
                                timeout=60, check=False)
        dump = result.stdout + result.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        dump = f"could not take a thread dump: {error}\n"
    (RUN / "server-threads.txt").write_text(dump)
    log("saved a thread dump of the hung server to run/server-threads.txt")


def run_server(cmd: list[str], timeout: int, quiet: bool) -> dict:
    started = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=SERVER, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    lines: queue.Queue = queue.Queue()
    threading.Thread(target=pump, args=(proc.stdout, lines), daemon=True).start()

    result = {"reached_done": False, "server_reported_seconds": None,
              "wall_seconds_to_done": None, "timed_out": False, "crashed": False}
    after_done: list[str] = []
    deadline = started + timeout

    while True:
        try:
            line = lines.get(timeout=max(0.1, deadline - time.monotonic()))
        except queue.Empty:
            result["timed_out"] = True
            save_thread_dump(cmd[0], proc.pid)
            proc.kill()
            break
        if line is None:
            break
        if not quiet:
            sys.stdout.write(line)
        if "Preparing crash report" in line:
            # A crashed server can sit there until the timeout; it is not going to recover.
            result["crashed"] = True
            proc.kill()
            break
        if result["reached_done"]:
            after_done.append(line.rstrip())
        elif match := DONE_LINE.search(line):
            result["reached_done"] = True
            result["server_reported_seconds"] = float(match["seconds"])
            result["wall_seconds_to_done"] = round(time.monotonic() - started, 1)
            for delay, command in PHYSICS_SMOKE:
                threading.Timer(delay, send, (proc, command)).start()
            # Let the server tick for a while so spark has real samples, then stop.
            threading.Timer(HEALTH_WAIT_SECONDS, send, (proc, "spark health")).start()
            threading.Timer(STOP_AFTER_SECONDS, send, (proc, "stop")).start()

    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        # Hung while saving or stopping.
        result["timed_out"] = True
        save_thread_dump(cmd[0], proc.pid)
        proc.kill()
        proc.wait()
    result["exit_code"] = proc.returncode
    result["clean_stop"] = result["reached_done"] and proc.returncode == 0
    result["health"] = parse_health(after_done)
    result["physics"] = parse_physics(after_done)
    return result


def parse_physics(lines: list[str]) -> dict:
    counts = [int(m["count"]) for line in lines if (m := SUB_LEVELS.search(line))]
    return {"assembled": any("Assembled a region" in line for line in lines),
            "sub_levels": counts[-1] if counts else None}


def lost_cities_dimensions() -> dict:
    """Map each dimension with Lost Cities data to how many of its city hubs hold a city."""
    path = SERVER / LOST_CITIES_DATA
    if not path.is_file():
        return {}
    dimensions = nbt.read(path).get("data", {}).get("dimensions", {})
    return {dim: sum(1 for hub in info.get("hubs", []) if hub.get("cityLevel", 0) > 0)
            for dim, info in dimensions.items()}


def scan_logs() -> dict:
    errors = gamelog.error_lines(gamelog.read_log(SERVER))
    return {
        "error_lines": [line for line in errors if not gamelog.known_upstream(line)],
        "known_upstream_error_lines": [line for line in errors if gamelog.known_upstream(line)],
        "crash_reports": gamelog.crash_reports(SERVER),
        "server_mods": gamelog.mod_jars(SERVER),
    }


# What a freshly booted, idle server may cost. CI runners are slower than a dev machine:
# on 2026-11-25 CI booted in 7 to 12 s at 20 TPS, median tick 1 to 2 ms, 95th percentile
# about 3 ms and about 1 GB of heap, so these leave a lot of room and still catch a mod
# that makes the server crawl.
BUDGETS = {
    "server_seconds": 60.0,
    "min_tps": 19.5,
    "median_mspt": 10.0,
    "p95_mspt": 25.0,
    "heap_mb": 3072.0,
}


def heap_mb(text: str) -> float | None:
    match = re.fullmatch(r"([\d.]+)\s*(MB|GB)", text or "")
    if not match:
        return None
    return float(match[1]) * (1024 if match[2] == "GB" else 1)


def over_budget(report: dict) -> list[str]:
    problems = []
    if report["server_reported_seconds"] > BUDGETS["server_seconds"]:
        problems.append(f"boot took {report['server_reported_seconds']}s (budget {BUDGETS['server_seconds']}s)")
    health = report.get("health") or {}
    tps, mspt = health.get("tps_5s"), health.get("mspt_10s") or {}
    if tps is not None and tps < BUDGETS["min_tps"]:
        problems.append(f"idle TPS {tps} (budget at least {BUDGETS['min_tps']})")
    if mspt.get("med") is not None and mspt["med"] > BUDGETS["median_mspt"]:
        problems.append(f"idle median tick {mspt['med']} ms (budget {BUDGETS['median_mspt']} ms)")
    if mspt.get("p95") is not None and mspt["p95"] > BUDGETS["p95_mspt"]:
        problems.append(f"idle 95th percentile tick {mspt['p95']} ms (budget {BUDGETS['p95_mspt']} ms)")
    heap = heap_mb(health.get("heap_used", ""))
    if heap is not None and heap > BUDGETS["heap_mb"]:
        problems.append(f"heap {heap:.0f} MB after boot (budget {BUDGETS['heap_mb']:.0f} MB)")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Boot the pack on a dedicated server and report the result.")
    parser.add_argument("--java", default=os.environ.get("PACK_JAVA", "java"),
                        help="Java 21 executable (default: $PACK_JAVA or java on PATH)")
    parser.add_argument("--timeout", type=int, default=600, help="seconds to wait for the server to finish booting")
    parser.add_argument("--memory", default="4G", help="server heap size")
    parser.add_argument("--max-errors", type=int, default=0, help="error/fatal log lines tolerated before failing")
    parser.add_argument("--quiet", action="store_true", help="do not echo server output")
    args = parser.parse_args()

    pack = tomllib.loads(PACK_TOML.read_text("utf-8"))
    neoforge_version = pack["versions"]["neoforge"]

    major = java_major_version(args.java)
    if major != 21:
        log(f"warning: Java {major} found; Minecraft 1.21.1 targets Java 21, so results may differ from players'")
    install_server(args.java, neoforge_version)
    install_pack(args.java)
    prepare_world(args.memory)
    log("starting server")
    run = run_server(server_command(args.java, neoforge_version), args.timeout, args.quiet)
    report = {
        "pack_version": pack["version"],
        "minecraft": pack["versions"]["minecraft"],
        "neoforge": neoforge_version,
        **run,
        **scan_logs(),
        "lost_cities": lost_cities_dimensions(),
    }

    failures = []
    if report["crashed"]:
        failures.append("server crashed (see run/server/crash-reports)")
    if not report["reached_done"]:
        failures.append("server never reached Done" + (" (timed out)" if report["timed_out"] else ""))
    if report["crash_reports"]:
        failures.append(f"{len(report['crash_reports'])} crash report(s)")
    if not report["clean_stop"]:
        failures.append(f"server did not stop cleanly (exit code {report['exit_code']})")
    if len(report["error_lines"]) > args.max_errors:
        failures.append(f"{len(report['error_lines'])} error line(s) in latest.log (allowed {args.max_errors})")
    if report["reached_done"] and not report["lost_cities"].get("minecraft:overworld"):
        failures.append(f"overworld has no Lost Cities cities near spawn (city hubs per dimension: {report['lost_cities']})")
    if report["reached_done"] and not (report["physics"]["assembled"] and report["physics"]["sub_levels"]):
        failures.append(f"Sable could not assemble a ship, its physics library may not load here: {report['physics']}")
    if report["reached_done"]:
        failures.extend(over_budget(report))
    report["failures"] = failures

    REPORT.write_text(json.dumps(report, indent=2))
    log(f"report written to {REPORT.relative_to(REPO)}")
    if report["reached_done"]:
        log(f"boot: {report['server_reported_seconds']}s (server), {report['wall_seconds_to_done']}s (wall)")
    log(f"{len(report['server_mods'])} server mods, {len(report['error_lines'])} error line(s)")
    log(f"health: {json.dumps(report['health'])}")
    log(f"lost cities: {json.dumps(report['lost_cities'])}")
    log(f"physics: {json.dumps(report['physics'])}")
    for f in failures:
        log(f"FAIL: {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
