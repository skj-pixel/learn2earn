"""encrypt_assets.py - AES-256 文件加密 (模型/数据/敏感资源)

使用:
    python encrypt_assets.py generate-key
    python encrypt_assets.py encrypt <file>
    python encrypt_assets.py decrypt <file> <key_hex>

密钥不存于源码,运行时由 license server 通过 HTTPS 下发。
"""
import base64
import hashlib
import os
import sys
from pathlib import Path

KEY_ENV = "ASSET_DECRYPT_KEY"


def generate_key():
    return os.urandom(32)


def derive_key(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


def _xor_fallback_encrypt(data, key):
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encrypt_file(path, key):
    """AES-256-CTR 加密;无 cryptography 时回退到 XOR。"""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        nonce = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        ct = encryptor.update(path.read_bytes()) + encryptor.finalize()
        out = path.with_suffix(path.suffix + ".enc")
        out.write_bytes(b"AES1" + nonce + ct)
        return out
    except ImportError:
        out = path.with_suffix(path.suffix + ".enc")
        out.write_bytes(b"XORF" + _xor_fallback_encrypt(path.read_bytes(), key))
        return out


def decrypt_file(path, key):
    data = path.read_bytes()
    out_path = path.with_suffix("")
    if data[:4] == b"XORF":
        out_path.write_bytes(_xor_fallback_encrypt(data[4:], key))
        return out_path
    if data[:4] == b"AES1":
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        nonce, ct = data[4:20], data[20:]
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
        decryptor = cipher.decryptor()
        pt = decryptor.update(ct) + decryptor.finalize()
        out_path.write_bytes(pt)
        return out_path
    raise ValueError("unknown file format")


def decrypt_with_key_from_env(path):
    """运行时从环境变量取密钥解密"""
    key_hex = os.environ.get(KEY_ENV)
    if not key_hex:
        raise RuntimeError("env {} not set".format(KEY_ENV))
    return decrypt_file(path, bytes.fromhex(key_hex))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "generate-key":
        print(generate_key().hex())
    elif cmd == "encrypt":
        p = Path(sys.argv[2])
        k = generate_key()
        out = encrypt_file(p, k)
        print("encrypted: {} -> {}".format(p, out))
        print("key (store in license server, never in source): {}".format(k.hex()))
    elif cmd == "decrypt":
        p = Path(sys.argv[2])
        k = bytes.fromhex(sys.argv[3])
        out = decrypt_file(p, k)
        print("decrypted: {} -> {}".format(p, out))