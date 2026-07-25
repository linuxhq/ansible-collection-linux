# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_maintenance_info
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.3.0
short_description: Gather kopia repository maintenance settings
description:
  - Gather the maintenance settings and schedule of the connected kopia
    repository from C(kopia maintenance info).
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
    type: path
requirements:
  - kopia
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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict
from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    maintenance_info,
)


def info(module):
    maintenance = maintenance_info(module)

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
