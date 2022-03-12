Create_tables = """
CREATE TABLE IF NOT EXISTS metadata
(
  name    text   NOT NULL UNIQUE,
  value   text   NOT NULL
);
"""

Insert_metadata = "INSERT INTO metadata (name, value) VALUES (?, ?);"
Get_metadata = "SELECT value FROM metadata WHERE name=?;"
Update_metadata = "UPDATE metadata SET value=:value WHERE name=:name;"
