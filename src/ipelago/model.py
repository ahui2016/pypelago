from dataclasses import dataclass
from enum import Enum, auto
from typing import TypedDict
import arrow

from result import Err, Ok, Result


Hour = 60 * 60
Day = 24 * Hour

PublicBucketID = "Public"
PrivateBucketID = "Private"

KB = 1024
OneMsgSizeLimit = KB  # 一条消息的体积上限
FeedSizeLimitBase = 20 * KB  # RSS feed 体积上限基数
FeedSizeLimitMargin = 10 * KB  # 体积上限允许超出一点 (比如 XML tag, 日期等的体积)
FeedSizeLimit = FeedSizeLimitBase + FeedSizeLimitMargin


class Bucket(Enum):
    Public = auto()
    Private = auto()
    News = auto()
    Fav = auto()

def my_bucket(pri:bool) -> Bucket:
    return Bucket.Private if pri else Bucket.Public

@dataclass
class FeedEntry:
    entry_id: str  # ShortID
    title: str  # size limit: 256 bytes
    content: str  # size limit: 1024 bytes
    link: str  # # size limit: 256 bytes
    published: str  # RFC3339(UTC)
    feed_id: str  # (不用于 xml)
    feed_name: str  # (不用于 xml)
    bucket: str  # Bucket.name  # (不用于 xml)


def new_my_msg(entry_id: str, content: str, bucket: Bucket) -> Result[FeedEntry, str]:
    size = byte_len(content)
    if size > OneMsgSizeLimit:
        return Err(f"size {size} > limit({OneMsgSizeLimit})")

    feed_id = PublicBucketID if bucket is Bucket.Public else PrivateBucketID
    entry = FeedEntry(
        entry_id=entry_id,
        title="",
        content=content,
        link="",
        published=arrow.now().format(arrow.FORMAT_RFC3339),
        feed_id=feed_id,
        feed_name="",
        bucket=bucket.name,
    )
    return Ok(entry)


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


def byte_len(s: str) -> int:
    return len(s.encode("utf8"))


def utf8_lead_byte(b):
    """A UTF-8 intermediate byte starts with the bits 10xxxxxx."""
    return (b & 0xC0) != 0x80


# https://stackoverflow.com/questions/13727977/truncating-string-to-byte-length-in-python
def utf8_byte_truncate(text: str, max_bytes: int) -> str:
    """If text[max_bytes] is not a lead byte, back up until a lead byte is
    found and truncate before that character."""
    utf8 = text.encode("utf8")
    if len(utf8) <= max_bytes:
        return utf8.decode("utf8")
    i = max_bytes
    while i > 0 and not utf8_lead_byte(utf8[i]):
        i -= 1
    return utf8[:i].decode("utf8") + " ..."
