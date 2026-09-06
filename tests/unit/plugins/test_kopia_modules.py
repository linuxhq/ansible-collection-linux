import json
from unittest.mock import Mock

import pytest

from ansible_collections.linuxhq.linux.plugins.modules import (
    kopia_maintenance,
    kopia_maintenance_info,
    kopia_policy,
    kopia_policy_info,
    kopia_repository,
    kopia_repository_info,
    kopia_snapshot,
    kopia_snapshot_info,
)


@pytest.mark.parametrize(
    "plugin,params,key",
    [
        (kopia_repository, {"storage": "filesystem", "password": "secret"}, "repository"),
        (kopia_repository_info, {}, "repository"),
        (kopia_maintenance, {"enable_full": False}, "maintenance"),
        (kopia_maintenance_info, {}, "maintenance"),
        (kopia_policy, {"target": "global", "policy": {}}, "policy"),
        (kopia_policy_info, {"target": "global"}, "effective_policy"),
        (kopia_snapshot_info, {}, "snapshots"),
    ],
)
def test_check_mode_without_kopia(monkeypatch, run_module, plugin, params, key):
    monkeypatch.setattr(plugin, "kopia_available", lambda module: False)
    result = run_module(plugin, params, check_mode=True)
    assert key in result
    assert not result.get("failed")
    assert result["changed"] is (plugin in (kopia_repository, kopia_maintenance, kopia_policy))


@pytest.mark.parametrize("check_mode", [False, True])
def test_connected_repository_is_idempotent(monkeypatch, run_module, check_mode):
    monkeypatch.setattr(kopia_repository, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module: {"storageType": "filesystem"})
    command = Mock(side_effect=AssertionError("must not connect again"))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(kopia_repository, {"storage": "filesystem", "password": "secret"}, check_mode)
    assert result == {"changed": False, "repository": {"storage_type": "filesystem"}}
    command.assert_not_called()


@pytest.mark.parametrize("create", [False, True])
def test_repository_connect_or_create(monkeypatch, run_module, create):
    status = Mock(side_effect=[None, {"storageType": "filesystem"}])
    monkeypatch.setattr(kopia_repository, "repository_status", status)
    replies = [(1, "", "repository not initialized"), (0, "", ""), (0, "", "")] if create else [(0, "", "")]
    command = Mock(side_effect=replies)
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(
        kopia_repository,
        {"storage": "filesystem", "password": "secret", "options": {"path": "/backup"}, "validate_provider": True},
    )
    assert result == {"changed": True, "repository": {"storage_type": "filesystem"}}
    assert command.call_args_list[0].args[1] == ["repository", "connect", "filesystem", "--path=/backup"]
    assert command.call_args_list[0].kwargs == {"password": "secret"}
    if create:
        assert command.call_args_list[1].args[1][0:2] == ["repository", "create"]
        assert command.call_args_list[2].args[1] == ["repository", "validate-provider"]
    else:
        assert command.call_count == 1


def test_repository_connection_error_does_not_create(monkeypatch, run_module):
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module: None)
    command = Mock(return_value=(1, "", "permission denied"))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(kopia_repository, {"storage": "filesystem", "password": "secret"})
    assert result["failed"] and "permission denied" in result["msg"]
    assert command.call_count == 1


@pytest.mark.parametrize("status,connected", [(None, False), ({"storageType": "s3"}, True)])
def test_repository_info(monkeypatch, run_module, status, connected):
    monkeypatch.setattr(kopia_repository_info, "repository_status", lambda module: status)
    result = run_module(kopia_repository_info)
    assert result["connected"] is connected and not result["changed"]
    assert result["repository"] == ({"storage_type": "s3"} if connected else {})


