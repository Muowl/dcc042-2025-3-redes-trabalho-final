"""Servidor RUDP com suporte a handshake e estado de conexão."""
from __future__ import annotations
import socket
import logging
from rudp.packet import Packet, PT_DATA, PT_ACK, PT_SYN, PT_SYN_ACK, PT_FIN
from rudp.connection import Connection, ConnectionState
from rudp.utils import should_drop

log = logging.getLogger("rudp.server")


class RUDPServer:
    """Servidor RUDP com gerenciamento de conexões e 3-way handshake."""
    
    def __init__(self, bind: str, port: int, drop_prob: float = 0.0):
        self.bind = bind
        self.port = port
        self.drop_prob = drop_prob
        # Dicionário de conexões ativas: addr -> Connection
        self.connections: dict[tuple[str, int], Connection] = {}

    def _get_or_create_connection(self, addr: tuple[str, int]) -> Connection:
        """Obtém conexão existente ou cria nova."""
        if addr not in self.connections:
            self.connections[addr] = Connection(remote_addr=addr)
        return self.connections[addr]

    def _handle_syn(self, pkt: Packet, addr: tuple[str, int], sock: socket.socket) -> None:
        """Trata pacote SYN: inicia handshake."""
        conn = self._get_or_create_connection(addr)
        conn.remote_seq = pkt.seq
        conn.local_seq = 0  # Poderia ser aleatório também
        conn.state = ConnectionState.SYN_RECEIVED
        
        # Enviar SYN-ACK
        syn_ack = Packet(
            ptype=PT_SYN_ACK,
            flags=0,
            seq=conn.local_seq,
            ack=pkt.seq,  # ACK do SYN recebido
            wnd=64,
            payload=b"",
        )
        sock.sendto(syn_ack.encode(), addr)
        log.info("SYN-ACK enviado para %s (ack=%d)", addr, pkt.seq)

    def _handle_ack(self, pkt: Packet, addr: tuple[str, int]) -> None:
        """Trata pacote ACK: pode completar handshake ou confirmar dados."""
        conn = self.connections.get(addr)
        if not conn:
            log.warning("ACK de conexão desconhecida %s", addr)
            return
        
        if conn.state == ConnectionState.SYN_RECEIVED:
            # Completar handshake
            conn.state = ConnectionState.ESTABLISHED
            log.info("Conexão ESTABLISHED com %s", addr)
        elif conn.state == ConnectionState.ESTABLISHED:
            log.debug("ACK recebido ack=%d de %s", pkt.ack, addr)

    def _handle_data(self, pkt: Packet, addr: tuple[str, int], sock: socket.socket) -> None:
        """Trata pacote DATA: recebe dados, acumula no buffer e envia ACK."""
        conn = self.connections.get(addr)
        if not conn or conn.state != ConnectionState.ESTABLISHED:
            log.warning("DATA recebido sem conexão estabelecida de %s", addr)
            return
        
        # Acumular dados no buffer
        conn.recv_buffer += pkt.payload
        conn.packets_recv += 1
        conn.bytes_recv += len(pkt.payload)
        
        log.debug("DATA de %s seq=%d len=%d (total: %d bytes, %d pacotes)", 
                 addr, pkt.seq, len(pkt.payload), conn.bytes_recv, conn.packets_recv)
        
        conn.remote_seq = pkt.seq
        
        # Enviar ACK
        ack_pkt = Packet(
            ptype=PT_ACK,
            flags=0,
            seq=0,
            ack=pkt.seq,
            wnd=64,
            payload=b"",
        )
        sock.sendto(ack_pkt.encode(), addr)

    def _handle_fin(self, pkt: Packet, addr: tuple[str, int], sock: socket.socket) -> None:
        """Trata pacote FIN: encerra conexão."""
        conn = self.connections.get(addr)
        if not conn:
            log.warning("FIN de conexão desconhecida %s", addr)
            return
        
        log.info("FIN recebido de %s", addr)
        conn.state = ConnectionState.CLOSE_WAIT
        
        # Enviar ACK do FIN
        ack_pkt = Packet(
            ptype=PT_ACK,
            flags=0,
            seq=0,
            ack=pkt.seq,
            wnd=0,
            payload=b"",
        )
        sock.sendto(ack_pkt.encode(), addr)
        
        # Log de métricas antes de encerrar
        log.info("Conexão com %s: %d pacotes, %d bytes recebidos", 
                 addr, conn.packets_recv, conn.bytes_recv)
        
        # Remover conexão
        del self.connections[addr]
        log.info("Conexão com %s encerrada", addr)

    def run(self) -> None:
        """Loop principal do servidor."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.bind, self.port))
        log.info("Servidor escutando em %s:%d", self.bind, self.port)

        while True:
            raw, addr = sock.recvfrom(65535)

            if should_drop(self.drop_prob):
                log.warning("Simulando perda: descartado pacote de %s", addr)
                continue

            try:
                pkt = Packet.decode(raw)
            except Exception as e:
                log.warning("Pacote inválido de %s: %s", addr, e)
                continue

            # Dispatch por tipo de pacote
            if pkt.ptype == PT_SYN:
                self._handle_syn(pkt, addr, sock)
            elif pkt.ptype == PT_ACK:
                self._handle_ack(pkt, addr)
            elif pkt.ptype == PT_DATA:
                self._handle_data(pkt, addr, sock)
            elif pkt.ptype == PT_FIN:
                self._handle_fin(pkt, addr, sock)
            else:
                log.warning("Tipo de pacote desconhecido: %d de %s", pkt.ptype, addr)
