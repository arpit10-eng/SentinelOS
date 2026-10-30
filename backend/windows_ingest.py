import csv
from pathlib import Path

from backend.db import get_connection


CSV_FILE = Path(__file__).resolve().parent.parent / "os_monitor" / "windows_processes.csv"


def map_state(status):
    status = (status or "").strip().lower()

    if status == "running":
        return "R"
    if status == "stopped":
        return "S"
    if status == "sleeping":
        return "S"
    if status == "disk-sleep":
        return "D"
    if status == "zombie":
        return "Z"

    return "U"


def ingest_windows_processes():
    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"Windows process CSV not found: {CSV_FILE}"
        )

    connection = get_connection()
    cursor = connection.cursor()
    inserted = 0

    try:
        with CSV_FILE.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            required_columns = {
                "pid",
                "ppid",
                "name",
                "status",
                "memory_mb",
            }

            if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
                raise ValueError("Windows process CSV is missing required columns.")

            for line_number, row in enumerate(reader, start=2):
                try:
                    pid = int(row["pid"])
                    ppid = int(row["ppid"])
                    name = row["name"].strip()
                    memory_mb = float(row["memory_mb"])

                    if pid < 0 or ppid < 0:
                        raise ValueError("PID and PPID cannot be negative.")
                    if not name:
                        raise ValueError("Process name cannot be empty.")
                    if memory_mb < 0:
                        raise ValueError("Memory usage cannot be negative.")

                except (TypeError, ValueError, KeyError) as error:
                    raise ValueError(
                        f"Invalid Windows process CSV record on line {line_number}: {error}"
                    ) from error

                state = map_state(row["status"])

                # Windows PIDs can overlap with Linux PIDs.
                # Use a negative start_ticks value to keep Windows
                # records separate under the existing unique key.
                windows_start_ticks = -pid - 1

                cursor.execute(
                    """
                    INSERT INTO processes
                        (pid, ppid, name, state, start_ticks, os_type)
                    VALUES (%s, %s, %s, %s, %s, 'Windows')
                    ON DUPLICATE KEY UPDATE
                        ppid = VALUES(ppid),
                        name = VALUES(name),
                        state = VALUES(state),
                        os_type = 'Windows'
                    """,
                    (pid, ppid, name, state, windows_start_ticks),
                )

                cursor.execute(
                    """
                    SELECT process_id
                    FROM processes
                    WHERE pid = %s
                      AND start_ticks = %s
                      AND os_type = 'Windows'
                    """,
                    (pid, windows_start_ticks),
                )

                process_row = cursor.fetchone()
                if process_row is None:
                    raise RuntimeError(
                        f"Could not find Windows database record for PID {pid}"
                    )

                process_id = process_row[0]
                memory_kb = round(memory_mb * 1024)

                cursor.execute(
                    """
                    INSERT INTO resource_usage
                        (process_id, cpu_usage, memory_usage, read_rate, write_rate)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (process_id, None, memory_kb, 0, 0),
                )

                inserted += 1

        connection.commit()
        print("Windows process data successfully stored in MySQL.")
        print(f"Windows processes processed: {inserted}")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    ingest_windows_processes()
