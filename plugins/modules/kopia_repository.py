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
  - The module runs C(kopia repository create) first, and runs
    C(kopia repository connect) when kopia reports that the storage already
    holds data, which may be a repository. With O(storage=from-config), it
    only connects.
  - For V(filesystem) storage, a C(path) that does not exist yet is created
    along with the repository.
  - The module is idempotent on the connection state reported by
    C(kopia repository status), so a host already connected to the repository
    is left untouched.
  - A host connected to a different repository fails rather than being
    reconnected. The connection is different when its storage type differs
    from O(storage), or when one of the options C(bucket), C(container),
    C(endpoint), C(folder_id), C(host), C(path), C(port), C(prefix),
    C(remote_path), C(storage_account), C(storage_domain) or C(url), or with
    O(storage=sftp) C(username), given in O(options) or O(secrets), differs
    from the connected storage configuration. A C(storage_domain) that is not
    stored is compared as C(blob.core.windows.net), the domain kopia uses
    then. C(port) is compared as the number kopia reads from it, which it
    reads as a decimal or hexadecimal floating-point number, as Go's
    C(strconv.ParseFloat) does, and truncates, so V("+22") and V("0x16p0")
    match a stored V(22), and V(" 22") does not. Another number in these
    options is compared as the text passed to kopia, so V(20261115) matches a
    stored V("20261115"), and that text is the number as Python formats it,
    as described in O(options). A leading V(~) in the C(path) of
    V(filesystem) storage is resolved to the home directory first, as kopia
    does, and that C(path) is compared as a normalized path, so
    V(/srv/kopia/) and V(//srv/kopia) match V(/srv/kopia). Disconnect it with
    C(kopia repository disconnect) first to switch repositories.
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
    C(path) directory, and any missing parent directory, before it writes the
    repository, and the C(.shards) file in it when it first reads or writes
    a blob. When it then fails, such as for lack of space, after creating
    any of them, the module fails reporting a change.
  - With V(sftp) storage, C(kopia repository create) also creates the remote
    C(path), and with V(sftp), V(webdav) or V(rclone) storage, it writes the
    C(.shards) file to the storage before the repository. The module cannot
    inspect remote storage, so when C(kopia repository create) then fails, it
    fails without reporting a change, although the remote C(path) or the
    C(.shards) file may have been created. kopia ignores them when it creates
    the repository on a later run.
  - C(kopia repository connect) writes the C(.shards) file, with legacy
    parameters, to storage that has none when it first reads a blob, even
    when the storage holds data but no repository, such as a stray file
    ending in C(.f) in the C(path) of V(filesystem) storage. When
    C(kopia repository connect) then fails after writing the C(.shards) file
    of V(filesystem) storage, the module fails reporting a change. With
    V(sftp), V(webdav) or V(rclone) storage, it fails without reporting a
    change, as the module cannot inspect remote storage.
  - When C(kopia repository connect) fails after kopia saved the connection,
    such as when persisting the password fails, the module fails reporting a
    change, and a later run finds the host connected. When the connection
    status cannot be read after C(kopia repository connect) fails, the module
    fails reporting a change, as kopia may have saved the connection.
notes:
  - While another client upgrades the repository format, C(kopia repository
    status) fails rather than waiting for the upgrade to end, but
    C(kopia repository connect), which has no option to fail instead, waits
    for as long as the other client holds the repository for the upgrade, and
    so does the module when it connects.
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
  options:
    description:
      - Storage provider flags passed to C(kopia repository create) and
        C(kopia repository connect), given as snake_case keys.
      - Flags that only C(kopia repository create) accepts, such as
        C(encryption), C(block_hash), C(object_splitter), C(format_version),
        C(retention_mode), C(retention_period), C(ecc) and C(create_only), in
        O(options) or O(secrets) make the connection fail as an unknown flag
        when the storage already holds a repository. C(create_only) also
        leaves a repository it creates unconnected.
      - Each key becomes the matching kebab-case CLI flag, so V(bucket) becomes
        C(--bucket) and V(storage_account) becomes C(--storage-account).
      - Booleans toggle the flag, V(true) emits C(--flag) and V(false) emits
        C(--no-flag), and a list repeats the flag once per element.
      - A dictionary value is passed as Python writes it. A list for one of
        the options that identify the repository, listed in the description,
        such as C(bucket) or C(path), which kopia takes once, is rejected
        before kopia runs.
        kopia rejects a Boolean for these options, which take a text value, so
        quote a value such as V(no) that YAML reads as a Boolean.
      - Values must be valid UTF-8, without a lone surrogate code point, or the
        module fails before kopia runs, also in check mode. kopia saves the
        storage options in its configuration with U+FFFD in place of other
        text and connects again from that copy, so the connection would fail
        or never match.
      - The exceptions are the file paths that kopia only reads and never
        saves in its configuration. These are C(file) and C(token_file) with
        O(storage=from-config), C(root_ca_pem_path) with O(storage=s3), whose
        file contents kopia saves instead, and C(embed_rclone_config) with
        O(storage=rclone), whose contents kopia embeds instead.
      - C(root_ca_pem_path) requires kopia 0.13.0 or later, and C(token_file)
        requires kopia 0.14.0 or later.
      - kopia reads a Boolean flag given a value, such as
        C(--embed-credentials=true) for a string V("true"), as the flag
        followed by an unexpected argument, which it refuses before it changes
        anything, so give Boolean flags Boolean values.
      - With C(embed_credentials) set to the Boolean V(true) in O(options) or
        O(secrets), kopia saves the file contents in place of the path of
        C(credentials_file) with O(storage=gcs) or O(storage=gdrive), and,
        with O(storage=sftp) when C(external) is not given or is V(false), of
        C(keyfile) when C(key_data) is not given or empty, and of
        C(known_hosts) when C(known_hosts_data) is not given or empty, so these
        are exceptions too.
      - U+DC80 to U+DCFF in these exceptions and in keys, which Ansible uses
        for bytes that are not valid UTF-8, are passed to kopia as those bytes.
        Another lone surrogate code point, from U+D800 to U+DC7F, cannot be
        passed to kopia, so it is rejected before kopia runs, also in check
        mode.
      - With O(storage=sftp) and C(external) set, kopia runs C(ssh), which asks
        for a password, a key passphrase or the confirmation of an unknown host
        key on the terminal rather than on its standard input, so the module
        can still wait for an answer. Give C(ssh) everything it needs, such as
        a key without a passphrase and a known host key, in its arguments or
        configuration.
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
      - kopia reads an empty password as no password, and fails to read one
        before it changes anything, except that it first creates a missing
        C(path) of V(filesystem) or V(sftp) storage. So an empty password is
        rejected before kopia runs, also in check mode, when the host is not
        connected and the storage is V(sftp), whose C(path) the module cannot
        check, or V(filesystem) with a C(path) that does not exist.
      - kopia removes whitespace around the password, so a password of only
        whitespace becomes an empty password, which C(kopia repository create)
        accepts.
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
      - A connection to a kopia server, C(kopia repository connect server), is
        not supported, as kopia reports no storage for it, so the module could
        not compare it with O(storage).
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
  - kopia >= 0.12.0
attributes:
  check_mode:
    description: Predicts changes without modifying the target.
    support: full
    details: Reports a potential change without querying current state when kopia is unavailable.
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
    - Empty when the module fails, also for an option value the module rejects
      before kopia runs. Not returned when Ansible rejects the arguments, such
      as a missing required option, a value of the wrong type or an invalid
      choice, or fails to log them, such as for a lone surrogate code point in
      an option that is not secret, or when the kopia command is not found or
      cannot be started, such as for a NUL character in a value passed to it.
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
          returned: unless the host reaches the repository through a kopia repository server
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
          returned: unless the host reaches the repository through a kopia repository server
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
          returned: unless the host reaches the repository through a kopia repository server
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
          returned: unless the host reaches the repository through a kopia repository server
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
            - V(null) when the host reaches the repository through a kopia
              repository server.
          returned: always
          type: dict
        type:
          description:
            - Storage type, such as C(filesystem) or C(s3).
            - Empty when the host reaches the repository through a kopia
              repository server.
          returned: always
          type: str
    unique_id_hex:
      description:
        - Unique ID of the repository in hexadecimal.
        - Empty when the host reaches the repository through a kopia
          repository server.
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
          returned: when the volume reports a non-zero size
          type: int
  sample:
    blob_retention: {}
    client_options:
      description: "Repository in Filesystem: /srv/backup/kopia"
      enable_actions: false
      format_blob_cache_duration: 900000000000
      hostname: server
      username: root
    config_file: /root/.config/kopia/repository.config
    content_format:
      enable_password_change: true
      encryption: AES256-GCM-HMAC-SHA256
      epoch_parameters:
        cleanup_safety_margin: 14400000000000
        delete_parallelism: 4
        enabled: true
        epoch_advance_on_count_threshold: 20
        epoch_advance_on_total_size_bytes_threshold: 10485760
        epoch_refresh_frequency: 1200000000000
        full_checkpoint_frequency: 7
        min_epoch_duration: 86400000000000
      hash: BLAKE2B-256-128
      index_version: 2
      max_pack_size: 20971520
      version: 3
    object_format:
      splitter: DYNAMIC-4M-BUZHASH
    storage:
      config:
        dir_mode: 448
        dir_shards: null
        file_mode: 384
        path: /srv/backup/kopia
      type: filesystem
    unique_id_hex: 0f5b8a29110e21bf6bd1e81e7a807933b0c40f3478064e63f63f7d253c785a9b
    volume:
      available: 61924470784
      capacity: 63928532992
"""

import os
import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    check_connection,
    check_utf8,
    clean_path,
    kopia_available,
    kopia_command,
    kopia_flags,
    repository_status,
    text_label,
)

STORAGE_KEYS = {
    "bucket": "bucket",
    "container": "container",
    "endpoint": "endpoint",
    "folder_id": "folderID",
    "host": "host",
    "path": "path",
    "port": "port",
    "prefix": "prefix",
    "remote_path": "remotePath",
    "storage_account": "storageAccount",
    "storage_domain": "storageDomain",
    "url": "url",
}

# an sftp username names the account on the host, and so the files its path reaches, so it identifies the repository;
# webdav takes its login as webdav_username, which only authenticates to the url, so it is not compared
STORAGE_TYPE_KEYS = {"sftp": {"username": "username"}}

# kingpin reads an int flag as a float and truncates it, so "+22" or "22.0" set the port 22
INT_OPTIONS = ("port",)

# the decimal and hexadecimal numbers Go's strconv.ParseFloat reads, a hexadecimal one only with a p exponent; it
# also reads "inf" and "nan", which are no port
GO_DECIMAL_FLOAT = re.compile(
    r"(?P<mantissa>[+-]?(?:[0-9_]+\.?[0-9_]*|\.[0-9_]+))(?:[eE](?P<sign>[+-]?)(?P<exponent>[0-9_]+))?"
)
GO_HEX_FLOAT = re.compile(
    r"(?P<mantissa>[+-]?0[xX](?:[0-9a-fA-F_]+\.?[0-9a-fA-F_]*|\.[0-9a-fA-F_]+))[pP](?P<sign>[+-]?)(?P<exponent>[0-9_]+)"
)

# Go allows an underscore only after a digit or the 0x prefix and before a digit
GO_DECIMAL_UNDERSCORE = re.compile(r"(?<![0-9])_|_(?![0-9])")
GO_HEX_UNDERSCORE = re.compile(r"(?<![0-9a-fA-FxX])_|_(?![0-9a-fA-F])")

# kopia uses this azure storage domain when none is stored
STORAGE_DEFAULTS = {"storageDomain": "blob.core.windows.net"}

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
# the storage holds no format blob; kopia 0.18 and later report both in these words
CREATE_NOT_EMPTY_ERROR = "found existing data in storage location"
CONNECT_NOT_INITIALIZED_ERROR = "repository not initialized"


def unsaved_options(module):
    """Return the options kopia only reads, never saving them in its configuration."""
    storage = module.params["storage"]
    options = storage_options(module)
    unsaved = set(UNSAVED_OPTIONS.get(storage, ()))

    # kopia_flags sends --embed-credentials only for a Boolean true, and kopia refuses any other value given to the flag
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


def kingpin_int(value):
    """Return value as text of the number kopia's flag parser reads from it, a float truncated, or as given."""
    text = str(value)
    hexadecimal = GO_HEX_FLOAT.fullmatch(text)
    match = hexadecimal or GO_DECIMAL_FLOAT.fullmatch(text)
    if match is None:
        return text

    underscores = GO_HEX_UNDERSCORE if hexadecimal else GO_DECIMAL_UNDERSCORE
    if underscores.search(text):
        return text

    # Go stops adding exponent digits once the exponent reaches 10000
    exponent = 0
    for digit in (match["exponent"] or "").replace("_", ""):
        if exponent < 10000:
            exponent = exponent * 10 + int(digit)

    number = f"{match['mantissa'].replace('_', '')}{'p' if hexadecimal else 'e'}{match['sign'] or ''}{exponent}"
    try:
        return str(int(float.fromhex(number) if hexadecimal else float(number)))
    except OverflowError:
        # strconv.ParseFloat refuses a number out of the float64 range
        return text


def identifying_keys(storage):
    """Return the options that identify a repository of the storage type, with the keys kopia stores them under."""
    return {**STORAGE_KEYS, **STORAGE_TYPE_KEYS.get(storage, {})}


def check_option_values(module):
    # kopia saves the storage options in its configuration with U+FFFD in place of bytes that are not UTF-8 and
    # reopens the storage from that copy, but it only reads these options, which run_command passes as the bytes
    unsaved = unsaved_options(module)

    for param in ("options", "secrets"):
        values = module.params[param]
        check_utf8(module, [(param, values)], errors="surrogateescape", failed_result={"repository": {}})
        check_utf8(
            module,
            [(f"{param}.{text_label(option)}", value) for option, value in values.items() if option not in unsaved],
            failed_result={"repository": {}},
        )

    keys = identifying_keys(module.params["storage"])

    for param in ("options", "secrets"):
        for option, value in sorted(module.params[param].items()):
            # kopia_flags sends a list as one flag per element, and kopia takes these flags once, so a list of one
            # value would connect to a repository that never matches the list, and an empty list would send none
            if option in keys and isinstance(value, (list, tuple)):
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
        for option in sorted(identifying_keys(module.params["storage"]))
        if options.get(option) is not None and option not in module.params["secrets"]
    ]

    return " ".join([module.params["storage"]] + details)


