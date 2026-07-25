# pam\_limit

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

PAM module to limit resources

## Requirements

None

## Role Variables

    pam_limit_d: []
    pam_limit_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.pam_limit
          pam_limit_list:
            - domain: '*'
              limit_item: core
              limit_type: hard
              value: 0

          pam_limit_d:
            - file: 99-vagrant
              limits:
                - domain: vagrant
                  limit_item: locks
                  limit_type: hard
                  value: 1024
                - domain: vagrant
                  limit_item: memlock
                  limit_type: hard
                  value: 4096
