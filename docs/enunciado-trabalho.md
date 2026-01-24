# Trabalho Final: Protocolo de Transporte Confiável sobre UDP

## 1) Organização

- Trabalho em grupo de 1 a 3 membros
- Linguagem: C ou Python
- Entrega do código: repositório no GitHub e compartilhamento com o professor (usuário: `edeunix`)
- Incluir: README com instruções de execução e descrição do projeto
- Entrega do relatório: PDF + link do Git na atividade

---

## 2) Objetivo

Construir um protocolo de transporte confiável sobre o protocolo UDP (não confiável), implementando os mecanismos de confiabilidade, controle e segurança na camada de aplicação.

---

## 3) Cenário do Sistema

- Comunicação ponto a ponto entre cliente (remetente) e servidor (destinatário)
- A troca de pacotes deve usar UDP (sem alterações no kernel do sistema operacional)
- Toda a lógica do "UDP modificado" deve ser implementada na aplicação, tratando os dados enviados e recebidos

---

## 4) Requisitos do Protocolo

Seu protocolo deve incluir as seguintes funcionalidades:

### 4.1) Entrega Ordenada
- Implementar numeração de sequência nos pacotes para reconstrução na ordem correta

### 4.2) Confirmação de Recebimento (ACK)
Escolher uma das opções:
- ACK acumulativo (cumulativo), ou
- Repetição seletiva (ACK individual por pacote)

### 4.3) Controle de Fluxo
- O remetente deve conhecer o tamanho da janela do destinatário para evitar sobrecarregá-lo (não "afogar" o receptor)

### 4.4) Controle de Congestionamento
- Criar uma equação/regra de controle para reduzir o envio quando houver sinais de perda na rede
- Exemplos de sinais: muitos ACKs pendentes, ACKs duplicados ou timeout

**Comentários:**
- Você deve propor um mecanismo (pode ser baseado em TCP, QUIC ou outro protocolo)
- Considere a Aula 13: TCP usa uma janela `cwnd` e a variável `ssthresh` para as fases de *Slow Start* e *Congestion Avoidance*

### 4.5) Criptografia dos Dados
- Propor e aplicar alguma criptografia (existente ou criada por você) aos dados trocados entre cliente e servidor
- O "acordo"/configuração criptográfica deve ocorrer antes ou depois do handshake do seu protocolo

---

## 5) Avaliação Experimental (Testes)

Você deve avaliar o protocolo no seguinte cenário:

- 1 remetente (cliente) envia um arquivo (ou dados sintéticos preenchendo o payload) para 1 destinatário (servidor)

**Restrições:**
- Os dados enviados devem equivaler a pelo menos 10.000 pacotes
- Para testar o controle de congestionamento, insira perdas arbitrárias no destinatário (por exemplo, usando uma função `rand()`)
  - A cada pacote recebido, sortear se ele será processado ou descartado

---

## 6) Relatório (Documentação + Resultados)

Escrever um relatório (template SBC) documentando:

- A lógica do protocolo e onde encontrar no código a resposta/implementação de cada requisito (seções 4.1 a 4.5)
- Gráficos de vazão (*throughput*) no envio de pacotes comparando:
  - Sem perdas vs. com perdas
  - Sem controle de congestionamento vs. com controle de congestionamento
- Discussão no texto de cada resultado apresentado

**Template SBC (Overleaf):**  
https://www.overleaf.com/latex/templates/sbc-conferences-template/blbxwjwzdngr

---

## 7) Entrega

Submeter nesta atividade:
1. Link do repositório GitHub (contendo código + README)
2. PDF do relatório

