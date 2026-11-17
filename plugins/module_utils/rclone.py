# Copyright: Ansible Project
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

from ansible.module_utils.common.text.converters import to_bytes, to_text

SECRET_KEY = (
    b"\x9c\x93\x5b\x48\x73\x0a\x55\x4d\x6b\xfd\x7c\x63\xc8\x86\xa9\x2b"
    b"\xd3\x90\x19\x8e\xb8\x12\x8a\xfb\xf4\xde\x16\x2b\x8b\x95\xf6\x38"
)

BASE64_URLSAFE_RAW = re.compile(r"[A-Za-z0-9_-]*\Z")

# Go's base64.StdEncoding: padded quanta only, nothing after the padding (Python 3.11 and older accept more).
# rclone decodes through base64.NewDecoder, which decodes each read on its own, so it also accepts padding that
# ends exactly where a read ends, such as at its 4096-byte buffer refill. That depends on how the file is read and
# is not emulated: padding before the end is always treated as damaged, so no file rclone rejects is accepted.
BASE64_STD = re.compile(rb"(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")

CONFIG_HEADER = "# Encrypted rclone configuration File"
CONFIG_MARKER = "RCLONE_ENCRYPT_V0:"
CONFIG_NONCE_SIZE = 24
CONFIG_TAG_SIZE = 16

# rclone reads the configuration header with bufio.Reader.ReadLine, which returns a longer line in pieces.
CONFIG_READ_SIZE = 4096

# Go's norm package inserts U+034F after this many consecutive non-starters (UAX #15 Stream-Safe Text Format).
MAX_NON_STARTERS = 30

# Hangul Jamo, whose medial vowels and final consonants Go counts as non-starters although their class is 0.
HANGUL_JAMO = range(0x1100, 0x1200)

# Other letters of class 0 that are the second element of a canonical composition, which Go also counts as
# non-starters: U+16D67 KIRAT RAI VOWEL SIGN E (Unicode 16).
BACKWARD_COMBINING = frozenset({0x16D67})

# Unicode White_Space, which Go's strings.TrimSpace removes. str.strip() also removes U+001C to U+001F.
GO_WHITESPACE = "".join(
    chr(code)
    for code in (
        0x09,
        0x0A,
        0x0B,
        0x0C,
        0x0D,
        0x20,
        0x85,
        0xA0,
        0x1680,
        *range(0x2000, 0x200B),
        0x2028,
        0x2029,
        0x202F,
        0x205F,
        0x3000,
    )
)


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
        return ""

    data = plaintext

    if isinstance(plaintext, str):
        # U+DC80 to U+DCFF stand for the bytes that are not valid UTF-8, which rclone obscure accepts; another lone
        # surrogate stands for no byte and fails to encode
        data = plaintext.encode("utf-8", "surrogateescape")

    iv = hashlib.sha256(data).digest()[: AES.block_size]

    crypter = AES.new(key=SECRET_KEY, mode=AES.MODE_CTR, initial_value=iv, nonce=b"")
    encrypted = crypter.encrypt(data)

    return base64_urlsafe_encode(iv + encrypted)


def deobscure(obscured):
    if not isinstance(obscured, (str, bytes)):
        raise TypeError(f"requires a string or bytes, got {type(obscured).__name__}")

    if not obscured:
        return ""

    if isinstance(obscured, bytes):
        obscured = obscured.decode("utf-8")

    decoded = base64_urlsafe_decode(obscured)
    iv = decoded[: AES.block_size]
    buf = decoded[AES.block_size :]

    crypter = AES.new(key=SECRET_KEY, mode=AES.MODE_CTR, initial_value=iv, nonce=b"")

    # rclone reveal returns bytes that are not valid UTF-8 as they are, which Ansible holds as U+DC80 to U+DCFF
    return crypter.decrypt(buf).decode("utf-8", "surrogateescape")


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
    value &= 0xFFFFFFFF

    return ((value << count) | (value >> (32 - count))) & 0xFFFFFFFF


def _salsa20_core(state):
    words = list(state)

    for dummy in range(10):
        for a, b, c, d in _SALSA20_QUARTERROUNDS:
            words[a] ^= _rotl32(words[b] + words[c], 7)
            words[d] ^= _rotl32(words[a] + words[b], 9)
            words[c] ^= _rotl32(words[d] + words[a], 13)
            words[b] ^= _rotl32(words[c] + words[d], 18)

    return words


