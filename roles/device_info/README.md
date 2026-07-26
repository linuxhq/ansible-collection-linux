# device\_info

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Gather information about devices and partitions

## Requirements

None

## Role Variables

None

## Dependencies

None

## Return Values

    _device_info_dict
    _device_info_list

## Example Playbook

    - hosts: server
      roles:
        - linuxhq.linux.device_info
