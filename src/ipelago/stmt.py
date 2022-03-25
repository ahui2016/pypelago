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
    notes         text   NOT NULL,
    parser        text   NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feed_updated ON feed(updated);

CREATE TABLE IF NOT EXISTS entry
(
    id          text   PRIMARY KEY COLLATE NOCASE,
    content     text   NOT NULL,
    link        text   NOT NULL,
    published   text   NOT NULL,
    feed_id     REFERENCES feed(id) COLLATE NOCASE,
    feed_name   text   NOT NULL,
    bucket      text   NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entry_feed_id ON entry(feed_id);
CREATE INDEX IF NOT EXISTS idx_entry_published ON entry(published);
CREATE INDEX IF NOT EXISTS idx_entry_bucket ON entry(bucket);
CREATE INDEX IF NOT EXISTS idx_entry_bucket_published ON entry(bucket, published);

CREATE TABLE IF NOT EXISTS tag
(
    name       text       NOT NULL  COLLATE NOCASE,
    entry_id   REFERENCES entry(id) COLLATE NOCASE
);

CREATE INDEX IF NOT EXISTS idx_tag_name ON tag(name);
CREATE INDEX IF NOT EXISTS idx_tag_entry_id ON tag(entry_id);
"""

Insert_metadata: Final[str] = "INSERT INTO metadata (name, value) VALUES (?, ?);"
Get_metadata: Final[str] = "SELECT value FROM metadata WHERE name=?;"
Update_metadata: Final[str] = "UPDATE metadata SET value=:value WHERE name=:name;"

Insert_tag: Final[
    str
] = """
    INSERT INTO tag (name, entry_id) VALUES (:name, :entry_id);
    """

Get_by_tag: Final[
    str
] = """
    SELECT id, content, link, published, feed_id, feed_name, bucket
    FROM tag, entry
    WHERE tag.name=:name and tag.entry_id=entry.id
    ORDER BY entry.published DESC LIMIT :limit;
    """
Count_by_tag: Final[
    str
] = """
    SELECT count(*) FROM tag, entry
    WHERE tag.name=:name and tag.entry_id=entry.id
    ORDER BY entry.published;
    """

Search_entry_content: Final[
    str
] = """
    SELECT * FROM entry WHERE content LIKE :content
    ORDER BY published DESC LIMIT :limit;
    """
Count_entry_content: Final[
    str
] = """
    SELECT count(*) FROM entry WHERE content LIKE :content
    ORDER BY published;
    """

Get_by_tag_bucket: Final[
    str
] = """
    SELECT id, content, link, published, feed_id, feed_name, bucket
    FROM tag, entry
    WHERE bucket=:bucket and tag.name=:name and tag.entry_id=entry.id
    ORDER BY entry.published DESC LIMIT :limit;
    """
Count_by_tag_bucket: Final[
    str
] = """
    SELECT count(*) FROM tag, entry
    WHERE bucket=:bucket and tag.name=:name and tag.entry_id=entry.id
    ORDER BY entry.published;
    """

Search_entry_content_bucket: Final[
    str
] = """
    SELECT * FROM entry WHERE bucket=:bucket and content LIKE :content
    ORDER BY published DESC LIMIT :limit;
    """
Count_entry_content_bucket: Final[
    str
] = """
    SELECT count(*) FROM entry WHERE bucket=:bucket and content LIKE :content
    ORDER BY published;
    """

Get_all_tags: Final[
    str
] = """
    SELECT name FROM tag GROUP BY name;
    """
Get_one_tag: Final[
    str
] = """
    SELECT name FROM tag WHERE name LIKE ?
    GROUP BY name;
    """

Get_feed_by_id: Final[
    str
] = """
    SELECT * FROM feed WHERE id=?;
    """

Delete_feed: Final[
    str
] = """
    DELETE FROM feed WHERE id=?;
    """

Update_feed_id: Final[
    str
] = """
    UPDATE feed SET id=:newid WHERE id=:oldid;
    """

Update_entry_feed_id: Final[
    str
] = """
    UPDATE entry SET feed_id=:newid WHERE feed_id=:oldid;
    """
Update_feed_title: Final[
    str
] = """
    UPDATE feed SET title=:title WHERE id=:id;
    """

Update_entry_feed_name: Final[
    str
] = """
    UPDATE entry SET feed_name=:feed_name WHERE feed_id=:feed_id;
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
        id, link, title, author_name, updated, notes, parser
    ) VALUES (
        :id, :link, :title, :author_name, :updated, :notes, :parser
    );
    """

Update_feed_parser: Final[
    str
] = """
    UPDATE feed SET parser=:parser WHERE id=:id;
    """

Update_feed_updated: Final[
    str
] = """
    UPDATE feed SET updated=:updated WHERE id=:id;
    """

Insert_my_feed: Final[
    str
] = """
    INSERT INTO feed (
        id, link, title, author_name, updated, notes, parser
    ) VALUES (:id, :link, :title, '', '', '', '');
    """

Update_my_feed_info: Final[
    str
] = """
    UPDATE feed SET link=:link, title=:title, author_name=:author
    WHERE id='Public';
    """
Update_my_feed_link: Final[
    str
] = """
    UPDATE feed SET link=:link WHERE id='Public';
    """
Update_my_feed_title: Final[
    str
] = """
    UPDATE feed SET title=:title WHERE id='Public';
    """
Update_my_feed_author: Final[
    str
] = """
    UPDATE feed SET author_name=:author WHERE id='Public';
    """

Get_subs_list: Final[
    str
] = """
    SELECT * FROM feed WHERE id<>'Public' and id<>'Private' and id<>'Fav'
    ORDER BY id;
    """

Insert_entry: Final[
    str
] = """
    INSERT INTO entry (
        id, content, link, published, feed_id, feed_name, bucket
    ) VALUES (
        :id, :content, :link, :published, :feed_id, :feed_name, :bucket
    );
    """

Insert_my_entry: Final[
    str
] = """
    INSERT INTO entry (
        id, content, link, published, feed_id, feed_name, bucket
    ) VALUES (
        :id, :content, '', :published, :feed_id, '', :bucket
    );
    """

# first 是指按照消息发布时间最新的信息。
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

My_cursor_goto: Final[
    str
] = """
    SELECT * FROM entry
    WHERE (bucket='Public' or bucket='Private') and published > :published
    ORDER BY published LIMIT 1;
    """
News_cursor_goto: Final[
    str
] = """
    SELECT * FROM entry
    WHERE bucket='News' and published > :published
    ORDER BY published LIMIT 1;
    """

Get_entries_limit: Final[
    str
] = """
    SELECT * FROM entry WHERE bucket=:bucket
    ORDER BY published DESC LIMIT :limit;
    """

Get_news_next_entry: Final[
    str
] = """
    SELECT * FROM entry
    WHERE bucket='News' and published < :published
    ORDER BY published DESC LIMIT 1;
    """

Get_entry_by_id: Final[
    str
] = """
    SELECT * FROM entry WHERE id=?;
    """

Get_entry_by_id_prefix: Final[
    str
] = """
    SELECT * FROM entry WHERE id LIKE ?;
    """
Get_entry_in_bucket: Final[
    str
] = """
    SELECT * FROM entry WHERE bucket=:bucket and id LIKE :id;
    """

Count_public: Final[
    str
] = """
    SELECT count(*) FROM entry WHERE bucket='Public';
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

