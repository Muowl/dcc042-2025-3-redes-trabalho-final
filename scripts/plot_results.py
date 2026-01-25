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
    
    # Cores: verde para CC on, vermelho para CC off
    colors = []
    for r in results:
        if r.get("cc_enabled", True):
            colors.append('#2ecc71')  # Verde
        else:
            colors.append('#e74c3c')  # Vermelho
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(scenarios, throughputs, color=colors)
    
    ax.set_ylabel('Vazão (KB/s)', fontsize=12)
    ax.set_xlabel('Cenário', fontsize=12)
    ax.set_title('Comparação de Vazão por Cenário (Verde=CC on, Vermelho=CC off)', fontsize=14, fontweight='bold')
    
    # Adicionar valores nas barras
    for bar, val in zip(bars, throughputs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    
    plt.xticks(rotation=25, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'throughput_comparison.png', dpi=150)
    plt.close()
    print(f"Gráfico salvo: {output_dir / 'throughput_comparison.png'}")


def plot_retransmissions(results: list[dict], output_dir: Path):
    """Gera gráfico de retransmissões por cenário."""
    scenarios = [r["scenario"] for r in results]
    retx = [r["retransmissions"] for r in results]
    
    # Cores: verde para CC on, vermelho para CC off
    colors = []
    for r in results:
        if r.get("cc_enabled", True):
            colors.append('#2ecc71')
        else:
            colors.append('#e74c3c')
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(scenarios, retx, color=colors)
    
    ax.set_ylabel('Retransmissões', fontsize=12)
    ax.set_xlabel('Cenário', fontsize=12)
    ax.set_title('Retransmissões por Cenário (Verde=CC on, Vermelho=CC off)', fontsize=14, fontweight='bold')
    
    for bar, val in zip(bars, retx):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{val}', ha='center', va='bottom', fontsize=9)
    
    plt.xticks(rotation=25, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'retransmissions.png', dpi=150)
    plt.close()
    print(f"Gráfico salvo: {output_dir / 'retransmissions.png'}")


def plot_cc_comparison(results: list[dict], output_dir: Path):
    """Gera gráfico de comparação CC on vs CC off lado a lado."""
    # Agrupar por taxa de perda
    loss_rates = [0.0, 0.05, 0.10]
    labels = ['0% perdas', '5% perdas', '10% perdas']
    
    cc_on_throughput = []
    cc_off_throughput = []
    
    for rate in loss_rates:
        # Encontrar resultado CC on
        on_result = next((r for r in results if r["drop_rate"] == rate and r.get("cc_enabled", True) and not r.get("crypto", False)), None)
        off_result = next((r for r in results if r["drop_rate"] == rate and not r.get("cc_enabled", True)), None)
        
        cc_on_throughput.append(on_result["throughput_kbps"] if on_result else 0)
        cc_off_throughput.append(off_result["throughput_kbps"] if off_result else 0)
    
    x = range(len(labels))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar([i - width/2 for i in x], cc_on_throughput, width, label='CC ON', color='#2ecc71')
    bars2 = ax.bar([i + width/2 for i in x], cc_off_throughput, width, label='CC OFF', color='#e74c3c')
    
    ax.set_ylabel('Vazão (KB/s)', fontsize=12)
    ax.set_xlabel('Taxa de Perda', fontsize=12)
    ax.set_title('Comparação: Controle de Congestionamento ON vs OFF', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    
    # Adicionar valores nas barras
    for bar in bars1:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 1, f'{height:.1f}', ha='center', va='bottom', fontsize=10)
    for bar in bars2:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 1, f'{height:.1f}', ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'cc_comparison.png', dpi=150)
    plt.close()
    print(f"Gráfico salvo: {output_dir / 'cc_comparison.png'}")


def plot_loss_vs_throughput(results: list[dict], output_dir: Path):
    """Gera gráfico de vazão vs taxa de perda para CC on e CC off."""
    # Filtrar resultados sem crypto
    cc_on = [r for r in results if r.get("cc_enabled", True) and not r.get("crypto", False)]
    cc_off = [r for r in results if not r.get("cc_enabled", True)]
    
    # Ordenar por drop_rate
    cc_on = sorted(cc_on, key=lambda x: x["drop_rate"])
    cc_off = sorted(cc_off, key=lambda x: x["drop_rate"])
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if cc_on:
        drop_rates_on = [r["drop_rate"] * 100 for r in cc_on]
        throughputs_on = [r["throughput_kbps"] for r in cc_on]
        ax.plot(drop_rates_on, throughputs_on, 'o-', markersize=10, linewidth=2, color='#2ecc71', label='CC ON')
    
    if cc_off:
        drop_rates_off = [r["drop_rate"] * 100 for r in cc_off]
        throughputs_off = [r["throughput_kbps"] for r in cc_off]
        ax.plot(drop_rates_off, throughputs_off, 's--', markersize=10, linewidth=2, color='#e74c3c', label='CC OFF')
    
    ax.set_ylabel('Vazão (KB/s)', fontsize=12)
    ax.set_xlabel('Taxa de Perda (%)', fontsize=12)
    ax.set_title('Impacto da Taxa de Perda na Vazão (CC ON vs CC OFF)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'loss_vs_throughput.png', dpi=150)
    plt.close()
    print(f"Gráfico salvo: {output_dir / 'loss_vs_throughput.png'}")


def generate_latex_table(results: list[dict], output_dir: Path):
    """Gera tabela LaTeX com resultados."""
    latex = """\\begin{table}[ht]
\\centering
\\caption{Resultados do Benchmark (10.000+ pacotes) - Comparação CC on/off}
\\label{tab:benchmark}
\\begin{tabular}{lrrrrr}
\\toprule
Cenário & Pacotes & Vazão (KB/s) & Retx & Tempo (s) & CC \\\\
\\midrule
"""
    for r in results:
        cc_status = "on" if r.get("cc_enabled", True) else "off"
        latex += f"{r['scenario']} & {r['packets_sent']} & {r['throughput_kbps']:.2f} & {r['retransmissions']} & {r['time_ms']/1000:.2f} & {cc_status} \\\\\n"
    
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
    
    # Tentar carregar benchmark_10k.json primeiro, fallback para benchmark_results.json
    results_file = results_dir / "benchmark_10k.json"
    if not results_file.exists():
        results_file = results_dir / "benchmark_results.json"
    
    if not results_file.exists():
        print(f"ERRO: Arquivo de resultados não encontrado: {results_file}")
        print("Execute primeiro o benchmark_10k.py")
        return
    
    results = load_results(results_file)
    print(f"Carregados {len(results)} resultados de {results_file.name}")
    
    # Gerar gráficos
    plot_throughput_comparison(results, results_dir)
    plot_retransmissions(results, results_dir)
    plot_cc_comparison(results, results_dir)
    plot_loss_vs_throughput(results, results_dir)
    
    # Gerar tabela LaTeX
    generate_latex_table(results, results_dir)
    
    print("\nTodos os gráficos gerados com sucesso!")
    print(f"Copie os arquivos PNG de {results_dir} para docs/figuras/")


if __name__ == "__main__":
    main()
