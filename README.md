# Trabalho Final — Redes de Computadores (DCC042-2025.3-A)

**Aluno:** Felipe Lazzarini Cunha

Implementação em **Python** de um protocolo de transporte **confiável** sobre **UDP**, com comunicação cliente/servidor na camada de aplicação (entrega ordenada, ACK, controle de fluxo, controle de congestionamento e criptografia).

## Como rodar (Windows / PowerShell)

### 1) Criar e ativar o ambiente virtual
Na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Instalar o projeto
```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

### 3) Executar servidor e cliente
Servidor
```powershell
rudp server --bind 127.0.0.1 --port 9000
```
Cliente
```powershell
.\.venv\Scripts\Activate.ps1
rudp client --host 127.0.0.1 --port 9000 --message "ola"
```