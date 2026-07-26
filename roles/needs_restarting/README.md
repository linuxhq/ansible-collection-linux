# needs\_restarting

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

DNF needs-restarting Plugin

## Requirements

None

## Role Variables

    needs_restarting_crontab: null
    needs_restarting_package_dir: /etc/dnf/plugins/needs-restarting.d
    needs_restarting_package_list: []
    needs_restarting_user: root

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.needs_restarting
          needs_restarting_crontab: '0 8 * * 1'
          needs_restarting_package_list:
            - kernel-lt
            - kernel-ml
