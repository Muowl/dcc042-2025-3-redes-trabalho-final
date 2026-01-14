from __future__ import annotations

class CryptoContext:
    """
    Placeholder de criptografia.
    """
    def __init__(self, key: bytes | None = None):
        self.key = key or b""

    def encrypt(self, data: bytes) -> bytes:
        # TODO: implementar criptografia real
        return data

    def decrypt(self, data: bytes) -> bytes:
        # TODO: implementar descriptografia real
        return data
