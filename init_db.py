import sqlite3

conn = sqlite3.connect('dp.sqlite')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    summary TEXT,
    message TEXT,
    image TEXT
)''')
conn.commit()
conn.close()

print("Database initialized!")
