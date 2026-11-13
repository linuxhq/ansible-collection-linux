# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json

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

    return module.run_command(command, environ_update=environ)


def repository_status(module, password=None):
    rc, stdout, stderr = kopia_command(module, ["repository", "status", "--json"], password=password)

    if rc == 0:
        try:
            return json.loads(stdout)
        except ValueError:
            module.fail_json(msg=f"unable to parse kopia repository status output: {stdout.strip()}")

    if "repository is not connected" in stderr:
        return None

    module.fail_json(msg=f"unable to query kopia repository status: {stderr.strip()}")


def maintenance_info(module):
    rc, stdout, stderr = kopia_command(module, ["maintenance", "info", "--json"])

    if rc != 0:
        module.fail_json(msg=f"unable to query kopia maintenance info: {stderr.strip()}")

    try:
        return json.loads(stdout)
    except ValueError:
        module.fail_json(msg=f"unable to parse kopia maintenance info output: {stdout.strip()}")


def policy_export(module, target):
    rc, stdout, stderr = kopia_command(module, ["policy", "export", target])

    if rc == 0:
        try:
            policies = json.loads(stdout)
        except ValueError:
            module.fail_json(msg=f"unable to parse kopia policy export output: {stdout.strip()}")

        return next(iter(policies.values()), {})

    if "policy not found" in stderr:
        return None

    module.fail_json(msg=f"unable to export kopia policy: {stderr.strip()}")


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
    return prune_empty(omit_empty(policy, POLICY_OMITEMPTY))


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
