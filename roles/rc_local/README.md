# rc\_local

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Compatibility

## Requirements

None

## Role Variables

    rc_local_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.rc_local
          rc_local_list:
            - echo 1 > /proc/sys/kernel/modules_disabled
