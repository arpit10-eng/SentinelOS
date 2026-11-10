import pandas as pd
import streamlit as st

from backend.db import get_connection


@st.cache_data(ttl=10)
def load_security_data():
    connection = get_connection()

    anomaly_query = """
        SELECT
            a.anomaly_id,
            p.pid,
            p.name AS process_name,
            p.os_type,
            a.anomaly_type,
            a.severity,
            a.description,
            a.detected_at
        FROM anomalies a
        JOIN processes p
            ON a.process_id = p.process_id
        ORDER BY a.detected_at DESC
    """

    alert_query = """
        SELECT
            al.alert_id,
            al.anomaly_id,
            p.pid,
            p.name AS process_name,
            p.os_type,
            al.message,
            al.severity,
            al.status,
            al.created_at,
            al.resolved_at
        FROM alerts al
        JOIN processes p
            ON al.process_id = p.process_id
        ORDER BY al.created_at DESC
    """

    action_query = """
        SELECT
            ca.action_id,
            ca.anomaly_id,
            p.pid,
            p.name AS process_name,
            p.os_type,
            ca.action_type,
            ca.reason,
            ca.status,
            ca.executed_at,
            ca.verified_at
        FROM corrective_actions ca
        JOIN processes p
            ON ca.process_id = p.process_id
        ORDER BY ca.executed_at DESC
    """

    try:
        anomalies = pd.read_sql(anomaly_query, connection)
        alerts = pd.read_sql(alert_query, connection)
        actions = pd.read_sql(action_query, connection)
    finally:
        connection.close()

    return anomalies, alerts, actions


def show_security_panels():
    st.header("Security Operations Center")

    try:
        anomalies, alerts, actions = load_security_data()
    except Exception as error:
        st.error(f"Could not load security data: {error}")
        return

    # Security overview
    total_anomalies = len(anomalies)
    active_alerts = (
        int((alerts["status"] == "ACTIVE").sum())
        if not alerts.empty else 0
    )
    pending_actions = (
        int((actions["status"] == "PENDING_APPROVAL").sum())
        if not actions.empty else 0
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Detected Anomalies", total_anomalies)
    col2.metric("Active Alerts", active_alerts)
    col3.metric("Pending Recommendations", pending_actions)

    # Anomaly monitoring
    st.subheader("Anomaly Monitoring")

    if anomalies.empty:
        st.info("No anomalies detected.")
    else:
        st.dataframe(
            anomalies,
            use_container_width=True,
            hide_index=True,
        )

    # Alert management
    st.subheader("Alert Management")

    if alerts.empty:
        st.info("No alerts generated.")
    else:
        alert_filter = st.selectbox(
            "Filter alerts",
            ["All", "ACTIVE", "RESOLVED"],
            key="alert_status_filter",
        )

        displayed_alerts = alerts

        if alert_filter != "All":
            displayed_alerts = alerts[
                alerts["status"] == alert_filter
            ]

        st.dataframe(
            displayed_alerts,
            use_container_width=True,
            hide_index=True,
        )

    # Corrective action recommendations
    st.subheader("Corrective Action Recommendations")

    st.caption(
        "Recommendations require human review. "
        "SentinelOS does not automatically terminate processes."
    )

    if actions.empty:
        st.info("No corrective-action recommendations available.")
    else:
        action_filter = st.selectbox(
            "Filter recommendations",
            ["All", "PENDING_APPROVAL", "APPROVED", "REJECTED"],
            key="action_status_filter",
        )

        displayed_actions = actions

        if action_filter != "All":
            displayed_actions = actions[
                actions["status"] == action_filter
            ]

        st.dataframe(
            displayed_actions,
            use_container_width=True,
            hide_index=True,
        )
