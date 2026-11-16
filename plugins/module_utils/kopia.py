# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import os
import re
import stat

ACTION_COMMAND_OMITEMPTY = {"args": [], "mode": "", "path": "", "script": "", "timeout": 0}

POLICY_OMITEMPTY = {
    "actions": {
        "afterFolder": ACTION_COMMAND_OMITEMPTY,
        "afterSnapshotRoot": ACTION_COMMAND_OMITEMPTY,
        "beforeFolder": ACTION_COMMAND_OMITEMPTY,
        "beforeSnapshotRoot": ACTION_COMMAND_OMITEMPTY,
    },
    "compression": {
        "compressorName": "",
        "maxSize": 0,
        "minSize": 0,
        "neverCompress": [],
        "noParentNeverCompress": False,
        "noParentOnlyCompress": False,
        "onlyCompress": [],
    },
    "files": {
        "ignore": [],
        "ignoreDotFiles": [],
        "maxFileSize": 0,
        "noParentDotFiles": False,
        "noParentIgnore": False,
    },
    "metadataCompression": {"compressorName": ""},
    "noParent": False,
    "scheduling": {
        "cron": [],
        "intervalSeconds": 0,
        "manual": False,
        "noParentTimeOfDay": False,
        "timeOfDay": [],
    },
    "splitter": {"algorithm": ""},
}

# kopia stores both fields of each scheduling.timeOfDay entry, even when zero
TIME_OF_DAY = {"hour": 0, "min": 0}

# kopia names each manifest, such as a policy or a snapshot, with 16 random bytes in lowercase hexadecimal
MANIFEST_ID = re.compile(r"[0-9a-f]{32}")

# kopia fails with this error when it asks for the password on a standard input that is not a terminal
PASSWORD_PROMPT_ERROR = "password prompt error"

# the JSON field names of kopia's policy, the same from kopia 0.18 on: a dictionary for each structure, a list holding
# one for a list of structures, and None for any other value
ACTION_COMMAND_FIELDS = {"args": None, "mode": None, "path": None, "script": None, "timeout": None}

POLICY_FIELDS = {
    "actions": {
        "afterFolder": ACTION_COMMAND_FIELDS,
        "afterSnapshotRoot": ACTION_COMMAND_FIELDS,
        "beforeFolder": ACTION_COMMAND_FIELDS,
        "beforeSnapshotRoot": ACTION_COMMAND_FIELDS,
    },
    "compression": {
        "compressorName": None,
        "maxSize": None,
        "minSize": None,
        "neverCompress": None,
        "noParentNeverCompress": None,
        "noParentOnlyCompress": None,
        "onlyCompress": None,
    },
    "errorHandling": {"ignoreDirectoryErrors": None, "ignoreFileErrors": None, "ignoreUnknownTypes": None},
    "files": {
        "ignore": None,
        "ignoreCacheDirs": None,
        "ignoreDotFiles": None,
        "maxFileSize": None,
        "noParentDotFiles": None,
        "noParentIgnore": None,
        "oneFileSystem": None,
    },
    "logging": {
        "directories": {"ignored": None, "snapshotted": None},
        "entries": {"cacheHit": None, "cacheMiss": None, "ignored": None, "snapshotted": None},
    },
    "metadataCompression": {"compressorName": None},
    "noParent": None,
    "osSnapshots": {"volumeShadowCopy": {"enable": None}},
    "retention": {
        "ignoreIdenticalSnapshots": None,
        "keepAnnual": None,
        "keepDaily": None,
        "keepHourly": None,
        "keepLatest": None,
        "keepMonthly": None,
        "keepWeekly": None,
    },
    "scheduling": {
        "cron": None,
        "intervalSeconds": None,
        "manual": None,
        "noParentTimeOfDay": None,
        "runMissed": None,
        "timeOfDay": [{"hour": None, "min": None}],
    },
    "splitter": {"algorithm": None},
    "upload": {"maxParallelFileReads": None, "maxParallelSnapshots": None, "parallelUploadAboveSize": None},
}


def kopia_flags(options):
    flags = []

    for key, value in sorted(options.items()):
        name = key.replace("_", "-")
        if value is None:
            continue

        if isinstance(value, bool):
            flags.append(f"--{name}" if value else f"--no-{name}")
        elif isinstance(value, (list, tuple)):
            flags.extend(f"--{name}={item}" for item in value)
        else:
            flags.append(f"--{name}={value}")

    return flags