def expand_home(path):
    """Return path with only a leading "~" resolved to HOME when it is set, as kopia resolves a filesystem path."""
    home = os.environ.get("HOME", "")

    if path.startswith("~") and home:
        return home + path[1:]

    return path


def storage_value(storage, option, value):
    if storage != "filesystem" or option != "path":
        return value

    return clean_path(expand_home(value))


def storage_mismatch(module, status):
    storage = module.params["storage"]

    if storage == "from-config":
        return None

    connected = status["storage"]
    expected = STORAGE_TYPES.get(storage, storage)

    # kopia reports a storage type only for a repository it reaches directly, not through a kopia repository server
    if not connected["type"]:
        return "it is connected to a kopia repository server, which this module does not manage"

    if connected["type"] != expected:
        return f"storage type is {connected['type']}, not {expected}"

    config = connected["config"] or {}
    options = storage_options(module)

    for option, key in sorted(identifying_keys(storage).items()):
        value = options.get(option)

        # check_option_values refuses a list, kopia rejects a Boolean, which kopia_flags sends as a flag without a
        # value, and kopia_flags sends any other value as --name=value, so compare it as text
        if value is None:
            continue

        # kopia leaves out an empty value, using its default then, and stores the sftp port as a number
        value = (kingpin_int(value) if option in INT_OPTIONS else str(value)) or STORAGE_DEFAULTS.get(key, "")
        stored = str(config.get(key) or STORAGE_DEFAULTS.get(key, ""))
        if storage_value(storage, option, stored) != storage_value(storage, option, value):
            if option in module.params["secrets"]:
                return f"{option} differs from the connected repository"

            return f"{option} is {stored}, not {value}"

    return None


