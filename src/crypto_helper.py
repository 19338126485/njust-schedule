"""
课表数据加密/解密工具

格式（envelope，JSON）：
{
    "v": 1,
    "alg": "AES-GCM",
    "kdf": "PBKDF2-SHA256",
    "iter": 200000,
    "salt": "<base64>",   # 16 字节随机盐
    "iv": "<base64>",     # 12 字节随机 IV
    "data": "<base64>"    # AES-256-GCM 密文（含认证标签）
}

密钥由密码经 PBKDF2-SHA256（200000 次迭代）派生 32 字节。
前端 webapp/js/app.js 用 WebCrypto 实现同样的格式，二者互通。
"""

import base64
import json
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITERATIONS = 200_000
SALT_LEN = 16
IV_LEN = 12
KEY_LEN = 32


def _derive_key(password: str, salt: bytes, iterations: int) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_data(plain_obj, password: str) -> dict:
    """把任意可 JSON 序列化的对象加密成 envelope dict。每次调用都用新随机 salt/iv。"""
    salt = os.urandom(SALT_LEN)
    iv = os.urandom(IV_LEN)
    key = _derive_key(password, salt, ITERATIONS)
    plaintext = json.dumps(plain_obj, ensure_ascii=False).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(iv, plaintext, None)

    b64 = lambda b: base64.b64encode(b).decode("ascii")  # noqa: E731
    return {
        "v": 1,
        "alg": "AES-GCM",
        "kdf": "PBKDF2-SHA256",
        "iter": ITERATIONS,
        "salt": b64(salt),
        "iv": b64(iv),
        "data": b64(ciphertext),
    }


def decrypt_data(envelope: dict, password: str):
    """解密 envelope，返回原始对象。密码错误时抛出 cryptography.exceptions.InvalidTag。"""
    salt = base64.b64decode(envelope["salt"])
    iv = base64.b64decode(envelope["iv"])
    ciphertext = base64.b64decode(envelope["data"])
    iterations = int(envelope["iter"])
    key = _derive_key(password, salt, iterations)
    plaintext = AESGCM(key).decrypt(iv, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))
