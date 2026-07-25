# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_repository
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.3.0
short_description: Manage the kopia repository connection
description:
  - Connect the host to a kopia repository, creating the repository when the
    storage location has not been initialized yet, or disconnect from it.
  - The module is idempotent on the connection state reported by
    C(kopia repository status), so an already connected host is left untouched.
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
    type: path
  options:
    description:
      - Storage provider flags passed to C(kopia repository create) and
        C(kopia repository connect), given as snake_case keys.
      - Each key becomes the matching kebab-case CLI flag, so V(bucket) becomes
        C(--bucket) and V(storage_account) becomes C(--storage-account).
      - Booleans toggle the flag, V(true) emits C(--flag) and V(false) emits
        C(--no-flag), and a list repeats the flag once per element.
      - Put credential-carrying flags in O(secrets) instead so they stay out of
        logs.
    type: dict
    default: {}
  password:
    description:
      - Password securing the kopia repository.
      - Exported to the kopia CLI as E(KOPIA_PASSWORD), never on the command
        line.
      - Required when O(state=present).
    type: str
  secrets:
    description:
      - Storage provider flags whose values are secrets, such as
        V(secret_access_key) or V(key).
      - Converted to CLI flags exactly like O(options), but kept out of logs.
    type: dict
    default: {}
  state:
    description:
      - V(present) connects the host to the repository, creating it first when
        the storage location is empty.
      - V(absent) disconnects the host from the repository.
    type: str
    choices:
      - absent
      - present
    default: present
  storage:
    description:
      - Storage provider backing the repository.
      - Required when O(state=present).
    type: str
    choices:
      - azure
      - b2
      - filesystem
      - from-config
      - gcs
      - gdrive
      - rclone
      - s3
      - sftp
      - webdav
  validate_provider:
    description:
      - Run C(kopia repository validate-provider) after creating a repository.
      - Only runs on creation, never for an existing repository.
    type: bool
    default: false
requirements:
  - kopia
"""

EXAMPLES = r"""
- name: Ensure kopia filesystem repository is present
  linuxhq.linux.kopia_repository:
    password: "{{ kopia_password }}"
    state: present
    storage: filesystem
    options:
      path: /srv/backup/kopia

- name: Ensure kopia s3 repository is present
  linuxhq.linux.kopia_repository:
    password: "{{ kopia_password }}"
    state: present
    storage: s3
    options:
      bucket: vagrant-kopia-backup
      endpoint: s3.us-west-1.amazonaws.com
      prefix: vagrant/
      region: us-west-1
    secrets:
      access_key: "{{ lookup('ansible.builtin.env', 'AWS_ACCESS_KEY_ID') }}"
      secret_access_key: "{{ lookup('ansible.builtin.env', 'AWS_SECRET_ACCESS_KEY') }}"
    validate_provider: true

- name: Ensure kopia repository is absent
  linuxhq.linux.kopia_repository:
    state: absent
"""

RETURN = r"""
repository:
  description: Repository status reported by C(kopia repository status).
  returned: when connected
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
    kopia_command,
    kopia_flags,
    repository_status,
)


def ensure_present(module):
    status = repository_status(module)

    if status is not None:
        module.exit_json(changed=False, repository=camel_dict_to_snake_dict(status))

    if module.check_mode:
        module.exit_json(changed=True, repository={})

    options = dict(module.params["options"])
    options.update(module.params["secrets"])
    target = [module.params["storage"]] + kopia_flags(options)
    password = module.params["password"]

    rc, _dummy, stderr = kopia_command(
        module, ["repository", "connect"] + target, password=password
    )

    if rc != 0 and "repository not initialized" in stderr:
        rc, _dummy, stderr = kopia_command(
            module, ["repository", "create"] + target, password=password
        )
        if rc == 0 and module.params["validate_provider"]:
            rc, _dummy, stderr = kopia_command(
                module, ["repository", "validate-provider"], password=password
            )

    if rc != 0:
        module.fail_json(msg=f"unable to connect to kopia repository: {stderr.strip()}")

    status = repository_status(module)

    module.exit_json(changed=True, repository=camel_dict_to_snake_dict(status or {}))


def ensure_absent(module):
    status = repository_status(module)

    if status is None:
        module.exit_json(changed=False)

    if module.check_mode:
        module.exit_json(changed=True)

    rc, _dummy, stderr = kopia_command(module, ["repository", "disconnect"])

    if rc != 0:
        module.fail_json(
            msg=f"unable to disconnect from kopia repository: {stderr.strip()}"
        )

    module.exit_json(changed=True)


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "options": {"type": "dict", "default": {}},
        "password": {"type": "str", "no_log": True},
        "secrets": {"type": "dict", "default": {}, "no_log": True},
        "state": {
            "type": "str",
            "choices": ["absent", "present"],
            "default": "present",
        },
        "storage": {
            "type": "str",
            "choices": [
                "azure",
                "b2",
                "filesystem",
                "from-config",
                "gcs",
                "gdrive",
                "rclone",
                "s3",
                "sftp",
                "webdav",
            ],
        },
        "validate_provider": {"type": "bool", "default": False},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[("state", "present", ("password", "storage"))],
        supports_check_mode=True,
    )

    if module.params["state"] == "present":
        ensure_present(module)

    ensure_absent(module)


if __name__ == "__main__":
    main()
