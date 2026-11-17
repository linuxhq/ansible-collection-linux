#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_maintenance
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Manage kopia repository maintenance settings
description:
  - Manage the maintenance settings of the connected kopia repository.
  - Settings are compared against C(kopia maintenance info) and only applied
    with C(kopia maintenance set) when they differ, options left unset are not
    touched.
  - At least one setting option besides O(config_file) is required.
  - When every stored log retention setting is zero, kopia starts from its
    default log retention before applying the requested log retention
    options, so the ones left unset take the default values. The result and
    check mode predictions follow kopia.
notes:
  - kopia reads the repository password persisted next to the configuration
    file, in a file named after it with C(.kopia-password) added. When there
    is none, such as for a connection made with C(persist_credentials) set to
    V(false), the module fails rather than kopia waiting for the password on
    its standard input.
  - While another client upgrades the repository format, kopia fails rather
    than waiting for the upgrade to end.
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
      - kopia looks up a bare file name, without a directory, in its
        configuration directory, C($XDG_CONFIG_HOME/kopia) or
        C(~/.config/kopia), not in the working directory, so write V(./name)
        for a file in the working directory.
      - A path with a lone surrogate code point from U+D800 to U+DC7F, which
        cannot be passed to kopia, is rejected before kopia runs, also in
        check mode. U+DC80 to U+DCFF, which Ansible uses for bytes that are
        not valid UTF-8, are passed as those bytes.
    type: path
  enable_full:
    description: Enable or disable periodic full maintenance.
    type: bool
  enable_quick:
    description: Enable or disable periodic quick maintenance.
    type: bool
  extend_object_locks:
    description:
      - Extend the retention period of locked objects as needed.
      - Requires kopia 0.14.0 or later.
    type: bool
  full_interval:
    description:
      - Interval between full maintenance runs, in seconds.
    type: int
  list_parallelism:
    description:
      - Override the list parallelism.
      - V(-1) is rejected before kopia runs, also in check mode, as kopia reads
        it as leaving the setting unchanged.
      - Must be from V(-9007199254740992) to V(9007199254740992), the values
        kopia parses without rounding, or the module fails before kopia runs,
        also in check mode.
      - Requires kopia 0.18.0 or later.
    type: int
  max_retained_log_age:
    description:
      - Maximum age of retained log sessions, in seconds.
      - V(0) means no age limit. When O(max_retained_log_age),
        O(max_retained_log_count) and O(max_retained_log_size_mb) are all
        V(0), kopia applies its default log retention instead, 30 days, 10000
        sessions and 1024 megabytes.
    type: int
  max_retained_log_count:
    description:
      - Maximum number of log sessions to retain.
      - V(-1) is rejected before kopia runs, also in check mode, as kopia reads
        it as leaving the setting unchanged.
      - Must be from V(-9007199254740992) to V(9007199254740992), the values
        kopia parses without rounding, or the module fails before kopia runs,
        also in check mode.
      - V(0) means no count limit. When O(max_retained_log_age),
        O(max_retained_log_count) and O(max_retained_log_size_mb) are all
        V(0), kopia applies its default log retention instead, 30 days, 10000
        sessions and 1024 megabytes.
    type: int
  max_retained_log_size_mb:
    description:
      - Maximum total size of retained log sessions, in megabytes.
      - V(-1) is rejected before kopia runs, also in check mode, as kopia reads
        it as leaving the setting unchanged.
      - Must be from V(-8796093022208) to V(8796093022207), the sizes in
        megabytes kopia stores in bytes without overflowing, or the module
        fails before kopia runs, also in check mode.
      - V(0) means no size limit. When O(max_retained_log_age),
        O(max_retained_log_count) and O(max_retained_log_size_mb) are all
        V(0), kopia applies its default log retention instead, 30 days, 10000
        sessions and 1024 megabytes.
    type: int
  owner:
    description:
      - Maintenance owner as C(user@hostname).
      - Must not be empty.
      - kopia resolves the special value V(me) to the client user and host of
        the connection, so V(me) is compared as that C(user@hostname), as
        C(kopia repository status) reports it, also in check mode.
      - An owner that is not valid UTF-8, such as one with a lone surrogate
        code point, is rejected before kopia runs, also in check mode, because
        kopia records it with U+FFFD in its place.
    type: str
  quick_interval:
    description:
      - Interval between quick maintenance runs, in seconds.
    type: int
requirements:
  - kopia
attributes:
  check_mode:
    description: Predicts changes without modifying the target.
    support: full
    details: Reports a potential change without querying current state when kopia is unavailable or no repository is connected.
  diff_mode:
    description: Diff mode is not supported.
    support: none
