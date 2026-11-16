# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import os

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


def invalid_utf8(value, name, errors="strict"):
    """Return the name of the first string in value, a key or item at any depth, that is not valid UTF-8, or None.

    With errors="surrogateescape", U+DC80 to U+DCFF, which Ansible uses for bytes that are not valid UTF-8, are
    accepted as those bytes, and only another lone surrogate is reported.
    """
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors)
        except UnicodeEncodeError:
            return name

    elif isinstance(value, dict):
        for key, item in value.items():
            child = f"{name}.{text_label(str(key))}"
            found = invalid_utf8(key, child, errors) or invalid_utf8(item, child, errors)
            if found:
                return found

    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found = invalid_utf8(item, f"{name}[{index}]", errors)
            if found:
                return found

    return None


def check_utf8(module, settings, errors="strict"):
    """Fail naming the first (name, value) setting holding text that is not valid UTF-8, never its value.

    With errors="surrogateescape", only a lone surrogate outside U+DC80 to U+DCFF fails, see invalid_utf8.
    """
    for name, value in settings:
        found = invalid_utf8(value, name, errors)

        if not found:
            continue

        # U+D800 to U+DC7F cannot be encoded, so run_command cannot pass them to kopia at all
        if errors == "surrogateescape":
            module.fail_json(
                msg=f"invalid {found}: it must not contain a lone surrogate code point other than U+DC80 to U+DCFF, "
                "which stand for bytes that are not valid UTF-8, as it cannot be passed to kopia"
            )

        # a lone surrogate, which a JSON value can carry, reaches kopia as a raw byte or not at all, and kopia records
        # text that is not valid UTF-8 with U+FFFD in its place, so the value it reports never matches
        module.fail_json(
            msg=f"invalid {found}: it must be valid UTF-8, without a lone surrogate code point, "
            "as kopia records other text with U+FFFD in its place"
        )


def kopia_available(module):
    return module.get_bin_path("kopia") is not None


def kopia_command(module, args, password=None):
    kopia = module.get_bin_path("kopia", required=True)

    command = [kopia]
    if module.params.get("config_file"):
        command.append(f"--config-file={module.params['config_file']}")

    command.extend(args)

    environ = {"KOPIA_CHECK_FOR_UPDATES": "false"}
    if password is not None:
        environ["KOPIA_PASSWORD"] = password

    return module.run_command(command, environ_update=environ, expand_user_and_vars=False)


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
    """Return whether kopia's ParseSourceInfo reads path as user@host or user@host:path rather than a local path."""
    at = path.find("@")
    colon = path.find(":")

    return 0 < at < colon or (at >= 0 and colon < 0)


def snapshot_source(module, path, operation):
    # the path is passed absolute, so a name such as "--all" or "(global)" stays a path, and kopia adds its own client
    # user and host; kopia reads an absolute path in which an "@" comes before any ":" as user@host or
    # user@host:path, so only such a path is qualified with the client user and host
    absolute = absolute_path(path)

    if not reads_as_user_host(absolute):
        return absolute

    status = repository_status(module, password=module.params["password"])

    if status is None:
        module.fail_json(msg=f"unable to {operation} of {path}: repository is not connected")

    options = status.get("clientOptions") if isinstance(status, dict) else None
    options = options if isinstance(options, dict) else {}
    username = options.get("username")
    hostname = options.get("hostname")

    if not isinstance(username, str) or not username or not isinstance(hostname, str) or not hostname:
        module.fail_json(msg=f"unable to {operation} of {path}: kopia did not report the client user and host")

    # kopia splits user@host:/path at the first "@" and the first ":", so a host may contain "@"
    if "@" in username or ":" in username or ":" in hostname:
        module.fail_json(
            msg=(
                f"unable to {operation} of {path}: kopia cannot list {absolute}, a path in which an '@' comes before "
                f"any ':', for client "
                f"user {username!r} on host {hostname!r}, as it splits user@host:/path at the first '@' and ':'"
            )
        )

    return f"{username}@{hostname}:{absolute}"


# The read helpers below add failed_result to a failure, such as changed=True when the caller has already written.


def repository_status(module, password=None, failed_result=None):
    failed_result = failed_result or {}
    rc, stdout, stderr = kopia_command(module, ["repository", "status", "--json"], password=password)

    if rc == 0:
        try:
            return json.loads(stdout)
        except ValueError:
            module.fail_json(msg=f"unable to parse kopia repository status output: {stdout.strip()}", **failed_result)

    if "repository is not connected" in stderr:
        return None

    module.fail_json(msg=f"unable to query kopia repository status: {stderr.strip()}", **failed_result)


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
    rc, stdout, stderr = kopia_command(module, ["policy", "export", target])

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


def check_policy_target(module, target):
    """Fail before kopia runs for a target that kopia policy export, show and delete would read as a flag."""
    # kopia policy import reads every target as a path, but the other commands read "--global" as the global policy
    if target.startswith("-"):
        module.fail_json(
            msg=(
                f"invalid target {target}: kopia reads a target starting with '-' as a command-line flag; "
                "use (global) for the global policy, or prefix a relative path with ./"
            )
        )


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
