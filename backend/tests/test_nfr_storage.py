import json
from pathlib import Path

import pytest

from app.core.storage_report import (
    GIB,
    directory_size,
    evaluate_storage,
    report_to_dict,
)

pytestmark = pytest.mark.nfr


@pytest.mark.parametrize(
    ("usage_gb", "expected_status", "expected_exit"),
    [
        pytest.param(0.0, "ok", 0, id="empty"),
        pytest.param(50.0, "ok", 0, id="half"),
        pytest.param(79.99, "ok", 0, id="below-alert"),
        pytest.param(80.0, "warning", 2, id="at-alert"),
        pytest.param(99.99, "warning", 2, id="below-quota"),
        pytest.param(100.0, "critical", 1, id="at-quota"),
        pytest.param(120.0, "critical", 1, id="over-quota"),
    ],
)
def test_storage_thresholds(
    usage_gb: float,
    expected_status: str,
    expected_exit: int,
) -> None:
    used_bytes = int(usage_gb * GIB)

    report = evaluate_storage(used_bytes, used_bytes)

    assert report.status == expected_status
    assert report.exit_code == expected_exit
    assert abs(report.usage_percent - usage_gb) < 0.01


def test_storage_discrepancy_warns() -> None:
    report = evaluate_storage(10 * GIB, 20 * GIB)

    assert report.usage_percent == 20.0
    assert report.discrepancy_percent == 50.0
    assert report.status == "warning"
    assert report.exit_code == 2
    assert any("Diferencia" in warning for warning in report.warnings)


def test_storage_small_discrepancy_is_ok() -> None:
    report = evaluate_storage(10 * GIB, int(10.4 * GIB))

    assert report.discrepancy_percent < 5
    assert report.status == "ok"
    assert report.exit_code == 0


def test_storage_critical_wins_over_discrepancy() -> None:
    report = evaluate_storage(100 * GIB, 120 * GIB)

    assert report.status == "critical"
    assert report.exit_code == 1
    assert len(report.warnings) == 2


def test_directory_size_sums_files(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"x" * 10)
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.bin").write_bytes(b"y" * 20)

    assert directory_size(tmp_path) == 30
    assert directory_size(tmp_path / "missing") == 0


def test_storage_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError):
        evaluate_storage(0, 0, quota_gb=0)
    with pytest.raises(ValueError):
        evaluate_storage(0, 0, alert_percent=101)


def test_storage_report_is_json_serializable() -> None:
    report = evaluate_storage(int(50 * GIB), int(50 * GIB))

    payload = json.dumps(report_to_dict(report))

    assert '"status": "ok"' in payload
    assert '"quota_gb": 100.0' in payload
