import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")

# على Wasmer، إذا لم يوجد DATABASE_URL، استخدم SQLite في /tmp
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # بيئة للقراءة فقط؟ استخدم /tmp
    db_path = os.environ.get("SQLITE_PATH", "/tmp/apex.db")
    engine = create_engine("sqlite:///" + db_path, pool_pre_ping=True)

def query(sql, params=None):
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).fetchall()

def execute(sql, params=None):
    with engine.begin() as conn:
        return conn.execute(text(sql), params or {})

def init_db():
    with engine.begin() as conn:
        # SQL لـ PostgreSQL
        if DATABASE_URL:
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                country VARCHAR(100),
                balance FLOAT DEFAULT 0,
                bonus FLOAT DEFAULT 0,
                total_earned FLOAT DEFAULT 0,
                referral_code VARCHAR(20) UNIQUE,
                referred_by VARCHAR(20),
                wallet VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_profit TIMESTAMP,
                kyc INTEGER DEFAULT 0,
                vip INTEGER DEFAULT 0
            );
            """))
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plans (
                id SERIAL PRIMARY KEY,
                slug VARCHAR(50) UNIQUE, name VARCHAR(100),
                price FLOAT, daily_rate FLOAT, duration INTEGER,
                hashpower VARCHAR(50), algo VARCHAR(50),
                badge VARCHAR(50), tagline TEXT, features TEXT,
                active INTEGER DEFAULT 1
            );
            """))
        else:
            # SQL لـ SQLite
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT, country TEXT,
                balance REAL DEFAULT 0, bonus REAL DEFAULT 0,
                total_earned REAL DEFAULT 0,
                referral_code TEXT UNIQUE, referred_by TEXT,
                wallet TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_profit TEXT,
                kyc INTEGER DEFAULT 0, vip INTEGER DEFAULT 0
            );
            """))
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE, name TEXT,
                price REAL, daily_rate REAL, duration INTEGER,
                hashpower TEXT, algo TEXT, badge TEXT,
                tagline TEXT, features TEXT,
                active INTEGER DEFAULT 1
            );
            """))

print("[+] db.py ready (dual-mode)")
