#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / 'kangaroo' / 'dashboard' / 'p2pk_monitor.db'

conn = sqlite3.connect(str(DB_PATH))
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS p2pk_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL,
    balance REAL,
    txid TEXT,
    pubkey TEXT,
    detected_at TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)''')
conn.commit()
conn.close()

print('✅ Banco de dados P2PK inicializado')
