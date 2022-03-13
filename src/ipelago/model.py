from dataclasses import dataclass
from enum import Enum, auto
from typing import TypedDict


Hour = 60 * 60
Day = 24 * Hour

PublicBucketID = "Public"
PrivateBucketID = "Private"


class Bucket(Enum):
    Public = auto()
    Private = auto()
    News = auto()
    Fav = auto()


@dataclass
class FeedEntry:
    entry_id: str  # ShortID
    title: str  # size limit: 256 bytes
    content: str  # size limit: 1024 bytes
    link: str  # # size limit: 256 bytes
    published: str  # RFC3339(UTC)
    feed_id: str  # (不用于 xml)
    feed_name: str  # (不用于 xml)
    bucket: str = Bucket.Public.name  # (不用于 xml)


@dataclass
class Feed:
    feed_id: str  # Publice/Private/RandomID
    link: str  # link to the feed itself (订阅地址)
    title: str  # size limit: 256 bytes
    author_name: str  # size limit: 256 bytes
    updated: str  # RFC3339
    notes: str = ""  # (不用于 xml)


class AppConfig(TypedDict):
    tl_cursor: str  # RFC3339(UTC)
    news_cursor: str  # RFC3339(UTC)
    zen_mode: bool  # 专注模式
    cli_page_n: int  # 命令行每页列表条数默认上限
    web_page_n: int  # 网页每页列表条数默认上限
    http_proxy: str
    use_proxy: bool


def default_config() -> AppConfig:
    return AppConfig(
        tl_cursor="",
        news_cursor="",
        zen_mode=False,
        cli_page_n=9,
        web_page_n=50,
        http_proxy="",
        use_proxy=True,
    )


CurrentList = list[str]  # list[entry_id]

SubsList = list[Feed]
