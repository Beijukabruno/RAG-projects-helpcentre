"""Inspect the current database shape.

Prints tables with row counts, per-table columns, foreign-key relationships,
and a few content summaries (projects, audiences, chunk counts). Useful for
quickly understanding "what the database looks like right now".

Usage:
    python scripts/inspect_db.py            # full report
    python scripts/inspect_db.py --tables   # tables + row counts only
    python scripts/inspect_db.py --table chat_message   # one table's columns

Reads DATABASE_URL from the environment / .env (same as the app).
"""

import argparse
import sys

from sqlalchemy import create_engine, text

# Allow running as `python scripts/inspect_db.py` from the repo root.
sys.path.insert(0, ".")
from app.core.config import DATABASE_URL  # noqa: E402


def _engine():
    return create_engine(DATABASE_URL, connect_args={"connect_timeout": 5})


def print_tables(conn):
    print("\n=== TABLES + ROW COUNTS ===")
    rows = conn.execute(
        text(
            """
            SELECT relname AS table_name, n_live_tup AS approx_rows
            FROM pg_stat_user_tables
            ORDER BY relname
            """
        )
    ).all()
    for name, count in rows:
        print(f"  {name:<28} {count:>10}")


def print_columns(conn, only_table=None):
    print("\n=== COLUMNS ===")
    params = {}
    filter_sql = ""
    if only_table:
        filter_sql = "AND table_name = :t"
        params["t"] = only_table
    rows = conn.execute(
        text(
            f"""
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' {filter_sql}
            ORDER BY table_name, ordinal_position
            """
        ),
        params,
    ).all()
    current = None
    for table, col, dtype, nullable in rows:
        if table != current:
            print(f"\n  [{table}]")
            current = table
        null = "" if nullable == "NO" else "  (nullable)"
        print(f"    - {col:<22} {dtype}{null}")


def print_foreign_keys(conn):
    print("\n=== FOREIGN KEYS ===")
    rows = conn.execute(
        text(
            """
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name  AS ref_table,
                ccu.column_name AS ref_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.table_name
            """
        )
    ).all()
    for table, col, ref_table, ref_col in rows:
        print(f"  {table}.{col} -> {ref_table}.{ref_col}")


def print_content_summary(conn):
    print("\n=== CONTENT SUMMARY ===")
    try:
        projects = conn.execute(text("SELECT id, name, enabled, status FROM projects ORDER BY id")).all()
        print("  projects:")
        for pid, name, enabled, status in projects:
            print(f"    - {pid:<18} {name:<18} enabled={enabled} status={status}")
    except Exception as exc:  # noqa: BLE001
        print(f"  (projects unavailable: {exc})")

    try:
        chunks = conn.execute(
            text(
                """
                SELECT project_id, audience, count(*)
                FROM knowledge_chunk_embedding
                GROUP BY 1, 2 ORDER BY 1, 2
                """
            )
        ).all()
        print("  knowledge chunks (project / audience / count):")
        for pid, aud, count in chunks:
            print(f"    - {pid:<18} {aud:<12} {count}")
    except Exception as exc:  # noqa: BLE001
        print(f"  (chunk counts unavailable: {exc})")


def main():
    parser = argparse.ArgumentParser(description="Inspect the database shape.")
    parser.add_argument("--tables", action="store_true", help="Only show tables + row counts.")
    parser.add_argument("--table", help="Show columns for a single table.")
    args = parser.parse_args()

    print(f"Connecting to: {DATABASE_URL.rsplit('@', 1)[-1]}")
    with _engine().connect() as conn:
        if args.table:
            print_columns(conn, only_table=args.table)
            return
        print_tables(conn)
        if args.tables:
            return
        print_columns(conn)
        print_foreign_keys(conn)
        print_content_summary(conn)


if __name__ == "__main__":
    main()
