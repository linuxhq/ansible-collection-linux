import os
import unicodedata
from unittest.mock import Mock

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.parameters import remove_values

from ansible_collections.linuxhq.linux.plugins.module_utils import rclone
from ansible_collections.linuxhq.linux.plugins.modules import rclone_config_encryption as plugin


@pytest.mark.parametrize("check_mode", [False, True])
def test_encrypt_plaintext(tmp_path, run_module, check_mode):
    path = tmp_path / "rclone.conf"
    content = b"[remote]\ntype=local\n"
    path.write_bytes(content)
    result = run_module(plugin, {"path": str(path), "password": "secret"}, check_mode)
    assert result["changed"] and result["encrypted"]
    if check_mode:
        assert path.read_bytes() == content
    else:
        assert rclone.decrypt_config(path.read_text(), "secret") == content


@pytest.mark.parametrize("state", ["present", "absent"])
def test_idempotent_file_keeps_contents(tmp_path, run_module, state):
    path = tmp_path / "rclone.conf"
    text = rclone.encrypt_config(b"config", "secret") if state == "present" else "config"
    path.write_text(text)
    result = run_module(plugin, {"path": str(path), "state": state, "password": "secret"})
    assert result["changed"] is False
    assert path.read_text() == text


@pytest.mark.parametrize("check_mode", [False, True])
def test_decrypt_file(tmp_path, run_module, check_mode):
    path = tmp_path / "rclone.conf"
    encrypted = rclone.encrypt_config(b"original", "secret")
    path.write_text(encrypted)
    result = run_module(plugin, {"path": str(path), "state": "absent", "password": "secret"}, check_mode)
    assert result["changed"] and not result["encrypted"]
    assert path.read_text() == (encrypted if check_mode else "original")


@pytest.mark.parametrize("state", ["present", "absent"])
def test_wrong_password_never_overwrites_file(tmp_path, run_module, state):
    path = tmp_path / "rclone.conf"
    original = rclone.encrypt_config(b"original", "secret")
    path.write_text(original)
    result = run_module(plugin, {"path": str(path), "state": state, "password": "wrong"})
    assert result["failed"]
    assert path.read_text() == original


def test_create_from_content_and_replace_encrypted_content(tmp_path, run_module):
    path = tmp_path / "rclone.conf"
    params = {"path": str(path), "password": "secret", "content": "first"}
    assert run_module(plugin, params)["changed"]
    assert rclone.decrypt_config(path.read_text(), "secret") == b"first"
    params["content"] = "second"
    assert run_module(plugin, params)["changed"]
    assert rclone.decrypt_config(path.read_text(), "secret") == b"second"
    assert not run_module(plugin, params)["changed"]


def test_missing_file_without_content_fails(tmp_path, run_module):
    result = run_module(plugin, {"path": str(tmp_path / "missing"), "password": "secret"})
    assert result["failed"]
    assert "does not exist" in result["msg"]


@pytest.mark.parametrize(
    "params, message",
    [
        ({}, "password"),
        ({"password": " "}, "no characters"),
        ({"password": "\u00a0\u3000"}, "no characters"),
        ({"password": "\x85\u2028"}, "no characters"),
    ],
)
def test_password_validation(tmp_path, run_module, params, message):
    result = run_module(plugin, {"path": str(tmp_path / "config"), **params})
    assert result["failed"]
    assert message in result["msg"]


@pytest.mark.parametrize("check_mode", [False, True])
def test_missing_crypto(monkeypatch, tmp_path, run_module, check_mode):
    monkeypatch.setattr(plugin, "HAS_PYCRYPTODOME", False)
    path = tmp_path / "config"
    path.write_text("config")
    result = run_module(plugin, {"path": str(path), "password": "secret"}, check_mode)
    assert path.read_text() == "config"
    assert result.get("failed", False) is not check_mode
    if check_mode:
        assert result["changed"] and result["encrypted"]
    else:
        assert "pycryptodome" in result["msg"]


