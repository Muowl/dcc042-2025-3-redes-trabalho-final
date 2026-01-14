from __future__ import annotations
import socket
import logging
from rudp.packet import Packet, PT_DATA, PT_ACK

log = logging.getLogger("rudp.client")

class RUDPClient:
    def __init__(self, host: str, port: int, timeout_s: float = 1.0):
        self.host = host
        self.port = port
        self.timeout_s = timeout_s

    def send_message(self, message: str) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout_s)

        seq = 1
        pkt = Packet(
            ptype=PT_DATA,
            flags=0,
            seq=seq,
            ack=0,
            wnd=0,
            payload=message.encode("utf-8"),
        )
        sock.sendto(pkt.encode(), (self.host, self.port))
        log.info("Enviado DATA seq=%d", seq)

        try:
            raw, _ = sock.recvfrom(65535)
            ack = Packet.decode(raw)
            if ack.ptype == PT_ACK:
                log.info("Recebido ACK ack=%d wnd=%d", ack.ack, ack.wnd)
            else:
                log.warning("Recebido pacote inesperado ptype=%d", ack.ptype)
        except socket.timeout:
            log.warning("Timeout esperando ACK (placeholder, ainda sem retransmissão)")
