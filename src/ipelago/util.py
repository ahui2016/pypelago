import sqlite3

from result import Err, Ok
from ipelago.db import get_my_next, get_cfg, update_cfg, update_current_list
from ipelago.model import (
    Bucket,
    FeedEntry,
)


def print_my_msg(n: int, msg: FeedEntry) -> None:
    title = f"[{n}] [{msg.entry_id}]"
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
