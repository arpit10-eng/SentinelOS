import csv
import subprocess

from backend.db import get_connection

def validate_process_row(row, line_number):
    """Validate and convert one process CSV record."""
    try:
        pid = int(row["pid"])
        ppid = int(row["ppid"])
        start_ticks = int(row["start_ticks"])
        memory_kb = int(row["memory_kb"])
        read_rate = int(row["read_rate"])
        write_rate = int(row["write_rate"])
        cpu_usage = float(row["cpu_usage"])

        name = row["name"].strip()
        state = row["state"].strip()

        if pid <= 0 or ppid < 0 or start_ticks < 0:
            raise ValueError("invalid PID, PPID, or start_ticks")

        if memory_kb < 0 or read_rate < 0 or write_rate < 0:
            raise ValueError("memory and I/O rates cannot be negative")

        if not 0 <= cpu_usage <= 100:
            raise ValueError("CPU usage must be between 0 and 100")

        if not name or len(state) != 1:
            raise ValueError("missing process name or invalid state")

        return {
            "pid": pid,
            "ppid": ppid,
            "start_ticks": start_ticks,
            "name": name,
            "state": state,
            "memory_kb": memory_kb,
            "read_rate": read_rate,
            "write_rate": write_rate,
            "cpu_usage": cpu_usage,
        }

    except (TypeError, ValueError, KeyError) as error:
        raise ValueError(
            f"Invalid process CSV record on line {line_number}: {error}"
        ) from error

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

    try:
        connection = get_connection()
    except RuntimeError as error:
        print(error)
        return

    cursor = connection.cursor()

    try:
        for line_number, row in enumerate(reader, start=2):
            try:
                row = validate_process_row(row, line_number)
            except ValueError as error:
                raise ValueError(
                    f"Process collection stopped: {error}"
                ) from error

            pid = row["pid"]
            start_ticks = row["start_ticks"]

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
                    row["ppid"],
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
                     read_rate, write_rate)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    process_id,
                    row["cpu_usage"],
                    row["memory_kb"],
                    row["read_rate"],
                    row["write_rate"]
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
