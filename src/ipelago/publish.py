import hashlib
from pathlib import Path
import shutil
import sqlite3
from typing import Final, TypedDict
import arrow
from jinja2 import (
    Environment,
    FileSystemLoader,
    PackageLoader,
    select_autoescape,
)
from result import Result, Err
from ipelago import stmt

from ipelago.db import get_feed_by_id, get_public_limit, get_recent_entries
from ipelago.model import OK, RFC3339, Bucket, Feed, FeedEntry, FeedSizeLimit, PublicBucketID

Conn = sqlite3.Connection

default_output_folder: Final[str] = "public"

index_html: Final[str] = "index.html"
atom_xml: Final[str] = "atom.xml"
atom_entries_limit: Final[int] = 30  # RSS 最多包含多少条信息


class Link(TypedDict):
    name: str
    href: str


def new_link():
    return Link(name="", href="")


class Links(TypedDict):
    index_page: Link
    next_page: Link
    prev_page: Link
    footer: Link


def new_links():
    return Links(
        index_page=new_link(),
        next_page=new_link(),
        prev_page=new_link(),
        footer=new_link(),
    )


try:
    loader = PackageLoader("ipelago")
except ValueError:
    loader = FileSystemLoader("src/ipelago/templates")

jinja_env = Environment(loader=loader, autoescape=select_autoescape())


def get_src_dir() -> Path:
    tmpl = jinja_env.get_template(index_html)
    if not tmpl.filename:
        raise ValueError(f"NotFound: {index_html}")
    return Path(tmpl.filename).parent


def copy_static_files(dst_dir: Path) -> None:
    static_files = ["simple.css", "style.css"]
    for name in static_files:
        dst = dst_dir.joinpath(name)
        if not dst.exists():
            src = get_src_dir().joinpath(name)
            shutil.copyfile(src, dst)


def ensure_dst_dir(dst_dir: Path, force: bool) -> bool:
    """Return False if encounter an error."""
    if not dst_dir.exists():
        print(f"Create folder {dst_dir.resolve()}")
        dst_dir.mkdir(parents=True)
        return True
    else:
        if not force:
            print("Error: require '-force' to overwrite.")
            print("请使用 '-force' 参数确认覆盖 output 文件夹的内容。\n")
            return False
    return True


def publish_html_rss(conn: Conn, limit: int, output: str, force: bool) -> None:
    dst_dir = Path(output) if output else Path(default_output_folder)
    dst_dir = dst_dir.resolve()
    print(f"\nOutput to {dst_dir}")
    ok = ensure_dst_dir(dst_dir, force)
    if not ok:
        return
    feed = get_feed_by_id(PublicBucketID, conn).unwrap()
    feed.updated = arrow.now().format(RFC3339)[:10]
    publish_html(conn, feed, limit, dst_dir)
    publish_rss(conn, feed, dst_dir)


def publish_rss(conn: Conn, feed: Feed, dst_dir: Path) -> None:
    entries = get_recent_entries(Bucket.Public.name, atom_entries_limit, conn)
    rss = render_atom_rss(atom_xml, feed, entries)
    output_file = dst_dir.joinpath(atom_xml)
    output_file.write_text(rss, encoding="utf-8")


def publish_html(conn: Conn, feed: Feed, limit: int, dst_dir: Path) -> None:
    total = conn.execute(stmt.Count_by_feed_id, (PublicBucketID,)).fetchone()[0]
    if total <= limit:
        entries = get_public_limit("", limit, conn)
        render_index_page(dst_dir, feed, entries)
    else:
        render_all_pages(dst_dir, feed, total, limit, conn)

    copy_static_files(dst_dir)
    print("OK.\n")


def get_output_names(current_page: int, total: int, page_limit: int) -> dict:
    names: dict = {}
    if current_page > 1:
        names["next"] = f"p{current_page-1}.html"

    if total - current_page * page_limit < page_limit:
        names["prev"] = index_html
    else:
        names["prev"] = f"p{current_page+1}.html"

    if total - current_page * page_limit <= 0:
        names["output"] = index_html
        names["prev"] = ""
    else:
        names["output"] = f"p{current_page}.html"

    return names


def render_all_pages(
    dst_dir: Path, feed: Feed, total: int, limit: int, conn: Conn
) -> None:
    page = 0
    cursor: str = ""

    while True:
        page += 1
        names = get_output_names(page, total, limit)
        footer = (
            Link(name=feed.website, href=feed.website)
            if names["output"] == index_html
            else new_link()
        )
        links = Links(
            index_page=Link(name="", href=index_html),
            prev_page=Link(name="Prev", href=names.get("prev", "")),
            next_page=Link(name="Next", href=names.get("next", "")),
            footer=footer,
        )
        entries = get_public_limit(cursor, limit, conn)
        cursor = entries[-1].published
        render_write_page(dst_dir, index_html, names["output"], feed, links, entries)
        if names["output"] == index_html:
            break


def render_index_page(dst_dir: Path, feed: Feed, entries: list[FeedEntry]) -> None:
    links = new_links()
    links["index_page"] = Link(name="", href=feed.website)
    links["footer"] = Link(name=feed.website, href=feed.website)
    render_write_page(dst_dir, index_html, index_html, feed, links, entries)


def render_write_page(
    dst_dir: Path,
    tmpl_name: str,
    output_name: str,
    feed: Feed,
    links: Links,
    entries: list[FeedEntry],
) -> None:
    tmpl = jinja_env.get_template(tmpl_name)
    if not tmpl.filename:
        raise ValueError(f"NotFound: {tmpl_name}")

    html = tmpl.render(
        dict(
            feed=feed,
            entries=entries,
            links=links,
        )
    )
    output_file = dst_dir.joinpath(output_name)
    output_file.write_text(html, encoding="utf-8")

def render_atom_rss(
    tmpl_name: str,
    feed: Feed,
    entries: list[FeedEntry],
) -> str:
    tmpl = jinja_env.get_template(tmpl_name)
    if not tmpl.filename:
        raise ValueError(f"NotFound: {tmpl_name}")

    while True:
        rss = tmpl.render(
            dict(
                feed_uuid=hashlib.sha1(feed.feed_link.encode()).hexdigest(),
                feed=feed,
                entries=entries,
            )
        )
        if len(rss) <= FeedSizeLimit:
            return rss
        else:
            entries = entries[:len(entries)//2]


def check_before_publish(conn: sqlite3.Connection) -> Result[str, str]:
    feed = get_feed_by_id(PublicBucketID, conn).unwrap()
    if feed.feed_link == "" or feed.title == "" or feed.author_name == "":
        return Err(
            """
第一次发布需要使用 'ago publish -g' 命令录入作者名称等信息。
另外也可使用 'ago publish --set-author' 等命令。
如有疑问可使用 'ago publish -h' 获取帮助。
"""
        )
    return OK


def publish_show_info(conn: sqlite3.Connection) -> None:
    feed = get_feed_by_id(PublicBucketID, conn).unwrap()
    print("通过 HTML/RSS 对外发布微博客时，对访客显示以下信息：\n")
    print(f"[Title] {feed.title}")
    print(f"[RSS Link] {feed.feed_link}")
    print(f"[Author] {feed.author_name}")
    print(f"[Website] {feed.website}")
    print(f"\n其中 Link 是指 RSS feed 本身的链接, " "Website 可以填写任意网址，通常是你的个人网站或博客的网址。")
