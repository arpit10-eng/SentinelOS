import csv
import subprocess

from backend.db import get_connection


def collect_processes():
    result = subprocess.run(
        ["./os_monitor/process_monitor", "--csv", "--once"],
        capture_output=True,
        text=True
    )

    lines = result.stdout.strip().splitlines()

    if not lines:
        return

    reader = csv.DictReader(lines)

    connection = get_connection()
    cursor = connection.cursor()

    for row in reader:
        cursor.execute(
            """
            INSERT INTO processes
            (pid, ppid, name, state)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                ppid = VALUES(ppid),
                name = VALUES(name),
                state = VALUES(state)
            """,
            (
                int(row["pid"]),
                int(row["ppid"]),
                row["name"],
                row["state"]
            )
        )

        cursor.execute(
            """
            SELECT process_id
            FROM processes
            WHERE pid = %s
            """,
            (int(row["pid"]),)
        )

        process_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO resource_usage
            (process_id, cpu_usage, memory_usage, read_bytes, write_bytes)
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

    cursor.close()
    connection.close()

    print("Process data successfully stored in MySQL.")


if __name__ == "__main__":
    collect_processes()
