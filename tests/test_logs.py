import boot_server
import gamelog


def test_parse_health_reads_spark_report():
    lines = [
        "> TPS from last 5s, 10s, 1m, 5m, 15m:",
        " *20.0, 20.0, 20.0, 20.0, 20.0",
        "> Tick durations (min/med/95%ile/max ms) from last 10s, 1m:",
        " 0.6/1.4/8.1/51.9;  0.6/1.4/8.1/51.9",
        "> Memory usage:",
        " 684.6 MB / 6.0 GB   (11%)",
    ]
    assert boot_server.parse_health(lines) == {
        "tps_5s": 20.0,
        "mspt_10s": {"min": 0.6, "med": 1.4, "p95": 8.1, "max": 51.9},
        "heap_used": "684.6 MB",
    }


def test_error_lines_only_takes_error_and_fatal():
    log = "\n".join([
        "[t] [Server thread/INFO] [x/]: fine",
        "[t] [Server thread/ERROR] [x/]: broken",
        "[t] [main/FATAL] [x/]: very broken",
        "[t] [Render thread/WARN] [x/]: careful",
    ])
    assert gamelog.error_lines(log) == [
        "[t] [Server thread/ERROR] [x/]: broken",
        "[t] [main/FATAL] [x/]: very broken",
    ]


def test_known_upstream_errors_match_by_text():
    text, issue = next(iter(gamelog.KNOWN_UPSTREAM_ERRORS.items()))
    assert gamelog.known_upstream(f"[t] [Server thread/ERROR] [x/]: {text} at 1,2,3") == issue
    assert gamelog.known_upstream("[t] [Server thread/ERROR] [x/]: something else") is None
