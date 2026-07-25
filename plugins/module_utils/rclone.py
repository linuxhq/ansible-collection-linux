# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import base64
import hashlib
import os
import re
import struct
import unicodedata

try:
    from Crypto.Cipher import AES, Salsa20
    from Crypto.Hash import Poly1305

    HAS_PYCRYPTODOME = True
except ImportError:
    try:
        from Cryptodome.Cipher import AES, Salsa20
        from Cryptodome.Hash import Poly1305

        HAS_PYCRYPTODOME = True
    except ImportError:
        HAS_PYCRYPTODOME = False

SECRET_KEY = (
    b"\x9c\x93\x5b\x48\x73\x0a\x55\x4d\x6b\xfd\x7c\x63\xc8\x86\xa9\x2b"
    b"\xd3\x90\x19\x8e\xb8\x12\x8a\xfb\xf4\xde\x16\x2b\x8b\x95\xf6\x38"
)

BASE64_URLSAFE_RAW = re.compile(r"[A-Za-z0-9_-]*\Z")

CONFIG_HEADER = "# Encrypted rclone configuration File"
CONFIG_MARKER = "RCLONE_ENCRYPT_V0:"
CONFIG_NONCE_SIZE = 24
CONFIG_TAG_SIZE = 16


def base64_urlsafe_encode(data):
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def base64_urlsafe_decode(string):
    string = string.replace("\r", "").replace("\n", "")

    if not BASE64_URLSAFE_RAW.match(string):
        raise ValueError("value is not unpadded base64url encoded")

    padding = (4 - len(string) % 4) % 4
    return base64.urlsafe_b64decode(string + ("=" * padding))


def obscure(plaintext):
    if not isinstance(plaintext, (str, bytes)):
        raise TypeError(f"requires a string or bytes, got {type(plaintext).__name__}")

    if not plaintext:
        return plaintext

    data = plaintext.encode("utf-8") if isinstance(plaintext, str) else plaintext

    iv = hashlib.sha256(data).digest()[: AES.block_size]

    crypter = AES.new(key=SECRET_KEY, mode=AES.MODE_CTR, initial_value=iv, nonce=b"")
    encrypted = crypter.encrypt(data)

    return base64_urlsafe_encode(iv + encrypted)


def deobscure(obscured):
    if not isinstance(obscured, (str, bytes)):
        raise TypeError(f"requires a string or bytes, got {type(obscured).__name__}")

    if not obscured:
        return obscured

    if isinstance(obscured, bytes):
        obscured = obscured.decode("utf-8")

    decoded = base64_urlsafe_decode(obscured)

    if len(decoded) < AES.block_size:
        raise ValueError("value is too short to contain an IV")

    iv = decoded[: AES.block_size]
    buf = decoded[AES.block_size :]

    crypter = AES.new(key=SECRET_KEY, mode=AES.MODE_CTR, initial_value=iv, nonce=b"")
    return crypter.decrypt(buf).decode("utf-8")


_SALSA20_QUARTERROUNDS = (
    (4, 0, 12, 8),
    (9, 5, 1, 13),
    (14, 10, 6, 2),
    (3, 15, 11, 7),
    (1, 0, 3, 2),
    (6, 5, 4, 7),
    (11, 10, 9, 8),
    (12, 15, 14, 13),
)

_SALSA20_CONSTANTS = (0x61707865, 0x3320646E, 0x79622D32, 0x6B206574)


def _rotl32(value, count):
    """Rotate a 32-bit word left."""
    value &= 0xFFFFFFFF

    return ((value << count) | (value >> (32 - count))) & 0xFFFFFFFF


def _salsa20_core(state):
    """Run the Salsa20 core over 16 words, omitting the final feedforward."""
    words = list(state)

    for dummy in range(10):
        for a, b, c, d in _SALSA20_QUARTERROUNDS:
            words[a] ^= _rotl32(words[b] + words[c], 7)
            words[d] ^= _rotl32(words[a] + words[b], 9)
            words[c] ^= _rotl32(words[d] + words[a], 13)
            words[b] ^= _rotl32(words[c] + words[d], 18)

    return words


