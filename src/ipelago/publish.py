from pathlib import Path
import shutil
import sqlite3
from typing import Final, cast
import arrow
from jinja2 import (
    Template,
    Environment,
    FileSystemLoader,
    PackageLoader,
    select_autoescape,
)
from result import Result, Err, Ok

from ipelago.db import get_cfg, get_feed_by_id, get_public_limit
from ipelago.model import OK, RFC3339, PublicBucketID

output_folder: Final[str] = "public"

try:
    loader = PackageLoader("ipelago")
except ValueError:
    loader = FileSystemLoader("src/ipelago/templates")

j_env = Environment(loader=loader, autoescape=select_autoescape())


def copy_static_files(tmpl: Template, folder:Path) -> None:
    static_files = ["simple.css", "style.css"]
    for filename in static_files:
        dst = folder.joinpath(filename)
        if not dst.exists():
            tmpl_path = cast(str, tmpl.filename)
            src = Path(tmpl_path).parent.joinpath(filename)
            shutil.copyfile(src, dst)


def publish_html(conn: sqlite3.Connection, output:str, force: bool) -> None:
    out = Path(output) if output else Path(output_folder)
    print(f'\nOutput to {out.resolve()}')

    if not out.exists():
        print(f'Create folder {out.resolve()}')
        out.mkdir(parents=True)
    else:
        if not force:
            print("Error: require '-force' to overwrite.")
            print("请使用 '-force' 参数确认覆盖 output 文件夹的内容。\n")
            return

    cfg = get_cfg(conn).unwrap()
    entries = get_public_limit("", cfg["web_page_n"], conn)
    feed = get_feed_by_id(PublicBucketID, conn).unwrap()
    feed.updated = arrow.now().format(RFC3339)[:10]

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
    output_file = out.joinpath(filename)
    output_file.write_text(index_html, encoding="utf-8")
    copy_static_files(index_tmpl, out)
    print("OK.\n")


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