def _hsalsa20(key, nonce):
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
    cipher = Salsa20.new(key=_hsalsa20(key, nonce[:16]), nonce=nonce[16:])

    mac_key = cipher.encrypt(b"\x00" * 32)
    ciphertext = cipher.encrypt(plaintext)
    tag = Poly1305.Poly1305_MAC(mac_key[:16], mac_key[16:], ciphertext).digest()

    return tag + ciphertext


def _secretbox_open(box, nonce, key):
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
    normalized = unicodedata.normalize("NFKC", password)
    seed = "[" + normalized + "][rclone-config]"

    return hashlib.sha256(seed.encode("utf-8")).digest()


def is_noncharacter(character):
    codepoint = ord(character)

    return 0xFDD0 <= codepoint <= 0xFDEF or codepoint & 0xFFFE == 0xFFFE


def is_non_starter(character):
    return (
        unicodedata.combining(character) != 0
        or unicodedata.category(character).startswith("M")
        or ord(character) in HANGUL_JAMO
        or ord(character) in BACKWARD_COMBINING
    )


def check_password_utf8(password):
    """Raise ValueError for a lone surrogate, which cannot be encoded as the UTF-8 the configuration key is made of."""
    for character in password:
        if unicodedata.category(character) == "Cs":
            raise ValueError(f"character U+{ord(character):04X} is a surrogate, which is not valid UTF-8")


def check_config_password(password):
    """Raise ValueError for a password rclone could not open a configuration encrypted with, as it reads it."""
    check_password_utf8(password)

    if not password.strip(GO_WHITESPACE):
        raise ValueError("no characters in password")

    for character in password:
        # NFKC of a code point unknown to this Python may differ from rclone's newer tables
        if unicodedata.category(character) == "Cn" and not is_noncharacter(character):
            raise ValueError(
                f"character U+{ord(character):04X} is unassigned in this Python's Unicode {unicodedata.unidata_version}, so rclone may normalize it differently"
            )

    # Python does not insert U+034F into a long run of non-starters, as rclone does. Go also counts characters
    # of class 0 that combine with the one before as non-starters, so every mark, Hangul jamo and other such
    # character is counted.
    run = 0
    for character in unicodedata.normalize("NFKD", password):
        if is_non_starter(character):
            run += 1
        else:
            run = 0

        if run > MAX_NON_STARTERS:
            raise ValueError(
                f"password has more than {MAX_NON_STARTERS} consecutive combining characters, marks or Hangul jamo, which rclone normalizes differently"
            )


def config_lines(data):
    # Yield each line as Go's bufio.Reader.ReadLine returns it, with the offset of the rest of the data.
    position = 0

    while position < len(data):
        window = data[position : position + CONFIG_READ_SIZE]
        end = window.find(b"\n")

        if end != -1:
            line, position = window[:end], position + end + 1
            line = line[:-1] if line.endswith(b"\r") else line
        elif len(window) == CONFIG_READ_SIZE:
            # a full buffer is returned as a piece of the line, keeping a final "\r" for the next piece
            line = window[:-1] if window.endswith(b"\r") else window
            position += len(line)
        else:
            line, position = window, len(data)

        yield line, position


def config_body(text):
    data = to_bytes(text, errors="surrogate_or_strict")

    for line, position in config_lines(data):
        stripped = to_text(line, errors="surrogate_or_strict").strip(GO_WHITESPACE)

        if not stripped or stripped.startswith(("#", ";")):
            continue

        if stripped == CONFIG_MARKER:
            # Go's base64 decoder skips "\r" and "\n", including those left in the rest of the marker line
            return data[position:].replace(b"\r", b"").replace(b"\n", b"")

        if stripped.startswith("RCLONE_ENCRYPT_V"):
            raise ValueError("unsupported or damaged configuration encryption header")

        return None

    return None


def is_encrypted(text):
    return config_body(text) is not None


def encrypt_config(plaintext, password, nonce=None):
    if nonce is None:
        nonce = os.urandom(CONFIG_NONCE_SIZE)

    box = _secretbox_seal(plaintext, nonce, config_key(password))
    payload = base64.b64encode(nonce + box).decode("ascii")

    return f"{CONFIG_HEADER}\n\n{CONFIG_MARKER}\n{payload}"


def decrypt_config(body, password):
    """Return the configuration sealed in body, the payload config_body() returns, or None for another password."""
    if not BASE64_STD.fullmatch(body):
        raise ValueError("configuration data is not valid base64")

    raw = base64.b64decode(body, validate=True)

    if len(raw) < CONFIG_NONCE_SIZE + CONFIG_TAG_SIZE:
        raise ValueError("configuration data too short")

    return _secretbox_open(raw[CONFIG_NONCE_SIZE:], raw[:CONFIG_NONCE_SIZE], config_key(password))
