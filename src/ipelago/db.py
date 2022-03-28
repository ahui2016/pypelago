import json
from pathlib import Path
import sqlite3
from typing import Any, Final, Iterable
import arrow
from result import Ok, Err, Result
from appdirs import AppDirs
from ipelago import model
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

Conn = sqlite3.Connection


def connect_db() -> Conn:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def connExec(
    conn: Conn, query: str, param: Iterable[Any], many: bool = False
) -> Result[int, str]:
    if many:
        n = conn.executemany(query, param).rowcount
    else:
        n = conn.execute(query, param).rowcount
    if n <= 0:
        return Err("sqlite row affected = 0")
    return Ok(n)


def get_cfg(conn: Conn) -> Result[AppConfig, str]:
    row = conn.execute(stmt.Get_metadata, (app_config_name,)).fetchone()
    if row is None:
        return Err(NoResultError)
    cfg = json.loads(row[0])
    return Ok(cfg)


def update_cfg(cfg: AppConfig, conn: Conn) -> None:
    conn.execute(
        stmt.Update_metadata, {"value": json.dumps(cfg), "name": app_config_name}
    )


def init_cfg(conn: Conn) -> None:
    cfg = get_cfg(conn)
    if cfg.err():
        default_cfg = model.default_config()
        conn.execute(stmt.Insert_metadata, (app_config_name, json.dumps(default_cfg)))


def get_current_id(conn: Conn) -> Result[str, str]:
    row = conn.execute(stmt.Get_metadata, (current_id_name,)).fetchone()
    if row is None:
        return Err(NoResultError)
    return Ok(row[0])


def update_current_id(cid: str, conn: Conn) -> None:
    conn.execute(stmt.Update_metadata, {"value": cid, "name": current_id_name})


def get_next_id(conn: Conn) -> str:
    cid = get_current_id(conn).unwrap()
    nid = parse_id(cid).next_id()
    update_current_id(nid, conn)
    return nid


def init_current_id(conn: Conn) -> None:
    cid = get_current_id(conn)
    if cid.err():
        conn.execute(stmt.Insert_metadata, (current_id_name, first_id()))


def get_feed_by_id(feed_id: str, conn: Conn) -> Result[Feed, str]:
    row = conn.execute(stmt.Get_feed_by_id, (feed_id,)).fetchone()
    if not row:
        return Err(NoResultError)
    return Ok(model.new_feed_from(row))


