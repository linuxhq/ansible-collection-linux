import os
from copy import deepcopy
from unittest.mock import Mock

import pytest

from ansible_collections.linuxhq.linux.plugins.module_utils import kopia

# kopia_command replaces the standard input of the test process with /dev/null
pytestmark = pytest.mark.usefixtures("keep_stdin")


def test_flags_preserve_false_zero_and_repeated_values():
    options = {"skip": None, "read_only": False, "enabled": True, "count": 0, "tag": ["a", "b"], "empty": ""}
    assert kopia.kopia_flags(options) == ["--count=0", "--empty=", "--enabled", "--no-read-only", "--tag=a", "--tag=b"]
    assert options["tag"] == ["a", "b"]


def test_command_keeps_password_out_of_argv(module_factory):
    module = module_factory({"config_file": "/tmp/config with spaces"})
    module.get_bin_path.return_value = "/usr/bin/kopia"
    module.run_command = Mock(return_value=(0, "result", ""))
    assert kopia.kopia_command(module, ["repository", "status"], password="secret") == (0, "result", "")
    # kopia fails rather than waits while another client upgrades the repository format
    module.run_command.assert_called_once_with(
        ["/usr/bin/kopia", "--config-file=/tmp/config with spaces", "repository", "status"],
        environ_update={
            "KOPIA_CHECK_FOR_UPDATES": "false",
            "KOPIA_PASSWORD": "secret",
            "KOPIA_REPO_UPGRADE_NO_BLOCK": "true",
        },
        expand_user_and_vars=False,
    )


@pytest.mark.parametrize(
    "config_file,environ,expected",
    [
        ("/etc/kopia/repository.config", {}, "/etc/kopia/repository.config"),
        ("./repository.config", {}, "./repository.config"),
        ("repository.config", {"XDG_CONFIG_HOME": "/xdg"}, "/xdg/kopia/repository.config"),
        ("repository.config", {"HOME": "/home/u"}, "/home/u/.config/kopia/repository.config"),
        (None, {"HOME": "/home/u"}, "/home/u/.config/kopia/repository.config"),
        (None, {"KOPIA_CONFIG_PATH": "other.config", "XDG_CONFIG_HOME": "/xdg"}, "/xdg/kopia/other.config"),
        # kopia joins the path with Go's filepath.Join, which cleans it
        ("repository.config", {"XDG_CONFIG_HOME": "/xdg/./a/../"}, "/xdg/kopia/repository.config"),
        ("repository.config", {"XDG_CONFIG_HOME": "//xdg//"}, "/xdg/kopia/repository.config"),
        (None, {"HOME": "/home/u/"}, "/home/u/.config/kopia/repository.config"),
    ],
)
def test_config_path_is_resolved_as_kopia_does(monkeypatch, module_factory, config_file, environ, expected):
    for name in ("KOPIA_CONFIG_PATH", "XDG_CONFIG_HOME"):
        monkeypatch.delenv(name, raising=False)

    for name, value in environ.items():
        monkeypatch.setenv(name, value)

    assert kopia.config_path(module_factory({"config_file": config_file})) == expected


@pytest.mark.parametrize("config_file", ["/etc/kopia/repository.config", None])
def test_command_explains_password_prompt(monkeypatch, module_factory, config_file):
    # kopia asks for a password neither given nor persisted, and fails at once on a pipe
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
    monkeypatch.delenv("KOPIA_CONFIG_PATH", raising=False)
    module = module_factory({"config_file": config_file})
    module.get_bin_path.return_value = "/usr/bin/kopia"
    error = "kopia: error: open repository: get password: password prompt error: inappropriate ioctl for device\n"
    module.run_command = Mock(return_value=(1, "Enter password to open repository: ", error))
    config = config_file or "/xdg/kopia/repository.config"
    missing = f"kopia needs the repository password, which is not given and not persisted next to {config}"
    assert kopia.kopia_command(module, ["policy", "list"]) == (
        1,
        "Enter password to open repository: ",
        (f"{missing}: {error.strip()}"),
    )


