import os
from pathlib import Path
import shutil
import sqlite3
from typing import Final
from xml.dom import NotFoundErr
from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape

from ipelago.db import get_cfg, get_feed_by_id, get_public_limit
from ipelago.model import PublicBucketID

output_folder: Final[str] = "public"

try:
    loader = PackageLoader("ipelago")
except ValueError:
    loader = FileSystemLoader("src/ipelago/templates")

j_env = Environment(loader=loader, autoescape=select_autoescape())


def publish_html(conn: sqlite3.Connection) -> None:
    cfg = get_cfg(conn).unwrap()
    entries = get_public_limit("", cfg["web_page_n"], conn)
    feed = get_feed_by_id(PublicBucketID, conn).unwrap()

    filename = "index.html"
    index_tmpl = j_env.get_template(filename)
    if not index_tmpl.filename:
        raise ValueError(f'NotFound: {filename}')

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

    style_filename = "style.css"
    style_file_dst = Path(output_folder).joinpath(style_filename)
    if not style_file_dst.exists():
        style_file_src = Path(index_tmpl.filename).parent.joinpath(style_filename)
        shutil.copyfile(style_file_src, style_file_dst)
