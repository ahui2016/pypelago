from typing import Final


Create_tables: Final = """
CREATE TABLE IF NOT EXISTS metadata
(
    name    text   NOT NULL UNIQUE,
    value   text   NOT NULL
);

CREATE TABLE IF NOT EXISTS feed
(
    id            text   PRIMARY KEY COLLATE NOCASE,
    feed_link     text   NOT NULL UNIQUE,
    website       text   NOT NULL,
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_tag_entry_name_id ON tag(name, entry_id);
"""

Insert_metadata: Final = "INSERT INTO metadata (name, value) VALUES (?, ?);"
Get_metadata: Final = "SELECT value FROM metadata WHERE name=?;"
Update_metadata: Final = "UPDATE metadata SET value=:value WHERE name=:name;"

Insert_tag: Final = """
    INSERT INTO tag (name, entry_id) VALUES (:name, :entry_id);
    """

Get_by_tag: Final = """
    SELECT id, content, link, published, feed_id, feed_name, bucket
    FROM tag, entry
    WHERE tag.name=:name and tag.entry_id=entry.id
    ORDER BY entry.published DESC LIMIT :limit;
    """
Count_by_tag: Final = """
    SELECT count(*) FROM tag, entry
    WHERE tag.name=:name and tag.entry_id=entry.id
    ORDER BY entry.published;
    """

Search_entry_content: Final = """
    SELECT * FROM entry WHERE content LIKE :content
    ORDER BY published DESC LIMIT :limit;
    """
Count_entry_content: Final = """
    SELECT count(*) FROM entry WHERE content LIKE :content
    ORDER BY published;
    """

Get_by_tag_bucket: Final = """
    SELECT id, content, link, published, feed_id, feed_name, bucket
    FROM tag, entry
    WHERE bucket=:bucket and tag.name=:name and tag.entry_id=entry.id
    ORDER BY entry.published DESC LIMIT :limit;
    """
Count_by_tag_bucket: Final = """
    SELECT count(*) FROM tag, entry
    WHERE bucket=:bucket and tag.name=:name and tag.entry_id=entry.id
    ORDER BY entry.published;
    """

Search_entry_content_bucket: Final = """
    SELECT * FROM entry WHERE bucket=:bucket and content LIKE :content
    ORDER BY published DESC LIMIT :limit;
    """
Count_entry_content_bucket: Final = """
    SELECT count(*) FROM entry WHERE bucket=:bucket and content LIKE :content
    ORDER BY published;
    """

Get_all_tags: Final = """
    SELECT name FROM tag GROUP BY name;
    """
Get_one_tag: Final = """
    SELECT name FROM tag WHERE name LIKE ?
    GROUP BY name;
    """

Get_feed_by_id: Final = """
    SELECT * FROM feed WHERE id=?;
    """

Delete_feed: Final = """
    DELETE FROM feed WHERE id=?;
    """

Update_feed_id: Final = """
    UPDATE feed SET id=:newid WHERE id=:oldid;
    """

Update_entry_feed_id: Final = """
    UPDATE entry SET feed_id=:newid WHERE feed_id=:oldid;
    """
Update_feed_title: Final = """
    UPDATE feed SET title=:title WHERE id=:id;
    """

Update_entry_feed_name: Final = """
    UPDATE entry SET feed_name=:feed_name WHERE feed_id=:feed_id;
    """

Get_feed_id: Final = """
    SELECT id FROM feed WHERE id=?;
    """

Get_feed_link: Final = """
    SELECT feed_link FROM feed WHERE feed_link=?;
    """

Insert_feed: Final = """
    INSERT INTO feed (
        id, feed_link, website, title, author_name, updated, notes, parser
    ) VALUES (
        :id, :feed_link, :website, :title, :author_name, :updated, :notes, :parser
    );
    """

Insert_my_feed: Final = """
    INSERT INTO feed (
        id, feed_link, website, title, author_name, updated, notes, parser
    ) VALUES (:id, :feed_link, "", :title, '', '', '', '');
    """

Update_feed_parser: Final = """
    UPDATE feed SET parser=:parser WHERE id=:id;
    """

Update_feed_updated: Final = """
    UPDATE feed SET updated=:updated WHERE id=:id;
    """

Update_my_feed_info: Final = """
    UPDATE feed SET feed_link=:feed_link, website=:website, title=:title, author_name=:author
    WHERE id='Public';
    """
