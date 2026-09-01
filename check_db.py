from backend.db import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(
        text("""
            ALTER TABLE public.inquiries
            ADD COLUMN IF NOT EXISTS reply VARCHAR(1000)
        """)
    )

print("Column added/verified")

with engine.connect() as conn:
    result = conn.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'inquiries'
            ORDER BY ordinal_position
        """)
    )

    print("\nINQUIRIES COLUMNS:")

    for row in result:
        print(row[0])