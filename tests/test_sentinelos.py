import numpy as np
import pandas as pd
import pytest

from unittest.mock import MagicMock, patch

from backend.collector import validate_process_row
from ml.anomaly_detector import prepare_features, detect_anomalies
from backend.corrective_actions import generate_recommendations


# -------------------------------
# Collector Tests
# -------------------------------

def valid_process_row():
    return {
        "pid": "123",
        "ppid": "1",
        "start_ticks": "1000",
        "name": "test_process",
        "state": "R",
        "memory_kb": "2048",
        "read_rate": "100",
        "write_rate": "200",
        "cpu_usage": "25.5"
    }


def test_valid_process_row():
    result = validate_process_row(valid_process_row(), 2)

    assert result["pid"] == 123
    assert result["ppid"] == 1
    assert result["name"] == "test_process"
    assert result["cpu_usage"] == 25.5


def test_invalid_pid_is_rejected():
    row = valid_process_row()
    row["pid"] = "-5"

    with pytest.raises(ValueError):
        validate_process_row(row, 2)


def test_cpu_above_100_is_rejected():
    row = valid_process_row()
    row["cpu_usage"] = "150"

    with pytest.raises(ValueError):
        validate_process_row(row, 2)


def test_negative_memory_is_rejected():
    row = valid_process_row()
    row["memory_kb"] = "-100"

    with pytest.raises(ValueError):
        validate_process_row(row, 2)


def test_missing_process_name_is_rejected():
    row = valid_process_row()
    row["name"] = ""

    with pytest.raises(ValueError):
        validate_process_row(row, 2)


# -------------------------------
# ML Feature Preparation Tests
# -------------------------------

def test_prepare_features_returns_expected_columns():
    data = pd.DataFrame({
        "cpu_usage": [10, 20],
        "memory_usage": [100, 200],
        "read_rate": [50, 100],
        "write_rate": [25, 50]
    })

    result = prepare_features(data)

    assert list(result.columns) == [
        "cpu_usage",
        "memory_usage",
        "read_rate",
        "write_rate"
    ]


def test_prepare_features_applies_log_transformation():
    data = pd.DataFrame({
        "cpu_usage": [10],
        "memory_usage": [100],
        "read_rate": [50],
        "write_rate": [25]
    })

    result = prepare_features(data)

    assert result["memory_usage"].iloc[0] == pytest.approx(np.log1p(100))
    assert result["read_rate"].iloc[0] == pytest.approx(np.log1p(50))


def test_prepare_features_handles_missing_values():
    data = pd.DataFrame({
        "cpu_usage": [10, np.nan, 30],
        "memory_usage": [100, 200, 300],
        "read_rate": [50, 60, 70],
        "write_rate": [20, 30, 40]
    })

    result = prepare_features(data)

    assert not result.isnull().any().any()


# -------------------------------
# Anomaly Detection Tests
# -------------------------------

def test_detector_skips_insufficient_samples():
    data = pd.DataFrame({
        "process_id": range(1, 30),
        "pid": range(101, 130),
        "name": ["test_process"] * 29,
        "os_type": ["Linux"] * 29,
        "cpu_usage": [10.0] * 29,
        "memory_usage": [100.0] * 29,
        "read_rate": [50.0] * 29,
        "write_rate": [20.0] * 29,
        "recorded_at": pd.date_range("2026-01-01", periods=29, freq="min")
    })

    result = detect_anomalies(data)

    assert result.empty


# -------------------------------
# Corrective Action Tests
# -------------------------------

def test_no_recommendations_when_no_anomalies():
    connection = MagicMock()
    cursor = MagicMock()

    connection.cursor.return_value = cursor
    cursor.fetchall.return_value = []

    with patch(
        "backend.corrective_actions.get_connection",
        return_value=connection
    ):
        generate_recommendations()

    connection.commit.assert_called_once()
    cursor.execute.assert_called_once()
    connection.rollback.assert_not_called()
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_recommendation_is_created_safely():
    connection = MagicMock()
    cursor = MagicMock()

    connection.cursor.return_value = cursor

    cursor.fetchall.return_value = [{
        "anomaly_id": 10,
        "process_id": 20,
        "severity": "MEDIUM",
        "description": "Unusual resource usage",
        "pid": 123,
        "name": "test_process",
        "os_type": "Linux"
    }]

    with patch(
        "backend.corrective_actions.get_connection",
        return_value=connection
    ):
        generate_recommendations()

    assert cursor.execute.call_count == 2

    insert_parameters = cursor.execute.call_args[0][1]

    assert insert_parameters[0] == 20
    assert insert_parameters[1] == 10
    assert insert_parameters[2] == "MANUAL_REVIEW"
    assert insert_parameters[4] == "PENDING_APPROVAL"

    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    cursor.close.assert_called_once()
    connection.close.assert_called_once()
