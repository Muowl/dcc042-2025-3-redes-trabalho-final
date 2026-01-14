# Trabalho Final Redes de Computadores (DCC042-2025.3-A)

**Aluno:** Felipe Lazzarini Cunha

Implementação em **Python** de um protocolo de transporte **confiável** sobre **UDP**, com comunicação cliente/servidor na camada de aplicação (entrega ordenada, ACK, controle de fluxo, controle de congestionamento e criptografia).

## Como rodar (modo base)
- Terminal 1 (servidor):
  - `python -m rudp.cli server --bind 127.0.0.1 --port 9000`
- Terminal 2 (cliente):
  - `python -m rudp.cli client --host 127.0.0.1 --port 9000 --message "ola"`