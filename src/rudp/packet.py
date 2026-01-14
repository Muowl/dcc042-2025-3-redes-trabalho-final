from __future__ import annotations
from dataclasses import dataclass
import struct
import zlib

# Tipos de pacote (você vai expandir)
PT_DATA = 0x01
PT_ACK  = 0x02
PT_SYN  = 0x03
PT_FIN  = 0x04

# Flags (placeholder)
FL_NONE = 0x00

# Cabeçalho fixo:
# magic(2) ver(1) type(1) flags(1) hdr_len(1) seq(4) ack(4) wnd(4) payload_len(2) crc32(4)
MAGIC = b"RU"
VER = 1
_HDR_FMT = "!2sBBBBIIIH I".replace(" ", "")  # (ver nota abaixo)

# Para evitar confusão: vamos montar explicitamente:
# ! 2s B B B B I I I H I
_HDR_STRUCT = struct.Struct("!2sBBBBIIIHI")

@dataclass(frozen=True)
class Packet:
    ptype: int
    flags: int
    seq: int
    ack: int
    wnd: int
    payload: bytes

    def encode(self) -> bytes:
        payload = self.payload or b""
        hdr_len = _HDR_STRUCT.size
        payload_len = len(payload)

        # CRC vai ser calculado com crc=0 primeiro
        crc0 = 0
        header_wo_crc = _HDR_STRUCT.pack(
            MAGIC, VER, self.ptype, self.flags, hdr_len, self.seq, self.ack, self.wnd, payload_len, crc0
        )
        crc = zlib.crc32(header_wo_crc + payload) & 0xFFFFFFFF

        header = _HDR_STRUCT.pack(
            MAGIC, VER, self.ptype, self.flags, hdr_len, self.seq, self.ack, self.wnd, payload_len, crc
        )
        return header + payload

    @staticmethod
    def decode(raw: bytes) -> "Packet":
        if len(raw) < _HDR_STRUCT.size:
            raise ValueError("Pacote muito pequeno")

        (magic, ver, ptype, flags, hdr_len, seq, ack, wnd, payload_len, crc) = _HDR_STRUCT.unpack(
            raw[: _HDR_STRUCT.size]
        )

        if magic != MAGIC:
            raise ValueError("Magic inválido")
        if ver != VER:
            raise ValueError("Versão inválida")
        if hdr_len != _HDR_STRUCT.size:
            raise ValueError("Header length inválido")
        if len(raw) != _HDR_STRUCT.size + payload_len:
            raise ValueError("Tamanho inválido")

        payload = raw[_HDR_STRUCT.size :]

        # valida CRC
        header_wo_crc = _HDR_STRUCT.pack(
            MAGIC, VER, ptype, flags, hdr_len, seq, ack, wnd, payload_len, 0
        )
        calc = zlib.crc32(header_wo_crc + payload) & 0xFFFFFFFF
        if calc != crc:
            raise ValueError("CRC inválido")

        return Packet(ptype=ptype, flags=flags, seq=seq, ack=ack, wnd=wnd, payload=payload)
