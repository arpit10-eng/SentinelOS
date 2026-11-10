import pandas as pd
import plotly.express as px
import streamlit as st

from backend.db import get_connection


st.set_page_config(
    page_title="SentinelOS Dashboard",
    page_icon="🛡️",
    layout="wide",
)


@st.cache_data(ttl=10)
def load_dashboard_data():
    connection = get_connection()

    process_query = """
        WITH latest_per_os AS (
            SELECT
                p.os_type,
                MAX(ru.recorded_at) AS latest_time
            FROM processes p
            JOIN resource_usage ru
                ON p.process_id = ru.process_id
            GROUP BY p.os_type
        )
        SELECT
            p.process_id,
            p.pid,
            p.ppid,
            p.name,
            p.state,
            p.os_type,
            ru.cpu_usage,
            ru.memory_usage,
            ru.read_rate,
            ru.write_rate,
            ru.recorded_at
        FROM processes p
        JOIN resource_usage ru
            ON p.process_id = ru.process_id
        JOIN latest_per_os latest
            ON p.os_type = latest.os_type
        WHERE ru.recorded_at >= latest.latest_time - INTERVAL 2 MINUTE
        ORDER BY ru.cpu_usage DESC
    """

    history_query = """
        SELECT
            DATE_FORMAT(ru.recorded_at, '%Y-%m-%d %H:%i') AS time_bucket,
            p.os_type,
            AVG(ru.cpu_usage) AS average_cpu,
            SUM(ru.memory_usage) / 1024 AS memory_mb,
            SUM(ru.read_rate) AS read_rate,
            SUM(ru.write_rate) AS write_rate
        FROM processes p
        JOIN resource_usage ru
            ON p.process_id = ru.process_id
        WHERE ru.recorded_at >= NOW() - INTERVAL 60 MINUTE
        GROUP BY time_bucket, p.os_type
        ORDER BY time_bucket
    """

    try:
        process_data = pd.read_sql(process_query, connection)
        history_data = pd.read_sql(history_query, connection)
    finally:
        connection.close()

    return process_data, history_data


@st.fragment(run_every="10s")
def show_dashboard():
    st.title("🛡️ SentinelOS")
    st.subheader("Cross-Platform System Monitoring Dashboard")

    st.caption(
        "Monitor Linux and Windows processes, CPU usage, memory, and disk activity."
    )

    try:
        data, history = load_dashboard_data()

    except Exception as error:
        st.error(f"Could not load monitoring data: {error}")
        return

    if data.empty:
        st.warning("No monitoring data found. Run the process collectors first.")
        return

    # Sidebar filters
    st.sidebar.header("Dashboard Filters")

    available_os = ["All"] + sorted(
        data["os_type"].dropna().unique().tolist()
    )

    selected_os = st.sidebar.selectbox(
        "Operating System",
        available_os,
    )

    if selected_os != "All":
        data = data[data["os_type"] == selected_os]

        if not history.empty:
            history = history[history["os_type"] == selected_os]

    # Overview metrics
    total_processes = len(data)
    average_cpu = data["cpu_usage"].mean()
    total_memory = data["memory_usage"].sum() / 1024
    total_read = data["read_rate"].fillna(0).sum()
    total_write = data["write_rate"].fillna(0).sum()

    st.header("System Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Processes", f"{total_processes:,}")
    col2.metric(
        "Average CPU",
        f"{average_cpu:.2f}%" if pd.notna(average_cpu) else "N/A",
    )
    col3.metric("Total Memory", f"{total_memory:,.2f} MB")
    col4.metric("Disk Read", f"{total_read:,.0f} B/s")
    col5.metric("Disk Write", f"{total_write:,.0f} B/s")

    # Operating system comparison
    st.header("Operating System Summary")

    summary = (
        data.groupby("os_type")
        .agg(
            processes=("process_id", "count"),
            average_cpu=("cpu_usage", "mean"),
            memory_kb=("memory_usage", "sum"),
        )
        .reset_index()
    )

    summary["average_cpu"] = summary["average_cpu"].round(2)
    summary["memory_mb"] = (summary["memory_kb"] / 1024).round(2)

    st.dataframe(
        summary[["os_type", "processes", "average_cpu", "memory_mb"]],
        use_container_width=True,
        hide_index=True,
    )

    # Historical charts
    st.header("Historical System Performance")
    st.caption("Showing monitoring history from the last 60 minutes.")

    if history.empty:
        st.info("Historical data will appear after more monitoring samples are collected.")
    else:
        history["time_bucket"] = pd.to_datetime(history["time_bucket"])

        st.subheader("CPU Usage Over Time")

        cpu_history = history.dropna(subset=["average_cpu"])

        if not cpu_history.empty:
            cpu_chart = px.line(
                cpu_history,
                x="time_bucket",
                y="average_cpu",
                color="os_type",
                markers=True,
                labels={
                    "time_bucket": "Time",
                    "average_cpu": "Average CPU (%)",
                    "os_type": "Operating System",
                },
            )
            st.plotly_chart(cpu_chart, use_container_width=True)
        else:
            st.info("No CPU history is available yet.")

        st.subheader("Memory Usage Over Time")

        memory_chart = px.line(
            history,
            x="time_bucket",
            y="memory_mb",
            color="os_type",
            markers=True,
            labels={
                "time_bucket": "Time",
                "memory_mb": "Memory (MB)",
                "os_type": "Operating System",
            },
        )
        st.plotly_chart(memory_chart, use_container_width=True)

        st.subheader("Disk Read Activity")

        read_chart = px.line(
            history,
            x="time_bucket",
            y="read_rate",
            color="os_type",
            markers=True,
            labels={
                "time_bucket": "Time",
                "read_rate": "Read Rate (B/s)",
                "os_type": "Operating System",
            },
        )
        st.plotly_chart(read_chart, use_container_width=True)

        st.subheader("Disk Write Activity")

        write_chart = px.line(
            history,
            x="time_bucket",
            y="write_rate",
            color="os_type",
            markers=True,
            labels={
                "time_bucket": "Time",
                "write_rate": "Write Rate (B/s)",
                "os_type": "Operating System",
            },
        )
        st.plotly_chart(write_chart, use_container_width=True)

    # Process table
    st.header("Process Monitor")

    search = st.text_input("Search process by name")

    if search:
        data = data[
            data["name"].str.contains(search, case=False, na=False)
        ]

    display_data = data[
        [
            "pid",
            "ppid",
            "name",
            "os_type",
            "state",
            "cpu_usage",
            "memory_usage",
            "read_rate",
            "write_rate",
            "recorded_at",
        ]
    ].copy()

    display_data = display_data.rename(
        columns={
            "pid": "PID",
            "ppid": "Parent PID",
            "name": "Process",
            "os_type": "Operating System",
            "state": "State",
            "cpu_usage": "CPU (%)",
            "memory_usage": "Memory (KB)",
            "read_rate": "Read (B/s)",
            "write_rate": "Write (B/s)",
            "recorded_at": "Last Recorded",
        }
    )

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
    )

    st.caption("Dashboard refresh interval: 10 seconds.")
    st.caption("Data source: SentinelOS MySQL database.")


show_dashboard()
