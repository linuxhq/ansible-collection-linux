import os
import signal
from pathlib import Path
from unittest.mock import Mock

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.parameters import remove_values

from ansible_collections.linuxhq.linux.plugins.module_utils import rclone
from ansible_collections.linuxhq.linux.plugins.modules import rclone_config_encryption as plugin


def decrypt(text, password):
    """Decrypt a configuration file's text as the module does, from the payload after its header."""
    return rclone.decrypt_config(rclone.config_body(text), password)


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
        assert decrypt(path.read_text(), "secret") == content


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
    assert decrypt(path.read_text(), "secret") == b"first"
    params["content"] = "second"
    assert run_module(plugin, params)["changed"]
    assert decrypt(path.read_text(), "secret") == b"second"
    assert not run_module(plugin, params)["changed"]


def test_missing_file_without_content_fails(tmp_path, run_module):
    result = run_module(plugin, {"path": str(tmp_path / "missing"), "password": "secret"})
    assert result["failed"]
    assert "does not exist" in result["msg"]


def test_password_required_when_present(tmp_path, run_module):
    result = run_module(plugin, {"path": str(tmp_path / "config")})
    assert result["failed"]
    assert "password" in result["msg"]


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
        assert result["msg"].startswith(f"unable to manage configuration file {path}: ")
        assert "(pycryptodome or pycryptodomex)" in result["msg"]


@pytest.mark.parametrize(
    "params, message",
    [
        ({"password": "secret"}, "configuration file does not exist"),
        ({"password": "pw\ud800", "state": "absent", "content": "config"}, "invalid password for configuration file"),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_missing_crypto_fails_like_a_real_run(monkeypatch, tmp_path, run_module, params, message, check_mode):
    monkeypatch.setattr(plugin, "HAS_PYCRYPTODOME", False)
    path = tmp_path / "config"
    result = run_module(plugin, {"path": str(path), **params}, check_mode)
    assert not path.exists()
    assert result["failed"] and message in result["msg"]


UNASSIGNED = "\U0001ccf0"


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
        f"invalid content for configuration file {path}: character U+{ord(character):04X} is a surrogate, which is not valid UTF-8"
    )


@pytest.mark.parametrize("state", ["present", "absent"])
def test_escaped_content_bytes_are_written(tmp_path, run_module, state):
    # Ansible passes bytes that are not valid UTF-8 as U+DC80 to U+DCFF
    path = tmp_path / "config"
    result = run_module(plugin, {"path": str(path), "password": "secret", "state": state, "content": "a\udcff\udc80"})
    assert result["changed"]
    written = path.read_bytes()
    assert (decrypt(written, "secret") if state == "present" else written) == b"a\xff\x80"


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
        # rclone itself refuses an empty or blank password, which still encrypts and decrypts consistently
        "",
        " ",
        "\u00a0\u3000",
        "pw" + UNASSIGNED,
        "a" + "\u0301" * 31,
        "a" + "\u1161" * 31,
    ],
)
def test_non_ascii_password_is_accepted(tmp_path, run_module, password):
    path = tmp_path / "rclone.conf"
    result = run_module(plugin, {"path": str(path), "password": password, "content": "config"})
    assert result["changed"] and not result.get("failed")
    assert decrypt(path.read_text(), password) == b"config"


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
        assert decrypt(path.read_text(), "secret") == b"new"
    else:
        assert path.read_text() == "new"


PRESENT_UNREADABLE = "is already encrypted with a different password or its encrypted payload is damaged"
ABSENT_UNREADABLE = "wrong or missing password or damaged encrypted payload"


@pytest.mark.parametrize("payload", ["AAAA", "!!!!"])
@pytest.mark.parametrize("state", ["present", "absent"])
def test_damaged_payload_without_content_fails_clearly(tmp_path, run_module, payload, state):
    path = tmp_path / "rclone.conf"
    original = f"{rclone.CONFIG_MARKER}\n{payload}"
    path.write_text(original)
    result = run_module(plugin, {"path": str(path), "password": "secret", "state": state})
    if state == "present":
        assert result == {"failed": True, "msg": f"configuration file {path} {PRESENT_UNREADABLE}"}
    else:
        assert result == {"failed": True, "msg": f"unable to decrypt configuration file {path}, {ABSENT_UNREADABLE}"}

    assert path.read_text() == original


