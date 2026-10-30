import csv
import os
from datetime import datetime

import psutil


OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "windows_processes.csv")


def collect_processes():
    collected_at = datetime.now().astimezone().isoformat(timespec="seconds")
    processes = []

    for process in psutil.process_iter(
        ["pid", "ppid", "name", "status", "memory_info"]
    ):
        try:
            info = process.info
            memory_info = info["memory_info"]

            processes.append({
                "collected_at": collected_at,
                "pid": info["pid"],
                "ppid": info["ppid"],
                "name": info["name"] or "Unknown",
                "status": info["status"] or "Unknown",
                "memory_mb": round(memory_info.rss / (1024 * 1024), 2)
                if memory_info else 0,
            })

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
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
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processes)


def main():
    processes = collect_processes()
    save_to_csv(processes)

    print("SentinelOS Windows Process Collector")
    print(f"Processes collected: {len(processes)}")
    print(f"CSV saved to: {OUTPUT_FILE}")
    print("\nSample processes:")

    for process in processes[:10]:
        print(
            f"PID: {process['pid']:<7} "
            f"Name: {process['name']:<25} "
            f"Memory: {process['memory_mb']:>8.2f} MB"
        )


if __name__ == "__main__":
    main()
