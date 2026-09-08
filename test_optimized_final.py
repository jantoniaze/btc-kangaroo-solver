#!/usr/bin/env python3
"""Teste final com parâmetros otimizados"""

import sys
import time
sys.path.insert(0, '/home/home/kangaroo/opencl_solver')

from kangaroo_engine import KangarooEngine
from ecc.curve import G, scalar_mul
import random

# Puzzle #45
PUZZLE = 45
K_START = 2 ** (PUZZLE - 1)
K_END = 2 ** PUZZLE - 1

random.seed(42)
test_key = random.randrange(K_START, K_END)
test_pubkey = scalar_mul(test_key, G)

print('=== Teste com parâmetros otimizados ===')
print(f'STEPS_CALL: 4096 (64×64)')
print()

# Parâmetros otimizados para RX 6600
N_TAME = 8192
N_WILD = 8192

engine = KangarooEngine(
    pubkey=test_pubkey,
    k_start=K_START,
    k_end=K_END,
    device_idx=0,
    n_tame=N_TAME,
    n_wild=N_WILD,
    dp_bits=0,
    use_mb=True,
    k_batch=16
)

engine.initialize()
print()

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
    
    if (i + 1) % 5 == 0:
        print(f'Step {i+1}: {hops:,} hops em {elapsed:.4f}s = {speed:.1f} Mhops/s')

t_end = time.time()
total_time = t_end - t_start

print()
print(f'=== Resultado ===')
print(f'Total hops: {total_hops:,}')
print(f'Velocidade média: {total_hops / total_time / 1_000_000:.1f} Mhops/s')
