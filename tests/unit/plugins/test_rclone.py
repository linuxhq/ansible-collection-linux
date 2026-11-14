import base64

import pytest

from ansible.errors import AnsibleFilterError

from ansible_collections.linuxhq.linux.plugins.filter import rclone_deobscure, rclone_obscure
from ansible_collections.linuxhq.linux.plugins.module_utils import rclone


@pytest.mark.parametrize("plaintext", ["", "password", "pāss🔑", b"bytes", b""])
def test_obscure_round_trip_and_determinism(plaintext):
    encoded = rclone.obscure(plaintext)
    assert encoded == rclone.obscure(plaintext)
    expected = plaintext.decode() if isinstance(plaintext, bytes) else plaintext
    assert rclone.deobscure(encoded) == expected


@pytest.mark.parametrize("function", [rclone.obscure, rclone.deobscure])
@pytest.mark.parametrize("value", ["", b""])
def test_empty_input_returns_empty_string(function, value):
    assert function(value) == "" and isinstance(function(value), str)


@pytest.mark.parametrize("value", [None, 42, [], {}])
@pytest.mark.parametrize("plugin", [rclone_obscure, rclone_deobscure])
def test_filter_invalid_type(plugin, value):
    function = next(iter(plugin.FilterModule().filters().values()))
    with pytest.raises(AnsibleFilterError, match="requires a string or bytes"):
        function(value)


@pytest.mark.parametrize("plugin", [rclone_obscure, rclone_deobscure])
def test_filter_missing_crypto(plugin, monkeypatch):
    monkeypatch.setattr(plugin, "HAS_PYCRYPTODOME", False)
    function = next(iter(plugin.FilterModule().filters().values()))
    with pytest.raises(AnsibleFilterError, match="requires the pycryptodome library"):
        function("test")


def test_filter_registration_and_round_trip():
    encoded = rclone_obscure.FilterModule().filters()["rclone_obscure"]("secret")
    assert rclone_deobscure.FilterModule().filters()["rclone_deobscure"](encoded) == "secret"


@pytest.mark.parametrize("value", ["abc=", "a+b", "a/b", "a b", "a", "abcd"])
def test_deobscure_rejects_invalid_encoding(value):
    with pytest.raises(AnsibleFilterError):
        rclone_deobscure.rclone_deobscure(value)


@pytest.mark.parametrize("function", [rclone.deobscure, rclone_deobscure.rclone_deobscure])
def test_deobscure_rejects_invalid_utf8(function):
    error = AnsibleFilterError if function is rclone_deobscure.rclone_deobscure else ValueError
    with pytest.raises(error, match="revealed value is not valid UTF-8"):
        function("AAAAAAAAAAAAAAAAAAAAAP8")


def test_base64_newlines_and_binary():
    value = b"\xff\x00\xfe"
    assert rclone.base64_urlsafe_decode("\r\n" + rclone.base64_urlsafe_encode(value) + "\n") == value


@pytest.mark.parametrize("password", ["", " ", "\t\n", "\v\f\r", "\x85\u00a0", "\u1680\u2000\u200a\u202f\u205f\u3000"])
def test_empty_config_password(password):
    with pytest.raises(ValueError, match="no characters"):
        rclone.encrypt_config(b"config", password)


@pytest.mark.parametrize("password", ["\x1f", "\x1c\x1d\x1e", " \x1f ", "\u180e", "\u200b"])
def test_config_password_trims_go_whitespace_only(password):
    assert rclone.decrypt_config(rclone.encrypt_config(b"config", password), password) == b"config"


def test_config_header_trims_go_whitespace_only():
    assert rclone.config_body("\u00a0RCLONE_ENCRYPT_V0:\u3000\nabcd") == "abcd"
    assert not rclone.is_encrypted("\x1fRCLONE_ENCRYPT_V0:\nAAAA")
    assert not rclone.is_encrypted("\x1c# comment\nRCLONE_ENCRYPT_V0:\nAAAA")


def test_config_unicode_password_normalization():
    assert rclone.config_key("é") == rclone.config_key("e\u0301")


