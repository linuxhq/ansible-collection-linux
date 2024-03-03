# sudo

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Execute a command as another user

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    sudoers_alias_cmnds: []
    sudoers_alias_hosts: []
    sudoers_alias_runas: []
    sudoers_alias_users: []
    sudoers_always_set_home: true
    sudoers_env_keep: []
    sudoers_env_reset: true
    sudoers_d: []
    sudoers_includedir: /etc/sudoers.d
    sudoers_match_group_by_gid: true
    sudoers_nopasswd_root: false
    sudoers_nopasswd_wheel: false
    sudoers_requiretty: false
    sudoers_visiblepw: false

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.sudo
          sudoers_d:
            - file: linuxhq
              user: %linuxhq
              host: ALL
              runas: ALL
              cmnds:
                - NOPASSWD:ALL

## License

Copyright (C) 2023 Linux HeadQuarters

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
