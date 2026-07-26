# authorized\_key

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage presence of authorized keys on a host

## Requirements

None

## Role Variables

    authorized_key_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.authorized_key
          authorized_key_list:
            - user: root
              exclusive: true
              key: >-
                ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBwCfEABKtScVJMqT8kH0rdaisRopPeLqAUnRz4BKM7S
