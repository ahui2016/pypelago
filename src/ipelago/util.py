import sqlite3
from typing import Callable, Final
import arrow
import requests
import feedparser
from feedparser import FeedParserDict
from result import Err, Ok, Result
from ipelago.db import (
    check_before_subscribe,
    get_by_date,
    get_by_date_buckets,
    get_my_next,
    get_cfg,
    get_proxies,
    update_cfg,
    update_current_list,
)
from ipelago.model import (
    Bucket,
    FeedEntry,
)

RequestsTimeout: Final[int] = 5


def requests_get(url: str, conn: sqlite3.Connection):
    return requests.get(url, proxies=get_proxies(conn), timeout=RequestsTimeout)


def print_my_msg(n: int, msg: FeedEntry) -> None:
    date = arrow.get(msg.published).format("YYYY-MM-DD")
    title = f"[{n}] [{msg.entry_id}] [{date}]"
    if Bucket[msg.bucket] is Bucket.Private:
        title += " [private]"
    print(f"{title}\n{msg.content}\n")


def print_my_next_msg(conn: sqlite3.Connection) -> None:
    cfg = get_cfg(conn).unwrap()
    match get_my_next(cfg["tl_cursor"], conn):
        case Err(_):
            cfg["tl_cursor"] = ""
            update_cfg(cfg, conn)
            update_current_list([], conn)
            print("我的消息：空空如也。")
            print("Try 'ago post [message]' to post a message.")
        case Ok(msg):
            cfg["tl_cursor"] = msg.published
            update_cfg(cfg, conn)
            update_current_list([msg.entry_id], conn)
            print_my_msg(1, msg)


def print_entries(
    entries: list[FeedEntry],
    printer: Callable[[int, FeedEntry], None],
    conn: sqlite3.Connection,
) -> None:
    if not entries:
        print("No message. (找不到该命令指定的消息)")
        update_current_list([], conn)
        return
    cl = []
    for i, entry in enumerate(entries):
        printer(i + 1, entry)
        cl.append(entry.entry_id)
    update_current_list(cl, conn)


def print_my_entries(
    prefix: str, limit: int, buckets: list[str], conn: sqlite3.Connection
) -> None:
    if len(buckets) > 1:
        entries = get_by_date_buckets(prefix, limit, buckets, conn)
    else:
        entries = get_by_date(prefix, limit, buckets[0], conn)
    print_entries(entries, print_my_msg, conn)


def print_my_today(limit: int, buckets: list[str], conn: sqlite3.Connection) -> None:
    prefix = arrow.now().format("YYYY-MM-DD")
    print_my_entries(prefix, limit, buckets, conn)


def print_my_yesterday(
    limit: int, buckets: list[str], conn: sqlite3.Connection
) -> None:
    prefix = arrow.now().shift(days=-1).format("YYYY-MM-DD")
    print_my_entries(prefix, limit, buckets, conn)


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


def subscribe(link:str, title:str, conn: sqlite3.Connection) -> None:
    e = check_before_subscribe(link, conn).err()
    if e:
        print(e)
        return
    
    match retrieve_feed(link, conn):
        case Err(e):
            print(e)
            return
        case Ok(parser_dict):
