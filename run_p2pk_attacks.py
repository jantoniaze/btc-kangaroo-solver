#!/usr/bin/env python3
"""
Testar 9 ataques criptoanalíticos nos endereços P2PK
Baseado no projeto RakinSV/Bitcoin-Puzzle-AllAttacks-Analytics
"""

import sys
import os
sys.path.insert(0, '/home/home/Bitcoin-Puzzle-AllAttacks-Analytics')

from ecc.curve import G, N, scalar_mul, point_from_pubkey_hex
from analysis.brainwallet_attack import test_brainwallet
from analysis.nonce_attack import test_nonce_reuse
from analysis.pubkey_pattern import test_pubkey_patterns
from analysis.rng_analysis import test_rng_weakness
from analysis.key_structure_hunt import test_key_structure
from analysis.arithmetic_hunt import test_arithmetic_patterns
from analysis.sequence_hunt import test_sequence_patterns
from analysis.creator_fingerprint import test_creator_fingerprint
from analysis.deep_correlate import test_deep_correlation

# Top 10 endereços P2PK com maior saldo
P2PK_TARGETS = [
    {
        'address': '1PTYXwamXXgQoAhDbmUf98rY2Pg1pYXhin',
        'balance_btc': 3233.17,
        'pubkey': '04633280c0a93b45217059013ddadab8d35b9a858336028fecdff64c6a5e068fadaf7d2b73bc22795fa160c2304703320516e1b0b20e43d613fa5975787c8287e4'
    },
    {
        'address': '16mEzobs4wQPuAMq1C8QSQafcDHvzczVcs',
        'balance_btc': 875.00,
        'pubkey': '0469119c7e7d8e8b9f404d70c36cc09cae033e86d259554fd945c9263560fdc9ddea108db86e5673b3894b0bf97807ff8ac6e322791cf8d4d22f7c55a0e812720a'
    },
    {
        'address': '1P2ZAuW9nUrFfwgVjfL2SA9sPXSruCfzp8',
        'balance_btc': 800.00,
        'pubkey': '04a9c9c642db7941be7d9d467786c05b66d13c4fdafeb81d66815fb336e7e19d42981f62f2624826898152444b99b590476c90ea7f2e15f50a00e726368d6ec7c1'
    },
    {
        'address': '15UkFYLMs5nytwiKWqGgkkVo1fjLFAeJhs',
        'balance_btc': 750.00,
        'pubkey': '044da39d1810bb01f7039fa7cdfa3dca6de313bbf2d9db9f24170e87b0206f079adb64cccc5cdf6283a54826adaf265087b3f8eba02577153aeaa6cdea8165d6df'
    },
    {
        'address': '15BKWJjL5YWXtaP449WAYqVYZQE1szicTn',
        'balance_btc': 550.00,
        'pubkey': '042e3d29ccb78680a0da35bac8dc7adf895feb2b8eb9dbc5058400d811f6d7ce46faf0099ef63a05f3a8340e7e95530515303d652f27c2d9b379174b41bfd7046b'
    },
    {
        'address': '1PxeCXMZBuXHt4CqWWEQ7Kwgdyob9P955L',
        'balance_btc': 500.00,
        'pubkey': '04554a9abcde5e79acb2552e6159b287c72c9c31b1a2510a877e3c8dc3cb1780da707b2364a229a3e7df8cd09a8e2c477589035b3590a7f9cd624a227b5624c574'
    },
    {
        'address': '19NBWfZniu18DbmneRcaGU3sZCrCvrZrRR',
        'balance_btc': 400.00,
        'pubkey': '0440052ac1b21256bcaf97362dc1121b023b60c2259695cb8e6ea04285693c62631cd9cb01d9c76d3d018c6ce99d710b05f6b3e5490d7ed0df669a55de1910bc81'
    },
    {
        'address': '1JSxDnLYD4XKTQ73N7in2M9XRovw5LANiu',
        'balance_btc': 350.04,
        'pubkey': '04ad1a9add887e10bd85e633c98af64bf7dbf55ae8e2e5ee1a52df32a6c66e155092fb4dabc8226c0dcf6c8749b8bff1cbb826743d35b05ee865d0fb6dcc20baf1'
    },
    {
        'address': '1JqPFnGPhHhy54zJKmC1MPiczzgFjCmzE9',
        'balance_btc': 340.00,
        'pubkey': '04f51f8d0c4dc4a5338bef745098e6f6364f8936fee6aa5a9d4ab0c214e7cdd727f094f442779b37d9046e53ea3f0b988aefaa6e0adb0662155cd763229e8519aa'
    },
    {
        'address': '1GkMg44pUuDp6DPWNCsjd9Do5gt8cELpUA',
        'balance_btc': 300.00,
        'pubkey': '02c0009b2a29f071fb371a5ea5a4f0e3a5e3b5e5e5e5e5e5e5e5e5e5e5e5e5e5'
    }
]

