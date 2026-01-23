"""Módulo de estado de conexão para protocolo RUDP."""
from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Tuple


class ConnectionState(Enum):
    """Estados possíveis de uma conexão RUDP (inspirado em TCP)."""
    CLOSED = auto()
    SYN_SENT = auto()       # Cliente enviou SYN, aguardando SYN-ACK
    SYN_RECEIVED = auto()   # Servidor recebeu SYN, enviou SYN-ACK
    ESTABLISHED = auto()    # Conexão estabelecida
    FIN_WAIT = auto()       # Enviou FIN, aguardando ACK
    CLOSE_WAIT = auto()     # Recebeu FIN, enviou ACK


@dataclass
class Connection:
    """Representa uma conexão RUDP ativa."""
    state: ConnectionState = ConnectionState.CLOSED
    remote_addr: Tuple[str, int] | None = None
    local_seq: int = 0      # Próximo seq a enviar
    remote_seq: int = 0     # Último seq recebido do peer
    last_ack: int = 0       # Último ACK enviado
    
    # Entrega ordenada (servidor)
    expected_seq: int = 0   # Próximo seq esperado em ordem
    out_of_order: dict = field(default_factory=dict)  # seq → payload (buffer)
    
    # Buffer de dados recebidos (servidor) - em ordem
    recv_buffer: bytes = field(default=b"")
    recv_buffer_max: int = 65536  # Limite do buffer (64KB default)
    
    # Controle de fluxo (cliente)
    remote_wnd: int = 64    # rwnd anunciado pelo servidor (em pacotes)
    
    # Controle de congestionamento (cliente)
    cwnd: int = 1           # Janela de congestionamento (em pacotes)
    ssthresh: int = 64      # Slow start threshold
    
    # Métricas
    packets_recv: int = 0
    bytes_recv: int = 0
    packets_dropped: int = 0  # Duplicatas descartadas
    
    def get_rwnd(self, payload_size: int = 1024) -> int:
        """Calcula rwnd disponível (em pacotes)."""
        bytes_free = max(0, self.recv_buffer_max - len(self.recv_buffer))
        return bytes_free // payload_size
