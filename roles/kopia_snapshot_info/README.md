# kopia\_snapshot\_info

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Gather information about kopia snapshots

## Requirements

None

## Role Variables

    kopia_snapshot_info_config_file: null
    kopia_snapshot_info_password: null
    kopia_snapshot_info_path: null

## Dependencies

None

## Return Values

    _kopia_snapshot_info_list

## Example Playbook

    - hosts: server
      roles:
        - linuxhq.linux.kopia_snapshot_info
