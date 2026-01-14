from __future__ import annotations
import socket
import logging
from rudp.packet import Packet, PT_DATA, PT_ACK
from rudp.utils import should_drop

log = logging.getLogger("rudp.server")

class RUDPServer:
    def __init__(self, bind: str, port: int, drop_prob: float = 0.0):
        self.bind = bind
        self.port = port
        self.drop_prob = drop_prob

    def run(self) -> None:
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

            if pkt.ptype == PT_DATA:
                log.info("DATA de %s seq=%d len=%d", addr, pkt.seq, len(pkt.payload))

                # ACK simples (aqui é só esqueleto; depois vira ACK cumulativo/RS)
                ack_pkt = Packet(
                    ptype=PT_ACK,
                    flags=0,
                    seq=0,
                    ack=pkt.seq,   # placeholder
                    wnd=64,        # placeholder: janela do receptor
                    payload=b"",
                )
                sock.sendto(ack_pkt.encode(), addr)

            else:
                log.info("Recebido ptype=%d de %s", pkt.ptype, addr)
