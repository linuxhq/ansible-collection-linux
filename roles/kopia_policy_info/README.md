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

    _kopia_policy_info_dict
    _kopia_policy_info_list

## Example Playbook

    - hosts: server
      roles:
        - linuxhq.linux.kopia_policy_info
