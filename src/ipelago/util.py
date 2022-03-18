import sqlite3
from typing import Callable, Final
import arrow
import requests
import feedparser
from feedparser import FeedParserDict
from result import Err, Ok, Result
import ipelago.db as db
import ipelago.stmt as stmt
from ipelago.model import (
    Bucket,
    FeedEntry,
    ShortStrSizeLimit,
    new_my_msg,
    utf8_byte_truncate,
)
from ipelago.parser import feed_to_entries

RequestsTimeout: Final[int] = 5


def requests_get(url: str, conn: sqlite3.Connection):
    return requests.get(url, proxies=db.get_proxies(conn), timeout=RequestsTimeout)


def print_my_msg(msg: FeedEntry, show_link: bool = False) -> None:
    date = arrow.get(msg.published).format("YYYY-MM-DD")
    title = f"[{msg.entry_id}] [{date}]"
    if Bucket[msg.bucket] is Bucket.Private:
        title += " [private]"
    print(f"{title}\n{msg.content}\n")


def print_my_next_msg(conn: sqlite3.Connection) -> None:
    cfg = db.get_cfg(conn).unwrap()
    match db.get_my_next(cfg["tl_cursor"], conn):
        case Err():
            cfg["tl_cursor"] = ""
            db.update_cfg(cfg, conn)
            print("我的消息：空空如也。")
            print("Try 'ago post [message]' to post a message.")
        case Ok(msg):
            cfg["tl_cursor"] = msg.published
            db.update_cfg(cfg, conn)
            print_my_msg(msg)


def print_news(msg: FeedEntry, show_link: bool, short_id: bool) -> None:
    entry_id = msg.entry_id[:4] if short_id else msg.entry_id
    date = arrow.get(msg.published).format("YYYY-MM-DD")
    title = f"[{entry_id}] ({msg.feed_id}) {date}"
    print(f"{title}\n{msg.content}")
    if show_link and msg.link:
        print(f"[link] {msg.link}")
    print()


def print_news_short_id(msg: FeedEntry, show_link: bool) -> None:
    return print_news(msg, show_link, True)


def print_news_next_msg(conn: sqlite3.Connection) -> None:
    cfg = db.get_cfg(conn).unwrap()
    match db.get_news_next(cfg["news_cursor"], conn):
        case Err():
            cfg["news_cursor"] = ""
            db.update_cfg(cfg, conn)
            print("订阅消息：空空如也。")
            print("Try 'ago news -follow [url]' to subscribe a feed.")
        case Ok(msg):
            cfg["news_cursor"] = msg.published
            db.update_cfg(cfg, conn)
            print_news_short_id(msg, cfg["news_show_link"])


def print_entries(
    entries: list[FeedEntry],
    show_link: bool,
    printer: Callable[[FeedEntry, bool], None],
) -> None:
    if not entries:
        print("No message. (找不到该命令指定的消息)")
        return
    for entry in entries:
        printer(entry, show_link)


def print_my_entries(
    prefix: str, limit: int, buckets: list[str], conn: sqlite3.Connection
) -> None:
    if len(buckets) > 1:
        entries = db.get_by_date_buckets(prefix, limit, buckets, conn)
    else:
        entries = db.get_by_date(prefix, limit, buckets[0], conn)
    print_entries(entries, False, print_my_msg)


def print_my_today(limit: int, buckets: list[str], conn: sqlite3.Connection) -> None:
    prefix = arrow.now().format("YYYY-MM-DD")
    print_my_entries(prefix, limit, buckets, conn)


def print_my_yesterday(
    limit: int, buckets: list[str], conn: sqlite3.Connection
) -> None:
    prefix = arrow.now().shift(days=-1).format("YYYY-MM-DD")
    print_my_entries(prefix, limit, buckets, conn)


def post_msg(msg: str, bucket: Bucket) -> None:
    with db.connect_db() as conn:
        match new_my_msg(db.get_next_id(conn), msg, bucket):
            case Err(e):
                print(e)
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
                first = db.get_my_next("", conn).unwrap()
                print_my_msg(first)


def retrieve_feed(
    feed_url: str, conn: sqlite3.Connection
) -> Result[FeedParserDict, str]:
    """每次 retrieve_feed 之前都应该检查更新频率，避免浪费网络资源。"""

    # 允许添加本地源
    if not feed_url.startswith("http"):
        return Ok(feedparser.parse(feed_url))

    print("retrieving", feed_url)
    r = requests_get(feed_url, conn)

    if r.status_code != 200:
        return Err(f"Fail: {r.status_code}: {r.text}")

    return Ok(feedparser.parse(r.text))


def subscribe(link: str, conn: sqlite3.Connection) -> None:
    e = db.check_before_subscribe(link, conn).err()
    if e:
        print(e)
        return

    match retrieve_feed(link, conn):
        case Err(e):
            print(e)
            return
        case Ok(parser_dict):
            feed_title = utf8_byte_truncate(parser_dict.feed.title, ShortStrSizeLimit)
            feed_id = db.subscribe_feed(link, feed_title, conn)
            entries = feed_to_entries(feed_id, feed_title, parser_dict)
            db.insert_entries(entries, conn)


# 如果指定 feed_id, 则只显示指定的一个源，否则显示全部源的信息。
def print_subs_list(conn: sqlite3.Connection, feed_id: str = "") -> None:
    sl = db.get_subs_list(conn, feed_id)
    if not sl:
        if feed_id:
            print(f"Not Found: {feed_id}")
            return
        print("Info: 尚未订阅任何源。")
        print("Try 'ago news -follow [url]' to subscribe a feed.")
        return

    print()
    if feed_id:
        feed = sl[0]
        print(f"[{feed.feed_id}] {feed.title}\n{feed.link}\n")
        return

    for feed in sl:
        print(f"[{feed.feed_id}] {feed.title}\n{feed.link}\n")


def print_fav_entry(msg: FeedEntry, show_link: bool = False) -> None:
    date = arrow.get(msg.published).format("YYYY-MM-DD")
    title = f"[{msg.entry_id}] ({msg.feed_id}) {date}"
    print(f"{title}\n{msg.content}")
    print("--------")
    if msg.link:
        print(msg.link)
    elif msg.feed_name:
        print(msg.feed_name)
    print()


def move_to_fav(prefix: str, conn: sqlite3.Connection) -> None:
    entries = db.get_entry_by_prefix(prefix, conn)
    if len(entries) < 1:
        print(f"Not Found: {prefix}")
    elif len(entries) == 1:
        newid = db.move_to_fav(entries[0].entry_id, conn)
        entry = db.get_entry_by_prefix(newid[:4], conn)[0]
        print_fav_entry(entry)
    else:
        for entry in entries:
            print_news(entry, False, False)
        print("Require long-id (需要使用完整ID)")


def print_recent_fav(conn: sqlite3.Connection) -> None:
    cfg = db.get_cfg(conn).unwrap()
    entries = db.get_recent_fav(cfg["cli_page_n"], conn)
    if not entries:
        print("收藏消息：空空如也。")
        print("Try 'ago fav -h' to get help.")
        return

    print_entries(entries, False, print_fav_entry)