Update_my_feed_link: Final = """
    UPDATE feed SET feed_link=? WHERE id='Public';
    """
Update_my_feed_website: Final = """
    UPDATE feed SET website=? WHERE id='Public';
    """
Update_my_feed_title: Final = """
    UPDATE feed SET title=? WHERE id='Public';
    """
Update_my_feed_author: Final = """
    UPDATE feed SET author_name=? WHERE id='Public';
    """

Get_subs_list: Final = """
    SELECT * FROM feed WHERE id<>'Public' and id<>'Private' and id<>'Fav'
    ORDER BY id;
    """
Get_feeds_by_title: Final = """
    SELECT * FROM feed WHERE id<>'Public' and id<>'Private' and id<>'Fav'
    and title LIKE ? ORDER BY id;
    """

Insert_entry: Final = """
    INSERT INTO entry (
        id, content, link, published, feed_id, feed_name, bucket
    ) VALUES (
        :id, :content, :link, :published, :feed_id, :feed_name, :bucket
    );
    """

Insert_my_entry: Final = """
    INSERT INTO entry (
        id, content, link, published, feed_id, feed_name, bucket
    ) VALUES (
        :id, :content, '', :published, :feed_id, '', :bucket
    );
    """

# first ????????????????????????????????????????????????
Get_my_first_entry: Final = """
    SELECT * FROM entry WHERE bucket='Public' or bucket='Private'
    ORDER BY published DESC LIMIT 1;
    """

Get_my_next_entry: Final = """
    SELECT * FROM entry
    WHERE (bucket='Public' or bucket='Private') and published < :published
    ORDER BY published DESC LIMIT 1;
    """

My_cursor_goto: Final = """
    SELECT * FROM entry
    WHERE (bucket='Public' or bucket='Private') and published > :published
    ORDER BY published LIMIT 1;
    """
News_cursor_goto: Final = """
    SELECT * FROM entry
    WHERE bucket='News' and published > :published
    ORDER BY published LIMIT 1;
    """

Get_entries_limit: Final = """
    SELECT * FROM entry WHERE bucket=:bucket
    ORDER BY published DESC LIMIT :limit;
    """

Get_news_next_entry: Final = """
    SELECT * FROM entry
    WHERE bucket='News' and published < :published
    ORDER BY published DESC LIMIT 1;
    """

Get_entry_by_id: Final = """
    SELECT * FROM entry WHERE id=?;
    """

Get_entry_by_id_prefix: Final = """
    SELECT * FROM entry WHERE id LIKE ?;
    """
Get_entry_in_bucket: Final = """
    SELECT * FROM entry WHERE bucket=:bucket and id LIKE :id;
    """

Count_by_feed_id: Final = """
    SELECT count(*) FROM entry WHERE feed_id=?;
    """

Get_public_limit: Final = """
    SELECT * FROM entry
    WHERE bucket='Public' and published > :published
    ORDER BY published LIMIT :limit;
    """

Get_by_date: Final = """
    SELECT * FROM entry
    WHERE bucket=:bucket and published LIKE :published
    ORDER BY published DESC LIMIT :limit;
    """

Get_by_date_my_buckets: Final = """
    SELECT * FROM entry
    WHERE (bucket='Public' or bucket='Private') and published LIKE :published
    ORDER BY published DESC LIMIT :limit;
    """

Count_by_date: Final = """
    SELECT count(*) FROM entry
    WHERE bucket=:bucket and published LIKE :published;
    """

Count_all_entries: Final = """
    SELECT count(*) FROM entry WHERE bucket=?;
    """

Move_entry_to_fav: Final = """
    UPDATE entry SET
    id=:newid, feed_id='Fav', bucket='Fav'
    WHERE id=:oldid;
    """

Update_entry_bucket: Final = """
    UPDATE entry SET feed_id=:feed_id, bucket=:bucket WHERE id=:id;
    """

Count_tag_by_entry_id: Final = """
    SELECT count(*) FROM tag WHERE entry_id=?;
    """

Delete_tag_entry: Final = """
    DELETE FROM tag WHERE entry_id=?;
    """

Delete_entry: Final = """
    DELETE FROM entry WHERE id=?;
    """

Delete_entries: Final = """
    DELETE FROM entry WHERE feed_id=?;
    """

Get_news_by_feed: Final = """
    SELECT * FROM entry WHERE feed_id=:feed_id
    ORDER BY published DESC LIMIT :limit;
    """
