# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_policy
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.3.0
short_description: Manage a kopia snapshot policy
description:
  - Define, replace, or delete the snapshot policy for a kopia target.
  - The desired policy is compared against C(kopia policy export) and applied
    with C(kopia policy import), which replaces the defined policy for the
    target, so O(policy) always describes the complete desired policy.
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
    type: path
  policy:
    description:
      - Complete desired policy for the target, given as snake_case keys
        mirroring the JSON structure of C(kopia policy export), for example
        V(retention.keep_latest) or V(compression.compressor_name).
      - Keys are converted to kopia's camelCase, so V(keep_latest) becomes
        C(keepLatest).
      - Fields left out are removed from the defined policy and fall back to
        inherited values.
      - Required when O(state=present).
    type: dict
  state:
    description:
      - V(present) ensures the defined policy matches O(policy) exactly.
      - V(absent) deletes the defined policy so the target only inherits.
    type: str
    choices:
      - absent
      - present
    default: present
  target:
    description:
      - Policy target, a directory path, C(user@host), C(user@host:/path), or
        V((global)) for the global policy.
      - Use absolute paths, kopia canonicalizes them into the policy target.
    type: str
    required: true
requirements:
  - kopia
"""

EXAMPLES = r"""
- name: Ensure kopia snapshot policy is present
  linuxhq.linux.kopia_policy:
    state: present
    target: /home/vagrant
    policy:
      compression:
        compressor_name: gzip
      retention:
        keep_annual: 0
        keep_hourly: 24
        keep_latest: 2
        keep_monthly: 3
        keep_weekly: 4
      scheduling:
        interval_seconds: 3600

- name: Ensure kopia global policy is managed
  linuxhq.linux.kopia_policy:
    state: present
    target: (global)
    policy:
      retention:
        keep_latest: 10

- name: Ensure kopia snapshot policy is absent
  linuxhq.linux.kopia_policy:
    state: absent
    target: /home/vagrant
"""

RETURN = r"""
policy:
  description: Defined policy reported by C(kopia policy export).
  returned: when O(state=present)
  type: dict
  sample:
    compression:
      compressor_name: gzip
    retention:
      keep_hourly: 24
      keep_latest: 2
    scheduling:
      interval_seconds: 3600
"""

import json
import os

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import (
    camel_dict_to_snake_dict,
    snake_dict_to_camel_dict,
)
from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    kopia_available,
    kopia_command,
    policy_export,
    prune_empty,
)


def ensure_present(module):
    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=True, policy={})

    target = module.params["target"]
    desired = prune_empty(snake_dict_to_camel_dict(module.params["policy"]))
    current = policy_export(module, target)

    if current is not None and prune_empty(current) == desired:
        module.exit_json(
            changed=False, policy=camel_dict_to_snake_dict(prune_empty(current))
        )

    if module.check_mode:
        module.exit_json(changed=True, policy=camel_dict_to_snake_dict(desired))

    source = os.path.join(module.tmpdir, "policy.json")
    with open(source, "w") as handle:
        json.dump({target: desired}, handle)

    rc, _dummy, stderr = kopia_command(
        module, ["policy", "import", "--from-file", source]
    )

    if rc != 0:
        module.fail_json(msg=f"unable to import kopia policy: {stderr.strip()}")

    current = policy_export(module, target)

    module.exit_json(
        changed=True, policy=camel_dict_to_snake_dict(prune_empty(current or {}))
    )


def ensure_absent(module):
    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=True)

    target = module.params["target"]
    current = policy_export(module, target)

    if current is None:
        module.exit_json(changed=False)

    if module.check_mode:
        module.exit_json(changed=True)

    rc, _dummy, stderr = kopia_command(module, ["policy", "delete", target])

    if rc != 0:
        module.fail_json(msg=f"unable to delete kopia policy: {stderr.strip()}")

    module.exit_json(changed=True)


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "policy": {"type": "dict"},
        "state": {
            "type": "str",
            "choices": ["absent", "present"],
            "default": "present",
        },
        "target": {"type": "str", "required": True},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[("state", "present", ("policy",))],
        supports_check_mode=True,
    )

    if module.params["state"] == "present":
        ensure_present(module)

    ensure_absent(module)


if __name__ == "__main__":
    main()
