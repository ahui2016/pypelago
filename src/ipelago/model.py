from dataclasses import dataclass
from enum import Enum, auto
import re
from typing import Final, Pattern, TypedDict
import arrow

from result import Err, Ok, Result

from ipelago.shortid import base_repr


Hour: Final[int] = 60 * 60
Day: Final[int] = 24 * Hour
RFC3339: Final[str] = "YYYY-MM-DDTHH:mm:ssZZ"

PublicBucketID: Final[str] = "Public"
PrivateBucketID: Final[str] = "Private"
FavBucketID: Final[str] = "Fav"

KB: Final[int] = 1024
EntrySizeLimit: Final[int] = KB  # 一条消息的体积上限
FeedSizeLimitBase: Final[int] = 20 * KB  # RSS feed 体积上限基数
FeedSizeLimitMargin: Final[int] = 10 * KB  # 体积上限允许超出一点 (比如 XML tag, 日期等的体积)
FeedSizeLimit: Final[int] = FeedSizeLimitBase + FeedSizeLimitMargin
ShortStrSizeLimit: Final[int] = 256  # bytes
TagSizeLimit: Final[int] = 30  # bytes

OK: Final[Ok] = Ok("OK")

TagsPattern: Final[Pattern[str]] = re.compile(r"\s#([\S]+)\s")
"""标签以“空格井号”开头，以空格结尾"""


class Bucket(Enum):
    Public = auto()
    Private = auto()
    News = auto()
    Fav = auto()


class MyParser(Enum):
    Base = auto()  # 忽略 title 和 summary
    HasTitle = auto()  # 不忽略 title
    HasSummary = auto()  # 获取 summary 当作正文


def my_bucket(pri: bool) -> Bucket:
    return Bucket.Private if pri else Bucket.Public


@dataclass
class FeedEntry:
    entry_id: str  # ShortID
    content: str  # size limit: 1024 bytes
    link: str  # size limit: 256 bytes
    published: str  # RFC3339(UTC)
    feed_id: str  # (不用于 xml)
    feed_name: str  # (不用于 xml)
    bucket: str  # Bucket.name  # (不用于 xml)

    def to_dict(self) -> dict:
        return dict(
            id=self.entry_id,
            content=self.content,
            link=self.link,
            published=self.published,
            feed_id=self.feed_id,
            feed_name=self.feed_name,
            bucket=self.bucket,
        )


def new_my_msg(entry_id: str, content: str, bucket: Bucket) -> Result[FeedEntry, str]:
    content = content.strip()
    size = byte_len(content)
    if size > EntrySizeLimit:
        return Err(f"size {size} > limit({EntrySizeLimit})")

    feed_id = PublicBucketID if bucket is Bucket.Public else PrivateBucketID
    entry = FeedEntry(
        entry_id=entry_id,
        content=content,
        link="",
        published=arrow.now().format(RFC3339),
        feed_id=feed_id,
        feed_name="",
        bucket=bucket.name,
    )
    return Ok(entry)


def new_entry_from(row: dict) -> FeedEntry:
    return FeedEntry(
        entry_id=row["id"],
        content=row["content"],
        link=row["link"],
        published=row["published"],
        feed_id=row["feed_id"],
        feed_name=row["feed_name"],
        bucket=row["bucket"],
    )


@dataclass
class Feed:
    feed_id: str  # Publice/Private/DateID
    feed_link: str  # link to the feed itself (订阅地址) size limit: 256 bytes
    website: str
    title: str  # size limit: 256 bytes
    author_name: str  # size limit: 256 bytes
    updated: str  # RFC3339
    notes: str = ""  # (不用于 xml)
    parser: str = ""  # (不用于 xml)

    def to_dict(self) -> dict:
        return dict(
            id=self.feed_id,
            feed_link=self.feed_link,
            website=self.website,
            title=self.title,
            author_name=self.author_name,
            updated=self.updated,
            notes=self.notes,
            parser=self.parser,
        )


def new_feed_from(row: dict) -> Feed:
    return Feed(
        feed_id=row["id"],
        feed_link=row["feed_link"],
        website=row["website"],
        title=row["title"],
        author_name=row["author_name"],
        updated=row["updated"],
        notes=row["notes"],
        parser=row["parser"],
    )


class AppConfig(TypedDict):
    tl_cursor: str  # RFC3339(UTC)
    news_cursor: str  # RFC3339(UTC)
    news_show_link: bool
    zen_mode: bool  # 专注模式
    cli_page_n: int  # 命令行每页列表条数默认上限
    web_page_n: int  # 网页每页列表条数默认上限
    http_proxy: str
    use_proxy: bool


def default_config() -> AppConfig:
    return AppConfig(
        tl_cursor="",
        news_cursor="",
        news_show_link=False,
        zen_mode=False,
        cli_page_n=9,
        web_page_n=50,
        http_proxy="",
        use_proxy=True,
    )


CurrentList = list[str]  # list[entry_id]


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


def next_feed_id(timestamp: int) -> tuple[str, int]:
    dt = arrow.now() if timestamp == 0 else arrow.get(timestamp + 1)
    new_id = base_repr(dt.int_timestamp, 36)
    return new_id, dt.int_timestamp


def extract_tags(s: str) -> list[str]:
    """标签必须以“空格井号”开头，以空格结尾，并且不超过 TagSizeLimit"""
    if s[0] == "#":
        s = " " + s  # 因为标签必须以“空格井号”开头
    tags = TagsPattern.findall(s)
    return [tag for tag in tags if byte_len(tag) <= TagSizeLimit]
