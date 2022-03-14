Create_tables = """
CREATE TABLE IF NOT EXISTS metadata
(
    name    text   NOT NULL UNIQUE,
    value   text   NOT NULL
);

CREATE TABLE IF NOT EXISTS feed
(
    id            text   NOT NULL UNIQUE,
    link          text   NOT NULL UNIQUE,
    title         text   NOT NULL,
    author_name   text   NOT NULL,
    updated       text   NOT NULL,
    notes         text   NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feed_updated ON feed(updated);

CREATE TABLE IF NOT EXISTS entry
(
    id          text   NOT NULL UNIQUE,
    title       text   NOT NULL,
    content     text   NOT NULL,
    link        text   NOT NULL,
    published   text   NOT NULL,
    feed_id     REFERENCES feed(id) ON DELETE CASCADE,
    feed_name   text   NOT NULL,
    bucket      text   NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entry_published ON entry(published);
CREATE INDEX IF NOT EXISTS idx_entry_bucket ON entry(bucket);
CREATE INDEX IF NOT EXISTS idx_entry_bucket_published ON entry(bucket, published);
"""

Insert_metadata = "INSERT INTO metadata (name, value) VALUES (?, ?);"
Get_metadata = "SELECT value FROM metadata WHERE name=?;"
Update_metadata = "UPDATE metadata SET value=:value WHERE name=:name;"

Get_feed_by_id = """SELECT * FROM feed WHERE id=?;"""

Insert_feed = """
INSERT INTO feed (
    id, link, title, author_name, updated, notes
) VALUES (
    :id, :link, :title, :author_name, :updated, :notes
);
"""

Insert_my_feed = """
INSERT INTO feed (
    id, link, title, author_name, updated, notes
) VALUES (:id, :link, :title, '', '', '');
"""

Insert_entry = """
INSERT INTO entry (
    id, title, content, link, published, feed_id, feed_name, bucket
) VALUES (
    :id, :title, :content, :link, :published, :feed_id, :feed_name, :bucket
)
"""

Insert_my_entry = """
INSERT INTO entry (
    id, title, content, link, published, feed_id, feed_name, bucket
) VALUES (
    :id, '', :content, '', :published, :feed_id, '', :bucket
)
"""

Get_my_first_entry = """
SELECT * FROM entry WHERE bucket='Public' or bucket='Private'
ORDER BY published DESC LIMIT 1;
"""

Get_my_next_entry = """
SELECT * FROM entry
WHERE (bucket='Public' or bucket='Private') and published < :published
ORDER BY published DESC LIMIT 1;
"""

Get_by_date = """
SELECT * FROM entry
WHERE bucket=:bucket and published LIKE :published
ORDER BY published DESC LIMIT :limit;
"""
