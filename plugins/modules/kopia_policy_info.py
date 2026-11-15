#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_policy_info
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Gather kopia snapshot policies
description:
  - List the policies defined in the kopia repository, or look up a single
    target's defined and effective policy.
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
    type: path
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
      - When set, RV(policy) and RV(effective_policy) are returned for the
        single target instead of RV(policies).
      - Passed to kopia as given, so V(~) and environment variables are not
        expanded.
      - A target that is not valid UTF-8, such as one with a lone surrogate
        code point, fails before kopia runs, also in check mode, because kopia
        records a target with U+FFFD in its place.
    type: str
requirements:
  - kopia >= 0.18.0
attributes:
  check_mode:
    description: This module only retrieves information and does not modify state.
    support: full
    details: Returns empty result data when Kopia is unavailable.
  diff_mode:
    description: Diff mode is not supported.
    support: none
"""

EXAMPLES = r"""
- name: Ensure kopia policies are gathered
  linuxhq.linux.kopia_policy_info:
  register: __kopia_policy_query

- name: Ensure kopia policy for a target is gathered
  linuxhq.linux.kopia_policy_info:
    target: /home/vagrant
  register: __kopia_policy_query
"""

RETURN = r"""
defined:
  description: Whether a policy is defined for O(target).
  returned: when O(target) is set
  type: bool
  sample: true
effective_policy:
  description:
    - Effective policy for O(target) reported by C(kopia policy show), with
      inherited values resolved.
  returned: when O(target) is set
  type: dict
  sample:
    compression:
      compressor_name: gzip
    retention:
      keep_daily: 7
      keep_latest: 2
policies:
  description: Policies defined in the repository from C(kopia policy list).
  returned: when O(target) is not set
  type: list
  elements: dict
  sample:
    - id: 5051ad95ebe43a87733f69615eb4ee9c
      target:
        host: ''
        path: ''
        user_name: ''
      retention:
        keep_latest: 10
policy:
  description:
    - Defined policy for O(target) reported by C(kopia policy export).
    - Empty when no policy is defined for the target.
  returned: when O(target) is set
  type: dict
  sample:
    retention:
      keep_latest: 2
"""

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    check_utf8,
    kopia_available,
    kopia_command,
    policy_export,
    prune_empty,
)


def info(module):
    check_utf8(module, [("target", module.params["target"])])

    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=False, defined=False, effective_policy={}, policy={})

    target = module.params["target"]
    defined = policy_export(module, target)

    rc, stdout, stderr = kopia_command(module, ["policy", "show", "--json", target])

    if rc != 0:
        module.fail_json(msg=f"unable to show kopia policy {target}: {stderr.strip()}")

    try:
        effective = json.loads(stdout)
    except ValueError:
        module.fail_json(msg=f"unable to parse kopia policy show output for {target}: {stdout.strip()}")

    module.exit_json(
        changed=False,
        defined=defined is not None,
        effective_policy=camel_dict_to_snake_dict(effective),
        policy=camel_dict_to_snake_dict(prune_empty(defined or {})),
    )


def list_policies(module):
    if module.check_mode and not kopia_available(module):
        module.exit_json(changed=False, policies=[])

    rc, stdout, stderr = kopia_command(module, ["policy", "list", "--json"])

    if rc != 0:
        module.fail_json(msg=f"unable to list kopia policies: {stderr.strip()}")

    try:
        policies = json.loads(stdout)
    except ValueError:
        module.fail_json(msg=f"unable to parse kopia policy list output: {stdout.strip()}")

    module.exit_json(
        changed=False,
        policies=[camel_dict_to_snake_dict(policy) for policy in policies],
    )


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "target": {"type": "str"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    if module.params["target"] is not None:
        info(module)

    list_policies(module)


if __name__ == "__main__":
    main()
