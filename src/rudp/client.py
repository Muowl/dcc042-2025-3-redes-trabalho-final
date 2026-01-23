"""Cliente RUDP com suporte a handshake, envio de múltiplos pacotes, métricas e retransmissão."""
from __future__ import annotations
import socket
import logging
import random
from dataclasses import dataclass
from rudp.packet import Packet, PT_DATA, PT_ACK, PT_SYN, PT_SYN_ACK, PT_FIN, PAYLOAD_SIZE
from rudp.connection import Connection, ConnectionState
from rudp.utils import now_ms

log = logging.getLogger("rudp.client")

# Configurações de retransmissão
MAX_RETRIES = 5  # Máximo de retransmissões por pacote


@dataclass
class TransferStats:
    """Métricas de uma transferência de dados."""
    packets_sent: int
    bytes_sent: int
    time_ms: int
    throughput_kbps: float
    retransmissions: int = 0


class RUDPClient:
    """Cliente RUDP com 3-way handshake, envio de múltiplos pacotes e retransmissão."""
    
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

    def _send_packet_reliable(self, pkt: Packet) -> tuple[bool, int]:
        """Envia pacote com retransmissão. Retorna (sucesso, retransmissões)."""
        retries = 0
        
        while retries <= MAX_RETRIES:
            self.sock.sendto(pkt.encode(), (self.host, self.port))
            
            if retries > 0:
                log.debug("Retransmissão [%d/%d] seq=%d", retries, MAX_RETRIES, pkt.seq)
            
            try:
                raw, _ = self.sock.recvfrom(65535)
                ack = Packet.decode(raw)
                
                if ack.ptype == PT_ACK:
                    # ACK cumulativo: confirma tudo até ack.ack
                    if ack.ack >= pkt.seq:
                        log.debug("ACK recebido ack=%d (confirmou seq=%d)", ack.ack, pkt.seq)
                        self.conn.last_ack = ack.ack
                        return True, retries
                    else:
                        log.debug("ACK parcial ack=%d (esperava >= %d)", ack.ack, pkt.seq)
                else:
                    log.warning("Pacote inesperado ptype=%d", ack.ptype)
                    
            except socket.timeout:
                retries += 1
                if retries <= MAX_RETRIES:
                    log.debug("Timeout para seq=%d, tentativa %d/%d", pkt.seq, retries, MAX_RETRIES)
        
        log.warning("Falha após %d retransmissões para seq=%d", MAX_RETRIES, pkt.seq)
        return False, retries

    def send_data(self, data: bytes) -> TransferStats:
        """Fragmenta dados e envia em múltiplos pacotes com retransmissão."""
        if self.conn.state != ConnectionState.ESTABLISHED:
            log.error("Não é possível enviar: conexão não estabelecida (state=%s)", 
                      self.conn.state.name)
            return TransferStats(0, 0, 0, 0.0, 0)
        
        start_ms = now_ms()
        packets_sent = 0
        bytes_sent = 0
        total_retransmissions = 0
        
        # Fragmentar em chunks
        chunks = [data[i:i+PAYLOAD_SIZE] for i in range(0, len(data), PAYLOAD_SIZE)]
        total_chunks = len(chunks)
        
        log.info("Enviando %d bytes em %d pacotes", len(data), total_chunks)
        
        for i, chunk in enumerate(chunks):
            self.conn.local_seq += 1
            pkt = Packet(
                ptype=PT_DATA,
                flags=0,
                seq=self.conn.local_seq,
                ack=self.conn.remote_seq,
                wnd=0,
                payload=chunk,
            )
            
            log.debug("DATA [%d/%d] seq=%d len=%d", i+1, total_chunks, self.conn.local_seq, len(chunk))
            
            success, retries = self._send_packet_reliable(pkt)
            total_retransmissions += retries
            
            if success:
                packets_sent += 1
                bytes_sent += len(chunk)
            else:
                log.error("Falha ao enviar pacote seq=%d, abortando", self.conn.local_seq)
                break
        
        elapsed_ms = now_ms() - start_ms
        throughput = (bytes_sent / 1024) / (elapsed_ms / 1000) if elapsed_ms > 0 else 0.0
        
        stats = TransferStats(
            packets_sent=packets_sent,
            bytes_sent=bytes_sent,
            time_ms=elapsed_ms,
            throughput_kbps=throughput,
            retransmissions=total_retransmissions,
        )
        log.info("Transferência: %d pacotes, %d bytes, %dms, %.2f KB/s, %d retransmissões",
                 stats.packets_sent, stats.bytes_sent, stats.time_ms, 
                 stats.throughput_kbps, stats.retransmissions)
        return stats

    def send_message(self, message: str) -> None:
        """Envia mensagem (wrapper para send_data)."""
        self.send_data(message.encode("utf-8"))

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
