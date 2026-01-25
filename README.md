# Trabalho Final — Redes de Computadores (DCC042-2025.3-A)

**Aluno:** Felipe Lazzarini Cunha

Implementação em **Python** de um protocolo de transporte **confiável** sobre **UDP** (RUDP), com comunicação cliente/servidor na camada de aplicação.

## Requisitos Implementados

| Requisito | Descrição |
|-----------|-----------|
| 1 | **Entrega ordenada** — `expected_seq`, buffer de fora de ordem |
| 2 | **ACK + Retransmissão** — ACK cumulativo, timeout, MAX_RETRIES=5 |
| 3 | **Controle de fluxo** — `rwnd` dinâmico anunciado nos ACKs |
| 4 | **Controle de congestionamento** — Slow Start + Congestion Avoidance (toggle via `cc_enabled`) |
| 5 | **Criptografia** — Fernet (AES-128-CBC), chave negociada no handshake |

## Estrutura do Repositório

```
├── src/rudp/
│   ├── cli.py          # Entry point (--file, --synthetic)
│   ├── packet.py       # Formato do pacote, PAYLOAD_SIZE
│   ├── connection.py   # Estados, métricas, cwnd/rwnd
│   ├── client.py       # RUDPClient com handshake, crypto e cc_enabled
│   ├── server.py       # RUDPServer com entrega ordenada
│   ├── crypto.py       # Fernet/AES criptografia
│   └── utils.py        # Helpers (now_ms, should_drop)
├── scripts/
│   ├── benchmark_10k.py   # Benchmark com ≥10k pacotes (CC on/off)
│   ├── run_benchmark.py   # Benchmark simplificado (1MB)
│   └── plot_results.py    # Geração de gráficos
├── docs/
│   ├── main.tex           # Documentação LaTeX
│   ├── figuras/           # Gráficos de avaliação
│   └── documentacao-final.pdf  # PDF do relatório
└── README.md
```

## Como Rodar (Windows / PowerShell)

### 1) Criar e ativar o ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> **Obs:** se o PowerShell bloquear, execute:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

### 2) Instalar o projeto e dependências

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
pip install cryptography matplotlib
```

### 3) Executar servidor e cliente

**Servidor:**
```powershell
rudp server --bind 127.0.0.1 --port 9000
```

**Cliente (mensagem simples):**
```powershell
rudp client --host 127.0.0.1 --port 9000 --message "Olá RUDP!"
```

**Cliente (dados sintéticos com 10k+ pacotes):**
```powershell
rudp client --host 127.0.0.1 --port 9000 --synthetic 10485760
```

**Cliente (arquivo):**
```powershell
rudp client --host 127.0.0.1 --port 9000 --file caminho/para/arquivo.txt
```

### 4) Executar benchmark completo (≥10k pacotes)

```powershell
python scripts/benchmark_10k.py
python scripts/plot_results.py
```

Os gráficos serão salvos em `scripts/results/` e copiados para `docs/figuras/`.

## Resultados do Benchmark (10MB ≈ 10.240 pacotes)

| Cenário | Vazão (KB/s) | Retransmissões | Tempo (s) | CC |
|---------|-------------|----------------|-----------|-----|
| Sem perdas (CC on) | 985.75 | 0 | 10.39 | on |
| Sem perdas (CC off) | 944.21 | 0 | 10.85 | off |
| 5% perdas (CC on) | 36.35 | 533 | 281.72 | on |
| 5% perdas (CC off) | 36.23 | 536 | 282.64 | off |
| 10% perdas (CC on) | 17.73 | 1117 | 577.47 | on |
| 10% perdas (CC off) | 17.09 | 1156 | 599.24 | off |
| Sem perdas + Crypto | 714.04 | 0 | 14.34 | on |

## Documentação

A documentação completa está em `/docs/documentacao-final.pdf`.

## Parâmetros do Cliente

| Parâmetro | Descrição |
|-----------|-----------|
| `--host` | IP do servidor (default: 127.0.0.1) |
| `--port` | Porta UDP (default: 9000) |
| `--synthetic` | Bytes de dados sintéticos a enviar |
| `--file` | Caminho do arquivo a enviar |
| `--message` | Mensagem de texto a enviar |

## Parâmetros do Servidor

| Parâmetro | Descrição |
|-----------|-----------|
| `--bind` | IP para escutar (default: 127.0.0.1) |
| `--port` | Porta UDP (default: 9000) |
| `--drop` | Taxa de perda simulada (0.0 a 1.0) |

## Controle de Congestionamento

- **Algoritmo:** Slow Start + Congestion Avoidance (inspirado em TCP)
- **Toggle:** `cc_enabled=True/False` na API Python
- **Comparação:** Benchmark inclui cenários com CC on/off

## Criptografia

- **Algoritmo:** Fernet (AES-128-CBC + HMAC-SHA256)
- **Negociação:** Chave enviada no payload do SYN
- **Desabilitar:** Use `use_crypto=False` na API Python

## Gráficos Gerados

- `throughput_comparison.png` — Comparação de vazão por cenário
- `retransmissions.png` — Retransmissões por cenário
- `loss_vs_throughput.png` — Impacto da perda na vazão (CC on vs off)
- `cc_comparison.png` — Comparação direta CC on vs CC off