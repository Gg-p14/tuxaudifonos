import hashlib
import hmac
import os
import time
from collections import defaultdict, deque

ITERACIONES = 240_000
VENTANA_SEG = 15 * 60
MAX_INTENTOS = 5
_intentos: dict[str, deque] = defaultdict(deque)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    clave = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERACIONES)
    return salt.hex() + ":" + clave.hex()


def verify_password(password: str, almacenado: str) -> bool:
    try:
        salt_hex, esperado = almacenado.split(":")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), ITERACIONES).hex()
        return hmac.compare_digest(actual, esperado)
    except (ValueError, AttributeError):
        return False


def _limpiar(clave: str):
    ahora = time.time()
    q = _intentos[clave]
    while q and ahora - q[0] > VENTANA_SEG:
        q.popleft()


def login_bloqueado(clave: str) -> bool:
    _limpiar(clave)
    return len(_intentos[clave]) >= MAX_INTENTOS


def registrar_fallo(clave: str):
    _limpiar(clave)
    _intentos[clave].append(time.time())


def reiniciar_intentos(clave: str):
    _intentos.pop(clave, None)
