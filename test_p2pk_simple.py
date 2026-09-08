#!/usr/bin/env python3
"""
Testar ataques simples nos endereços P2PK
Usa os módulos do RakinSV diretamente
"""

import sys
import os
sys.path.insert(0, '/home/home/Bitcoin-Puzzle-AllAttacks-Analytics')

from ecc.curve import G, N, scalar_mul
from utils.address import point_to_address

# Top 5 endereços P2PK para teste
TARGETS = [
    {
        'address': '1PTYXwamXXgQoAhDbmUf98rY2Pg1pYXhin',
        'balance_btc': 3233.17,
        'pubkey_hex': '04633280c0a93b45217059013ddadab8d35b9a858336028fecdff64c6a5e068fadaf7d2b73bc22795fa160c2304703320516e1b0b20e43d613fa5975787c8287e4'
    },
    {
        'address': '16mEzobs4wQPuAMq1C8QSQafcDHvzczVcs',
        'balance_btc': 875.00,
        'pubkey_hex': '0469119c7e7d8e8b9f404d70c36cc09cae033e86d259554fd945c9263560fdc9ddea108db86e5673b3894b0bf97807ff8ac6e322791cf8d4d22f7c55a0e812720a'
    }
]

def parse_pubkey(hex_str):
    """Converter pubkey hex para ponto (x, y)"""
    if hex_str.startswith('04'):
        # Não comprimida
        x = int(hex_str[2:66], 16)
        y = int(hex_str[66:130], 16)
        return (x, y)
    elif hex_str.startswith('02') or hex_str.startswith('03'):
        # Comprimida - precisa derivar y
        print("  ⚠️ Pubkey comprimida - derivando y...")
        x = int(hex_str[2:66], 16)
        # y² = x³ + 7 mod p
        p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
        y_squared = (pow(x, 3, p) + 7) % p
        y = pow(y_squared, (p + 1) // 4, p)
        if hex_str.startswith('03'):
            y = p - y
        return (x, y)
    return None

def test_brainwallet_simple(pubkey_point, target_address):
    """Teste simples de brainwallet com senhas comuns"""
    common_passwords = [
        'bitcoin', 'password', '123456', 'admin', 'test',
        'bitcoin2009', 'satoshi', 'nakamoto', 'puzzle',
        '123456789', 'qwerty', 'letmein', 'welcome'
    ]
    
    for pwd in common_passwords:
        # SHA256(password)
        h = hashlib.sha256(pwd.encode()).hexdigest()
        k = int(h, 16)
        
        # Calcular ponto público
        pub = scalar_mul(k, G)
        
        if pub == pubkey_point:
            return {'found': True, 'password': pwd, 'method': 'SHA256'}
        
        # SHA256(SHA256(password))
        h2 = hashlib.sha256(bytes.fromhex(h)).hexdigest()
        k2 = int(h2, 16)
        pub2 = scalar_mul(k2, G)
        
        if pub2 == pubkey_point:
            return {'found': True, 'password': pwd, 'method': 'SHA256x2'}
    
    return {'found': False}

def test_simple_patterns(pubkey_point):
    """Testar padrões simples na chave"""
    x, y = pubkey_point
    
    # Verificar se x ou y têm padrões óbvios
    x_hex = hex(x)[2:]
    y_hex = hex(y)[2:]
    
    patterns = []
    
    # Muitos zeros
    if x_hex.count('0') > 50:
        patterns.append('x tem muitos zeros')
    if y_hex.count('0') > 50:
        patterns.append('y tem muitos zeros')
    
    # Sequências repetidas
    if 'aaaa' in x_hex or 'ffff' in x_hex:
        patterns.append('x tem sequência repetida')
    
    # Números pequenos
    if x < 2**128:
        patterns.append('x é muito pequeno (< 128 bits)')
    if y < 2**128:
        patterns.append('y é muito pequeno (< 128 bits)')
    
    return patterns

import hashlib

def main():
    print(" Testando ataques simples em endereços P2PK\n")
    
    for i, target in enumerate(TARGETS):
        print(f"[{i+1}/{len(TARGETS)}] {target['address']}")
        print(f"  Saldo: {target['balance_btc']} BTC")
        print(f"  Pubkey: {target['pubkey_hex'][:30]}...")
        
        # Parse pubkey
        pubkey_point = parse_pubkey(target['pubkey_hex'])
        if not pubkey_point:
            print("  ❌ Erro ao parsear pubkey\n")
            continue
        
        # Teste 1: Brainwallet simples
        print("  [1/3] Testando brainwallet...")
        result = test_brainwallet_simple(pubkey_point, target['address'])
        if result['found']:
            print(f"  ✅ ENCONTRADO! Senha: {result['password']} (método: {result['method']})")
        else:
            print("   Não encontrado em senhas comuns")
        
        # Teste 2: Padrões simples
        print("  [2/3] Testando padrões...")
        patterns = test_simple_patterns(pubkey_point)
        if patterns:
            print(f"  ️  Padrões detectados: {', '.join(patterns)}")
        else:
            print("  ✅ Sem padrões óbvios")
        
        # Teste 3: Verificar se pubkey gera o endereço correto
        print("  [3/3] Verificando endereço...")
        try:
            x, y = pubkey_point
            addr = point_to_address(x, y)
            if addr == target['address']:
                print(f"  ✅ Endereço correto: {addr}")
            else:
                print(f"  ❌ Endereço não bate: {addr} != {target['address']}")
        except Exception as e:
            print(f"  ️  Erro ao verificar endereço: {e}")
        
        print()

if __name__ == '__main__':
    main()
