# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_maintenance
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.3.0
short_description: Manage kopia repository maintenance settings
description:
  - Manage the maintenance settings of the connected kopia repository.
  - Settings are compared against C(kopia maintenance info) and only applied
    with C(kopia maintenance set) when they differ, options left unset are not
    touched.
  - At least one setting option besides O(config_file) is required.
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
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
    description: Interval between full maintenance runs, in seconds.
    type: int
  list_parallelism:
    description: Override the list parallelism.
    type: int
  max_retained_log_age:
    description: Maximum age of retained log sessions, in seconds.
    type: int
  max_retained_log_count:
    description: Maximum number of log sessions to retain.
    type: int
  max_retained_log_size_mb:
    description: Maximum total size of retained log sessions, in megabytes.
    type: int
  owner:
    description:
      - Maintenance owner as C(user@hostname).
      - kopia resolves the special value V(me) to the current user and host at
        set time, so V(me) always reports a change, prefer the explicit form.
    type: str
  quick_interval:
    description: Interval between quick maintenance runs, in seconds.
    type: int
requirements:
  - kopia
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
    kopia_command,
    maintenance_info,
)

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


def ensure_present(module):
    current = maintenance_info(module)
    predicted = deepcopy(current)
    flags = []

    for param, flag, path, kind in SETTINGS:
        value = module.params[param]
        if value is None:
            continue

        node = predicted
        for key in path[:-1]:
            node = node.setdefault(key, {})

        desired = normalize(kind, value)
        if node.get(path[-1]) != desired:
            node[path[-1]] = desired
            flags.append(f"{flag}={flag_value(kind, value)}")

    if not flags:
        module.exit_json(changed=False, maintenance=camel_dict_to_snake_dict(current))

    if module.check_mode:
        module.exit_json(changed=True, maintenance=camel_dict_to_snake_dict(predicted))

    rc, _dummy, stderr = kopia_command(module, ["maintenance", "set"] + flags)

    if rc != 0:
        module.fail_json(
            msg=f"unable to set kopia maintenance settings: {stderr.strip()}"
        )

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
