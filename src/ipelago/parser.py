import arrow
from bs4 import BeautifulSoup
from feedparser import FeedParserDict
from ipelago.model import (
    RFC3339,
    Bucket,
    ShortStrSizeLimit,
    EntrySizeLimit,
    FeedEntry,
    utf8_byte_truncate,
)
from ipelago.shortid import rand_date_id


def PubDateToRFC3339(pubdate: str) -> str:
    a = arrow.get(0)
    try:
        a = arrow.get(pubdate).to("local")
    except arrow.parser.ParserError:
        pass

    if a.int_timestamp > 0:
        return a.format(RFC3339)

    date_formats = [
        "DD MMM YYYY HH:mm:ss Z",
    ]
    for date_format in date_formats:
        try:
            a = arrow.get(pubdate, date_format).to("local")
            break
        except arrow.parser.ParserError:
            pass

    if a.int_timestamp == 0:
        raise arrow.parser.ParserError(f"Failed to parse '{pubdate}'")

    return a.format(RFC3339)


def get_text_from_soup(soup, sep: str = "\n") -> str:
    contents = []
    for child in soup.contents:
        if child.name in ["p", "div"]:
            contents.append("\n")
            contents.append(get_text_from_soup(child, " "))
        elif child.name == "a":
            if child.text == child.get("href"):
                contents.append(child.text)
            else:
                contents.append(f'[{child.text}]({child.get("href")})')
        elif child.name == "img":
            contents.append(f'![{child.get("alt")}]({child.get("src")})')
        else:
            contents.append(child.get_text(strip=True))

    contents = [x for x in contents if x.strip()]
    return sep.join(contents)


def mstdn_to_entries(
    feed_id: str, feed_title: str, parser_dict: FeedParserDict, title: bool
) -> list[FeedEntry]:
    entries = []
    for item in parser_dict.entries:
        published = PubDateToRFC3339(item.published)
        link = item.get("link")
        contents = item.title if title else ""

        soup = BeautifulSoup(item.description, "html.parser")
        body = f"{contents}\n{get_text_from_soup(soup)}"
        msg = FeedEntry(
            entry_id=rand_date_id(),
            content=utf8_byte_truncate(body, EntrySizeLimit),
            link=utf8_byte_truncate(link, ShortStrSizeLimit),
            published=published,
            feed_id=feed_id,
            feed_name=feed_title,
            bucket=Bucket.News.name,
        )
        entries.append(msg)

    return entries


def feed_to_entries(
    feed_id: str, feed_title: str, parser_dict: FeedParserDict
) -> list[FeedEntry]:
    print("feed-id:", parser_dict.feed.get("id", ""))
    print("feed-link:", parser_dict.feed.get("link", ""))

    if parser_dict.feed.get("id") == "https://www.v2ex.com/":
        return mstdn_to_entries(feed_id, feed_title, parser_dict, True)
    if parser_dict.feed.get("link") == "https://sspai.com":
        return mstdn_to_entries(feed_id, feed_title, parser_dict, True)

    return mstdn_to_entries(feed_id, feed_title, parser_dict, False)


"""
def messages_to_json(entries: list[FeedEntry]) -> Result[str, str]:
    m_json = json.dumps(entries, ensure_ascii=False)
    news_size = len(m_json)
    if news_size > FeedSizeLimit:
        # 如果体积太大，取一半消息，如果还是太大，就返回错误。
        entries = entries[: len(entries) // 2]
        m_json = json.dumps(entries, ensure_ascii=False)
        news_size = len(m_json)
        if news_size > FeedSizeLimit:
            return Err(
                f"feed size({format_size(news_size)}) > limit({format_size(FeedSizeLimit)})",
            )

    return Ok(m_json)
"""