def test_config_encryption_authenticates_password_and_ciphertext():
    content = b"[remote]\ntype = local\n"
    encrypted = rclone.encrypt_config(content, "secret", nonce=bytes(range(24)))
    assert rclone.is_encrypted(encrypted)
    assert rclone.decrypt_config(encrypted, "secret") == content
    assert rclone.decrypt_config(encrypted, "wrong") is None
    raw = bytearray(base64.b64decode(rclone.config_body(encrypted)))
    raw[-1] ^= 1
    damaged = rclone.CONFIG_MARKER + "\n" + base64.b64encode(raw).decode()
    assert rclone.decrypt_config(damaged, "secret") is None


def test_encryption_uses_fresh_nonces():
    assert rclone.encrypt_config(b"config", "secret") != rclone.encrypt_config(b"config", "secret")


@pytest.mark.parametrize("text", ["", "# comment\n; comment", "[remote]\ntype=local"])
def test_plaintext_is_not_encrypted(text):
    assert not rclone.is_encrypted(text)
    with pytest.raises(ValueError, match="not encrypted"):
        rclone.decrypt_config(text, "secret")


def test_config_header_and_wrapped_payload():
    assert rclone.config_body("# comment\n; comment\n\n RCLONE_ENCRYPT_V0: \nabcd\r\nefgh\n") == "abcdefgh"
    with pytest.raises(ValueError, match="unsupported"):
        rclone.config_body("RCLONE_ENCRYPT_V1:\nAAAA")

    with pytest.raises(ValueError, match="too short"):
        rclone.decrypt_config("RCLONE_ENCRYPT_V0:\nAAAA", "secret")


RCLONE_OBSCURED = "rBC881X_mHbsCyx3DSUR8DhvJ6EaxsNN68rbOveoFA"
RCLONE_CONFIG_PASSWORD = "vector-config-pass"
RCLONE_CONFIG = (
    "# Encrypted rclone configuration File\n\n"
    "RCLONE_ENCRYPT_V0:\n"
    "G8SDbQkHqQM2prjC2y1CdVERxlam3EJFe2BFSg1NO64uzmahBcvcL9gH0biZIXjtztDGYv2z0OHDT9QIAmv1"
)


def test_rclone_obscure_vector():
    assert rclone.deobscure(RCLONE_OBSCURED) == "vector-password"


def test_rclone_config_vector():
    assert rclone.decrypt_config(RCLONE_CONFIG, RCLONE_CONFIG_PASSWORD) == b"[vector]\ntype = local\n\n"
    assert rclone.decrypt_config(RCLONE_CONFIG, "wrong") is None


def test_config_payload_line_endings_match_rclone():
    header, payload = RCLONE_CONFIG.rsplit("\n", 1)
    wrapped = f"{header}\r\n{payload[:40]}\r\n{payload[40:]}\r\n"
    assert rclone.decrypt_config(wrapped, RCLONE_CONFIG_PASSWORD) == b"[vector]\ntype = local\n\n"


@pytest.mark.parametrize("separator", [" ", "\t", "\x0b"])
def test_config_payload_rejects_other_whitespace(separator):
    header, payload = RCLONE_CONFIG.rsplit("\n", 1)
    with pytest.raises(ValueError):
        rclone.decrypt_config(f"{header}\n{payload[:40]}{separator}{payload[40:]}", RCLONE_CONFIG_PASSWORD)


def test_config_lines_split_on_newline_only():
    assert not rclone.is_encrypted("# comment\x0bRCLONE_ENCRYPT_V0:\nAAAA")


@pytest.mark.parametrize(
    "plugin, value, expected", [(rclone_obscure, "secret", None), (rclone_deobscure, None, "secret")]
)
def test_filter_accepts_vault_encrypted_value(monkeypatch, plugin, value, expected):
    class VaultValue:
        def __init__(self, data):
            self.data = data

        def __str__(self):
            return self.data

    monkeypatch.setattr(plugin, "AnsibleVaultEncryptedUnicode", VaultValue)
    function = next(iter(plugin.FilterModule().filters().values()))
    data = value if value is not None else rclone.obscure("secret")
    result = function(VaultValue(data))
    if expected is None:
        assert rclone.deobscure(result) == "secret"
    else:
        assert result == expected


@pytest.mark.parametrize("plugin", [rclone_obscure, rclone_deobscure])
def test_filter_empty_string_passes_through(plugin):
    function = next(iter(plugin.FilterModule().filters().values()))
    assert function("") == ""
