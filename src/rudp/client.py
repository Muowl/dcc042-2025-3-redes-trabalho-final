"""Cliente RUDP com suporte a handshake e estado de conexão."""
from __future__ import annotations
import socket
import logging
import random
from rudp.packet import Packet, PT_DATA, PT_ACK, PT_SYN, PT_SYN_ACK, PT_FIN
from rudp.connection import Connection, ConnectionState

log = logging.getLogger("rudp.client")


class RUDPClient:
    """Cliente RUDP com 3-way handshake."""
    
    def __init__(self, host: str, port: int, timeout_s: float = 1.0):
        self.host = host
        self.port = port
        self.timeout_s = timeout_s
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout_s)
        self.conn = Connection()
        # ISN (Initial Sequence Number) aleatório
        self.conn.local_seq = random.randint(0, 0xFFFFFFFF)
    
    def connect(self) -> bool:
        """Executa 3-way handshake: SYN → SYN-ACK → ACK."""
        if self.conn.state != ConnectionState.CLOSED:
            log.warning("Conexão já está em estado %s", self.conn.state.name)
            return False
        
        # Enviar SYN
        syn_pkt = Packet(
            ptype=PT_SYN,
            flags=0,
            seq=self.conn.local_seq,
            ack=0,
            wnd=0,
            payload=b"",
        )
        self.sock.sendto(syn_pkt.encode(), (self.host, self.port))
        self.conn.state = ConnectionState.SYN_SENT
        log.info("SYN enviado seq=%d → %s:%d", self.conn.local_seq, self.host, self.port)
        
        # Aguardar SYN-ACK
        try:
            raw, addr = self.sock.recvfrom(65535)
            pkt = Packet.decode(raw)
            
            if pkt.ptype == PT_SYN_ACK and pkt.ack == self.conn.local_seq:
                log.info("SYN-ACK recebido de %s, ack=%d, seq=%d", addr, pkt.ack, pkt.seq)
                self.conn.remote_seq = pkt.seq
                self.conn.remote_addr = addr
                
                # Enviar ACK final
                self.conn.local_seq += 1
                ack_pkt = Packet(
                    ptype=PT_ACK,
                    flags=0,
                    seq=self.conn.local_seq,
                    ack=pkt.seq,
                    wnd=0,
                    payload=b"",
                )
                self.sock.sendto(ack_pkt.encode(), (self.host, self.port))
                self.conn.state = ConnectionState.ESTABLISHED
                log.info("ACK enviado. Conexão ESTABLISHED")
                return True
            else:
                log.warning("Resposta inesperada: ptype=%d, ack=%d", pkt.ptype, pkt.ack)
                self.conn.state = ConnectionState.CLOSED
                return False
                
        except socket.timeout:
            log.error("Timeout aguardando SYN-ACK")
            self.conn.state = ConnectionState.CLOSED
            return False

    def send_message(self, message: str) -> None:
        """Envia mensagem (requer conexão estabelecida)."""
        if self.conn.state != ConnectionState.ESTABLISHED:
            log.error("Não é possível enviar: conexão não estabelecida (state=%s)", 
                      self.conn.state.name)
            return
        
        self.conn.local_seq += 1
        pkt = Packet(
            ptype=PT_DATA,
            flags=0,
            seq=self.conn.local_seq,
            ack=self.conn.remote_seq,
            wnd=0,
            payload=message.encode("utf-8"),
        )
        self.sock.sendto(pkt.encode(), (self.host, self.port))
        log.info("DATA enviado seq=%d len=%d", self.conn.local_seq, len(pkt.payload))

        try:
            raw, _ = self.sock.recvfrom(65535)
            ack = Packet.decode(raw)
            if ack.ptype == PT_ACK:
                log.info("ACK recebido ack=%d wnd=%d", ack.ack, ack.wnd)
                self.conn.last_ack = ack.ack
            else:
                log.warning("Pacote inesperado ptype=%d", ack.ptype)
        except socket.timeout:
            log.warning("Timeout esperando ACK")

    def close(self) -> None:
        """Encerra conexão com FIN."""
        if self.conn.state != ConnectionState.ESTABLISHED:
            log.warning("Não é possível fechar: conexão não estabelecida")
            self.sock.close()
            return
        
        self.conn.local_seq += 1
        fin_pkt = Packet(
            ptype=PT_FIN,
            flags=0,
            seq=self.conn.local_seq,
            ack=self.conn.remote_seq,
            wnd=0,
            payload=b"",
        )
        self.sock.sendto(fin_pkt.encode(), (self.host, self.port))
        self.conn.state = ConnectionState.FIN_WAIT
        log.info("FIN enviado seq=%d", self.conn.local_seq)
        
        try:
            raw, _ = self.sock.recvfrom(65535)
            pkt = Packet.decode(raw)
            if pkt.ptype == PT_ACK:
                log.info("ACK recebido para FIN. Conexão encerrada.")
            else:
                log.warning("Resposta inesperada para FIN: ptype=%d", pkt.ptype)
        except socket.timeout:
            log.warning("Timeout aguardando ACK do FIN")
        
        self.conn.state = ConnectionState.CLOSED
        self.sock.close()
