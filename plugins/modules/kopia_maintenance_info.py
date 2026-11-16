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
      - The module fails before kopia runs, also in check mode, when the file,
        or kopia's default one when this is unset, is a FIFO or a character
        device, on which kopia can wait forever. So is the password file kopia
        reads, named after the file with
        C(.kopia-password) added. kopia reports any other file it cannot read,
        such as a directory.
      - A path with a NUL character, which the module cannot look up, or a
        lone surrogate code point from U+D800 to U+DC7F, which cannot be passed
        to kopia, is rejected before kopia runs, also in check mode. U+DC80 to
        U+DCFF, which Ansible uses for bytes that are not valid UTF-8, are
        passed as those bytes.
    type: path
requirements:
  - kopia
attributes:
  check_mode:
    description: This module only retrieves information and does not modify state.
    support: full
    details: Returns empty result data when Kopia is unavailable.
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
    - Empty when the module fails, and when kopia is unavailable in check mode.
      Not returned when Ansible rejects the arguments, such as a missing
      required option, a value of the wrong type or an invalid choice, or fails
      to log them, such as for a lone surrogate code point in an option that is
      not secret, or when the kopia command is not found or cannot be started,
      such as for a NUL character in a value passed to it.
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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    check_connection,
    kopia_available,
    maintenance_info,
)


def info(module):
    check_connection(module, failed_result={"maintenance": {}})

    if module.check_mode and not kopia_available(module):
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
