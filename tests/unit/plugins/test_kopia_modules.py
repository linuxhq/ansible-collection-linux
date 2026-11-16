import json
from unittest.mock import Mock

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.linuxhq.linux.plugins.module_utils import kopia as kopia_utils
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
# the kopia_client fixture replaces the shared helper, which kopia_repository also imports
REPOSITORY_STATUS = kopia_utils.repository_status

FAKE_KOPIA = """#!/bin/sh
for arg in "$@"; do printf '%s\\n' "$arg" >> "$KOPIA_FAKE_DIR/argv"; done
case "$2" in
  export)
    if [ -f "$KOPIA_FAKE_DIR/policy.json" ]; then cat "$KOPIA_FAKE_DIR/policy.json"; else echo "policy not found" >&2; exit 1; fi
    ;;
  import) cp "$4" "$KOPIA_FAKE_DIR/policy.json" ;;
  delete) rm "$KOPIA_FAKE_DIR/policy.json" ;;
  show) echo '{}' ;;
esac
"""


CLIENT_STATUS = {"clientOptions": {"hostname": "host", "username": "root"}}

NOT_CONNECTED = (1, "", "repository is not connected")
NOT_INITIALIZED = (1, "", "repository not initialized")


@pytest.fixture(autouse=True)
def kopia_client(monkeypatch):
    """Report the client user and host that kopia_snapshot and kopia_snapshot_info qualify a path with."""
    status = Mock(return_value=CLIENT_STATUS)
    monkeypatch.setattr(kopia_utils, "repository_status", status)
    return status


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
    assert result["failed"] and "permission denied" in result["msg"] and not result.get("changed")
    assert [entry.args[1][:2] for entry in command.call_args_list] == [
        ["repository", "connect"],
        ["repository", "status"],
    ]


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
    command = Mock(side_effect=[(1, "", stderr), (0, "", "") if created else NOT_CONNECTED])
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(
        kopia_repository, {"storage": storage, "password": "secret", "options": {"path": "/backup/kopia"}}
    )
    if created:
        assert result["changed"] and not result.get("failed")
        assert command.call_args_list[1].args[1] == ["repository", "create", "filesystem", "--path=/backup/kopia"]
    else:
        assert result["failed"] and stderr in result["msg"] and not result.get("changed")
        assert command.call_args_list[1].args[1] == ["repository", "status", "--json"]


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


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("value", [None, True, False, 42, 1.5, ["a", "b"], {"a": "b"}])
def test_snapshot_rejects_non_string_tag_values(monkeypatch, run_module, check_mode, value):
    # str() would record them as Python text, such as "None", "True" or "1.1" for an unquoted 1.10
    monkeypatch.setattr(kopia_snapshot, "kopia_command", Mock(side_effect=AssertionError("must not run kopia")))
    monkeypatch.setattr(kopia_snapshot, "kopia_available", Mock(side_effect=AssertionError("must not look up kopia")))
    result = run_module(kopia_snapshot, {"path": "/data", "tags": {"env": value, "role": "db"}}, check_mode)
    assert result["failed"] and "'env'" in result["msg"] and "not a string" in result["msg"]
    assert "string filter" in result["msg"]


