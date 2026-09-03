import mysql.connector


def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="sentinel_user",
        password="SentinelOS@2026",
        database="sentinelos"
    )

    return connection
