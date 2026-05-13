"""Shared SQLAlchemy MySQL URL for this project.

Set ``MYSQL_URL`` or ``DATABASE_URL`` to override (recommended for production).
Password characters such as ``@`` must be URL-encoded in the connection string
(e.g. ``@`` → ``%40``).
"""

from __future__ import annotations

import os

# Local default matches a typical dev setup; override with MYSQL_URL.
_DEFAULT = "mysql+pymysql://root:%40Yorkie18@localhost/nfl_analytics"


def get_database_url() -> str:
    url = (os.environ.get("MYSQL_URL") or os.environ.get("DATABASE_URL") or "").strip()
    if url:
        return url
    return _DEFAULT
