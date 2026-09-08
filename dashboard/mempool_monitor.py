#!/usr/bin/env python3
"""
Monitor de Mempool para Snipe de Puzzles P2PK
Monitora endereços P2PK e alerta quando pubkey é exposta em transação
"""

import json
import time
import requests
import sqlite3
from datetime import datetime
from pathlib import Path

# Configuração
DB_PATH = Path.home() / 'kangaroo' / 'dashboard' / 'solutions.db'
P2PK_DB_PATH = Path.home() / 'kangaroo' / 'dashboard' / 'p2pk_monitor.db'

# Endereços P2PK para monitorar (top 20 por saldo)
P2PK_ADDRESSES = [
    {'address': '1PTYXwamXXgQoAhDbmUf98rY2Pg1pYXhin', 'balance': 3233.17, 'puzzle': 'P2PK-3233'},
    {'address': '16mEzobs4wQPuAMq1C8QSQafcDHvzczVcs', 'balance': 875.00, 'puzzle': 'P2PK-875'},
    {'address': '1P2ZAuW9nUrFfwgVjfL2SA9sPXSruCfzp8', 'balance': 800.00, 'puzzle': 'P2PK-800'},
    {'address': '15UkFYLMs5nytwiKWqGgkkVo1fjLFAeJhs', 'balance': 750.00, 'puzzle': 'P2PK-750'},
    {'address': '15BKWJjL5YWXtaP449WAYqVYZQE1szicTn', 'balance': 550.00, 'puzzle': 'P2PK-550'},
    {'address': '1PxeCXMZBuXHt4CqWWEQ7Kwgdyob9P955L', 'balance': 500.00, 'puzzle': 'P2PK-500'},
    {'address': '19NBWfZniu18DbmneRcaGU3sZCrCvrZrRR', 'balance': 400.00, 'puzzle': 'P2PK-400'},
    {'address': '1JSxDnLYD4XKTQ73N7in2M9XRovw5LANiu', 'balance': 350.04, 'puzzle': 'P2PK-350'},
    {'address': '1JqPFnGPhHhy54zJKmC1MPiczzgFjCmzE9', 'balance': 340.00, 'puzzle': 'P2PK-340'},
    {'address': '1GkMg44pUuDp6DPWNCsjd9Do5gt8cELpUA', 'balance': 300.00, 'puzzle': 'P2PK-300'},
]

def init_p2pk_db():
    """Inicializar banco de dados do monitor P2PK"""
    conn = sqlite3.connect(str(P2PK_DB_PATH))
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

def check_mempool(address):
    """Verificar mempool para um endereço"""
    try:
        # Usar mempool.space API
        url = f"https://mempool.space/api/address/{address}/txs/mempool"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            txs = response.json()
            if txs:
                return txs[0]  # Retorna primeira transação não confirmada
        return None
    except Exception as e:
        print(f"Erro ao verificar {address}: {e}")
        return None

def extract_pubkey_from_tx(tx, address):
    """Extrair public key de uma transação"""
    try:
        for vin in tx.get('vin', []):
            if vin.get('prevout', {}).get('scriptpubkey_address') == address:
                # Script sig contém a pubkey
                script_sig = vin.get('scriptsig', '')
                if script_sig:
                    # Pubkey está no script sig (formato P2PK)
                    # Último campo antes do OP_CHECKSIG
                    parts = script_sig.split(' ')
                    for part in parts:
                        if len(part) >= 66:  # Pubkey comprimida ou não
                            return part
        return None
    except Exception as e:
        print(f"Erro ao extrair pubkey: {e}")
        return None

def save_alert(address, balance, txid, pubkey):
    """Salvar alerta no banco de dados"""
    conn = sqlite3.connect(str(P2PK_DB_PATH))
    c = conn.cursor()
    c.execute('''INSERT INTO p2pk_alerts (address, balance, txid, pubkey, detected_at)
                 VALUES (?, ?, ?, ?, ?)''',
              (address, balance, txid, pubkey, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_pending_alerts():
    """Obter alertas pendentes"""
    conn = sqlite3.connect(str(P2PK_DB_PATH))
    c = conn.cursor()
    c.execute('SELECT * FROM p2pk_alerts WHERE status = "pending" ORDER BY created_at DESC')
    columns = [desc[0] for desc in c.description]
    results = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return results

def monitor_loop():
    """Loop principal de monitoramento"""
    print("🔍 Iniciando monitor de mempool P2PK...")
    print(f"📊 Monitorando {len(P2PK_ADDRESSES)} endereços")
    print(f"💰 Saldo total: {sum(a['balance'] for a in P2PK_ADDRESSES):.2f} BTC")
    print()
    
    while True:
        for addr_info in P2PK_ADDRESSES:
            address = addr_info['address']
            balance = addr_info['balance']
            
            # Verificar mempool
            tx = check_mempool(address)
            
            if tx:
                txid = tx.get('txid', 'unknown')
                print(f"🚨 ALERTA! Transação detectada em {address}")
                print(f"   Saldo: {balance} BTC")
                print(f"   TXID: {txid}")
                
                # Extrair pubkey
                pubkey = extract_pubkey_from_tx(tx, address)
                
                if pubkey:
                    print(f"   Pubkey: {pubkey[:30]}...")
                    save_alert(address, balance, txid, pubkey)
                    print(f"   ✅ Alerta salvo no banco de dados")
                    
                    # Aqui poderia disparar Kangaroo automaticamente
                    print(f"   🔫 Pronto para rodar Kangaroo!")
                else:
                    print(f"   ️  Não foi possível extrair pubkey")
                
                print()
        
        # Aguardar antes de próxima verificação
        time.sleep(5)  # Verificar a cada 5 segundos

def api_get_alerts():
    """API para obter alertas (usado pelo dashboard)"""
    alerts = get_pending_alerts()
    return json.dumps(alerts, default=str)

if __name__ == '__main__':
    init_p2pk_db()
    monitor_loop()
