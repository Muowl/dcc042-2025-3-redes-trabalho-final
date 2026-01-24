"""Módulo de criptografia para protocolo RUDP."""
from __future__ import annotations
import os
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

log = logging.getLogger("rudp.crypto")


def derive_key(shared_secret: bytes, salt: bytes) -> bytes:
    """Deriva uma chave Fernet a partir de um segredo compartilhado."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(shared_secret))
    return key


class CryptoContext:
    """Contexto de criptografia usando Fernet (AES-128-CBC)."""
    
    def __init__(self, key: bytes | None = None):
        """
        Inicializa o contexto.
        
        Args:
            key: Chave Fernet (32 bytes base64-encoded). Se None, gera uma nova.
        """
        if key is None:
            self.key = Fernet.generate_key()
            log.debug("Chave gerada: %s...", self.key[:16])
        else:
            self.key = key
        self._fernet = Fernet(self.key)
    
    @classmethod
    def from_shared_secret(cls, shared_secret: bytes, salt: bytes | None = None) -> "CryptoContext":
        """Cria contexto a partir de um segredo compartilhado."""
        if salt is None:
            salt = os.urandom(16)
        key = derive_key(shared_secret, salt)
        return cls(key)
    
    def encrypt(self, data: bytes) -> bytes:
        """Cifra dados com Fernet."""
        return self._fernet.encrypt(data)
    
    def decrypt(self, data: bytes) -> bytes:
        """Decifra dados com Fernet."""
        return self._fernet.decrypt(data)
    
    def get_key(self) -> bytes:
        """Retorna a chave para compartilhamento."""
        return self.key


class NoCrypto:
    """Contexto sem criptografia (passthrough)."""
    
    def encrypt(self, data: bytes) -> bytes:
        return data
    
    def decrypt(self, data: bytes) -> bytes:
        return data
