import json
from pathlib import Path
import sqlite3
from typing import Any, Final, Iterable
import arrow
from result import Ok, Err, Result
from appdirs import AppDirs
from ipelago.model import (
    OK,
    RFC3339,
    AppConfig,
    Bucket,
    FavBucketID,
    Feed,
    FeedEntry,
    PrivateBucketID,
    PublicBucketID,
    default_config,
    new_entry_from,
    new_feed_from,
    next_feed_id,
)
from ipelago.shortid import first_id, parse_id
import ipelago.stmt as stmt

Hour: Final[int] = 60 * 60
Day: Final[int] = 24 * Hour
UpdateRateLimit: Final[int] = 1 * Day

db_filename: Final[str] = "pypelago.db"
app_config_name: Final[str] = "app-config"
current_id_name: Final[str] = "current-id"

app_dirs = AppDirs("pypelago", "github-ahui2016")
app_config_dir = Path(app_dirs.user_config_dir)
db_path = app_config_dir.joinpath(db_filename)

NoResultError = "database-no-result"


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def connExec(
    conn: sqlite3.Connection, query: str, param: Iterable[Any]
) -> Result[int, str]:
    n = conn.execute(query, param).rowcount
    if n <= 0:
        return Err("sqlite row affected = 0")
    return Ok(n)


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


def get_feed_by_id(feed_id: str, conn: sqlite3.Connection) -> Result[Feed, str]:
    row = conn.execute(stmt.Get_feed_by_id, (feed_id,)).fetchone()
    if not row:
        return Err(NoResultError)
    return Ok(new_feed_from(row))


def init_my_feeds(title: str, conn: sqlite3.Connection) -> None:
    if get_feed_by_id(PublicBucketID, conn).err():
        conn.execute(
            stmt.Insert_my_feed, {"id": PublicBucketID, "link": "", "title": title}
        )
    if get_feed_by_id(PrivateBucketID, conn).err():
        conn.execute(
            stmt.Insert_my_feed,
            {
                "id": PrivateBucketID,
                "link": PrivateBucketID,
                "title": "My Private Channel",
            },
        )
    if get_feed_by_id(FavBucketID, conn).err():
        conn.execute(
            stmt.Insert_my_feed,
            {
                "id": FavBucketID,
                "link": FavBucketID,
                "title": "The Favorite Bucket",
            },
        )


def init_app(name: str) -> str:
    """在正式使用前必须先使用该函数进行初始化。"""
    app_config_dir.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        return "不可重复初始化"
    with connect_db() as conn:
        conn.executescript(stmt.Create_tables)
        init_cfg(conn)
        init_current_id(conn)
        init_my_feeds(name, conn)
    return "OK. 初始化成功。"


def get_proxies_cfg(cfg: AppConfig) -> dict | None:
    if cfg["use_proxy"] and cfg["http_proxy"]:
        return dict(
            http=cfg["http_proxy"],
            https=cfg["http_proxy"],
        )


def get_proxies(conn: sqlite3.Connection) -> dict | None:
    cfg = get_cfg(conn).unwrap()
    return get_proxies_cfg(cfg)


def get_my_next(cursor: str, conn: sqlite3.Connection) -> Result[FeedEntry, str]:
    row = conn.execute(stmt.Get_my_next_entry, {"published": cursor}).fetchone()
    if not row:
        row = conn.execute(stmt.Get_my_first_entry).fetchone()
    if not row:
        return Err(NoResultError)
    return Ok(new_entry_from(row))


def get_news_next(cursor: str, conn: sqlite3.Connection) -> Result[FeedEntry, str]:
    row = conn.execute(stmt.Get_news_next_entry, {"published": cursor}).fetchone()
    if not row:
        # 回到最新一条消息
        row = conn.execute(
            stmt.Get_entries_limit, {"bucket": Bucket.News.name, "limit": 1}
        ).fetchone()

    if not row:
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


def get_news_by_feed(
    feed_id: str, limit: int, conn: sqlite3.Connection
) -> list[FeedEntry]:
    result: list[FeedEntry] = []
    for row in conn.execute(
        stmt.Get_news_by_feed, {"feed_id": feed_id, "limit": limit}
    ):
        result.append(new_entry_from(row))
    return result


def get_subs_list(conn: sqlite3.Connection, feed_id: str = "") -> list[Feed]:
    subs_list: list[Feed] = []

    if feed_id in [PublicBucketID, PrivateBucketID, FavBucketID]:
        return []

    if feed_id:
        feed = get_feed_by_id(feed_id, conn).ok()
        if feed:
            subs_list.append(feed)
    else:
        for row in conn.execute(stmt.Get_subs_list):
            subs_list.append(new_feed_from(row))
    return subs_list


