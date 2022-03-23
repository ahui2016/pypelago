import sqlite3
from typing import Callable, Final
import arrow
import pyperclip
import requests
import feedparser
from feedparser import FeedParserDict
from result import Err, Ok, Result
import ipelago.db as db
import ipelago.stmt as stmt
from ipelago.model import (
    Bucket,
    Feed,
    FeedEntry,
    ShortStrSizeLimit,
    extract_tags,
    new_my_msg,
    utf8_byte_truncate,
)
from ipelago.parser import feed_to_entries

RequestsTimeout: Final[int] = 5

Conn = sqlite3.Connection


def copytext(text: str) -> None:
    try:
        pyperclip.copy(text)
    except Exception:
        pass


def requests_get(url: str, conn: Conn):
    return requests.get(url, proxies=db.get_proxies(conn), timeout=RequestsTimeout)


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


def print_my_msg(msg: FeedEntry, show_link: bool = False) -> None:
    if Bucket[msg.bucket] is Bucket.Fav:
        print_fav_entry(msg)
        return

    date = arrow.get(msg.published).format("YYYY-MM-DD")
    title = f"[{msg.entry_id}] [{date}]"
    if Bucket[msg.bucket] is Bucket.Private:
        title += " [private]"
    print(f"{title}\n{msg.content}\n")


def print_my_next_msg(conn: Conn) -> None:
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


def my_cursor_goto(date_prefix: str, conn: Conn) -> None:
    cfg = db.get_cfg(conn).unwrap()
    match db.my_cursor_goto(date_prefix, conn):
        case Err(e):
            print(e)
        case Ok(msg):
            cfg["tl_cursor"] = msg.published
            db.update_cfg(cfg, conn)
            print_my_msg(msg)


def news_cursor_goto(date_prefix: str, conn: Conn) -> None:
    cfg = db.get_cfg(conn).unwrap()
    match db.news_cursor_goto(date_prefix, conn):
        case Err(e):
            print(e)
        case Ok(msg):
            cfg["news_cursor"] = msg.published
            db.update_cfg(cfg, conn)
            print_news_short_id(msg, cfg["news_show_link"])


def print_news(msg: FeedEntry, show_link: bool, short_id: bool) -> None:
    entry_id = msg.entry_id[:4] if short_id else msg.entry_id
    date = arrow.get(msg.published).format("YYYY-MM-DD")
    title = f"[{entry_id}] ({date}) {msg.feed_name}"
    print(f"{title}\n{msg.content}")
    if show_link and msg.link:
        print(f"[link] {msg.link}")
    print()


def print_news_short_id(msg: FeedEntry, show_link: bool) -> None:
    return print_news(msg, show_link, True)


def print_news_next_msg(conn: Conn) -> None:
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
        print("Not Found. (找不到该命令指定的消息)")
        return
    for entry in entries:
        printer(entry, show_link)


def print_my_entries(prefix: str, limit: int, buckets: list[str], conn: Conn) -> None:
    if not buckets:
        entries = db.get_by_date_my_buckets(prefix, limit, conn)
    else:
        entries = db.get_by_date(prefix, limit, buckets[0], conn)

    print_entries(entries, False, print_my_msg)


def count_my_entries(prefix: str, buckets: list[str], conn: Conn) -> None:
    if not buckets:
        buckets = [Bucket.Public.name, Bucket.Private.name]
    n = db.conut_by_date_buckets(prefix, buckets, conn)
    print(f"[{prefix}]: {n} message(s)")


def print_my_today(limit: int, buckets: list[str], conn: Conn) -> None:
    prefix = arrow.now().format("YYYY-MM-DD")
    print_my_entries(prefix, limit, buckets, conn)


def print_my_yesterday(limit: int, buckets: list[str], conn: Conn) -> None:
    prefix = arrow.now().shift(days=-1).format("YYYY-MM-DD")
    print_my_entries(prefix, limit, buckets, conn)


def insert_tags(tags: list[str], entry_id: str, conn: Conn) -> None:
    db.insert_tags(tags, entry_id, conn).unwrap()
    print(f'[Tags] {" ".join(tags)}')


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
                print_my_msg(entry)
                tags = extract_tags(msg)
                if tags:
                    insert_tags(tags, entry.entry_id, conn)