@pytest.mark.parametrize("value", ["a\x00b", {"a": ["b\x00"]}, {"a\x00": "b"}])
@pytest.mark.parametrize("errors", ["strict", "surrogateescape"])
def test_check_utf8_accepts_nul(module_factory, value, errors):
    # run_command fails cleanly for a NUL in an argument, and JSON carries it as \u0000
    kopia.check_utf8(module_factory(), [("name", value)], errors, {"key": {}})


@pytest.mark.parametrize("password", [None, "secret"])
def test_check_connection_rejects_nul_in_config_file(module_factory, invoke, password):
    # os.stat fails with a traceback for a path with a NUL
    module = module_factory({"config_file": "/etc/kopia\x00.config", "password": password})
    result = invoke(kopia.check_connection, module, {"key": {}})
    assert result == {"failed": True, "msg": "invalid config_file: it must not contain a NUL character", "key": {}}


@pytest.mark.parametrize("kind", ["fifo", "device"])
@pytest.mark.parametrize("password", [None, ""])
def test_check_connection_rejects_password_file_kopia_waits_reading(module_factory, invoke, tmp_path, kind, password):
    # kopia reads the persisted password when none is given, and waits reading a FIFO or a terminal
    config = tmp_path / "repository.config"
    config.write_text("{}")
    password_file = tmp_path / "repository.config.kopia-password"
    if kind == "fifo":
        os.mkfifo(password_file)
    else:
        password_file.symlink_to(os.devnull)

    module = module_factory({"config_file": str(config), "password": password})
    result = invoke(kopia.check_connection, module, {"key": {}})
    reason = "it is a FIFO or a character device, which kopia can wait reading forever"
    assert result == {"failed": True, "msg": f"invalid kopia password file {password_file}: {reason}", "key": {}}


def test_check_connection_ignores_password_file_when_password_is_given(module_factory, tmp_path):
    config = tmp_path / "repository.config"
    config.write_text("{}")
    os.mkfifo(tmp_path / "repository.config.kopia-password")
    kopia.check_connection(module_factory({"config_file": str(config), "password": "secret"}))


@pytest.mark.parametrize("kind", ["directory", "missing", "regular"])
def test_check_connection_leaves_other_files_to_kopia(module_factory, tmp_path, kind):
    # kopia fails reading a directory, which it reports itself
    config = tmp_path / "repository.config"
    if kind == "directory":
        config.mkdir()
        (tmp_path / "repository.config.kopia-password").mkdir()
    elif kind == "regular":
        config.write_text("{}")

    kopia.check_connection(module_factory({"config_file": str(config), "password": None}))


@pytest.mark.parametrize(
    "key,fields,expected",
    [
        ("keepLatest", {"keepLatest": None}, None),
        ("keeplatest", {"keepLatest": None}, "keepLatest"),
        ("KEEPLATEST", {"keepLatest": None}, "keepLatest"),
        # Go folds the long s to S and the Kelvin sign to K, and no other character to an ASCII letter
        ("keepLateſt", {"keepLatest": None}, "keepLatest"),
        ("\u212aeepLatest", {"keepLatest": None}, "keepLatest"),
        ("\u0131gnore", {"ignore": None}, None),
        ("\u0130gnore", {"ignore": None}, None),
        ("keepForever", {"keepLatest": None}, None),
        ("hour", None, None),
    ],
)
def test_policy_field_mismatch(key, fields, expected):
    assert kopia.policy_field_mismatch(key, fields) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("text", None),
        ({"a": ["b", 1, None, True], "c": {"d": "é"}}, None),
        ("\udc80", "name"),
        ("a\ud800b", "name"),
        ({"a": {"b": ["c", "d\udcff"]}}, "name.a.b[1]"),
        ({"a": {"\udc80": "b"}}, "name.a.\\udc80"),
    ],
)
def test_invalid_utf8_names_the_first_text_that_is_not_utf8(value, expected):
    assert kopia.invalid_utf8(value, "name") == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("\udc80\udcff", None),
        ({"a": ["b", "c\udce9"], "\udc80": "d"}, None),
        ("a\ud800b", "name"),
        ("\udc7f", "name"),
        ({"a": {"b": ["c", "d\udbff"]}}, "name.a.b[1]"),
    ],
)
def test_invalid_utf8_surrogateescape_accepts_only_escaped_bytes(value, expected):
    assert kopia.invalid_utf8(value, "name", "surrogateescape") == expected


