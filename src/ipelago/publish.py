from pathlib import Path
import shutil
import sqlite3
from typing import Final, cast
from jinja2 import (
    Template,
    Environment,
    FileSystemLoader,
    PackageLoader,
    select_autoescape,
)
from result import Result, Err, Ok

from ipelago.db import get_cfg, get_feed_by_id, get_public_limit
from ipelago.model import OK, PublicBucketID

output_folder: Final[str] = "public"

try:
    loader = PackageLoader("ipelago")
except ValueError:
    loader = FileSystemLoader("src/ipelago/templates")

j_env = Environment(loader=loader, autoescape=select_autoescape())


def copy_static_files(tmpl: Template) -> None:
    static_files = ["simple.css", "style.css"]
    for filename in static_files:
        dst = Path(output_folder).joinpath(filename)
        if not dst.exists():
            tmpl_path = cast(str, tmpl.filename)
            src = Path(tmpl_path).parent.joinpath(filename)
            shutil.copyfile(src, dst)


def publish_html(conn: sqlite3.Connection, force: bool) -> None:
    if not force:
        print("Error: require '-force' to publish.")
        print("请使用 '-force' 参数确认覆盖当前目录的 public 文件夹的内容。")
        return

    cfg = get_cfg(conn).unwrap()
    entries = get_public_limit("", cfg["web_page_n"], conn)
    feed = get_feed_by_id(PublicBucketID, conn).unwrap()

    filename = "index.html"
    index_tmpl = j_env.get_template(filename)
    if not index_tmpl.filename:
        raise ValueError(f"NotFound: {filename}")

    index_html = index_tmpl.render(
        dict(
            feed=feed,
            entries=entries,
        )
    )
    Path(output_folder).mkdir(exist_ok=True)
    print(f"[output] {Path(output_folder).resolve()}")
    output_file = Path(output_folder).joinpath(filename)
    output_file.write_text(index_html, encoding="utf-8")
    copy_static_files(index_tmpl)


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
