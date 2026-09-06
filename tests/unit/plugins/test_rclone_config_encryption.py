import os
from unittest.mock import Mock

import pytest

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


@pytest.mark.parametrize("params, message", [({}, "password"), ({"password": " "}, "no characters")])
def test_password_validation(tmp_path, run_module, params, message):
    result = run_module(plugin, {"path": str(tmp_path / "config"), **params})
    assert result["failed"]
    assert message in result["msg"]


@pytest.mark.parametrize("check_mode", [False, True])
def test_missing_crypto(monkeypatch, tmp_path, run_module, check_mode):
    monkeypatch.setattr(plugin, "HAS_PYCRYPTODOME", False)
    path = tmp_path / "config"
    result = run_module(plugin, {"path": str(path), "password": "secret"}, check_mode)
    assert not path.exists()
    assert result.get("failed", False) is not check_mode
    if check_mode:
        assert result["changed"] and result["encrypted"]


def test_atomic_move_failure_removes_temporary_file(tmp_path, module_factory, invoke):
    path = tmp_path / "config"
    path.write_text("original")
    module = module_factory({"path": str(path)})
    module.atomic_move.side_effect = lambda *args: module.fail_json(msg="move failed")
    assert invoke(plugin.write_config, module, b"replacement")["failed"]
    assert path.read_text() == "original"
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_move_writes_complete_content(tmp_path, module_factory):
    path = tmp_path / "config"
    module = module_factory({"path": str(path)})
    module.atomic_move.side_effect = os.replace
    plugin.write_config(module, b"replacement")
    assert path.read_bytes() == b"replacement"
    assert list(tmp_path.iterdir()) == [path]


def test_write_failure_is_reported(monkeypatch, tmp_path, module_factory, invoke):
    module = module_factory({"path": str(tmp_path / "config")})
    monkeypatch.setattr(plugin.tempfile, "mkstemp", Mock(side_effect=OSError("permission denied")))
    result = invoke(plugin.write_config, module, b"data")
    assert result["failed"] and "permission denied" in result["msg"]
    module.atomic_move.assert_not_called()
