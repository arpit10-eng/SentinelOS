import csv
import subprocess

from backend.db import get_connection


def collect_processes():
    result = subprocess.run(
        ["./os_monitor/process_monitor", "--csv", "--once"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("Process monitor failed:")
        print(result.stderr)
        return

    lines = result.stdout.strip().splitlines()

    if not lines:
        print("No process data received.")
        return

    reader = csv.DictReader(lines)

    required_columns = {
        "pid",
        "ppid",
        "start_ticks",
        "name",
        "state",
        "cpu_usage",
        "memory_kb",
        "read_rate",
        "write_rate"
    }

    if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
        print("Error: Process monitor CSV is missing required columns.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        for row in reader:
            pid = int(row["pid"])
            start_ticks = int(row["start_ticks"])

            cursor.execute(
                """
                INSERT INTO processes
                    (pid, ppid, name, state, start_ticks)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    ppid = VALUES(ppid),
                    name = VALUES(name),
                    state = VALUES(state)
                """,
                (
                    pid,
                    int(row["ppid"]),
                    row["name"],
                    row["state"],
                    start_ticks
                )
            )

            cursor.execute(
                """
                SELECT process_id
                FROM processes
                WHERE pid = %s AND start_ticks = %s
                """,
                (pid, start_ticks)
            )

            process_row = cursor.fetchone()

            if process_row is None:
                raise RuntimeError(
                    f"Could not find database record for PID {pid}"
                )

            process_id = process_row[0]

            cursor.execute(
                """
                INSERT INTO resource_usage
                    (process_id, cpu_usage, memory_usage,
                     read_bytes, write_bytes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    process_id,
                    float(row["cpu_usage"]),
                    int(row["memory_kb"]),
                    int(row["read_rate"]),
                    int(row["write_rate"])
                )
            )

        connection.commit()
        print("Process data successfully stored in MySQL.")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    collect_processes()