def test_snapshot_records_quoted_tag_values_as_given(monkeypatch, run_module):
    command = Mock(side_effect=[(0, '{"id":"new"}\n', ""), (0, '[{"id":"new"}]', "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/data", "tags": {"build": "42", "ratio": "1.10", "time": "12:30"}})
    assert result == {"changed": True, "snapshot": {"id": "new"}}
    assert command.call_args_list[0].args[1] == [
        "snapshot",
        "create",
        "/data",
        "--json",
        "--tags=build:42",
        "--tags=ratio:1.10",
        "--tags=time:12:30",
    ]


def test_snapshot_creates_with_tags_and_returns_latest(monkeypatch, run_module):
    created = '{"id":"new","startTime":"new"}\n'
    command = Mock(side_effect=[(0, created, ""), (0, '[{"startTime":"old"},{"startTime":"new"}]', "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/data", "description": "backup", "tags": {"z": "last", "a": "first"}})
    assert result == {"changed": True, "snapshot": {"start_time": "new"}}
    assert command.call_args_list[0].args[1] == [
        "snapshot",
        "create",
        "/data",
        "--json",
        "--description=backup",
        "--tags=a:first",
        "--tags=z:last",
    ]


@pytest.mark.parametrize(
    "created,expected",
    [
        # a newer snapshot of the path, such as a scheduled one, is not returned as the one just created
        ('{"id":"new","startTime":"new"}\n', {"id": "new", "start_time": "new"}),
        # the newest listed snapshot is returned when the created one cannot be identified or found
        ('{"id":"gone"}\n', {"id": "other", "start_time": "later"}),
        ("not json\n", {"id": "other", "start_time": "later"}),
        ('["new"]\n', {"id": "other", "start_time": "later"}),
    ],
)
def test_snapshot_returns_the_created_snapshot(monkeypatch, run_module, created, expected):
    listing = '[{"id":"old","startTime":"old"},{"id":"new","startTime":"new"},{"id":"other","startTime":"later"}]'
    command = Mock(side_effect=[(0, created, ""), (0, listing, "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/data"})
    assert result == {"changed": True, "snapshot": expected}


def test_snapshot_skipped_as_identical_is_unchanged(monkeypatch, run_module):
    skipped = (0, "", "Not saving snapshot because no files have been changed since previous snapshot")
    command = Mock(side_effect=[skipped, (0, '[{"id":"old"}]', "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/data"})
    assert result == {"changed": False, "snapshot": {"id": "old"}}
    assert command.call_args_list[0].args[1] == ["snapshot", "create", "/data", "--json"]


@pytest.mark.parametrize("path", [None, "/data"])
def test_snapshot_info(monkeypatch, run_module, path):
    command = Mock(return_value=(0, '[{"startTime":"now"}]', ""))
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", command)
    result = run_module(kopia_snapshot_info, {"path": path})
    assert result == {"changed": False, "snapshots": [{"start_time": "now"}]}
    assert command.call_args.args[1] == ["snapshot", "list", "--json"] + (["--", "/data"] if path else [])


@pytest.mark.parametrize(
    "path,source",
    [
        # kopia reads a bare path with "@" before any ":" as user@host or user@host:path, listing nothing or another source
        ("/home/alice@example.com", "root@host:/home/alice@example.com"),
        ("/x@h:/y", "root@host:/x@h:/y"),
        # qualified as kopia records the source, absolute and cleaned
        ("//srv/./a@b/../a@b/", "root@host:/srv/a@b"),
    ],
)
def test_snapshot_info_qualifies_path(monkeypatch, run_module, path, source):
    command = Mock(return_value=(0, "[]", ""))
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", command)
    assert run_module(kopia_snapshot_info, {"path": path}) == {"changed": False, "snapshots": []}
    assert command.call_args.args[1] == ["snapshot", "list", "--json", "--", source]


@pytest.mark.parametrize("status", [None, {}, {"clientOptions": {"hostname": "host"}}])
def test_snapshot_info_path_without_client_fails(monkeypatch, run_module, kopia_client, status):
    kopia_client.return_value = status
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", Mock(side_effect=AssertionError("must not list")))
    result = run_module(kopia_snapshot_info, {"path": "/a@b"})
    assert result["failed"] and "unable to list kopia snapshots of /a@b" in result["msg"]


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


def test_snapshot_saved_with_errors_reports_change(monkeypatch, run_module):
    # kopia prints the saved manifest, then exits non-zero for fatal errors such as an unreadable file
    created = '{"id":"new","rootEntry":{"summ":{"numFailed":1}}}\n'
    listing = '[{"id":"new","startTime":"new"},{"id":"other","startTime":"later"}]'
    command = Mock(side_effect=[(1, created, "Found 1 fatal error(s) while snapshotting\n"), (0, listing, "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/data"})
    assert result["failed"] and result["changed"]
    assert result["snapshot"] == {"id": "new", "start_time": "new"}
    assert (
        result["msg"]
        == "created kopia snapshot new of /data, but kopia reported errors: Found 1 fatal error(s) while snapshotting"
    )
    assert command.call_args_list[1].args[1] == ["snapshot", "list", "--json", "--", "/data"]


SOURCE = {"host": "client", "userName": "alice", "path": "/home/a@b"}


@pytest.mark.parametrize(
    "created,rc,source",
    [
        # the source kopia printed with the saved snapshot is listed
        ({"id": "new", "source": SOURCE}, 0, "alice@client:/home/a@b"),
        ({"id": "new", "source": SOURCE}, 1, "alice@client:/home/a@b"),
        # without one, the path is qualified with the client user and host
        ({"id": "new"}, 0, "root@host:/home/a@b"),
        ({"id": "new", "source": {**SOURCE, "host": ""}}, 1, "root@host:/home/a@b"),
    ],
)
def test_snapshot_of_path_with_at_sign_is_listed(monkeypatch, run_module, created, rc, source):
    # kopia snapshot list reads a bare /home/a@b as user "/home/a" on host "b" and lists nothing
    listing = '[{"id":"new","startTime":"new"}]'
    created = (rc, json.dumps(created), "Found 1 fatal error(s) while snapshotting\n")
    command = Mock(side_effect=[created, (0, listing, "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/home/a@b"})
    assert result["changed"] and result["snapshot"] == {"id": "new", "start_time": "new"}
    assert bool(result.get("failed")) is (rc != 0)
    assert command.call_args_list[0].args[1] == ["snapshot", "create", "/home/a@b", "--json"]
    assert command.call_args_list[1].args[1] == ["snapshot", "list", "--json", "--", source]


def test_snapshot_skipped_as_identical_lists_qualified_path(monkeypatch, run_module, kopia_client):
    command = Mock(side_effect=[(0, "", ""), (0, '[{"id":"old"}]', "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/home/a@b/./"})
    assert result == {"changed": False, "snapshot": {"id": "old"}}
    assert command.call_args_list[1].args[1] == ["snapshot", "list", "--json", "--", "root@host:/home/a@b"]
    kopia_client.assert_called_once()


@pytest.mark.parametrize("listing", ['[{"id":"other","startTime":"later"}]', "[]", "null"])
def test_snapshot_printed_but_not_saved_is_unchanged(monkeypatch, run_module, listing):
    # kopia prints the manifest before its final flush, so a flush error leaves the printed snapshot unsaved
    created = '{"id":"new"}\n'
    command = Mock(side_effect=[(1, created, "flush error: disk full\n"), (0, listing, "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/data"})
    assert result["failed"] and not result.get("changed")
    assert result["snapshot"] == {}
    assert result["msg"] == "unable to create kopia snapshot of /data: flush error: disk full"


@pytest.mark.parametrize("listing", [(1, "", "denied"), (0, "not json", "")])
def test_snapshot_printed_with_errors_and_listing_failed_may_be_changed(monkeypatch, run_module, listing):
    created = '{"id":"new"}\n'
    command = Mock(side_effect=[(1, created, "flush error: disk full\n"), listing])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/data"})
    assert result["failed"] and result["changed"]
    assert result["snapshot"] == {}
    assert "may have been created" in result["msg"] and "new" in result["msg"] and "disk full" in result["msg"]


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


@pytest.mark.parametrize("check_mode", [False, True])
def test_maintenance_rejects_log_size_beyond_kopia_limit(monkeypatch, run_module, check_mode):
    monkeypatch.setattr(kopia_maintenance, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_maintenance, "maintenance_info", Mock(side_effect=AssertionError("must not query")))
    command = Mock(side_effect=AssertionError("must not run kopia"))
    monkeypatch.setattr(kopia_maintenance, "kopia_command", command)
    result = run_module(kopia_maintenance, {"max_retained_log_size_mb": 8796093022208}, check_mode)
    assert result["failed"]
    assert result["msg"] == "invalid max_retained_log_size_mb 8796093022208: it must not exceed 8796093022207"


def test_maintenance_accepts_log_size_at_kopia_limit(monkeypatch, run_module):
    monkeypatch.setattr(kopia_maintenance, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_maintenance, "maintenance_info", lambda module: {})
    result = run_module(kopia_maintenance, {"max_retained_log_size_mb": 8796093022207}, True)
    assert result["changed"]
    assert result["maintenance"]["log_retention"]["max_total_size"] == 8796093022207 << 20


def repository_params(**params):
    return {"storage": "filesystem", "password": "secret", "options": {"path": "/backup"}, **params}


@pytest.mark.parametrize(
    "replies,message,error",
    [
        (
            [(1, "", "permission denied"), NOT_CONNECTED],
            "unable to connect to the kopia repository in filesystem path=/backup",
            "permission denied",
        ),
        (
            [(1, "", "repository not initialized"), (1, "", "disk full")],
            "unable to create the kopia repository in filesystem path=/backup",
            "disk full",
        ),
        (
            [(1, "", "repository not initialized"), (0, "", ""), (1, "", "listing failed")],
            "created the kopia repository in filesystem path=/backup, but validating the provider failed",
            "listing failed",
        ),
    ],
)
def test_repository_failure_names_operation_and_storage(monkeypatch, run_module, replies, message, error):
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: None)
    command = Mock(side_effect=replies)
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(kopia_repository, repository_params(validate_provider=True))
    assert result["failed"] and result["msg"].startswith(message)
    assert error in result["msg"]
    assert command.call_count == len(replies)


def test_repository_from_config_never_creates(monkeypatch, run_module):
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: None)
    command = Mock(return_value=(1, "", "repository not initialized"))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    result = run_module(kopia_repository, {"storage": "from-config", "password": "secret", "options": {"file": "/c"}})
    assert result["failed"] and "unable to connect" in result["msg"]
    assert [entry.args[1][:2] for entry in command.call_args_list] == [
        ["repository", "connect"],
        ["repository", "status"],
    ]


def test_repository_status_uses_password(monkeypatch, run_module):
    status = Mock(side_effect=[None, {"storage": {"type": "filesystem", "config": {"path": "/backup"}}}])
    monkeypatch.setattr(kopia_repository, "repository_status", status)
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(return_value=(0, "", "")))
    params = repository_params(options={"path": "/backup", "persist_credentials": False})
    assert run_module(kopia_repository, params)["changed"]
    assert [entry.kwargs["password"] for entry in status.call_args_list] == ["secret", "secret"]


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
        (
            {"storage": "s3", "password": "secret", "options": {"bucket": 20261115}},
            {"type": "s3", "config": {"bucket": "other"}},
            "bucket is other, not 20261115",
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
        (
            {"storage": "s3", "password": "secret", "options": {"bucket": 20261115}},
            {"type": "s3", "config": {"bucket": "20261115"}},
        ),
    ],
)
def test_repository_connected_same_storage(monkeypatch, run_module, params, storage):
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: {"storage": storage})
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(side_effect=AssertionError("must not reconnect")))
    assert run_module(kopia_repository, params)["changed"] is False


@pytest.mark.parametrize(
    "param,option,value,message",
    [
        ("options", "region", {"name": "us-west-1"}, "invalid options value for region: a dictionary"),
        ("secrets", "access_key", {"id": "key"}, "invalid secrets value for access_key: a dictionary"),
        ("options", "bucket", ["first", "second"], "invalid options value for bucket: it identifies the repository"),
        ("secrets", "path", ["/a", "/b"], "invalid secrets value for path: it identifies the repository"),
        # kopia_flags would send --no-prefix, and the comparison skipped it
        (
            "options",
            "prefix",
            False,
            "invalid options value for prefix: it identifies the repository, so it takes a text value, not a Boolean",
        ),
        (
            "secrets",
            "url",
            True,
            "invalid secrets value for url: it identifies the repository, so it takes a text value, not a Boolean",
        ),
    ],
)
@pytest.mark.parametrize("connected", [False, True])
@pytest.mark.parametrize("check_mode", [False, True])
def test_repository_rejects_values_kopia_cannot_take(
    monkeypatch, run_module, param, option, value, message, connected, check_mode
):
    status = Mock(side_effect=AssertionError("must not query kopia"))
    monkeypatch.setattr(kopia_repository, "repository_status", status)
    monkeypatch.setattr(kopia_repository, "kopia_available", lambda module: connected)
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(side_effect=AssertionError("must not run kopia")))
    params = {"storage": "s3", "password": "secret", "options": {"bucket": "b"}, param: {option: value}}
    result = run_module(kopia_repository, params, check_mode)
    assert result["failed"] and message in result["msg"]
    status.assert_not_called()
    assert repr(value) not in result["msg"]


@pytest.mark.parametrize("check_mode", [False, True])
def test_repository_secret_connected_elsewhere_fails_without_values(monkeypatch, run_module, check_mode):
    storage = {"type": "webdav", "config": {"url": "https://other:stored@dav.example.com/kopia"}}
    monkeypatch.setattr(kopia_repository, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: {"storage": storage})
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(side_effect=AssertionError("must not reconnect")))
    params = {
        "storage": "webdav",
        "password": "secret",
        "options": {"url": "https://dav.example.com/kopia"},
        "secrets": {"url": "https://user:requested@dav.example.com/kopia"},
    }
    result = run_module(kopia_repository, params, check_mode)
    assert result["failed"]
    assert result["msg"] == (
        "already connected to a different repository than webdav: url differs from the connected repository"
    )
    assert "requested" not in result["msg"] and "stored" not in result["msg"]


