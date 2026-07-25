# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json


def kopia_flags(options):
    """Convert a snake_case options dict into kopia CLI flags."""
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


def kopia_command(module, args, password=None):
    """Run the kopia CLI and return (rc, stdout, stderr)."""
    kopia = module.get_bin_path("kopia", required=True)

    command = [kopia]
    if module.params.get("config_file"):
        command.append(f"--config-file={module.params['config_file']}")
    command.extend(args)

    environ = {"KOPIA_CHECK_FOR_UPDATES": "false"}
    if password is not None:
        environ["KOPIA_PASSWORD"] = password

    return module.run_command(command, environ_update=environ)


def repository_status(module):
    """Return the parsed repository status, or None when not connected."""
    rc, stdout, stderr = kopia_command(module, ["repository", "status", "--json"])

    if rc == 0:
        try:
            return json.loads(stdout)
        except ValueError:
            module.fail_json(
                msg=f"unable to parse kopia repository status output: {stdout.strip()}"
            )

    if "repository is not connected" in stderr:
        return None

    module.fail_json(msg=f"unable to query kopia repository status: {stderr.strip()}")


def maintenance_info(module):
    """Return the parsed maintenance settings and schedule."""
    rc, stdout, stderr = kopia_command(module, ["maintenance", "info", "--json"])

    if rc != 0:
        module.fail_json(
            msg=f"unable to query kopia maintenance info: {stderr.strip()}"
        )

    try:
        return json.loads(stdout)
    except ValueError:
        module.fail_json(
            msg=f"unable to parse kopia maintenance info output: {stdout.strip()}"
        )


def policy_export(module, target):
    """Return the defined policy for target, or None when no policy is defined."""
    rc, stdout, stderr = kopia_command(module, ["policy", "export", target])

    if rc == 0:
        try:
            policies = json.loads(stdout)
        except ValueError:
            module.fail_json(
                msg=f"unable to parse kopia policy export output: {stdout.strip()}"
            )
        return next(iter(policies.values()), {})

    if "policy not found" in stderr:
        return None

    module.fail_json(msg=f"unable to export kopia policy: {stderr.strip()}")


def prune_empty(value):
    """Recursively drop dict entries whose value is None or an empty dict."""
    if not isinstance(value, dict):
        return value

    pruned = {key: prune_empty(item) for key, item in value.items() if item is not None}

    return {key: item for key, item in pruned.items() if item != {}}
