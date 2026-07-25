# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_repository_info
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.3.0
short_description: Gather kopia repository status
description:
  - Gather the repository connection status from C(kopia repository status).
  - A host that is not connected to a repository returns RV(connected=false)
    with an empty RV(repository), it is not an error.
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
- name: Ensure kopia repository status is gathered
  linuxhq.linux.kopia_repository_info:
  register: __kopia_repository_query

- name: Ensure kopia repository status is gathered from an alternate config
  linuxhq.linux.kopia_repository_info:
    config_file: /etc/kopia/repository.config
  register: __kopia_repository_query
"""

RETURN = r"""
connected:
  description: Whether the host is connected to a kopia repository.
  returned: always
  type: bool
  sample: true
repository:
  description: Repository status reported by C(kopia repository status).
  returned: always
  type: dict
  sample:
    config_file: /root/.config/kopia/repository.config
    client_options:
      description: "Repository in Filesystem: /srv/backup/kopia"
      enable_actions: false
      hostname: server
      username: root
    content_format:
      enable_password_change: true
      encryption: AES256-GCM-HMAC-SHA256
      hash: BLAKE2B-256-128
      version: 3
    storage:
      type: filesystem
      config:
        path: /srv/backup/kopia
    unique_id_hex: 557e318faad94ead
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict
from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    kopia_available,
    repository_status,
)


def info(module):
    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=False, connected=False, repository={})

    status = repository_status(module)

    module.exit_json(
        changed=False,
        connected=status is not None,
        repository=camel_dict_to_snake_dict(status or {}),
    )


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
