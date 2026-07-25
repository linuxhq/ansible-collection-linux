# kopia\_repository\_info

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Gather information about a kopia repository

## Requirements

None

## Role Variables

    kopia_repository_info_config_file: null

## Dependencies

None

## Return Values

    _kopia_repository_info_dict

## Example Playbook

    - hosts: server
      roles:
        - linuxhq.linux.kopia_repository_info
