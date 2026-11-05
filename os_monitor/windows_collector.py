import csv
import os
import time
from datetime import datetime

import psutil


OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "windows_processes.csv")
SAMPLE_INTERVAL = 1.0


def collect_processes():
    processes = []
    initial_snapshots = {}

    # First snapshot: establish CPU and disk I/O baselines.
    for process in psutil.process_iter(
        ["pid", "ppid", "name", "status", "memory_info", "create_time"]
    ):
        try:
            info = process.info

            # Exclude the special System Idle Process.
            if info["pid"] == 0:
                continue

            create_time = info["create_time"]

            # Establish CPU measurement baseline.
            process.cpu_percent(interval=None)

            # Establish disk I/O baseline.
            io_info = process.io_counters()

            initial_snapshots[info["pid"]] = {
                "process": process,
                "create_time": create_time,
                "io_read": io_info.read_bytes if io_info else None,
                "io_write": io_info.write_bytes if io_info else None,
            }

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    # Wait once for all processes instead of waiting individually.
    time.sleep(SAMPLE_INTERVAL)

    collected_at = datetime.now().astimezone().isoformat(timespec="seconds")

    # Second snapshot: calculate CPU and disk I/O rates.
    for pid, snapshot in initial_snapshots.items():
        process = snapshot["process"]

        try:
            if not process.is_running():
                continue

            current_create_time = process.create_time()

            # Avoid mixing measurements if a PID has been reused.
            if current_create_time != snapshot["create_time"]:
                continue

            info = process.as_dict(
                attrs=["pid", "ppid", "name", "status", "memory_info"]
            )

            memory_info = info["memory_info"]

            # CPU percentage across the entire logical CPU capacity.
            cpu_usage = process.cpu_percent(interval=None)
            cpu_usage = cpu_usage / psutil.cpu_count()

            # Current cumulative disk I/O counters.
            io_info = process.io_counters()

            if io_info and snapshot["io_read"] is not None:
                read_rate = max(
                    0,
                    round(
                        (io_info.read_bytes - snapshot["io_read"])
                        / SAMPLE_INTERVAL
                    ),
                )
                write_rate = max(
                    0,
                    round(
                        (io_info.write_bytes - snapshot["io_write"])
                        / SAMPLE_INTERVAL
                    ),
                )
            else:
                read_rate = 0
                write_rate = 0

            processes.append({
                "collected_at": collected_at,
                "pid": info["pid"],
                "ppid": info["ppid"],
                "name": info["name"] or "Unknown",
                "status": info["status"] or "Unknown",
                "memory_mb": round(memory_info.rss / (1024 * 1024), 2)
                if memory_info else 0,
                "create_time": current_create_time,
                "cpu_usage": round(cpu_usage, 2),
                "read_rate": read_rate,
                "write_rate": write_rate,
            })

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    return processes


def save_to_csv(processes):
    fieldnames = [
        "collected_at",
        "pid",
        "ppid",
        "name",
        "status",
        "memory_mb",
        "create_time",
        "cpu_usage",
        "read_rate",
        "write_rate",
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processes)


def main():
    processes = collect_processes()
    save_to_csv(processes)

    print("SentinelOS Windows Process Collector")
    print("-" * 75)
    print(f"Processes collected: {len(processes)}")
    print(f"CSV saved to: {OUTPUT_FILE}")

    print("\nSample processes:")

    for process in processes[:10]:
        print(
            f"PID: {process['pid']:<7} "
            f"Name: {process['name']:<22} "
            f"CPU: {process['cpu_usage']:>7.2f}% "
            f"Memory: {process['memory_mb']:>8.2f} MB "
            f"Read: {process['read_rate']:>9} B/s "
            f"Write: {process['write_rate']:>9} B/s"
        )


if __name__ == "__main__":
    main()