@pytest.mark.parametrize("check_mode", [False, True])
def test_absent_without_password_or_content_fails_on_encrypted_file(tmp_path, run_module, check_mode):
    path = tmp_path / "rclone.conf"
    original = rclone.encrypt_config(b"[remote]\ntype=local\n", "secret")
    path.write_text(original)
    result = run_module(plugin, {"path": str(path), "state": "absent"}, check_mode)
    assert result == {"failed": True, "msg": f"unable to decrypt configuration file {path}, {ABSENT_UNREADABLE}"}
    assert path.read_text() == original


@pytest.mark.parametrize("check_mode", [False, True])
def test_absent_without_password_replaces_encrypted_file_with_content(tmp_path, run_module, check_mode):
    path = tmp_path / "rclone.conf"
    original = rclone.encrypt_config(b"[remote]\ntype=local\n", "secret")
    path.write_text(original)
    content = "[other]\ntype=local\n"
    result = run_module(plugin, {"path": str(path), "state": "absent", "content": content}, check_mode)
    assert result == {"changed": True, "encrypted": False, "path": str(path)}
    assert path.read_text() == (original if check_mode else content)


@pytest.mark.parametrize("character", [chr(0xD800), chr(0xDBFF), chr(0xDC00), chr(0xDC7F)])
@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("check_mode", [False, True])
def test_path_with_surrogate_is_rejected_before_file_access(
    monkeypatch, tmp_path, run_module, character, state, check_mode
):
    # such a path stands for no bytes, so os.path.realpath failed with a traceback; Ansible logs no value with no_log
    monkeypatch.setattr(plugin.os.path, "realpath", Mock(side_effect=AssertionError("must not access files")))
    path = f"{tmp_path}/rclone{character}.conf"
    params = {"path": path, "password": "secret", "state": state, "content": "config", "_ansible_no_log": True}
    result = run_module(plugin, params, check_mode)
    label = path.encode("utf-8", "backslashreplace").decode("utf-8")
    msg = f"invalid path {label}: U+{ord(character):04X} is a lone surrogate that stands for no byte, unlike U+DC80 to U+DCFF"
    assert result == {"failed": True, "msg": msg}
    assert sorted(tmp_path.iterdir()) == []


@pytest.mark.parametrize("check_mode", [False, True])
def test_path_with_nul_is_rejected_before_file_access(monkeypatch, tmp_path, run_module, check_mode):
    monkeypatch.setattr(plugin.os.path, "realpath", Mock(side_effect=AssertionError("must not access files")))
    params = {"path": f"{tmp_path}/a\x00b", "password": "secret", "content": "config", "_ansible_no_log": True}
    result = run_module(plugin, params, check_mode)
    # the message escapes the NUL character, so it is printable and can be logged
    msg = f"invalid path {tmp_path}/a\\x00b: it contains a NUL character, which a file path cannot contain"
    assert result == {"failed": True, "msg": msg}
    assert sorted(tmp_path.iterdir()) == []


def test_path_with_escaped_bytes_is_accepted(module_factory):
    # U+DC80 to U+DCFF stand for the bytes that are not valid UTF-8, which a Linux file name can hold
    plugin.check_path(module_factory(), "/etc/rclone/r\udcff\udc80.conf")


def test_path_check_does_not_depend_on_the_filesystem_encoding(monkeypatch, module_factory):
    # os.fsencode follows the locale, which may not be UTF-8; a path is checked for code points that are no bytes
    def ascii_fsencode(path):
        return path.encode("ascii")

    monkeypatch.setattr(plugin.os, "fsencode", ascii_fsencode)
    plugin.check_path(module_factory(), "/etc/rclone/r\u00e9\udcff.conf")


@pytest.mark.parametrize("state", ["present", "absent"])
def test_path_with_escaped_bytes_is_returned_escaped(tmp_path, run_module, state):
    # Ansible 2.19 and later refuse a result that is not valid UTF-8, so the returned path escapes U+DC80 to U+DCFF
    try:
        os.close(os.open(os.fsencode(tmp_path) + b"/probe\xff", os.O_CREAT | os.O_WRONLY))
        os.remove(os.fsencode(tmp_path) + b"/probe\xff")
    except OSError:
        pytest.skip("the file system refuses names that are not valid UTF-8")

    path = f"{tmp_path}/r\udcff.conf"
    params = {"path": path, "password": "secret", "state": state, "content": "config", "_ansible_no_log": True}
    result = run_module(plugin, params)
    assert result == {"changed": True, "encrypted": state == "present", "path": f"{tmp_path}/r\\udcff.conf"}
    assert os.listdir(os.fsencode(tmp_path)) == [b"r\xff.conf"]


