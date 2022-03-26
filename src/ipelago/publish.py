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

from ipelago.db import get_cfg, get_feed_by_id, get_public_limit
from ipelago.model import OK, RFC3339, Feed, PublicBucketID

Conn = sqlite3.Connection

default_output_folder: Final[str] = "public"


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


def copy_static_files(src_dir: Path, dst_dir: Path) -> None:
    static_files = ["simple.css", "style.css"]
    for name in static_files:
        dst = dst_dir.joinpath(name)
        if not dst.exists():
            src = src_dir.joinpath(name)
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


def publish_html(conn: Conn, limit: int, output: str, force: bool) -> None:
    dst_dir = Path(output) if output else Path(default_output_folder)
    dst_dir = dst_dir.resolve()
    print(f"\nOutput to {dst_dir}")
    ok = ensure_dst_dir(dst_dir, force)
    if not ok:
        return

    feed = get_feed_by_id(PublicBucketID, conn).unwrap()
    feed.updated = arrow.now().format(RFC3339)[:10]

    n = conn.execute(stmt.Count_public).fetchone()[0]
    if n <= limit:
        tmpl_name = "index.html"
        links = new_links()
        links["index_page"] = Link(name="", href="https://github.com/ahui2016/pypelago")
        render_write_page(
            conn, dst_dir, tmpl_name, "index.html", feed, links, "", limit
        )

    src_dir = Path(__file__).parent.joinpath("templates")
    copy_static_files(src_dir, dst_dir)
    print("OK.\n")


def render_write_page(
    conn: Conn,
    dst_dir: Path,
    tmpl_name: str,
    output_name: str,
    feed: Feed,
    links: Links,
    cursor: str,
    limit: int,
) -> None:
    entries = get_public_limit(cursor, limit, conn)
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


def check_before_publish(conn: sqlite3.Connection) -> Result[str, str]:
    feed = get_feed_by_id(PublicBucketID, conn).unwrap()
    if feed.link == "" or feed.title == "" or feed.author_name == "":
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
    print("通过 HTML/RSS 对外发布微博客时，对访客显示以下信息：")
    print(f"[Title] {feed.title}")
    print(f"[RSS Link] {feed.link}")
    print(f"[Author] {feed.author_name}")