def mkdir_all_paths(path):
    """Return path and each parent Go's os.MkdirAll creates when missing, cut textually as it does."""
    paths = []

    while path:
        paths.append(path)
        # the parent ends before the last "/" that precedes the final name, or is empty
        parent = path.rfind("/", 0, len(path.rstrip("/")))
        path = path[: max(parent, 0)]

    return paths


def filesystem_path(module):
    """Return the path kopia uses for filesystem storage, with only a leading "~" resolved, or None."""
    path = storage_options(module).get("path")

    if module.params["storage"] != "filesystem" or path is None:
        return None

    return expand_home(str(path))


def missing_directories(module):
    """Return the directories kopia repository create would make for filesystem storage that do not exist yet."""
    path = filesystem_path(module)

    if path is None:
        return []

    # kopia makes the path it is given, so the kernel resolves any ".." after the directories it creates and the
    # symbolic links on the way
    return [directory for directory in mkdir_all_paths(path) if not os.path.lexists(directory)]


def missing_storage_files(module):
    """Return the directories and the .shards file kopia repository create would make for filesystem storage."""
    path = filesystem_path(module)

    if path is None:
        return []

    # kopia's sharded storage writes its .shards parameters on the first blob it reads or writes, before the
    # repository, and keeps going when it cannot
    shards = os.path.join(path, ".shards")

    return missing_directories(module) + ([] if os.path.lexists(shards) else [shards])


