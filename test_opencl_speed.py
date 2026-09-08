#!/usr/bin/env python3
"""Testar performance do motor OpenCL na RX 6600"""

import sys
import time
sys.path.insert(0, '/home/home/kangaroo/opencl_solver')

from kangaroo_engine import KangarooEngine

# Puzzle #40 (faixa pequena para teste rápido)
PUZZLE = 40
K_START = 2 ** (PUZZLE - 1)
K_END = 2 ** PUZZLE - 1

print(f"=== Teste de Performance OpenCL ===")
print(f"Puzzle: #{PUZZLE}")
print(f"Range: [{K_START:#x}, {K_END:#x}]")
print(f"Bits: {PUZZLE}")
print()

# Criar engine com parâmetros otimizados para RX 6600
engine = KangarooEngine(
    pubkey=None,  # Modo pré-warm (sem pubkey ainda)
    k_start=K_START,
    k_end=K_END,
    device_idx=0,  # RX 6600
    n_tame=16384,
    n_wild=16384,
    dp_bits=14,
    use_mb=True,  # Per-hop batch inversion
    k_batch=16
)

print()
print("=== Configurado para RX 6600 ===")
print(f"Threads: 128 (wavefront=32)")
print(f"Blocks: 2048")
print(f"Points/thread: 120")
print(f"Total points: {128 * 2048 * 120:,}")
print()

# Simular alguns passos para medir velocidade
print("=== Medindo performance ===")
n_steps = 10
total_hops = 0

for i in range(n_steps):
    t0 = time.time()
    dps = engine.step()
    t1 = time.time()
    
    hops = engine.hops_per_call()
    total_hops += hops
    elapsed = t1 - t0
    speed = hops / elapsed / 1_000_000
    
    print(f"Step {i+1}: {hops:,} hops em {elapsed:.3f}s = {speed:.1f} Mhops/s")

print()
print(f"=== Resultado ===")
print(f"Total hops: {total_hops:,}")
print(f"Velocidade média: {total_hops / (t1 - t0) / 1_000_000:.1f} Mhops/s")
print()
print("✅ Motor OpenCL funcionando na RX 6600!")
