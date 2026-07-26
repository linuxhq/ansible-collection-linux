# rush

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Restricted user shell

## Requirements

None

## Role Variables

    rush_global:
      - debug 1
    rush_rules:
      - name: default
        rules:
          - clrenv
          - keepenv USER LOGNAME HOME PATH
          - fall-through

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.rush
          rush_global:
            - debug 1
            - include-security all
            - sleep-time 0
          rush_rules:
            - name: default
              rules:
                - clrenv
                - keepenv USER LOGNAME HOME PATH
                - fall-through
            - name: rsync
              rules:
                - chdir "~"
                - match $command ~ "^rsync --server"
                - set program = "/usr/bin/rsync"
                - set [0] = "/usr/bin/rsync"
