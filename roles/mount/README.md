# mount

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Control active and configured mount points

## Requirements

None

## Role Variables

    mount_list: []

## Return Values

None

## Dependencies

* [linuxhq.aws.device\_info](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/device_info)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.mount
          mount_list:
            - fstype: ext4
              opts: nodev,noexec,nosuid
              path: /srv
              src: LABEL=srv