def test_messages_escape_bytes_of_the_resolved_path(tmp_path, run_module):
    # an ASCII path can resolve through a symbolic link to a name with bytes that are not valid UTF-8
    link = tmp_path / "rclone.conf"
    os.symlink(os.fsencode(tmp_path) + b"/r\xff.conf", os.fsencode(link))
    result = run_module(plugin, {"path": str(link), "password": "secret"})
    assert result == {"failed": True, "msg": f"configuration file does not exist: {tmp_path}/r\\udcff.conf"}
    result["msg"].encode("utf-8")


@pytest.mark.parametrize(
    "params, message",
    [
        ({"owner": "p36-no-such-user"}, "failed to look up user p36-no-such-user"),
        ({"owner": "root\x00", "_ansible_no_log": True}, "failed to look up user root\\x00"),
        ({"group": "p36-no-such-group"}, "failed to look up group p36-no-such-group"),
        ({"group": "x\udcff", "_ansible_no_log": True}, "failed to look up group x\\udcff"),
        ({"mode": "u+z"}, "mode u+z must be in octal or symbolic form"),
        ({"mode": "0x9"}, "mode 0x9 must be in octal or symbolic form"),
    ],
)
@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("check_mode", [False, True])
def test_file_attributes_are_checked_before_writing(tmp_path, run_module, params, message, state, existing, check_mode):
    # Ansible applies them after the file is written, so the configuration changed before the failure
    path = tmp_path / "rclone.conf"
    if existing:
        path.write_text("old")

    result = run_module(
        plugin, {"path": str(path), "password": "secret", "state": state, "content": "new", **params}, check_mode
    )
    assert result == {"failed": True, "msg": f"unable to manage configuration file {path}: {message}"}
    assert (path.read_text() if existing else path.exists()) == ("old" if existing else False)


@pytest.mark.parametrize("kind, option", [("user", "owner"), ("group", "group")])
@pytest.mark.parametrize("value", ["-5", "-1", "4294967295", "4294967296"])
@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("check_mode", [False, True])
def test_id_out_of_range_fails_before_writing(tmp_path, run_module, kind, option, value, state, check_mode):
    # os.lchown raises OverflowError beyond uid_t, which Ansible does not catch, and reads -1 and 2**32 - 1 as no change
    path = tmp_path / "rclone.conf"
    params = {"path": str(path), "password": "secret", "state": state, "content": "new", option: value}
    result = run_module(plugin, params, check_mode)
    assert result == {
        "failed": True,
        "msg": f"unable to manage configuration file {path}: {kind} ID {value} must be from 0 to 4294967294",
    }
    assert not path.exists()


@pytest.mark.parametrize(
    "params", [{"owner": str(os.getuid())}, {"group": str(os.getgid())}, {"mode": "u=rw,g=r,o="}, {"mode": "0640"}]
)
def test_valid_file_attributes_are_applied(tmp_path, run_module, params):
    import grp
    import pwd

    path = tmp_path / "rclone.conf"
    named = {"owner": pwd.getpwuid(os.getuid()).pw_name} if "owner" in params else {}
    named = {"group": grp.getgrgid(os.getgid()).gr_name} if "group" in params else named
    for values in (params, named):
        result = run_module(plugin, {"path": str(path), "password": "secret", "content": "config", **values})
        assert not result.get("failed"), result

    assert decrypt(path.read_text(), "secret") == b"config"


@pytest.mark.parametrize("state", ["present", "absent"])
def test_wrong_password_message_names_path(tmp_path, run_module, state):
    path = tmp_path / "rclone.conf"
    path.write_text(rclone.encrypt_config(b"original", "secret"))
    result = run_module(plugin, {"path": str(path), "state": state, "password": "wrong"})
    assert result["failed"] and str(path) in result["msg"]


