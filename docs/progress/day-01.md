# Day 1 — SentinelOS Pipeline Verification

## Completed
- Compiled and ran the C process monitor.
- Verified CSV output from the process monitor.
- Ran the Python collector using the project virtual environment.
- Confirmed that the collector connects to MySQL.
- Verified process records in the `processes` table.
- Verified CPU, memory, and I/O measurement fields in `resource_usage`.
- Confirmed that process records join correctly to resource-usage records.

## Verification snapshot
- Process records: 309
- Resource-usage records: 430
- Python dependencies: `mysql-connector-python`, `python-dotenv`

## Follow-up work
- Test repeated collection and process deduplication.
- Validate disk read/write measurements.
- Investigate process-name truncation.
- Add Windows process monitoring.