@pytest.mark.parametrize(
    "function,args,output,expected",
    [
        (kopia.repository_status, (), '{"storageType":"filesystem"}', {"storageType": "filesystem"}),
        (kopia.maintenance_info, (), '{"full":{"enabled":false}}', {"full": {"enabled": False}}),
        (kopia.policy_export, ("target",), '{"target":{"retention":{}}}', {"retention": {}}),
        (kopia.policy_export, ("target",), "{}", {}),
    ],
)
def test_query_parses_json(monkeypatch, module_factory, function, args, output, expected):
    monkeypatch.setattr(kopia, "kopia_command", Mock(return_value=(0, output, "")))
    assert function(module_factory(), *args) == expected


@pytest.mark.parametrize(
    "function,args", [(kopia.repository_status, ()), (kopia.maintenance_info, ()), (kopia.policy_export, ("target",))]
)
@pytest.mark.parametrize("response, message", [((1, "", "denied"), "denied")])
def test_query_failures(monkeypatch, module_factory, invoke, function, args, response, message):
    monkeypatch.setattr(kopia, "kopia_command", Mock(return_value=response))
    result = invoke(function, module_factory(), *args)
    assert result["failed"] and message in result["msg"]


@pytest.mark.parametrize(
    "function,args,error",
    [
        (kopia.repository_status, (), "repository is not connected"),
        (kopia.policy_export, ("target",), "policy not found"),
    ],
)
def test_missing_resource(monkeypatch, module_factory, function, args, error):
    monkeypatch.setattr(kopia, "kopia_command", Mock(return_value=(1, "", error)))
    assert function(module_factory(), *args) is None


@pytest.mark.parametrize("response", [(1, "", "denied")])
def test_policy_export_failure_names_target(monkeypatch, module_factory, invoke, response):
    monkeypatch.setattr(kopia, "kopia_command", Mock(return_value=response))
    result = invoke(kopia.policy_export, module_factory(), "root@host:/data")
    assert result["failed"] and "root@host:/data" in result["msg"]


def test_prune_empty_preserves_false_zero_and_lists():
    original = {"empty": {"nested": None}, "keep": {"false": False, "zero": 0, "list": [], "text": ""}}
    assert kopia.prune_empty(original) == {"keep": {"false": False, "zero": 0, "list": [], "text": ""}}
    assert original["empty"] == {"nested": None}


def test_repository_status_passes_password(monkeypatch, module_factory):
    command = Mock(return_value=(0, "{}", ""))
    monkeypatch.setattr(kopia, "kopia_command", command)
    assert kopia.repository_status(module_factory(), password="secret") == {}
    assert command.call_args.kwargs == {"password": "secret"}