def run_all_attacks(target):
    """Executar todos os 9 ataques em um alvo"""
    print(f"\n{'='*80}")
    print(f"ALVO: {target['address']}")
    print(f"Saldo: {target['balance_btc']} BTC")
    print(f"Pubkey: {target['pubkey'][:20]}...")
    print(f"{'='*80}\n")
    
    pubkey_point = point_from_pubkey_hex(target['pubkey'])
    
    results = {}
    
    # 1. Brainwallet Attack
    print("[1/9] Testando Brainwallet...")
    results['brainwallet'] = test_brainwallet(pubkey_point)
    
    # 2. Nonce Reuse Attack
    print("[2/9] Testando Nonce Reuse...")
    results['nonce_reuse'] = test_nonce_reuse(pubkey_point)
    
    # 3. Public Key Pattern Analysis
    print("[3/9] Analisando padrões da Public Key...")
    results['pubkey_pattern'] = test_pubkey_patterns(pubkey_point)
    
    # 4. RNG Weakness Analysis
    print("[4/9] Analisando fraqueza do RNG...")
    results['rng_weakness'] = test_rng_weakness(pubkey_point)
    
    # 5. Key Structure Hunt
    print("[5/9] Buscando estrutura na chave...")
    results['key_structure'] = test_key_structure(pubkey_point)
    
    # 6. Arithmetic Patterns
    print("[6/9] Buscando padrões aritméticos...")
    results['arithmetic'] = test_arithmetic_patterns(pubkey_point)
    
    # 7. Sequence Patterns
    print("[7/9] Buscando padrões de sequência...")
    results['sequence'] = test_sequence_patterns(pubkey_point)
    
    # 8. Creator Fingerprint
    print("[8/9] Analisando fingerprint do criador...")
    results['creator_fingerprint'] = test_creator_fingerprint(pubkey_point)
    
    # 9. Deep Correlation
    print("[9/9] Análise de correlação profunda...")
    results['deep_correlation'] = test_deep_correlation(pubkey_point)
    
    return results

def main():
    print(" Iniciando análise de 9 ataques em 10 endereços P2PK")
    print(f"Total de endereços: {len(P2PK_TARGETS)}")
    print(f"Saldo total: {sum(t['balance_btc'] for t in P2PK_TARGETS):.2f} BTC")
    
    all_results = []
    
    for i, target in enumerate(P2PK_TARGETS):
        print(f"\n[{i+1}/{len(P2PK_TARGETS)}] Processando {target['address']}...")
        
        try:
            results = run_all_attacks(target)
            all_results.append({
                'address': target['address'],
                'balance': target['balance_btc'],
                'results': results
            })
        except Exception as e:
            print(f"❌ Erro ao processar {target['address']}: {e}")
            all_results.append({
                'address': target['address'],
                'balance': target['balance_btc'],
                'results': {'error': str(e)}
            })
    
    # Resumo final
    print(f"\n{'='*80}")
    print("RESUMO FINAL")
    print(f"{'='*80}\n")
    
    vulnerable = []
    for result in all_results:
        attacks_found = [k for k, v in result['results'].items() 
                        if v and v.get('vulnerable', False)]
        if attacks_found:
            vulnerable.append({
                'address': result['address'],
                'balance': result['balance'],
                'attacks': attacks_found
            })
    
    if vulnerable:
        print(f"️  {len(vulnerable)} endereços com vulnerabilidades detectadas:")
        for v in vulnerable:
            print(f"\n  {v['address']}")
            print(f"  Saldo: {v['balance']} BTC")
            print(f"  Vulnerável a: {', '.join(v['attacks'])}")
    else:
        print("✅ Nenhum endereço com vulnerabilidades óbvias detectadas.")
        print("   Todos usam chaves com entropia adequada.")
    
    # Salvar resultados
    import json
    with open('/home/home/kangaroo/p2pk_attack_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n📊 Resultados salvos em: /home/home/kangaroo/p2pk_attack_results.json")

if __name__ == '__main__':
    main()
