# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import base64
import hashlib
import re

try:
    from Crypto.Cipher import AES

    HAS_PYCRYPTODOME = True
except ImportError:
    HAS_PYCRYPTODOME = False

SECRET_KEY = (
    b"\x9c\x93\x5b\x48\x73\x0a\x55\x4d\x6b\xfd\x7c\x63\xc8\x86\xa9\x2b"
    b"\xd3\x90\x19\x8e\xb8\x12\x8a\xfb\xf4\xde\x16\x2b\x8b\x95\xf6\x38"
)

BASE64_URLSAFE_RAW = re.compile(r"[A-Za-z0-9_-]*\Z")


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
        raise TypeError("requires a string or bytes, got %s" % type(plaintext).__name__)

    if not plaintext:
        return plaintext

    data = plaintext.encode("utf-8") if isinstance(plaintext, str) else plaintext

    iv = hashlib.sha256(data).digest()[: AES.block_size]

    crypter = AES.new(key=SECRET_KEY, mode=AES.MODE_CTR, initial_value=iv, nonce=b"")
    encrypted = crypter.encrypt(data)

    return base64_urlsafe_encode(iv + encrypted)


def deobscure(obscured):
    if not isinstance(obscured, (str, bytes)):
        raise TypeError("requires a string or bytes, got %s" % type(obscured).__name__)

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