def test_repository_secret_overriding_option_converges(monkeypatch, run_module):
    connected = {"storage": {"type": "s3", "config": {"bucket": "b"}}}
    status = Mock(side_effect=[None, connected, connected])
    monkeypatch.setattr(kopia_repository, "repository_status", status)
    command = Mock(return_value=(0, "", ""))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    params = {"storage": "s3", "password": "secret", "options": {"bucket": "a"}, "secrets": {"bucket": "b"}}
    assert run_module(kopia_repository, params)["changed"]
    assert command.call_args_list[0].args[1] == ["repository", "connect", "s3", "--bucket=b"]
    assert run_module(kopia_repository, params)["changed"] is False
    assert command.call_count == 1


def test_repository_failure_omits_option_overridden_by_secret(monkeypatch, run_module):
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: None)
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(return_value=(1, "", "access denied")))
    params = {
        "storage": "s3",
        "password": "secret",
        "options": {"bucket": "a", "prefix": "p/"},
        "secrets": {"bucket": "b"},
    }
    result = run_module(kopia_repository, params)
    assert result["failed"]
    assert result["msg"] == "unable to connect to the kopia repository in s3 prefix=p/: access denied"


def test_repository_passes_lists_for_other_options(monkeypatch, run_module):
    monkeypatch.setattr(kopia_repository, "repository_status", Mock(side_effect=[None, {"storage": {}}]))
    command = Mock(return_value=(0, "", ""))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    params = {"storage": "s3", "password": "secret", "options": {"bucket": "b", "tag": ["a", "b"]}}
    assert run_module(kopia_repository, params)["changed"]
    assert command.call_args_list[0].args[1] == ["repository", "connect", "s3", "--bucket=b", "--tag=a", "--tag=b"]


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
    # each target is passed after "--", so kopia never reads it as a flag
    targets = [argv[index + 2] for index, arg in enumerate(argv) if arg in ("export", "delete")]
    assert targets and set(targets) == {target}
    assert all(argv[index + 1] == "--" for index, arg in enumerate(argv) if arg in ("export", "delete"))


def test_snapshot_tags_keep_their_keys(monkeypatch, run_module):
    listing = '[{"startTime":"now","tags":{"tag:Env":"prod","tag:role_name":"db"}}]'
    monkeypatch.setattr(kopia_snapshot, "kopia_command", Mock(side_effect=[(0, "", ""), (0, listing, "")]))
    result = run_module(kopia_snapshot, {"path": "/data", "tags": {"Env": "prod", "role_name": "db"}})
    assert result["snapshot"] == {"start_time": "now", "tags": {"tag:Env": "prod", "tag:role_name": "db"}}
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", Mock(return_value=(0, listing, "")))
    result = run_module(kopia_snapshot_info)
    assert result["snapshots"] == [{"start_time": "now", "tags": {"tag:Env": "prod", "tag:role_name": "db"}}]


@pytest.mark.parametrize("check_mode", [False, True])
def test_maintenance_rejects_empty_owner(monkeypatch, run_module, check_mode):
    monkeypatch.setattr(kopia_maintenance, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_maintenance, "maintenance_info", Mock(side_effect=AssertionError("must not query")))
    monkeypatch.setattr(kopia_maintenance, "kopia_command", Mock(side_effect=AssertionError("must not run kopia")))
    result = run_module(kopia_maintenance, {"owner": ""}, check_mode)
    assert result["failed"] and "owner" in result["msg"]


