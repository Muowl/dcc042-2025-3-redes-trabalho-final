"""Script de benchmark simplificado para avaliação do protocolo RUDP."""
import sys
import os
import time
import threading
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rudp.server import RUDPServer
from rudp.client import RUDPClient

DATA_SIZE = 1024 * 1024  # 1MB

results = []

scenarios = [
    ("Sem perdas", 0.0, False, 9400),
    ("Sem perdas + Crypto", 0.0, True, 9401),
    ("5% perdas", 0.05, False, 9402),
    ("5% perdas + Crypto", 0.05, True, 9403),
    ("10% perdas", 0.10, False, 9404),
]

for name, drop, crypto, port in scenarios:
    print(f"Testando: {name}...")
    s = RUDPServer("127.0.0.1", port, drop)
    t = threading.Thread(target=s.run, daemon=True)
    t.start()
    time.sleep(0.3)
    
    c = RUDPClient("127.0.0.1", port, 0.3, use_crypto=crypto)
    if c.connect():
        stats = c.send_data(os.urandom(DATA_SIZE))
        c.close()
        results.append({
            "scenario": name,
            "packets_sent": stats.packets_sent,
            "throughput_kbps": stats.throughput_kbps,
            "retransmissions": stats.retransmissions,
            "time_ms": stats.time_ms,
            "drop_rate": drop,
            "crypto": crypto
        })
        print(f"  OK: {stats.packets_sent} pkts, {stats.throughput_kbps:.1f} KB/s")
    else:
        print(f"  FALHA na conexao")
        results.append({
            "scenario": name,
            "packets_sent": 0,
            "throughput_kbps": 0,
            "retransmissions": 0,
            "time_ms": 0,
            "drop_rate": drop,
            "crypto": crypto
        })

# Salvar resultados
results_dir = Path(__file__).parent / "results"
results_dir.mkdir(exist_ok=True, parents=True)
with open(results_dir / "benchmark_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nResultados salvos em scripts/results/benchmark_results.json")
print("\n" + "=" * 70)
print(f"{'Cenário':<25} {'Pacotes':>8} {'Vazão (KB/s)':>12} {'Retx':>6}")
print("-" * 70)
for r in results:
    print(f"{r['scenario']:<25} {r['packets_sent']:>8} {r['throughput_kbps']:>12.1f} {r['retransmissions']:>6}")
print("=" * 70)
