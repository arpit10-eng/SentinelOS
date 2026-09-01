# SentinelOS

## Intelligent OS Resource Guardian

SentinelOS is an intelligent operating-system resource monitoring and prevention system.

The system continuously monitors processes and system resources, stores historical resource-usage data, detects abnormal behavior, predicts potential resource problems, and recommends or performs safe corrective actions.

## Project Workflow

Monitor → Collect Data → Store in Database → Analyze Behavior → Detect Anomaly → Predict Risk → Decide Action → Perform OS-Level Action → Verify Result → Display on Dashboard

## Technology Stack

- C — OS-level and process-related operations
- Python — monitoring, data processing, machine learning, and backend services
- MySQL — historical system data storage
- FastAPI — backend/API layer
- HTML, CSS, JavaScript — dashboard
- Ubuntu Linux through WSL2 — development environment
- Git and GitHub — version control

## Project Structure

```text
SentinelOS/
├── os_monitor/
├── database/
├── ml/
├── backend/
├── dashboard/
├── tests/
├── docs/
└── README.md

The project description and technology choices above are based on your supplied synopsis.
