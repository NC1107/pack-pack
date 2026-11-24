#!/usr/bin/env python3
"""Install the client side of the pack, launch the real client, join a world, and report.

    python3 tools/boot_client.py --java /path/to/java21/bin/java --hmc-java /path/to/java25/bin/java

HeadlessMC launches the game and mc-runtime-test drives it: once the client is up it
creates a singleplayer world, waits for the player to load and tick, then quits.
Writes run/client-report.json and exits 1 if the client crashes, never finishes,
or logs more errors than --max-errors allows.

The game renders for real on a virtual X display, so it needs xvfb-run
(Ubuntu: xvfb, Fedora: xorg-x11-server-Xvfb). There is no display-less mode:
HeadlessMC's -lwjgl swaps LWJGL for a stub that Sodium refuses to start on, and
with an offline account HeadlessMC forces that mode unless it runs under Xvfb.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import gamelog
from downloads import CACHE, cached_download, packwiz_bootstrap, packwiz_installer

REPO = Path(__file__).resolve().parent.parent
PACK_TOML = REPO / "pack" / "pack.toml"
RUN = REPO / "run"
GAME_DIR = RUN / "client"
HMC_DIR = RUN / "headlessmc"
REPORT = RUN / "client-report.json"
# Minecraft's versions and libraries, kept in .cache so CI can cache them between runs.
MINECRAFT_DIR = CACHE / "minecraft"

# HeadlessMC itself needs Java 25; the game runs on the pack's Java 21.
HEADLESSMC_URL = "https://github.com/headlesshq/headlessmc/releases/download/3.0.0-RC9/headlessmc.jar"
HEADLESSMC_SHA256 = "a343a7c51e48c566a5cd408bd0012ddf091ea105ecc31daff00af600d3a7218a"
RUNTIME_TEST_URL = ("https://github.com/headlesshq/mc-runtime-test-mod/releases/download/"
                    "1.21.1-5.1.0/mc-runtime-test-1.21.1-neoforge-5.1.0.jar")
RUNTIME_TEST_SHA256 = "95a54e65f4e4b61cf663c652f0eacefdda05ce57de25c796a6bd8d1264097cd0"
NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge"

SUCCESS_LINE = "Successfully finished."

# Errors that come from the test environment rather than the pack: CI plays with an
# offline account and has no audio device. Anything else still fails the run.
ENVIRONMENT_ERRORS = (
    "Failed to fetch user properties",
    "Error starting SoundSystem",
    "Couldn't connect to realms",
    "Failed to retrieve profile key pair",
)
XVFB_SCREEN = "-screen 0 1920x1080x24 +extension GLX +render -noreset"


def log(msg: str) -> None:
    print(f"[client] {msg}", flush=True)


def java_home(java: str) -> Path:
    resolved = shutil.which(java)
    if not resolved:
        raise SystemExit(f"java not found: {java}")
    return Path(resolved).resolve().parent.parent


# Xaero's World Map 1.47.0 deadlocks when the world unloads while it is loading regions from the
# world save: its loader thread holds a lock and waits for a task on the render thread, which is
# blocked waiting for the server thread, which waits for that lock. The test quits right after
# joining, so it hits this almost every time. The thread dump is in the plan. Players can hit it
# too, only less often, so this is a test workaround and not a fix.
KNOWN_HANG_MODS = ["xaeroworldmap"]


def exclude_known_hang_mods() -> None:
    for prefix in KNOWN_HANG_MODS:
        for jar in (GAME_DIR / "mods").glob(f"{prefix}*.jar"):
            jar.unlink()
            log(f"excluded {jar.name} from the client test, known shutdown deadlock (docs/plan.md)")


def install_pack(java: str) -> None:
    if GAME_DIR.exists():
        shutil.rmtree(GAME_DIR)
    GAME_DIR.mkdir(parents=True)
    shutil.copy(packwiz_installer(), GAME_DIR / "packwiz-installer.jar")
    log("installing client-side mods with packwiz-installer")
    subprocess.run([java, "-jar", str(packwiz_bootstrap()), "--bootstrap-no-update", "-g", "-s", "client",
                    PACK_TOML.as_uri()], cwd=GAME_DIR, check=True)
    shutil.copy(cached_download(RUNTIME_TEST_URL, RUNTIME_TEST_SHA256), GAME_DIR / "mods")
    exclude_known_hang_mods()
    with (GAME_DIR / "options.txt").open("a") as options:
        # An unfocused virtual display would otherwise pause the game before the test can finish.
        options.write("pauseOnLostFocus:false\n")
        # The test quits right after joining. With the default view distance the server is still
        # generating chunks (domes are heavy) and the vanilla unload loop can spin forever on
        # a chunk that is still being generated, so keep the amount of generation small.
        options.write("renderDistance:6\nsimulationDistance:5\n")


def configure_headlessmc(game_java: str) -> dict:
    HMC_DIR.mkdir(parents=True, exist_ok=True)
    MINECRAFT_DIR.mkdir(parents=True, exist_ok=True)
    (HMC_DIR / "config.properties").write_text("\n".join([
        f"hmc.java.versions={java_home(game_java).as_posix()}",
        f"hmc.files.game={GAME_DIR.as_posix()}",
        "hmc.files.game-for-each-version=false",
        f"hmc.files.mc={MINECRAFT_DIR.as_posix()}",
        "hmc.jline.enabled=false",
        "hmc.launcher.crash-report-watcher=true",
        "hmc.assets.dummy=true",
        "",
    ]))
    return {**os.environ, "HMC_FILES_LOCATION": str(HMC_DIR)}


def install_neoforge(hmc_java: str, hmc: Path, env: dict, minecraft: str, neoforge: str) -> None:
    installer = f"{NEOFORGE_MAVEN}/{neoforge}/neoforge-{neoforge}-installer.jar"
    log(f"installing NeoForge {neoforge} client")
    subprocess.run([hmc_java, "-jar", str(hmc), "version", "install", "neoforge", minecraft, "-u", installer],
                   cwd=RUN, env=env, check=True, stdin=subprocess.DEVNULL)
    installed = [p.name for p in (MINECRAFT_DIR / "versions").iterdir() if "neoforge" in p.name.lower()]
    if not any(neoforge in name for name in installed):
        raise SystemExit(f"HeadlessMC installed {installed}, expected NeoForge {neoforge}")


def game_pids() -> list[int]:
    """Java processes running this test's game directory (Linux /proc)."""
    pids = []
    for proc_dir in Path("/proc").iterdir():
        if not proc_dir.name.isdigit():
            continue
        try:
            cmdline = (proc_dir / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            continue
        if "java" in cmdline and str(GAME_DIR) in cmdline:
            pids.append(int(proc_dir.name))
    return pids


def dump_threads(game_java: str) -> None:
    """Save a thread dump of every hung game JVM, so a timeout shows where it is stuck."""
    jcmd = java_home(game_java) / "bin" / "jcmd"
    dumps = []
    for pid in game_pids():
        result = subprocess.run([str(jcmd), str(pid), "Thread.print"], capture_output=True, text=True, timeout=60)
        dumps.append(f"===== pid {pid} =====\n{result.stdout}{result.stderr}")
    (RUN / "client-threads.txt").write_text("\n".join(dumps) or "no game JVM found\n")
    log(f"saved thread dumps of {len(dumps)} JVM(s) to run/client-threads.txt")


def launch(hmc_java: str, game_java: str, hmc: Path, env: dict, minecraft: str, memory: str, timeout: int) -> dict:
    jvm = f"-Djava.awt.headless=true -Xmx{memory}"
    cmd = ["xvfb-run", "-a", "-s", XVFB_SCREEN, hmc_java, "-Dhmc.xvfb.check=true", "-jar", str(hmc),
           "launch", "--offline", "--jvm", jvm, "neoforge", minecraft]
    log("launching the client on a virtual display")
    started = time.monotonic()
    launcher_log = RUN / "client-launcher.log"
    # Its own process group, so a timeout can take down xvfb, HeadlessMC, the game
    # and anything the game spawned, instead of leaving them holding the output open.
    with launcher_log.open("w", encoding="utf-8") as out:
        proc = subprocess.Popen(cmd, cwd=RUN, env=env, stdin=subprocess.DEVNULL, stdout=out,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            exit_code, timed_out = proc.wait(timeout=timeout), False
        except subprocess.TimeoutExpired:
            dump_threads(game_java)
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            exit_code, timed_out = None, True
    return {"exit_code": exit_code, "timed_out": timed_out, "wall_seconds": round(time.monotonic() - started, 1)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Boot the pack's client, join a world, and report the result.")
    parser.add_argument("--java", default=os.environ.get("PACK_JAVA", "java"),
                        help="Java 21 for the game (default: $PACK_JAVA or java on PATH)")
    parser.add_argument("--hmc-java", default=os.environ.get("HMC_JAVA", "java"),
                        help="Java 25 for HeadlessMC (default: $HMC_JAVA or java on PATH)")
    parser.add_argument("--memory", default="4G", help="client heap size")
    parser.add_argument("--timeout", type=int, default=900, help="seconds before the run counts as hung")
    parser.add_argument("--max-errors", type=int, default=0, help="error/fatal log lines tolerated before failing")
    args = parser.parse_args()

    if not shutil.which("xvfb-run"):
        raise SystemExit("xvfb-run not found (Ubuntu: apt install xvfb, Fedora: dnf install xorg-x11-server-Xvfb)")

    pack = tomllib.loads(PACK_TOML.read_text("utf-8"))
    minecraft, neoforge = pack["versions"]["minecraft"], pack["versions"]["neoforge"]

    hmc = cached_download(HEADLESSMC_URL, HEADLESSMC_SHA256)
    install_pack(args.java)
    env = configure_headlessmc(args.java)
    install_neoforge(args.hmc_java, hmc, env, minecraft, neoforge)
    run = launch(args.hmc_java, args.java, hmc, env, minecraft, args.memory, args.timeout)

    game_log = gamelog.read_log(GAME_DIR)
    all_errors = gamelog.error_lines(game_log)
    environment_errors = [line for line in all_errors if any(known in line for known in ENVIRONMENT_ERRORS)]
    upstream_errors = [line for line in all_errors if gamelog.known_upstream(line)]
    report = {
        "pack_version": pack["version"],
        "minecraft": minecraft,
        "neoforge": neoforge,
        **run,
        "finished": SUCCESS_LINE in game_log,
        "startup_seconds": gamelog.seconds(gamelog.GAME_TOOK, game_log),
        "menu_to_world_seconds": gamelog.seconds(gamelog.MENU_TO_WORLD, game_log),
        "client_mods": gamelog.mod_jars(GAME_DIR),
        "error_lines": [line for line in all_errors if line not in environment_errors + upstream_errors],
        "environment_error_lines": environment_errors,
        "known_upstream_error_lines": upstream_errors,
        "crash_reports": gamelog.crash_reports(GAME_DIR),
    }

    failures = []
    if run["timed_out"]:
        failures.append(f"client did not finish within {args.timeout}s")
    if not report["finished"]:
        failures.append("client never joined a world and finished the runtime test")
    if run["exit_code"] not in (0, None):
        failures.append(f"launcher exited with code {run['exit_code']}")
    if report["crash_reports"]:
        failures.append(f"{len(report['crash_reports'])} crash report(s)")
    if len(report["error_lines"]) > args.max_errors:
        failures.append(f"{len(report['error_lines'])} error line(s) in latest.log (allowed {args.max_errors})")
    report["failures"] = failures

    REPORT.write_text(json.dumps(report, indent=2))
    log(f"report written to {REPORT.relative_to(REPO)}")
    log(f"startup {report['startup_seconds']}s, menu to world {report['menu_to_world_seconds']}s, "
        f"{len(report['client_mods'])} client mods, {len(report['error_lines'])} error line(s), "
        f"{len(environment_errors)} environment-only, {len(upstream_errors)} known upstream")
    for line in report["error_lines"][:10]:
        log(f"error: {line}")
    for failure in failures:
        log(f"FAIL: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
