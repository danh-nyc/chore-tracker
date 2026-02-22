import sqlite3

with sqlite3.connect("choretracker.db") as conn:
    with open("schema.sql") as f:
        conn.executescript(f.read())

print("Database initialized.")
