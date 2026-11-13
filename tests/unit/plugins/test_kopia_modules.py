import json
from unittest.mock import Mock

import pytest

from ansible.module_utils import basic

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

RUN_COMMAND = basic.AnsibleModule.run_command

FAKE_KOPIA = """#!/bin/sh
for arg in "$@"; do printf '%s\\n' "$arg" >> "$KOPIA_FAKE_DIR/argv"; done
case "$2" in
  export)
    if [ -f "$KOPIA_FAKE_DIR/policy.json" ]; then cat "$KOPIA_FAKE_DIR/policy.json"; else echo "policy not found" >&2; exit 1; fi
    ;;
  import) cp "$4" "$KOPIA_FAKE_DIR/policy.json" ;;
  delete) rm "$KOPIA_FAKE_DIR/policy.json" ;;
esac
"""


@pytest.mark.parametrize(
    "plugin,params,key",
    [
        (kopia_repository, {"storage": "filesystem", "password": "secret"}, "repository"),
        (kopia_repository_info, {}, "repository"),
        (kopia_maintenance, {"enable_full": False}, "maintenance"),
        (kopia_maintenance_info, {}, "maintenance"),
        (kopia_policy, {"target": "global", "policy": {}}, "policy"),
        (kopia_policy_info, {"target": "global"}, "effective_policy"),
        (kopia_policy_info, {"target": "global"}, "policy"),
        (kopia_policy_info, {}, "policies"),
        (kopia_snapshot_info, {}, "snapshots"),
    ],
)
def test_check_mode_without_kopia(monkeypatch, run_module, plugin, params, key):
    monkeypatch.setattr(plugin, "kopia_available", lambda module: False)
    if hasattr(plugin, "kopia_command"):
        monkeypatch.setattr(plugin, "kopia_command", Mock(side_effect=AssertionError("must not run kopia")))

    result = run_module(plugin, params, check_mode=True)
    assert key in result
    assert not result.get("failed")
    assert result["changed"] is (plugin in (kopia_repository, kopia_maintenance, kopia_policy))


@pytest.mark.parametrize("check_mode", [False, True])
def test_connected_repository_is_idempotent(monkeypatch, run_module, check_mode):
    monkeypatch.setattr(kopia_repository, "kopia_available", lambda module: True)
    status = {"storage": {"type": "filesystem", "config": {"path": "/backup"}}}
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: status)
    command = Mock(side_effect=AssertionError("must not connect again"))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    params = {"storage": "filesystem", "password": "secret", "options": {"path": "/backup"}}
    result = run_module(kopia_repository, params, check_mode)
    assert result == {"changed": False, "repository": status}
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
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: None)
    command = Mock(return_value=(1, "", "permission denied"))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(kopia_repository, {"storage": "filesystem", "password": "secret"})
    assert result["failed"] and "permission denied" in result["msg"]
    assert command.call_count == 1


MISSING_PATH = "can't connect to storage: cannot access storage path: stat /backup/kopia: no such file or directory"


@pytest.mark.parametrize(
    "storage,stderr,created",
    [
        ("filesystem", MISSING_PATH, True),
        ("filesystem", "can't connect to storage: cannot access storage path: stat /backup: permission denied", False),
        ("sftp", MISSING_PATH, False),
    ],
)
def test_repository_missing_filesystem_path_is_created(monkeypatch, run_module, storage, stderr, created):
    status = Mock(side_effect=[None, {"storageType": storage}])
    monkeypatch.setattr(kopia_repository, "repository_status", status)
    command = Mock(side_effect=[(1, "", stderr), (0, "", "")])
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(
        kopia_repository, {"storage": storage, "password": "secret", "options": {"path": "/backup/kopia"}}
    )
    if created:
        assert result["changed"] and not result.get("failed")
        assert command.call_args_list[1].args[1] == ["repository", "create", "filesystem", "--path=/backup/kopia"]
    else:
        assert result["failed"] and stderr in result["msg"]
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


