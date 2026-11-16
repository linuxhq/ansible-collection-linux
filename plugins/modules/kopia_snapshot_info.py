#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_snapshot_info
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Gather information about kopia snapshots
description:
  - Gather the snapshots held in the connected kopia repository, as reported by
    C(kopia snapshot list).
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
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
      - C(kopia snapshot list) also includes the snapshots of every parent
        directory of the path, since they contain it, so the result can hold
        more than one source.
      - All sources are listed when unset.
      - Made absolute and cleaned, as kopia does, and listed by that path, to
        which kopia adds the client user and host. kopia reads a bare path in
        which an V(@) comes before any V(:) as C(user@host) or
        C(user@host:path), so when the absolute path is such a path, such as
        V(/home/alice@example.com), it is listed as the source
        C(user@host:/path), with the client user and host reported by
        C(kopia repository status), as kopia records it. A path with a V(:)
        before its first V(@), such as V(/srv/a:b@c), is read as a path.
      - kopia splits C(user@host:/path) at the first V(@) and the first V(:), so
        the module fails when the absolute path is one in which an V(@) comes
        before any V(:) and the client user contains V(@) or V(:), such as
        V(alice@corp.example.com), or the host contains V(:).
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
      - A path that is not valid UTF-8, such as one with a lone surrogate code
        point, which Ansible uses for a byte that is not valid UTF-8, is
        rejected before kopia runs, also in check mode, because kopia records
        it with U+FFFD in its place and cannot list its snapshots.
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
  description:
    - Snapshots reported by C(kopia snapshot list), grouped by source and
      oldest first within each source.
    - With O(path), the snapshots of its parent directories are included as
      well, each under its own C(source).
    - Keys under C(tags) are returned as kopia reports them, such as
      C(tag:role).
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
    check_utf8,
    kopia_available,
    kopia_command,
    snapshot_source,
)


def list_snapshots(module):
    check_utf8(module, [("path", module.params["path"])])

    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=False, snapshots=[])

    command = ["snapshot", "list", "--json"]
    source = ""

    if module.params["path"]:
        source = f" of {module.params['path']}"
        command.extend(["--", snapshot_source(module, module.params["path"], "list kopia snapshots")])

    rc, stdout, stderr = kopia_command(module, command, password=module.params["password"])

    if rc != 0:
        module.fail_json(msg=f"unable to list kopia snapshots{source}: {stderr.strip()}")

    try:
        snapshots = json.loads(stdout)
    except ValueError:
        module.fail_json(msg=f"unable to parse kopia snapshot list output{source}: {stdout.strip()}")

    return [camel_dict_to_snake_dict(snapshot, ignore_list=["tags"]) for snapshot in snapshots or []]


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
