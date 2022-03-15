import sqlite3
from typing import Callable
import arrow
from result import Err, Ok
from ipelago.db import (
    get_by_date,
    get_by_date_buckets,
    get_my_next,
    get_cfg,
    update_cfg,
    update_current_list,
)
from ipelago.model import (
    Bucket,
    FeedEntry,
)


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
