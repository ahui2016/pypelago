import json
from pathlib import Path
import sqlite3
from typing import Final
import arrow
from result import Ok, Err, Result
from appdirs import AppDirs
from ipelago.model import (
    OK,
    RFC3339,
    AppConfig,
    Bucket,
    CurrentList,
    Feed,
    FeedEntry,
    PrivateBucketID,
    PublicBucketID,
    default_config,
    new_entry_from,
    new_feed_from,
    new_my_msg,
    next_feed_id,
)
from ipelago.shortid import first_id, parse_id
import ipelago.stmt as stmt

Hour: Final[int] = 60 * 60
Day: Final[int] = 24 * Hour
UpdateRateLimit: Final[int] = 1 * Day

db_filename: Final[str] = "pypelago.db"
app_config_name: Final[str] = "app-config"
current_list_name: Final[str] = "current-list"
current_id_name: Final[str] = "current-id"

app_dirs = AppDirs("pypelago", "github-ahui2016")
app_config_dir = Path(app_dirs.user_config_dir)
db_path = app_config_dir.joinpath(db_filename)

NoResultError = "database-no-result"


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_cfg(conn: sqlite3.Connection) -> Result[AppConfig, str]:
    row = conn.execute(stmt.Get_metadata, (app_config_name,)).fetchone()
    if row is None:
        return Err(NoResultError)
    cfg = json.loads(row[0])
    return Ok(cfg)


def update_cfg(cfg: AppConfig, conn: sqlite3.Connection) -> None:
    conn.execute(
        stmt.Update_metadata, {"value": json.dumps(cfg), "name": app_config_name}
    )


def init_cfg(conn: sqlite3.Connection) -> None:
    cfg = get_cfg(conn)
    if cfg.err():
        default_cfg = default_config()
        conn.execute(stmt.Insert_metadata, (app_config_name, json.dumps(default_cfg)))


def get_current_id(conn: sqlite3.Connection) -> Result[str, str]:
    row = conn.execute(stmt.Get_metadata, (current_id_name,)).fetchone()
    if row is None:
        return Err(NoResultError)
    return Ok(row[0])


def update_current_id(cid: str, conn: sqlite3.Connection) -> None:
    conn.execute(stmt.Update_metadata, {"value": cid, "name": current_id_name})


def get_next_id(conn: sqlite3.Connection) -> str:
    cid = get_current_id(conn).unwrap()
    nid = parse_id(cid).next_id()
    update_current_id(nid, conn)
    return nid


def init_current_id(conn: sqlite3.Connection) -> None:
    cid = get_current_id(conn)
    if cid.err():
        conn.execute(stmt.Insert_metadata, (current_id_name, first_id()))


def get_current_list(conn: sqlite3.Connection) -> Result[CurrentList, str]:
    row = conn.execute(stmt.Get_metadata, (current_list_name,)).fetchone()
    if row is None:
        return Err(NoResultError)
    cl = json.loads(row[0])
    return Ok(cl)


def update_current_list(cl: CurrentList, conn: sqlite3.Connection) -> None:
    conn.execute(
        stmt.Update_metadata, {"value": json.dumps(cl), "name": current_list_name}
    )


def init_current_list(conn: sqlite3.Connection) -> None:
    cl = get_current_list(conn)
    if cl.err():
        conn.execute(stmt.Insert_metadata, (current_list_name, json.dumps([])))


def get_feed_by_id(feed_id: str, conn: sqlite3.Connection) -> Result[Feed, str]:
    row = conn.execute(stmt.Get_feed_by_id, (feed_id,)).fetchone()
    if row is None:
        return Err(NoResultError)
    return Ok(new_feed_from(row))


def init_my_feeds(title: str, conn: sqlite3.Connection) -> None:
    my_pub = get_feed_by_id(PublicBucketID, conn)
    if my_pub.err():
        conn.execute(
            stmt.Insert_my_feed, {"id": PublicBucketID, "link": "", "title": title}
        )
    my_pri = get_feed_by_id(PrivateBucketID, conn)
    if my_pri.err():
        conn.execute(
            stmt.Insert_my_feed,
            {
                "id": PrivateBucketID,
                "link": "http://exmaple.com",
                "title": "My Private Channel",
            },
        )


def init_app(name: str) -> Result[str, str]:
    """在正式使用前必须先使用该函数进行初始化。"""
    app_config_dir.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        return Err("不可重复初始化")
    with connect_db() as conn:
        conn.executescript(stmt.Create_tables)
        init_cfg(conn)
        init_current_list(conn)
        init_current_id(conn)
        init_my_feeds(name, conn)
    return OK


def get_current_n(n: int, conn: sqlite3.Connection) -> Result[str, str]:
    cl = get_current_list(conn).unwrap()

    i = n - 1
    if i < 0 or i >= len(cl):
        return Err("IndexError: list index out of range")
    return Ok(cl[i])