@pytest.mark.parametrize(
    "params, message",
    [
        ({"password": "secret"}, "configuration file does not exist"),
        ({"password": " ", "content": "config"}, "invalid password for configuration file"),
        ({"password": " ", "state": "absent", "content": "config"}, "invalid password for configuration file"),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_missing_crypto_fails_like_a_real_run(monkeypatch, tmp_path, run_module, params, message, check_mode):
    monkeypatch.setattr(plugin, "HAS_PYCRYPTODOME", False)
    path = tmp_path / "config"
    result = run_module(plugin, {"path": str(path), **params}, check_mode)
    assert not path.exists()
    assert result["failed"] and message in result["msg"]


def test_invalid_password_names_path(tmp_path, run_module):
    path = tmp_path / "config"
    result = run_module(plugin, {"path": str(path), "password": " ", "content": "config"})
    assert result["msg"] == f"invalid password for configuration file {path}: no characters in password"


UNASSIGNED = "\U0001ccf0"


@pytest.mark.skipif(unicodedata.category(UNASSIGNED) != "Cn", reason="assigned in this Python's Unicode tables")
@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("crypto", [True, False])
@pytest.mark.parametrize("check_mode", [False, True])
def test_unassigned_password_character_is_rejected(monkeypatch, tmp_path, run_module, state, crypto, check_mode):
    monkeypatch.setattr(plugin, "HAS_PYCRYPTODOME", crypto)
    path = tmp_path / "config"
    params = {"path": str(path), "password": "pw" + UNASSIGNED, "state": state, "content": "config"}
    result = run_module(plugin, params, check_mode)
    assert not path.exists()
    assert result["failed"] and result["msg"] == (
        f"invalid password for configuration file {path}: character U+1CCF0 is unassigned in Unicode "
        f"{unicodedata.unidata_version}, the version of this Python, so its normalization may differ from rclone's"
    )


@pytest.mark.parametrize(
    "password",
    [
        "a" + "\u0301" * 31,
        "\u00e9" + "\u0301" * 30,
        "a" + "\u0344" * 16,
        "a" + "\u0301" * 30 + "b" + "\u0301" * 31,
        "\uac00" + "\u0301" * 30,
        "\uac01" + "\u0301" * 29,
        "a" + "\u0b3e" * 31,
        "a" + "\u1161" * 31,
        "a" + "\u11a8" * 31,
    ],
)
@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("crypto", [True, False])
@pytest.mark.parametrize("check_mode", [False, True])
def test_long_combining_run_password_is_rejected(
    monkeypatch, tmp_path, run_module, password, state, crypto, check_mode
):
    monkeypatch.setattr(plugin, "HAS_PYCRYPTODOME", crypto)
    path = tmp_path / "config"
    params = {"path": str(path), "password": password, "state": state, "content": "config"}
    result = run_module(plugin, params, check_mode)
    assert not path.exists()
    assert result["failed"] and result["msg"] == (
        f"invalid password for configuration file {path}: password has more than 30 consecutive combining "
        "characters, marks or Hangul jamo, which rclone normalizes differently"
    )


@pytest.mark.skipif(
    int(unicodedata.unidata_version.split(".", maxsplit=1)[0]) < 16, reason="U+16D67 is unassigned before Unicode 16"
)
@pytest.mark.parametrize("password", ["a" + "\U00016d67" * 31, "a" + "\U00016d68" * 16])
@pytest.mark.parametrize("check_mode", [False, True])
def test_backward_combining_letter_run_password_is_rejected(tmp_path, run_module, password, check_mode):
    path = tmp_path / "config"
    result = run_module(plugin, {"path": str(path), "password": password, "content": "config"}, check_mode)
    assert not path.exists()
    assert result["failed"] and "more than 30 consecutive" in result["msg"]


def test_every_second_element_of_a_composition_is_a_non_starter():
    # Go counts the second element of every canonical composition as a non-starter, so a Unicode upgrade that
    # adds one of class 0 outside the marks and Hangul jamo must be added to rclone.BACKWARD_COMBINING
    missing = []
    for codepoint in range(0x110000):
        decomposition = unicodedata.decomposition(chr(codepoint)).split()
        if len(decomposition) != 2 or decomposition[0].startswith("<"):
            continue

        first, second = (chr(int(part, 16)) for part in decomposition)
        if unicodedata.normalize("NFC", first + second) == chr(codepoint) and not rclone.is_non_starter(second):
            missing.append(f"U+{ord(second):04X}")

    assert not missing


@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("crypto", [True, False])
@pytest.mark.parametrize("check_mode", [False, True])
def test_surrogate_password_character_is_rejected(monkeypatch, tmp_path, run_module, state, crypto, check_mode):
    monkeypatch.setattr(plugin, "HAS_PYCRYPTODOME", crypto)
    path = tmp_path / "config"
    params = {"path": str(path), "password": "pw\ud800", "state": state, "content": "config"}
    result = run_module(plugin, params, check_mode)
    assert not path.exists()
    assert result["failed"] and result["msg"] == (
        f"invalid password for configuration file {path}: character U+D800 is a surrogate, which is not valid UTF-8"
    )


@pytest.mark.parametrize("character", [chr(0xD800), chr(0xDBFF), chr(0xDC00), chr(0xDC7F)])
@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("crypto", [True, False])
@pytest.mark.parametrize("check_mode", [False, True])
def test_surrogate_content_character_is_rejected(
    monkeypatch, tmp_path, run_module, character, state, crypto, check_mode
):
    monkeypatch.setattr(plugin, "HAS_PYCRYPTODOME", crypto)
    path = tmp_path / "config"
    params = {"path": str(path), "password": "secret", "state": state, "content": f"[remote]{character}\n"}
    result = run_module(plugin, params, check_mode)
    assert not path.exists()
    assert result["failed"] and result["msg"] == (
        f"invalid content for configuration file {path}: character U+{ord(character):04X} is a surrogate,"
        " which is not valid UTF-8"
    )


@pytest.mark.parametrize("state", ["present", "absent"])
def test_escaped_content_bytes_are_written(tmp_path, run_module, state):
    # Ansible passes bytes that are not valid UTF-8 as U+DC80 to U+DCFF
    path = tmp_path / "config"
    result = run_module(plugin, {"path": str(path), "password": "secret", "state": state, "content": "a\udcff\udc80"})
    assert result["changed"]
    written = path.read_bytes()
    assert (rclone.decrypt_config(written, "secret") if state == "present" else written) == b"a\xff\x80"


def test_backward_combining_letter_is_a_non_starter():
    # U+16D67 is unassigned on Pythons before Unicode 16, so it must be counted without the Unicode tables
    assert rclone.is_non_starter("\U00016d67")


@pytest.mark.parametrize(
    "password",
    [
        "pāss🔑",
        "e\u0301",
        "\uff21\u2460",
        "a" + "\u0301" * 30,
        "\u00e9" + "\u0301" * 29,
        "a" + "\u0344" * 15,
        "a" + "\u0301" * 30 + "b" + "\u0301" * 30,
        "a" + "\u0b3e" * 30,
        "pw\uffff",
        "pw\ufdd0",
        "pw\U0010fffe",
    ],
)
def test_non_ascii_password_is_accepted(tmp_path, run_module, password):
    path = tmp_path / "rclone.conf"
    result = run_module(plugin, {"path": str(path), "password": password, "content": "config"})
    assert result["changed"] and not result.get("failed")
    assert rclone.decrypt_config(path.read_text(), password) == b"config"


def test_atomic_move_failure_removes_temporary_file(tmp_path, module_factory, invoke):
    path = tmp_path / "config"
    path.write_text("original")
    module = module_factory({"path": str(path), "unsafe_writes": False})
    module.atomic_move.side_effect = lambda *args, **kwargs: module.fail_json(msg="move failed")
    assert invoke(plugin.write_config, module, str(path), b"replacement")["failed"]
    assert path.read_text() == "original"
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_move_writes_complete_content(tmp_path, module_factory):
    path = tmp_path / "config"
    module = module_factory({"path": str(path), "mode": None, "unsafe_writes": False})
    module.atomic_move.side_effect = lambda src, dest, **kwargs: os.replace(src, dest)
    plugin.write_config(module, str(path), b"replacement")
    assert path.read_bytes() == b"replacement"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("unsafe_writes", [False, True])
def test_write_failure_is_reported(monkeypatch, tmp_path, module_factory, invoke, unsafe_writes):
    module = module_factory({"path": str(tmp_path / "config"), "unsafe_writes": unsafe_writes})
    monkeypatch.setattr(plugin.tempfile, "mkstemp", Mock(side_effect=OSError("permission denied")))
    result = invoke(plugin.write_config, module, str(tmp_path / "config"), b"data")
    assert result["failed"] and "permission denied" in result["msg"]
    module.atomic_move.assert_not_called()


@pytest.fixture
def unwritable_directory(monkeypatch, tmp_path):
    """Refuse temporary files in the configuration directory only, like a directory the user cannot write."""
    directory = tmp_path / "config"
    directory.mkdir()
    mkstemp = plugin.tempfile.mkstemp

    def refuse_config_directory(*args, **kwargs):
        if os.path.realpath(kwargs.get("dir", "")) == os.path.realpath(directory):
            raise PermissionError(13, "Permission denied", str(directory))

        return mkstemp(*args, **kwargs)

    monkeypatch.setattr(plugin.tempfile, "mkstemp", refuse_config_directory)
    return directory


def test_unsafe_writes_stages_the_file_outside_an_unwritable_directory(tmp_path, module_factory, unwritable_directory):
    path = unwritable_directory / "rclone.conf"
    path.write_text("original")
    staging = tmp_path / "staging"
    staging.mkdir()
    module = module_factory({"path": str(path), "unsafe_writes": True})
    module.tmpdir = str(staging)
    moves = []

    def move(src, dest, **kwargs):
        moves.append((os.path.dirname(src), kwargs))
        with open(src, "rb") as source, open(dest, "wb") as target:
            target.write(source.read())

    module.atomic_move.side_effect = move
    plugin.write_config(module, str(path), b"replacement")
    assert moves == [(str(staging), {"unsafe_writes": True})]
    assert path.read_bytes() == b"replacement"
    assert list(staging.iterdir()) == []


def test_unwritable_directory_without_unsafe_writes_fails(module_factory, invoke, unwritable_directory):
    path = unwritable_directory / "rclone.conf"
    path.write_text("original")
    module = module_factory({"path": str(path), "unsafe_writes": False})
    result = invoke(plugin.write_config, module, str(path), b"replacement")
    assert result["failed"] and "Permission denied" in result["msg"] and str(path) in result["msg"]
    module.atomic_move.assert_not_called()
    assert path.read_text() == "original"


@pytest.mark.parametrize("payload", ["AAAA", "!!!!", "AAAA AAAA", ""])
@pytest.mark.parametrize("state", ["present", "absent"])
def test_damaged_payload_is_replaced_by_content(tmp_path, run_module, payload, state):
    path = tmp_path / "rclone.conf"
    path.write_text(f"{rclone.CONFIG_MARKER}\n{payload}")
    result = run_module(plugin, {"path": str(path), "password": "secret", "content": "new", "state": state})
    assert result["changed"] and not result.get("failed")
    if state == "present":
        assert rclone.decrypt_config(path.read_text(), "secret") == b"new"
    else:
        assert path.read_text() == "new"


@pytest.mark.parametrize("payload", ["AAAA", "!!!!"])
@pytest.mark.parametrize("state, message", [("present", "different password"), ("absent", "unable to decrypt")])
def test_damaged_payload_without_content_fails_clearly(tmp_path, run_module, payload, state, message):
    path = tmp_path / "rclone.conf"
    original = f"{rclone.CONFIG_MARKER}\n{payload}"
    path.write_text(original)
    result = run_module(plugin, {"path": str(path), "password": "secret", "state": state})
    assert result["failed"] and message in result["msg"] and str(path) in result["msg"]
    assert path.read_text() == original


@pytest.mark.parametrize("state", ["present", "absent"])
def test_wrong_password_message_names_path(tmp_path, run_module, state):
    path = tmp_path / "rclone.conf"
    path.write_text(rclone.encrypt_config(b"original", "secret"))
    result = run_module(plugin, {"path": str(path), "state": state, "password": "wrong"})
    assert result["failed"] and str(path) in result["msg"]


def test_unsupported_encryption_message_names_path(tmp_path, run_module):
    path = tmp_path / "rclone.conf"
    path.write_text("RCLONE_ENCRYPT_V1:\nAAAA")
    result = run_module(plugin, {"path": str(path), "password": "secret"})
    assert result["failed"] and "unsupported" in result["msg"] and str(path) in result["msg"]


@pytest.mark.parametrize("header", ["RCLONE_ENCRYPT_V0:", "RCLONE_ENCRYPT_V1:"])
@pytest.mark.parametrize("with_content, crypto", [(False, True), (True, True), (True, False)])
@pytest.mark.parametrize("check_mode", [False, True])
def test_absent_plain_text_with_encryption_header_fails_before_writing(
    monkeypatch, tmp_path, run_module, header, with_content, crypto, check_mode
):
    monkeypatch.setattr(plugin, "HAS_PYCRYPTODOME", crypto)
    path = tmp_path / "rclone.conf"
    plain = f"# comment\n\n{header}\nAAAA\n"
    params = {"path": str(path), "state": "absent", "password": "secret"}
    if with_content:
        params["content"] = plain
        original = None
    else:
        original = rclone.encrypt_config(plain.encode(), "secret")
        path.write_text(original)

    result = run_module(plugin, params, check_mode)
    assert result["failed"] and "encryption header" in result["msg"] and str(path) in result["msg"]
    if original is None:
        assert sorted(tmp_path.iterdir()) == []
    else:
        assert sorted(tmp_path.iterdir()) == [path]
        assert path.read_text() == original


@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("mode, expected", [(None, 0o600), ("0640", 0o640)])
def test_created_file_mode(tmp_path, run_module, state, mode, expected):
    path = tmp_path / "rclone.conf"
    params = {"path": str(path), "password": "secret", "content": "config", "state": state}
    if mode is not None:
        params["mode"] = mode

    assert run_module(plugin, params)["changed"]
    assert path.stat().st_mode & 0o777 == expected


@pytest.mark.parametrize("password", ["\x1f", "\x1c\x1d\x1e"])
def test_password_of_separator_characters_is_accepted(tmp_path, run_module, password):
    path = tmp_path / "rclone.conf"
    result = run_module(plugin, {"path": str(path), "password": password, "content": "config"})
    assert result["changed"] and not result.get("failed")
    assert rclone.decrypt_config(path.read_text(), password) == b"config"


@pytest.fixture
def recorded_moves(monkeypatch):
    """Wrap the real atomic_move to record the arguments and the mode the file has right after it."""
    moves = []
    original = basic.AnsibleModule.atomic_move

    def atomic_move(self, src, dest, *args, **kwargs):
        result = original(self, src, dest, *args, **kwargs)
        moves.append({"kwargs": kwargs, "mode": os.stat(dest).st_mode & 0o777})
        return result

    monkeypatch.setattr(basic.AnsibleModule, "atomic_move", atomic_move)
    umask = os.umask(0o022)
    yield moves
    os.umask(umask)


@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("mode, expected", [(None, 0o600), ("0640", 0o640)])
def test_created_file_is_private_from_the_start(tmp_path, run_module, recorded_moves, state, mode, expected):
    path = tmp_path / "rclone.conf"
    params = {"path": str(path), "password": "secret", "content": "config", "state": state}
    if mode is not None:
        params["mode"] = mode

    assert run_module(plugin, params)["changed"]
    assert [move["mode"] for move in recorded_moves] == [0o600]
    assert path.stat().st_mode & 0o777 == expected
    assert os.umask(0o022) == 0o022


def test_existing_file_keeps_its_mode_through_the_move(tmp_path, run_module, recorded_moves):
    path = tmp_path / "rclone.conf"
    path.write_text("config")
    path.chmod(0o644)
    assert run_module(plugin, {"path": str(path), "password": "secret"})["changed"]
    assert [move["mode"] for move in recorded_moves] == [0o644]


@pytest.mark.parametrize("unsafe_writes", [False, True])
def test_unsafe_writes_is_passed_to_atomic_move(tmp_path, run_module, recorded_moves, unsafe_writes):
    path = tmp_path / "rclone.conf"
    params = {"path": str(path), "password": "secret", "content": "config", "unsafe_writes": unsafe_writes}
    assert run_module(plugin, params)["changed"]
    assert [move["kwargs"].get("unsafe_writes") for move in recorded_moves] == [unsafe_writes]


def test_existing_file_keeps_mode(tmp_path, run_module):
    path = tmp_path / "rclone.conf"
    path.write_text("config")
    path.chmod(0o644)
    assert run_module(plugin, {"path": str(path), "password": "secret"})["changed"]
    assert path.stat().st_mode & 0o777 == 0o644


@pytest.mark.parametrize("state", ["present", "absent"])
def test_symlink_target_is_written(tmp_path, run_module, state):
    target = tmp_path / "target.conf"
    target.write_text(rclone.encrypt_config(b"old", "secret"))
    link = tmp_path / "rclone.conf"
    link.symlink_to(target)
    result = run_module(plugin, {"path": str(link), "password": "secret", "content": "new", "state": state})
    assert result["changed"] and result["path"] == str(link)
    assert link.is_symlink()
    text = target.read_text()
    assert (rclone.decrypt_config(text, "secret") if state == "present" else text.encode()) == b"new"


def test_content_is_kept_out_of_logs(monkeypatch, tmp_path, run_module):
    captured = {}
    original = basic.AnsibleModule.exit_json

    def exit_json(self, **values):
        captured.update(no_log_values=set(self.no_log_values))
        original(self, **values)

    monkeypatch.setattr(basic.AnsibleModule, "exit_json", exit_json)
    path = tmp_path / "rclone.conf"
    run_module(plugin, {"path": str(path), "password": "secret", "content": "token = sensitive"}, True)
    assert "token = sensitive" in captured["no_log_values"]


@pytest.mark.parametrize("state", ["present", "absent"])
def test_diff_of_non_utf8_configuration_is_valid_text(tmp_path, run_module, state):
    path = tmp_path / "rclone.conf"
    path.write_bytes(b"[remote]\nkey = \xff\n")
    result = run_module(plugin, {"path": str(path), "password": "secret", "state": state, "_ansible_diff": True})
    for side in ("before", "after"):
        assert result["diff"][side] == "[remote]\nkey = \ufffd\n"
        result["diff"][side].encode("utf-8")


@pytest.mark.parametrize(
    "content,after",
    [
        ("[remote]\nkey = sensitive\n", "VALUE_SPECIFIED_IN_NO_LOG_PARAMETER"),
        ("[remote]\nkey = \udce9\n", "[remote]\nkey = \ufffd\n"),
    ],
)
def test_diff_after_side_masks_content_unless_it_holds_escaped_bytes(monkeypatch, tmp_path, run_module, content, after):
    # Ansible masks the no_log content where it appears, which U+FFFD in place of a byte no longer matches
    original = basic.AnsibleModule.exit_json
    monkeypatch.setattr(
        basic.AnsibleModule,
        "exit_json",
        lambda self, **values: original(self, **remove_values(values, self.no_log_values)),
    )
    path = tmp_path / "rclone.conf"
    params = {"path": str(path), "password": "secret", "content": content, "_ansible_diff": True}
    result = run_module(plugin, params, True)
    assert result["changed"] and result["diff"]["after"] == after
