# permission

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage file permissions on a host

## Requirements

None

## Role Variables

    permission_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.permission
          permission_list:
            - path: /usr/bin/su
              mode: '0755'
