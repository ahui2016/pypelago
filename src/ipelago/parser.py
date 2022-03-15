import arrow
from bs4 import BeautifulSoup
from feedparser import FeedParserDict
from ipelago.model import (
    RFC3339,
    Bucket,
    FeedEntry,
)

def PubDateToRFC3339(pubdate: str) ->  str:
    a = arrow.get(0)
    try:
        a = arrow.get(pubdate).to("local")
    except arrow.parser.ParserError:
        pass

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


def mstdn_to_entries(parserDict: FeedParserDict, title: bool) -> list[FeedEntry]:
    entries = []
    for item in parserDict.entries:
        published = PubDateToRFC3339(item.published)
        link = item.get("link")
        contents = ""

        if title:
            contents = item.title

        soup = BeautifulSoup(item.description, "html.parser")
        body = f"{contents}\n{get_text_from_soup(soup)}"
        msg = FeedEntry(
            feed_id=date_id,
            IslandID="",  # 为节省流量，在服务器端统一填充
            IslandName="",  # 为节省流量，在服务器端统一填充
            Hide=False,
            Time=timestamp,
            Body=utf8_byte_truncate(body, OneMsgSizeLimit),
            Notes=utf8_byte_truncate(link, OneMsgSizeLimit),
        )
        messages.append(msg)

    return messages


def feed_to_messages(feed: FeedParserDict) -> list[Message]:
    print("feed-id:", feed.feed.get("id", ""))
    print("feed-link:", feed.feed.get("link", ""))

    if feed.feed.get("id") == "https://www.v2ex.com/":
        return mstdn_to_messages(feed, True)
    if feed.feed.get("link") == "https://sspai.com":
        return mstdn_to_messages(feed, True)

    return mstdn_to_messages(feed, False)


def messages_to_json(messages: list[Message]) -> tuple[str, ErrMsg]:
    m_json = json.dumps(messages, ensure_ascii=False)
    news_size = len(m_json)
    if news_size > NewsSizeLimit:
        # 如果体积太大，取一半消息，如果还是太大，就返回错误。
        messages = messages[: len(messages) // 2]
        m_json = json.dumps(messages, ensure_ascii=False)
        news_size = len(m_json)
        if news_size > NewsSizeLimit:
            return (
                "",
                f"feed size({format_size(news_size)}) > limit({format_size(NewsSizeLimit)})",
            )

    return m_json, None

