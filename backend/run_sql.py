import mysql.connector
from local_config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, MYSQL_PORT

conn = mysql.connector.connect(
    host=MYSQL_HOST, user=MYSQL_USER,
    password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
    port=MYSQL_PORT
)
cursor = conn.cursor()

with open('pickem_database.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

# แยก statement และรันทีละอัน
for statement in sql.split(';'):
    statement = statement.strip()
    if statement:
        try:
            cursor.execute(statement)
            print(f"✅ OK: {statement[:50]}...")
        except Exception as e:
            print(f"⚠️  {e}: {statement[:50]}...")

conn.commit()
cursor.close()
conn.close()
print("Done!")