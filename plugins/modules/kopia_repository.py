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
    from O(storage), or when one of the options C(bucket), C(container),
    C(endpoint), C(folder_id), C(host), C(path), C(prefix), C(remote_path),
    C(storage_account) or C(url), given in O(options) or O(secrets), differs
    from the connected storage configuration. A number in these options is compared as the text passed
    to kopia, so V(20261115) matches a stored V("20261115"), and that text is
    the number as Python formats it, as described in O(options). A leading V(~)
    in the C(path) of V(filesystem) storage is resolved to the home directory
    first, as kopia does, and that C(path) is compared as a normalized path,
    so V(/srv/kopia/) and V(//srv/kopia) match V(/srv/kopia). Disconnect it
    with C(kopia repository disconnect) first to switch repositories.
  - With O(storage=from-config), the existing connection is not compared, so
    a host already connected to any repository is left untouched.
  - C(kopia repository create) can fail after it has initialized the
    storage, when connecting to the new repository or setting its default
    global policy and maintenance owner fails. The module then fails reporting
    a change, and a later run connects to it, or finds it connected, without
    retrying that setup, which kopia only does when it creates a repository.
  - C(kopia repository create) can also fail after writing the
    C(kopia.blobcfg) blob, stored as the file C(kopia.blobcfg.f) with
    V(filesystem), V(rclone), V(sftp) or V(webdav) storage, when writing the
    format blob fails. The module then fails reporting a change, as the
    storage holds a partial repository, and creating the repository fails
    until that blob is removed from the storage. A later run that finds such
    data without a repository fails saying so.
  - For V(filesystem) storage, C(kopia repository create) creates the
    C(path) directory before it writes the repository. When it then fails,
    such as for lack of space, and the directory did not exist before, the
    module fails reporting a change.
  - When C(kopia repository connect) fails after kopia saved the connection,
    such as when persisting the password fails, the module fails reporting a
    change, and a later run finds the host connected. When the connection
    status cannot be read after C(kopia repository connect) fails, the module
    fails reporting a change, as kopia may have saved the connection.
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
      - A dictionary value is rejected before kopia runs, and so is a Boolean
        or a list for one of the options that identify the repository, listed
        in the description, such as C(bucket) or C(path). Quote a value such as
        V(no) that YAML reads as a Boolean.
      - Keys and values must be valid UTF-8, without a lone surrogate code
        point, or the module fails before kopia runs, also in check mode.
        kopia saves the storage options in its configuration with U+FFFD in
        place of other text and connects again from that copy, so the
        connection would fail or never match.
      - The exceptions are the file paths that kopia only reads and never
        saves in its configuration. These are C(file) and C(token_file) with
        O(storage=from-config), C(root_ca_pem_path) with O(storage=s3), whose
        file contents kopia saves instead, and C(embed_rclone_config) with
        O(storage=rclone), whose contents kopia embeds instead.
      - With C(embed_credentials) set to the Boolean V(true) in O(options) or
        O(secrets), kopia saves the file contents in place of the path of
        C(credentials_file) with O(storage=gcs) or O(storage=gdrive), and,
        with O(storage=sftp) when C(external) is not given or is V(false), of
        C(keyfile) when C(key_data) is not given or empty, and of
        C(known_hosts) when C(known_hosts_data) is not given or empty, so these
        are exceptions too.
      - U+DC80 to U+DCFF in these exceptions, which Ansible uses for bytes
        that are not valid UTF-8, are passed to kopia as those bytes. Another
        lone surrogate code point, from U+D800 to U+DC7F, cannot be passed to
        kopia, so it is rejected before kopia runs, also in check mode.
      - Put credential-carrying flags in O(secrets) instead so they stay out of
        logs.
      - Values are passed to kopia as given, so the module does not expand V(~)
        or environment variables in them.
      - A number is passed as Python formats it, so a value that YAML reads as
        a number changes, such as an unquoted V(0755), V(12:30) or V(1.10),
        which reach kopia as C(493), C(750) and C(1.1). Quote such values to
        pass them as written.
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
      - Converted to CLI flags exactly like O(options), with the same rejected
        values and number formatting, but kept out of logs. A rejected value is
        not included in the failure message.
      - A key also given in O(options) takes its value from O(secrets).
      - The options that identify the repository, listed in the description,
        are compared with the connected repository like O(options), but a
        failure names only the option, not its value or the connected one.
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
    - Empty when the module fails, also for an invalid option before kopia
      runs. Not returned when the kopia command is not found.
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
    check_utf8,
    clean_path,
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

# kopia reads these files and never saves their paths in its configuration
UNSAVED_OPTIONS = {
    "from-config": ("file", "token_file"),
    "rclone": ("embed_rclone_config",),
    "s3": ("root_ca_pem_path",),
}

# with embed_credentials, kopia saves the contents of these files in place of their paths
EMBEDDED_OPTIONS = {
    "gcs": ("credentials_file",),
    "gdrive": ("credentials_file",),
    "sftp": ("keyfile", "known_hosts"),
}

# kopia keeps the sftp file path when the matching data option is also given
SFTP_DATA_OPTIONS = {"keyfile": "key_data", "known_hosts": "known_hosts_data"}

# kopia repository create reports these once it has initialized the storage, when connecting to the new repository or
# setting its default global policy and maintenance owner fails
CREATE_INITIALIZED_ERRORS = ("unable to connect to repository", "error populating repository")

# kopia repository create reports this when writing the format blob fails after it wrote the kopia.blobcfg blob
CREATE_PARTIAL_ERROR = "unable to write format blob"

# kopia repository create reports this for storage that holds any blob, and kopia repository connect the other when
# the storage holds no format blob
CREATE_NOT_EMPTY_ERROR = "found existing data in storage location"
CONNECT_NOT_INITIALIZED_ERROR = "repository not initialized"

# kopia stores a blob in a file named after it with ".f" added in sharded storage, which these providers use, rclone
# through a WebDAV server
BLOBCFG = "the kopia.blobcfg blob (the file kopia.blobcfg.f with filesystem, rclone, sftp or webdav storage)"


def unsaved_options(module):
    """Return the options kopia only reads, never saving them in its configuration."""
    storage = module.params["storage"]
    options = storage_options(module)
    unsaved = set(UNSAVED_OPTIONS.get(storage, ()))

    # kopia_flags sends --embed-credentials only for a Boolean true
    if options.get("embed_credentials") is not True:
        return unsaved

    # kopia embeds the sftp files only without an external SSH command
    external = options.get("external")
    if storage == "sftp" and external is not None and external is not False:
        return unsaved

    for option in EMBEDDED_OPTIONS.get(storage, ()):
        data = SFTP_DATA_OPTIONS.get(option)
        if data is None or options.get(data) in (None, ""):
            unsaved.add(option)

    return unsaved


def check_option_values(module):
    # kopia saves the storage options in its configuration with U+FFFD in place of bytes that are not UTF-8 and
    # reopens the storage from that copy, but it only reads these options, which run_command passes as the bytes
    unsaved = unsaved_options(module)

    for param in ("options", "secrets"):
        values = module.params[param]
        check_utf8(
            module,
            [(param, {option: value for option, value in values.items() if option in unsaved})],
            errors="surrogateescape",
            failed_result={"repository": {}},
        )
        check_utf8(
            module,
            [(param, {option: value for option, value in values.items() if option not in unsaved})],
            failed_result={"repository": {}},
        )

    for param in ("options", "secrets"):
        for option, value in sorted(module.params[param].items()):
            # kopia_flags would send a dictionary as Python text and a list as one flag per element
            if isinstance(value, dict):
                module.fail_json(
                    msg=f"invalid {param} value for {option}: a dictionary cannot be passed to kopia", repository={}
                )

            # kopia takes these as text flags, which kopia_flags cannot send for a Boolean or a list
            if option in STORAGE_KEYS and isinstance(value, bool):
                module.fail_json(
                    msg=f"invalid {param} value for {option}: it identifies the repository, so it takes a text value, not a Boolean; quote it",
                    repository={},
                )

            if option in STORAGE_KEYS and isinstance(value, (list, tuple)):
                module.fail_json(
                    msg=f"invalid {param} value for {option}: it identifies the repository, so it takes one value, not a list",
                    repository={},
                )


def storage_options(module):
    """Return the options sent to kopia, secrets overriding options of the same name."""
    options = dict(module.params["options"])
    options.update(module.params["secrets"])

    return options


def storage_description(module):
    options = module.params["options"]
    # an option overridden by a secret is not the value sent, and the secret stays out of the message
    details = [
        f"{option}={options[option]}"
        for option in sorted(STORAGE_KEYS)
        if options.get(option) is not None and option not in module.params["secrets"]
    ]

    return " ".join([module.params["storage"]] + details)


def storage_value(storage, option, value):
    if storage != "filesystem" or option != "path":
        return value

    home = os.environ.get("HOME", "")

    if value.startswith("~") and home:
        value = home + value[1:]

    return clean_path(value)


def storage_mismatch(module, status):
    storage = module.params["storage"]

    if storage == "from-config":
        return None

    connected = status.get("storage") or {}
    expected = STORAGE_TYPES.get(storage, storage)

    if connected.get("type") != expected:
        return f"storage type is {connected.get('type')}, not {expected}"

    config = connected.get("config") or {}
    options = storage_options(module)

    for option, key in sorted(STORAGE_KEYS.items()):
        value = options.get(option)

        # check_option_values refuses a Boolean or a list, and kopia_flags sends any other value as --name=value,
        # so compare it as text
        if value is None:
            continue

        value = str(value)
        stored = config.get(key, "")
        if storage_value(storage, option, stored) != storage_value(storage, option, value):
            if option in module.params["secrets"]:
                return f"{option} differs from the connected repository"

            return f"{option} is {stored}, not {value}"

    return None


def not_initialized(storage, stderr):
    if storage == "from-config":
        return False

    if CONNECT_NOT_INITIALIZED_ERROR in stderr:
        return True

    # kopia only creates a missing filesystem path when creating the repository
    return storage == "filesystem" and "cannot access storage path" in stderr and "no such file or directory" in stderr


def created_directory(module):
    """Return the path kopia repository create makes for filesystem storage when it does not exist yet, or None."""
    path = storage_options(module).get("path")

    if module.params["storage"] != "filesystem" or path is None:
        return None

    path = storage_value("filesystem", "path", str(path))

    return None if os.path.lexists(path) else path


def ensure_present(module):
    check_option_values(module)

    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=True, repository={})

    password = module.params["password"]
    status = repository_status(module, password=password, failed_result={"repository": {}})

    if status is not None:
        mismatch = storage_mismatch(module, status)
        if mismatch:
            module.fail_json(
                msg=f"already connected to a different repository than {storage_description(module)}: {mismatch}",
                repository={},
            )

        module.exit_json(changed=False, repository=camel_dict_to_snake_dict(status))

    if module.check_mode:
        module.exit_json(changed=True, repository={})

    target = [module.params["storage"]] + kopia_flags(storage_options(module))
    description = storage_description(module)

    rc, _dummy, stderr = kopia_command(module, ["repository", "connect"] + target, password=password)

    if rc != 0 and not_initialized(module.params["storage"], stderr):
        uninitialized = CONNECT_NOT_INITIALIZED_ERROR in stderr
        # kopia creates the directory of filesystem storage before it writes the repository, which can still fail
        directory = created_directory(module)

        rc, _dummy, stderr = kopia_command(module, ["repository", "create"] + target, password=password)

        if rc != 0 and any(error in stderr for error in CREATE_INITIALIZED_ERRORS):
            unset = (
                "so its default global policy and maintenance owner may not be set, and a later run does not retry them"
            )
            msg = (
                f"created the kopia repository in {description}, but kopia failed afterwards, {unset}: {stderr.strip()}"
            )
            module.fail_json(changed=True, msg=msg, repository={})

        if rc != 0 and CREATE_PARTIAL_ERROR in stderr:
            partial = "the storage holds a partial repository, and creating it fails until that blob is removed from the storage"
            msg = f"kopia failed to create the repository in {description} after writing {BLOBCFG}, so {partial}: {stderr.strip()}"
            module.fail_json(changed=True, msg=msg, repository={})

        if rc != 0 and uninitialized and CREATE_NOT_EMPTY_ERROR in stderr:
            hint = f"the storage holds data but no kopia repository, such as {BLOBCFG} left by a failed create"
            module.fail_json(
                msg=f"unable to create the kopia repository in {description}: {hint}: {stderr.strip()}", repository={}
            )

        if rc != 0 and directory is not None and os.path.lexists(directory):
            msg = f"kopia created the storage directory but failed to create the repository in {description}: {stderr.strip()}"
            module.fail_json(changed=True, msg=msg, repository={})

        if rc != 0:
            module.fail_json(
                msg=f"unable to create the kopia repository in {description}: {stderr.strip()}", repository={}
            )

        if module.params["validate_provider"]:
            rc, _dummy, stderr = kopia_command(module, ["repository", "validate-provider"], password=password)

            if rc != 0:
                msg = f"created the kopia repository in {description}, but validating the provider failed and is not retried on a later run: {stderr.strip()}"
                module.fail_json(changed=True, msg=msg, repository={})

    if rc != 0:
        # kopia saves the connection before it persists the password, which can still fail
        status = repository_status(
            module,
            password=password,
            failed_result={"changed": True, "repository": {}},
            context=f"unable to connect to the kopia repository in {description}, and kopia may have saved the connection: {stderr.strip()}",
        )

        if status is not None:
            msg = f"connected to the kopia repository in {description}, but kopia reported an error: {stderr.strip()}"
            module.fail_json(changed=True, msg=msg, repository={})

        module.fail_json(
            msg=f"unable to connect to the kopia repository in {description}: {stderr.strip()}", repository={}
        )

    status = repository_status(module, password=password, failed_result={"changed": True, "repository": {}})

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