@pytest.mark.parametrize("check_mode", [False, True])
def test_maintenance_false_zero_and_unit_conversion(monkeypatch, run_module, check_mode):
    initial = {"full": {"enabled": True, "interval": 100}, "logRetention": {"maxTotalSize": 99}}
    updated = {"full": {"enabled": False, "interval": 2000000000}, "logRetention": {"maxTotalSize": 0}}
    monkeypatch.setattr(kopia_maintenance, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_maintenance, "maintenance_info", Mock(side_effect=[initial, updated]))
    command = Mock(return_value=(0, "", ""))
    monkeypatch.setattr(kopia_maintenance, "kopia_command", command)
    result = run_module(
        kopia_maintenance, {"enable_full": False, "full_interval": 2, "max_retained_log_size_mb": 0}, check_mode
    )
    assert result["changed"]
    assert result["maintenance"] == {
        "full": {"enabled": False, "interval": 2000000000},
        "log_retention": {"max_total_size": 0},
    }
    assert initial["full"]["enabled"] is True
    if check_mode:
        command.assert_not_called()
    else:
        assert command.call_args.args[1] == [
            "maintenance",
            "set",
            "--enable-full=false",
            "--full-interval=2s",
            "--max-retained-log-size-mb=0",
        ]


def test_maintenance_no_change_and_info(monkeypatch, run_module):
    data = {"full": {"enabled": False}, "listParallelism": 2}
    for plugin in (kopia_maintenance, kopia_maintenance_info):
        monkeypatch.setattr(plugin, "maintenance_info", lambda module: data)
        result = run_module(plugin, {"enable_full": False} if plugin is kopia_maintenance else {})
        assert result == {"changed": False, "maintenance": {"full": {"enabled": False}, "list_parallelism": 2}}


@pytest.mark.parametrize("current,check_mode,changed", [(None, True, True), ({"keepLatest": 2}, False, False)])
def test_policy_present_prediction_and_idempotence(monkeypatch, run_module, current, check_mode, changed):
    monkeypatch.setattr(kopia_policy, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_policy, "policy_export", lambda *args: current)
    command = Mock(side_effect=AssertionError("must not mutate"))
    monkeypatch.setattr(kopia_policy, "kopia_command", command)
    result = run_module(kopia_policy, {"target": "global", "policy": {"keep_latest": 2}}, check_mode)
    assert result == {"changed": changed, "policy": {"keep_latest": 2}}
    command.assert_not_called()


def test_policy_imports_json_and_refreshes(monkeypatch, run_module, tmp_path):
    monkeypatch.setattr(kopia_policy, "policy_export", Mock(side_effect=[None, {"keepLatest": 2}]))
    captured = []

    def command(module, args):
        with open(args[-1]) as stream:
            captured.append(json.load(stream))

        assert args[:3] == ["policy", "import", "--from-file"]
        return 0, "", ""

    monkeypatch.setattr(kopia_policy, "kopia_command", command)
    result = run_module(
        kopia_policy, {"target": "global", "policy": {"keep_latest": 2}, "_ansible_remote_tmp": str(tmp_path)}
    )
    assert result["changed"]
    assert captured == [{"global": {"keepLatest": 2}}]


@pytest.mark.parametrize("current,check_mode,changed", [(None, False, False), ({}, True, True), ({}, False, True)])
def test_policy_delete(monkeypatch, run_module, current, check_mode, changed):
    monkeypatch.setattr(kopia_policy, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_policy, "policy_export", lambda *args: current)
    command = Mock(return_value=(0, "", ""))
    monkeypatch.setattr(kopia_policy, "kopia_command", command)
    assert run_module(kopia_policy, {"target": "global", "state": "absent"}, check_mode) == {"changed": changed}
    assert command.call_count == int(changed and not check_mode)


def test_policy_info_distinguishes_inherited_policy(monkeypatch, run_module):
    monkeypatch.setattr(kopia_policy_info, "policy_export", lambda *args: None)
    monkeypatch.setattr(kopia_policy_info, "kopia_command", Mock(return_value=(0, '{"keepLatest":2}', "")))
    assert run_module(kopia_policy_info, {"target": "global"}) == {
        "changed": False,
        "defined": False,
        "policy": {},
        "effective_policy": {"keep_latest": 2},
    }


def test_policy_list(monkeypatch, run_module):
    monkeypatch.setattr(kopia_policy_info, "kopia_command", Mock(return_value=(0, '[{"keepLatest":2}]', "")))
    assert run_module(kopia_policy_info) == {"changed": False, "policies": [{"keep_latest": 2}]}


