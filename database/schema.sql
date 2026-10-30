CREATE DATABASE IF NOT EXISTS sentinelos;

USE sentinelos;

CREATE TABLE IF NOT EXISTS processes (
    process_id INT AUTO_INCREMENT PRIMARY KEY,
    pid INT NOT NULL,
    ppid INT,
    name VARCHAR(255) NOT NULL,
    state CHAR(1),
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    start_ticks BIGINT NULL,
    os_type VARCHAR(20) NOT NULL DEFAULT 'Linux',
    UNIQUE KEY unique_pid_start_ticks (pid, start_ticks)
);

CREATE TABLE IF NOT EXISTS resource_usage (
    usage_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    process_id INT NOT NULL,
    cpu_usage DECIMAL(6,2),
    memory_usage BIGINT,
    read_rate BIGINT,
    write_rate BIGINT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (process_id)
        REFERENCES processes(process_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS anomalies (
    anomaly_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    process_id INT NOT NULL,
    anomaly_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (process_id)
        REFERENCES processes(process_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    process_id INT NOT NULL,
    predicted_resource VARCHAR(50) NOT NULL,
    predicted_value DECIMAL(10,2),
    risk_score DECIMAL(5,2),
    risk_level VARCHAR(20),
    prediction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (process_id)
        REFERENCES processes(process_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    anomaly_id BIGINT,
    process_id INT NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    FOREIGN KEY (anomaly_id)
        REFERENCES anomalies(anomaly_id)
        ON DELETE SET NULL,
    FOREIGN KEY (process_id)
        REFERENCES processes(process_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS corrective_actions (
    action_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    process_id INT NOT NULL,
    anomaly_id BIGINT,
    action_type VARCHAR(50) NOT NULL,
    reason TEXT,
    status VARCHAR(20) NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP NULL,
    FOREIGN KEY (process_id)
        REFERENCES processes(process_id)
        ON DELETE CASCADE,
    FOREIGN KEY (anomaly_id)
        REFERENCES anomalies(anomaly_id)
        ON DELETE SET NULL
);