def text_label(text):
    """Return text with any character that cannot be encoded as UTF-8 written as an escape, for a message."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def find_text(value, name, test):
    """Return the name of the first string in value, a key or item at any depth, for which test is true, or None."""
    if isinstance(value, str):
        return name if test(value) else None

    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{name}.{text_label(str(key))}"
            found = find_text(key, child, test) or find_text(item, child, test)
            if found:
                return found

    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found = find_text(item, f"{name}[{index}]", test)
            if found:
                return found

    return None


def invalid_utf8(value, name, errors="strict"):
    """Return the name of the first string in value, a key or item at any depth, that is not valid UTF-8, or None.

    With errors="surrogateescape", U+DC80 to U+DCFF, which Ansible uses for bytes that are not valid UTF-8, are
    accepted as those bytes, and only another lone surrogate is reported.
    """

    def not_utf8(text):
        try:
            text.encode("utf-8", errors)
        except UnicodeEncodeError:
            return True

        return False

    return find_text(value, name, not_utf8)


def check_utf8(module, settings, errors="strict", failed_result=None):
    """Fail naming the first (name, value) setting holding a NUL or text that is not valid UTF-8, never its value.

    With errors="surrogateescape", only a lone surrogate outside U+DC80 to U+DCFF fails, see invalid_utf8.
    """
    failed_result = failed_result or {}

    for name, value in settings:
        # a command-line argument or an environment variable cannot carry a NUL, which run_command cannot pass
        found = find_text(value, name, lambda text: "\x00" in text)

        if found:
            module.fail_json(msg=f"invalid {found}: it must not contain a NUL character", **failed_result)

        found = invalid_utf8(value, name, errors)

        if not found:
            continue

        # U+D800 to U+DC7F cannot be encoded, so run_command cannot pass them to kopia at all
        if errors == "surrogateescape":
            rule = "it must not contain a lone surrogate code point other than U+DC80 to U+DCFF"
            escaped = "which stand for bytes that are not valid UTF-8"
            module.fail_json(
                msg=f"invalid {found}: {rule}, {escaped}, as it cannot be passed to kopia", **failed_result
            )

        # a lone surrogate, which a JSON value can carry, reaches kopia as a raw byte or not at all, and kopia records
        # text that is not valid UTF-8 with U+FFFD in its place, so the value it reports never matches
        recorded = "kopia records other text with U+FFFD in its place"
        module.fail_json(
            msg=f"invalid {found}: it must be valid UTF-8, without a lone surrogate code point, as {recorded}",
            **failed_result,
        )


def config_path(module):
    """Return the configuration file kopia uses, which it looks up in its configuration directory for a bare name."""
    path = module.params.get("config_file") or os.environ.get("KOPIA_CONFIG_PATH") or "repository.config"

    if os.path.basename(path) != path:
        return path

    settings = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.environ.get("HOME", ""), ".config")

    return os.path.join(settings, "kopia", path)


def check_connection(module, failed_result=None):
    """Fail before kopia runs for a config_file or password that kopia cannot be given or cannot use."""
    failed_result = failed_result or {}
    settings = [(name, module.params.get(name)) for name in ("config_file", "password")]

    # run_command passes U+DC80 to U+DCFF in a path or a password to kopia as the bytes they stand for
    check_utf8(module, settings, errors="surrogateescape", failed_result=failed_result)

    # kopia reads an empty KOPIA_PASSWORD as no password, and uses a persisted password or asks for one instead
    if module.params.get("password") == "":
        reason = "as kopia reads an empty password as no password"
        module.fail_json(msg=f"invalid password: it must not be empty, {reason}", **failed_result)

    path = config_path(module)

    try:
        mode = os.stat(path).st_mode
    except OSError:
        return

    # kopia waits reading a FIFO or a terminal, and fails reading a directory, as its configuration
    if not stat.S_ISREG(mode):
        label = "config_file" if module.params.get("config_file") else "kopia configuration file"
        module.fail_json(msg=f"invalid {label} {path}: it is not a regular file", **failed_result)


def kopia_available(module):
    return module.get_bin_path("kopia") is not None


def kopia_command(module, args, password=None):
    kopia = module.get_bin_path("kopia", required=True)

    command = [kopia]
    if module.params.get("config_file"):
        command.append(f"--config-file={module.params['config_file']}")

    command.extend(args)

    # kopia otherwise waits for as long as another client holds the repository for a format upgrade
    environ = {"KOPIA_CHECK_FOR_UPDATES": "false", "KOPIA_REPO_UPGRADE_NO_BLOCK": "true"}
    if password is not None:
        environ["KOPIA_PASSWORD"] = password

    # kopia asks for a password that is neither given nor persisted on the standard input it inherits, which can be a
    # terminal, such as over SSH without pipelining, so it inherits /dev/null instead, on which it fails at once; data
    # would give it a pipe, but writing it fails when kopia exits first
    null = os.open(os.devnull, os.O_RDONLY)
    try:
        os.dup2(null, 0)
    finally:
        os.close(null)

    rc, stdout, stderr = module.run_command(command, environ_update=environ, expand_user_and_vars=False)

    if rc != 0 and PASSWORD_PROMPT_ERROR in stderr:
        missing = "kopia needs the repository password, which is not given"
        persisted = f"and not persisted next to {config_path(module)}"
        stderr = f"{missing} {persisted}: {stderr.strip()}"

    return rc, stdout, stderr


def clean_path(path):
    path = os.path.normpath(path)

    # normpath keeps a leading "//", which Linux resolves like "/" and Go's filepath.Clean reduces to "/"
    if path.startswith("//"):
        path = "/" + path.lstrip("/")

    return path


def working_directory():
    # Go's os.Getwd prefers $PWD when it is absolute and names the working directory
    pwd = os.environ.get("PWD", "")

    try:
        if pwd.startswith("/") and os.path.samefile(pwd, "."):
            return pwd
    except OSError:
        pass

    return os.getcwd()


def absolute_path(path):
    # kopia records a local source as filepath.Abs does: joined to the working directory and cleaned
    return clean_path(path if path.startswith("/") else os.path.join(working_directory(), path))


def reads_as_user_host(path):
    """Return whether kopia's ParseSourceInfo does not read path as a local path.

    It reads such a path as user@host or user@host:path, or rejects it when its only "@" is its last character.
    """
    at = path.find("@")
    colon = path.find(":")

    return 0 < at < colon or (at >= 0 and colon < 0)


def snapshot_source(module, path, operation, failed_result=None):
    # the path is passed absolute, so a name such as "--all" or "(global)" stays a path, and kopia adds its own client
    # user and host; kopia reads an absolute path in which an "@" comes before any ":" as user@host or
    # user@host:path, so only such a path is qualified with the client user and host, whose user can start with "-",
    # so callers pass the source after "--"
    failed_result = failed_result or {}
    absolute = absolute_path(path)

    if not reads_as_user_host(absolute):
        return absolute

    status = repository_status(module, password=module.params["password"], failed_result=failed_result)

    if status is None:
        module.fail_json(msg=f"unable to {operation} of {path}: repository is not connected", **failed_result)

    options = status.get("clientOptions") if isinstance(status, dict) else None
    options = options if isinstance(options, dict) else {}
    username = options.get("username")
    hostname = options.get("hostname")

    if not isinstance(username, str) or not username or not isinstance(hostname, str) or not hostname:
        module.fail_json(
            msg=f"unable to {operation} of {path}: kopia did not report the client user and host", **failed_result
        )

    # kopia splits user@host:/path at the first "@" and the first ":", so a host may contain "@"
    if "@" in username or ":" in username or ":" in hostname:
        client = f"client user {username!r} on host {hostname!r}"
        split = "as it splits user@host:/path at the first '@' and ':'"
        reason = f"a path in which an '@' comes before any ':', for {client}, {split}"
        module.fail_json(
            msg=f"unable to {operation} of {path}: kopia cannot list {absolute}, {reason}", **failed_result
        )

    return f"{username}@{hostname}:{absolute}"


# The read helpers below add failed_result to a failure, such as changed=True when the caller has already written.


def repository_status(module, password=None, failed_result=None, context=None):
    """Return the status kopia reports, or None only when kopia reports that the repository is not connected.

    Any other failure fails the module, its message starting with context when given.
    """
    failed_result = failed_result or {}
    prefix = f"{context}; " if context else ""
    rc, stdout, stderr = kopia_command(module, ["repository", "status", "--json"], password=password)

    if rc == 0:
        try:
            return json.loads(stdout)
        except ValueError:
            module.fail_json(
                msg=f"{prefix}unable to parse kopia repository status output: {stdout.strip()}", **failed_result
            )

    if "repository is not connected" in stderr:
        return None

    module.fail_json(msg=f"{prefix}unable to query kopia repository status: {stderr.strip()}", **failed_result)


def maintenance_info(module, failed_result=None):
    failed_result = failed_result or {}
    rc, stdout, stderr = kopia_command(module, ["maintenance", "info", "--json"])

    if rc != 0:
        module.fail_json(msg=f"unable to query kopia maintenance info: {stderr.strip()}", **failed_result)

    try:
        return json.loads(stdout)
    except ValueError:
        module.fail_json(msg=f"unable to parse kopia maintenance info output: {stdout.strip()}", **failed_result)


def policy_export(module, target, failed_result=None):
    failed_result = failed_result or {}
    # after "--", kopia reads a target starting with "-", such as "--global", as a path, as policy import does
    rc, stdout, stderr = kopia_command(module, ["policy", "export", "--", target])

    if rc == 0:
        try:
            policies = json.loads(stdout)
        except ValueError:
            module.fail_json(
                msg=f"unable to parse kopia policy export output for {target}: {stdout.strip()}", **failed_result
            )

        return next(iter(policies.values()), {})

    if "policy not found" in stderr:
        return None

    module.fail_json(msg=f"unable to export kopia policy {target}: {stderr.strip()}", **failed_result)


def check_policy_target(module, target, failed_result=None):
    """Fail before kopia runs for a target that kopia rejects or that its commands read differently."""
    failed_result = failed_result or {}

    # kopia policy import reads every target as a path, but the other commands look a target up as a manifest ID
    # first, such as the ID of another policy or of a snapshot, whose source they then use
    if MANIFEST_ID.fullmatch(target):
        lookup = "kopia policy export, show and delete read it as a manifest ID, such as that of a policy or a snapshot"
        spelling = f"write a relative directory with such a name as ./{target}"
        module.fail_json(
            msg=f"invalid target {target}: {lookup}, while kopia policy import reads it as a path; {spelling}",
            **failed_result,
        )

    # kopia reads a target with an "@" and no ":" as user@host, and rejects one with no host after its only "@"
    if target.endswith("@") and target.count("@") == 1 and ":" not in target:
        user_host = "kopia reads a target with an '@' and no ':' as user@host"
        rejected = "rejects one with nothing after the '@'"
        module.fail_json(
            msg=f"invalid target {target}: {user_host}, and {rejected}; write such a directory as user@host:/path",
            **failed_result,
        )


def go_fold(name):
    """Return name in upper case, as Go's encoding/json folds a key to match it to a field name ignoring case."""
    return "".join(char.upper() if len(char.upper()) == 1 else char for char in name)