@pytest.mark.parametrize("state", ["present", "absent"])
def test_policy_mutation_failure_names_target(monkeypatch, run_module, state):
    monkeypatch.setattr(kopia_policy, "policy_export", lambda *args: {"keepLatest": 1})
    monkeypatch.setattr(kopia_policy, "kopia_command", Mock(return_value=(1, "", "permission denied")))
    params = {"target": "root@host:/data", "state": state, "policy": {"keep_latest": 2}}
    result = run_module(kopia_policy, params)
    assert result["failed"] and "root@host:/data" in result["msg"]


@pytest.mark.parametrize("response", [(1, "", "denied"), (0, "not json", "")])
def test_policy_info_show_failure_names_target(monkeypatch, run_module, response):
    monkeypatch.setattr(kopia_policy_info, "policy_export", lambda *args: None)
    monkeypatch.setattr(kopia_policy_info, "kopia_command", Mock(return_value=response))
    result = run_module(kopia_policy_info, {"target": "root@host:/data"})
    assert result["failed"] and "root@host:/data" in result["msg"]


def test_snapshot_failure_names_path(monkeypatch, run_module):
    monkeypatch.setattr(kopia_snapshot, "kopia_command", Mock(return_value=(1, "", "disk full")))
    result = run_module(kopia_snapshot, {"path": "/data"})
    assert result["failed"] and "unable to create kopia snapshot of /data" in result["msg"]


@pytest.mark.parametrize("response", [(1, "", "denied"), (0, "not json", "")])
@pytest.mark.parametrize("path", [None, "/data"])
def test_snapshot_info_failure_names_path(monkeypatch, run_module, response, path):
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", Mock(return_value=response))
    result = run_module(kopia_snapshot_info, {"path": path})
    assert result["failed"] and ("of /data" in result["msg"]) is (path is not None)


@pytest.mark.parametrize("stored", ["/srv/kopia/", "//srv/kopia", "/srv/./kopia", "/srv/other/../kopia"])
@pytest.mark.parametrize("swap", [False, True])
def test_repository_filesystem_path_is_normalized(monkeypatch, run_module, stored, swap):
    stored, path = ("/srv/kopia", stored) if swap else (stored, "/srv/kopia")
    storage = {"type": "filesystem", "config": {"path": stored}}
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: {"storage": storage})
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(side_effect=AssertionError("must not reconnect")))
    assert run_module(kopia_repository, repository_params(options={"path": path}))["changed"] is False


def test_repository_other_paths_are_compared_literally(monkeypatch, run_module):
    storage = {"type": "sftp", "config": {"host": "backup", "path": "/srv/kopia"}}
    monkeypatch.setattr(kopia_repository, "repository_status", lambda module, password=None: {"storage": storage})
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(side_effect=AssertionError("must not reconnect")))
    params = {"storage": "sftp", "password": "secret", "options": {"host": "backup", "path": "/srv/kopia/"}}
    result = run_module(kopia_repository, params)
    assert result["failed"] and "path is /srv/kopia, not /srv/kopia/" in result["msg"]


FQDN_CLIENT = {"clientOptions": {"hostname": "host", "username": "alice@corp.example.com"}}
FQDN_SOURCE = '{"id":"new","source":{"host":"host","userName":"alice@corp.example.com","path":"/srv/data"}}'