@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("header", ["RCLONE_ENCRYPT_V1:\nAAAA", "RCLONE_ENCRYPT_V0:AAAA\n"])
def test_unsupported_encryption_message_names_path(tmp_path, run_module, state, check_mode, header):
    path = tmp_path / "rclone.conf"
    path.write_text(header)
    result = run_module(plugin, {"path": str(path), "password": "secret", "state": state}, check_mode)
    assert result["failed"] and result["msg"] == (
        f"unable to read configuration file {path}: unsupported or damaged configuration encryption header"
    )
    assert path.read_text() == header


@pytest.mark.parametrize("state, password", [("present", "secret"), ("absent", "secret"), ("absent", None)])
@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("header", ["RCLONE_ENCRYPT_V1:\nAAAA", "RCLONE_ENCRYPT_V0:AAAA\n"])
def test_unsupported_encryption_header_is_replaced_by_content(
    tmp_path, run_module, state, password, check_mode, header
):
    # with content the file is read as encrypted and unreadable, as with another password, and replaced
    path = tmp_path / "rclone.conf"
    path.write_text(header)
    params = {"path": str(path), "password": password, "state": state, "content": "config"}
    result = run_module(plugin, params, check_mode)
    assert result["changed"] and not result.get("failed")
    if check_mode:
        assert path.read_text() == header
    elif state == "present":
        assert decrypt(path.read_text(), password) == b"config"
    else:
        assert path.read_text() == "config"

    if not check_mode:
        assert not run_module(plugin, params)["changed"]


@pytest.mark.parametrize(
    "password",
    [" ", "\u00a0\u3000", "pw" + UNASSIGNED, "a" + "\u0301" * 31],
)
@pytest.mark.parametrize("content", [None, "config"])
def test_absent_decrypts_with_a_password_rclone_could_not_have_used(tmp_path, run_module, password, content):
    # a file encrypted with a password rclone itself refuses or may normalize differently can be decrypted
    path = tmp_path / "rclone.conf"
    path.write_text(rclone.encrypt_config(b"original", password))
    params = {"path": str(path), "password": password, "state": "absent"}
    if content is not None:
        params["content"] = content

    result = run_module(plugin, params)
    assert result["changed"] and not result.get("failed")
    assert path.read_text() == (content or "original")


@pytest.mark.parametrize("mode", [2**31, "0" + oct(2**31)[2:], -(2**31) - 1])
@pytest.mark.parametrize("state", ["present", "absent"])
def test_mode_out_of_range_fails_before_writing(tmp_path, run_module, mode, state):
    # os.chmod refuses a mode beyond a C int, which Ansible reports only after the file is written
    path = tmp_path / "rclone.conf"
    result = run_module(
        plugin, {"path": str(path), "password": "secret", "state": state, "content": "new", "mode": mode}
    )
    assert result == {"failed": True, "msg": f"unable to manage configuration file {path}: mode {mode} is out of range"}
    assert not path.exists()


@pytest.mark.parametrize("kind", ["fifo", "device"])
@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("check_mode", [False, True])
def test_path_that_is_not_a_regular_file_fails_before_reading(tmp_path, run_module, kind, state, check_mode):
    # reading a FIFO would block and a device such as /dev/zero never end, and writing would replace the device;
    # /dev/null stands for any device, as reading /dev/zero would not end
    link = tmp_path / "rclone.conf"
    if kind == "fifo":
        target = tmp_path / "fifo"
        os.mkfifo(target)
    else:
        target = Path("/dev/null")

    link.symlink_to(target)

    def expire(signum, frame):
        raise AssertionError("the module blocked")

    previous = signal.signal(signal.SIGALRM, expire)
    signal.alarm(5)
    try:
        result = run_module(
            plugin, {"path": str(link), "password": "secret", "state": state, "content": "new"}, check_mode
        )
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)

    resolved = os.path.realpath(link)
    assert result == {
        "failed": True,
        "msg": f"unable to manage configuration file {resolved}: it is not a regular file",
    }
    assert link.is_symlink() and os.path.realpath(link) == resolved


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


@pytest.mark.parametrize("password", ["\x1f", "\x1c\x1d\x1e"])
def test_password_of_separator_characters_is_accepted(tmp_path, run_module, password):
    path = tmp_path / "rclone.conf"
    result = run_module(plugin, {"path": str(path), "password": password, "content": "config"})
    assert result["changed"] and not result.get("failed")
    assert decrypt(path.read_text(), password) == b"config"


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
    assert (decrypt(text, "secret") if state == "present" else text.encode()) == b"new"


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
