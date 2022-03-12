Create_tables = '''
CREATE TABLE IF NOT EXISTS metadata
(
  name    text   NOT NULL UNIQUE,
  value   blob   NOT NULL 
);
'''

Insert_metadata = 'INSERT INTO metadata (name, value) VALUES (?, ?);'
Get_metadata = 'SELECT value FROM metadata WHERE name=?;'
Update_metadata = 'UPDATE metadata SET text_value=? WHERE name=?;'