def get_proxies_cfg(cfg: AppConfig) -> dict | None:
    if cfg["use_proxy"] and cfg["http_proxy"]:
        return dict(
            http=cfg["http_proxy"],
            https=cfg["http_proxy"],
        )


def get_proxies(conn: sqlite3.Connection) -> dict | None:
    cfg = get_cfg(conn).unwrap()
    return get_proxies_cfg(cfg)


def post_msg(msg: str, bucket: Bucket) -> str:
    resp = "OK. 已发送至公开岛。"
    if bucket is Bucket.Private:
        resp = "OK. 已发送至隐藏岛。"

    with connect_db() as conn:
        match new_my_msg(get_next_id(conn), msg, bucket):
            case Err(e):
                resp = e
            case Ok(entry):
                conn.execute(
                    stmt.Insert_my_entry,
                    {
                        "id": entry.entry_id,
                        "content": entry.content,
                        "published": entry.published,
                        "feed_id": entry.feed_id,
                        "bucket": entry.bucket,
                    },
                )
    return resp


def get_my_next(cursor: str, conn: sqlite3.Connection) -> Result[FeedEntry, str]:
    row = conn.execute(stmt.Get_my_next_entry, {"published": cursor}).fetchone()
    if row is None:
        row = conn.execute(stmt.Get_my_first_entry).fetchone()
    if row is None:
        return Err(NoResultError)
    return Ok(new_entry_from(row))


def get_by_date(
    date: str,
    limit: int,
    bucket: str,
    conn: sqlite3.Connection,
) -> list[FeedEntry]:
    result: list[FeedEntry] = []
    for row in conn.execute(
        stmt.Get_by_date, {"bucket": bucket, "published": date + "%", "limit": limit}
    ):
        result.append(new_entry_from(row))
    return result


def get_by_date_buckets(
    date: str,
    limit: int,
    buckets: list[str],
    conn: sqlite3.Connection,
) -> list[FeedEntry]:
    result: list[FeedEntry] = []
    for bucket in buckets:
        entries = get_by_date(date, limit, bucket, conn)
        result += entries
    result.sort(key=lambda x: x.published, reverse=True)
    return result


def get_public_limit(
    cursor: str, limit: int, conn: sqlite3.Connection
) -> list[FeedEntry]:
    result: list[FeedEntry] = []
    for row in conn.execute(
        stmt.Get_public_limit, {"published": cursor, "limit": limit}
    ):
        result.append(new_entry_from(row))
    return result


def get_subs_list(conn: sqlite3.Connection) -> list[Feed]:
    subs_list = []
    for row in conn.execute(stmt.Get_subs_list):
        subs_list.append(new_feed_from(row))
    return subs_list


def check_before_update(
    feed_id: str, force: bool, conn: sqlite3.Connection
) -> Result[str, str]:
    if feed_id in [PublicBucketID, PrivateBucketID]:
        return Err(f"Not Found: {feed_id}")

    match get_feed_by_id(feed_id, conn):
        case Err():
            return Err(f"Not Found: {feed_id}")
        case Ok(feed):
            updated = arrow.get(feed.updated, RFC3339)
            if force or updated + UpdateRateLimit < arrow.now().int_timestamp:
                return OK
            else:
                return Err("Too Many Requests (默认每天最多拉取一次)")


def insert_entries(entries:list[FeedEntry],conn: sqlite3.Connection) -> None:
    item_list = [entry.to_dict() for entry in entries]
    conn.executemany(stmt.Insert_entry, item_list)

def delete_entries(feed_id:str, conn:sqlite3.Connection) -> None:
    conn.execute(stmt.Delete_entries, (feed_id,))


def update_entries(feed_id:str, entries:list[FeedEntry],conn: sqlite3.Connection) -> None:
    delete_entries(feed_id, conn)
    insert_entries(entries, conn)


def new_feed_id(conn: sqlite3.Connection) -> str:
    timestamp = 0
    while True:
        feed_id, timestamp = next_feed_id(timestamp)
        row = conn.execute(stmt.Get_feed_id, (feed_id)).fetchone()
        if not row:
            return feed_id
    
def check_before_subscribe(link:str, conn: sqlite3.Connection) -> Result[str, str]:
    row = conn.execute(stmt.Get_feed_link, (link,)).fetchone()
    if row:
        return Err(f"Exists(不可重复订阅): {link}")
    else:
        return OK


def subscribe_feed(link:str, title:str,conn: sqlite3.Connection) -> str:
    """Return the feed_id if nothing wrong."""
    feed_id = new_feed_id(conn)
    conn.execute(stmt.Insert_feed, dict(
        id=feed_id,
        link=link,
        title=title,
        author_name='',
        updated=arrow.now().format(RFC3339),
        notes='',
    ))
    return feed_id
