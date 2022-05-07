import arrow
from bs4 import BeautifulSoup
from feedparser import FeedParserDict
from ipelago.model import (
    RFC3339,
    Bucket,
    MyParser,
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
        "D MMM YYYY HH:mm:ss Z",
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
        if child.name == "p":
            contents.append("\n")

        if child.name in ["p", "div"]:
            contents.append(get_text_from_soup(child, " "))
        elif child.name == "a":
            link_text = child.text.replace("\n", "")
            if link_text == child.get("href"):
                contents.append(link_text)
            else:
                contents.append(f'[{link_text}]({child.get("href")})')
        elif child.name == "img":
            contents.append(f'![{child.get("alt")}]({child.get("src")})')
        else:
            contents.append(child.get_text(strip=True))

    contents = [x for x in contents if x.strip()]
    return sep.join(contents)


def rss_to_entries(
    feed_id: str,
    feed_title: str,
    parser_dict: FeedParserDict,
    has_title: bool,
    has_summary: bool,
) -> list[FeedEntry]:
    entries = []
    for item in parser_dict.entries:
        published = PubDateToRFC3339(item.published)
        link = item.get("link")
        contents = item.title + "\n" if has_title else ""

        summary = item["content"][1].value if has_summary else item.description
        soup = BeautifulSoup(summary, "html.parser")
        body = contents + get_text_from_soup(soup)
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
    feed_id: str,
    feed_title: str,
    parser: str,
    parser_dict: FeedParserDict,
    verbose: bool,
) -> list[FeedEntry]:
    if verbose:
        print(f"Using parser: {parser}")

    match parser:
        case MyParser.HasTitle.name:
            return rss_to_entries(feed_id, feed_title, parser_dict, True, False)
        case MyParser.HasSummary.name:
            return rss_to_entries(feed_id, feed_title, parser_dict, False, True)
        case _:
            return rss_to_entries(feed_id, feed_title, parser_dict, False, False)