def check_before_update(
    feed_id: str, parser: str, force: bool, conn: sqlite3.Connection
) -> Result[Feed, str]:
    if feed_id in [PublicBucketID, PrivateBucketID, FavBucketID]:
        return Err(f"Not Found: {feed_id}")

    match get_feed_by_id(feed_id, conn):
        case Err():
            return Err(f"Not Found: {feed_id}")
        case Ok(feed):

            if parser:
                connExec(
                    conn, stmt.Update_feed_parser, {"parser": parser, "id": feed_id}
                ).unwrap()
                feed.parser = parser
                print(f"The parser is set to '{parser}'")

            updated = arrow.get(feed.updated, RFC3339)
            if (
                force
                or updated.int_timestamp + UpdateRateLimit < arrow.now().int_timestamp
            ):
                return Ok(feed)
            else:
                return Err(
                    "Too Many Requests (默认每天最多拉取一次)\
                    \n可使用 '-force' 参数强制更新。"
                )


def insert_entries(entries: list[FeedEntry], conn: sqlite3.Connection) -> None:
    item_list = [entry.to_dict() for entry in entries]
    conn.executemany(stmt.Insert_entry, item_list)


def delete_entries(feed_id: str, conn: sqlite3.Connection) -> None:
    conn.execute(stmt.Delete_entries, (feed_id,))


def update_entries(
    feed_id: str, entries: list[FeedEntry], conn: sqlite3.Connection
) -> None:
    delete_entries(feed_id, conn)
    insert_entries(entries, conn)
    updated = arrow.now().format(RFC3339)
    connExec(
        conn, stmt.Update_feed_updated, {"updated": updated, "id": feed_id}
    ).unwrap()


def new_feed_id(conn: sqlite3.Connection) -> str:
    timestamp = 0
    while True:
        feed_id, timestamp = next_feed_id(timestamp)
        row = conn.execute(stmt.Get_feed_id, (feed_id,)).fetchone()
        if not row:
            return feed_id


def check_before_subscribe(link: str, conn: sqlite3.Connection) -> Result[str, str]:
    row = conn.execute(stmt.Get_feed_link, (link,)).fetchone()
    if row:
        return Err(f"Exists(不可重复订阅): {link}")
    else:
        return OK


def subscribe_feed(link: str, title: str, parser: str, conn: sqlite3.Connection) -> str:
    """Return the feed_id if nothing wrong."""
    feed_id = new_feed_id(conn)
    conn.execute(
        stmt.Insert_feed,
        dict(
            id=feed_id,
            link=link,
            title=title,
            author_name="",
            updated=arrow.now().format(RFC3339),
            notes="",
            parser=parser,
        ),
    )
    return feed_id


def delete_feed(feed_id: str, conn: sqlite3.Connection) -> str:
    row = conn.execute(stmt.Get_feed_id, (feed_id,)).fetchone()
    if not row:
        return f"Not Found: {feed_id}"

    conn.execute(stmt.Delete_feed, (feed_id,))
    delete_entries(feed_id, conn)
    return "OK. 已删除"


def update_feed_id(
    oldid: str, newid: str, conn: sqlite3.Connection
) -> Result[str, str]:
    if oldid.upper() == newid.upper():
        return OK

    err = connExec(conn, stmt.Update_feed_id, {"oldid": oldid, "newid": newid}).err()
    if err:
        return Err(err)

    connExec(conn, stmt.Update_entry_feed_id, {"oldid": oldid, "newid": newid}).unwrap()
    return OK


def get_entry_by_prefix(prefix: str, conn: sqlite3.Connection) -> list[FeedEntry]:
    rows = conn.execute(stmt.Get_entry_by_id_prefix, (prefix + "%",)).fetchall()
    if not rows:
        return []

    return [new_entry_from(row) for row in rows]


def move_to_fav(entry_id: str, conn: sqlite3.Connection) -> str:
    newid = get_next_id(conn)
    connExec(conn, stmt.Move_entry_to_fav, {"oldid": entry_id, "newid": newid}).unwrap()
    return newid


def get_recent_fav(limit: int, conn: sqlite3.Connection) -> list[FeedEntry]:
    entries = []
    for row in conn.execute(
        stmt.Get_entries_limit, {"bucket": Bucket.Fav.name, "limit": limit}
    ):
        entries.append(new_entry_from(row))
    return entries


def toggle_entry_bucket(
    entry: FeedEntry, conn: sqlite3.Connection
) -> Result[FeedEntry, str]:
    bucket = Bucket[entry.bucket]
    if bucket not in [Bucket.Public, Bucket.Private]:
        return Err("The bucket is not Public or Private.\n只能在 Public 与 Private 之间切换。")

    toggled = Bucket.Public if bucket is Bucket.Private else Bucket.Private
    entry.bucket = toggled.name
    connExec(
        conn, stmt.Update_entry_bucket, {"bucket": entry.bucket, "id": entry.entry_id}
    ).unwrap()
    return Ok(entry)


def update_my_feed_info(
    link: str, title: str, author: str, conn: sqlite3.Connection
) -> Result[int, str]:
    return connExec(
        conn, stmt.Update_my_feed_info, {"link": link, "title": title, "author": author}
    )
