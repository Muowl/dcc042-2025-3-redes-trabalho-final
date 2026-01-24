# Trabalho Final — Redes de Computadores (DCC042-2025.3-A)

**Aluno:** Felipe Lazzarini Cunha

Implementação em **Python** de um protocolo de transporte **confiável** sobre **UDP** (RUDP), com comunicação cliente/servidor na camada de aplicação.

## Requisitos Implementados

| Requisito | Descrição |
|-----------|-----------|
| 1 | **Entrega ordenada** — `expected_seq`, buffer de fora de ordem |
| 2 | **ACK + Retransmissão** — ACK cumulativo, timeout, MAX_RETRIES=5 |
| 3 | **Controle de fluxo** — `rwnd` dinâmico anunciado nos ACKs |
| 4 | **Controle de congestionamento** — Slow Start + Congestion Avoidance |
| 5 | **Criptografia** — Fernet (AES-128-CBC), chave negociada no handshake |

## Estrutura do Repositório

```
├── src/rudp/
│   ├── cli.py          # Entry point (--file, --synthetic)
│   ├── packet.py       # Formato do pacote, PAYLOAD_SIZE
│   ├── connection.py   # Estados, métricas, cwnd/rwnd
│   ├── client.py       # RUDPClient com handshake e crypto
│   ├── server.py       # RUDPServer com entrega ordenada
│   ├── crypto.py       # Fernet/AES criptografia
│   └── utils.py        # Helpers (now_ms, should_drop)
├── scripts/
│   ├── run_benchmark.py   # Benchmark automatizado
│   └── plot_results.py    # Geração de gráficos
├── docs/
│   ├── main.tex           # Documentação LaTeX
│   ├── figuras/           # Gráficos de avaliação
│   └── AGENT.md           # Instruções para agentes
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

**Cliente (dados sintéticos):**
```powershell
rudp client --host 127.0.0.1 --port 9000 --synthetic 10240
```

**Cliente (arquivo):**
```powershell
rudp client --host 127.0.0.1 --port 9000 --file caminho/para/arquivo.txt
```

### 4) Executar benchmark

```powershell
python scripts/run_benchmark.py
python scripts/plot_results.py
```

Os gráficos serão salvos em `scripts/results/`.

## Resultados do Benchmark

| Cenário | Vazão (KB/s) | Retransmissões | Tempo (s) |
|---------|-------------|----------------|-----------|
| Sem perdas | 34.50 | 6 | 1.85 |
| Sem perdas + Crypto | 34.52 | 6 | 1.85 |
| 5% perdas | 17.25 | 12 | 3.71 |
| 10% perdas | 20.62 | 10 | 3.10 |

## Documentação

A documentação completa está em `/docs`.

## Parâmetros do Servidor

| Parâmetro | Descrição |
|-----------|-----------|
| `--bind` | IP para escutar (default: 127.0.0.1) |
| `--port` | Porta UDP (default: 9000) |
| `--drop` | Taxa de perda simulada (0.0 a 1.0) |

## Criptografia

- **Algoritmo:** Fernet (AES-128-CBC + HMAC-SHA256)
- **Negociação:** Chave enviada no payload do SYN
- **Desabilitar:** Use `use_crypto=False` na API Python

## Gráficos Gerados

- `throughput_comparison.png` — Comparação de vazão
- `retransmissions.png` — Retransmissões por cenário
- `loss_vs_throughput.png` — Impacto da perda na vazão