def policy_field_mismatch(key, fields):
    """Return the kopia field that key matches only ignoring case, or None for an exact match or an unknown key."""
    if not isinstance(fields, dict) or key in fields:
        return None

    return next((field for field in sorted(fields) if go_fold(field) == go_fold(key)), None)


def prune_empty(value):
    if not isinstance(value, dict):
        return value

    pruned = {key: prune_empty(item) for key, item in value.items() if item is not None}

    return {key: item for key, item in pruned.items() if item != {}}


def omit_empty(value, schema):
    if not isinstance(value, dict) or not isinstance(schema, dict):
        return value

    result = {}

    for key, item in value.items():
        zero = schema.get(key)

        if isinstance(zero, dict):
            result[key] = omit_empty(item, zero)
        elif key not in schema or not same_value(item, zero):
            result[key] = item

    return result


def policy_normalize(policy):
    policy = prune_empty(omit_empty(policy, POLICY_OMITEMPTY))
    scheduling = policy.get("scheduling")

    if isinstance(scheduling, dict) and isinstance(scheduling.get("timeOfDay"), list):
        scheduling["timeOfDay"] = [
            dict(TIME_OF_DAY, **entry) if isinstance(entry, dict) else entry for entry in scheduling["timeOfDay"]
        ]

    return policy


def same_value(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right

    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same_value(left[key], right[key]) for key in left)

    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same_value(a, b) for a, b in zip(left, right))

    if isinstance(left, (dict, list)) or isinstance(right, (dict, list)):
        return False

    return left == right
