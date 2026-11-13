#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_repository
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Manage the kopia repository connection
description:
  - Connect the host to a kopia repository, creating the repository when the
    storage location has not been initialized yet.
  - For V(filesystem) storage, a C(path) that does not exist yet is created
    along with the repository.
  - The module is idempotent on the connection state reported by
    C(kopia repository status), so a host already connected to the repository
    is left untouched.
  - A host connected to a different repository fails rather than being
    reconnected. The connection is different when its storage type differs
    from O(storage), or when one of the O(options) C(bucket), C(container),
    C(endpoint), C(folder_id), C(host), C(path), C(prefix), C(remote_path),
    C(storage_account) or C(url) differs from the connected storage
    configuration. A leading V(~) in the C(path) of V(filesystem) storage is
    resolved to the home directory first, as kopia does. Disconnect it with
    C(kopia repository disconnect) first to switch repositories.
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
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
      - Values are passed to kopia as given, so the module does not expand V(~)
        or environment variables in them.
    type: dict
    default: {}
  password:
    description:
      - Password securing the kopia repository.
      - Exported to the kopia CLI as E(KOPIA_PASSWORD), never on the command
        line.
      - Also used to read the connection status, so a connection made with
        V(persist_credentials) set to V(false) in O(options) is recognized.
    type: str
    required: true
  secrets:
    description:
      - Storage provider flags whose values are secrets, such as
        V(secret_access_key) or V(key).
      - Converted to CLI flags exactly like O(options), but kept out of logs.
    type: dict
    default: {}
  storage:
    description:
      - Storage provider backing the repository.
      - V(from-config) only connects to an existing repository described by a
        configuration file or token, it cannot create one.
    type: str
    required: true
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
      - Only runs in the run that creates the repository, never for an existing
        repository. When it fails, the repository has already been created and
        a later run does not retry the validation.
    type: bool
    default: false
requirements:
  - kopia
attributes:
  check_mode:
    description: Predicts changes without modifying the target.
    support: full
    details: Reports a potential change without querying current state when Kopia is unavailable.
  diff_mode:
    description: Diff mode is not supported.
    support: none
"""

EXAMPLES = r"""
- name: Ensure kopia filesystem repository is present
  linuxhq.linux.kopia_repository:
    password: "{{ kopia_password }}"
    storage: filesystem
    options:
      path: /srv/backup/kopia

- name: Ensure kopia s3 repository is present
  linuxhq.linux.kopia_repository:
    password: "{{ kopia_password }}"
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
"""

RETURN = r"""
repository:
  description:
    - Repository status reported by C(kopia repository status).
    - Empty in check mode when a connection would be made, and when kopia is
      unavailable in check mode.
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

import os

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    kopia_available,
    kopia_command,
    kopia_flags,
    repository_status,
)

STORAGE_KEYS = {
    "bucket": "bucket",
    "container": "container",
    "endpoint": "endpoint",
    "folder_id": "folderID",
    "host": "host",
    "path": "path",
    "prefix": "prefix",
    "remote_path": "remotePath",
    "storage_account": "storageAccount",
    "url": "url",
}

STORAGE_TYPES = {"azure": "azureBlob"}


def storage_description(module):
    options = module.params["options"]
    details = [f"{option}={options[option]}" for option in sorted(STORAGE_KEYS) if options.get(option) is not None]

    return " ".join([module.params["storage"]] + details)


def storage_value(storage, option, value):
    home = os.environ.get("HOME", "")

    if storage == "filesystem" and option == "path" and value.startswith("~") and home:
        return home + value[1:]

    return value


def storage_mismatch(module, status):
    storage = module.params["storage"]

    if storage == "from-config":
        return None

    connected = status.get("storage") or {}
    expected = STORAGE_TYPES.get(storage, storage)

    if connected.get("type") != expected:
        return f"storage type is {connected.get('type')}, not {expected}"

    config = connected.get("config") or {}

    for option, key in sorted(STORAGE_KEYS.items()):
        value = module.params["options"].get(option)
        if not isinstance(value, str):
            continue

        value = storage_value(storage, option, value)
        if config.get(key, "") != value:
            return f"{option} is {config.get(key, '')}, not {value}"

    return None


def not_initialized(storage, stderr):
    if storage == "from-config":
        return False

    if "repository not initialized" in stderr:
        return True

    # kopia only creates a missing filesystem path when creating the repository
    return storage == "filesystem" and "cannot access storage path" in stderr and "no such file or directory" in stderr


def ensure_present(module):
    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=True, repository={})

    password = module.params["password"]
    status = repository_status(module, password=password)

    if status is not None:
        mismatch = storage_mismatch(module, status)
        if mismatch:
            module.fail_json(
                msg=f"already connected to a different repository than {storage_description(module)}: {mismatch}"
            )

        module.exit_json(changed=False, repository=camel_dict_to_snake_dict(status))

    if module.check_mode:
        module.exit_json(changed=True, repository={})

    options = dict(module.params["options"])
    options.update(module.params["secrets"])
    target = [module.params["storage"]] + kopia_flags(options)
    description = storage_description(module)

    rc, _dummy, stderr = kopia_command(module, ["repository", "connect"] + target, password=password)

    if rc != 0 and not_initialized(module.params["storage"], stderr):
        rc, _dummy, stderr = kopia_command(module, ["repository", "create"] + target, password=password)

        if rc != 0:
            module.fail_json(msg=f"unable to create the kopia repository in {description}: {stderr.strip()}")

        if module.params["validate_provider"]:
            rc, _dummy, stderr = kopia_command(module, ["repository", "validate-provider"], password=password)

            if rc != 0:
                module.fail_json(
                    msg=f"created the kopia repository in {description}, but validating the provider failed and is not retried on a later run: {stderr.strip()}"
                )

    if rc != 0:
        module.fail_json(msg=f"unable to connect to the kopia repository in {description}: {stderr.strip()}")

    status = repository_status(module, password=password)

    module.exit_json(changed=True, repository=camel_dict_to_snake_dict(status or {}))


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "options": {"type": "dict", "default": {}},
        "password": {"type": "str", "required": True, "no_log": True},
        "secrets": {"type": "dict", "default": {}, "no_log": True},
        "storage": {
            "type": "str",
            "required": True,
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
        supports_check_mode=True,
    )

    ensure_present(module)


if __name__ == "__main__":
    main()
