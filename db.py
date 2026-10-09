import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Production (Wasmer Postgres)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # Local dev (SQLite)
    engine = create_engine("sqlite:///" + os.path.join(os.path.dirname(__file__), "apex.db"), pool_pre_ping=True)

def query(sql, params=None):
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).fetchall()

def execute(sql, params=None):
    with engine.begin() as conn:
        return conn.execute(text(sql), params or {})

def init_db():
    with engine.begin() as conn:
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

print("[+] db.py ready")
