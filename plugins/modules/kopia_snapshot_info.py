# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_snapshot_info
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.3.0
short_description: Gather information about kopia snapshots
description:
  - Gather the snapshots held in the connected kopia repository, as reported by
    C(kopia snapshot list).
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
    type: path
  password:
    description:
      - Password securing the kopia repository.
      - Only needed when the repository configuration does not already hold the
        key, and exported to the kopia CLI as E(KOPIA_PASSWORD) rather than
        placed on the command line.
    type: str
  path:
    description:
      - Restrict the result to snapshots of this local path.
      - All sources are listed when unset.
    type: path
requirements:
  - kopia
"""

EXAMPLES = r"""
- name: Gather all kopia snapshots
  linuxhq.linux.kopia_snapshot_info:
  register: __kopia_snapshot_query

- name: Gather kopia snapshots for one path
  linuxhq.linux.kopia_snapshot_info:
    path: /home/vagrant
  register: __kopia_snapshot_query
"""

RETURN = r"""
snapshots:
  description: Snapshots reported by C(kopia snapshot list), oldest first.
  returned: always
  type: list
  elements: dict
  sample:
    - id: k9c8f0b1c2d3e4f5
      description: nightly
      source:
        host: server
        path: /home/vagrant
        user_name: root
      start_time: '2026-07-25T10:15:00.000000-07:00'
      end_time: '2026-07-25T10:15:04.000000-07:00'
"""

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict
from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    kopia_available,
    kopia_command,
)


def list_snapshots(module):
    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=False, snapshots=[])

    command = ["snapshot", "list", "--json"]

    if module.params["path"]:
        command.append(module.params["path"])

    rc, stdout, stderr = kopia_command(
        module, command, password=module.params["password"]
    )

    if rc != 0:
        module.fail_json(msg=f"unable to list kopia snapshots: {stderr.strip()}")

    try:
        snapshots = json.loads(stdout)
    except ValueError:
        module.fail_json(
            msg=f"unable to parse kopia snapshot list output: {stdout.strip()}"
        )

    return [camel_dict_to_snake_dict(snapshot) for snapshot in snapshots or []]


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "password": {"type": "str", "no_log": True},
        "path": {"type": "path"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    module.exit_json(changed=False, snapshots=list_snapshots(module))


if __name__ == "__main__":
    main()