def retrieve_feed(feed_url: str, conn: Conn) -> Result[FeedParserDict, str]:
    """每次 retrieve_feed 之前都应该检查更新频率，避免浪费网络资源。"""

    # 允许添加本地源
    if not feed_url.startswith("http"):
        return Ok(feedparser.parse(feed_url))

    print("retrieving", feed_url)
    r = requests_get(feed_url, conn)

    if r.status_code != 200:
        return Err(f"Fail: {r.status_code}: {r.text}")

    return Ok(feedparser.parse(r.text))


def subscribe(link: str, parser: str, conn: Conn) -> None:
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
            feed_id = db.subscribe_feed(link, feed_title, parser, conn)
            print_subs_list(conn, feed_id)
            entries = feed_to_entries(feed_id, feed_title, parser, parser_dict, True)
            db.insert_entries(entries, conn)
            print("OK.")


def retrieve_and_update(feed: Feed, verbose: bool, conn: Conn) -> None:
    match retrieve_feed(feed.link, conn):
        case Err(e):
            print(e)
            return
        case Ok(parser_dict):
            entries = feed_to_entries(
                feed.feed_id, feed.title, feed.parser, parser_dict, verbose
            )
            db.update_entries(feed.feed_id, entries, conn)
            print("OK.")


def update_one_feed(feed_id: str, parser: str, force: bool, conn: Conn) -> None:
    match db.check_before_update_one(feed_id, parser, force, conn):
        case Err(e):
            print(e)
        case Ok(feed):
            retrieve_and_update(feed, True, conn)


def update_all_feeds(conn: Conn) -> None:
    sl = db.get_subs_list(conn)
    for feed in sl:
        match db.check_before_update_all(feed):
            case Err(e):
                print(e)
            case Ok():
                retrieve_and_update(feed, False, conn)


# 如果指定 feed_id, 则只显示指定的一个源，否则显示全部源的信息。
def print_subs_list(conn: Conn, feed_id: str = "") -> None:
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


def get_one_from(entries: list[FeedEntry], prefix: str) -> Result[FeedEntry, str]:
    if len(entries) < 1:
        return Err(f"Not Found: {prefix}")

    if len(entries) > 1:
        for entry in entries:
            print_news(entry, False, False)
        return Err("Require long-id (需要使用完整ID)")

    return Ok(entries[0])


def get_entry_by_prefix(prefix: str, conn: Conn) -> Result[FeedEntry, str]:
    entries = db.get_entry_by_prefix(prefix, conn)
    return get_one_from(entries, prefix)


def get_entry_in_bucket(prefix: str, conn: Conn) -> Result[FeedEntry, str]:
    entries = db.get_entry_in_bucket(Bucket.News.name, prefix, conn)
    return get_one_from(entries, prefix)


def move_to_fav(prefix: str, conn: Conn) -> None:
    match get_entry_in_bucket(prefix, conn):
        case Err(e):
            print(e)
        case Ok(entry):
            newid = db.move_to_fav(entry.entry_id, conn)
            fav_entry = db.get_entry_by_prefix(newid, conn)[0]
            print_fav_entry(fav_entry)


def copy_msg_link(prefix: str, link: bool, conn: Conn) -> None:
    match get_entry_by_prefix(prefix, conn):
        case Err(e):
            print(e)
        case Ok(entry):
            if link:
                print(entry.link)
                copytext(entry.link)
            else:
                copytext(entry.content)


def toggle_entry_bucket(prefix: str) -> None:
    with db.connect_db() as conn:
        match get_entry_by_prefix(prefix, conn):
            case Err(e):
                print(e)
            case Ok(entry):
                match db.toggle_entry_bucket(entry, conn):
                    case Err(e):
                        print(e)
                    case Ok(toggled):
                        print_my_msg(toggled)


def print_recent_fav(limit: int, conn: Conn) -> None:
    entries = db.get_recent_fav(limit, conn)
    if not entries:
        print("收藏消息：空空如也。")
        print("Try 'ago fav -h' to get help.")
        return

    print_entries(entries, False, print_fav_entry)


def search_by_tag(tag: str, limit:int, conn: Conn) -> None:
    print(f"Search Tag: {tag}\n")
    entries = db.get_by_tag(tag, limit, conn)
    if not entries:
        print("Not Found (找不到相关信息)")
    else:
        print_entries(entries, False, print_my_msg)
