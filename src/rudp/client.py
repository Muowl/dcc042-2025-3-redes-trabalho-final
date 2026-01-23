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

# Configurações de controle de congestionamento
INITIAL_CWND = 1
INITIAL_SSTHRESH = 64


@dataclass
class TransferStats:
    """Métricas de uma transferência de dados."""
    packets_sent: int
    bytes_sent: int
    time_ms: int
    throughput_kbps: float
    retransmissions: int = 0
    cwnd_history: list = None  # Histórico de cwnd para gráficos


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
            # Verificar controle de fluxo (rwnd)
            if self.conn.remote_wnd == 0:
                log.debug("rwnd=0, aguardando...")
                # Espera por um ACK que libere a janela
                try:
                    raw, _ = self.sock.recvfrom(65535)
                    ack = Packet.decode(raw)
                    if ack.ptype == PT_ACK:
                        self.conn.remote_wnd = ack.wnd
                        log.debug("rwnd atualizado para %d", ack.wnd)
                        if ack.wnd == 0:
                            continue
                except socket.timeout:
                    retries += 1
                    continue
            
            self.sock.sendto(pkt.encode(), (self.host, self.port))
            
            if retries > 0:
                log.debug("Retransmissão [%d/%d] seq=%d", retries, MAX_RETRIES, pkt.seq)
            
            try:
                raw, _ = self.sock.recvfrom(65535)
                ack = Packet.decode(raw)
                
                if ack.ptype == PT_ACK:
                    # Atualizar rwnd do servidor
                    self.conn.remote_wnd = ack.wnd
                    
                    # ACK cumulativo: confirma tudo até ack.ack
                    if ack.ack >= pkt.seq:
                        log.debug("ACK recebido ack=%d wnd=%d (confirmou seq=%d)", 
                                 ack.ack, ack.wnd, pkt.seq)
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
        """Fragmenta dados e envia com retransmissão e controle de congestionamento."""
        if self.conn.state != ConnectionState.ESTABLISHED:
            log.error("Não é possível enviar: conexão não estabelecida (state=%s)", 
                      self.conn.state.name)
            return TransferStats(0, 0, 0, 0.0, 0, [])
        
        start_ms = now_ms()
        packets_sent = 0
        bytes_sent = 0
        total_retransmissions = 0
        cwnd_history = []
        
        # Inicializar CC
        self.conn.cwnd = INITIAL_CWND
        self.conn.ssthresh = INITIAL_SSTHRESH
        
        # Fragmentar em chunks
        chunks = [data[i:i+PAYLOAD_SIZE] for i in range(0, len(data), PAYLOAD_SIZE)]
        total_chunks = len(chunks)
        
        log.info("Enviando %d bytes em %d pacotes (cwnd=%d, ssthresh=%d)", 
                 len(data), total_chunks, self.conn.cwnd, self.conn.ssthresh)
        
        for i, chunk in enumerate(chunks):
            # Registrar cwnd atual
            cwnd_history.append(self.conn.cwnd)
            
            # Janela efetiva: min(cwnd, rwnd)
            effective_wnd = min(self.conn.cwnd, self.conn.remote_wnd)
            log.debug("Janela efetiva: min(cwnd=%d, rwnd=%d) = %d", 
                     self.conn.cwnd, self.conn.remote_wnd, effective_wnd)
            
            self.conn.local_seq += 1
            pkt = Packet(
                ptype=PT_DATA,
                flags=0,
                seq=self.conn.local_seq,
                ack=self.conn.remote_seq,
                wnd=0,
                payload=chunk,
            )
            
            log.debug("DATA [%d/%d] seq=%d cwnd=%d", i+1, total_chunks, 
                     self.conn.local_seq, self.conn.cwnd)
            
            success, retries = self._send_packet_reliable(pkt)
            total_retransmissions += retries
            
            if success:
                packets_sent += 1
                bytes_sent += len(chunk)
                
                # Controle de congestionamento: sucesso
                if retries == 0:
                    # Sem timeout: aumentar cwnd
                    if self.conn.cwnd < self.conn.ssthresh:
                        # Slow Start: dobra (cresce exponencialmente)
                        self.conn.cwnd = min(self.conn.cwnd * 2, self.conn.ssthresh)
                        log.debug("Slow Start: cwnd → %d", self.conn.cwnd)
                    else:
                        # Congestion Avoidance: cresce linearmente
                        self.conn.cwnd += 1
                        log.debug("Congestion Avoidance: cwnd → %d", self.conn.cwnd)
                else:
                    # Houve timeout/retransmissão: reduzir
                    self.conn.ssthresh = max(self.conn.cwnd // 2, 1)
                    self.conn.cwnd = INITIAL_CWND
                    log.debug("Timeout detectado: ssthresh=%d, cwnd=%d", 
                             self.conn.ssthresh, self.conn.cwnd)
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
            cwnd_history=cwnd_history,
        )
        log.info("Transferência: %d pkts, %d bytes, %dms, %.2f KB/s, %d retx, cwnd_final=%d",
                 stats.packets_sent, stats.bytes_sent, stats.time_ms, 
                 stats.throughput_kbps, stats.retransmissions, self.conn.cwnd)
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
