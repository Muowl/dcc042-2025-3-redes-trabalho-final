"""Script de benchmark completo para avaliação do protocolo RUDP.

Atende aos requisitos:
- >= 10.000 pacotes
- Comparação CC on vs CC off
"""
import sys
import os
import time
import threading
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rudp.server import RUDPServer
from rudp.client import RUDPClient

# 10.000 pacotes * 1024 bytes = 10.240.000 bytes ≈ 10MB
DATA_SIZE = 10 * 1024 * 1024  # 10MB = ~10.000 pacotes

results = []

# Cenários: (nome, drop_rate, use_crypto, port, cc_enabled)
scenarios = [
    # Comparação CC on vs CC off - Sem perdas
    ("Sem perdas (CC on)", 0.0, False, 9500, True),
    ("Sem perdas (CC off)", 0.0, False, 9501, False),
    # Comparação CC on vs CC off - 5% perdas
    ("5% perdas (CC on)", 0.05, False, 9502, True),
    ("5% perdas (CC off)", 0.05, False, 9503, False),
    # Comparação CC on vs CC off - 10% perdas
    ("10% perdas (CC on)", 0.10, False, 9504, True),
    ("10% perdas (CC off)", 0.10, False, 9505, False),
    # Extra: com criptografia
    ("Sem perdas + Crypto (CC on)", 0.0, True, 9506, True),
]

print(f"Benchmark: {DATA_SIZE / 1024 / 1024:.1f}MB ({DATA_SIZE // 1024} pacotes)")
print("=" * 80)

for name, drop, crypto, port, cc_enabled in scenarios:
    print(f"\nTestando: {name}...")
    s = RUDPServer("127.0.0.1", port, drop)
    t = threading.Thread(target=s.run, daemon=True)
    t.start()
    time.sleep(0.3)
    
    c = RUDPClient("127.0.0.1", port, 0.5, use_crypto=crypto, cc_enabled=cc_enabled)
    if c.connect():
        data = os.urandom(DATA_SIZE)
        stats = c.send_data(data)
        c.close()
        
        results.append({
            "scenario": name,
            "packets_sent": stats.packets_sent,
            "throughput_kbps": stats.throughput_kbps,
            "retransmissions": stats.retransmissions,
            "time_ms": stats.time_ms,
            "drop_rate": drop,
            "crypto": crypto,
            "cc_enabled": cc_enabled,
            "data_mb": DATA_SIZE / 1024 / 1024,
        })
        print(f"  OK: {stats.packets_sent} pkts, {stats.throughput_kbps:.1f} KB/s, {stats.retransmissions} retx")
    else:
        print(f"  FALHA na conexao")
        results.append({
            "scenario": name,
            "packets_sent": 0,
            "throughput_kbps": 0,
            "retransmissions": 0,
            "time_ms": 0,
            "drop_rate": drop,
            "crypto": crypto,
            "cc_enabled": cc_enabled,
            "data_mb": DATA_SIZE / 1024 / 1024,
        })

# Salvar resultados
results_dir = Path(__file__).parent / "results"
results_dir.mkdir(exist_ok=True, parents=True)
with open(results_dir / "benchmark_10k.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 80)
print("RESULTADOS (>= 10.000 pacotes) - Comparação CC on vs CC off")
print("=" * 80)
print(f"{'Cenário':<35} {'Pacotes':>8} {'Vazão (KB/s)':>12} {'Retx':>6} {'Tempo (s)':>10}")
print("-" * 80)
for r in results:
    print(f"{r['scenario']:<35} {r['packets_sent']:>8} {r['throughput_kbps']:>12.1f} {r['retransmissions']:>6} {r['time_ms']/1000:>10.1f}")
print("=" * 80)
print(f"\nResultados salvos em: {results_dir / 'benchmark_10k.json'}")
