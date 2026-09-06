import base64

import pytest

from ansible.errors import AnsibleFilterError

from ansible_collections.linuxhq.linux.plugins.filter import rclone_deobscure, rclone_obscure
from ansible_collections.linuxhq.linux.plugins.module_utils import rclone


@pytest.mark.parametrize("plaintext", ["", "password", "pāss🔑", b"bytes", b""])
def test_obscure_round_trip_and_determinism(plaintext):
    encoded = rclone.obscure(plaintext)
    assert encoded == rclone.obscure(plaintext)
    expected = plaintext.decode() if isinstance(plaintext, bytes) and plaintext else plaintext
    assert rclone.deobscure(encoded) == expected


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


def test_base64_newlines_and_binary():
    value = b"\xff\x00\xfe"
    assert rclone.base64_urlsafe_decode("\r\n" + rclone.base64_urlsafe_encode(value) + "\n") == value


@pytest.mark.parametrize("password", ["", " ", "\t\n"])
def test_empty_config_password(password):
    with pytest.raises(ValueError, match="no characters"):
        rclone.encrypt_config(b"config", password)


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
    assert rclone.config_body("# comment\n; comment\n\n RCLONE_ENCRYPT_V0: \n abcd\n efgh ") == "abcdefgh"
    with pytest.raises(ValueError, match="unsupported"):
        rclone.config_body("RCLONE_ENCRYPT_V1:\nAAAA")

    with pytest.raises(ValueError, match="too short"):
        rclone.decrypt_config("RCLONE_ENCRYPT_V0:\nAAAA", "secret")