def create(module, target, description):
    """Create the repository, returning False when the storage already holds data, which may be a repository."""
    password = module.params["password"]
    # kopia creates the directory of filesystem storage and its .shards file before it writes the repository, which
    # can still fail
    missing = missing_storage_files(module)

    rc, _dummy, stderr = kopia_command(module, ["repository", "create"] + target, password=password)

    if rc != 0 and CREATE_NOT_EMPTY_ERROR in stderr:
        return False

    if rc != 0 and any(error in stderr for error in CREATE_INITIALIZED_ERRORS):
        module.fail_json(
            changed=True,
            msg=f"created the kopia repository in {description}, but kopia failed to finish its setup, which a later run does not retry: {stderr.strip()}",
            repository={},
        )

    if rc != 0 and CREATE_PARTIAL_ERROR in stderr:
        module.fail_json(
            changed=True,
            msg=f"kopia wrote kopia.blobcfg, then failed to create the repository in {description}; remove that blob to create it: {stderr.strip()}",
            repository={},
        )

    if rc != 0 and any(os.path.lexists(directory) for directory in missing):
        module.fail_json(
            changed=True,
            msg=f"kopia created the storage directory, a parent or its .shards file, but failed to create the repository in {description}: {stderr.strip()}",
            repository={},
        )

    if rc != 0:
        module.fail_json(msg=f"unable to create the kopia repository in {description}: {stderr.strip()}", repository={})

    if module.params["validate_provider"]:
        rc, _dummy, stderr = kopia_command(module, ["repository", "validate-provider"], password=password)

        if rc != 0:
            module.fail_json(
                changed=True,
                msg=f"created the kopia repository in {description}, but validating the provider failed and is not retried on a later run: {stderr.strip()}",
                repository={},
            )

    return True