def _hsalsa20(key, nonce):
    """Derive the XSalsa20 subkey, the HSalsa20 step NaCl secretbox begins with."""
    k = struct.unpack("<8I", key)
    n = struct.unpack("<4I", nonce)

    words = _salsa20_core(
        [
            _SALSA20_CONSTANTS[0],
            k[0],
            k[1],
            k[2],
            k[3],
            _SALSA20_CONSTANTS[1],
            n[0],
            n[1],
            n[2],
            n[3],
            _SALSA20_CONSTANTS[2],
            k[4],
            k[5],
            k[6],
            k[7],
            _SALSA20_CONSTANTS[3],
        ]
    )

    return struct.pack(
        "<8I",
        words[0],
        words[5],
        words[10],
        words[15],
        words[6],
        words[7],
        words[8],
        words[9],
    )


def _secretbox_seal(plaintext, nonce, key):
    """Seal plaintext with XSalsa20-Poly1305, returning the tag followed by ciphertext."""
    cipher = Salsa20.new(key=_hsalsa20(key, nonce[:16]), nonce=nonce[16:])

    mac_key = cipher.encrypt(b"\x00" * 32)
    ciphertext = cipher.encrypt(plaintext)
    tag = Poly1305.Poly1305_MAC(mac_key[:16], mac_key[16:], ciphertext).digest()

    return tag + ciphertext


def _secretbox_open(box, nonce, key):
    """Open an XSalsa20-Poly1305 box, returning None when authentication fails."""
    cipher = Salsa20.new(key=_hsalsa20(key, nonce[:16]), nonce=nonce[16:])

    mac_key = cipher.encrypt(b"\x00" * 32)
    tag = box[:CONFIG_TAG_SIZE]
    ciphertext = box[CONFIG_TAG_SIZE:]

    try:
        Poly1305.Poly1305_MAC(mac_key[:16], mac_key[16:], ciphertext).verify(tag)
    except ValueError:
        return None

    return cipher.encrypt(ciphertext)


def config_key(password):
    """Derive the 32 byte configuration key rclone hashes out of the password."""
    normalized = unicodedata.normalize("NFKC", password)
    seed = "[" + normalized + "][rclone-config]"

    return hashlib.sha256(seed.encode("utf-8")).digest()


def check_config_password(password):
    """Raise when the password is one rclone itself refuses."""
    if not password or not password.strip():
        raise ValueError("no characters in password")

    return password


def config_body(text):
    """Return the base64 payload of an encrypted configuration, or None when plain."""
    lines = text.splitlines()

    for index, line in enumerate(lines):
        stripped = line.strip()

        if not stripped or stripped.startswith(("#", ";")):
            continue
        if stripped == CONFIG_MARKER:
            return "".join(item.strip() for item in lines[index + 1 :])
        if stripped.startswith("RCLONE_ENCRYPT_V"):
            raise ValueError(
                "unsupported configuration encryption, update rclone for support"
            )

        return None

    return None


def is_encrypted(text):
    """Report whether the configuration text carries the rclone encryption marker."""
    return config_body(text) is not None


def encrypt_config(plaintext, password, nonce=None):
    """Wrap configuration bytes in rclone's RCLONE_ENCRYPT_V0 envelope."""
    check_config_password(password)

    if nonce is None:
        nonce = os.urandom(CONFIG_NONCE_SIZE)

    box = _secretbox_seal(plaintext, nonce, config_key(password))
    payload = base64.b64encode(nonce + box).decode("ascii")

    return f"{CONFIG_HEADER}\n\n{CONFIG_MARKER}\n{payload}"


def decrypt_config(text, password):
    """Unwrap an encrypted configuration, returning None when the password is wrong."""
    check_config_password(password)

    body = config_body(text)

    if body is None:
        raise ValueError("configuration is not encrypted")

    raw = base64.b64decode(body)

    if len(raw) < CONFIG_NONCE_SIZE + CONFIG_TAG_SIZE:
        raise ValueError("configuration data too short")

    return _secretbox_open(
        raw[CONFIG_NONCE_SIZE:], raw[:CONFIG_NONCE_SIZE], config_key(password)
    )
