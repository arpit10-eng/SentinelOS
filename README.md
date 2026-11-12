# SentinelOS

## Intelligent OS Resource Guardian

SentinelOS is an operating-system resource monitoring and anomaly detection system designed to monitor processes, collect system resource information, store historical data, identify unusual system behavior, and generate corrective-action recommendations.

## Project Workflow

Process Monitoring → Data Collection → Database Storage → Resource Analysis → Anomaly Detection → Alert Generation → Corrective Action Recommendation → Dashboard Visualization

## Technology Stack

- C — Process monitoring and OS-level information collection
- Python — Data collection, processing, machine learning, and backend logic
- MySQL — Historical process and resource-usage storage
- Streamlit — Interactive monitoring dashboard
- Plotly — Data visualization and charts
- Pandas — Data processing
- Scikit-learn — Machine learning and anomaly detection
- Pytest — Automated testing
- Ubuntu Linux through WSL2 — Development environment
- Git and GitHub — Version control

## Project Structure

SentinelOS/
- backend/ — Data collection, database connectivity, and corrective-action logic
- dashboard/ — Streamlit monitoring dashboard
- database/ — Database-related files and backups
- docs/ — Project documentation
- ml/ — Machine learning and anomaly detection
- os_monitor/ — C-based process monitoring
- tests/ — Automated tests
- requirements.txt

## Current Features

- Process monitoring using C and Linux process information.
- CPU, memory, and I/O resource data collection.
- MySQL storage of process and resource-usage information.
- Historical resource-usage visualization.
- Machine-learning-based anomaly detection using Isolation Forest.
- Security alerts for detected anomalies.
- Corrective-action recommendations requiring manual approval.
- Automated tests for important project components.

## Running SentinelOS

Activate the virtual environment:

    source .venv/bin/activate

Run the data collector:

    python -m backend.collector

Start the dashboard in another terminal:

    cd ~/SentinelOS
    source .venv/bin/activate
    PYTHONPATH="$PWD" streamlit run dashboard/app.py

## Running Tests

    python -m pytest -v

## Safety Note

SentinelOS currently generates corrective-action recommendations for manual review. It does not automatically terminate processes or perform unapproved corrective actions.

Anomaly detection identifies statistically unusual behavior; an anomaly is not, by itself, proof of malware or malicious activity.

## Development Environment

This project is developed using Ubuntu Linux on WSL2.
