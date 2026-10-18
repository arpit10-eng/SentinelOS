CREATE DATABASE IF NOT EXISTS sentinelos;

USE sentinelos;

CREATE TABLE processes (
    process_id INT AUTO_INCREMENT PRIMARY KEY,
    pid INT NOT NULL,
    ppid INT,
    name VARCHAR(255) NOT NULL,
    state CHAR(1),
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (pid)
);

CREATE TABLE resource_usage (
    usage_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    process_id INT NOT NULL,
    cpu_usage DECIMAL(6,2),
    memory_usage BIGINT,
    read_bytes BIGINT,
    write_bytes BIGINT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (process_id)
        REFERENCES processes(process_id)
        ON DELETE CASCADE
);

CREATE TABLE anomalies (
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

CREATE TABLE predictions (
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

CREATE TABLE alerts (
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

CREATE TABLE corrective_actions (
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