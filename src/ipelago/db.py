import json
from pathlib import Path
import sqlite3
from result import Ok, Err, Result
from appdirs import AppDirs
from ipelago.model import AppConfig, CurrentList, default_config
from ipelago.stmt import Create_tables, Get_metadata, Insert_metadata, Update_metadata

db_filename = "pypelago.sqlite"
app_config_name = "app-config"
current_list_name = "current-list"

app_dirs = AppDirs("ipelago-cli", "github-ahui2016")
app_config_dir = Path(app_dirs.user_config_dir)
db_path = app_config_dir.joinpath(db_filename)

NoResultError = "database-no-result"


def connect_db() -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def get_cfg(conn: sqlite3.Connection) -> Result[AppConfig, str]:
    row = conn.execute(Get_metadata, (app_config_name,)).fetchone()
    if row is None:
        return Err(NoResultError)
    cfg = json.loads(row[0])
    return Ok(cfg)


def update_cfg(cfg: AppConfig, conn: sqlite3.Connection) -> None:
    conn.execute(Update_metadata, {"value": json.dumps(cfg), "name": app_config_name})


def init_cfg(conn: sqlite3.Connection) -> None:
    cfg = get_cfg(conn)
    if cfg.err():
        default_cfg = default_config()
        conn.execute(
            Insert_metadata, (app_config_name,json.dumps(default_cfg))
        )


def get_current_list(conn: sqlite3.Connection) -> Result[CurrentList, str]:
    row = conn.execute(Get_metadata, (current_list_name,)).fetchone()
    if row is None:
        return Err(NoResultError)
    cl = json.loads(row[0])
    return Ok(cl)


def update_current_list(cl: CurrentList, conn: sqlite3.Connection) -> None:
    conn.execute(Update_metadata, {"value": json.dumps(cl), "name": current_list_name})


def init_current_list(conn: sqlite3.Connection) -> None:
    cl = get_current_list(conn)
    if cl.err():
        conn.execute(
            Insert_metadata, (current_list_name, json.dumps([]))
        )


def init_tables() -> None:
    """Initialize tables and the app-config"""
    app_config_dir.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        with connect_db() as conn:
            conn.execute(Create_tables)
            init_cfg(conn)
            init_current_list(conn)


def get_current_n(n: int, conn: sqlite3.Connection) -> Result[str, str]:
    cl = get_current_list(conn).unwrap()

    i = n - 1
    if i < 0 or i >= len(cl):
        return Err("IndexError: list index out of range")
    return Ok(cl[i])


def get_proxies(cfg: AppConfig) -> dict | None:
    if cfg["use_proxy"] and cfg["http_proxy"]:
        return dict(
            http=cfg["http_proxy"],
            https=cfg["http_proxy"],
        )


def set_pwd(pwd: str) -> None:
    with connect_db() as conn:
        cfg = get_cfg(conn).unwrap()
        cfg["password"] = pwd
        update_cfg(cfg, conn)
