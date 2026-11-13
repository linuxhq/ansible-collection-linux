#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_snapshot
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Create a kopia snapshot
description:
  - Create a snapshot of a local path in the connected kopia repository.
  - The module is deliberately one-shot. Every run takes a new snapshot and
    reports RV(ignore:changed) as V(true), the same way C(kopia snapshot create)
    behaves, so it is not idempotent and belongs in a play that is meant to run
    on a schedule rather than in a converge that is expected to settle.
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
    type: path
  description:
    description:
      - Description recorded on the snapshot.
    type: str
  password:
    description:
      - Password securing the kopia repository.
      - Only needed when the repository configuration does not already hold the
        key, and exported to the kopia CLI as E(KOPIA_PASSWORD) rather than
        placed on the command line.
    type: str
  path:
    description:
      - Local path to snapshot.
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
    type: path
    required: true
  tags:
    description:
      - Tags to record on the snapshot.
      - Each entry becomes one C(--tags key:value) flag, with the key used as
        given.
      - kopia splits each flag at its first V(:), so a key containing V(:) is
        rejected before kopia runs. Values may contain V(:).
    type: dict
requirements:
  - kopia
attributes:
  check_mode:
    description: Reports changed without creating a snapshot.
    support: full
  diff_mode:
    description: Diff mode is not supported.
    support: none
"""

EXAMPLES = r"""
- name: Ensure kopia snapshot is created
  linuxhq.linux.kopia_snapshot:
    path: /home/vagrant

- name: Ensure kopia snapshot is created with a description and tags
  linuxhq.linux.kopia_snapshot:
    description: nightly
    path: /srv/data
    tags:
      role: database
      tier: production
"""

RETURN = r"""
snapshot:
  description:
    - Newest snapshot for the path, reported by C(kopia snapshot list).
    - Keys under C(tags) are returned as kopia reports them, such as
      C(tag:role).
    - Empty in check mode and when the snapshot manifest cannot be read back.
  returned: always
  type: dict
  sample:
    id: k9c8f0b1c2d3e4f5
    description: nightly
    start_time: '2026-07-25T10:15:00.000000-07:00'
    end_time: '2026-07-25T10:15:04.000000-07:00'
    stats:
      total_size: 10485760
"""

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import kopia_command


def latest_snapshot(module, path):
    rc, stdout, _dummy = kopia_command(module, ["snapshot", "list", path, "--json"], password=module.params["password"])

    if rc != 0:
        return {}

    try:
        snapshots = json.loads(stdout)
    except ValueError:
        return {}

    if not snapshots:
        return {}

    return camel_dict_to_snake_dict(snapshots[-1], ignore_list=["tags"])


def ensure_present(module):
    path = module.params["path"]

    for key in module.params["tags"] or {}:
        if ":" in key:
            module.fail_json(msg=f"invalid tag key {key!r}: kopia splits tags at the first ':'")

    if module.check_mode:
        module.exit_json(changed=True, snapshot={})

    command = ["snapshot", "create", path]

    if module.params["description"]:
        command.append(f"--description={module.params['description']}")

    for key, value in sorted((module.params["tags"] or {}).items()):
        command.append(f"--tags={key}:{value}")

    rc, _dummy, stderr = kopia_command(module, command, password=module.params["password"])

    if rc != 0:
        module.fail_json(msg=f"unable to create kopia snapshot: {stderr.strip()}")

    module.exit_json(changed=True, snapshot=latest_snapshot(module, path))


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "description": {"type": "str"},
        "password": {"type": "str", "no_log": True},
        "path": {"type": "path", "required": True},
        "tags": {"type": "dict"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    ensure_present(module)


if __name__ == "__main__":
    main()
