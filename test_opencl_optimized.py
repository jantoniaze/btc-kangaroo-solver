#!/usr/bin/env python3
"""Testar performance otimizada do motor OpenCL na RX 6600"""

import sys
import time
sys.path.insert(0, '/home/home/kangaroo/opencl_solver')

from kangaroo_engine import KangarooEngine
from ecc.curve import G, N, scalar_mul

# Puzzle #45 (um pouco maior para teste melhor)
PUZZLE = 45
K_START = 2 ** (PUZZLE - 1)
K_END = 2 ** PUZZLE - 1

# Gerar pubkey de teste
import random
random.seed(42)
test_key = random.randrange(K_START, K_END)
test_pubkey = scalar_mul(test_key, G)

print(f"=== Teste de Performance OpenCL Otimizado ===")
print(f"Puzzle: #{PUZZLE}")
print(f"Range: [{K_START:#x}, {K_END:#x}]")
print()

# Parâmetros OTIMIZADOS para RX 6600 (do projeto RakinSV)
# threads=128, blocks=2048, points_per_thread=120
# Total: 31.5M pontos
N_TAME = 16384 * 4   # 65536
N_WILD = 16384 * 4   # 65536

print(f"Configuração otimizada:")
print(f"  N_TAME: {N_TAME:,}")
print(f"  N_WILD: {N_WILD:,}")
print(f"  Total: {N_TAME + N_WILD * 2:,} cangurus")
print()

# Criar engine
engine = KangarooEngine(
    pubkey=test_pubkey,
    k_start=K_START,
    k_end=K_END,
    device_idx=0,
    n_tame=N_TAME,
    n_wild=N_WILD,
    dp_bits=0,  # Auto
    use_mb=True,
    k_batch=16
)

print("=== Inicializando ===")
engine.initialize()
print()

# Medir performance
print("=== Medindo performance ===")
n_steps = 20
total_hops = 0
t_start = time.time()

for i in range(n_steps):
    t0 = time.time()
    dps = engine.step()
    t1 = time.time()
    
    hops = engine.hops_per_call()
    total_hops += hops
    elapsed = t1 - t0
    speed = hops / elapsed / 1_000_000 if elapsed > 0 else 0
    
    if (i + 1) % 5 == 0:
        print(f"Step {i+1}: {hops:,} hops em {elapsed:.4f}s = {speed:.1f} Mhops/s")

t_end = time.time()
total_time = t_end - t_start

print()
print(f"=== Resultado Final ===")
print(f"Total hops: {total_hops:,}")
print(f"Tempo total: {total_time:.3f}s")
print(f"Velocidade média: {total_hops / total_time / 1_000_000:.1f} Mhops/s")
print()

# Comparar com projeto RakinSV
expected_speed = 600  # Mhops/s
actual_speed = total_hops / total_time / 1_000_000
percentage = (actual_speed / expected_speed) * 100

print(f"=== Comparação ===")
print(f"Esperado (RakinSV): ~{expected_speed} Mhops/s")
print(f"Atual: {actual_speed:.1f} Mhops/s")
print(f"Performance: {percentage:.1f}% do esperado")
print()

if percentage < 50:
    print("⚠️  Performance baixa. Verificar:")
    print("  - Parâmetros do kernel (threads, blocks, points/thread)")
    print("  - Ocupância da GPU")
    print("  - VRAM disponível")
else:
    print("✅ Performance boa!")
