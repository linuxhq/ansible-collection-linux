#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_maintenance_info
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Gather kopia repository maintenance settings
description:
  - Gather the maintenance settings and schedule of the connected kopia
    repository from C(kopia maintenance info).
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
requirements:
  - kopia >= 0.12.0
attributes:
  check_mode:
    description: This module only retrieves information and does not modify state.
    support: full
    details: Returns empty result data when kopia is unavailable or no repository is connected.
  diff_mode:
    description: Diff mode is not supported.
    support: none
"""

EXAMPLES = r"""
- name: Ensure kopia maintenance settings are gathered
  linuxhq.linux.kopia_maintenance_info:
  register: __kopia_maintenance_query
"""

RETURN = r"""
maintenance:
  description:
    - Maintenance settings reported by C(kopia maintenance info).
    - Durations are in nanoseconds and sizes in bytes, as reported by kopia.
    - Empty when the module fails, and when kopia is unavailable or no
      repository is connected in check mode.
      Not returned when Ansible rejects the arguments, such as a missing
      required option, a value of the wrong type or an invalid choice, or fails
      to log them, such as for a lone surrogate code point in an option that is
      not secret, or when the kopia command is not found or cannot be started,
      such as for a NUL character in a value passed to it.
  returned: unless Ansible rejects or cannot log the arguments or start kopia
  type: dict
  contains:
    extend_object_locks:
      description:
        - Whether maintenance extends object locks.
      returned: with kopia 0.14.0 or later
      type: bool
    full:
      description:
        - Full maintenance cycle.
      returned: always
      type: dict
      contains:
        enabled:
          description:
            - Whether the cycle is enabled.
          returned: always
          type: bool
        interval:
          description:
            - Interval of the cycle in nanoseconds.
          returned: always
          type: int
    list_parallelism:
      description:
        - Number of parallel listings, C(0) for kopia's default.
      returned: with kopia 0.18.0 or later
      type: int
    log_retention:
      description:
        - Retention of kopia's logs in the repository.
      returned: always
      type: dict
      contains:
        max_age:
          description:
            - Age in nanoseconds above which logs are deleted.
          returned: always
          type: int
        max_count:
          description:
            - Number of logs kept.
          returned: always
          type: int
        max_total_size:
          description:
            - Total size in bytes of the logs kept.
          returned: always
          type: int
    owner:
      description:
        - User and host, as C(user@host), that runs maintenance.
      returned: always
      type: str
    quick:
      description:
        - Quick maintenance cycle.
      returned: always
      type: dict
      contains:
        enabled:
          description:
            - Whether the cycle is enabled.
          returned: always
          type: bool
        interval:
          description:
            - Interval of the cycle in nanoseconds.
          returned: always
          type: int
    schedule:
      description:
        - Maintenance schedule and history.
      returned: always
      type: dict
      contains:
        next_full_maintenance:
          description:
            - Time of the next full maintenance, in RFC 3339 with nanoseconds.
          returned: always
          type: str
        next_quick_maintenance:
          description:
            - Time of the next quick maintenance, in RFC 3339 with nanoseconds.
          returned: always
          type: str
        runs:
          description:
            - Recent runs of each maintenance task, keyed by the task kopia
              names, such as C(snapshot-gc), newest first.
            - Each run is a dictionary with its C(start) and C(end) times, in
              RFC 3339 with nanoseconds, C(success) set to V(true) when it
              succeeded, C(error) when it failed, and C(extra), the statistics
              kopia reports, passed through.
          returned: always, as V(none) when kopia has recorded no run
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
      next_full_maintenance: '2026-11-20T08:43:23.044209127Z'
      next_quick_maintenance: '2026-11-19T09:43:23.04420921Z'
      runs:
        snapshot-gc:
          - end: '2026-11-19T08:43:23.04546328Z'
            extra:
              - data:
                  deleted_content_count: 0
                  deleted_content_size: 0
                  in_use_content_count: 0
                  in_use_content_size: 0
                  in_use_system_content_count: 2
                  in_use_system_content_size: 1030
                  recovered_content_count: 0
                  recovered_content_size: 0
                  unreferenced_content_count: 0
                  unreferenced_content_size: 0
                  unreferenced_recent_content_count: 0
                  unreferenced_recent_content_size: 0
                kind: snapshotGCStats
            start: '2026-11-19T08:43:23.04525815Z'
            success: true
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    check_connection,
    kopia_available,
    maintenance_info,
    repository_connected,
)


def info(module):
    check_connection(module, failed_result={"maintenance": {}})

    # an earlier task in check mode, such as kopia_repository, may only have predicted the connection
    if module.check_mode and not (
        kopia_available(module) and repository_connected(module, failed_result={"maintenance": {}})
    ):
        module.exit_json(changed=False, maintenance={})

    maintenance = maintenance_info(module, failed_result={"maintenance": {}})

    module.exit_json(changed=False, maintenance=camel_dict_to_snake_dict(maintenance))


def main():
    module = AnsibleModule(
        argument_spec={
            "config_file": {"type": "path"},
        },
        supports_check_mode=True,
    )

    info(module)


if __name__ == "__main__":
    main()
