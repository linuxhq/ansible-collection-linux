#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_policy
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
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
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
    type: path
  policy:
    description:
      - Complete desired policy for the target, given as snake_case keys
        mirroring the JSON structure of C(kopia policy export), for example
        V(retention.keep_latest) or V(compression.compressor_name).
      - Keys are converted to kopia's camelCase, so V(keep_latest) becomes
        C(keepLatest). Write keys in snake_case, such as V(keep_latest), or in
        kopia's camelCase, such as V(keepLatest).
      - kopia matches keys to its fields ignoring case, but reports them in
        camelCase, so a key that converts to other capitalization, such as
        V(Retention) or V(KEEP_LATEST), would never match. Such a key, one that
        starts with an upper-case letter, contains two upper-case letters in a
        row, ends with an upper-case letter or contains a character other than
        an ASCII letter or digit once converted, is rejected before kopia runs,
        also in check mode. A key written without its word breaks, such as
        V(keeplatest), cannot be told apart from a field name and reports a
        change on every run.
      - Text that is not valid UTF-8, such as a lone surrogate code point, in a
        key or value is rejected before kopia runs, also in check mode, because
        kopia records it with U+FFFD in its place.
      - Fields left out are removed from the defined policy and fall back to
        inherited values.
      - kopia does not store V(false), V(0), an empty string or an empty list
        for fields such as C(scheduling.manual), C(scheduling.interval_seconds),
        C(files.max_file_size), C(files.ignore), C(compression.compressor_name)
        or C(no_parent), so these values are treated as left out, the same as
        kopia treats them. Fields kopia stores as optional values, such as the
        C(retention) counts, keep V(0) and V(false).
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
      - kopia reads a target in which an V(@) comes before any V(:) as
        C(user@host) or C(user@host:path), so a directory whose path is such a
        path, such as V(/home/alice@example.com), must be written as
        C(user@host:/path). A path with a V(:) before its first V(@), such as
        V(/srv/a:b@c), is read as a directory path. A target that starts with
        V(@) and contains V(:), such as V(@host:/path), is read as a relative
        directory path.
      - kopia stores the user, host and path of C(user@host) and
        C(user@host:/path) as given. To match the snapshots of the client, the
        user and host must be the C(clientOptions.username) and
        C(clientOptions.hostname) reported by C(kopia repository status), where
        the host defaults to the short, lowercased hostname, and the path must
        be absolute and clean, without V(.) or V(..) components or a trailing
        V(/).
      - kopia splits C(user@host:/path) at the first V(@) and the first V(:), so
        when the client user contains V(@) or V(:), or the host contains V(:),
        no target can name a directory whose path is one in which an V(@) comes
        before any V(:), as kopia would store a different source.
      - kopia makes a bare directory path absolute and cleans it into the
        policy target.
      - A target of 32 lowercase hexadecimal digits is rejected before kopia
        runs, also in check mode, because C(kopia policy export),
        C(kopia policy show) and C(kopia policy delete) read it as a manifest
        ID, such as that of another policy or of a snapshot, whose source they
        use instead, while C(kopia policy import) reads it as a path. Write a
        relative directory with such a name as V(./name).
      - A target that starts with V(-) is passed to kopia as a target, never as
        a command-line flag, so V(--global) is a relative directory path, and
        V(-svc@host:/path) names the client user V(-svc). The global policy is
        V((global)).
      - Passed to kopia as given, so V(~) and environment variables are not
        expanded.
      - A target that is not valid UTF-8, such as one with a lone surrogate
        code point, is rejected before kopia runs, also in check mode, because
        kopia records it with U+FFFD in its place.
    type: str
    required: true
requirements:
  - kopia >= 0.18.0
attributes:
  check_mode:
    description: Predicts changes without modifying the target.
    support: full
    details: When Kopia is unavailable, reports changed for present policies and unchanged for absent policies.
  diff_mode:
    description: Diff mode is not supported.
    support: none
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
  description:
    - Defined policy reported by C(kopia policy export).
    - In check mode, when a change would be made, the desired policy from
      O(policy), without the values kopia does not store.
    - Empty when kopia is unavailable in check mode.
    - Empty when the module fails after running kopia.
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
import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import (
    camel_dict_to_snake_dict,
    snake_dict_to_camel_dict,
)

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    check_policy_target,
    check_utf8,
    kopia_available,
    kopia_command,
    policy_export,
    policy_normalize,
    prune_empty,
    same_value,
)

# kopia's field names are camelCase words, each capital followed by a lower-case letter or digit
POLICY_KEY = re.compile(r"[a-z][a-z0-9]*(?:[A-Z][a-z0-9]+)*")


def camel_key(key):
    return next(iter(snake_dict_to_camel_dict({key: None})))


def check_policy_keys(module, value, name):
    """Fail naming the first key that converts to a capitalization kopia does not report."""
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{name}.{key}"

            # kopia matches field names ignoring case, so it accepts such a key, then reports the field in camelCase
            if not POLICY_KEY.fullmatch(camel_key(key)):
                module.fail_json(
                    msg=(
                        f"invalid policy key {child}: kopia reads it as {camel_key(key)}, which kopia matches ignoring "
                        "case but reports in camelCase, so the policy would never match; write it in snake_case, "
                        "such as keep_latest, or in kopia's camelCase, such as keepLatest"
                    )
                )

            check_policy_keys(module, item, child)

    elif isinstance(value, list):
        for index, item in enumerate(value):
            check_policy_keys(module, item, f"{name}[{index}]")


def ensure_present(module):
    check_utf8(module, [("target", module.params["target"]), ("policy", module.params["policy"])])
    check_policy_target(module, module.params["target"])
    check_policy_keys(module, module.params["policy"], "policy")

    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=True, policy={})

    target = module.params["target"]
    desired = policy_normalize(snake_dict_to_camel_dict(module.params["policy"]))
    current = policy_export(module, target, failed_result={"policy": {}})

    if current is not None and same_value(policy_normalize(current), desired):
        module.exit_json(changed=False, policy=camel_dict_to_snake_dict(prune_empty(current)))

    if module.check_mode:
        module.exit_json(changed=True, policy=camel_dict_to_snake_dict(desired))

    source = os.path.join(module.tmpdir, "policy.json")
    with open(source, "w") as handle:
        json.dump({target: desired}, handle)

    rc, _dummy, stderr = kopia_command(module, ["policy", "import", "--from-file", source])

    if rc != 0:
        module.fail_json(msg=f"unable to import kopia policy {target}: {stderr.strip()}", policy={})

    current = policy_export(module, target, failed_result={"changed": True, "policy": {}})

    module.exit_json(changed=True, policy=camel_dict_to_snake_dict(prune_empty(current or {})))


def ensure_absent(module):
    check_utf8(module, [("target", module.params["target"])])
    check_policy_target(module, module.params["target"])

    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=False)

    target = module.params["target"]
    current = policy_export(module, target)

    if current is None:
        module.exit_json(changed=False)

    if module.check_mode:
        module.exit_json(changed=True)

    rc, _dummy, stderr = kopia_command(module, ["policy", "delete", "--", target])

    if rc != 0:
        module.fail_json(msg=f"unable to delete kopia policy {target}: {stderr.strip()}")

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