ZERO_RETENTION = {"maxAge": 0, "maxCount": 0, "maxTotalSize": 0}
DAY = 86400000000000


@pytest.mark.parametrize(
    "stored,params,expected,flags",
    [
        (
            ZERO_RETENTION,
            {"max_retained_log_count": 5},
            {"maxAge": 30 * DAY, "maxCount": 5, "maxTotalSize": 1073741824},
            ["--max-retained-log-count=5"],
        ),
        (
            ZERO_RETENTION,
            {"max_retained_log_count": 0, "max_retained_log_age": 60},
            {"maxAge": 60000000000, "maxCount": 0, "maxTotalSize": 1073741824},
            ["--max-retained-log-count=0", "--max-retained-log-age=60s"],
        ),
        (
            {"maxAge": 0, "maxCount": 5, "maxTotalSize": 0},
            {"max_retained_log_count": 0, "max_retained_log_age": 60},
            {"maxAge": 60000000000, "maxCount": 10000, "maxTotalSize": 1073741824},
            ["--max-retained-log-count=0", "--max-retained-log-age=60s"],
        ),
        (
            {"maxAge": 30 * DAY, "maxCount": 10, "maxTotalSize": 1073741824},
            {"max_retained_log_count": 10, "max_retained_log_size_mb": 1},
            {"maxAge": 30 * DAY, "maxCount": 10, "maxTotalSize": 1048576},
            ["--max-retained-log-count=10", "--max-retained-log-size-mb=1"],
        ),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_maintenance_log_retention_follows_kopia(monkeypatch, run_module, stored, params, expected, flags, check_mode):
    monkeypatch.setattr(kopia_maintenance, "kopia_available", lambda module: True)
    info = Mock(side_effect=[{"logRetention": dict(stored)}, {"logRetention": expected}])
    monkeypatch.setattr(kopia_maintenance, "maintenance_info", info)
    command = Mock(return_value=(0, "", ""))
    monkeypatch.setattr(kopia_maintenance, "kopia_command", command)
    result = run_module(kopia_maintenance, params, check_mode)
    assert result["changed"]
    assert result["maintenance"]["log_retention"] == {
        "max_age": expected["maxAge"],
        "max_count": expected["maxCount"],
        "max_total_size": expected["maxTotalSize"],
    }
    if check_mode:
        command.assert_not_called()
    else:
        assert command.call_args.args[1] == ["maintenance", "set"] + flags


@pytest.mark.parametrize(
    "stored,params",
    [
        (ZERO_RETENTION, {"max_retained_log_count": 0, "max_retained_log_age": 0, "max_retained_log_size_mb": 0}),
        ({"maxAge": 30 * DAY, "maxCount": 0, "maxTotalSize": 1073741824}, {"max_retained_log_count": 0}),
    ],
)
def test_maintenance_log_retention_is_idempotent(monkeypatch, run_module, stored, params):
    monkeypatch.setattr(kopia_maintenance, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_maintenance, "maintenance_info", Mock(return_value={"logRetention": stored}))
    monkeypatch.setattr(kopia_maintenance, "kopia_command", Mock(side_effect=AssertionError("must not mutate")))
    assert not run_module(kopia_maintenance, params)["changed"]


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


@pytest.mark.parametrize("check_mode", [False, True])
def test_snapshot_rejects_tag_key_with_colon(monkeypatch, run_module, check_mode):
    monkeypatch.setattr(kopia_snapshot, "kopia_command", Mock(side_effect=AssertionError("must not run kopia")))
    result = run_module(kopia_snapshot, {"path": "/data", "tags": {"app:tier": "web", "role": "db"}}, check_mode)
    assert result["failed"] and "'app:tier'" in result["msg"]


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


@pytest.mark.parametrize("check_mode", [False, True])
def test_policy_time_of_day_without_minute_is_idempotent(monkeypatch, run_module, check_mode):
    monkeypatch.setattr(kopia_policy, "kopia_available", lambda module: True)
    current = {"scheduling": {"timeOfDay": [{"hour": 2, "min": 0}]}}
    monkeypatch.setattr(kopia_policy, "policy_export", lambda *args: current)
    command = Mock(side_effect=AssertionError("must not mutate"))
    monkeypatch.setattr(kopia_policy, "kopia_command", command)
    result = run_module(
        kopia_policy, {"target": "global", "policy": {"scheduling": {"time_of_day": [{"hour": 2}]}}}, check_mode
    )
    assert result == {"changed": False, "policy": {"scheduling": {"time_of_day": [{"hour": 2, "min": 0}]}}}


def test_policy_zero_values_kopia_omits_are_idempotent(monkeypatch, run_module):
    monkeypatch.setattr(kopia_policy, "kopia_available", lambda module: True)
    current = {"retention": {"keepLatest": 0}, "scheduling": {"intervalSeconds": 3600}, "files": {}}
    monkeypatch.setattr(kopia_policy, "policy_export", lambda *args: current)
    command = Mock(side_effect=AssertionError("must not mutate"))
    monkeypatch.setattr(kopia_policy, "kopia_command", command)
    policy = {
        "no_parent": False,
        "retention": {"keep_latest": 0},
        "scheduling": {"interval_seconds": 3600, "manual": False, "time_of_day": [], "no_parent_time_of_day": False},
        "files": {"ignore": [], "max_file_size": 0, "no_parent_ignore": False},
        "compression": {"compressor_name": "", "min_size": 0, "max_size": 0},
        "actions": {"before_folder": {"script": "", "timeout": 0}},
    }
    result = run_module(kopia_policy, {"target": "global", "policy": policy})
    assert result == {
        "changed": False,
        "policy": {"retention": {"keep_latest": 0}, "scheduling": {"interval_seconds": 3600}},
    }


@pytest.mark.parametrize(
    "policy",
    [
        {"retention": {"keep_latest": 0}},
        {"files": {"ignore_cache_dirs": False}},
        {"scheduling": {"manual": True}},
        {"scheduling": {"manual": 0}},
    ],
)
def test_policy_optional_values_are_compared(monkeypatch, run_module, policy):
    monkeypatch.setattr(kopia_policy, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_policy, "policy_export", lambda *args: {})
    result = run_module(kopia_policy, {"target": "global", "policy": policy}, True)
    assert result["changed"]


@pytest.mark.parametrize("desired,current", [(True, 1), (1, True), (False, 0), (0, False)])
def test_policy_compare_does_not_treat_booleans_as_numbers(monkeypatch, run_module, desired, current):
    monkeypatch.setattr(kopia_policy, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_policy, "policy_export", lambda *args: {"retention": {"keepLatest": current}})
    result = run_module(kopia_policy, {"target": "global", "policy": {"retention": {"keep_latest": desired}}}, True)
    assert result["changed"]


def test_maintenance_compare_does_not_treat_booleans_as_numbers(monkeypatch, run_module):
    monkeypatch.setattr(kopia_maintenance, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_maintenance, "maintenance_info", lambda module: {"listParallelism": True})
    result = run_module(kopia_maintenance, {"list_parallelism": 1}, True)
    assert result["changed"]


@pytest.mark.parametrize(
    "param",
    [
        "full_interval",
        "list_parallelism",
        "max_retained_log_age",
        "max_retained_log_count",
        "max_retained_log_size_mb",
        "quick_interval",
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_maintenance_rejects_negative_values(monkeypatch, run_module, param, check_mode):
    monkeypatch.setattr(kopia_maintenance, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_maintenance, "maintenance_info", Mock(side_effect=AssertionError("must not query")))
    command = Mock(side_effect=AssertionError("must not run kopia"))
    monkeypatch.setattr(kopia_maintenance, "kopia_command", command)
    result = run_module(kopia_maintenance, {"enable_full": True, param: -1}, check_mode)
    assert result["failed"] and param in result["msg"]


def repository_params(**params):
    return {"storage": "filesystem", "password": "secret", "options": {"path": "/backup"}, **params}


@pytest.mark.parametrize(
    "replies,message",
    [
        ([(1, "", "permission denied")], "unable to connect to the kopia repository in filesystem path=/backup"),
        (
            [(1, "", "repository not initialized"), (1, "", "disk full")],
            "unable to create the kopia repository in filesystem path=/backup",
        ),
        (
            [(1, "", "repository not initialized"), (0, "", ""), (1, "", "listing failed")],
            "created the kopia repository in filesystem path=/backup, but validating the provider failed",
        ),
    ],
)
def test_repository_failure_names_operation_and_storage(monkeypatch, run_module, replies, message):
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: None)
    command = Mock(side_effect=replies)
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(kopia_repository, repository_params(validate_provider=True))
    assert result["failed"] and result["msg"].startswith(message)
    assert replies[-1][2] in result["msg"]
    assert command.call_count == len(replies)


def test_repository_from_config_never_creates(monkeypatch, run_module):
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: None)
    command = Mock(return_value=(1, "", "repository not initialized"))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(kopia_repository, {"storage": "from-config", "password": "secret", "options": {"file": "/c"}})
    assert result["failed"] and "unable to connect" in result["msg"]
    assert command.call_count == 1


def test_repository_status_uses_password(monkeypatch, run_module):
    status = Mock(side_effect=[None, {"storage": {"type": "filesystem", "config": {"path": "/backup"}}}])
    monkeypatch.setattr(kopia_repository, "repository_status", status)
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(return_value=(0, "", "")))
    params = repository_params(options={"path": "/backup", "persist_credentials": False})
    assert run_module(kopia_repository, params)["changed"]
    assert [entry.kwargs for entry in status.call_args_list] == [{"password": "secret"}, {"password": "secret"}]


@pytest.mark.parametrize(
    "params,storage,message",
    [
        (repository_params(), {"type": "s3", "config": {"bucket": "b"}}, "storage type is s3, not filesystem"),
        (repository_params(), {"type": "filesystem", "config": {"path": "/other"}}, "path is /other, not /backup"),
        (
            {"storage": "s3", "password": "secret", "options": {"bucket": "new", "prefix": "a/"}},
            {"type": "s3", "config": {"bucket": "new", "prefix": "b/"}},
            "prefix is b/, not a/",
        ),
        (
            {"storage": "azure", "password": "secret", "options": {"container": "new"}},
            {"type": "azureBlob", "config": {"container": "old"}},
            "container is old, not new",
        ),
        (
            {"storage": "s3", "password": "secret", "options": {"bucket": "b", "prefix": "a/"}},
            {"type": "s3", "config": {"bucket": "b"}},
            "prefix is , not a/",
        ),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_repository_connected_elsewhere_fails(monkeypatch, run_module, params, storage, message, check_mode):
    monkeypatch.setattr(kopia_repository, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: {"storage": storage})
    command = Mock(side_effect=AssertionError("must not reconnect"))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(kopia_repository, params, check_mode)
    assert result["failed"] and "connected to a different repository" in result["msg"] and message in result["msg"]


@pytest.mark.parametrize(
    "params,storage",
    [
        (
            {"storage": "azure", "password": "secret", "options": {"container": "c", "storage_account": "a"}},
            {"type": "azureBlob", "config": {"container": "c", "storageAccount": "a"}},
        ),
        (
            {"storage": "s3", "password": "secret", "options": {"bucket": "b", "region": "elsewhere", "prefix": ""}},
            {"type": "s3", "config": {"bucket": "b", "region": "us-west-1"}},
        ),
        ({"storage": "from-config", "password": "secret", "options": {"file": "/c"}}, {"type": "s3", "config": {}}),
        (
            {"storage": "rclone", "password": "secret", "options": {"remote_path": "remote:kopia"}},
            {"type": "rclone", "config": {"remotePath": "remote:kopia"}},
        ),
    ],
)
def test_repository_connected_same_storage(monkeypatch, run_module, params, storage):
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: {"storage": storage})
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(side_effect=AssertionError("must not reconnect")))
    assert run_module(kopia_repository, params)["changed"] is False


def test_repository_home_path_matches_resolved_path(monkeypatch, run_module):
    monkeypatch.setenv("HOME", "/home/user")
    storage = {"type": "filesystem", "config": {"path": "/home/user/backup"}}
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: {"storage": storage})
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(side_effect=AssertionError("must not reconnect")))
    assert run_module(kopia_repository, repository_params(options={"path": "~/backup"}))["changed"] is False


