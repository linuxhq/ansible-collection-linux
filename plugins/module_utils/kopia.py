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
    """Fail naming the first (name, value) setting holding text that is not valid UTF-8, never its value.

    With errors="surrogateescape", only a lone surrogate outside U+DC80 to U+DCFF fails, see invalid_utf8.
    """
    failed_result = failed_result or {}

    for name, value in settings:
        found = invalid_utf8(value, name, errors)

        if not found:
            continue

        # run_command cannot encode U+D800 to U+DC7F in an argument, and fails with a traceback
        if errors == "surrogateescape":
            module.fail_json(
                msg=f"invalid {found}: it must not contain a lone surrogate code point from U+D800 to U+DC7F, which cannot be passed to kopia",
                **failed_result,
            )

        # a lone surrogate reaches kopia as a raw byte or as a JSON escape, and kopia records text that is not valid
        # UTF-8 with U+FFFD in its place, so the value it reports never matches
        module.fail_json(
            msg=f"invalid {found}: it must be valid UTF-8, without a lone surrogate code point, as kopia records other text with U+FFFD in its place",
            **failed_result,
        )


def text_labels(value):
    """Return value with every string in it, a key or item at any depth, written as text_label writes it."""
    if isinstance(value, str):
        return text_label(value)

    if isinstance(value, dict):
        return {text_labels(key): text_labels(item) for key, item in value.items()}

    if isinstance(value, list):
        return [text_labels(item) for item in value]

    return value


def config_path(module):
    """Return the configuration file kopia uses, which it looks up in its configuration directory for a bare name."""
    path = module.params.get("config_file") or os.environ.get("KOPIA_CONFIG_PATH") or "repository.config"

    if os.path.basename(path) != path:
        return path

    settings = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.environ.get("HOME", ""), ".config")

    # kopia joins the path with Go's filepath.Join, which cleans it
    return clean_path(os.path.join(settings, "kopia", path))


def check_readable(module, path, label, failed_result):
    """Fail when path is a FIFO or a character device, on which kopia can wait forever reading it."""
    try:
        mode = os.stat(path).st_mode
    except OSError:
        return

    # kopia reports any other file it cannot read or decode, such as a directory
    if stat.S_ISFIFO(mode) or stat.S_ISCHR(mode):
        module.fail_json(
            msg=f"invalid {label} {text_label(path)}: it is a FIFO or a character device, which kopia can wait reading forever",
            **failed_result,
        )


def check_connection(module, failed_result=None):
    """Fail before kopia runs for a config_file that cannot be passed to kopia, or files kopia would wait reading."""
    failed_result = failed_result or {}
    config_file = module.params.get("config_file")

    # os.stat fails with a traceback for a NUL, and run_command for U+D800 to U+DC7F; it passes U+DC80 to U+DCFF to
    # kopia as the bytes they stand for
    if config_file and "\x00" in config_file:
        module.fail_json(msg="invalid config_file: it must not contain a NUL character", **failed_result)

    check_utf8(module, [("config_file", config_file)], errors="surrogateescape", failed_result=failed_result)

    path = config_path(module)
    check_readable(module, path, "config_file" if config_file else "kopia configuration file", failed_result)

    # kopia reads the persisted password when none is given, as it reads an empty KOPIA_PASSWORD
    if not module.params.get("password"):
        check_readable(module, f"{path}.kopia-password", "kopia password file", failed_result)


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
    try:
        null = os.open(os.devnull, os.O_RDONLY)
    except OSError as error:
        module.fail_json(msg=f"unable to open {os.devnull} as the standard input of kopia: {error}")

    # with standard input closed, os.open returns 0, which is then already /dev/null
    if null != 0:
        try:
            os.dup2(null, 0)
        finally:
            os.close(null)

    rc, stdout, stderr = module.run_command(command, environ_update=environ, expand_user_and_vars=False)

    # kopia's messages can repeat a value with bytes that are not valid UTF-8, which every message must be
    stderr = text_label(stderr)

    if rc != 0 and PASSWORD_PROMPT_ERROR in stderr:
        stderr = f"kopia needs the repository password, which is not given and not persisted next to {text_label(config_path(module))}: {stderr.strip()}"

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
    label = text_label(path)

    if status is None:
        module.fail_json(msg=f"unable to {operation} of {label}: repository is not connected", **failed_result)

    # kopia fills in the client user and host of every connection
    username = status["clientOptions"]["username"]
    hostname = status["clientOptions"]["hostname"]

    # kopia splits user@host:/path at the first "@" and the first ":", so a host may contain "@"
    if "@" in username or ":" in username or ":" in hostname:
        module.fail_json(
            msg=f"unable to {operation} of {text_label(absolute)}: kopia cannot list it for {username!r} at {hostname!r}, splitting at the first '@' and ':'",
            **failed_result,
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
        return json.loads(stdout)

    if "repository is not connected" in stderr:
        return None

    module.fail_json(msg=f"{prefix}unable to query kopia repository status: {stderr.strip()}", **failed_result)


def maintenance_info(module, failed_result=None):
    failed_result = failed_result or {}
    rc, stdout, stderr = kopia_command(module, ["maintenance", "info", "--json"])

    if rc != 0:
        module.fail_json(msg=f"unable to query kopia maintenance info: {stderr.strip()}", **failed_result)

    return json.loads(stdout)


def policy_export(module, target, failed_result=None):
    failed_result = failed_result or {}
    # after "--", kopia reads a target starting with "-", such as "--global", as a path, as policy import does
    rc, stdout, stderr = kopia_command(module, ["policy", "export", "--", target])

    if rc == 0:
        return next(iter(json.loads(stdout).values()), {})

    if "policy not found" in stderr:
        return None

    module.fail_json(msg=f"unable to export kopia policy {text_label(target)}: {stderr.strip()}", **failed_result)


def check_policy_target(module, target, failed_result=None):
    """Fail before kopia runs for a target that kopia's policy commands read differently."""
    failed_result = failed_result or {}

    # kopia policy import reads every target as a path, but the other commands look a target up as a manifest ID
    # first, such as the ID of another policy or of a snapshot, whose source they then use
    if MANIFEST_ID.fullmatch(target):
        module.fail_json(
            msg=f"invalid target {target}: kopia policy export, show and delete read it as a manifest ID, but import as a path; write the directory ./{target}",
            **failed_result,
        )


def go_fold(name):
    """Return name folded as Go's encoding/json folds a key to match it to one of kopia's ASCII field names.

    Go folds an ASCII letter, the Kelvin sign U+212A to K and the long s U+017F to S; it folds no other character to
    an ASCII letter, so any other character is kept.
    """
    folds = {"\u212a": "K", "\u017f": "S"}

    return "".join(folds.get(char, char.upper() if char.isascii() else char) for char in name)


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
