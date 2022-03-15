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

from ipelago.db import get_cfg, get_feed_by_id, get_public_limit
from ipelago.model import PublicBucketID

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


def publish_html(conn: sqlite3.Connection) -> None:
    cfg = get_cfg(conn).unwrap()
    entries = get_public_limit("", cfg["web_page_n"], conn)
    feed = get_feed_by_id(PublicBucketID, conn).unwrap()

    filename = "index.html"
    index_tmpl = j_env.get_template(filename)
    if not index_tmpl.filename:
        raise ValueError(f"NotFound: {filename}")

    print(index_tmpl.filename)
    index_html = index_tmpl.render(
        dict(
            feed=feed,
            entries=entries,
        )
    )
    Path(output_folder).mkdir(exist_ok=True)
    output_file = Path(output_folder).joinpath(filename)
    output_file.write_text(index_html, encoding="utf-8")
    copy_static_files(index_tmpl)
