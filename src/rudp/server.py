"""Servidor RUDP com suporte a handshake, criptografia e estado de conexão."""
from __future__ import annotations
import socket
import logging
from rudp.packet import Packet, PT_DATA, PT_ACK, PT_SYN, PT_SYN_ACK, PT_FIN
from rudp.connection import Connection, ConnectionState
from rudp.crypto import CryptoContext, NoCrypto
from rudp.utils import should_drop

log = logging.getLogger("rudp.server")


class RUDPServer:
    """Servidor RUDP com gerenciamento de conexões, criptografia e 3-way handshake."""
    
    def __init__(self, bind: str, port: int, drop_prob: float = 0.0):
        self.bind = bind
        self.port = port
        self.drop_prob = drop_prob
        # Dicionário de conexões ativas: addr -> Connection
        self.connections: dict[tuple[str, int], Connection] = {}
        # Dicionário de contextos de criptografia: addr -> CryptoContext
        self.crypto_contexts: dict[tuple[str, int], CryptoContext | NoCrypto] = {}

    def _get_or_create_connection(self, addr: tuple[str, int]) -> Connection:
        """Obtém conexão existente ou cria nova."""
        if addr not in self.connections:
            self.connections[addr] = Connection(remote_addr=addr)
        return self.connections[addr]

    def _handle_syn(self, pkt: Packet, addr: tuple[str, int], sock: socket.socket) -> None:
        """Trata pacote SYN: inicia handshake e extrai chave de criptografia."""
        conn = self._get_or_create_connection(addr)
        conn.remote_seq = pkt.seq
        conn.local_seq = 0  # Poderia ser aleatório também
        conn.state = ConnectionState.SYN_RECEIVED
        
        # Extrair chave de criptografia do payload (se presente)
        if pkt.payload and len(pkt.payload) > 0:
            try:
                self.crypto_contexts[addr] = CryptoContext(pkt.payload)
                log.info("Criptografia habilitada para %s", addr)
            except Exception as e:
                log.warning("Erro ao criar contexto crypto: %s", e)
                self.crypto_contexts[addr] = NoCrypto()
        else:
            self.crypto_contexts[addr] = NoCrypto()
            log.debug("Sem criptografia para %s", addr)
        
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
            # Inicializar expected_seq para o próximo DATA esperado
            conn.expected_seq = pkt.seq + 1
            log.info("Conexão ESTABLISHED com %s (expected_seq=%d)", addr, conn.expected_seq)
        elif conn.state == ConnectionState.ESTABLISHED:
            log.debug("ACK recebido ack=%d de %s", pkt.ack, addr)

    def _handle_data(self, pkt: Packet, addr: tuple[str, int], sock: socket.socket) -> None:
        """Trata pacote DATA com entrega ordenada."""
        conn = self.connections.get(addr)
        if not conn or conn.state != ConnectionState.ESTABLISHED:
            log.warning("DATA recebido sem conexão estabelecida de %s", addr)
            return
        
        seq = pkt.seq
        
        # Verificar duplicata (seq < expected_seq)
        if seq < conn.expected_seq:
            log.debug("Duplicata descartada: seq=%d (expected=%d)", seq, conn.expected_seq)
            conn.packets_dropped += 1
            # Ainda envia ACK para confirmar recebimento
            self._send_ack(sock, addr, conn.expected_seq - 1)
            return
        
        # Pacote em ordem?
        if seq == conn.expected_seq:
            # Decifrar payload
            crypto = self.crypto_contexts.get(addr, NoCrypto())
            try:
                decrypted = crypto.decrypt(pkt.payload)
            except Exception as e:
                log.warning("Erro ao decifrar payload seq=%d: %s", seq, e)
                decrypted = pkt.payload
            
            # Entregar este pacote
            self._deliver_packet(conn, decrypted, seq, addr)
            
            # Verificar buffer de fora de ordem para pacotes consecutivos
            while conn.expected_seq in conn.out_of_order:
                payload = conn.out_of_order.pop(conn.expected_seq)
                try:
                    decrypted = crypto.decrypt(payload)
                except Exception:
                    decrypted = payload
                self._deliver_packet(conn, decrypted, conn.expected_seq, addr)
        else:
            # Fora de ordem: bufferizar (ainda cifrado)
            if seq not in conn.out_of_order:
                conn.out_of_order[seq] = pkt.payload
                log.debug("Fora de ordem: seq=%d bufferizado (expected=%d, buffer=%d)", 
                         seq, conn.expected_seq, len(conn.out_of_order))
        
        # Enviar ACK cumulativo (último em ordem)
        self._send_ack(sock, addr, conn.expected_seq - 1)
    
    def _deliver_packet(self, conn: Connection, payload: bytes, seq: int, addr: tuple = None) -> None:
        """Entrega pacote decifrado em ordem para o buffer da aplicação."""
        conn.recv_buffer += payload
        conn.packets_recv += 1
        conn.bytes_recv += len(payload)
        conn.expected_seq = seq + 1
        log.debug("Entregue seq=%d (próximo=%d, total=%d bytes)", 
                 seq, conn.expected_seq, conn.bytes_recv)
    
    def _send_ack(self, sock: socket.socket, addr: tuple[str, int], ack_num: int) -> None:
        """Envia ACK cumulativo com rwnd."""
        conn = self.connections.get(addr)
        rwnd = conn.get_rwnd() if conn else 64
        
        ack_pkt = Packet(
            ptype=PT_ACK,
            flags=0,
            seq=0,
            ack=ack_num,
            wnd=rwnd,
            payload=b"",
        )
        sock.sendto(ack_pkt.encode(), addr)
        log.debug("ACK enviado ack=%d wnd=%d", ack_num, rwnd)

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
