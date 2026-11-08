import argparse
import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest

from backend.db import get_connection
from datetime import datetime


FEATURES = [
    "cpu_usage",
    "memory_usage",
    "read_rate",
    "write_rate"
]

MINIMUM_SAMPLES = 30
CONTAMINATION = 0.05


def fetch_resource_data():
    connection = get_connection()

    query = """
        SELECT
            p.process_id,
            p.pid,
            p.name,
            p.os_type,
            ru.cpu_usage,
            ru.memory_usage,
            ru.read_rate,
            ru.write_rate,
            ru.recorded_at
        FROM resource_usage ru
        JOIN processes p
            ON ru.process_id = p.process_id
        WHERE ru.cpu_usage IS NOT NULL
          AND ru.memory_usage IS NOT NULL
          AND ru.read_rate IS NOT NULL
          AND ru.write_rate IS NOT NULL
        ORDER BY ru.recorded_at
    """

    try:
        data = pd.read_sql(query, connection)
    finally:
        connection.close()

    return data


def prepare_features(data):
    features = data[FEATURES].copy()

    for column in FEATURES:
        features[column] = pd.to_numeric(
            features[column],
            errors="coerce"
        )

    features = features.replace([np.inf, -np.inf], np.nan)

    features = features.fillna(features.median())

    # Log transformation reduces the effect of extremely large
    # memory and disk-I/O values.
    for column in ["memory_usage", "read_rate", "write_rate"]:
        features[column] = np.log1p(
            features[column].clip(lower=0)
        )

    return features


def detect_anomalies(data):
    results = []

    for os_type, os_data in data.groupby("os_type"):
        os_data = os_data.copy()

        if len(os_data) < MINIMUM_SAMPLES:
            print(
                f"Skipping {os_type}: only {len(os_data)} samples available."
            )
            continue

        features = prepare_features(os_data)

        model = IsolationForest(
            n_estimators=100,
            contamination=CONTAMINATION,
            random_state=42
        )

        model.fit(features)

        # Get the most recent observation for each process.
        latest = (
            os_data.sort_values("recorded_at")
            .groupby("process_id", as_index=False)
            .tail(1)
            .copy()
        )

        latest_features = prepare_features(latest)

        predictions = model.predict(latest_features)
        scores = model.decision_function(latest_features)

        latest["is_anomaly"] = predictions == -1
        latest["anomaly_score"] = scores

        results.append(latest)

    if not results:
        return pd.DataFrame()

    return pd.concat(results, ignore_index=True)



def save_anomalies(anomalies):
    if anomalies.empty:
        print("\\nNo anomalies to save.")
        return

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    saved_count = 0

    try:
        for _, row in anomalies.iterrows():
            process_id = int(row["process_id"])
            pid = int(row["pid"])
            name = str(row["name"])
            os_type = str(row["os_type"])

            anomaly_type = "ML_STATISTICAL_ANOMALY"
            severity = "MEDIUM"

            description = (
                f"Unusual resource usage detected for {name} "
                f"(PID: {pid}, OS: {os_type}). "
                f"CPU: {row['cpu_usage']}%, "
                f"Memory: {row['memory_usage']} KB, "
                f"Read rate: {row['read_rate']}, "
                f"Write rate: {row['write_rate']}."
            )

            cursor.execute(
                """
                SELECT anomaly_id
                FROM anomalies
                WHERE process_id = %s
                  AND anomaly_type = %s
                  AND detected_at >= NOW() - INTERVAL 5 MINUTE
                LIMIT 1
                """,
                (process_id, anomaly_type)
            )

            if cursor.fetchone():
                continue

            cursor.execute(
                """
                INSERT INTO anomalies
                (process_id, anomaly_type, severity, description)
                VALUES (%s, %s, %s, %s)
                """,
                (process_id, anomaly_type, severity, description)
            )

            anomaly_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO alerts
                (anomaly_id, process_id, message, severity, status)
                VALUES (%s, %s, %s, %s, 'ACTIVE')
                """,
                (anomaly_id, process_id, description, severity)
            )

            saved_count += 1

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    print(f"\\nNew anomalies saved: {saved_count}")
    print(f"New alerts generated: {saved_count}")


def main():
    parser = argparse.ArgumentParser(
        description="SentinelOS ML Anomaly Detector"
    )

    parser.add_argument(
        "--show-normal",
        action="store_true",
        help="Display normal process records as well."
    )

    args = parser.parse_args()

    print("\n===== SentinelOS ML Anomaly Detector =====\n")

    data = fetch_resource_data()

    if data.empty:
        print("No usable resource-usage data found.")
        return

    print(f"Historical records loaded: {len(data)}")

    results = detect_anomalies(data)

    if results.empty:
        print("Not enough data to train the anomaly detector.")
        return

    anomalies = results[results["is_anomaly"]]

    print(f"\nProcesses evaluated: {len(results)}")
    print(f"Anomalies detected: {len(anomalies)}")

    save_anomalies(anomalies)

    if args.show_normal:
        display_data = results
    else:
        display_data = anomalies

    if display_data.empty:
        print("\nNo anomalies detected in the latest process samples.")
        return

    print("\n===== Detection Results =====\n")

    columns = [
        "os_type",
        "pid",
        "name",
        "cpu_usage",
        "memory_usage",
        "read_rate",
        "write_rate",
        "anomaly_score",
        "is_anomaly"
    ]

    print(
        display_data[columns].to_string(index=False)
    )


if __name__ == "__main__":
    main()
