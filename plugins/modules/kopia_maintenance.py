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
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
    type: path
  enable_full:
    description: Enable or disable periodic full maintenance.
    type: bool
  enable_quick:
    description: Enable or disable periodic quick maintenance.
    type: bool
  extend_object_locks:
    description: Extend the retention period of locked objects as needed.
    type: bool
  full_interval:
    description:
      - Interval between full maintenance runs, in seconds.
      - Must not be negative.
    type: int
  list_parallelism:
    description:
      - Override the list parallelism.
      - Must not be negative, kopia reads V(-1) as leaving it unset.
      - Requires kopia 0.18.0 or later.
    type: int
  max_retained_log_age:
    description:
      - Maximum age of retained log sessions, in seconds.
      - Must not be negative.
      - V(0) means no age limit. When O(max_retained_log_age),
        O(max_retained_log_count) and O(max_retained_log_size_mb) are all
        V(0), kopia applies its default log retention instead, 30 days, 10000
        sessions and 1024 megabytes.
    type: int
  max_retained_log_count:
    description:
      - Maximum number of log sessions to retain.
      - Must not be negative, kopia reads V(-1) as leaving it unset.
      - V(0) means no count limit. When O(max_retained_log_age),
        O(max_retained_log_count) and O(max_retained_log_size_mb) are all
        V(0), kopia applies its default log retention instead, 30 days, 10000
        sessions and 1024 megabytes.
    type: int
  max_retained_log_size_mb:
    description:
      - Maximum total size of retained log sessions, in megabytes.
      - Must not be negative, kopia reads V(-1) as leaving it unset.
      - V(0) means no size limit. When O(max_retained_log_age),
        O(max_retained_log_count) and O(max_retained_log_size_mb) are all
        V(0), kopia applies its default log retention instead, 30 days, 10000
        sessions and 1024 megabytes.
    type: int
  owner:
    description:
      - Maintenance owner as C(user@hostname).
      - kopia resolves the special value V(me) to the current user and host at
        set time, so V(me) always reports a change, prefer the explicit form.
    type: str
  quick_interval:
    description:
      - Interval between quick maintenance runs, in seconds.
      - Must not be negative.
    type: int
requirements:
  - kopia
attributes:
  check_mode:
    description: Predicts changes without modifying the target.
    support: full
    details: Reports a potential change without querying current state when Kopia is unavailable.
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
  description: Maintenance settings reported by C(kopia maintenance info).
  returned: always
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
    kopia_available,
    kopia_command,
    maintenance_info,
    same_value,
)

INTEGER_KINDS = ("duration", "int", "megabytes")
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
    if all(not retention.get(key) for key in LOG_RETENTION_DEFAULTS):
        return dict(retention, **LOG_RETENTION_DEFAULTS)

    return dict(retention)


def log_retention_change(module, current):
    settings = {setting[0]: setting for setting in SETTINGS}
    stored = current.get("logRetention") or {}
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


def validate_settings(module):
    for param, _dummy, _dummy, kind in SETTINGS:
        value = module.params[param]

        if kind in INTEGER_KINDS and value is not None and value < 0:
            module.fail_json(msg=f"invalid {param} {value}: it must not be negative")


def ensure_present(module):
    validate_settings(module)

    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=True, maintenance={})

    current = maintenance_info(module)
    predicted = deepcopy(current)
    flags = []

    for param, flag, path, kind in SETTINGS:
        value = module.params[param]
        if value is None or param in LOG_RETENTION:
            continue

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
        module.fail_json(msg=f"unable to set kopia maintenance settings: {stderr.strip()}")

    current = maintenance_info(module)

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