@pytest.mark.parametrize(
    "created,listed",
    [
        # saved
        ((0, FQDN_SOURCE, ""), "new"),
        # skipped as identical
        ((0, "", ""), "old"),
        # saved, then kopia reported errors
        ((1, FQDN_SOURCE, "Found 1 fatal error(s) while snapshotting\n"), "new"),
    ],
)
def test_snapshot_without_at_sign_lists_bare_path(monkeypatch, run_module, kopia_client, created, listed):
    # kopia splits user@host:/path at the first "@", so a client user such as alice@corp.example.com cannot be
    # qualified; a bare path is resolved by kopia with its own client user and host
    kopia_client.return_value = FQDN_CLIENT
    command = Mock(side_effect=[created, (0, '[{"id":"new"},{"id":"old"}]', "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "/srv/data"})
    assert result["snapshot"] == {"id": listed}
    assert result["changed"] is (listed == "new")
    assert command.call_args_list[1].args[1] == ["snapshot", "list", "--json", "--", "/srv/data"]
    kopia_client.assert_not_called()


@pytest.mark.parametrize("check_mode", [False, True])
def test_snapshot_path_with_colon_before_at_sign_lists_bare_path(monkeypatch, run_module, kopia_client, check_mode):
    # kopia reads /srv/a:b@c as a path, as its ":" comes before the first "@", so any client user can list it
    kopia_client.return_value = FQDN_CLIENT
    created = '{"id":"new","source":{"host":"host","userName":"alice@corp.example.com","path":"/srv/a:b@c"}}'
    command = Mock(side_effect=[(0, created, ""), (0, '[{"id":"new"}]', "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    monkeypatch.setattr(kopia_snapshot, "kopia_available", lambda module: True)
    result = run_module(kopia_snapshot, {"path": "/srv/a:b@c"}, check_mode=check_mode)
    assert not result.get("failed") and result["changed"]
    if check_mode:
        command.assert_not_called()
    else:
        assert result["snapshot"] == {"id": "new"}
        assert command.call_args_list[1].args[1] == ["snapshot", "list", "--json", "--", "/srv/a:b@c"]

    command = Mock(return_value=(0, '[{"id":"new"}]', ""))
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", command)
    assert run_module(kopia_snapshot_info, {"path": "/srv/a:b@c"}) == {"changed": False, "snapshots": [{"id": "new"}]}
    assert command.call_args.args[1] == ["snapshot", "list", "--json", "--", "/srv/a:b@c"]
    kopia_client.assert_not_called()


def test_snapshot_info_without_at_sign_lists_bare_path(monkeypatch, run_module, kopia_client):
    kopia_client.return_value = FQDN_CLIENT
    command = Mock(return_value=(0, '[{"id":"old"}]', ""))
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", command)
    assert run_module(kopia_snapshot_info, {"path": "/srv/data"}) == {"changed": False, "snapshots": [{"id": "old"}]}
    assert command.call_args.args[1] == ["snapshot", "list", "--json", "--", "/srv/data"]
    kopia_client.assert_not_called()


@pytest.mark.parametrize(
    "client",
    [
        {"hostname": "host", "username": "alice@corp.example.com"},
        {"hostname": "host", "username": "corp:alice"},
        {"hostname": "host:1", "username": "root"},
    ],
)
@pytest.mark.parametrize("plugin", [kopia_snapshot, kopia_snapshot_info])
def test_path_with_at_sign_for_unlistable_client_fails(monkeypatch, run_module, kopia_client, plugin, client):
    # no user@host:/path form can express a user containing "@" or ":", or a host containing ":"
    kopia_client.return_value = {"clientOptions": client}
    monkeypatch.setattr(plugin, "kopia_command", Mock(side_effect=AssertionError("must not run kopia")))
    result = run_module(plugin, {"path": "/home/a@b"})
    assert result["failed"] and not result.get("changed")
    assert "/home/a@b" in result["msg"] and repr(client["username"]) in result["msg"]
    assert repr(client["hostname"]) in result["msg"]


# reads options as kingpin does: an argument starting with "-" is a flag unless it follows "--"
KINGPIN_KOPIA = """#!/bin/sh
for arg in "$@"; do printf '%s\\n' "$arg" >> "$KOPIA_FAKE_DIR/argv"; done
separated=
for arg in "$@"; do
  case "$separated$arg" in
    --) separated=1 ;;
    --json) ;;
    -*) echo "kopia: error: unknown short flag '$arg', try --help" >&2; exit 1 ;;
  esac
done
case "$2" in
  create) echo '{"id":"new"}' ;;
  list) echo '[{"id":"new"}]' ;;
esac
"""


@pytest.mark.parametrize("plugin", [kopia_snapshot, kopia_snapshot_info])
def test_path_with_at_sign_for_user_starting_with_dash_is_listed(
    monkeypatch, run_module, tmp_path, kopia_client, plugin
):
    # kopia accepts any client user, such as one set with --override-username, and records it in the source
    kopia_client.return_value = {"clientOptions": {"hostname": "host", "username": "-svc"}}
    kopia = tmp_path / "kopia"
    kopia.write_text(KINGPIN_KOPIA)
    kopia.chmod(0o755)
    monkeypatch.setenv("KOPIA_FAKE_DIR", str(tmp_path))
    monkeypatch.setattr(basic.AnsibleModule, "run_command", RUN_COMMAND)
    monkeypatch.setattr(basic.AnsibleModule, "get_bin_path", lambda self, name, required=False: str(kopia))
    result = run_module(plugin, {"path": "/home/a@b"})
    assert not result.get("failed")
    assert result.get("snapshot", result.get("snapshots")) in ({"id": "new"}, [{"id": "new"}])
    assert (tmp_path / "argv").read_text().splitlines()[-4:] == ["list", "--json", "--", "-svc@host:/home/a@b"]


def test_path_with_at_sign_for_host_with_at_sign_is_qualified(monkeypatch, run_module, kopia_client):
    # kopia ends the user at the first "@" and the host at the first ":", so a host may contain "@"
    kopia_client.return_value = {"clientOptions": {"hostname": "host@corp", "username": "root"}}
    command = Mock(side_effect=[(0, '{"id":"new"}', ""), (0, '[{"id":"new"}]', "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    assert run_module(kopia_snapshot, {"path": "/home/a@b"}) == {"changed": True, "snapshot": {"id": "new"}}
    assert command.call_args_list[1].args[1] == ["snapshot", "list", "--json", "--", "root@host@corp:/home/a@b"]
    command = Mock(return_value=(0, "[]", ""))
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", command)
    assert run_module(kopia_snapshot_info, {"path": "/home/a@b"}) == {"changed": False, "snapshots": []}
    assert command.call_args.args[1] == ["snapshot", "list", "--json", "--", "root@host@corp:/home/a@b"]


@pytest.mark.parametrize("available", [False, True])
def test_snapshot_check_mode_with_at_sign_for_unlistable_client(monkeypatch, run_module, kopia_client, available):
    kopia_client.return_value = FQDN_CLIENT
    monkeypatch.setattr(kopia_snapshot, "kopia_available", lambda module: available)
    result = run_module(kopia_snapshot, {"path": "/home/a@b"}, check_mode=True)
    assert bool(result.get("failed")) is available
    assert kopia_client.called is available


@pytest.mark.parametrize("path", ["--all", "(global)"])
def test_snapshot_relative_path_is_passed_absolute(monkeypatch, run_module, kopia_client, path):
    # a relative name such as "--all" would be read as an option, and "(global)" as the global source
    monkeypatch.setattr(kopia_utils, "working_directory", lambda: "/work")
    command = Mock(side_effect=[(0, '{"id":"new"}', ""), (0, '[{"id":"new"}]', "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    assert run_module(kopia_snapshot, {"path": path}) == {"changed": True, "snapshot": {"id": "new"}}
    assert command.call_args_list[0].args[1] == ["snapshot", "create", f"/work/{path}", "--json"]
    assert command.call_args_list[1].args[1] == ["snapshot", "list", "--json", "--", f"/work/{path}"]
    command = Mock(return_value=(0, "[]", ""))
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", command)
    assert run_module(kopia_snapshot_info, {"path": path}) == {"changed": False, "snapshots": []}
    assert command.call_args.args[1] == ["snapshot", "list", "--json", "--", f"/work/{path}"]
    kopia_client.assert_not_called()


@pytest.mark.parametrize("client,listed", [(CLIENT_STATUS, True), (FQDN_CLIENT, False)])
def test_relative_path_in_directory_with_at_sign_is_qualified(monkeypatch, run_module, kopia_client, client, listed):
    # the absolute path decides, as kopia reads /home/alice@example.com/data as user@host
    kopia_client.return_value = client
    monkeypatch.setattr(kopia_utils, "working_directory", lambda: "/home/alice@example.com")
    source = "root@host:/home/alice@example.com/data"
    command = Mock(side_effect=[(0, '{"id":"new"}', ""), (0, '[{"id":"new"}]', "")])
    monkeypatch.setattr(kopia_snapshot, "kopia_command", command)
    result = run_module(kopia_snapshot, {"path": "data"})
    assert bool(result.get("failed")) is not listed
    if listed:
        assert result == {"changed": True, "snapshot": {"id": "new"}}
        assert command.call_args_list[0].args[1] == ["snapshot", "create", "/home/alice@example.com/data", "--json"]
        assert command.call_args_list[1].args[1] == ["snapshot", "list", "--json", "--", source]
    else:
        assert "/home/alice@example.com/data" in result["msg"] and not result.get("changed")
        command.assert_not_called()

    command = Mock(return_value=(0, "[]", ""))
    monkeypatch.setattr(kopia_snapshot_info, "kopia_command", command)
    result = run_module(kopia_snapshot_info, {"path": "data"})
    assert bool(result.get("failed")) is not listed
    if listed:
        assert command.call_args.args[1] == ["snapshot", "list", "--json", "--", source]
    else:
        command.assert_not_called()


def must_not_run_kopia(monkeypatch, plugin):
    for name in ("kopia_available", "kopia_command", "policy_export", "repository_status", "maintenance_info"):
        if hasattr(plugin, name):
            monkeypatch.setattr(plugin, name, Mock(side_effect=AssertionError(f"must not call {name}")))


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize(
    "policy,key",
    [
        ({"Retention": {"keep_latest": 2}}, "policy.Retention: kopia reads it as Retention,"),
        ({"retention": {"KEEP_LATEST": 2}}, "policy.retention.KEEP_LATEST: kopia reads it as KEEPLatest,"),
        ({"retention": {"keepLatesT": 2}}, "policy.retention.keepLatesT:"),
        ({"scheduling": {"time_of_day": [{"Hour": 1}]}}, "policy.scheduling.time_of_day[0].Hour:"),
    ],
)
def test_policy_rejects_keys_kopia_reports_differently(monkeypatch, run_module, policy, key, check_mode):
    # kopia matches field names ignoring case, stores the policy, then exports camelCase keys that never match
    must_not_run_kopia(monkeypatch, kopia_policy)
    result = run_module(kopia_policy, {"target": "/data", "policy": policy}, check_mode)
    assert result["failed"] and result["msg"].startswith(f"invalid policy key {key}")
    assert "keep_latest" in result["msg"] and "keepLatest" in result["msg"]


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("key", ["keep_latest", "keepLatest", "keep_LATEST"])
def test_policy_accepts_snake_and_camel_case_keys(monkeypatch, run_module, key, check_mode):
    monkeypatch.setattr(kopia_policy, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_policy, "policy_export", lambda *args: {"retention": {"keepLatest": 2}})
    monkeypatch.setattr(kopia_policy, "kopia_command", Mock(side_effect=AssertionError("must not mutate")))
    result = run_module(kopia_policy, {"target": "/data", "policy": {"retention": {key: 2}}}, check_mode)
    assert result == {"changed": False, "policy": {"retention": {"keep_latest": 2}}}


SURROGATE = "\udc80"


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize(
    "plugin,params,name",
    [
        (kopia_policy, {"target": f"/srv/{SURROGATE}", "policy": {}}, "target"),
        (kopia_policy, {"target": f"/srv/{SURROGATE}", "state": "absent"}, "target"),
        (kopia_policy, {"target": "/srv", "policy": {"files": {"ignore": ["a", SURROGATE]}}}, "policy.files.ignore[1]"),
        (kopia_policy, {"target": "/srv", "policy": {"actions": {SURROGATE: {}}}}, "policy.actions.\\udc80"),
        (kopia_policy_info, {"target": "/srv/\ud800"}, "target"),
        (kopia_maintenance, {"owner": f"root@{SURROGATE}"}, "owner"),
        (kopia_repository, repository_params(options={"path": f"/srv/{SURROGATE}"}), "options.path"),
        (kopia_repository, repository_params(options={"path": "/srv/\udce9"}), "options.path"),
        (
            kopia_repository,
            repository_params(secrets={"bucket": SURROGATE}, storage="s3", options={}),
            "secrets.bucket",
        ),
        (kopia_repository, repository_params(options={"path": "/\udbff"}), "options.path"),
        (kopia_repository, repository_params(options={"path": "/srv", "tag": ["a", "\ud800"]}), "options.tag[1]"),
        (
            kopia_repository,
            repository_params(storage="sftp", options={"keyfile": "/root/.ssh/id_\udce9"}),
            "options.keyfile",
        ),
        (
            kopia_repository,
            repository_params(storage="sftp", secrets={"password": "hunter2\udce9xyz"}),
            "secrets.password",
        ),
        (
            kopia_repository,
            {"storage": "from-config", "password": "secret", "options": {"token": "\udce9"}},
            "options.token",
        ),
        (kopia_snapshot, {"path": f"/srv/{SURROGATE}"}, "path"),
        (kopia_snapshot, {"path": "/srv", "description": SURROGATE}, "description"),
        (kopia_snapshot, {"path": "/srv", "tags": {"env": SURROGATE}}, "tags.env"),
        (kopia_snapshot, {"path": "/srv", "tags": {SURROGATE: "prod"}}, "tags.\\udc80"),
        (kopia_snapshot_info, {"path": "/srv/\ud800"}, "path"),
    ],
)
def test_text_kopia_records_differently_is_rejected(monkeypatch, run_module, plugin, params, name, check_mode):
    # kopia receives a lone surrogate as a raw byte, or not at all, and records text that is not UTF-8 with U+FFFD;
    # Ansible logs the invocation by encoding each text option, which only a task with no_log skips
    must_not_run_kopia(monkeypatch, plugin)
    result = run_module(plugin, dict(params, _ansible_no_log=True), check_mode)
    assert result["failed"]
    assert result["msg"].startswith(f"invalid {name}: it must be valid UTF-8")
    assert "hunter2" not in result["msg"] and "xyz" not in result["msg"]


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize(
    "params,name",
    [
        ({"storage": "from-config", "password": "secret", "options": {"file": "/c\udc7f"}}, "options.file"),
        (
            {"storage": "from-config", "password": "secret", "secrets": {"token_file": "/t\ud800xyz"}},
            "secrets.token_file",
        ),
    ],
)
def test_repository_surrogate_kopia_cannot_receive_is_rejected(monkeypatch, run_module, params, name, check_mode):
    # U+D800 to U+DC7F cannot be encoded, so run_command would fail with a traceback; a failure omits the value
    must_not_run_kopia(monkeypatch, kopia_repository)
    result = run_module(kopia_repository, dict(params, _ansible_no_log=True), check_mode)
    assert result["failed"]
    assert result["msg"].startswith(f"invalid {name}: it must not contain a lone surrogate code point other than")
    assert "hunter2" not in result["msg"] and "xyz" not in result["msg"]


@pytest.mark.parametrize("option", ["file", "token_file"])
@pytest.mark.parametrize("param", ["options", "secrets"])
def test_repository_unsaved_option_passes_raw_bytes(monkeypatch, run_module, param, option):
    # kopia only reads the from-config file paths, so the byte Ansible stands for with U+DCE9 reaches it unchanged
    monkeypatch.setattr(kopia_repository, "repository_status", Mock(side_effect=[None, {"storageType": "x"}]))
    command = Mock(return_value=(0, "", ""))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    params = {"storage": "from-config", "password": "secret", param: {option: "/etc/kopia/r\udce9.config"}}
    result = run_module(kopia_repository, dict(params, _ansible_no_log=True))
    assert result["changed"] and not result.get("failed")
    flag = command.call_args.args[1][-1]
    flag_name = option.replace("_", "-")
    assert flag == f"--{flag_name}=/etc/kopia/r\udce9.config"
    assert to_bytes(flag, errors="surrogate_or_strict") == f"--{flag_name}=/etc/kopia/r".encode() + b"\xe9.config"


READ_ONLY_PATHS = [
    ("s3", {"bucket": "b"}, "root_ca_pem_path"),
    ("rclone", {"remote_path": "r:p"}, "embed_rclone_config"),
    ("gcs", {"bucket": "b", "embed_credentials": True}, "credentials_file"),
    ("gdrive", {"folder_id": "f", "embed_credentials": True}, "credentials_file"),
    ("sftp", {"host": "h", "path": "/p", "embed_credentials": True}, "keyfile"),
    ("sftp", {"host": "h", "path": "/p", "embed_credentials": True, "key_data": ""}, "keyfile"),
    ("sftp", {"host": "h", "path": "/p", "embed_credentials": True, "external": False}, "known_hosts"),
]


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("param", ["options", "secrets"])
@pytest.mark.parametrize("storage,options,option", READ_ONLY_PATHS)
def test_repository_read_only_path_passes_raw_bytes(
    monkeypatch, run_module, storage, options, option, param, check_mode
):
    # kopia reads these files and saves their contents, never the path, so the byte U+DCE9 stands for reaches it
    monkeypatch.setattr(kopia_repository, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_repository, "repository_status", Mock(side_effect=[None, {"storageType": "x"}]))
    command = Mock(return_value=(0, "", ""))
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    params = {"storage": storage, "password": "secret", "options": dict(options)}
    params.setdefault(param, {})[option] = "/etc/kopia/f\udce9"
    result = run_module(kopia_repository, dict(params, _ansible_no_log=True), check_mode)
    assert result["changed"] and not result.get("failed")

    if check_mode:
        command.assert_not_called()
        return

    flag_name = option.replace("_", "-")
    flag = next(arg for arg in command.call_args.args[1] if arg.startswith(f"--{flag_name}="))
    assert to_bytes(flag, errors="surrogate_or_strict") == f"--{flag_name}=/etc/kopia/f".encode() + b"\xe9"


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("embed,accepted", [(True, True), (False, False)])
def test_repository_embed_credentials_from_secrets(monkeypatch, run_module, embed, accepted, check_mode):
    # a secret overrides an option of the same name, so embed_credentials counts from either
    monkeypatch.setattr(kopia_repository, "kopia_available", lambda module: True)
    monkeypatch.setattr(kopia_repository, "repository_status", Mock(side_effect=[None, {"storageType": "x"}]))
    monkeypatch.setattr(kopia_repository, "kopia_command", Mock(return_value=(0, "", "")))
    params = {
        "storage": "sftp",
        "password": "secret",
        "options": {"host": "h", "path": "/p", "keyfile": "/k\udce9", "embed_credentials": not embed},
        "secrets": {"embed_credentials": embed},
    }
    result = run_module(kopia_repository, dict(params, _ansible_no_log=True), check_mode)
    assert bool(result.get("failed")) is not accepted


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("storage,options,option", READ_ONLY_PATHS)
def test_repository_read_only_path_rejects_unencodable_surrogate(
    monkeypatch, run_module, storage, options, option, check_mode
):
    must_not_run_kopia(monkeypatch, kopia_repository)
    params = {"storage": storage, "password": "secret", "options": dict(options, **{option: "/f\udc7f"})}
    result = run_module(kopia_repository, dict(params, _ansible_no_log=True), check_mode)
    assert result["failed"]
    assert result["msg"].startswith(f"invalid options.{option}: it must not contain a lone surrogate code point other")


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize(
    "storage,options,option",
    [
        # kopia saves these paths in its configuration and opens the storage again from that copy
        ("sftp", {"host": "h", "path": "/p"}, "keyfile"),
        ("sftp", {"host": "h", "path": "/p", "embed_credentials": False}, "keyfile"),
        ("sftp", {"host": "h", "path": "/p", "embed_credentials": "true"}, "keyfile"),
        ("sftp", {"host": "h", "path": "/p", "embed_credentials": True, "key_data": "k"}, "keyfile"),
        ("sftp", {"host": "h", "path": "/p", "embed_credentials": True, "external": True}, "keyfile"),
        ("sftp", {"host": "h", "path": "/p", "embed_credentials": True, "known_hosts_data": "k"}, "known_hosts"),
        ("gcs", {"bucket": "b"}, "credentials_file"),
        ("gdrive", {"folder_id": "f", "embed_credentials": False}, "credentials_file"),
        ("s3", {"bucket": "b", "embed_credentials": True}, "credentials_file"),
        ("azure", {"container": "c", "embed_credentials": True}, "azure_federated_token_file"),
        ("filesystem", {"embed_credentials": True}, "path"),
    ],
)
def test_repository_saved_path_rejects_raw_bytes(monkeypatch, run_module, storage, options, option, check_mode):
    must_not_run_kopia(monkeypatch, kopia_repository)
    params = {"storage": storage, "password": "secret", "options": dict(options, **{option: "/f\udce9"})}
    result = run_module(kopia_repository, dict(params, _ansible_no_log=True), check_mode)
    assert result["failed"]
    assert result["msg"].startswith(f"invalid options.{option}: it must be valid UTF-8")


def fake_kopia(monkeypatch, tmp_path, policy=None):
    """Install a fake kopia that records its argv, for the real run_command, holding policy as the exported one."""
    kopia = tmp_path / "kopia"
    kopia.write_text(FAKE_KOPIA)
    kopia.chmod(0o755)
    if policy is not None:
        (tmp_path / "policy.json").write_text(json.dumps(policy))

    monkeypatch.setenv("KOPIA_FAKE_DIR", str(tmp_path))
    monkeypatch.setattr(basic.AnsibleModule, "run_command", RUN_COMMAND)
    monkeypatch.setattr(basic.AnsibleModule, "get_bin_path", lambda self, name, required=False: str(kopia))


MANIFEST_ID = "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize(
    "plugin,params",
    [
        (kopia_policy, {"target": MANIFEST_ID, "policy": {"retention": {"keep_latest": 2}}}),
        (kopia_policy, {"target": MANIFEST_ID, "state": "absent"}),
        (kopia_policy_info, {"target": MANIFEST_ID}),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_policy_manifest_id_target_fails_before_kopia_runs(
    monkeypatch, run_module, tmp_path, plugin, params, check_mode
):
    """kopia policy export, show and delete would look the target up as a manifest ID, such as a snapshot's."""
    fake_kopia(monkeypatch, tmp_path, {MANIFEST_ID: {"retention": {"keepLatest": 10}}})
    result = run_module(plugin, params, check_mode)
    assert result["failed"] and result["msg"] == (
        f"invalid target {MANIFEST_ID}: kopia policy export, show and delete read a target of 32 lowercase "
        "hexadecimal digits as a manifest ID, such as that of a policy or a snapshot, while kopia policy import "
        f"reads it as a path; write a relative directory with such a name as ./{MANIFEST_ID}"
    )
    assert not (tmp_path / "argv").exists()
    assert (tmp_path / "policy.json").exists()


@pytest.mark.parametrize("target", [f"./{MANIFEST_ID}", MANIFEST_ID.upper(), MANIFEST_ID[:-1], MANIFEST_ID + "0"])
def test_policy_target_that_is_not_a_manifest_id_is_passed(monkeypatch, run_module, tmp_path, target):
    fake_kopia(monkeypatch, tmp_path, {target: {"retention": {"keepLatest": 10}}})
    result = run_module(kopia_policy_info, {"target": target})
    assert not result.get("failed") and result["defined"]


@pytest.mark.parametrize("target", ["--global", "-data", "-svc@host:/x"])
@pytest.mark.parametrize("check_mode", [False, True])
def test_policy_target_starting_with_dash_is_passed_after_separator(
    monkeypatch, run_module, tmp_path, target, check_mode
):
    """kopia policy export, show and delete read a target starting with '-' as a flag unless it follows '--'."""
    policy = {"retention": {"keep_latest": 2}}
    fake_kopia(monkeypatch, tmp_path)

    present = run_module(kopia_policy, {"target": target, "policy": policy}, check_mode)
    assert present["changed"] and not present.get("failed")
    info = run_module(kopia_policy_info, {"target": target}, check_mode)
    assert not info.get("failed")
    absent = run_module(kopia_policy, {"target": target, "state": "absent"}, check_mode)
    assert absent["changed"] is not check_mode and not absent.get("failed")

    argv = (tmp_path / "argv").read_text().splitlines()
    starts = [index for index, arg in enumerate(argv) if arg == "policy"]
    commands = [argv[start:end] for start, end in zip(starts, starts[1:] + [len(argv)])]
    expected = [["policy", "export", "--", target]]
    if not check_mode:
        expected += [["policy", "import"], ["policy", "export", "--", target]]

    expected += [["policy", "export", "--", target], ["policy", "show", "--json", "--", target]]
    expected += [["policy", "export", "--", target]] + ([] if check_mode else [["policy", "delete", "--", target]])
    assert [command if command[1] != "import" else command[:2] for command in commands] == expected


@pytest.mark.parametrize(
    "replies,validate",
    [
        # validate-provider fails after create
        ([NOT_CONNECTED, NOT_INITIALIZED, (0, "", ""), (1, "", "listing failed")], True),
        # repository status fails after connect
        ([NOT_CONNECTED, (0, "", ""), (1, "", "status failed")], False),
        # repository status fails after create
        ([NOT_CONNECTED, NOT_INITIALIZED, (0, "", ""), (1, "", "status failed")], False),
        # repository status output cannot be parsed after connect
        ([NOT_CONNECTED, (0, "", ""), (0, "not json", "")], False),
    ],
)
def test_repository_failure_after_write_reports_change(monkeypatch, run_module, replies, validate):
    command = Mock(side_effect=replies)
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    monkeypatch.setattr(kopia_utils, "kopia_command", command)
    monkeypatch.setattr(kopia_repository, "repository_status", REPOSITORY_STATUS)
    result = run_module(kopia_repository, repository_params(validate_provider=validate))
    assert result["failed"] and result["changed"] is True and result["repository"] == {}
    assert command.call_count == len(replies)


def test_repository_failure_before_write_reports_no_change(monkeypatch, run_module):
    command = Mock(side_effect=[NOT_CONNECTED, (1, "", "permission denied"), NOT_CONNECTED])
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    monkeypatch.setattr(kopia_utils, "kopia_command", command)
    monkeypatch.setattr(kopia_repository, "repository_status", REPOSITORY_STATUS)
    result = run_module(kopia_repository, repository_params())
    assert result["failed"] and not result.get("changed")


@pytest.mark.parametrize(
    "stderr",
    [
        # kopia repository create wraps these after repo.Initialize has written the repository format
        "kopia: error: unable to connect to repository: error connecting to repository: unable to set up caching",
        "kopia: error: error populating repository: unable to set global policy: write failed",
    ],
)
def test_repository_create_failure_after_initialize_reports_change(monkeypatch, run_module, stderr):
    command = Mock(side_effect=[NOT_CONNECTED, NOT_INITIALIZED, (1, "", stderr)])
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    monkeypatch.setattr(kopia_utils, "kopia_command", command)
    monkeypatch.setattr(kopia_repository, "repository_status", REPOSITORY_STATUS)
    result = run_module(kopia_repository, repository_params(validate_provider=True))
    assert result["failed"] and result["changed"] is True and result["repository"] == {}
    assert result["msg"] == (
        "created the kopia repository in filesystem path=/backup, but kopia failed afterwards, so its default global "
        f"policy and maintenance owner may not be set, and a later run does not retry them: {stderr}"
    )
    assert command.call_count == 3


def test_repository_connect_failure_after_saving_connection_reports_change(monkeypatch, run_module):
    # kopia saves the connection, then fails to persist the password
    stderr = "kopia: error: error connecting to repository: unable to persist password"
    command = Mock(side_effect=[NOT_CONNECTED, (1, "", stderr), (0, "{}", "")])
    monkeypatch.setattr(kopia_repository, "kopia_command", command)
    monkeypatch.setattr(kopia_utils, "kopia_command", command)
    monkeypatch.setattr(kopia_repository, "repository_status", REPOSITORY_STATUS)
    result = run_module(kopia_repository, repository_params())
    assert result["failed"] and result["changed"] is True and result["repository"] == {}
    assert result["msg"] == (
        f"connected to the kopia repository in filesystem path=/backup, but kopia reported an error: {stderr}"
    )
    assert command.call_args_list[2].args[1] == ["repository", "status", "--json"]
    assert command.call_args_list[2].kwargs == {"password": "secret"}


@pytest.mark.parametrize("export", [(1, "", "denied"), (0, "not json", "")])
def test_policy_export_failure_after_import_reports_change(monkeypatch, run_module, export):
    command = Mock(side_effect=[(1, "", "policy not found"), (0, "", ""), export])
    monkeypatch.setattr(kopia_policy, "kopia_command", command)
    monkeypatch.setattr(kopia_utils, "kopia_command", command)
    monkeypatch.setattr(kopia_policy, "policy_export", kopia_utils.policy_export)
    result = run_module(kopia_policy, {"target": "/data", "policy": {"retention": {"keep_latest": 2}}})
    assert result["failed"] and result["changed"] is True and result["policy"] == {}
    assert "/data" in result["msg"]
    assert command.call_args_list[1].args[1][:2] == ["policy", "import"]


@pytest.mark.parametrize("info", [(1, "", "denied"), (0, "not json", "")])
def test_maintenance_info_failure_after_set_reports_change(monkeypatch, run_module, info):
    command = Mock(side_effect=[(0, '{"full": {"enabled": false}}', ""), (0, "", ""), info])
    monkeypatch.setattr(kopia_maintenance, "kopia_command", command)
    monkeypatch.setattr(kopia_utils, "kopia_command", command)
    monkeypatch.setattr(kopia_maintenance, "maintenance_info", kopia_utils.maintenance_info)
    result = run_module(kopia_maintenance, {"enable_full": True})
    assert result["failed"] and result["changed"] is True and result["maintenance"] == {}
    assert command.call_args_list[1].args[1][:2] == ["maintenance", "set"]
