"""Run a read-only SQL query against the pre-loaded SQLite connection."""
from __future__ import annotations

from smolagents import tool


@tool
def query_db(conn: object, sql: str, limit: int = 50) -> str:
    """Execute a SQL query against the pre-loaded DB connection.

    Args:
        conn: The `sqlite3.Connection` from scope.
        sql: A SELECT statement. Other statements are rejected.
        limit: Row cap on the returned result.

    Returns:
        A CSV-formatted string (header row + up to `limit` data rows), or an
        error message if the query is rejected or fails.
    """
    stripped = sql.strip().rstrip(";").lstrip()
    if not stripped.lower().startswith("select") and not stripped.lower().startswith("with"):
        return "[query_db only accepts SELECT/WITH statements]"

    try:
        cur = conn.execute(stripped)  # type: ignore[attr-defined]
    except Exception as e:
        return f"[SQL error: {e}]"

    cols = [d[0] for d in (cur.description or [])]
    rows = cur.fetchmany(limit)
    out_lines = [",".join(cols)]
    for row in rows:
        out_lines.append(",".join("" if v is None else str(v) for v in row))
    return "\n".join(out_lines)
