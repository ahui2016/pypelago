from typing import Final


Create_tables: Final[
    str
] = """
CREATE TABLE IF NOT EXISTS metadata
(
    name    text   NOT NULL UNIQUE,
    value   text   NOT NULL
);

CREATE TABLE IF NOT EXISTS feed
(
    id            text   PRIMARY KEY COLLATE NOCASE,
    link          text   NOT NULL UNIQUE,
    title         text   NOT NULL,
    author_name   text   NOT NULL,
    updated       text   NOT NULL,
    notes         text   NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feed_updated ON feed(updated);

CREATE TABLE IF NOT EXISTS entry
(
    id          text   PRIMARY KEY COLLATE NOCASE,
    content     text   NOT NULL,
    link        text   NOT NULL,
    published   text   NOT NULL,
    feed_id     REFERENCES feed(id) ON UPDATE CASCADE COLLATE NOCASE,
    feed_name   text   NOT NULL,
    bucket      text   NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entry_published ON entry(published);
CREATE INDEX IF NOT EXISTS idx_entry_bucket ON entry(bucket);
CREATE INDEX IF NOT EXISTS idx_entry_bucket_published ON entry(bucket, published);
"""

Insert_metadata: Final[str] = "INSERT INTO metadata (name, value) VALUES (?, ?);"
Get_metadata: Final[str] = "SELECT value FROM metadata WHERE name=?;"
Update_metadata: Final[str] = "UPDATE metadata SET value=:value WHERE name=:name;"

Get_feed_by_id: Final[
    str
] = """
    SELECT * FROM feed WHERE id=?;
    """

# Get_feed_by_id_prefix: Final[
#     str
# ] = """
#     SELECT * FROM feed WHERE id LIKE ?;
#     """

Delete_feed: Final[
    str
] = """
    DELETE FROM feed WHERE id=?;
    """

Get_feed_id: Final[
    str
] = """
SELECT id FROM feed WHERE id=?;
"""

Get_feed_link: Final[
    str
] = """
SELECT link FROM feed WHERE link=?;
"""

Insert_feed: Final[
    str
] = """
INSERT INTO feed (
    id, link, title, author_name, updated, notes
) VALUES (
    :id, :link, :title, :author_name, :updated, :notes
);
"""

Insert_my_feed: Final[
    str
] = """
INSERT INTO feed (
    id, link, title, author_name, updated, notes
) VALUES (:id, :link, :title, '', '', '');
"""

Get_subs_list: Final[
    str
] = """
SELECT * FROM feed WHERE id<>'Public' and id<>'Private'
ORDER BY id;
"""

Insert_entry: Final[
    str
] = """
INSERT INTO entry (
    id, content, link, published, feed_id, feed_name, bucket
) VALUES (
    :id, :content, :link, :published, :feed_id, :feed_name, :bucket
)
"""

Insert_my_entry: Final[
    str
] = """
INSERT INTO entry (
    id, content, link, published, feed_id, feed_name, bucket
) VALUES (
    :id, :content, '', :published, :feed_id, '', :bucket
)
"""

Get_my_first_entry: Final[
    str
] = """
SELECT * FROM entry WHERE bucket='Public' or bucket='Private'
ORDER BY published DESC LIMIT 1;
"""

Get_my_next_entry: Final[
    str
] = """
SELECT * FROM entry
WHERE (bucket='Public' or bucket='Private') and published < :published
ORDER BY published DESC LIMIT 1;
"""

Get_news_first_entry: Final[
    str
] = """
SELECT * FROM entry WHERE bucket='News'
ORDER BY published DESC LIMIT 1;
"""

Get_news_next_entry: Final[
    str
] = """
SELECT * FROM entry
WHERE bucket='News' and published < :published
ORDER BY published DESC LIMIT 1;
"""

Get_public_limit: Final[
    str
] = """
SELECT * FROM entry
WHERE bucket='Public' and published > :published
ORDER BY published LIMIT :limit;
"""

Get_by_date: Final[
    str
] = """
SELECT * FROM entry
WHERE bucket=:bucket and published LIKE :published
ORDER BY published DESC LIMIT :limit;
"""

Delete_entries: Final[
    str
] = """
    DELETE FROM entry WHERE feed_id=?;
    """
