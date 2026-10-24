"""Where the plugin keeps its data.

Inside Hermes this is the per-plugin data dir (<hermes home>/plugin-data/apply/),
which survives plugin updates and follows the active profile. Outside Hermes
(local scripts, tests) it falls back to $APPLY_DATA_DIR or ./data.
"""

import os
import sqlite3
from pathlib import Path

PLUGIN_NAME = "apply"


def data_dir() -> Path:
    override = os.environ.get("APPLY_DATA_DIR")
    if override:
        path = Path(override)
    else:
        try:
            from plugins.plugin_storage import plugin_data_dir

            path = plugin_data_dir(PLUGIN_NAME)
        except ImportError:
            path = Path.cwd() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(data_dir() / "apply.db")
    conn.row_factory = sqlite3.Row
    return conn
