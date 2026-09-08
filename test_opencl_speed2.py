#!/usr/bin/env python3
"""Testar performance do motor OpenCL na RX 6600"""

import sys
import time
sys.path.insert(0, '/home/home/kangaroo/opencl_solver')

from kangaroo_engine import KangarooEngine
from ecc.curve import G, N, scalar_mul

# Puzzle #40 (faixa pequena para teste rápido)
PUZZLE = 40
K_START = 2 ** (PUZZLE - 1)
K_END = 2 ** PUZZLE - 1

# Gerar pubkey de teste (chave aleatória no range)
import random
random.seed(42)
test_key = random.randrange(K_START, K_END)
test_pubkey = scalar_mul(test_key, G)

print(f"=== Teste de Performance OpenCL ===")
print(f"Puzzle: #{PUZZLE}")
print(f"Range: [{K_START:#x}, {K_END:#x}]")
print(f"Pubkey teste: ({test_pubkey[0]:#x}, {test_pubkey[1]:#x})")
print()

# Criar engine com parâmetros otimizados para RX 6600
engine = KangarooEngine(
    pubkey=test_pubkey,
    k_start=K_START,
    k_end=K_END,
    device_idx=0,  # RX 6600
    n_tame=16384,
    n_wild=16384,
    dp_bits=0,  # Auto
    use_mb=True,  # Per-hop batch inversion
    k_batch=16
)

print()
print("=== Inicializando cangurus ===")
engine.initialize()
print()

# Simular alguns passos para medir velocidade
print("=== Medindo performance ===")
n_steps = 10
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
    
    print(f"Step {i+1}: {hops:,} hops em {elapsed:.4f}s = {speed:.1f} Mhops/s")

t_end = time.time()
total_time = t_end - t_start

print()
print(f"=== Resultado ===")
print(f"Total hops: {total_hops:,}")
print(f"Tempo total: {total_time:.3f}s")
print(f"Velocidade média: {total_hops / total_time / 1_000_000:.1f} Mhops/s")
print()
print("✅ Motor OpenCL funcionando na RX 6600!")
