# kopia\_policy\_info

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Gather information about kopia policies

## Requirements

None

## Role Variables

    kopia_policy_info_config_file: null
    kopia_policy_info_target: null

## Dependencies

None

## Return Values

    _kopia_policy_info_defined
    _kopia_policy_info_effective_policy
    _kopia_policy_info_list
    _kopia_policy_info_policy

With `kopia_policy_info_target` set, `_kopia_policy_info_defined` tells
whether a policy is defined for the target, `_kopia_policy_info_policy` holds
that defined policy and `_kopia_policy_info_effective_policy` the effective
policy, with inherited values resolved, and `_kopia_policy_info_list` is `[]`.
Without it, `_kopia_policy_info_list` holds every policy defined in the
repository, `_kopia_policy_info_defined` is `false`, and the policies are `{}`.

## Example Playbook

    - hosts: server
      roles:
        - linuxhq.linux.kopia_policy_info
