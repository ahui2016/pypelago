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
    get_news_next,
    get_proxies,
    get_subs_list,
    insert_entries,
    subscribe_feed,
    update_cfg,
)
from ipelago.model import (
    Bucket,
    FeedEntry,
    ShortStrSizeLimit,
    utf8_byte_truncate,
)
from ipelago.parser import feed_to_entries

RequestsTimeout: Final[int] = 5


def requests_get(url: str, conn: sqlite3.Connection):
    return requests.get(url, proxies=get_proxies(conn), timeout=RequestsTimeout)


def print_my_msg(msg: FeedEntry, show_link: bool = False) -> None:
    date = arrow.get(msg.published).format("YYYY-MM-DD")
    title = f"[{msg.entry_id}] [{date}]"
    if Bucket[msg.bucket] is Bucket.Private:
        title += " [private]"
    print(f"{title}\n{msg.content}\n")


def print_my_next_msg(conn: sqlite3.Connection) -> None:
    cfg = get_cfg(conn).unwrap()
    match get_my_next(cfg["tl_cursor"], conn):
        case Err():
            cfg["tl_cursor"] = ""
            update_cfg(cfg, conn)
            print("我的消息：空空如也。")
            print("Try 'ago post [message]' to post a message.")
        case Ok(msg):
            cfg["tl_cursor"] = msg.published
            update_cfg(cfg, conn)
            print_my_msg(msg)


def print_news_msg(msg: FeedEntry, show_link: bool) -> None:
    date = arrow.get(msg.published).format("YYYY-MM-DD")
    title = f"[{msg.entry_id[:4]}] [{date}]"
    print(f"{title}\n{msg.content}")
    if show_link and msg.link:
        print(f"[link] {msg.link}")
    print()


def print_news_next_msg(conn: sqlite3.Connection) -> None:
    cfg = get_cfg(conn).unwrap()
    match get_news_next(cfg["news_cursor"], conn):
        case Err():
            cfg["news_cursor"] = ""
            update_cfg(cfg, conn)
            print("订阅消息：空空如也。")
            print("Try 'ago news -follow [url]' to subscribe a feed.")
        case Ok(msg):
            cfg["news_cursor"] = msg.published
            update_cfg(cfg, conn)
            print_news_msg(msg, cfg["news_show_link"])


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
        entries = get_by_date_buckets(prefix, limit, buckets, conn)
    else:
        entries = get_by_date(prefix, limit, buckets[0], conn)
    print_entries(entries, False, print_my_msg)


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


def subscribe(link: str, conn: sqlite3.Connection) -> None:
    e = check_before_subscribe(link, conn).err()
    if e:
        print(e)
        return

    match retrieve_feed(link, conn):
        case Err(e):
            print(e)
            return
        case Ok(parser_dict):
            feed_title = utf8_byte_truncate(parser_dict.feed.title, ShortStrSizeLimit)
            feed_id = subscribe_feed(link, feed_title, conn)
            entries = feed_to_entries(feed_id, feed_title, parser_dict)
            insert_entries(entries, conn)


def print_subs_list(conn: sqlite3.Connection) -> None:
    sl = get_subs_list(conn)
    if not sl:
        print("Info: 尚未订阅任何源。")
        print("Try 'ago news -follow [url]' to subscribe a feed.")
        return

    for feed in sl:
        print(f"[{feed.feed_id}] {feed.title}\n{feed.link}\n")


# def delete_feed(prefix:str, conn: sqlite3.Connection) -> None:
#     feeds = get_feed_by_id_prefix(prefix, conn)
#     if len(feeds) < 1:
#         print(f'Not Found: {prefix}')
#     elif len(feeds) == 1:
#         print(delete_feed_by_id(feeds[0].feed_id, conn))
#     else:
#         for feed in feeds:
#             print(f"[{feed.feed_id}]\n{feed.title}\n{feed.link}\n")
#         print('')