"""

EXAMPLES = r"""
- name: Ensure kopia maintenance settings are managed
  linuxhq.linux.kopia_maintenance:
    enable_full: true
    enable_quick: true
    full_interval: 86400
    owner: root@server
    quick_interval: 3600

- name: Ensure kopia maintenance log retention is managed
  linuxhq.linux.kopia_maintenance:
    max_retained_log_age: 604800
    max_retained_log_count: 1000
    max_retained_log_size_mb: 512
"""

RETURN = r"""
maintenance:
  description:
    - Maintenance settings reported by C(kopia maintenance info).
    - In check mode, when a change would be made, the settings reported by
      kopia with the requested changes applied, as the module predicts them.
    - Empty when kopia is unavailable or no repository is connected in check
      mode.
    - Empty when the module fails, also for an option value the module rejects
      before kopia runs. Not returned when Ansible rejects the arguments, such
      as a missing required option, a value of the wrong type or an invalid
      choice, or fails to log them, such as for a lone surrogate code point in
      an option that is not secret, or when the kopia command is not found or
      cannot be started, such as for a NUL character in a value passed to it.
  returned: unless Ansible rejects or cannot log the arguments or start kopia
  type: dict
  sample:
    extend_object_locks: false
    full:
      enabled: true
      interval: 86400000000000
    list_parallelism: 0
    log_retention:
      max_age: 2592000000000000
      max_count: 10000
      max_total_size: 1073741824
    owner: root@server
    quick:
      enabled: true
      interval: 3600000000000
    schedule:
      next_full_maintenance: '2026-07-21T22:59:38.254277-07:00'
      next_quick_maintenance: '2026-07-20T23:59:38.254277-07:00'