def test_policy_normalize_drops_only_values_kopia_omits():
    policy = {
        "noParent": False,
        "retention": {"keepLatest": 0, "ignoreIdenticalSnapshots": False},
        "scheduling": {"manual": False, "intervalSeconds": 0, "cron": [], "timeOfDay": [{"hour": 0, "min": 0}]},
        "files": {"ignore": [], "maxFileSize": 0, "oneFileSystem": False},
        "compression": {"compressorName": "", "minSize": 0, "neverCompress": ["*.zip"]},
        "metadataCompression": {"compressorName": ""},
        "splitter": {"algorithm": ""},
        "actions": {"beforeSnapshotRoot": {"script": "", "timeout": 0, "mode": "essential"}},
        "unknown": {"value": 0},
    }
    original = deepcopy(policy)
    assert kopia.policy_normalize(policy) == {
        "retention": {"keepLatest": 0, "ignoreIdenticalSnapshots": False},
        "scheduling": {"timeOfDay": [{"hour": 0, "min": 0}]},
        "files": {"oneFileSystem": False},
        "compression": {"neverCompress": ["*.zip"]},
        "actions": {"beforeSnapshotRoot": {"mode": "essential"}},
        "unknown": {"value": 0},
    }
    assert policy == original


def test_policy_normalize_fills_time_of_day_fields():
    policy = {"scheduling": {"timeOfDay": [{"hour": 2}, {"min": 30}, {"hour": 4, "min": 15}]}}
    original = deepcopy(policy)
    assert kopia.policy_normalize(policy) == {
        "scheduling": {"timeOfDay": [{"hour": 2, "min": 0}, {"hour": 0, "min": 30}, {"hour": 4, "min": 15}]}
    }
    assert policy == original


def test_policy_normalize_keeps_wrong_types():
    assert kopia.policy_normalize({"scheduling": {"manual": 0, "intervalSeconds": False}}) == {
        "scheduling": {"manual": 0, "intervalSeconds": False}
    }


@pytest.mark.parametrize(
    "left,right,expected",
    [
        (True, 1, False),
        (0, False, False),
        (1, 1.0, True),
        ({"a": [True]}, {"a": [1]}, False),
        ({"a": [1, {"b": "c"}]}, {"a": [1, {"b": "c"}]}, True),
        ({"a": 1}, {"a": 1, "b": 2}, False),
        ([1], [1, 2], False),
        ([], {}, False),
        ("", None, False),
    ],
)
def test_same_value(left, right, expected):
    assert kopia.same_value(left, right) is expected


CLIENT = {"clientOptions": {"hostname": "host", "username": "root"}}


@pytest.mark.parametrize(
    "path,source",
    [
        ("/home/a@b", "root@host:/home/a@b"),
        ("//srv//a@b/./", "root@host:/srv/a@b"),
        ("/srv/other/../a@b", "root@host:/srv/a@b"),
        ("data@x", "root@host:/work/data@x"),
        ("/srv/a@b:c", "root@host:/srv/a@b:c"),
        ("/srv/a@", "root@host:/srv/a@"),
        # a path without "@", or with a ":" before its first "@", is passed absolute, without a user and host
        ("/srv/a:b@c", "/srv/a:b@c"),
        ("/srv/data/", "/srv/data"),
        ("data", "/work/data"),
        ("--all", "/work/--all"),
        ("(global)", "/work/(global)"),
    ],
)
def test_snapshot_source_is_qualified_as_kopia_records_it(monkeypatch, module_factory, path, source):
    monkeypatch.setattr(kopia, "working_directory", lambda: "/work")
    monkeypatch.setattr(kopia, "repository_status", lambda module, **kwargs: CLIENT)
    assert kopia.snapshot_source(module_factory({"password": None}), path, "list") == source


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/srv/data", False),
        ("/home/alice@example.com", True),
        ("/x@h:/y", True),
        ("/srv/a@", True),
        ("/srv/a:b@c", False),
        ("/srv/a:b", False),
        ("root@host", True),
        ("@host", True),
        ("@host:/data", False),
        ("", False),
    ],
)
def test_reads_as_user_host_follows_parse_source_info(path, expected):
    assert kopia.reads_as_user_host(path) is expected


