"""Script de benchmark para avaliação do protocolo RUDP."""
from __future__ import annotations
import os
import sys
import json
import time
import logging
import threading
from dataclasses import dataclass, asdict
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rudp.server import RUDPServer
from rudp.client import RUDPClient

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
log = logging.getLogger("benchmark")
log.setLevel(logging.INFO)


@dataclass
class BenchmarkResult:
    """Resultado de um cenário de benchmark."""
    scenario: str
    packets_sent: int
    bytes_sent: int
    time_ms: int
    throughput_kbps: float
    retransmissions: int
    drop_rate: float
    congestion_control: bool
    crypto: bool


def run_scenario(
    name: str,
    data_size: int,
    drop_rate: float = 0.0,
    use_crypto: bool = True,
    port: int = 9100,
    timeout: float = 0.5,
) -> BenchmarkResult:
    """Executa um cenário de benchmark."""
    log.info(f"=== {name} ===")
    log.info(f"  Data: {data_size} bytes, Drop: {drop_rate*100:.0f}%, Crypto: {use_crypto}")
    
    # Iniciar servidor em thread
    server = RUDPServer("127.0.0.1", port, drop_prob=drop_rate)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    time.sleep(0.3)  # Aguardar servidor iniciar
    
    # Cliente
    client = RUDPClient("127.0.0.1", port, timeout_s=timeout, use_crypto=use_crypto)
    
    if not client.connect():
        log.error("Falha ao conectar")
        return None
    
    # Gerar dados sintéticos
    data = os.urandom(data_size)
    
    # Enviar e coletar métricas
    stats = client.send_data(data)
    client.close()
    
    result = BenchmarkResult(
        scenario=name,
        packets_sent=stats.packets_sent,
        bytes_sent=stats.bytes_sent,
        time_ms=stats.time_ms,
        throughput_kbps=stats.throughput_kbps,
        retransmissions=stats.retransmissions,
        drop_rate=drop_rate,
        congestion_control=True,  # Sempre ativo nesta versão
        crypto=use_crypto,
    )
    
    log.info(f"  Resultado: {result.packets_sent} pkts, {result.throughput_kbps:.2f} KB/s, {result.retransmissions} retx")
    return result


def main():
    """Executa todos os cenários de benchmark."""
    results = []
    
    # Tamanho para >= 10.000 pacotes (cada pacote = 1024 bytes)
    # 10.000 * 1024 = 10.240.000 bytes ≈ 10MB
    DATA_SIZE = 10 * 1024 * 1024  # 10MB = ~10.000 pacotes
    
    port = 9100
    
    # Cenário 1: Sem perdas, com crypto
    r = run_scenario("Sem perdas + Crypto", DATA_SIZE, drop_rate=0.0, use_crypto=True, port=port)
    if r: results.append(r)
    port += 1
    
    # Cenário 2: Sem perdas, sem crypto
    r = run_scenario("Sem perdas + Sem Crypto", DATA_SIZE, drop_rate=0.0, use_crypto=False, port=port)
    if r: results.append(r)
    port += 1
    
    # Cenário 3: Com 5% perdas, com crypto
    r = run_scenario("5% perdas + Crypto", DATA_SIZE, drop_rate=0.05, use_crypto=True, port=port, timeout=0.3)
    if r: results.append(r)
    port += 1
    
    # Cenário 4: Com 10% perdas, com crypto
    r = run_scenario("10% perdas + Crypto", DATA_SIZE, drop_rate=0.10, use_crypto=True, port=port, timeout=0.3)
    if r: results.append(r)
    port += 1
    
    # Cenário 5: Com 5% perdas, sem crypto
    r = run_scenario("5% perdas + Sem Crypto", DATA_SIZE, drop_rate=0.05, use_crypto=False, port=port, timeout=0.3)
    if r: results.append(r)
    port += 1
    
    # Salvar resultados
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    results_file = output_dir / "benchmark_results.json"
    with open(results_file, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    log.info(f"Resultados salvos em {results_file}")
    
    # Imprimir tabela resumo
    print("\n" + "=" * 80)
    print("RESUMO DOS RESULTADOS")
    print("=" * 80)
    print(f"{'Cenário':<30} {'Pacotes':>10} {'Vazão (KB/s)':>15} {'Retx':>8} {'Tempo (s)':>10}")
    print("-" * 80)
    for r in results:
        print(f"{r.scenario:<30} {r.packets_sent:>10} {r.throughput_kbps:>15.2f} {r.retransmissions:>8} {r.time_ms/1000:>10.2f}")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    main()
