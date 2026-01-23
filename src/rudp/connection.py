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
    
    # Métricas
    packets_recv: int = 0
    bytes_recv: int = 0
    packets_dropped: int = 0  # Duplicatas descartadas
