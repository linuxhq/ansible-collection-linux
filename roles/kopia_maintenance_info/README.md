# kopia\_maintenance\_info

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Gather information about kopia maintenance

## Requirements

None

## Role Variables

    kopia_maintenance_info_config_file: null

## Dependencies

None

## Return Values

    _kopia_maintenance_info_dict

## Example Playbook

    - hosts: server
      roles:
        - linuxhq.linux.kopia_maintenance_info
