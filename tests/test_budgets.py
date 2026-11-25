import boot_server


def report(seconds=8.0, tps=20.0, med=1.5, p95=3.0, heap="1008.0 MB"):
    return {"server_reported_seconds": seconds,
            "health": {"tps_5s": tps, "mspt_10s": {"med": med, "p95": p95}, "heap_used": heap}}


def test_a_healthy_boot_is_within_budget():
    assert boot_server.over_budget(report()) == []


def test_each_budget_is_enforced():
    assert len(boot_server.over_budget(report(seconds=90))) == 1
    assert len(boot_server.over_budget(report(tps=15.0))) == 1
    assert len(boot_server.over_budget(report(med=30.0))) == 1
    assert len(boot_server.over_budget(report(p95=80.0))) == 1
    assert len(boot_server.over_budget(report(heap="3.5 GB"))) == 1


def test_missing_health_is_not_a_failure():
    assert boot_server.over_budget({"server_reported_seconds": 8.0, "health": {}}) == []
