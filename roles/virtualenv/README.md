# virtualenv

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage presence of virtual environments on a host

## Requirements

None

## Role Variables

    virtualenv_become: false
    virtualenv_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.virtualenv
          virtualenv_become: true
          virtualenv_list:
            - virtualenv: /opt/ansible
              virtualenv_command: /usr/bin/python3 -m venv
              name:
                - 'ansible>8,<9'
              extra_args: '--no-cache-dir'