@pytest.mark.parametrize("path", ["$BACKUP_ROOT/backup", "${BACKUP_ROOT}/backup"])
def test_repository_variable_path_is_compared_literally(monkeypatch, run_module, path):
    monkeypatch.setenv("BACKUP_ROOT", "/srv")
    storage = {"type": "filesystem", "config": {"path": "/srv/backup"}}
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: {"storage": storage})
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(side_effect=AssertionError("must not reconnect")))
    result = run_module(kopia_repository, repository_params(options={"path": path}))
    assert result["failed"] and f"path is /srv/backup, not {path}" in result["msg"]


@pytest.mark.parametrize("target", ["$KOPIA_FAKE_ROOT/data", "~/data"])
def test_policy_commands_use_identical_target(monkeypatch, run_module, tmp_path, target):
    """Run the real run_command against a fake kopia so its argument handling reaches the recorded argv."""
    kopia = tmp_path / "kopia"
    kopia.write_text(FAKE_KOPIA)
    kopia.chmod(0o755)
    monkeypatch.setenv("KOPIA_FAKE_DIR", str(tmp_path))
    monkeypatch.setenv("KOPIA_FAKE_ROOT", "/expanded")
    monkeypatch.setattr(basic.AnsibleModule, "run_command", RUN_COMMAND)
    monkeypatch.setattr(basic.AnsibleModule, "get_bin_path", lambda self, name, required=False: str(kopia))
    policy = {"retention": {"keep_latest": 2}}

    present = run_module(kopia_policy, {"target": target, "policy": policy})
    assert present["changed"] and present["policy"] == policy
    assert list(json.loads((tmp_path / "policy.json").read_text())) == [target]
    assert not run_module(kopia_policy, {"target": target, "policy": policy})["changed"]
    assert run_module(kopia_policy, {"target": target, "state": "absent"})["changed"]
    assert not (tmp_path / "policy.json").exists()

    argv = (tmp_path / "argv").read_text().splitlines()
    targets = [argv[index + 1] for index, arg in enumerate(argv) if arg in ("export", "delete")]
    assert targets and set(targets) == {target}


def test_snapshot_tags_keep_their_keys(monkeypatch, run_module):
    listing = '[{"startTime":"now","tags":{"tag:Env":"prod","tag:role_name":"db"}}]'
    monkeypatch.setattr(kopia_snapshot, "kopia_command", Mock(side_effect=[(0, "", ""), (0, listing, "")]))
    result = run_module(kopia_snapshot, {"path": "/data", "tags": {"Env": "prod", "role_name": "db"}})
    assert result["snapshot"] == {"start_time": "now", "tags": {"tag:Env": "prod", "tag:role_name": "db"}}
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", Mock(return_value=(0, listing, "")))
    result = run_module(kopia_snapshot_info)
    assert result["snapshots"] == [{"start_time": "now", "tags": {"tag:Env": "prod", "tag:role_name": "db"}}]
