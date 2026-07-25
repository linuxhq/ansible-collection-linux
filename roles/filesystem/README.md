# filesystem

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Makes a filesystem

## Requirements

None

## Role Variables

    filesystem_list: []
    filesystem_packages:
      - e2fsprogs
      - xfsprogs

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.filesystem
          filesystem_list:
            - dev: /dev/sdb1
              fstype: ext4
