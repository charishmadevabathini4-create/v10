import sqlite3
import os

DB_PATH = "Preliminary_data.db"

print("Database path:")
print(os.path.abspath(DB_PATH))

if not os.path.exists(DB_PATH):
    print("\nERROR: Database file does not exist.")
    exit()

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

print("\nDATABASE TABLES")
print("=" * 50)

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
""")

tables = cursor.fetchall()

if not tables:
    print("NO TABLES FOUND")
else:
    for (table_name,) in tables:

        print(f"\nTABLE: {table_name}")

        cursor.execute(
            f'PRAGMA table_info("{table_name}")'
        )

        columns = cursor.fetchall()

        for column in columns:
            print(
                f"  {column[1]} "
                f"({column[2]})"
            )

        cursor.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        )

        count = cursor.fetchone()[0]

        print(f"  Records: {count}")

connection.close()