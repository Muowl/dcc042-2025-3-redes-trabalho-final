"""Script para gerar gráficos de avaliação do protocolo RUDP."""
from __future__ import annotations
import json
from pathlib import Path

# Tentar importar matplotlib
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Backend não-interativo
except ImportError:
    print("ERRO: matplotlib não instalado. Execute: pip install matplotlib")
    exit(1)


def load_results(results_file: Path) -> list[dict]:
    """Carrega resultados do benchmark."""
    with open(results_file) as f:
        return json.load(f)


def plot_throughput_comparison(results: list[dict], output_dir: Path):
    """Gera gráfico de comparação de vazão."""
    scenarios = [r["scenario"] for r in results]
    throughputs = [r["throughput_kbps"] for r in results]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(scenarios, throughputs, color=['#2ecc71', '#3498db', '#e74c3c', '#9b59b6', '#f39c12'])
    
    ax.set_ylabel('Vazão (KB/s)', fontsize=12)
    ax.set_xlabel('Cenário', fontsize=12)
    ax.set_title('Comparação de Vazão por Cenário', fontsize=14, fontweight='bold')
    
    # Adicionar valores nas barras
    for bar, val in zip(bars, throughputs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                f'{val:.1f}', ha='center', va='bottom', fontsize=10)
    
    plt.xticks(rotation=15, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'throughput_comparison.png', dpi=150)
    plt.close()
    print(f"Gráfico salvo: {output_dir / 'throughput_comparison.png'}")


def plot_retransmissions(results: list[dict], output_dir: Path):
    """Gera gráfico de retransmissões por cenário."""
    scenarios = [r["scenario"] for r in results]
    retx = [r["retransmissions"] for r in results]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(scenarios, retx, color=['#2ecc71', '#3498db', '#e74c3c', '#9b59b6', '#f39c12'])
    
    ax.set_ylabel('Retransmissões', fontsize=12)
    ax.set_xlabel('Cenário', fontsize=12)
    ax.set_title('Retransmissões por Cenário', fontsize=14, fontweight='bold')
    
    for bar, val in zip(bars, retx):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{val}', ha='center', va='bottom', fontsize=10)
    
    plt.xticks(rotation=15, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'retransmissions.png', dpi=150)
    plt.close()
    print(f"Gráfico salvo: {output_dir / 'retransmissions.png'}")


def plot_loss_vs_throughput(results: list[dict], output_dir: Path):
    """Gera gráfico de vazão vs taxa de perda."""
    # Filtrar apenas cenários com crypto para comparação justa
    filtered = [r for r in results if r.get("crypto", True)]
    if len(filtered) < 2:
        filtered = results
    
    drop_rates = [r["drop_rate"] * 100 for r in filtered]
    throughputs = [r["throughput_kbps"] for r in filtered]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(drop_rates, throughputs, 'o-', markersize=10, linewidth=2, color='#3498db')
    
    ax.set_ylabel('Vazão (KB/s)', fontsize=12)
    ax.set_xlabel('Taxa de Perda (%)', fontsize=12)
    ax.set_title('Impacto da Taxa de Perda na Vazão', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'loss_vs_throughput.png', dpi=150)
    plt.close()
    print(f"Gráfico salvo: {output_dir / 'loss_vs_throughput.png'}")


def generate_latex_table(results: list[dict], output_dir: Path):
    """Gera tabela LaTeX com resultados."""
    latex = """\\begin{table}[ht]
\\centering
\\caption{Resultados do Benchmark (10.000+ pacotes)}
\\label{tab:benchmark}
\\begin{tabular}{lrrrr}
\\toprule
Cenário & Pacotes & Vazão (KB/s) & Retx & Tempo (s) \\\\
\\midrule
"""
    for r in results:
        latex += f"{r['scenario']} & {r['packets_sent']} & {r['throughput_kbps']:.2f} & {r['retransmissions']} & {r['time_ms']/1000:.2f} \\\\\n"
    
    latex += """\\bottomrule
\\end{tabular}
\\end{table}
"""
    
    output_file = output_dir / "benchmark_table.tex"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"Tabela LaTeX salva: {output_file}")
    return latex


def main():
    """Gera todos os gráficos e tabelas."""
    script_dir = Path(__file__).parent
    results_dir = script_dir / "results"
    
    if not results_dir.exists():
        results_dir.mkdir(parents=True)
    
    results_file = results_dir / "benchmark_results.json"
    
    if not results_file.exists():
        print(f"ERRO: Arquivo de resultados não encontrado: {results_file}")
        print("Execute primeiro o benchmark.py")
        return
    
    results = load_results(results_file)
    print(f"Carregados {len(results)} resultados")
    
    # Gerar gráficos
    plot_throughput_comparison(results, results_dir)
    plot_retransmissions(results, results_dir)
    plot_loss_vs_throughput(results, results_dir)
    
    # Gerar tabela LaTeX
    generate_latex_table(results, results_dir)
    
    print("\nTodos os gráficos gerados com sucesso!")


if __name__ == "__main__":
    main()
