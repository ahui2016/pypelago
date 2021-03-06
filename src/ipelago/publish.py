import hashlib
from pathlib import Path
import shutil
import sqlite3
from typing import Final, TypedDict
import jinja2
from result import Result, Err
from ipelago import stmt

from ipelago.db import get_feed_by_id, get_public_limit, get_recent_entries
from ipelago.model import (
    OK,
    Bucket,
    Feed,
    FeedEntry,
    FeedSizeLimit,
    PublicBucketID,
)

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
    loader = jinja2.PackageLoader("ipelago")
except ValueError:
    loader = jinja2.FileSystemLoader("src/ipelago/templates")

default_env = jinja2.Environment(loader=loader, autoescape=jinja2.select_autoescape())


def get_fs_env(tmpl_folder: str) -> jinja2.Environment:
    loader = jinja2.FileSystemLoader(tmpl_folder)
    return jinja2.Environment(loader=loader, autoescape=jinja2.select_autoescape())


def get_jinja_env(tmpl_folder: str) -> jinja2.Environment:
    if not tmpl_folder:
        return default_env
    else:
        return get_fs_env(tmpl_folder)


def get_src_dir(tmpl_folder: str) -> Path:
    tmpl = get_jinja_env(tmpl_folder).get_template(index_html)
    if not tmpl.filename:
        raise ValueError(f"NotFound: {index_html}")
    return Path(tmpl.filename).parent


def copy_static_files(tmpl_folder: str, dst_dir: Path) -> None:
    static_files = get_src_dir(tmpl_folder).glob("*.css")
    for src in static_files:
        dst = dst_dir.joinpath(src.name)
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


def print_tmpl_folder(tmpl_folder: str) -> None:
    try:
        src_dir = get_src_dir(tmpl_folder)
    except jinja2.exceptions.TemplateNotFound:
        src_dir = Path(tmpl_folder)
    print(f"\n[Templates] {src_dir.resolve()}")


def publish_html_rss(
    conn: Conn, limit: int, output: str, tmpl_folder: str, force: bool
) -> None:
    print_tmpl_folder(tmpl_folder)
    dst_dir = Path(output) if output else Path(default_output_folder)
    dst_dir = dst_dir.resolve()
    print(f"[Output] {dst_dir}")
    ok = ensure_dst_dir(dst_dir, force)
    if not ok:
        return

    feed = get_feed_by_id(PublicBucketID, conn).unwrap()
    publish_html(conn, feed, limit, tmpl_folder, dst_dir)
    publish_rss(conn, feed, tmpl_folder, dst_dir)


def publish_rss(conn: Conn, feed: Feed, tmpl_folder: str, dst_dir: Path) -> None:
    entries = get_recent_entries(Bucket.Public.name, atom_entries_limit, conn)
    rss = render_atom_rss(tmpl_folder, atom_xml, feed, entries)
    output_file = dst_dir.joinpath(atom_xml)
    output_file.write_text(rss, encoding="utf-8")


def publish_html(
    conn: Conn, feed: Feed, limit: int, tmpl_folder: str, dst_dir: Path
) -> None:
    total = conn.execute(stmt.Count_by_feed_id, (PublicBucketID,)).fetchone()[0]
    if total <= limit:
        entries = get_public_limit("", limit, conn)
        render_index_page(dst_dir, tmpl_folder, feed, entries)
    else:
        render_all_pages(dst_dir, tmpl_folder, feed, total, limit, conn)

    copy_static_files(tmpl_folder, dst_dir)
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
    dst_dir: Path, tmpl_folder: str, feed: Feed, total: int, limit: int, conn: Conn
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
        render_write_page(
            dst_dir, tmpl_folder, index_html, names["output"], feed, links, entries
        )
        if names["output"] == index_html:
            break


def render_index_page(
    dst_dir: Path, tmpl_folder: str, feed: Feed, entries: list[FeedEntry]
) -> None:
    links = new_links()
    links["index_page"] = Link(name="", href=feed.website)
    links["footer"] = Link(name=feed.website, href=feed.website)
    render_write_page(
        dst_dir, tmpl_folder, index_html, index_html, feed, links, entries
    )


def render_write_page(
    dst_dir: Path,
    tmpl_folder: str,
    tmpl_name: str,
    output_name: str,
    feed: Feed,
    links: Links,
    entries: list[FeedEntry],
) -> None:
    tmpl = get_jinja_env(tmpl_folder).get_template(tmpl_name)
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
    tmpl_folder: str,
    tmpl_name: str,
    feed: Feed,
    entries: list[FeedEntry],
) -> str:
    tmpl = get_jinja_env(tmpl_folder).get_template(tmpl_name)
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
            entries = entries[: len(entries) // 2]


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
