# rush

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Restricted user shell

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    rush_global:
      - debug 1
    rush_rules:
      - name: default
        rules:
          - clrenv
          - keepenv USER LOGNAME HOME PATH
          - fall-through
    rush_version: 2.3

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
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
