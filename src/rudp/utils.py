from __future__ import annotations
import time
import random

def now_ms() -> int:
    return int(time.time() * 1000)

def should_drop(p: float) -> bool:
    """Retorna True se deve descartar (simular perda). p entre 0 e 1."""
    if p <= 0:
        return False
    if p >= 1:
        return True
    return random.random() < p
