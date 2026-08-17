import os
import json
import sys
from datetime import datetime

import psycopg2


CONFIG_FILE = "config.json"
REPORT_DIR = "reports"


def load_config():
    """Load configuration from config.json."""

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except FileNotFoundError:
        print("ERROR: config.json not found.")
        sys.exit(1)

    except json.JSONDecodeError:
        print("ERROR: Invalid JSON configuration.")
        sys.exit(1)


def connect_database(config):
    """Connect to PostgreSQL database."""

    db_config = config["database"]

    password = os.getenv("DB_PASSWORD")

    if not password:
        print("ERROR: DB_PASSWORD environment variable is not set.")
        sys.exit(1)

    try:
        connection = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=password,
            connect_timeout=10
        )

        return connection

    except psycopg2.Error as error:
        print(f"ERROR: Database connection failed: {error}")
        return None


def check_database_version(cursor):
    cursor.execute("SELECT version();")
    return cursor.fetchone()[0]


def check_database_size(cursor, database_name):
    cursor.execute(
        "SELECT pg_size_pretty(pg_database_size(%s));",
        (database_name,)
    )

    return cursor.fetchone()[0]


def check_active_connections(cursor):
    cursor.execute(
        """
        SELECT count(*)
        FROM pg_stat_activity
        WHERE state = 'active';
        """
    )

    return cursor.fetchone()[0]


def check_long_running_queries(cursor, threshold):
    cursor.execute(
        """
        SELECT
            pid,
            usename,
            state,
            EXTRACT(
                EPOCH FROM (clock_timestamp() - query_start)
            ) AS duration_seconds,
            LEFT(query, 100) AS query
        FROM pg_stat_activity
        WHERE query_start IS NOT NULL
          AND state <> 'idle'
          AND clock_timestamp() - query_start >
              (%s * INTERVAL '1 second')
        ORDER BY duration_seconds DESC;
        """,
        (threshold,)
    )

    queries = []

    for row in cursor.fetchall():
        queries.append(
            {
                "pid": row[0],
                "user": row[1],
                "state": row[2],
                "duration_seconds": round(float(row[3]), 2),
                "query": row[4]
            }
        )

    return queries


def generate_report(connection, config):

    cursor = connection.cursor()

    database_name = config["database"]["database"]

    threshold = config["thresholds"]["long_query_seconds"]

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "database": database_name,
        "status": "HEALTHY",
        "checks": {}
    }

    try:

        report["checks"]["database_version"] = \
            check_database_version(cursor)

        report["checks"]["database_size"] = \
            check_database_size(cursor, database_name)

        active_connections = \
            check_active_connections(cursor)

        report["checks"]["active_connections"] = \
            active_connections

        long_queries = \
            check_long_running_queries(cursor, threshold)

        report["checks"]["long_running_queries"] = \
            long_queries

        max_connections = \
            config["thresholds"]["max_connections"]

        if active_connections >= max_connections:
            report["status"] = "WARNING"

        if long_queries:
            report["status"] = "WARNING"

        return report

    finally:
        cursor.close()


def save_report(report):

    os.makedirs(REPORT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"db_health_{timestamp}.json"

    filepath = os.path.join(REPORT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    return filepath


def main():

    print("=" * 60)
    print("DATABASE HEALTH CHECK")
    print("=" * 60)

    config = load_config()

    connection = connect_database(config)

    if connection is None:
        sys.exit(1)

    try:

        report = generate_report(connection, config)

        report_file = save_report(report)

        print(f"Database: {report['database']}")
        print(f"Status: {report['status']}")

        print(
            f"Active connections: "
            f"{report['checks']['active_connections']}"
        )

        print(
            f"Long-running queries: "
            f"{len(report['checks']['long_running_queries'])}"
        )

        print(f"Report: {report_file}")

        if report["status"] == "WARNING":
            sys.exit(2)

        sys.exit(0)

    finally:
        connection.close()


if __name__ == "__main__":
    main()
