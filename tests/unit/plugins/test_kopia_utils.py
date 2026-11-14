from copy import deepcopy
from unittest.mock import Mock

import pytest

from ansible_collections.linuxhq.linux.plugins.module_utils import kopia


def test_flags_preserve_false_zero_and_repeated_values():
    options = {"skip": None, "read_only": False, "enabled": True, "count": 0, "tag": ["a", "b"], "empty": ""}
    assert kopia.kopia_flags(options) == ["--count=0", "--empty=", "--enabled", "--no-read-only", "--tag=a", "--tag=b"]
    assert options["tag"] == ["a", "b"]


def test_command_keeps_password_out_of_argv(module_factory):
    module = module_factory({"config_file": "/tmp/config with spaces"})
    module.get_bin_path.return_value = "/usr/bin/kopia"
    module.run_command = Mock(return_value=(0, "result", ""))
    assert kopia.kopia_command(module, ["repository", "status"], password="secret") == (0, "result", "")
    module.run_command.assert_called_once_with(
        ["/usr/bin/kopia", "--config-file=/tmp/config with spaces", "repository", "status"],
        environ_update={"KOPIA_CHECK_FOR_UPDATES": "false", "KOPIA_PASSWORD": "secret"},
        expand_user_and_vars=False,
    )


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
@pytest.mark.parametrize("response, message", [((0, "not json", ""), "parse"), ((1, "", "denied"), "denied")])
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


@pytest.mark.parametrize("response", [(0, "not json", ""), (1, "", "denied")])
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