"""

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    check_connection,
    check_utf8,
    kopia_available,
    kopia_command,
    maintenance_info,
    repository_status,
    same_value,
)

# kopia reads -1 for these flags as not given, so -1 would never be set
UNSET_SENTINEL = ("list_parallelism", "max_retained_log_count", "max_retained_log_size_mb")

# kopia stores max_retained_log_size_mb in bytes, shifting it left by 20 bits in an int64, which wraps outside these
MAX_LOG_SIZE_MB = (2**63 - 1) // 1048576
MIN_LOG_SIZE_MB = -(2**63) // 1048576
# kopia parses these as a float64 before converting them to an int, which rounds or wraps beyond 2**53
FLOAT_PARSED = ("list_parallelism", "max_retained_log_count")
MAX_FLOAT_INT = 2**53
MEGABYTES = 1048576
NANOSECONDS = 1000000000

SETTINGS = [
    ("enable_full", "--enable-full", ("full", "enabled"), "bool"),
    ("enable_quick", "--enable-quick", ("quick", "enabled"), "bool"),
    ("extend_object_locks", "--extend-object-locks", ("extendObjectLocks",), "bool"),
    ("full_interval", "--full-interval", ("full", "interval"), "duration"),
    ("list_parallelism", "--list-parallelism", ("listParallelism",), "int"),
    (
        "max_retained_log_age",
        "--max-retained-log-age",
        ("logRetention", "maxAge"),
        "duration",
    ),
    (
        "max_retained_log_count",
        "--max-retained-log-count",
        ("logRetention", "maxCount"),
        "int",
    ),
    (
        "max_retained_log_size_mb",
        "--max-retained-log-size-mb",
        ("logRetention", "maxTotalSize"),
        "megabytes",
    ),
    ("owner", "--owner", ("owner",), "str"),
    ("quick_interval", "--quick-interval", ("quick", "interval"), "duration"),
]

# kopia applies the log retention flags in this order, each starting from its
# defaults when every stored log retention setting is zero
LOG_RETENTION = ["max_retained_log_count", "max_retained_log_age", "max_retained_log_size_mb"]

LOG_RETENTION_DEFAULTS = {
    "maxAge": 30 * 86400 * NANOSECONDS,
    "maxCount": 10000,
    "maxTotalSize": 1024 * MEGABYTES,
}


def normalize(kind, value):
    if kind == "duration":
        return value * NANOSECONDS

    if kind == "megabytes":
        return value * MEGABYTES

    return value


def flag_value(kind, value):
    if kind == "bool":
        return "true" if value else "false"

    if kind == "duration":
        return f"{value}s"

    return f"{value}"


def log_retention_or_default(retention):
    if all(not retention[key] for key in LOG_RETENTION_DEFAULTS):
        return dict(retention, **LOG_RETENTION_DEFAULTS)

    return dict(retention)


def log_retention_change(module, current):
    settings = {setting[0]: setting for setting in SETTINGS}
    stored = current["logRetention"]
    expected = dict(stored)
    flags = []

    for param in LOG_RETENTION:
        value = module.params[param]
        if value is None:
            continue

        _dummy, flag, path, kind = settings[param]
        expected = log_retention_or_default(expected)
        expected[path[-1]] = normalize(kind, value)
        flags.append(f"{flag}={flag_value(kind, value)}")

    if same_value(expected, stored):
        return None, []

    return expected, flags


def owner_me(module, status):
    """Return the owner kopia sets for "me", the client user and host of the connection, reading status when None."""
    if status is None:
        status = repository_status(module, failed_result={"maintenance": {}})

    if status is None:
        module.fail_json(msg="unable to resolve the maintenance owner me: repository is not connected", maintenance={})

    return "{username}@{hostname}".format(**status["clientOptions"])


def validate_settings(module):
    check_connection(module, failed_result={"maintenance": {}})

    for param in UNSET_SENTINEL:
        if module.params[param] == -1:
            module.fail_json(msg=f"invalid {param} -1: kopia reads it as not given, so it is never set", maintenance={})

    size = module.params["max_retained_log_size_mb"]
    if size is not None and not MIN_LOG_SIZE_MB <= size <= MAX_LOG_SIZE_MB:
        module.fail_json(
            msg=f"invalid max_retained_log_size_mb {size}: it must be from {MIN_LOG_SIZE_MB} to {MAX_LOG_SIZE_MB}",
            maintenance={},
        )

    for param in FLOAT_PARSED:
        value = module.params[param]
        if value is not None and not -MAX_FLOAT_INT <= value <= MAX_FLOAT_INT:
            module.fail_json(
                msg=f"invalid {param} {value}: it must be from {-MAX_FLOAT_INT} to {MAX_FLOAT_INT}",
                maintenance={},
            )

    # kopia ignores an empty --owner, so the owner would never be set
    if module.params["owner"] == "":
        module.fail_json(msg="invalid owner: it must not be empty", maintenance={})

    # kopia stores an owner with U+FFFD in place of bytes that are not valid UTF-8, and run_command cannot pass
    # U+D800 to U+DC7F to kopia
    check_utf8(module, [("owner", module.params["owner"])], failed_result={"maintenance": {}})


def ensure_present(module):
    validate_settings(module)

    status = None

    # an earlier task in check mode, such as kopia_repository, may only have predicted the connection
    if module.check_mode:
        if kopia_available(module):
            status = repository_status(module, failed_result={"maintenance": {}})

        if status is None:
            module.exit_json(changed=True, maintenance={})

    current = maintenance_info(module, failed_result={"maintenance": {}})
    predicted = deepcopy(current)
    flags = []

    for param, flag, path, kind in SETTINGS:
        value = module.params[param]
        if value is None or param in LOG_RETENTION:
            continue

        # kopia sets "me" as the client user and host of the connection, which never equal "me"
        if param == "owner" and value == "me":
            value = owner_me(module, status)

        # kopia before 0.14 reports no extendObjectLocks and before 0.18 no listParallelism, as it has no such setting
        node = predicted
        for key in path[:-1]:
            node = node.setdefault(key, {})

        desired = normalize(kind, value)
        if path[-1] not in node or not same_value(node[path[-1]], desired):
            node[path[-1]] = desired
            flags.append(f"{flag}={flag_value(kind, value)}")

    retention, retention_flags = log_retention_change(module, current)
    if retention_flags:
        predicted["logRetention"] = retention
        flags.extend(retention_flags)

    if not flags:
        module.exit_json(changed=False, maintenance=camel_dict_to_snake_dict(current))

    if module.check_mode:
        module.exit_json(changed=True, maintenance=camel_dict_to_snake_dict(predicted))

    rc, _dummy, stderr = kopia_command(module, ["maintenance", "set"] + flags)

    if rc != 0:
        module.fail_json(msg=f"unable to set kopia maintenance settings: {stderr.strip()}", maintenance={})

    current = maintenance_info(module, failed_result={"changed": True, "maintenance": {}})

    module.exit_json(changed=True, maintenance=camel_dict_to_snake_dict(current))


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "enable_full": {"type": "bool"},
        "enable_quick": {"type": "bool"},
        "extend_object_locks": {"type": "bool"},
        "full_interval": {"type": "int"},
        "list_parallelism": {"type": "int"},
        "max_retained_log_age": {"type": "int"},
        "max_retained_log_count": {"type": "int"},
        "max_retained_log_size_mb": {"type": "int"},
        "owner": {"type": "str"},
        "quick_interval": {"type": "int"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[[setting[0] for setting in SETTINGS]],
        supports_check_mode=True,
    )

    ensure_present(module)


if __name__ == "__main__":
    main()
