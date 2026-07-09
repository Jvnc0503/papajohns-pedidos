import base64
import json
import hmac
import hashlib
import os

def hash_password(password: str) -> str:
    """Hashea una contraseña usando salting y PBKDF2 (nativo de Python)"""
    salt = os.urandom(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return base64.b64encode(salt + pwdhash).decode('utf-8')

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifica si la contraseña coincide con el hash guardado"""
    decoded = base64.b64decode(stored_hash)
    salt, stored_pwdhash = decoded[:16], decoded[16:]
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return pwdhash == stored_pwdhash

def b64url_encode(data: bytes) -> bytes:
    """Codificación segura para URLs requerida por JWT"""
    return base64.urlsafe_b64encode(data).replace(b'=', b'')

def generate_jwt(payload: dict, secret: str) -> str:
    """Genera un JSON Web Token (JWT) válido sin usar librerías externas"""
    header = b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_enc = b64url_encode(json.dumps(payload).encode())
    msg = header + b'.' + payload_enc
    signature = b64url_encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest())
    return (msg + b'.' + signature).decode()

def verify_jwt(token: str, secret: str) -> dict:
    """Verifica un JWT y retorna su payload. Lanza excepción si es inválido."""
    try:
        header, payload_enc, signature = token.split('.')
        msg = f"{header}.{payload_enc}".encode()
        expected_sig = b64url_encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).decode()
        
        if signature != expected_sig:
            raise ValueError("Firma de token inválida")
            
        payload_json = base64.urlsafe_b64decode(payload_enc + "==").decode()
        return json.loads(payload_json)
    except Exception:
        raise ValueError("Token malformado o inválido")