Get_by_date_my_buckets: Final[
    str
] = """
    SELECT * FROM entry
    WHERE (bucket='Public' or bucket='Private') and published LIKE :published
    ORDER BY published DESC LIMIT :limit;
    """

Count_by_date: Final[
    str
] = """
    SELECT count(*) FROM entry
    WHERE bucket=:bucket and published LIKE :published
    ORDER BY published DESC;
    """

Move_entry_to_fav: Final[
    str
] = """
    UPDATE entry SET
    id=:newid, feed_id='Fav', bucket='Fav'
    WHERE id=:oldid;
    """

Update_entry_bucket: Final[
    str
] = """
    UPDATE entry SET bucket=:bucket WHERE id=:id;
    """

Count_tag_by_entry_id: Final[
    str
] = """
    SELECT count(*) FROM tag WHERE entry_id=?;
    """

Delete_tag_entry: Final[
    str
] = """
    DELETE FROM tag WHERE entry_id=?;
    """

Delete_entry: Final[
    str
] = """
    DELETE FROM entry WHERE id=?;
    """

Delete_entries: Final[
    str
] = """
    DELETE FROM entry WHERE feed_id=?;
    """

Get_news_by_feed: Final[
    str
] = """
    SELECT * FROM entry WHERE feed_id=:feed_id
    ORDER BY published DESC LIMIT :limit;
    """