def test_snapshot_check_mode_never_executes(run_module):
    assert run_module(kopia_snapshot, {"path": "/data"}, True) == {"changed": True, "snapshot": {}}


def test_snapshot_creates_with_tags_and_returns_latest(monkeypatch, run_module):
    command = Mock(side_effect=[(0, "", ""), (0, '[{"startTime":"old"},{"startTime":"new"}]', "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/data", "description": "backup", "tags": {"z": "last", "a": "first"}})
    assert result == {"changed": True, "snapshot": {"start_time": "new"}}
    assert command.call_args_list[0].args[1] == [
        "snapshot",
        "create",
        "/data",
        "--description=backup",
        "--tags=a:first",
        "--tags=z:last",
    ]


@pytest.mark.parametrize("path", [None, "/data"])
def test_snapshot_info(monkeypatch, run_module, path):
    command = Mock(return_value=(0, '[{"startTime":"now"}]', ""))
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", command)
    result = run_module(kopia_snapshot_info, {"path": path})
    assert result == {"changed": False, "snapshots": [{"start_time": "now"}]}
    assert command.call_args.args[1] == ["snapshot", "list", "--json"] + ([path] if path else [])


@pytest.mark.parametrize("response", [(1, "", "denied"), (0, "not json", "")])
@pytest.mark.parametrize("plugin,params", [(kopia_snapshot_info, {}), (kopia_policy_info, {})])
def test_info_command_errors(monkeypatch, run_module, response, plugin, params):
    monkeypatch.setattr(plugin, "kopia_command", Mock(return_value=response))
    result = run_module(plugin, params)
    assert result["failed"]
    assert "denied" in result["msg"] or "parse" in result["msg"]


@pytest.mark.parametrize(
    "plugin,params,message",
    [
        (kopia_repository, {"storage": "filesystem"}, "password"),
        (kopia_repository, {"storage": "invalid", "password": "secret"}, "storage"),
        (kopia_policy, {"target": "global"}, "policy"),
        (kopia_policy, {"target": "global", "state": "invalid"}, "state"),
        (kopia_maintenance, {}, "required"),
        (kopia_snapshot, {}, "path"),
    ],
)
def test_argument_validation(run_module, plugin, params, message):
    result = run_module(plugin, params)
    assert result["failed"] and message in result["msg"]


@pytest.mark.parametrize("state", ["present", "absent"])
def test_policy_mutation_failure(monkeypatch, run_module, tmp_path, state):
    monkeypatch.setattr(kopia_policy, "policy_export", lambda *args: {"keepLatest": 1})
    command = Mock(return_value=(1, "", "permission denied"))
    monkeypatch.setattr(kopia_policy, "kopia_command", command)
    result = run_module(kopia_policy, {"target": "global", "state": state, "policy": {"keep_latest": 2}})
    assert result["failed"] and "permission denied" in result["msg"]
    assert command.call_count == 1


def test_maintenance_mutation_failure(monkeypatch, run_module):
    monkeypatch.setattr(kopia_maintenance, "maintenance_info", Mock(return_value={"full": {"enabled": False}}))
    monkeypatch.setattr(kopia_maintenance, "kopia_command", Mock(return_value=(1, "", "locked")))
    result = run_module(kopia_maintenance, {"enable_full": True})
    assert result["failed"] and "locked" in result["msg"]
    assert kopia_maintenance.maintenance_info.call_count == 1


def test_snapshot_failure_does_not_query_latest(monkeypatch, run_module):
    command = Mock(return_value=(1, "", "disk full"))
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/data"})
    assert result["failed"] and "disk full" in result["msg"]
    assert command.call_count == 1


@pytest.mark.parametrize("response", [(1, "", "denied"), (0, "not json", ""), (0, "[]", "")])
def test_latest_snapshot_unavailable(monkeypatch, module_factory, response):
    monkeypatch.setattr(kopia_snapshot, "kopia_command", Mock(return_value=response))
    assert kopia_snapshot.latest_snapshot(module_factory({"password": None}), "/data") == {}