@pytest.mark.parametrize(
    "status,reason",
    [
        (None, "repository is not connected"),
        ({"clientOptions": {"username": "a@b", "hostname": "host"}}, "cannot list it for 'a@b' at 'host'"),
        ({"clientOptions": {"username": "a:b", "hostname": "host"}}, "cannot list it for 'a:b' at 'host'"),
        ({"clientOptions": {"username": "root", "hostname": "h:1"}}, "cannot list it for 'root' at 'h:1'"),
    ],
)
def test_snapshot_source_with_at_sign_fails(monkeypatch, module_factory, invoke, status, reason):
    monkeypatch.setattr(kopia, "repository_status", lambda module, **kwargs: status)
    result = invoke(kopia.snapshot_source, module_factory({"password": None}), "/a@b", "list snapshots")
    assert result["failed"] and result["msg"].startswith("unable to list snapshots of /a@b: ")
    assert reason in result["msg"]


def test_absolute_path_follows_pwd_like_go(monkeypatch, tmp_path):
    # Go's os.Getwd returns $PWD when it names the working directory, such as through a symlink
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    monkeypatch.chdir(real)
    monkeypatch.setenv("PWD", str(link))
    assert kopia.absolute_path("a@b/./") == f"{link}/a@b"
    # a stale, relative or missing $PWD is ignored
    for pwd in (str(tmp_path), "link", str(tmp_path / "missing")):
        monkeypatch.setenv("PWD", pwd)
        assert kopia.absolute_path("a@b") == f"{os.getcwd()}/a@b"


@pytest.mark.parametrize(
    "name,folded",
    [
        ("keepLatest", "KEEPLATEST"),
        # the Kelvin sign and the long s fold to ASCII letters
        ("\u212a\u017f", "KS"),
        # the dotless i and the dotted capital I fold to no ASCII letter
        ("\u0131\u0130", "\u0131\u0130"),
    ],
)
def test_go_fold_folds_as_go_does_for_ascii_fields(name, folded):
    assert kopia.go_fold(name) == folded


def test_command_with_standard_input_closed_keeps_dev_null(module_factory):
    # os.open returns 0 when the standard input is closed, which must stay open as /dev/null for kopia
    module = module_factory({})
    module.get_bin_path.return_value = "/usr/bin/kopia"
    module.run_command = Mock(return_value=(0, "", ""))
    os.close(0)
    assert kopia.kopia_command(module, ["repository", "status"]) == (0, "", "")
    assert os.fstat(0).st_rdev == os.stat(os.devnull).st_rdev


def test_command_fails_when_dev_null_cannot_be_opened(monkeypatch, module_factory, invoke):
    module = module_factory({})
    module.get_bin_path.return_value = "/usr/bin/kopia"
    monkeypatch.setattr(kopia.os, "open", Mock(side_effect=OSError(24, "Too many open files")))
    result = invoke(kopia.kopia_command, module, ["repository", "status"])
    assert result == {
        "failed": True,
        "msg": f"unable to open {os.devnull} as the standard input of kopia: [Errno 24] Too many open files",
    }
    module.run_command.assert_not_called()


def test_command_escapes_bytes_that_are_not_utf8(monkeypatch, module_factory):
    # kopia repeats a path with a byte that is not valid UTF-8, which run_command decodes as U+DC80 to U+DCFF
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
    module = module_factory({"config_file": "/etc/r\udce9.config"})
    module.get_bin_path.return_value = "/usr/bin/kopia"
    error = "kopia: error: open repository: get password: password prompt error: /p\udce9\n"
    module.run_command = Mock(return_value=(1, "out \udce9", error))
    _dummy, stdout, stderr = kopia.kopia_command(module, ["policy", "list"])
    assert stdout == "out \udce9"
    missing = "kopia needs the repository password, which is not given and not persisted next to /etc/r\\udce9.config"
    assert stderr == f"{missing}: kopia: error: open repository: get password: password prompt error: /p\\udce9"
    stderr.encode("utf-8")


def test_text_labels_escapes_keys_and_values():
    assert kopia.text_labels({"a\udc80": ["b\ud800", 1, {"c": None}]}) == {"a\\udc80": ["b\\ud800", 1, {"c": None}]}
