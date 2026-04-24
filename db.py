import psycopg2, os

def get_conn():
    try:
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    except:
        return None

def init_db():
    conn = get_conn()
    if not conn:
        return

    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS news(
        id SERIAL PRIMARY KEY,
        text TEXT,
        risk INT,
        source TEXT,
        link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    cur.close()
    conn.close()