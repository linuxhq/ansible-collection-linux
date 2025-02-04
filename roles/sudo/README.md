# sudo

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Execute a command as another user

## Requirements

None

## Role Variables

    sudo_alias_cmnds: []
    sudo_alias_hosts: []
    sudo_alias_runas: []
    sudo_alias_users: []

    sudo_always_set_home: true
    sudo_env_keep: []
    sudo_env_reset: true
    sudo_includedir: /etc/sudoers.d
    sudo_match_group_by_gid: true
    sudo_requiretty: false
    sudo_visiblepw: false

    sudo_d: []

    sudo_nopasswd_root: false
    sudo_nopasswd_wheel: false

    sudo_pam:
      - module_interface: auth
        control_flag: include
        module_name: system-auth
      - module_interface: account
        control_flag: include
        module_name: system-auth
      - module_interface: password
        control_flag: include
        module_name: system-auth
      - module_interface: session
        control_flag: include
        module_name: system-auth

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.sudo
          sudo_d:
            - file: linuxhq
              user: '%linuxhq'
              host: ALL
              runas: ALL
              cmnds:
                - NOPASSWD:ALL
          sudo_env_keep:
            - SSH_AUTH_SOCK
          sudo_pam:
            - module_interface: auth
              control_flag: sufficient
              module_name: pam_ssh_agent_auth.so
              module_arguments: file=/etc/security/authorized_keys
            - module_interface: auth
              control_flag: include
              module_name: system-auth
            - module_interface: account
              control_flag: include
              module_name: system-auth
            - module_interface: password
              control_flag: include
              module_name: system-auth
            - module_interface: session
              control_flag: include
              module_name: system-auth

## License

Copyright (C) 2025 Linux HeadQuarters

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