def init_my_feeds(title: str, conn: Conn) -> None:
    if get_feed_by_id(PublicBucketID, conn).err():
        conn.execute(
            stmt.Insert_my_feed,
            {"id": PublicBucketID, "feed_link": "", "title": title},
        )
    if get_feed_by_id(PrivateBucketID, conn).err():
        conn.execute(
            stmt.Insert_my_feed,
            {"id": PrivateBucketID, "feed_link": "1", "title": "My Private Channel"},
        )
    if get_feed_by_id(FavBucketID, conn).err():
        conn.execute(
            stmt.Insert_my_feed,
            {"id": FavBucketID, "feed_link": "2", "title": "The Favorite Bucket"},
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


def get_proxies(conn: Conn) -> dict | None:
    cfg = get_cfg(conn).unwrap()
    return get_proxies_cfg(cfg)


def get_my_next(cursor: str, conn: Conn) -> Result[FeedEntry, str]:
    row = conn.execute(stmt.Get_my_next_entry, {"published": cursor}).fetchone()
    if not row:
        row = conn.execute(stmt.Get_my_first_entry).fetchone()
    if not row:
        return Err(NoResultError)
    return Ok(model.new_entry_from(row))


def my_cursor_goto(date_prefix: str, conn: Conn) -> Result[FeedEntry, str]:
    row = conn.execute(stmt.My_cursor_goto, {"published": date_prefix}).fetchone()
    if not row:
        return Err("Not Found. (找不到该命令指定的消息)")

    return Ok(model.new_entry_from(row))


def news_cursor_goto(date_prefix: str, conn: Conn) -> Result[FeedEntry, str]:
    row = conn.execute(stmt.News_cursor_goto, {"published": date_prefix}).fetchone()
    if not row:
        return Err("Not Found. (找不到该命令指定的消息)")

    return Ok(model.new_entry_from(row))


def get_news_next(cursor: str, conn: Conn) -> Result[FeedEntry, str]:
    row = conn.execute(stmt.Get_news_next_entry, {"published": cursor}).fetchone()
    if not row:
        # 回到最新一条消息
        row = conn.execute(
            stmt.Get_entries_limit, {"bucket": Bucket.News.name, "limit": 1}
        ).fetchone()

    if not row:
        return Err(NoResultError)

    return Ok(model.new_entry_from(row))


def get_by_date(date: str, limit: int, bucket: str, conn: Conn) -> list[FeedEntry]:
    result: list[FeedEntry] = []
    for row in conn.execute(
        stmt.Get_by_date, {"bucket": bucket, "published": date + "%", "limit": limit}
    ):
        result.append(model.new_entry_from(row))
    return result


def get_by_date_my_buckets(date: str, limit: int, conn: Conn) -> list[FeedEntry]:
    result: list[FeedEntry] = []
    for row in conn.execute(
        stmt.Get_by_date_my_buckets, {"published": date + "%", "limit": limit}
    ):
        result.append(model.new_entry_from(row))
    return result


def conut_by_date_buckets(date: str, buckets: list[str], conn: Conn) -> int:
    total = 0
    for bucket in buckets:
        row = conn.execute(
            stmt.Count_by_date,
            {"bucket": bucket, "published": date + "%"},
        ).fetchone()
        if row:
            total += row[0]

    return total


def get_public_limit(cursor: str, limit: int, conn: Conn) -> list[FeedEntry]:
    result: list[FeedEntry] = []
    for row in conn.execute(
        stmt.Get_public_limit, {"published": cursor, "limit": limit}
    ):
        result.append(model.new_entry_from(row))
    return result


def get_news_by_feed(feed_id: str, limit: int, conn: Conn) -> list[FeedEntry]:
    result: list[FeedEntry] = []
    for row in conn.execute(
        stmt.Get_news_by_feed, {"feed_id": feed_id, "limit": limit}
    ):
        result.append(model.new_entry_from(row))
    return result


def get_subs_list(conn: Conn, feed_id: str = "") -> list[Feed]:
    subs_list: list[Feed] = []

    if feed_id in [PublicBucketID, PrivateBucketID, FavBucketID]:
        return []

    if feed_id:
        feed = get_feed_by_id(feed_id, conn).ok()
        if feed:
            subs_list.append(feed)
    else:
        for row in conn.execute(stmt.Get_subs_list):
            subs_list.append(model.new_feed_from(row))
    return subs_list


def get_feeds_by_title(conn: Conn, title: str) -> list[Feed]:
    feeds: list[Feed] = []
    for row in conn.execute(stmt.Get_feeds_by_title, ("%" + title + "%",)).fetchall():
        feeds.append(model.new_feed_from(row))
    return feeds


def check_before_update_all(feed: Feed) -> Result[str, str]:
    updated = arrow.get(feed.updated, RFC3339)
    if updated.int_timestamp + UpdateRateLimit < arrow.now().int_timestamp:
        return OK
    else:
        return Err(
            f"Checking {feed.title} ... Info: Too many requests.\n"
            f"可使用 'ago news -force -u {feed.feed_id}' 强制更新。\n"
        )


def check_before_update_one(
    feed_id: str, parser: str, force: bool, conn: Conn
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


def insert_entries(entries: list[FeedEntry], conn: Conn) -> None:
    item_list = [entry.to_dict() for entry in entries]
    conn.executemany(stmt.Insert_entry, item_list)


def delete_entries(feed_id: str, conn: Conn) -> None:
    conn.execute(stmt.Delete_entries, (feed_id,))


def update_entries(feed_id: str, entries: list[FeedEntry], conn: Conn) -> None:
    delete_entries(feed_id, conn)
    insert_entries(entries, conn)
    updated = arrow.now().format(RFC3339)
    connExec(
        conn, stmt.Update_feed_updated, {"updated": updated, "id": feed_id}
    ).unwrap()


def new_feed_id(conn: Conn) -> str:
    timestamp = 0
    while True:
        feed_id, timestamp = model.next_feed_id(timestamp)
        row = conn.execute(stmt.Get_feed_id, (feed_id,)).fetchone()
        if not row:
            return feed_id


def check_before_subscribe(feed_link: str, conn: Conn) -> Result[str, str]:
    row = conn.execute(stmt.Get_feed_link, (feed_link,)).fetchone()
    if row:
        return Err(f"Exists(不可重复订阅): {feed_link}")
    else:
        return OK


def subscribe_feed(feed_link: str, title: str, parser: str, conn: Conn) -> str:
    """Return the feed_id if nothing wrong."""
    feed_id = new_feed_id(conn)
    conn.execute(
        stmt.Insert_feed,
        dict(
            id=feed_id,
            feed_link=feed_link,
            website="",
            title=title,
            author_name="",
            updated=arrow.now().format(RFC3339),
            notes="",
            parser=parser,
        ),
    )
    return feed_id


def delete_feed(feed_id: str, conn: Conn) -> str:
    row = conn.execute(stmt.Get_feed_id, (feed_id,)).fetchone()
    if not row:
        return f"Not Found: {feed_id}"

    conn.execute(stmt.Delete_feed, (feed_id,))
    delete_entries(feed_id, conn)
    return "OK. 已删除"


def update_feed_id(newid: str, oldid: str, conn: Conn) -> Result[str, str]:
    if oldid.upper() == newid.upper():
        return OK

    param = {"newid": newid, "oldid": oldid}
    err = connExec(conn, stmt.Update_feed_id, param).err()
    if err:
        return Err(err)

    connExec(conn, stmt.Update_entry_feed_id, param).unwrap()
    return OK


def update_feed_title(title: str, feed_id: str, conn: Conn) -> Result[str, str]:
    err = connExec(conn, stmt.Update_feed_title, {"title": title, "id": feed_id}).err()
    if err:
        return Err(err)

    connExec(
        conn, stmt.Update_entry_feed_name, {"feed_name": title, "feed_id": feed_id}
    ).unwrap()
    return OK


def get_entry_by_prefix(prefix: str, conn: Conn) -> list[FeedEntry]:
    rows = conn.execute(stmt.Get_entry_by_id_prefix, (prefix + "%",)).fetchall()
    if not rows:
        return []

    return [model.new_entry_from(row) for row in rows]


def get_entry_in_bucket(bucket: str, prefix: str, conn: Conn) -> list[FeedEntry]:
    rows = conn.execute(
        stmt.Get_entry_in_bucket, {"bucket": bucket, "id": prefix + "%"}
    ).fetchall()

    if not rows:
        return []
    return [model.new_entry_from(row) for row in rows]


def move_to_fav(entry_id: str, conn: Conn) -> str:
    newid = get_next_id(conn)
    connExec(conn, stmt.Move_entry_to_fav, {"oldid": entry_id, "newid": newid}).unwrap()
    return newid


def get_recent_entries(bucket: str, limit: int, conn: Conn) -> list[FeedEntry]:
    entries = []
    for row in conn.execute(stmt.Get_entries_limit, {"bucket": bucket, "limit": limit}):
        entries.append(model.new_entry_from(row))
    return entries


def toggle_entry_bucket(entry: FeedEntry, conn: Conn) -> Result[FeedEntry, str]:
    bucket = Bucket[entry.bucket]
    if bucket not in [Bucket.Public, Bucket.Private]:
        return Err("The bucket is not Public or Private.\n只能在 Public 与 Private 之间切换。")

    toggled = Bucket.Public if bucket is Bucket.Private else Bucket.Private
    feed_id = PublicBucketID if toggled is Bucket.Public else PrivateBucketID
    entry.bucket = toggled.name
    entry.feed_id = feed_id

    connExec(
        conn,
        stmt.Update_entry_bucket,
        {"feed_id": feed_id, "bucket": entry.bucket, "id": entry.entry_id},
    ).unwrap()
    return Ok(entry)


def delete_one_entry(entry_id: str, conn: Conn) -> Result[int, str]:
    match connExec(conn, stmt.Delete_entry, (entry_id,)):
        case Err(e):
            return Err(e)
        case Ok():
            row = conn.execute(stmt.Count_tag_by_entry_id, (entry_id,)).fetchone()
            if row[0]:
                return connExec(conn, stmt.Delete_tag_entry, (entry_id,))
            else:
                return OK


def update_my_feed_info(
    feed_link: str, website: str, title: str, author: str, conn: Conn
) -> Result[int, str]:
    return connExec(
        conn,
        stmt.Update_my_feed_info,
        {"feed_link": feed_link, "website": website, "title": title, "author": author},
    )


def insert_tags(names: list[str], entry_id: str, conn: Conn) -> Result[int, str]:
    pairs = [{"name": name, "entry_id": entry_id} for name in names]
    return connExec(conn, stmt.Insert_tag, pairs, many=True)


def get_by_tag(name: str, limit: int, bucket: str, conn: Conn) -> list[FeedEntry]:
    if bucket == "All":
        rows = conn.execute(stmt.Get_by_tag, {"name": name, "limit": limit})
    else:
        rows = conn.execute(
            stmt.Get_by_tag_bucket, {"name": name, "limit": limit, "bucket": bucket}
        )
    return [model.new_entry_from(row) for row in rows]


def count_by_tag(name: str, bucket: str, conn: Conn) -> int:
    if bucket == "All":
        row = conn.execute(stmt.Count_by_tag, {"name": name}).fetchone()
    else:
        row = conn.execute(
            stmt.Count_by_tag_bucket, {"name": name, "bucket": bucket}
        ).fetchone()
    return row[0]


def search_entry_content(
    keyword: str, limit: int, bucket: str, conn: Conn
) -> list[FeedEntry]:
    if bucket == "All":
        rows = conn.execute(
            stmt.Search_entry_content, {"content": "%" + keyword + "%", "limit": limit}
        )
    else:
        rows = conn.execute(
            stmt.Search_entry_content_bucket,
            {"content": "%" + keyword + "%", "limit": limit, "bucket": bucket},
        )
    return [model.new_entry_from(row) for row in rows]


def count_entry_content(keyword: str, bucket: str, conn: Conn) -> list[FeedEntry]:
    if bucket == "All":
        row = conn.execute(
            stmt.Count_entry_content, {"content": "%" + keyword + "%"}
        ).fetchone()
    else:
        row = conn.execute(
            stmt.Count_entry_content_bucket,
            {"content": "%" + keyword + "%", "bucket": bucket},
        ).fetchone()
    return row[0]


def get_all_tags(conn: Conn) -> list[str]:
    tags = []
    for row in conn.execute(stmt.Get_all_tags):
        tags.append("#" + row[0])
    return tags


def get_tags_by_name(name: str, conn: Conn) -> list[str]:
    tags = []
    for row in conn.execute(stmt.Get_one_tag, ("%" + name + "%",)):
        tags.append("#" + row[0])
    return tags
