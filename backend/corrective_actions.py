from backend.db import get_connection


def generate_recommendations():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    created_count = 0

    try:
        cursor.execute(
            """
            SELECT
                a.anomaly_id,
                a.process_id,
                a.severity,
                a.description,
                p.pid,
                p.name,
                p.os_type
            FROM anomalies a
            JOIN processes p
                ON a.process_id = p.process_id
            LEFT JOIN corrective_actions ca
                ON a.anomaly_id = ca.anomaly_id
            WHERE ca.action_id IS NULL
            ORDER BY a.detected_at DESC
            """
        )

        anomalies = cursor.fetchall()

        for anomaly in anomalies:
            reason = (
                f"Statistical anomaly detected for "
                f"{anomaly['name']} "
                f"(PID: {anomaly['pid']}, "
                f"OS: {anomaly['os_type']}). "
                f"Manual review and fresh resource measurement "
                f"are recommended before taking action. "
                f"Original finding: {anomaly['description']}"
            )

            cursor.execute(
                """
                INSERT INTO corrective_actions
                (
                    process_id,
                    anomaly_id,
                    action_type,
                    reason,
                    status
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    anomaly["process_id"],
                    anomaly["anomaly_id"],
                    "MANUAL_REVIEW",
                    reason,
                    "PENDING_APPROVAL"
                )
            )

            created_count += 1

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    print(f"New recommendations created: {created_count}")


if __name__ == "__main__":
    print("\n===== SentinelOS Corrective Action Engine =====\n")
    generate_recommendations()
