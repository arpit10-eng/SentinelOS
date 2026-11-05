import csv
from datetime import datetime, timezone
from pathlib import Path

from backend.db import get_connection


CSV_FILE = Path(__file__).resolve().parent.parent / "os_monitor" / "windows_processes.csv"


def map_state(status):
    status = (status or "").strip().lower()

    if status == "running":
        return "R"
    if status in ("stopped", "sleeping"):
        return "S"
    if status == "disk-sleep":
        return "D"
    if status == "zombie":
        return "Z"

    return "U"


def get_start_ticks(pid, create_time):
    if create_time <= 0:
        return -pid - 1

    return int(datetime.fromtimestamp(
        create_time, tz=timezone.utc
    ).timestamp() * 1_000_000)


def ingest_windows_processes():
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"Windows process CSV not found: {CSV_FILE}")

    connection = get_connection()
    cursor = connection.cursor()
    processed = 0

    try:
        with CSV_FILE.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            required_columns = {
                "pid",
                "ppid",
                "name",
                "status",
                "memory_mb",
                "create_time",
                "cpu_usage",
                "read_rate",
                "write_rate",
            }

            if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
                raise ValueError("Windows process CSV is missing required columns.")

            for line_number, row in enumerate(reader, start=2):
                try:
                    pid = int(row["pid"])
                    ppid = int(row["ppid"])
                    name = row["name"].strip()
                    memory_mb = float(row["memory_mb"])
                    create_time = float(row["create_time"])
                    cpu_usage = float(row["cpu_usage"])
                    read_rate = int(row["read_rate"])
                    write_rate = int(row["write_rate"])

                    if pid < 0 or ppid < 0:
                        raise ValueError("PID and PPID cannot be negative.")

                    if not name:
                        raise ValueError("Process name cannot be empty.")

                    if min(memory_mb, create_time, cpu_usage, read_rate, write_rate) < 0:
                        raise ValueError("Resource measurements cannot be negative.")

                except (TypeError, ValueError, KeyError) as error:
                    raise ValueError(
                        f"Invalid CSV record on line {line_number}: {error}"
                    ) from error

                start_ticks = get_start_ticks(pid, create_time)
                state = map_state(row["status"])
                memory_kb = round(memory_mb * 1024)

                cursor.execute(
                    """
                    INSERT INTO processes
                        (pid, ppid, name, state, start_ticks, os_type)
                    VALUES (%s, %s, %s, %s, %s, 'Windows')
                    ON DUPLICATE KEY UPDATE
                        ppid = VALUES(ppid),
                        name = VALUES(name),
                        state = VALUES(state)
                    """,
                    (pid, ppid, name, state, start_ticks),
                )

                cursor.execute(
                    """
                    SELECT process_id
                    FROM processes
                    WHERE os_type = 'Windows'
                      AND pid = %s
                      AND start_ticks = %s
                    """,
                    (pid, start_ticks),
                )

                process_row = cursor.fetchone()

                if process_row is None:
                    raise RuntimeError(f"Could not find Windows process PID {pid}")

                cursor.execute(
                    """
                    INSERT INTO resource_usage
                        (process_id, cpu_usage, memory_usage, read_rate, write_rate)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        process_row[0],
                        cpu_usage,
                        memory_kb,
                        read_rate,
                        write_rate,
                    ),
                )

                processed += 1

        connection.commit()

        print("Windows process data successfully stored in MySQL.")
        print(f"Windows processes processed: {processed}")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    ingest_windows_processes()
