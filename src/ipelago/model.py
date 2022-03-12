from dataclasses import dataclass
from enum import Enum, auto
from typing import TypedDict


Hour = 60 * 60
Day = 24 * Hour


class Bucket(Enum):
    Public = auto()
    Private = auto()
    News = auto()
    Fav = auto()


@dataclass
class FeedEntry:
    entry_id: str  # ShortID
    title: str
    content: str
    link: str
    published: str  # RFC3339(UTC)
    updated: str  # RFC3339(UTC)
    feed_id: str  # (不用于 xml)


@dataclass
class Feed:
    feed_id: str  # RandomID 或订阅地址
    link: str  # link to the feed itself
    title: str
    author_name: str
    updated: str  # RFC3339
    notes: str = ""  # (不用于 xml)
    bucket: str = Bucket.Public.name  # (不用于 xml)


class AppConfig(TypedDict):
    tl_cursor: str  # RFC3339(UTC)
    news_cursor: str  # RFC3339(UTC)
    zen_mode: bool  # 专注模式
    cli_page_n: int  # 命令行每页列表条数默认上限
    web_page_n: int  # 网页每页列表条数默认上限
    http_proxy: str
    use_proxy: bool
    password: str  # 与 session_max_age 一起形成简单的密码保护，安全性不高
    session_started_at: int  # timestamp
    session_max_age: int  # 单位：秒，设置时转换单位：小时。


def default_config() -> AppConfig:
    return AppConfig(
        tl_cursor="",
        news_cursor="",
        zen_mode=False,
        cli_page_n=9,
        web_page_n=50,
        http_proxy="",
        use_proxy=True,
        password="",
        session_started_at=0,
        session_max_age=Day,
    )


CurrentList = list[str]  # list[ShortID]