def connect(module, target, description):
    password = module.params["password"]
    # kopia's sharded storage writes the .shards file of filesystem storage on the first blob it reads, also when the
    # storage holds no repository
    missing = missing_storage_files(module)

    rc, _dummy, stderr = kopia_command(module, ["repository", "connect"] + target, password=password)

    if rc == 0:
        return

    written = any(os.path.lexists(path) for path in missing)
    shards = ", and kopia wrote its .shards file" if written else ""

    if CONNECT_NOT_INITIALIZED_ERROR in stderr and module.params["storage"] != "from-config":
        reason = f"the storage holds data, such as kopia.blobcfg, but no repository{shards}"
        module.fail_json(
            changed=written,
            msg=f"unable to create the kopia repository in {description}: {reason}: {stderr.strip()}",
            repository={},
        )

    # kopia saves the connection before it persists the password, which can still fail
    status = repository_status(
        module,
        password=password,
        failed_result={"changed": True, "repository": {}},
        context=f"unable to connect to the kopia repository in {description}, and kopia may have saved the connection: {stderr.strip()}",
    )

    if status is not None:
        module.fail_json(
            changed=True,
            msg=f"connected to the kopia repository in {description}, but kopia reported an error: {stderr.strip()}",
            repository={},
        )

    module.fail_json(
        changed=written,
        msg=f"unable to connect to the kopia repository in {description}{shards}: {stderr.strip()}",
        repository={},
    )


def ensure_present(module):
    check_connection(module, failed_result={"repository": {}})
    check_option_values(module)

    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=True, repository={})

    password = module.params["password"]
    status = repository_status(module, password=password, failed_result={"repository": {}})

    # kopia reads an empty KOPIA_PASSWORD as no password, which it fails to read only after the storage of filesystem
    # and sftp storage has made a missing path
    storage = module.params["storage"]
    if status is None and password == "" and (storage == "sftp" or missing_directories(module)):
        module.fail_json(
            msg=f"invalid password: it must not be empty, as kopia reads it as no password after it creates the {storage} path",
            repository={},
        )

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

    # kopia repository create refuses storage that holds data, which may be a repository to connect to
    if module.params["storage"] == "from-config" or not create(module, target, description):
        connect(module, target, description)

    status = repository_status(module, password=password, failed_result={"changed": True, "repository": {}})

    module.exit_json(changed=True, repository=camel_dict_to_snake_dict(status or {}))


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "options": {"type": "dict", "default": {}},
        "password": {"type": "str", "required": True, "no_log": True},
        "secrets": {"type": "dict", "default": {}, "no_log": True},
        # kopia reports no storage for a connection to a kopia server, so "server" could never match
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
