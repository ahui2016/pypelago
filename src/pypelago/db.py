import json
from pathlib import Path
import sqlite3
from appdirs import AppDirs
from pypelago.model import AppConfig, default_config
from pypelago.stmt import Create_tables, Get_metadata, Insert_metadata

db_filename = "pypelago.sqlite"
app_config_name = "app-config"

app_dirs = AppDirs("ipelago-cli", "github-ahui2016")
app_config_dir = Path(app_dirs.user_config_dir)
db_path = app_config_dir.joinpath(db_filename)


def get_cfg(cur: sqlite3.Cursor) -> AppConfig|None:
    row = cur.execute(Get_metadata, (app_config_name,)).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def init_tables_cfg() -> None:
    """Initialize tables and the app-config"""
    app_config_dir.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute(Create_tables)
            cur.execute(Insert_metadata)
            cfg = default_config()

