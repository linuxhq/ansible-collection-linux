#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_repository_info
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Gather kopia repository status
description:
  - Gather the repository connection status from C(kopia repository status).
  - A host that is not connected to a repository returns RV(connected=false)
    with an empty RV(repository), it is not an error.
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
  description:
    - Whether the host is connected to a kopia repository.
    - Not returned when the module fails, as the connection state is then
      unknown, nor when kopia is unavailable in check mode.
  returned: success, unless kopia is unavailable in check mode
  type: bool
  sample: true
repository:
  description:
    - Repository status reported by C(kopia repository status).
    - Empty when the module fails, and when kopia is unavailable in check mode.
      Not returned when Ansible rejects the arguments, such as a missing
      required option, a value of the wrong type or an invalid choice, or fails
      to log them, such as for a lone surrogate code point in an option that is
      not secret, or when the kopia command is not found or cannot be started,
      such as for a NUL character in a value passed to it.
  returned: unless Ansible rejects or cannot log the arguments or start kopia
  type: dict
  contains:
    blob_retention:
      description:
        - Blob retention of the repository.
        - Its fields are passed through.
      returned: always
      type: dict
    client_options:
      description:
        - Options of the client connection.
        - Other fields kopia reports are passed through.
      returned: always
      type: dict
      contains:
        description:
          description:
            - Description of the connection.
          returned: when set
          type: str
        enable_actions:
          description:
            - Whether snapshot actions run.
          returned: always
          type: bool
        format_blob_cache_duration:
          description:
            - Nanoseconds the repository format is cached.
          returned: when set
          type: int
        hostname:
          description:
            - Host name the client records in its snapshots.
          returned: always
          type: str
        readonly:
          description:
            - Whether the connection is read-only.
          returned: when the connection is read-only
          type: bool
        username:
          description:
            - User name the client records in its snapshots.
          returned: always
          type: str
    config_file:
      description:
        - Configuration file of the connection.
      returned: always
      type: str
    content_format:
      description:
        - Format of the repository contents.
        - Other fields kopia reports are passed through.
      returned: always
      type: dict
      contains:
        enable_password_change:
          description:
            - Whether the repository password can be changed.
          returned: always
          type: bool
        encryption:
          description:
            - Encryption algorithm.
          returned: always
          type: str
        epoch_parameters:
          description:
            - Parameters of the epoch manager.
            - Its fields are passed through.
          returned: always
          type: dict
        hash:
          description:
            - Hash algorithm.
          returned: always
          type: str
        index_version:
          description:
            - Version of the index format.
          returned: when kopia reports it
          type: int
        max_pack_size:
          description:
            - Size in bytes of the largest pack.
          returned: when kopia reports it
          type: int
        version:
          description:
            - Version of the repository format.
          returned: always
          type: int
    object_format:
      description:
        - Format of the repository objects.
      returned: always
      type: dict
      contains:
        splitter:
          description:
            - Splitter algorithm.
          returned: always
          type: str
    storage:
      description:
        - Storage of the repository.
      returned: always
      type: dict
      contains:
        config:
          description:
            - Configuration of the storage, whose fields depend on its type and
              are passed through.
          returned: always
          type: dict
        type:
          description:
            - Storage type, such as C(filesystem) or C(s3).
          returned: always
          type: str
    unique_id_hex:
      description:
        - Unique ID of the repository in hexadecimal.
      returned: always
      type: str
    volume:
      description:
        - Capacity of the storage volume.
      returned: when the storage reports it
      type: dict
      contains:
        available:
          description:
            - Bytes available.
          returned: always
          type: int
        capacity:
          description:
            - Bytes in all.
          returned: always
          type: int
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
    unique_id_hex: 0f5b8a29110e21bf6bd1e81e7a807933b0c40f3478064e63f63f7d253c785a9b
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    check_connection,
    kopia_available,
    repository_status,
)


def info(module):
    check_connection(module, failed_result={"repository": {}})

    # whether the host is connected is unknown without kopia, so it is left out
    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=False, repository={})

    status = repository_status(module, failed_result={"repository": {}})

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
